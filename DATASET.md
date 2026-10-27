# Bộ dữ liệu JD IT Việt Nam

Tin tuyển dụng (JD) ngành CNTT tại Việt Nam, crawl ngày **24/10/2026** để dùng cho môn Trực quan dữ liệu. Bộ dữ liệu có **3 lớp**, từ thô đến sẵn sàng phân tích:

| Lớp | File | Mô tả |
|---|---|---|
| 1. Thô | `data/all_jobs.jsonl`, `data/all_jobs.csv` | 40 cột, giá trị giữ nguyên như nguồn hiển thị, chưa làm sạch, chưa khử trùng lặp |
| 2. Trích cột thống kê | `data/jobs_stats.csv` | 17 cột có giá trị thống kê, vẫn là giá trị thô |
| 3. Chuẩn hoá | `data/jobs_clean.csv` | 24 cột, lương quy về VND/tháng, min/max → trung bình, địa điểm/cấp bậc/ngày được gom về dạng chuẩn |

Biểu đồ và phân tích dùng lớp 3 (xem `notebook/main.ipynb`).

## 1. Nguồn và phạm vi

| Nguồn | Số JD | Phạm vi | Cách lấy |
|---|---|---|---|
| ITviec | 607 | Toàn bộ job trong sitemap/listing của site (đều là IT) | HTML chi tiết + JSON-LD `JobPosting` |
| VietnamWorks | 756 | Nhóm ngành "Information Technology/Telecommunications" (API báo 757) | API tìm kiếm công khai, 1 object JSON/job |
| CareerViet | 665 | Danh mục "CNTT - Phần mềm" và "CNTT - Phần cứng / Mạng" | HTML chi tiết + JSON-LD |
| TopCV | 0 | Chưa có | Bị Cloudflare chặn |
| Glints | 0 | Chưa có | Bị Cloudflare chặn |
| **Tổng** | **2028** | | |

Mỗi cặp (`source`, `job_id`) là duy nhất (2028/2028). Cùng một tin có thể xuất hiện ở nhiều trang vì chưa khử trùng lặp liên trang.

Giới hạn cần biết:
- Đây là ảnh chụp các tin **đang tuyển** tại ngày crawl; tin đã hết hạn thường không còn trên site.
- Ngày đăng trải từ 08/09/2026 (ITviec) và 24/09/2026 (VietnamWorks, CareerViet) đến 24/10/2026, nên không dùng được cho phân tích xu hướng dài hạn.
- Chỉ có 3 trong 5 nguồn dự kiến; so sánh giữa các trang chỉ phản ánh 3 trang này.
- Phạm vi "IT" mỗi trang tự định nghĩa khác nhau (VietnamWorks và CareerViet có thể chứa vị trí gần CNTT như viễn thông).
- Chỉ khoảng 28% job (571/2028) ghi mức lương cụ thể; còn lại là lương thoả thuận. Phân tích lương chỉ đại diện cho nhóm có ghi lương.

## 2. Các file

```
data/
  all_jobs.jsonl        # lớp 1: 2028 dòng, gộp 3 nguồn, đủ cả jsonld/extra
  all_jobs.csv          # lớp 1: cùng nội dung, UTF-8 có BOM (mở được bằng Excel)
  jobs_stats.csv        # lớp 2: 17 cột thống kê (giá trị thô)
  jobs_clean.csv        # lớp 3: 24 cột đã chuẩn hoá
  <nguồn>/jobs.jsonl    # dữ liệu theo từng trang
  <nguồn>/urls.jsonl    # URL job đã phát hiện
  <nguồn>/errors.jsonl  # lỗi khi tải (hiện không có)
  <nguồn>/_stats.json   # thống kê lần crawl
  <nguồn>/raw/          # HTML (ITviec, CareerViet) hoặc JSON (VietnamWorks) gốc của từng job
notebook/main.ipynb     # phân tích và biểu đồ (đọc jobs_clean.csv)
crawlers/               # mã crawl, gộp, xuất CSV và chuẩn hoá
```

Quy ước trong CSV: trường dạng danh sách (`category`, `skills`, `benefits`) nối bằng ` | `; `jsonld` và `extra` là chuỗi JSON; giá trị thiếu là ô rỗng (trong JSONL là `null`).

## 3. Lớp 1: schema thô (40 cột, giống nhau cho mọi nguồn)

