"""Shared helpers: HTTP client with rate limit, JSONL storage with resume, schema record."""
import json, re, time, threading
from datetime import datetime, timezone
from pathlib import Path
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

ROOT = Path(__file__).resolve().parent.parent / "data"
CRAWLER_VERSION = "0.1"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

FIELDS = ["source", "job_id", "url", "title", "company_name", "company_url", "company_size",
          "company_industry", "company_address", "salary_text", "location_text", "work_address",
          "work_model", "job_type", "level", "experience_text", "education_text", "category",
          "skills", "benefits", "description_text", "requirements_text", "benefits_text",
          "full_text", "headcount_text", "gender_text", "language_text", "posted_at_text",
          "posted_at", "expires_at_text", "expires_at", "status", "view_count_text", "jsonld",
          "extra", "raw_path", "listing_url", "crawled_at", "crawler_version"]
LIST_FIELDS = {"category", "skills", "benefits"}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_record(source, job_id, url, **kw):
    r = {f: ([] if f in LIST_FIELDS else ({} if f == "extra" else None)) for f in FIELDS}
    r.update(source=source, job_id=str(job_id), url=url, status="active",
             crawled_at=now(), crawler_version=CRAWLER_VERSION)
    r.update(kw)
    return r


class Store:
    def __init__(self, source):
        self.dir = ROOT / source
        (self.dir / "raw").mkdir(parents=True, exist_ok=True)
        self.source = source
        self.lock = threading.Lock()

    def path(self, name):
        return self.dir / name

    def append(self, name, obj):
        with self.lock, open(self.path(name), "a", encoding="utf8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    def read(self, name):
        p = self.path(name)
        if not p.exists():
            return []
        with open(p, encoding="utf8") as f:
            return [json.loads(l) for l in f if l.strip()]

    def done_ids(self):
        return {r["job_id"] for r in self.read("jobs.jsonl")}

    def save_raw(self, job_id, text, ext="html"):
        rel = f"raw/{job_id}.{ext}"
        (self.dir / rel).write_text(text, encoding="utf8")
        return f"{self.source}/{rel}"

    def log_error(self, url, status, err):
        self.append("errors.jsonl", {"source": self.source, "url": url, "http_status": status,
                                     "error": str(err)[:300], "at": now()})

    def write_stats(self, extra=None):
        d = {"source": self.source, "urls_found": len(self.read("urls.jsonl")),
             "fetched_ok": len(self.read("jobs.jsonl")), "failed": len(self.read("errors.jsonl")),
             "at": now()}
        d.update(extra or {})
        self.path("_stats.json").write_text(json.dumps(d, indent=1), encoding="utf8")


class Http:
    def __init__(self, delay=1.0, **kw):
        self.delay, self._last, self._lock = delay, 0.0, threading.Lock()
        self.c = httpx.Client(headers={"User-Agent": UA, "Accept-Language": "vi,en;q=0.8"},
                              follow_redirects=True, timeout=30, **kw)

    def _wait(self):
        with self._lock:
            t = max(0, self._last + self.delay - time.time())
            self._last = time.time() + t
        if t:
            time.sleep(t)

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(2, max=30), reraise=True,
           retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)))
    def get(self, url, **kw):
        self._wait()
        r = self.c.get(url, **kw)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(10 if r.status_code == 429 else 2)
            r.raise_for_status()
        return r


def jsonld_blocks(html):
    out = []
    for m in re.findall(r"<script[^>]*ld\+json[^>]*>(.*?)</script>", html, re.S):
        try:
            out.append(json.loads(m, strict=False))
        except Exception:
            pass
    return out


def jobposting(html):
    for b in jsonld_blocks(html):
        for x in (b if isinstance(b, list) else [b]):
            if isinstance(x, dict) and x.get("@type") == "JobPosting":
                return x
    return None
