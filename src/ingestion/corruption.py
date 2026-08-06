from __future__ import annotations

from pathlib import Path
import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path) -> pd.DataFrame:
    """Simulate realistic data corruption scenarios on a cleaned DataFrame."""
    if df.empty:
        write_json(Path(output_log_path), {"status": "empty_dataframe"})
        return df.copy()

    corrupted = df.copy()
    corruption_log: dict[str, Any] = {
        "initial_rows": len(corrupted),
        "actions": [],
    }

    # 1. Drop latest 2 records
    if len(corrupted) > 5:
        dropped_ids = corrupted.iloc[:2]["paper_id"].tolist()
        corrupted = corrupted.iloc[2:].reset_index(drop=True)
        corruption_log["actions"].append({
            "action": "drop_latest_records",
            "count": len(dropped_ids),
            "dropped_ids": dropped_ids,
        })

    # 2. Blank summary on 3 rows
    if len(corrupted) >= 3:
        blank_indices = [0, 2]
        for idx in blank_indices:
            if idx < len(corrupted):
                corrupted.at[idx, "summary"] = ""
                corrupted.at[idx, "summary_chars"] = 0
        corruption_log["actions"].append({
            "action": "blank_summaries",
            "affected_indices": blank_indices,
        })

    # 3. Inject noise into text & truncate titles
    if len(corrupted) >= 2:
        idx = 1
        if idx < len(corrupted):
            corrupted.at[idx, "title"] = corrupted.at[idx, "title"][:15] + " [CORRUPTED_NOISE]"
            corrupted.at[idx, "summary"] = "[TEXT CORRUPTED BY DATA PIPELINE BUG] " + str(corrupted.at[idx, "summary"])
        corruption_log["actions"].append({
            "action": "inject_noise_and_truncate",
            "affected_index": idx,
        })

    # 4. Make published date very old (stale date)
    if len(corrupted) >= 4:
        stale_idx = 3
        if stale_idx < len(corrupted):
            corrupted.at[stale_idx, "published"] = "2000-01-01"
            corrupted.at[stale_idx, "age_days"] = 9000
        corruption_log["actions"].append({
            "action": "make_date_stale",
            "affected_index": stale_idx,
            "new_date": "2000-01-01",
        })

    # 5. Add duplicate rows
    if len(corrupted) >= 2:
        dupe_rows = corrupted.iloc[:2].copy()
        corrupted = pd.concat([corrupted, dupe_rows], ignore_index=True)
        corruption_log["actions"].append({
            "action": "add_duplicates",
            "count": len(dupe_rows),
        })

    # 6. Rebuild text_for_embedding
    def _make_embedding_text(row: pd.Series) -> str:
        parts = [
            f"Title: {row['title']}",
            f"Authors: {row.get('authors_joined', '')}",
            f"Categories: {row.get('categories_joined', '')}",
            f"Published: {row['published']}",
        ]
        if row.get("summary"):
            parts.append(f"Summary: {row['summary']}")
        return "\n".join(parts)

    corrupted["text_for_embedding"] = corrupted.apply(_make_embedding_text, axis=1)

    corruption_log["final_rows"] = len(corrupted)
    write_json(Path(output_log_path), corruption_log)
    return corrupted