| Cột | Ý nghĩa |
|---|---|
| `source` | `itviec` / `vietnamworks` / `careerviet` |
| `job_id` | ID gốc của trang (ITviec: 4+ chữ số; VietnamWorks: số; CareerViet: mã hex 8 ký tự) |
| `url` | Link chi tiết |
| `title` | Tên vị trí |
| `company_name`, `company_url`, `company_size`, `company_industry`, `company_address` | Thông tin công ty |
| `salary_text` | Lương, nguyên văn hoặc JSON (xem mục 5) |
| `location_text`, `work_address` | Địa điểm làm việc |
| `work_model`, `job_type`, `level` | Hình thức làm việc, loại hợp đồng, cấp bậc |
| `experience_text`, `education_text`, `gender_text`, `language_text`, `headcount_text` | Yêu cầu ứng viên và số lượng tuyển |
| `category` | Ngành nghề do site gán (danh sách) |
| `skills` | Kỹ năng/công nghệ do site gán (danh sách) |
| `benefits`, `benefits_text` | Phúc lợi dạng tag / dạng đoạn văn |
| `description_text`, `requirements_text` | Mô tả công việc, yêu cầu |
| `full_text` | Toàn bộ nội dung JD (phòng khi tách mục chưa chính xác) |
| `posted_at_text`, `posted_at` | Ngày đăng dạng chữ / dạng ISO |
| `expires_at_text`, `expires_at` | Hạn nộp dạng chữ / dạng ISO |
| `status` | Luôn `active` ở lần crawl này |
| `view_count_text` | Lượt xem (chưa nguồn nào có) |
| `jsonld` | Khối JSON-LD `JobPosting` gốc (ITviec, CareerViet) |
| `extra` | Trường riêng của từng nguồn (xem mục 5) |
| `raw_path` | Đường dẫn tới file gốc trong `data/` |
| `listing_url` | Trang listing/sitemap nơi phát hiện job |
| `crawled_at`, `crawler_version` | Thời điểm crawl (UTC) và phiên bản parser |

## 4. Mức độ đầy đủ của lớp 1

Số bản ghi có giá trị (không rỗng):

| Trường | ITviec (607) | VietnamWorks (756) | CareerViet (665) |
|---|---|---|---|
| `title`, `company_name` | 607 | 756 | 665 |
| `salary_text` | 606 | 756 | 665 |
| `location_text` | 606 | 756 | 4 |
| `work_address` | 0 | 625 | 665 |
| `level` | 0 | 756 | 652 |
| `experience_text` | 0 | 756 | 599 |
| `skills` | 606 | 756 | 532 |
| `category` | 606 | 756 | 652 |
| `description_text` | 581 | 756 | 665 |
| `requirements_text` | 580 | 756 | 0 |
| `benefits` (tag) | 0 | 756 | 0 |
| `benefits_text` | 592 | 0 | 617 |
| `company_size` | 0 | 337 | 0 |
| `posted_at`, `expires_at` | 606 | 756 | 665 |

Các ô trống thường do nguồn không có trường đó hoặc cấu trúc trang khác nhau, không phải lỗi tải. Một job ITviec không có JSON-LD nên thiếu hầu hết trường có cấu trúc, nhưng vẫn có `title` và `full_text`.

## 5. Lưu ý khi dùng lớp 1 và 2 (chưa chuẩn hoá)

- **Lương (`salary_text`)** có nhiều dạng: chuỗi nguyên văn ("Tới $ 2,000 /tháng", "Thương lượng", "Cạnh tranh") ở VietnamWorks và một phần CareerViet; **chuỗi JSON `MonetaryAmount`** ở ITviec và một phần CareerViet. Nhiều giá trị chỉ là nhãn như "Very Attractive!!!", "Cạnh tranh", tiền tệ có thể là mã lạ (ví dụ `LTT`).
- **Số liệu VietnamWorks:** `job_type`, `education_text` là **mã số** của site (ví dụ `1`), `experience_text` là số năm; chi tiết lương số (`salary`, `salaryMin`, `salaryMax`, `salaryCurrency`) nằm trong `extra`.
- **Địa điểm:** ITviec lưu JSON `jobLocation` trong `location_text`; VietnamWorks lưu tên thành phố; CareerViet lưu JSON `jobLocation` trong `work_address` (có `addressLocality`, `addressRegion`, toạ độ), còn `location_text` gần như trống.
- **Định dạng ngày:** ITviec dùng `YYYY-MM-DD`, VietnamWorks dùng ISO có múi giờ `+07:00`, CareerViet dùng ISO UTC (`Z`). `expires_at_text` của CareerViet là `dd/mm/yyyy`.
- **Ngôn ngữ:** lẫn tiếng Việt và tiếng Anh.
- **Nội dung HTML:** `description_text` và `requirements_text` đã bỏ thẻ HTML nhưng chưa làm sạch ký tự/dòng trống.
- **`extra` theo nguồn:** ITviec chứa `sections` (các mục theo tiêu đề h2) và `header_text`; VietnamWorks chứa `companyId`, `industriesV3`, `jobFunction`, `workingLocations`, các trường lương số…; CareerViet chứa `info_box` (khung thông tin trên trang).
- **Dữ liệu cá nhân:** có thể xuất hiện tên người liên hệ HR (`contactName` trong `extra` của VietnamWorks). Nên bỏ trường này khi công bố.

