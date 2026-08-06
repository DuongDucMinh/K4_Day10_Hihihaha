# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| ------------------ | -------------------------- |
| Họ và tên | Dương Đức Minh |
| MSSV | 2A202601306 |
| Khóa/Lớp | K4 |
| Tên nhóm | Hihihaha |
| Vai trò chính | Data Model & Eval Set Owner |
| Repository | DuongDucMinh/K4_Day10_Hihihaha |
| Ngày hoàn thành | 2026-08-06 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Data Cleaning & Modeling | `src/ingestion/cleaning.py` | Danh sách `PaperRecord` từ Ingestion | `data/clean/papers_clean.csv`, `papers_clean.json` | Hoàn thành 100% |
| Evaluation Test Set Generator | `src/evaluation/testset.py` | Cleaned Pandas DataFrame | `data/eval/test_set.json` (45 QA pairs) | Hoàn thành 100% |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Clean & Construct Embedding Text | `build_clean_dataframe()` | 24 clean records, 0 null title, 0 dupes | `data/clean/papers_clean.csv` (101 KB) |
| Feature Engineering & Freshness | `build_clean_dataframe()` | Tính `age_days`, `summary_chars`, `authors_joined` | `data/clean/papers_clean.csv` |
| Evaluation Test Set Freezing | `build_test_set()` | Sinh bộ 45 câu hỏi test set thuộc 4 nhóm type | `data/eval/test_set.json` (47.8 KB) |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. Chuyển đổi dữ liệu thô từ Crossref thành một DataFrame chuẩn hóa sẵn sàng cho nhúng Vector DB (`text_for_embedding`).
2. Sinh bộ câu hỏi đánh giá (Evaluation Test Set) phong phú và cố định (frozen testset) để đo lường công bằng 3 trạng thái của pipeline.

### Cách triển khai
1. **Cleaning Logic (`cleaning.py`):**
   - Loại bỏ khoảng trắng thừa với `normalize_whitespace`.
   - Tính toán `age_days = (run_date - published_date).days`.
   - Tạo cột `text_for_embedding` kết hợp giữa `Title`, `Authors`, `Categories`, `Published`, và `Summary`.
   - Áp dụng loại bỏ trùng lặp tiêu đề và DOI: `df.drop_duplicates(subset=["paper_id"])` và `df.drop_duplicates(subset=["title"])`.
2. **Test Set Building (`testset.py`):**
   - Duyệt qua các bài báo tiêu biểu trong cleaned dataframe.
   - Sinh tự động 4 loại câu hỏi: `summary`, `authors`, `date`, và `categories`.
   - Lưu trữ danh sách JSON với đầy đủ cấu trúc: `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`.

### Cách xác minh
```powershell
uv run python -c "import json; data = json.load(open('data/eval/test_set.json')); print('Total questions:', len(data))"
```
- **Kết quả thực tế:** Trả về đúng 45 câu hỏi test set đa dạng.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn chiến lược quản lý bộ câu hỏi test set (Evaluation Set).
- **Phương án cân nhắc:**
  1. Mỗi lần đánh giá pipeline lại tự động sinh lại test set mới.
  2. Sinh test set 1 lần ở Baseline Phase và **đóng băng (freeze)** cố định tại `data/eval/test_set.json` dùng chung cho 3 pha.
- **Phương án chọn:** Phương án 2 (Cố định Test Set).
- **Lý do:** Đây là nguyên tắc cốt lõi của RAG Evaluation. Để đo lường chính xác tác động của Data Corruption và phục hồi của Data Repair, bộ câu hỏi và đáp án chuẩn phải hoàn toàn không đổi.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Dữ liệu sau cleaning chứa một số dòng có `authors_joined` bị rỗng hoặc lỗi định dạng danh sách.
- **Nguyên nhân gốc:** Tác giả từ Crossref API đôi khi là danh sách dicts thiếu `given` name.
- **Cách xử lý:** Viết helper function `_join_list` xử lý an toàn:
  ```python
  def _join_list(val: Any) -> str:
      if isinstance(val, list):
          return compact_join(val, sep=", ")
      return str(val or "")
  ```
- **Xác minh:** Kiểm tra `papers_clean.csv`, tất cả cột `authors_joined` đều là chuỗi phân tách bởi dấu phẩy đẹp mắt.

---

## 7. Hiểu biết về luồng end-to-end

Cleaning là chiếc cầu nối biến dữ liệu thô rác thành tri thức có cấu trúc cho Vector Store. Cùng với việc đóng băng Test Set, phần việc của tôi đảm bảo hệ thống có được thước đo chuẩn xác (ground truth) để phát hiện sự cố hỏng dữ liệu và chứng minh sự phục hồi của RAG Agent.
