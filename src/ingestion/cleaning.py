from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw PaperRecord list into a structured pandas DataFrame ready for embedding."""
    if not records:
        return pd.DataFrame(
            columns=[
                "paper_id",
                "title",
                "summary",
                "authors",
                "categories",
                "primary_category",
                "published",
                "updated",
                "abs_url",
                "pdf_url",
                "comment",
                "authors_joined",
                "categories_joined",
                "summary_chars",
                "age_days",
                "text_for_embedding",
            ]
        )

    raw_dicts = [asdict(r) if isinstance(r, PaperRecord) else r for r in records]
    df = pd.DataFrame(raw_dicts)

    # Normalize text fields
    df["title"] = df["title"].fillna("").astype(str).apply(normalize_whitespace)
    df["summary"] = df["summary"].fillna("").astype(str).apply(normalize_whitespace)

    # Format authors and categories joined strings
    def _join_list(val: Any) -> str:
        if isinstance(val, list):
            return compact_join(val, sep=", ")
        return str(val or "")

    df["authors_joined"] = df["authors"].apply(_join_list)
    df["categories_joined"] = df["categories"].apply(_join_list)
    df["summary_chars"] = df["summary"].apply(len)

    # Compute date & age_days
    pub_dt = pd.to_datetime(df["published"], errors="coerce")
    run_dt = pd.to_datetime(run_date.date() if isinstance(run_date, datetime) else run_date)
    df["age_days"] = (run_dt - pub_dt).dt.days.fillna(0).astype(int)

    # Filter out empty title or paper_id
    df = df[(df["paper_id"].astype(str).str.len() > 0) & (df["title"].str.len() > 0)]

    # Deduplicate
    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df = df.drop_duplicates(subset=["title"], keep="first")

    # Build text_for_embedding
    def _make_embedding_text(row: pd.Series) -> str:
        parts = [
            f"Title: {row['title']}",
            f"Authors: {row['authors_joined']}",
            f"Categories: {row['categories_joined']}",
            f"Published: {row['published']}",
        ]
        if row["summary"]:
            parts.append(f"Summary: {row['summary']}")
        return "\n".join(parts)

    df["text_for_embedding"] = df.apply(_make_embedding_text, axis=1)

    # Sort by published date descending
    df = df.sort_values(by=["published"], ascending=False).reset_index(drop=True)
    return df

