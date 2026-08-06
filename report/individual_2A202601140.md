# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| ------------------ | -------------------------- |
| Họ và tên | Nguyễn Thanh Tùng |
| MSSV | 2A202601140 |
| Khóa/Lớp | K4 |
| Tên nhóm | Hihihaha |
| Vai trò chính | Corruption & Integration Owner |
| Repository | DuongDucMinh/K4_Day10_Hihihaha |
| Ngày hoàn thành | 2026-08-06 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Data Corruption Simulator | `src/ingestion/corruption.py` | Cleaned Pandas DataFrame | `data/clean/papers_clean_corrupted.csv`, `corruption_log.json` | Hoàn thành 100% |
| Baseline Pipeline Orchestration | `src/pipelines/phase1.py` | Config & Modules Ingestion/Eval | `script/run_phase1.py` entrypoint | Hoàn thành 100% |
| Corruption & Repair Flow Pipeline | `src/pipelines/corruption_flow.py` | Baseline artifacts & Raw Snapshot | `script/run_corruption_flow.py` entrypoint | Hoàn thành 100% |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Corrupt Clean DataFrame | `corrupt_clean_dataframe()` | Mô phỏng 5 kịch bản hỏng dữ liệu thực tế | `data/results/corruption_log.json` |
| End-to-End Baseline Flow | `phase1.py` | Hit Rate = 1.0000, F1 = 0.7547 | `data/results/baseline_metrics.json` |
| Tri-State Corruption & Repair Flow | `corruption_flow.py` | Đo lường sụt giảm (0.8667) và khôi phục (1.0000) | `data/results/corrupted_metrics.json`, `repaired_metrics.json` |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. Thiết kế các kịch bản hỏng dữ liệu (Data Corruption) thực tế có kiểm soát để chứng minh ảnh hưởng trực tiếp tới chất lượng RAG.
2. Tích hợp tất cả các module rời rạc (`ingestion`, `cleaning`, `index`, `evaluation`, `observability`) thành 2 đường ống pipeline hoàn chỉnh có thể chạy bằng 1 lệnh duy nhất.

### Cách triển khai
1. **Corruption Scenarios (`corruption.py`):**
   - **Xóa bản ghi mới nhất:** Drop 2 dòng đầu tiên (simulate thiếu bài báo mới).
   - **Xóa Summary:** Xóa rỗng `summary` ở 2 dòng (simulate mất dữ liệu abstract).
   - **Chèn Noise & Truncate:** Truncate tiêu đề bài báo và chèn chuỗi nhiễu `[CORRUPTED_NOISE]`.
   - **Làm Stale Date:** Sửa ngày xuất bản thành `2000-01-01` (tuổi 9000 ngày).
   - **Tạo Duplicate Rows:** Nhân bản 2 dòng dữ liệu.
   - Tái cấu trúc lại `text_for_embedding` và ghi nhật ký vào `corruption_log.json`.
2. **Pipeline Integration (`phase1.py` & `corruption_flow.py`):**
   - **Pha 1:** Kéo/Load dữ liệu thô -> Clean -> Index ChromaDB -> Sinh TestSet -> Đánh giá Baseline -> Kiểm tra Observability -> Sinh Phase 1 Report.
   - **Pha 2:** Corrupt Data -> Re-index & Re-evaluate Corrupted -> Repair từ Raw Snapshot -> Re-clean & Re-index -> Re-evaluate Repaired -> Sinh Comparison Report.

### Cách xác minh
```powershell
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```
- **Kết quả thực tế:** Cả 2 script chạy thành công 100%, tự động sinh toàn bộ artifacts trong `data/`.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp Data Repair (Phục hồi dữ liệu).
- **Phương án cân nhắc:**
  1. Chỉ dùng hàm sửa chuỗi thủ công để thay thế lại các dòng bị lỗi.
  2. Phục hồi bài bản bằng cách load lại danh sách `PaperRecord` từ **Raw Records Snapshot (`crossref_records.json`)** và chạy lại qua quy tắc `build_clean_dataframe()`.
- **Phương án chọn:** Phương án 2 (Repair từ Raw Snapshot).
- **Lý do:** Đây là chuẩn mực Data Engineering. Phục hồi dữ liệu từ nguồn thô đáng tin cậy giúp hệ thống khôi phục triệt để mọi trường bị corrupt, đồng thời chứng minh tầm quan trọng của việc lưu trữ Raw Artifacts.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** `ModuleNotFoundError: No module named 'pipelines'` khi chạy script.
- **Nguyên nhân gốc:** Gói package chưa được cài đặt ở chế độ editable trong môi trường ảo `.venv`.
- **Cách xử lý:** Chạy lệnh `uv pip install -e .` để cài đặt thư mục `src/` thành một python package nội bộ.
- **Xác minh:** Lệnh `uv run python script/run_phase1.py` nhận diện đúng tất cả các module và chạy mượt mà.

---

## 7. Hiểu biết về luồng end-to-end

Vai trò Integration đòi hỏi cái nhìn toàn cảnh về bức tranh dữ liệu. Việc thực thi thành công chu trình: *Clean (Baseline) -> Corrupt -> Repair -> Compare* trên cùng một bộ câu hỏi đánh giá cố định đã chứng minh hoàn toàn khẳng định: Chất lượng dữ liệu ở đầu vào quyết định trực tiếp chất lượng đầu ra của hệ thống RAG Agent.
