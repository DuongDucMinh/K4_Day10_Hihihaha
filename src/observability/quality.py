from __future__ import annotations

from pathlib import Path
from typing import Any
import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run comprehensive data quality checks on a DataFrame and save the results."""
    total_rows = int(len(df))
    if total_rows == 0:
        report = {
            "report_name": report_name,
            "total_rows": 0,
            "null_paper_ids": 0,
            "duplicate_paper_ids": 0,
            "null_titles": 0,
            "empty_summaries": 0,
            "short_summaries": 0,
            "stale_rows": 0,
            "is_healthy": False,
        }
    else:
        null_paper_ids = int(df["paper_id"].isna().sum()) if "paper_id" in df else 0
        duplicate_paper_ids = int(df["paper_id"].duplicated().sum()) if "paper_id" in df else 0
        null_titles = int(df["title"].isna().sum() + (df["title"] == "").sum()) if "title" in df else 0
        
        summaries = df["summary"].fillna("").astype(str) if "summary" in df else pd.Series([], dtype=str)
        empty_summaries = int((summaries == "").sum())
        short_summaries = int((summaries.str.len() < 30).sum())

        age_days = df["age_days"] if "age_days" in df else pd.Series([0] * total_rows)
        stale_rows = int((age_days > settings.freshness_threshold_days).sum())

        is_healthy = bool(
            null_paper_ids == 0
            and duplicate_paper_ids == 0
            and null_titles == 0
            and empty_summaries == 0
        )

        report = {
            "report_name": report_name,
            "total_rows": total_rows,
            "null_paper_ids": null_paper_ids,
            "duplicate_paper_ids": duplicate_paper_ids,
            "null_titles": null_titles,
            "empty_summaries": empty_summaries,
            "short_summaries": short_summaries,
            "stale_rows": stale_rows,
            "is_healthy": is_healthy,
        }

    report_file = settings.paths.quality_dir / f"{report_name}.json"
    write_json(report_file, report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path) -> dict[str, Any]:
    """Aggregate freshness metrics and save report JSON to report_path."""
    total_rows = int(len(df))
    if total_rows == 0 or "published" not in df or df["published"].empty:
        report = {
            "latest_published": "N/A",
            "oldest_published": "N/A",
            "avg_age_days": 0.0,
            "stale_rows": 0,
            "total_rows": 0,
            "is_fresh": False,
        }
    else:
        valid_dates = df["published"].dropna().astype(str)
        latest_published = str(valid_dates.max()) if not valid_dates.empty else "N/A"
        oldest_published = str(valid_dates.min()) if not valid_dates.empty else "N/A"
        
        age_days_series = df["age_days"] if "age_days" in df else pd.Series([0] * total_rows)
        avg_age_days = float(round(age_days_series.mean(), 2))
        stale_rows = int((age_days_series > settings.freshness_threshold_days).sum())
        
        is_fresh = bool(stale_rows / total_rows < 0.20) if total_rows > 0 else False

        report = {
            "latest_published": latest_published,
            "oldest_published": oldest_published,
            "avg_age_days": avg_age_days,
            "stale_rows": stale_rows,
            "total_rows": total_rows,
            "freshness_threshold_days": settings.freshness_threshold_days,
            "is_fresh": is_fresh,
        }

    write_json(Path(report_path), report)
    return report

