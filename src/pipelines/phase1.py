from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    print("=== Starting Phase 1 Baseline Pipeline ===")
    settings = load_settings()
    run_date = now_utc()

    # 1. Fetch or Load Raw Records
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        print(f"Fetching raw records from source: {settings.source_api}...")
        records = fetch_source_records(settings)
    else:
        print(f"Loading raw records from snapshot: {settings.paths.raw_records_json}...")
        records = load_raw_records(settings.paths.raw_records_json)

    print(f"Total raw records loaded: {len(records)}")

    # 2. Clean Data
    clean_df = build_clean_dataframe(records, run_date)
    print(f"Cleaned records count: {len(clean_df)}")
    write_csv(clean_df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))

    # 3. Build Vector Index
    print("Building ChromaDB Vector Index...")
    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)

    # 4. Build Test Set
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        print("Generating evaluation test set...")
        build_test_set(clean_df, settings.paths.eval_testset)
    else:
        print("Using existing test set...")

    # 5. Evaluate Baseline Pipeline
    print("Evaluating Baseline Agent & Retrieval Performance...")
    eval_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    print(f"Baseline Retrieval Hit Rate: {eval_bundle.summary['retrieval_hit_rate']:.4f}")
    print(f"Baseline Mean Token F1:     {eval_bundle.summary['mean_token_f1']:.4f}")

    # 6. Data Observability (Quality & Freshness)
    print("Running Data Quality Checks & Freshness Reporting...")
    quality_summary = run_data_quality_checks(clean_df, settings, "baseline_quality")
    freshness_summary = build_freshness_report(clean_df, settings, settings.paths.freshness_report)

    # 7. Generate Baseline Report
    print("Generating Phase 1 Report...")
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary={
            "total_records": len(clean_df),
            "source_api": settings.source_api,
            "query": settings.source_query,
        },
        metrics=eval_bundle.summary,
        quality=quality_summary,
        freshness=freshness_summary,
    )

    # 8. Demo Agent Sample Execution
    try:
        print("Running RAG Agent Demo...")
        agent = build_agent(settings, index)
        sample_q = "What are the latest research papers in the corpus?"
        answer = run_agent_question(agent, sample_q)
        demo_payload = [{"question": sample_q, "answer": answer}]
        write_json(settings.paths.demo_answers, demo_payload)
    except Exception as exc:
        print(f"Agent demo note: {exc}")

    print("=== Phase 1 Baseline Pipeline Completed Successfully ===")


if __name__ == "__main__":
    main()

