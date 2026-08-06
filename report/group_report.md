# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| ------------------ | -------------------------- |
| Khóa/Lớp | K4 |
| Tên nhóm | Hihihaha |
| Repository | DuongDucMinh/K4_Day10_Hihihaha |
| Ngày hoàn thành | 2026-08-06 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Phạm Tấn Gia Quốc | 2A202601606 | Source Ingestion Owner | `src/ingestion/crossref.py` |
| 2 | Dương Đức Minh | 2A202601306 | Data Model & Eval Set Owner | `src/ingestion/cleaning.py`, `src/evaluation/testset.py` |
| 3 | Thái Hoài An | 2A202601862 | Data Observability Owner | `src/observability/quality.py`, `src/observability/reporting.py` |
| 4 | Nguyễn Thanh Tùng | 2A202601140 | Corruption & Integration Owner | `src/ingestion/corruption.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` |

---

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành 100% toàn bộ hệ thống Data Pipeline & Data Observability end-to-end từ Crossref API.
1. **Baseline Pipeline (Phase 1):** Lấy thành công 24 bản ghi học thuật từ Crossref API, làm sạch dữ liệu, xây dựng ChromaDB Vector Store với model embedding `all-MiniLM-L6-v2`. Kết quả baseline đạt **Retrieval Hit Rate = 1.0000 (100%)** và **Mean Token F1 = 0.7547**.
2. **Controlled Corruption (Phase 2):** Giả lập 5 kịch bản hỏng dữ liệu thực tế (missing latest papers, blank summary, noise text injection, stale dates, duplicate rows). Tín hiệu Data Quality lập tức chuyển sang `UNHEALTHY` (phát hiện `empty_summaries`, `duplicate_paper_ids`, `stale_rows`), kéo theo chỉ số **Retrieval Hit Rate sụt giảm xuống 0.8667 (-13.3%)** và **Token F1 giảm xuống 0.6221 (-13.3%)**.
3. **Data Repair & Recovery:** Hệ thống tự động khôi phục dữ liệu từ Raw Snapshot (`crossref_records.json`), tái cấu trúc pipeline sạch và phục hồi hoàn toàn các chỉ số về **Retrieval Hit Rate = 1.0000** và **Token F1 = 0.7547**.

---

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> Raw response/records snapshot (data/raw/crossref_records.json)
    -> Cleaning & Data modeling (data/clean/papers_clean.csv)
    -> Embedding + ChromaDB index (papers-baseline)
    -> Freeze Evaluation testset (data/eval/test_set.json)
    -> Evaluation Baseline (data/results/baseline_metrics.json)
    -> Data Quality & Freshness reports (data/quality/)
    -> Controlled Corruption (data/clean/papers_clean_corrupted.csv)
    -> Re-index (papers-corrupted) & Re-evaluate
    -> Repair từ Raw Snapshot (data/clean/papers_clean_repaired.csv)
    -> Re-index (papers-repaired) & Re-evaluate
    -> Tri-state Comparison Report (data/reports/corruption_report.md)
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion | Crossref API | Fetch API, exponential backoff retry, parse JSON | `data/raw/crossref_response.json`, `raw_records_json` | Dương Đức Minh |
| Cleaning | Raw Records | Clean text, parse dates, compute `text_for_embedding`, dedup | `data/clean/papers_clean.csv`, `papers_clean.json` | Thành viên 02 |
| Embedding/index | Cleaned DataFrame | MiniLM Embedding + ChromaDB PersistentClient | `data/chroma/`, `data/embeddings/*.json` | Thành viên 03 |
| Evaluation | Cleaned DF + TestSet | Sinh QA pairs, tính Hit Rate, Token F1, LLM Judge | `data/eval/test_set.json`, `data/results/*_metrics.json` | Thành viên 04 |
| Observability | DataFrames | Quality checks (null, dupe, empty summary) & Freshness | `data/quality/*.json`, `data/reports/phase1_report.md` | Thành viên 05 |
| Corruption/Repair | Clean DF & Raw Snapshot | Corrupt data, log anomaly, repair from raw snapshot | `data/results/corruption_log.json`, `corruption_report.md` | Thành viên 05 |

---

## 4. Cách tái hiện kết quả

### Cấu hình môi trường

| Biến/cấu hình | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER` | `gemini` |
| `LLM_MODEL` | `gemini-2.5-flash` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 days |

### Lệnh chạy tái hiện

```powershell
# 1. Cài đặt môi trường
uv sync
uv pip install -e .

# 2. Chạy Pha 1 - Baseline Pipeline
uv run python script/run_phase1.py

# 3. Chạy Pha 2 - Corruption, Repair & Comparison Flow
uv run python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công 100% | 2026-08-06 14:54 | `data/results/baseline_metrics.json` |
| Corruption flow | Thành công 100% | 2026-08-06 14:55 | `data/results/corrupted_metrics.json`, `repaired_metrics.json` |

---

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu
- **Source API:** `https://api.crossref.org/works`
- **Query:** `agentic retrieval augmented generation large language model`
- **Filter:** `from-pub-date:2026-02-07,has-abstract:true`
- **Max Results:** 24 records
- **Cơ chế retry:** Exponential backoff cho HTTP Status 429, 503, 500 với max retries = 3.

