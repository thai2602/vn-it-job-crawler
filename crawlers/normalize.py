"""Normalize all_jobs.jsonl -> data/jobs_clean.csv (one row per job, analysis-ready).

Rules
- Salary is converted to VND per month. Year -> /12. USD -> VND at USD_VND (a fixed assumption, edit if needed).
- When both min and max exist, avg = (min + max) / 2. With only one bound ("up to X", "from X"), avg = that bound.
- "Negotiable"/"Competitive"/unparsable salary -> empty numbers, salary_type = negotiable.
- Experience (years) and company size follow the same min/max/avg rule.
Raw files are not modified.
"""
import csv, json, re, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.core import ROOT

USD_VND = 26000  # assumed fixed exchange rate

COLS = ["source", "job_id", "title", "company_name", "company_size", "company_size_avg",
        "salary_type", "salary_min_vnd", "salary_max_vnd", "salary_avg_vnd", "salary_currency_orig",
        "city", "cities", "level_std", "job_type_std",
        "exp_min_years", "exp_max_years", "exp_avg_years",
        "skills", "n_skills", "benefits", "posted_date", "expires_date", "days_open"]

# ---------- salary ----------
UNIT_RE = re.compile(r"(?<![a-zà-ỹ])(triệu|trieu|tr|million|mil|m|k)(?![a-zà-ỹ])", re.I)
NUM_RE = re.compile(r"\d[\d.,]*")
UPTO = re.compile(r"up to|tới|lên đến|đến|tối đa", re.I)
FROM = re.compile(r"\btừ\b|\btrên\b|from|over|tối thiểu|>", re.I)


def to_number(s):
    s = s.strip(".,")
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", s):
        return float(re.sub(r"[.,]", "", s))
    return float(s.replace(",", "."))


def parse_salary_text(text):
    """Return (type, min, max, currency, per_year) with money in original currency units, or None."""
    t = text.lower()
    cur = "USD" if ("usd" in t or "$" in t) else ("VND" if re.search(r"vnd|vnđ|₫|triệu|trieu|\btr\b|\bm\b|mil", t) else None)
    nums = [to_number(n) for n in NUM_RE.findall(t)]
    if not nums or cur is None:
        return None
    u = UNIT_RE.search(t)
    mult = 1
    if u:
        mult = {"k": 1e3}.get(u.group(1).lower(), 1e6)
    elif cur == "VND" and max(nums) < 1000:
        return None
    nums = [n * mult for n in nums]
    per_year = bool(re.search(r"/\s*năm|per year|/year|\bnăm\b", t)) and "kinh nghiệm" not in t
    if len(nums) >= 2:
        lo, hi = sorted(nums[:2])
        return ("range", lo, hi, cur, per_year)
    n = nums[0]
    if UPTO.search(t):
        return ("up_to", None, n, cur, per_year)
    if FROM.search(t):
        return ("from", n, None, cur, per_year)
    return ("fixed", n, n, cur, per_year)


def salary(r):
    s, e, src = r.get("salary_text"), r.get("extra") or {}, r["source"]
    parsed = None
    if src == "vietnamworks":
        if e.get("isSalaryVisible") and (e.get("salaryMax") or e.get("salaryMin")):
            lo, hi = e.get("salaryMin") or None, e.get("salaryMax") or None
            typ = "range" if lo and hi and lo != hi else ("up_to" if hi and not lo else ("from" if lo and not hi else "fixed"))
            parsed = (typ, lo, hi, e.get("salaryCurrency") or "VND", e.get("salaryPeriodId") == 2)
    elif s and s.startswith("{"):
        try:
            j = json.loads(s)
            v, cur = j.get("value") or {}, j.get("currency")
            if "minValue" in v or "maxValue" in v:
                lo, hi = v.get("minValue"), v.get("maxValue")
                if isinstance(lo, (int, float)) and isinstance(hi, (int, float)):
                    parsed = ("range" if lo != hi else "fixed", min(lo, hi), max(lo, hi), cur, False)
            elif isinstance(v.get("value"), str):
                parsed = parse_salary_text(v["value"])
        except Exception:
            pass
    elif s:
        parsed = parse_salary_text(s)
    if not parsed:
        return "negotiable", None, None, None, None
    typ, lo, hi, cur, yearly = parsed
    k = (USD_VND if cur == "USD" else 1) / (12 if yearly else 1)
    lo, hi = (lo * k if lo else None), (hi * k if hi else None)
    avg = (lo + hi) / 2 if lo and hi else (lo or hi)
    if not avg or not (1e6 <= avg <= 2e9):  # implausible monthly VND -> treat as unparsable
        return "negotiable", None, None, None, cur
    return typ, round(lo) if lo else None, round(hi) if hi else None, round(avg), cur


# ---------- other fields ----------
CITY = {"tp.hcm": "Hồ Chí Minh", "tp. hồ chí minh": "Hồ Chí Minh", "ho chi minh": "Hồ Chí Minh",
        "thành phố hồ chí minh": "Hồ Chí Minh", "hanoi": "Hà Nội", "ha noi": "Hà Nội",
        "da nang": "Đà Nẵng", "thành phố khác": "Khác", "danang": "Đà Nẵng"}
