# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| ------------------ | -------------------------- |
| Họ và tên | Thái Hoài An |
| MSSV | 2A202601862 |
| Khóa/Lớp | K4 |
| Tên nhóm | K4_Day10_DataObservability_Team |
| Vai trò chính | Data Observability Owner |
| Repository | DuongDucMinh/K4_Day10_Hihihaha |
| Ngày hoàn thành | 2026-08-06 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Data Quality Monitor | `src/observability/quality.py` | Clean/Corrupted/Repaired DataFrames | `data/quality/*.json` | Hoàn thành 100% |
| Data Freshness Monitor | `build_freshness_report()` | DataFrame & `freshness_threshold_days` | `data/quality/freshness_report.json` | Hoàn thành 100% |
| Executive Markdown Reports | `src/observability/reporting.py` | Summaries & Evaluation Metrics | `data/reports/phase1_report.md`, `corruption_report.md` | Hoàn thành 100% |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Quality Check Suite | `run_data_quality_checks()` | Kiểm tra null, unique paper_id, empty summary | `data/quality/baseline_quality.json` |
| Freshness Monitoring | `build_freshness_report()` | Đo `avg_age_days`, tìm `latest_published`, đếm `stale_rows` | `data/quality/freshness_report.json` |
| Tri-State Comparison Report | `generate_corruption_report()` | Báo cáo Markdown chi tiết bảng so sánh 3 pha | `data/reports/corruption_report.md` |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Xây dựng chốt chặn quan sát dữ liệu (Data Observability) để kịp thời phát hiện các hiện tượng bất thường (dữ liệu rỗng, trùng lặp, bị lỗi thời) trước khi nó ảnh hưởng tới trải nghiệm người dùng cuối, đồng thời tổng hợp các số liệu so sánh thành báo cáo Markdown trực quan.

### Cách triển khai
1. **Quality Monitoring (`quality.py`):**
   - Đếm số dòng (`total_rows`).
   - Đếm số `paper_id` bị null hoặc bị trùng lặp.
   - Đếm số `summary` bị rỗng (`empty_summaries`) hoặc quá ngắn (`short_summaries`).
   - Xác định cờ sức khỏe `is_healthy` (`True` khi nulls=0, duplicates=0, empty_summaries=0).
2. **Freshness Monitoring:**
   - Tìm ngày xuất bản mới nhất (`latest_published`) và cũ nhất (`oldest_published`).
   - Tính tuổi trung bình (`avg_age_days`).
   - Đánh giá cờ `is_fresh` dựa trên tỷ lệ dòng stale (`age_days > 180`).
3. **Automated Markdown Generator (`reporting.py`):**
   - Định dạng bảng Markdown hiển thị song song chỉ số 3 pha (`Baseline` vs `Corrupted` vs `Repaired`).
   - Tự động tính toán mức độ sụt giảm (Delta) và tỷ lệ phục hồi (Recovery Delta).

### Cách xác minh
```powershell
uv run python -c "import json; print(json.load(open('data/quality/corrupted_quality.json')))"
```
- **Kết quả thực tế:** Trạng thái `is_healthy: false`, ghi nhận đúng `duplicate_paper_ids: 2` và `empty_summaries: 2`.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn tiêu chí để gán trạng thái `is_healthy` cho đường ống dữ liệu.
- **Phương án cân nhắc:**
  1. Chỉ cảnh báo lỗi nếu toàn bộ dataframe bị rỗng.
  2. Áp dụng quy tắc ngặt nghèo: Không cho phép bất kỳ tiêu đề/paper_id rỗng, trùng lặp hoặc summary rỗng nào xuất hiện.
- **Phương án chọn:** Phương án 2 (Quy tắc ngặt nghèo).
- **Lý do:** Trong hệ thống RAG, chỉ cần 1 vài document bị rỗng summary hoặc trùng lặp tiêu đề sẽ làm nhiễu kết quả Vector Search Top-k, trực tiếp kéo tụt Retrieval Hit Rate.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Báo cáo so sánh Markdown không hiển thị đúng số liệu khi chạy pipeline lần 2.
- **Nguyên nhân gốc:** Hàm ghi file chưa đảm bảo tạo thư mục cha `data/reports/` nếu thư mục này chưa tồn tại.
- **Cách xử lý:** Sử dụng helper function `write_text` có sẵn cơ chế `ensure_parent(path)` trước khi viết file.
- **Xác minh:** File `data/reports/corruption_report.md` được sinh ra ổn định và hiển thị bảng so sánh đẹp mắt.

---

## 7. Hiểu biết về luồng end-to-end

Data Observability chính là hệ thống "báo cháy" của Data Pipeline. Nếu không có các chỉ số Quality và Freshness checks do tôi phát triển, nhóm sẽ không thể chứng minh được mối quan hệ nhân quả: *Sự cố dữ liệu làm suy giảm tín hiệu chất lượng dữ liệu, kéo theo sự sụt giảm trực tiếp của điểm số RAG Agent*.
