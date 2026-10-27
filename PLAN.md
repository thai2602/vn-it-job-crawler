# Kế hoạch crawl JD IT Việt Nam (5 nguồn)

Mục đích: dữ liệu thô phục vụ môn Trực quan dữ liệu. **Không làm sạch / chuẩn hoá** ở giai đoạn crawl.

## 1. Kết quả thăm dò (24/10/2026, curl + UA trình duyệt)

| Site | Listing | Sitemap/robots | Ghi chú |
|---|---|---|---|
| itviec.com | 200, HTML SSR (~540KB), link `/it-jobs/<slug>-<4 số>` | robots trỏ `https://itviec.com/dunggiatminh.xml`; `/sitemap.xml` 404 | Chỉ toàn job IT. Có Cloudflare, có thể bị chặn khi tăng tốc |
| topcv.vn | **403** (Cloudflare challenge) | `/sitemap.xml` 403 | Cần trình duyệt thật (Playwright, headful) hoặc cookie `cf_clearance` |
| vietnamworks.com | 200, Next.js (`__NEXT_DATA__`) | `https://www.vietnamworks.com/sitemap/sitemap.xml` | Nên dùng API JSON nội bộ mà frontend gọi (xác nhận bằng DevTools) |
| glints.com/vn | **403** (Cloudflare) | `sitemap_index.xml`, `sitemaps/explore-page-id-sitemap.xml` | Next.js; có API JSON; cần browser để lấy cookie |
| careerviet.vn | 200, HTML SSR (~2MB) | robots rỗng, sitemap 404 | Listing phân trang `trang-N`, category CNTT-Phần mềm `c1` (và CNTT-Phần cứng/Mạng) |

Môi trường: máy chưa có Python (chỉ có shortcut Microsoft Store) → cần cài Python 3.11+ trước khi code.

## 2. Công nghệ & kiến trúc chung

- Python 3.11+, `httpx` (site không chặn), `playwright` (topcv, glints, fallback), `selectolax`/`parsel` để parse, `tenacity` retry.
- **Hai pha cho mỗi site**:
  1. *Discovery*: thu thập toàn bộ URL/ID job → `data/<site>/urls.jsonl` (id, url, listing_page, discovered_at).
  2. *Detail fetch*: tải từng job, **lưu raw HTML/JSON gốc** vào `data/<site>/raw/<job_id>.html|json` + ghi 1 dòng vào `data/<site>/jobs.jsonl` theo schema bên dưới.
- Resume được: bỏ qua ID đã có trong `jobs.jsonl`; lưu checkpoint.
- Lịch sự: 1 req/1–2s/site, concurrency ≤ 2, retry backoff với 429/5xx, dừng hẳn khi gặp captcha liên tục.
- Giữ raw HTML để nếu parse sai có thể parse lại mà không cần crawl lại.
- Chạy được lặp (re-run) để lấy bản snapshot mới; mỗi dòng có `crawled_at`.
- Chỉ lấy tin tuyển dụng công khai; không đăng nhập, không lấy thông tin cá nhân (email/SĐT người đăng nếu có thì bỏ qua).

> Lưu ý pháp lý: các site đều có điều khoản cấm bot ở mức độ khác nhau; dữ liệu chỉ dùng học tập, không phát tán lại. Việc vượt Cloudflare (topcv, glints) là rủi ro bị khoá IP — dùng tốc độ chậm.

## 3. Phạm vi "toàn bộ JD IT"

- **itviec**: toàn bộ job trong site (đều là IT). Duyệt `/it-jobs?page=N` đến khi hết, bổ sung theo kỹ năng/thành phố (`/it-jobs/<skill>/<city>`) để bù job bị giới hạn phân trang.
- **topcv**: danh mục CNTT `tim-viec-lam-cong-nghe-thong-tin-cr257` + từng nhóm con (Phần mềm, Phần cứng, Mạng, AI/Data...); chia nhỏ theo tỉnh/thành để vượt giới hạn số trang.
- **vietnamworks**: ngành IT Software (`i35`) + IT Hardware/Networking + IT khác; ưu tiên API search phân trang; bổ sung bằng sitemap.
- **glints**: `keyword`/category Technology + Software/Data/Design... với `country=VN`; ưu tiên API; sitemap `explore-page-id`.
- **careerviet**: categories CNTT-Phần mềm (`c1`), CNTT-Phần cứng/Mạng; duyệt `trang-N` đến hết; chia theo địa điểm nếu bị giới hạn.
- Mọi site: nếu một query bị giới hạn số trang → **chia nhỏ query** (theo thành phố, kỹ năng, cấp bậc) rồi dedup theo `job_id`.
- Job hết hạn: lưu `status` nếu trang còn tồn tại; không cố khôi phục.

