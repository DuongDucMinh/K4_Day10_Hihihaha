from __future__ import annotations

from pathlib import Path
from typing import Any
import pandas as pd

from core.utils import write_json


def build_test_set(df: pd.DataFrame, output_path: Path | None = None) -> list[dict[str, Any]]:
    """Build a comprehensive evaluation test set from the cleaned dataframe."""
    if df.empty:
        return []

    # Select representative papers (up to 15 papers to keep evaluation fast & diverse)
    sample_df = df.head(15) if len(df) >= 15 else df
    test_set: list[dict[str, Any]] = []
    item_id = 1

    for _, row in sample_df.iterrows():
        paper_id = str(row["paper_id"])
        title = str(row["title"])
        authors = str(row.get("authors_joined", ""))
        summary = str(row.get("summary", ""))
        pub_date = str(row.get("published", ""))
        categories = str(row.get("categories_joined", ""))

        # 1. Summary Question
        if summary:
            test_set.append(
                {
                    "id": f"eval-{item_id}",
                    "question_type": "summary",
                    "question": f"What is the summary of the paper '{title}'?",
                    "ground_truth": summary,
                    "ground_truth_doc_ids": [paper_id],
                }
            )
            item_id += 1

        # 2. Authors Question
        if authors:
            test_set.append(
                {
                    "id": f"eval-{item_id}",
                    "question_type": "authors",
                    "question": f"Who authored the paper '{title}'?",
                    "ground_truth": authors,
                    "ground_truth_doc_ids": [paper_id],
                }
            )
            item_id += 1

        # 3. Publication Date Question
        if pub_date:
            test_set.append(
                {
                    "id": f"eval-{item_id}",
                    "question_type": "date",
                    "question": f"When was the paper '{title}' published?",
                    "ground_truth": pub_date,
                    "ground_truth_doc_ids": [paper_id],
                }
            )
            item_id += 1

        # 4. Categories Question
        if categories:
            test_set.append(
                {
                    "id": f"eval-{item_id}",
                    "question_type": "categories",
                    "question": f"What categories does the paper '{title}' belong to?",
                    "ground_truth": categories,
                    "ground_truth_doc_ids": [paper_id],
                }
            )
            item_id += 1

    if output_path:
        write_json(Path(output_path), test_set)

    return test_set