## 6. Lớp 2: `data/jobs_stats.csv`

17 cột lấy nguyên giá trị từ lớp 1: `source`, `job_id`, `title`, `company_name`, `company_size`, `salary_text`, `location_text`, `work_address`, `job_type`, `level`, `experience_text`, `education_text`, `category`, `skills`, `benefits`, `posted_at`, `expires_at`. Bỏ các cột trống ở cả 3 nguồn, văn bản dài (`description_text`, `full_text`…) và cột kỹ thuật (`url`, `raw_path`, `jsonld`, `extra`…). Tạo bằng `crawlers/export_stats_csv.py`.

## 7. Lớp 3: `data/jobs_clean.csv` (đã chuẩn hoá)

Tạo bằng `crawlers/normalize.py` từ `all_jobs.jsonl`: 2028 dòng, 24 cột. Dữ liệu thô không bị sửa.

| Nhóm | Cột | Quy tắc |
|---|---|---|
| Định danh | `source`, `job_id`, `title`, `company_name` | Giữ nguyên |
| Quy mô công ty | `company_size`, `company_size_avg` | Khoảng "100-499" → trung bình 299,5; "Less Than 10" → 5; "Over 50,000" → 50.000. Chỉ VietnamWorks có (337 job) |
| Lương | `salary_type`, `salary_min_vnd`, `salary_max_vnd`, `salary_avg_vnd`, `salary_currency_orig` | Xem bên dưới |
| Địa điểm | `city`, `cities` | Thành phố đầu tiên / tất cả thành phố (nối ` \| `) |
| Phân loại | `level_std`, `job_type_std` | `Intern / Fresher / Staff / Lead / Manager / Director`; `Full-time / Part-time / Internship…` |
| Kinh nghiệm | `exp_min_years`, `exp_max_years`, `exp_avg_years` | Cùng quy tắc min/max/avg; "Chưa có kinh nghiệm" = 0 |
| Kỹ năng | `skills`, `n_skills`, `benefits` | Danh sách nối ` \| ` và số kỹ năng |
| Thời gian | `posted_date`, `expires_date`, `days_open` | `YYYY-MM-DD` giờ Việt Nam; `days_open` = hạn nộp − ngày đăng |

**Quy tắc lương**
- Quy về **VND/tháng**: lương theo năm chia 12; USD × **26.000** (tỷ giá cố định giả định, sửa hằng `USD_VND` trong `normalize.py` nếu cần).
- Khi có đủ min và max thì `salary_avg_vnd` = (min + max) / 2. Khi chỉ có một cận ("tới X", "từ X") thì avg bằng cận đó.
- `salary_type`: `range` / `up_to` / `from` / `fixed` / `negotiable`. Lương thoả thuận để trống số.
- Giá trị ngoài khoảng 1 triệu – 2 tỷ VND/tháng được coi là không hợp lệ và xếp vào `negotiable`.

| Nguồn | Có lương số | Thoả thuận |
|---|---|---|
| ITviec | 150 | 457 |
| VietnamWorks | 181 | 575 |
| CareerViet | 240 | 425 |
| **Tổng** | **571 (28%)** | 1457 |

**Lưu ý lớp 3**
- `level_std` trống ở khoảng 620 job, phần lớn là ITviec vì trang không có cấp bậc. Chưa suy ra từ tiêu đề.
- `exp_*_years` chỉ có cho VietnamWorks và CareerViet.
- Mã loại hình của VietnamWorks ngoài `1` (Full-time) chưa rõ nghĩa nên giữ dạng `unknown(vnw_code=N)`.
- `days_open` có giá trị âm (nhỏ nhất −12), có thể do tin được đăng lại; nên lọc khi phân tích.
- `city` có 6 job không xác định được. Hà Nội 1016, TP.HCM 839, Đà Nẵng 25.
- Cột học vấn không có trong lớp 3 vì VietnamWorks chỉ có mã số chưa rõ nghĩa.

## 8. Tái tạo

Chạy từ thư mục gốc dự án; mỗi crawler tiếp tục được từ chỗ dừng.

```
python crawlers/itviec.py
python crawlers/vietnamworks.py
python crawlers/careerviet.py
python -m crawlers.merge              # → all_jobs.jsonl, all_jobs.csv
python -m crawlers.export_stats_csv   # → jobs_stats.csv
python -m crawlers.normalize          # → jobs_clean.csv
```

Tốc độ crawl giữ ở mức chậm (khoảng 1 request mỗi 0,7 giây, tối đa 2 luồng). Cần Python 3.11+ và các thư viện trong `requirements.txt`.

Dữ liệu là tin tuyển dụng công khai, thu thập cho mục đích học tập. Các trang có điều khoản về việc sử dụng tự động, nên không phát tán lại bộ dữ liệu này công khai.
