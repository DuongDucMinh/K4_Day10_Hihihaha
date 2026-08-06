from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    print("=== Starting Phase 2 Data Corruption & Repair Flow ===")
    settings = load_settings()
    run_date = now_utc()

    # 1. Load Baseline Metrics & Clean Dataset
    if not settings.paths.baseline_metrics.exists() or not settings.paths.clean_csv.exists():
        raise FileNotFoundError(
            "Baseline artifacts missing! Please run Phase 1 baseline pipeline (`run_phase1.py`) first."
        )

    baseline_metrics = read_json(settings.paths.baseline_metrics)
    clean_df = pd.read_csv(settings.paths.clean_csv)
    print(f"Loaded baseline clean dataset: {len(clean_df)} records.")

    # 2. Corrupt Dataset
    print("Simulating data corruption (dropping records, blanking summaries, noise injection, stale dates)...")
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    print(f"Corrupted dataset created: {len(corrupted_df)} records.")
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))

    # 3. Rebuild Corrupted Index & Evaluate
    print("Building Corrupted ChromaDB Vector Index...")
    corrupted_index = LocalEmbeddingIndex.build(corrupted_df, settings, settings.paths.corrupted_embeddings_json)

    print("Evaluating Corrupted Pipeline Performance...")
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    print(f"Corrupted Retrieval Hit Rate: {corrupted_bundle.summary['retrieval_hit_rate']:.4f}")

    # 4. Corrupted Observability
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted_quality")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, settings.paths.quality_dir / "corrupted_freshness.json"
    )

    # 5. Data Repair Step (Re-clean from raw records snapshot)
    print("Repairing data pipeline from Raw Records snapshot...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, run_date)
    print(f"Repaired dataset created: {len(repaired_df)} records.")
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))

    # 6. Rebuild Repaired Index & Evaluate
    print("Building Repaired ChromaDB Vector Index...")
    repaired_index = LocalEmbeddingIndex.build(repaired_df, settings, settings.paths.repaired_embeddings_json)

    print("Evaluating Repaired Pipeline Performance...")
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    print(f"Repaired Retrieval Hit Rate: {repaired_bundle.summary['retrieval_hit_rate']:.4f}")

    # 7. Repaired Observability
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired_quality")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, settings.paths.quality_dir / "repaired_freshness.json"
    )

    # 8. Generate Comparison Report
    print("Generating Comparison Report (Baseline vs Corrupted vs Repaired)...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    print("=== Phase 2 Corruption & Repair Flow Completed Successfully ===")


if __name__ == "__main__":
    main()