KNOWN = {"Hồ Chí Minh", "Hà Nội", "Đà Nẵng"}


def norm_city(c):
    if not c or c.strip().lower() in ("not available", "city", "none"):
        return None
    c = c.strip()
    return CITY.get(c.lower(), c)


def cities(r):
    out = []
    src = r["source"]
    try:
        if src == "itviec" and r.get("location_text"):
            for p in json.loads(r["location_text"]):
                a = p["address"]
                out += [norm_city(a.get("addressRegion")) or (norm_city(a.get("addressLocality")) if norm_city(a.get("addressLocality")) in KNOWN else None)]
        elif src == "careerviet" and r.get("work_address"):
            j = json.loads(r["work_address"])
            for p in (j if isinstance(j, list) else [j]):
                out.append(norm_city(p["address"].get("addressLocality")))
        elif src == "vietnamworks" and r.get("location_text"):
            out = [norm_city(x) for x in r["location_text"].split(";")]
    except Exception:
        pass
    seen = []
    for c in out:
        if c and c not in seen:
            seen.append(c)
    return seen


LEVEL = [("thực tập", "Intern"), ("mới tốt nghiệp", "Fresher"), ("giám đốc", "Director"),
         ("trưởng phòng", "Manager"), ("quản lý", "Manager"), ("trưởng nhóm", "Lead"),
         ("nhân viên", "Staff")]


def level(r):
    t = (r.get("level") or "").lower()
    for k, v in LEVEL:
        if k in t:
            return v
    return None


def job_type(r):
    t, src = r.get("job_type") or "", r["source"]
    if src == "itviec":
        return {"FULL_TIME": "Full-time"}.get(t)
    if src == "vietnamworks":
        return "Full-time" if t == "1" else (f"unknown(vnw_code={t})" if t else None)
    out = []
    for k, v in (("chính thức", "Full-time"), ("bán thời gian", "Part-time"), ("thực tập", "Internship"),
                 ("thời vụ", "Temporary"), ("hợp đồng", "Contract")):
        if k in t.lower():
            out.append(v)
    return " | ".join(out) or None


def experience(r):
    t, src = (r.get("experience_text") or "").strip(), r["source"]
    if not t:
        return None, None, None
    if src == "vietnamworks":
        n = int(t)
        return (None, None, None) if n < 0 else (n, n, n)
    tl = t.lower()
    if "chưa có kinh nghiệm" in tl:
        return 0, 0, 0
    nums = [float(x) for x in re.findall(r"\d+(?:[.,]\d+)?", tl.replace(",", "."))]
    if "năm" not in tl or not nums or len(t) > 40:
        return None, None, None
    if len(nums) >= 2:
        lo, hi = sorted(nums[:2])
        return lo, hi, (lo + hi) / 2
    n = nums[0]
    if "lên đến" in tl or "đến" in tl:
        return None, n, n
    return n, None, n


def size_avg(t):
    if not t:
        return None
    t = t.replace(",", "")
    if t.lower().startswith("less than"):
        return 5
    m = re.fullmatch(r"(\d+)-(\d+)", t)
    if m:
        return (int(m.group(1)) + int(m.group(2))) / 2
    m = re.fullmatch(r"over (\d+)", t.lower())
    return int(m.group(1)) if m else None


def to_date(s, src):
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if d.tzinfo:
            d = d.astimezone(timezone(timedelta(hours=7)))
        return d.date()
    except Exception:
        return None


def fmt(x):
    if x is None:
        return ""
    return int(x) if isinstance(x, float) and x == int(x) else (round(x, 2) if isinstance(x, float) else x)


def main():
    n = 0
    with open(ROOT / "all_jobs.jsonl", encoding="utf8") as fi, \
            open(ROOT / "jobs_clean.csv", "w", encoding="utf-8-sig", newline="") as fo:
        w = csv.writer(fo)
        w.writerow(COLS)
        for line in fi:
            if not line.strip():
                continue
            r = json.loads(line)
            styp, lo, hi, avg, cur = salary(r)
            cs = cities(r)
            e = experience(r)
            pd_, ed = to_date(r.get("posted_at"), r["source"]), to_date(r.get("expires_at"), r["source"])
            row = [r["source"], r["job_id"], r["title"], r["company_name"], r.get("company_size"),
                   size_avg(r.get("company_size")), styp, lo, hi, avg, cur,
                   cs[0] if cs else None, " | ".join(cs), level(r), job_type(r), *e,
                   " | ".join(r["skills"]), len(r["skills"]), " | ".join(r["benefits"]), pd_, ed,
                   (ed - pd_).days if pd_ and ed else None]
            w.writerow([fmt(x) for x in row])
            n += 1
    print("rows", n, flush=True)


if __name__ == "__main__":
    main()
