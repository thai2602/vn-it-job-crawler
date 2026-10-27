"""ITviec: discovery via sitemap + listing pages, detail via HTML + JSON-LD."""
import json, re, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from selectolax.lexbor import LexborHTMLParser as P

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.core import Http, Store, new_record, jobposting, now

SRC = "itviec"
SITEMAPS = ["twinnings_jobs_desc_en.xml", "twinnings_jobs_desc_vn.xml",
            "twinnings_jobs_by_title_en.xml", "twinnings_jobs_by_skill_en.xml"]
JOB_RE = re.compile(r"https://itviec\.com/it-jobs/[a-z0-9-]+-(\d{4,})")
LINK_RE = re.compile(r"/it-jobs/[a-z0-9-]+-\d{4,}")


def discover(http, store):
    seen = {r["job_id"] for r in store.read("urls.jsonl")}

    def add(url, listing):
        m = JOB_RE.fullmatch(url)
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            store.append("urls.jsonl", {"source": SRC, "job_id": m.group(1), "url": url,
                                        "listing_url": listing, "discovered_at": now()})
            return True
        return False

    for sm in SITEMAPS:
        r = http.get(f"https://itviec.com/{sm}")
        for url in re.findall(r"<loc>([^<]+)</loc>", r.text):
            add(url, f"sitemap:{sm}")
    for page in range(1, 300):
        r = http.get(f"https://itviec.com/it-jobs?page={page}")
        links = set(LINK_RE.findall(r.text))
        if not links:
            break
        for l in links:
            add("https://itviec.com" + l, f"page={page}")
    print(SRC, "urls:", len(seen))


def sections(t):
    secs = {}
    for h2 in t.css("h2"):
        buf, n = [], h2.next
        while n is not None and n.tag != "h2":
            if not n.tag.startswith("-"):
                buf.append(n.text(separator="\n", strip=True))
            n = n.next
        secs[h2.text(strip=True)] = "\n".join(b for b in buf if b)
    return secs


def parse(html, item):
    t = P(html)
    jp = jobposting(html) or {}
    h1 = t.css_first("h1")
    rec = new_record(SRC, item["job_id"], item["url"], listing_url=item.get("listing_url"),
                     jsonld=jp or None, title=h1.text(strip=True) if h1 else jp.get("title"))
    org = jp.get("hiringOrganization") or {}
    if isinstance(org, dict):
        rec["company_name"] = org.get("name")
        rec["company_url"] = org.get("sameAs") or org.get("url")
    rec["skills"] = [s.strip() for s in (jp.get("skills") or "").split(",") if s.strip()]
    rec["category"] = [jp["industry"]] if jp.get("industry") else []
    rec["posted_at"], rec["expires_at"] = jp.get("datePosted"), jp.get("validThrough")
    rec["job_type"] = jp.get("employmentType")
    rec["location_text"] = json.dumps(jp["jobLocation"], ensure_ascii=False) if jp.get("jobLocation") else None
    rec["salary_text"] = json.dumps(jp["baseSalary"], ensure_ascii=False) if jp.get("baseSalary") else None
    c = t.css_first("[class*=job-content]")
    rec["full_text"] = c.text(separator="\n", strip=True) if c else ""
    secs = sections(t)
    for k, v in secs.items():
        kl = k.lower()
        if "job description" in kl or "mô tả" in kl:
            rec["description_text"] = v
        elif "skills and experience" in kl or "kỹ năng" in kl:
            rec["requirements_text"] = v
        elif "love working" in kl or "yêu thích" in kl:
            rec["benefits_text"] = v
    main = t.css_first("main") or t.body
    rec["extra"] = {"sections": secs,
                    "header_text": main.text(separator=" | ", strip=True)[:1500] if main else None}
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
    print(SRC, "todo:", len(todo))
    with ThreadPoolExecutor(2) as ex:
        list(ex.map(lambda i: fetch(http, store, i), todo))
    store.write_stats()


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else None)
