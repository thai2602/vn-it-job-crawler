"""VietnamWorks: public search API returns full job objects (IT = jobFunction parentId 5)."""
import json, re, sys
from pathlib import Path
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.core import Http, Store, new_record, now

SRC = "vietnamworks"
API = "https://ms.vietnamworks.com/job-search/v1.0/search"
HEADERS = {"Origin": "https://www.vietnamworks.com", "Referer": "https://www.vietnamworks.com/",
           "Content-Type": "application/json"}
# Each filter set is one pass; ids are de-duplicated across passes.
PASSES = [
    ("function_IT", [{"field": "jobFunction", "value": json.dumps([{"parentId": 5, "childrenIds": [-1]}])}]),
]
PAGE_SIZE = 50


def strip_html(s):
    return re.sub(r"\n{2,}", "\n", re.sub(r"<[^>]+>", "\n", re.sub(r"<br\s*/?>|</p>|</li>", "\n", s or ""))).strip()


def parse(d, listing):
    jid = str(d["jobId"])
    jf = d.get("jobFunction") or {}
    locs = d.get("workingLocations") or []
    rec = new_record(
        SRC, jid, d.get("jobUrl") or f"https://www.vietnamworks.com/{d.get('canonical')}",
        listing_url=listing, title=d.get("jobTitle"), company_name=d.get("companyName"),
        company_url=d.get("companyUrl") or None, company_size=d.get("companySize") or d.get("companySizeVI") or None,
        company_address=d.get("address"), salary_text=d.get("prettySalary"),
        location_text="; ".join(filter(None, [l.get("cityNameVI") or l.get("cityName") for l in locs])) or None,
        work_address=d.get("address"), job_type=str(d.get("typeWorkingId")) if d.get("typeWorkingId") else None,
        level=d.get("jobLevelVI") or d.get("jobLevel"),
        experience_text=str(d.get("yearsOfExperience")) if d.get("yearsOfExperience") is not None else None,
        education_text=str(d.get("highestDegreeId")) if d.get("highestDegreeId") else None,
        category=[x for x in [jf.get("parentName"), jf.get("childName")] if x],
        skills=[s.get("skillName") for s in (d.get("skills") or []) if s.get("skillName")],
        benefits=[b.get("benefitName") for b in (d.get("benefits") or []) if b.get("benefitName")],
        description_text=strip_html(d.get("jobDescription")),
        requirements_text=strip_html(d.get("jobRequirement")),
        full_text=strip_html((d.get("jobDescription") or "") + "\n" + (d.get("jobRequirement") or "")),
        headcount_text=str(d.get("numberOfRecruits")) if d.get("numberOfRecruits") else None,
        language_text=d.get("languageSelectedVI") or d.get("languageSelected"),
        posted_at_text=d.get("approvedOnText"), posted_at=d.get("approvedOn") or d.get("createdOn"),
        expires_at=d.get("expiredOn"), extra={k: d.get(k) for k in (
            "companyId", "companyProfile", "contactName", "isSalaryVisible", "salary", "salaryMin", "salaryMax",
            "salaryCurrency", "salaryPeriodId", "jobLevelId", "typeWorkingId", "industriesV3", "industries",
            "jobFunction", "groupJobFunctionsV3", "jobFunctionsV3", "workingLocations", "rangeAge",
            "yearsOfExperience", "highestDegreeId", "languageSelectedId", "lastUpdatedOn", "createdOn")},
    )
    return rec


def run(limit=None):
    store, http = Store(SRC), httpx.Client(headers=HEADERS, timeout=60)
    done = store.done_ids()
    n = 0
    for name, flt in PASSES:
        page = 0
        while True:
            body = {"userId": 0, "query": "", "filter": flt, "ranges": [], "order": [],
                    "hitsPerPage": PAGE_SIZE, "page": page, "retrieveFields": [], "summaryVersion": ""}
            r = http.post(API, json=body)
            if r.status_code != 200:
                store.log_error(f"{API}#{name}:{page}", r.status_code, r.text[:200])
                break
            j = r.json()
            hits = j.get("data") or []
            for d in hits:
                jid = str(d["jobId"])
                if jid in done:
                    continue
                done.add(jid)
                rec = parse(d, f"{name}:page={page}")
                rec["raw_path"] = store.save_raw(jid, json.dumps(d, ensure_ascii=False), "json")
                store.append("urls.jsonl", {"source": SRC, "job_id": jid, "url": rec["url"],
                                            "listing_url": rec["listing_url"], "discovered_at": now()})
                store.append("jobs.jsonl", rec)
                n += 1
            print(SRC, name, "page", page, "/", j["meta"].get("nbPages"), "total", len(done), flush=True)
            page += 1
            if not hits or page >= j["meta"].get("nbPages", 0) or (limit and n >= limit):
                break
    store.write_stats()


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else None)