### Schema dữ liệu chính

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id` | `str` | Có | DOI duy nhất của bài báo | Filter out nếu thiếu |
| `title` | `str` | Có | Tiêu đề bài báo | Filter out nếu thiếu |
| `summary` | `str` | Không | Abstract/tóm tắt bài báo | Strip HTML tags, normalize whitespace |
| `authors` | `list[str]` | Không | Danh sách tác giả | Format `"Given Family"` |
| `published` | `str` | Có | Ngày xuất bản (YYYY-MM-DD) | Fallback `"2024-01-01"` |
| `text_for_embedding` | `str` | Có | Văn bản hợp nhất cho Vector DB | Tái cấu trúc từ Title + Authors + Categories + Summary |

---

## 6. Evaluation Setup

- **Số lượng mẫu test set:** 45 câu hỏi
- **Loại câu hỏi (`question_type`):** `summary`, `authors`, `date`, `categories`
- **Quy tắc đóng đóng băng test set:** Test set được sinh 1 lần ở Baseline Phase và được lưu cố định tại `data/eval/test_set.json`. Cả 3 trạng thái (`Baseline`, `Corrupted`, `Repaired`) đều sử dụng chung 100% file test set này để đảm bảo so sánh công bằng tuyệt đối.

---

## 7. Kết quả Baseline

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` | **1.0000** | 100% câu hỏi trong test set tìm được đúng tài liệu chứa câu trả lời |
| `mean_token_f1` | **0.7547** | Độ khớp từ giữa câu trả lời RAG và Ground Truth ở mức rất cao |
| `judge_accuracy` | **0.6889** | 68.9% câu trả lời đạt mức chuẩn xác theo đánh giá của Judge |
| `mean_judge_score` | **3.71 / 5.0** | Điểm số chất lượng trung bình của RAG Agent |

---

## 8. Data Quality và Freshness

| Observability Metric | Baseline (Clean) | Corrupted State | Repaired State |
| :--- | :---: | :---: | :---: |
| **Data Quality Status** | `HEALTHY` | `UNHEALTHY` | `HEALTHY` |
| **Total Rows** | 24 | 24 | 24 |
| **Duplicate Paper IDs** | 0 | 2 | 0 |
| **Empty Summaries** | 0 | 2 | 0 |
| **Data Freshness Status** | `FRESH` | `STALE` | `FRESH` |
| **Stale Rows (> 180 days)** | 0 | 1 | 0 |

---

## 9. Corruption Scenarios và Repair

| Corruption Scenario | Cách tạo | Record tác động | Quality signal phát hiện | Tác động thực tế lên RAG | Cách Repair |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **Drop Latest Records** | Xóa 2 bản ghi mới nhất | 2 | Decrease row count | Trực tiếp làm giảm Hit Rate với các câu hỏi liên quan | Reload từ Raw Snapshot |
| **Blank Summary** | Xóa nội dung abstract | 2 | `empty_summaries = 2` | Agent không tìm đủ thông tin tóm tắt | Re-clean từ Raw Snapshot |
| **Noise & Truncate** | Chèn chuỗi rác vào text | 1 | Vector similarity distortion | Làm sai lệch kết quả tìm kiếm ngữ nghĩa | Re-parse từ Raw Snapshot |
| **Stale Date Injection** | Đổi ngày về `2000-01-01` | 1 | `stale_rows = 1` | Báo động Freshness Monitor | Khôi phục date từ Raw Record |
| **Add Duplicate Rows** | Nhân bản dòng | 2 | `duplicate_paper_ids = 2` | Làm loãng Vector Search Top-k | Run Deduplication logic |

---

## 10. Bảng So sánh 3 Trạng thái (Baseline vs Corrupted vs Repaired)

| Metric / Observability Signal | Baseline (Clean) | Corrupted State | Repaired State | Delta (Corrupted vs Base) | Recovery Delta (Repaired vs Corrupted) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Retrieval Hit Rate** | **1.0000** | **0.8667** | **1.0000** | `-0.1333` | `+0.1333` |
| **Mean Token F1** | **0.7547** | **0.6221** | **0.7547** | `-0.1326` | `+0.1326` |
| **LLM Judge Accuracy** | **0.6889** | **0.5778** | **0.6889** | `-0.1111` | `+0.1111` |
| **Mean Judge Score (1-5)** | **3.71** | **3.27** | **3.71** | `-0.44` | `+0.44` |
| **Quality Check Status** | `HEALTHY` | `UNHEALTHY` | `HEALTHY` | Anomaly Detected | Fully Restored |
| **Freshness Status** | `FRESH` | `STALE` | `FRESH` | Stale Alert | Fully Restored |

---

## 11. Hai Kết luận Nhân quả Quan trọng

1. **Mối quan hệ Dữ liệu hỏng -> Tín hiệu giám sát -> Chất lượng RAG:**
   Khi dữ liệu bị hỏng (Blank Summary, Noise, Duplicate), hệ thống Data Observability lập tức phát hiện anomalies (`empty_summaries=2`, `duplicate_paper_ids=2`). Tương ứng, chất lượng RAG giảm sút rõ rệt: **Retrieval Hit Rate giảm từ 100% xuống 86.67%**, **Token F1 giảm từ 0.7547 xuống 0.6221**.
2. **Mối quan hệ Phục hồi Dữ liệu -> Tín hiệu giám sát -> Phục hồi RAG:**
   Khi thực hiện Data Repair từ Raw Snapshot (`crossref_records.json`), tất cả các quy tắc cleaning và deduplication được áp dụng lại hoàn chỉnh. Tín hiệu Data Quality trở lại trạng thái `HEALTHY` và **Retrieval Hit Rate phục hồi hoàn toàn về 1.0000 (100%)**.

---

## 12. Checklist Hoàn thành Bài nộp

- [x] Đã hoàn thành 100% code trong `src/` không còn `TODO(student)`.
- [x] Đã sinh đầy đủ artifacts trong `data/raw/`, `data/clean/`, `data/eval/`, `data/results/`, `data/quality/`, `data/reports/`.
- [x] Đã chạy lặp lại thành công cả Phase 1 và Phase 2.
- [x] Báo cáo nhóm `group_report.md` và Báo cáo cá nhân `individual_report.md` đầy đủ số liệu thực tế.
