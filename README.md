# vn-it-job-crawler

Crawl tin tuyển dụng (JD) ngành CNTT tại Việt Nam từ ITviec, VietnamWorks và CareerViet, sau đó gộp, chuẩn hoá và phân tích. Dự án dùng cho môn Trực quan dữ liệu; dữ liệu crawl ngày **24/10/2026**.

| Nguồn | Số JD | Cách lấy |
|---|---|---|
| ITviec | 607 | sitemap + listing, HTML chi tiết + JSON-LD |
| VietnamWorks | 756 | API tìm kiếm công khai (JSON) |
| CareerViet | 665 | listing theo danh mục CNTT + HTML chi tiết |
| TopCV, Glints | 0 | bị Cloudflare chặn, chưa làm |

## Cấu trúc

```
common/core.py     # HTTP client có rate limit, lưu JSONL có resume, schema chung
crawlers/          # itviec.py, vietnamworks.py, careerviet.py, merge.py,
                   # export_stats_csv.py, normalize.py, reparse_careerviet.py
notebook/main.ipynb# phân tích và biểu đồ (đọc data/jobs_clean.csv)
data/              # jobs_stats.csv, jobs_clean.csv được commit; phần còn lại sinh ra khi crawl
DATASET.md         # mô tả chi tiết bộ dữ liệu và các lưu ý
PLAN.md            # kế hoạch crawl ban đầu
```

## Cài đặt

Cần Python 3.11+.

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows; Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

Muốn chạy notebook, cài thêm `pandas matplotlib numpy jupyter`.

## Chạy

Chạy từ thư mục gốc của repo. Tham số số nguyên tuỳ chọn giới hạn số job (để chạy thử).

```bash
python -m crawlers.itviec [N]
python -m crawlers.vietnamworks [N]
python -m crawlers.careerviet [N]

python -m crawlers.merge              # gộp -> data/all_jobs.jsonl, data/all_jobs.csv
python -m crawlers.export_stats_csv   # -> data/jobs_stats.csv
python -m crawlers.normalize          # -> data/jobs_clean.csv
```

Crawler lưu HTML/JSON gốc vào `data/<nguồn>/raw/` và có thể chạy lại (bỏ qua ID đã có).

## Dữ liệu

Bộ dữ liệu có 3 lớp (thô → thống kê → chuẩn hoá); xem [DATASET.md](DATASET.md). Repo chỉ chứa lớp 2 và 3 (`data/jobs_stats.csv`, `data/jobs_clean.csv`). Lớp thô và HTML gốc (~1.2 GB, có nội dung JD đầy đủ và tên người liên hệ) không được đưa lên git; chạy lại crawler để tạo.

## Lưu ý

- Chỉ lấy tin tuyển dụng công khai, tốc độ thấp, không đăng nhập. Các trang có điều khoản hạn chế bot; dữ liệu chỉ dùng học tập, không phát tán lại.
- Dữ liệu là ảnh chụp các tin đang tuyển tại ngày crawl, không dùng được cho xu hướng dài hạn.
- Mã nguồn theo giấy phép MIT. Giấy phép này không áp dụng cho nội dung JD thuộc về các trang nguồn và nhà tuyển dụng.