## 4. Kế hoạch theo từng site

### 4.1 ITviec (làm đầu tiên, dễ nhất)
1. Discovery: `GET /it-jobs?page=N` (lặp tới khi không có card mới) + các URL theo skill/city. Regex slug `/it-jobs/<slug>-<id4+>`; `job_id` = số cuối slug.
2. Detail: `GET /it-jobs/<slug>`; parse từ HTML (kèm JSON-LD `JobPosting` nếu có: title, datePosted, validThrough, baseSalary, hiringOrganization).
3. Lương trên ITviec thường bị ẩn khi chưa đăng nhập ("Sign in to view salary") → lưu nguyên chuỗi.
4. Rủi ro: Cloudflare/429 → giảm tốc; fallback Playwright.

### 4.2 CareerViet
1. Discovery: `https://careerviet.vn/viec-lam/cntt-phan-mem-c1-vi.html` và trang `trang-N`; đọc "Tìm thấy N việc làm" để đối chiếu tổng.
2. Detail: link dạng `careerviet.vn/vi/tim-viec-lam/<slug>.<id>.html`; HTML SSR, có JSON-LD.
3. Trang nặng (2MB) nhưng không chặn → dễ.

### 4.3 VietnamWorks
1. Mở DevTools xác nhận endpoint search JSON (hiện frontend Next.js gọi API nội bộ); nếu POST search phân trang được → dùng thẳng, lưu JSON nguyên bản (đã có gần đủ trường).
2. Fallback: duyệt sitemap `sitemap/sitemap.xml` lấy URL job, fetch HTML và đọc `__NEXT_DATA__`.
3. Chia query theo `jobFunction`/`industry`/địa điểm vì API thường giới hạn tổng số kết quả.

### 4.4 TopCV
1. Bị 403 → dùng Playwright (headful, profile bền vững), vượt challenge một lần rồi tái sử dụng cookie cho `httpx` nếu chạy được.
2. Discovery: `/tim-viec-lam-cong-nghe-thong-tin-cr257?page=N` (+ chia theo tỉnh/thành). Link job dạng `/viec-lam/<slug>/<id>.html`.
3. Detail: parse HTML; lương/địa điểm/kinh nghiệm nằm ở khối thông tin chung.
4. Rủi ro cao nhất (anti-bot, giới hạn trang). Chậm hơn: 3–5s/req.

### 4.5 Glints
1. 403 với curl → Playwright để lấy cookie; quan sát request XHR/`_next/data` tới API job (`/api/...`) trong DevTools.
2. Discovery: API search `country=VN` + category/keyword IT, phân trang; hoặc sitemap `explore-page-id-sitemap.xml`.
3. Detail: JSON của job (đã có cấu trúc: skills, salaries, company) → lưu raw JSON.
4. Nhiều job Glints là thực tập/part-time và bằng tiếng Anh – giữ nguyên.

## 5. Thứ tự thực hiện

1. Cài Python + thư viện, dựng khung chung (`common/` : http client, rate limiter, storage JSONL, resume).
2. ITviec → CareerViet → VietnamWorks (không cần vượt bot).
3. TopCV → Glints (cần Playwright).
4. Chạy full, đối chiếu số job thu được với tổng hiển thị trên site, ghi `data/<site>/_stats.json` (số URL, số fetch OK, số lỗi).
5. Gộp 5 file JSONL → `data/all_jobs.jsonl` (chỉ concat, không biến đổi giá trị).

## 6. Schema

**Nguyên tắc:** mọi giá trị là chuỗi/mảng đúng như site hiển thị (thô). Trường không có → `null`. Mỗi site ghi cùng một bộ cột để gộp dễ; phần đặc thù nằm trong `extra` và nguyên bản trong `raw_*`.

### 6.1 Schema chung (`jobs.jsonl`, 1 dòng = 1 job)

