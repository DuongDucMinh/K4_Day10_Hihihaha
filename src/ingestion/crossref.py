from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
import time
from typing import Any
import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_html(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    return normalize_whitespace(cleaned)


def _parse_date(date_obj: dict | None) -> str:
    if not isinstance(date_obj, dict):
        return "2024-01-01"
    date_parts = date_obj.get("date-parts", [[]])
    if not date_parts or not date_parts[0]:
        return "2024-01-01"
    parts = date_parts[0]
    year = parts[0] if len(parts) > 0 else 2024
    month = parts[1] if len(parts) > 1 else 1
    day = parts[2] if len(parts) > 2 else 1
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref API payload into a list of PaperRecord."""
    message = payload.get("message", payload)
    items = message.get("items", []) if isinstance(message, dict) else []
    
    records: list[PaperRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        paper_id = item.get("DOI") or item.get("id")
        title_raw = item.get("title", [])
        if isinstance(title_raw, list):
            title = title_raw[0] if title_raw else ""
        else:
            title = str(title_raw or "")
        
        title = _clean_html(title)
        if not paper_id or not title:
            continue
            
        summary = _clean_html(item.get("abstract", ""))
        
        authors_raw = item.get("author", [])
        authors: list[str] = []
        if isinstance(authors_raw, list):
            for a in authors_raw:
                if isinstance(a, dict):
                    given = a.get("given", "").strip()
                    family = a.get("family", "").strip()
                    name = f"{given} {family}".strip()
                    if name:
                        authors.append(name)
                        
        categories_raw = item.get("subject", [])
        categories = [str(c).strip() for c in categories_raw if str(c).strip()] if isinstance(categories_raw, list) else []
        primary_category = categories[0] if categories else "General"
        
        pub_date = _parse_date(item.get("published-online") or item.get("published-print") or item.get("created") or item.get("issued"))
        upd_date = _parse_date(item.get("updated") or item.get("issued") or item.get("created"))
        
        abs_url = item.get("URL", f"https://doi.org/{paper_id}")
        pdf_url = abs_url
        link_list = item.get("link", [])
        if isinstance(link_list, list):
            for link in link_list:
                if isinstance(link, dict) and link.get("content-type") == "application/pdf":
                    pdf_url = link.get("URL", abs_url)
                    break

        publisher = item.get("publisher", "")
        comment = f"Publisher: {publisher}" if publisher else ""

        records.append(
            PaperRecord(
                paper_id=str(paper_id),
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=pub_date,
                updated=upd_date,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch records from Crossref API, save raw response & snapshot, return parsed records."""
    headers = {"User-Agent": "DataObservabilityLab/1.0 (mailto:student@example.com)"}
    params: dict[str, Any] = {
        "query": settings.source_query,
        "rows": settings.max_results,
    }
    if settings.source_filter:
        params["filter"] = settings.source_filter

    url = settings.source_api if settings.source_api.startswith("http") else "https://api.crossref.org/works"
    max_retries = 3
    payload: dict = {}

    
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                payload = resp.json()
                break
            elif resp.status_code in (429, 503, 500, 502, 504):
                time.sleep(2 ** attempt)
            else:
                resp.raise_for_status()
        except Exception as exc:
            if attempt == max_retries - 1:
                # If network fails, fallback to reading existing snapshot if available
                if settings.paths.raw_api_response.exists():
                    payload = read_json(settings.paths.raw_api_response)
                    break
                raise exc
            time.sleep(2 ** attempt)

    if payload:
        write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)
    records_dict = [asdict(rec) for rec in records]
    write_json(settings.paths.raw_records_json, records_dict)
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load raw records from JSON snapshot."""
    raw_data = read_json(path)
    return [PaperRecord(**item) for item in raw_data]

