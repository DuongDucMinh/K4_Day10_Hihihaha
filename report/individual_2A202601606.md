# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| ------------------ | -------------------------- |
| Họ và tên | Phạm Tấn Gia Quốc |
| MSSV | 2A202601606 |
| Khóa/Lớp | K4 |
| Tên nhóm | Hihihaha |
| Vai trò chính | Source Ingestion Owner |
| Repository | DuongDucMinh/K4_Day10_Hihihaha |
| Ngày hoàn thành | 2026-08-06 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Crossref Ingestion Module | `src/ingestion/crossref.py` | Crossref REST API (`https://api.crossref.org/works`) | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Hoàn thành 100% |
| Payload Parser | `parse_crossref_payload()` | Raw JSON dictionary | Danh sách dataclass `PaperRecord` | Hoàn thành 100% |
| Snapshot Loader | `load_raw_records()` | `crossref_records.json` | Danh sách `PaperRecord` cho repair step | Hoàn thành 100% |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Gọi API & Retry Backoff | `fetch_source_records()` | Ingest thành công 24 bản ghi thô từ Crossref | `data/raw/crossref_response.json` (245 KB) |
| Parse & Normalization HTML | `parse_crossref_payload()` | Loại bỏ tag `<jats:p>`, bóc tách DOI, Title, Abstract | `data/raw/crossref_records.json` (60 KB) |
| Raw Data Preservation | `write_json()` | Lưu snapshot thô phục vụ quy trình Data Repair offline | `data/raw/crossref_records.json` |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Crossref API trả về JSON chứa các cấu trúc phức tạp, nhúng các tag HTML như `<jats:p>`, tên tác giả phân mảnh thành `given` và `family`, và ngày xuất bản dạng mảng `[year, month, day]`. Ngoài ra, API công khai dễ gặp sự cố rate limiting (HTTP status 429 hoặc 503).

### Cách triển khai
1. **Exponential Backoff Retry:** Thiết lập vòng lặp gọi `requests.get()` với `headers={"User-Agent": "DataObservabilityLab/1.0"}`. Nếu gặp mã lỗi 429, 503, 500 thì dừng `time.sleep(2 ** attempt)` trước khi thử lại (tối đa 3 lần).
2. **Loại bỏ HTML Tag:** Sử dụng biểu thức chính quy `re.sub(r"<[^>]+>", " ", text)` để làm sạch abstract và title trước khi gán vào `PaperRecord`.
3. **Parse Ngày tháng:** Bóc tách `date-parts` từ các trường `published-online`, `published-print` hoặc `created` để định dạng chuẩn `YYYY-MM-DD`.

### Cách xác minh
```powershell
uv run python -c "from ingestion.crossref import load_raw_records; records = load_raw_records('data/raw/crossref_records.json'); print(len(records), records[0].title)"
```
- **Kết quả thực tế:** Trả về đúng 24 records, tiêu đề được làm sạch hoàn toàn tag HTML.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương án lưu trữ dữ liệu thô (Raw Data Artifacts).
- **Phương án cân nhắc:**
  1. Chỉ lưu duy nhất file CSV đã làm sạch để tiết kiệm bộ nhớ.
  2. Lưu cả response JSON gốc (`crossref_response.json`) và bản ghi thô dạng JSON (`crossref_records.json`).
- **Phương án chọn:** Phương án 2.
- **Lý do:** Lưu Raw Snapshot cho phép quy trình Data Repair có thể phục hồi pipeline 100% offline mà không cần gọi lại API bên ngoài, đảm bảo tính tái hiện (reproducibility) và giảm rủi ro nới rộng thời gian làm lab do API rate limit.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** `requests.exceptions.MissingSchema: Invalid URL 'Crossref REST API'`.
- **Nguyên nhân gốc:** `settings.source_api` trong `config.py` đặt giá trị chuỗi mô tả `"Crossref REST API"` thay vì URL `https://...`.
- **Cách xử lý:** Cập nhật hàm `fetch_source_records`:
  ```python
  url = settings.source_api if settings.source_api.startswith("http") else "https://api.crossref.org/works"
  ```
- **Xác minh:** Lệnh `fetch_source_records(settings)` chạy thành công và kéo 24 bản ghi về máy.

---

## 7. Hiểu biết về luồng end-to-end

Lớp Ingestion đóng vai trò là "cổng vào" của toàn bộ Data Pipeline. Nếu dữ liệu thô ở bước này không được lưu vết snapshot cẩn thận, khi xảy ra Data Corruption ở các bước sau, hệ thống sẽ không có mốc đối chứng chuẩn để thực hiện khôi phục (Data Repair).
