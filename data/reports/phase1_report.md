# Phase 1 Baseline Pipeline Report

## Executive Summary
This report summarizes the baseline data ingestion, data cleaning, retrieval indexing, evaluation metrics, and data observability status for the Crossref Scholarly Paper Corpus.

---

## 1. Data Ingestion & Cleaning
- **Source API:** `Crossref REST API`
- **Query / Subject:** `agentic retrieval augmented generation large language model`
- **Total Records Ingested & Cleaned:** `24`

---

## 2. Evaluation & Agent Performance (Baseline)
| Metric | Score | Target Status |
| :--- | :---: | :---: |
| **Retrieval Hit Rate** | `1.0000` | PASS |
| **Mean Token F1** | `0.7547` | PASS |
| **Judge Accuracy** | `0.6889` | WARN |
| **Mean Judge Score (1-5)** | `3.71` | PASS |

---

## 3. Data Observability & Health
### Data Quality
- **Healthy Status:** `HEALTHY`
- **Total Rows:** `24`
- **Null Paper IDs:** `0`
- **Duplicate Paper IDs:** `0`
- **Empty Summaries:** `0`

### Data Freshness
- **Fresh Status:** `FRESH`
- **Latest Published Date:** `2026-08-05`
- **Oldest Published Date:** `2026-02-13`
- **Average Age (Days):** `77.54`
- **Stale Rows (> Threshold):** `0`
