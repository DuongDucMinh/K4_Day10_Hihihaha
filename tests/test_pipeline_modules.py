import json
from datetime import datetime
from pathlib import Path
import pytest
import pandas as pd

from core.config import load_settings
from ingestion.crossref import PaperRecord, parse_crossref_payload, load_raw_records
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from evaluation.testset import build_test_set
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_phase1_report, generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def test_crossref_parsing():
    sample_payload = {
        "message": {
            "items": [
                {
                    "DOI": "10.1000/182",
                    "title": ["<jats:p>Test Paper Title</jats:p>"],
                    "abstract": "<jats:p>This is a test abstract about LLM agents.</jats:p>",
                    "author": [{"given": "Jane", "family": "Doe"}],
                    "subject": ["Artificial Intelligence"],
                    "published-online": {"date-parts": [[2026, 2, 1]]},
                    "URL": "https://doi.org/10.1000/182",
                }
            ]
        }
    }
    records = parse_crossref_payload(sample_payload)
    assert len(records) == 1
    rec = records[0]
    assert rec.paper_id == "10.1000/182"
    assert rec.title == "Test Paper Title"
    assert rec.summary == "This is a test abstract about LLM agents."
    assert rec.authors == ["Jane Doe"]
    assert rec.primary_category == "Artificial Intelligence"


def test_clean_dataframe_building():
    rec = PaperRecord(
        paper_id="10.1000/182",
        title="Test Paper Title",
        summary="This is a test abstract about LLM agents.",
        authors=["Jane Doe"],
        categories=["AI"],
        primary_category="AI",
        published="2026-02-01",
        updated="2026-02-01",
        abs_url="https://doi.org/10.1000/182",
        pdf_url="https://doi.org/10.1000/182",
        comment="",
    )
    df = build_clean_dataframe([rec], run_date=datetime(2026, 2, 6))
    assert len(df) == 1
    assert "text_for_embedding" in df.columns
    assert "authors_joined" in df.columns
    assert df.iloc[0]["authors_joined"] == "Jane Doe"


def test_corruption_and_quality_checks(tmp_path):
    settings = load_settings()
    rec = PaperRecord(
        paper_id="10.1000/182",
        title="Test Paper Title",
        summary="This is a test abstract about LLM agents.",
        authors=["Jane Doe"],
        categories=["AI"],
        primary_category="AI",
        published="2026-02-01",
        updated="2026-02-01",
        abs_url="https://doi.org/10.1000/182",
        pdf_url="https://doi.org/10.1000/182",
        comment="",
    )
    clean_df = build_clean_dataframe([rec] * 5, run_date=datetime(2026, 2, 6))
    assert len(clean_df) == 1  # deduplicated

    # Duplicate rows for corruption test
    df_multi = pd.concat([clean_df, clean_df, clean_df, clean_df, clean_df], ignore_index=True)
    df_multi["paper_id"] = [f"id-{i}" for i in range(len(df_multi))]
    
    log_path = tmp_path / "corruption_log.json"
    corrupted_df = corrupt_clean_dataframe(df_multi, log_path)
    assert log_path.exists()
    
    q_report = run_data_quality_checks(corrupted_df, settings, "test_corrupted_quality")
    assert "is_healthy" in q_report


def test_testset_generation(tmp_path):
    rec = PaperRecord(
        paper_id="10.1000/182",
        title="Test Paper Title",
        summary="This is a test abstract about LLM agents.",
        authors=["Jane Doe"],
        categories=["AI"],
        primary_category="AI",
        published="2026-02-01",
        updated="2026-02-01",
        abs_url="https://doi.org/10.1000/182",
        pdf_url="https://doi.org/10.1000/182",
        comment="",
    )
    df = build_clean_dataframe([rec], run_date=datetime(2026, 2, 6))
    out_json = tmp_path / "test_set.json"
    test_set = build_test_set(df, out_json)
    assert len(test_set) >= 4
    assert out_json.exists()
