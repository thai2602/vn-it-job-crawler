"""CareerViet: listing pages of IT categories (c1 software, c63 hardware/network) + detail HTML/JSON-LD."""
import json, re, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from selectolax.lexbor import LexborHTMLParser as P

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.core import Http, Store, new_record, jobposting, now

SRC = "careerviet"
CATEGORIES = [("cntt-phan-mem", 1), ("cntt-phan-cung-mang", 63)]
JOB_RE = re.compile(r"/vi/tim-viec-lam/[^\"'\s<>]*?\.([0-9A-Fa-f]{8})\.html")
LABELS = {"Nơi làm việc": "location_text", "Cấp bậc": "level", "Lương": "salary_text",
          "Hết hạn nộp": "expires_at_text", "Kinh nghiệm": "experience_text", "Ngành nghề": "category",
          "Hình thức": "job_type", "Học vấn": "education_text", "Giới tính": "gender_text",
          "Độ tuổi": "age_text", "Ngôn ngữ": "language_text"}


def discover(http, store):
    seen = {r["job_id"] for r in store.read("urls.jsonl")}
    for slug, cid in CATEGORIES:
        page = 1
        while True:
            url = (f"https://careerviet.vn/viec-lam/{slug}-c{cid}-vi.html" if page == 1
                   else f"https://careerviet.vn/viec-lam/{slug}-c{cid}-trang-{page}-vi.html")
            r = http.get(url)
            found = {m.group(1).upper(): m.group(0) for m in JOB_RE.finditer(r.text)}
            new = [k for k in found if k not in seen]
            for k in new:
                seen.add(k)
                store.append("urls.jsonl", {"source": SRC, "job_id": k, "url": "https://careerviet.vn" + found[k],
                                            "listing_url": url, "discovered_at": now()})
            print(SRC, slug, "page", page, "found", len(found), "new", len(new), flush=True)
            if not found or not new or page >= 300:
                break
            page += 1


def parse(html, item):
    t = P(html)
    jp = jobposting(html) or {}
    h1 = t.css_first("h1")
    rec = new_record(SRC, item["job_id"], item["url"], listing_url=item.get("listing_url"),
                     jsonld=jp or None, title=h1.text(strip=True) if h1 else jp.get("title"))
    org = jp.get("hiringOrganization") or {}
    if isinstance(org, dict):
        rec["company_name"], rec["company_url"] = org.get("name"), org.get("sameAs") or org.get("url")
    rec["posted_at"], rec["expires_at"] = jp.get("datePosted"), jp.get("validThrough")
    rec["job_type"] = jp.get("employmentType") if isinstance(jp.get("employmentType"), str) else None
    info = {}
    for li in t.css("li"):
        b = li.css_first("b") or li.css_first("strong")
        v = li.css_first("div.value") or li.css_first("p")
        if b is not None and v is not None:
            info[b.text(strip=True)] = v.text(separator=" ", strip=True)
    for lab, field in LABELS.items():
        for k, v in info.items():
            if k.startswith(lab):
                if field == "category":
                    rec[field] = [c.strip() for c in v.split(",") if c.strip()]
                elif field in rec:
                    rec[field] = v
                else:
                    rec["extra"][field] = v
    if jp.get("jobLocation"):
        rec["work_address"] = json.dumps(jp["jobLocation"], ensure_ascii=False)
    er = jp.get("experienceRequirements")
    if isinstance(er, dict) and not rec["experience_text"]:
        rec["experience_text"] = er.get("description")
    if jp.get("baseSalary") and not rec["salary_text"]:
        rec["salary_text"] = json.dumps(jp["baseSalary"], ensure_ascii=False)
    if jp.get("skills"):
        rec["skills"] = [s.strip() for s in str(jp["skills"]).split(",") if s.strip()]
    rec["description_text"] = P(jp["description"]).text(separator="\n", strip=True) if jp.get("description") else None
    rec["requirements_text"] = P(jp["qualifications"]).text(separator="\n", strip=True) if isinstance(jp.get("qualifications"), str) else None
    rec["benefits_text"] = P(jp["jobBenefits"]).text(separator="\n", strip=True) if isinstance(jp.get("jobBenefits"), str) else None
    main = t.css_first("section.detail-job, [class*=job-detail], main") or t.body
    rec["full_text"] = main.text(separator="\n", strip=True) if main else ""
    rec["extra"]["info_box"] = info
    return rec


def fetch(http, store, item):
    try:
        r = http.get(item["url"])
        if r.status_code == 404:
            store.log_error(item["url"], 404, "not found")
            return
        r.raise_for_status()
        rec = parse(r.text, item)
        rec["raw_path"] = store.save_raw(item["job_id"], r.text)
        store.append("jobs.jsonl", rec)
    except Exception as e:
        store.log_error(item["url"], getattr(getattr(e, "response", None), "status_code", None), e)


def run(limit=None):
    store, http = Store(SRC), Http(delay=0.7)
    if not store.path("urls.jsonl").exists():
        discover(http, store)
    done = store.done_ids()
    todo = [u for u in store.read("urls.jsonl") if u["job_id"] not in done][:limit]
    print(SRC, "todo:", len(todo), flush=True)
    with ThreadPoolExecutor(2) as ex:
        list(ex.map(lambda i: fetch(http, store, i), todo))
    store.write_stats()


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else None)