| Trường | Kiểu | Mô tả |
|---|---|---|
| `source` | string | `itviec` \| `topcv` \| `vietnamworks` \| `glints` \| `careerviet` |
| `job_id` | string | ID gốc của site |
| `url` | string | URL chi tiết |
| `title` | string | Tên vị trí |
| `company_name` | string | Tên công ty |
| `company_url` | string\|null | Link trang công ty |
| `company_size` | string\|null | Quy mô, nguyên văn |
| `company_industry` | string\|null | Lĩnh vực công ty |
| `company_address` | string\|null | Địa chỉ công ty |
| `salary_text` | string\|null | Lương nguyên văn ("Up to $3000", "15 - 25 triệu", "Thoả thuận") |
| `location_text` | string\|null | Địa điểm làm việc nguyên văn |
| `work_address` | string\|null | Địa chỉ chi tiết nếu có |
| `work_model` | string\|null | Tại văn phòng/Hybrid/Remote (nguyên văn) |
| `job_type` | string\|null | Full-time/Part-time/Intern/... |
| `level` | string\|null | Cấp bậc (Fresher, Junior, Senior, Manager…) |
| `experience_text` | string\|null | Yêu cầu kinh nghiệm nguyên văn |
| `education_text` | string\|null | Học vấn |
| `category` | string[] | Ngành/nhóm nghề do site gán |
| `skills` | string[] | Tag kỹ năng/công nghệ do site gán |
| `benefits` | string[] | Phúc lợi dạng tag/danh sách |
| `description_text` | string\|null | Mô tả công việc (text thô) |
| `requirements_text` | string\|null | Yêu cầu ứng viên |
| `benefits_text` | string\|null | Quyền lợi (đoạn văn) |
| `full_text` | string | Toàn bộ nội dung chính của JD (phòng khi tách mục sai) |
| `headcount_text` | string\|null | Số lượng tuyển |
| `gender_text` | string\|null | Giới tính yêu cầu |
| `language_text` | string\|null | Ngôn ngữ/ngoại ngữ |
| `posted_at_text` | string\|null | Ngày đăng nguyên văn ("Đăng 3 ngày trước") |
| `posted_at` | string\|null | ISO nếu site cung cấp (JSON-LD `datePosted`) |
| `expires_at_text` | string\|null | Hạn nộp nguyên văn |
| `expires_at` | string\|null | ISO nếu có (`validThrough`) |
| `status` | string | `active` \| `expired` \| `not_found` |
| `view_count_text` | string\|null | Lượt xem / số ứng viên nếu hiển thị |
| `jsonld` | object\|null | Khối JSON-LD `JobPosting` nguyên bản |
| `extra` | object | Trường đặc thù site không khớp ở trên |
| `raw_path` | string | Đường dẫn file raw HTML/JSON đã lưu |
| `listing_url` | string | Trang listing nơi phát hiện job |
| `crawled_at` | string | Thời điểm crawl (ISO 8601, UTC) |
| `crawler_version` | string | Phiên bản parser |

### 6.2 Trường `extra` theo site (gợi ý, xác nhận khi crawl)

- **itviec**: `reviews_summary`, `company_rating`, `why_love_working` (list), `job_expertise`, `job_domain`, `company_type` (Product/Outsource), `company_country`, `working_days`, `overtime_policy`.
- **topcv**: `company_verified`, `hot_job_flag`, `branch_addresses`, `deadline_text`, `job_position`, `topcv_recommendation_tags`.
- **vietnamworks**: `job_function`, `industries`, `benefit_items` (kèm icon/tên), `salary_min`, `salary_max`, `salary_currency` (nếu API trả), `is_salary_visible`, `level_id`, `company_id`.
- **glints**: `salary_min`, `salary_max`, `salary_currency`, `salary_mode`, `employment_type`, `min_years_experience`, `max_years_experience`, `education_level`, `skills_with_mandatory_flag`, `company_id`, `city_id`.
- **careerviet**: `job_code`, `job_level`, `contact_person` (bỏ nếu là dữ liệu cá nhân), `update_date`, `company_logo_url`.

### 6.3 Các file phụ

- `urls.jsonl`: `{source, job_id, url, listing_url, discovered_at}`
- `errors.jsonl`: `{source, url, http_status, error, attempt, at}`
- `_stats.json`: `{source, site_reported_total, urls_found, fetched_ok, failed, started_at, finished_at}`

## 7. Cấu trúc thư mục dự kiến

```
JD_IT/
  PLAN.md
  requirements.txt
  common/        # http.py, browser.py, storage.py, ratelimit.py
  crawlers/      # itviec.py, careerviet.py, vietnamworks.py, topcv.py, glints.py
  data/
    <site>/{urls.jsonl, jobs.jsonl, errors.jsonl, _stats.json, raw/}
    all_jobs.jsonl
```

## 8. Rủi ro / việc cần xác nhận khi bắt tay vào code

- TopCV và Glints đang chặn bằng Cloudflare → có thể cần chạy Playwright headful trên máy bạn, và vẫn có khả năng bị chặn.
- API nội bộ của VietnamWorks/Glints cần xác nhận bằng DevTools (endpoint, tham số, giới hạn phân trang).
- Số lượng ước tính (cần đối chiếu khi chạy): ITviec ~ vài nghìn, CareerViet/VietnamWorks/TopCV ~ vài nghìn đến chục nghìn job IT mỗi site; Glints ít hơn. Dung lượng raw HTML có thể vài GB (CareerViet ~2MB/listing).
- Tin hết hạn thường bị gỡ khỏi listing → dữ liệu chỉ là snapshot "đang tuyển" tại ngày crawl.
