"""Export data/jobs_stats.csv from all_jobs.jsonl: only columns useful for statistics/visualization.
Values are copied as-is (no cleaning)."""
import csv, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.core import ROOT

COLS = ["source", "job_id", "title", "company_name", "company_size", "salary_text", "location_text",
        "work_address", "job_type", "level", "experience_text", "education_text", "category", "skills",
        "benefits", "posted_at", "expires_at"]
LISTS = {"category", "skills", "benefits"}

n = 0
with open(ROOT / "all_jobs.jsonl", encoding="utf8") as fi, \
        open(ROOT / "jobs_stats.csv", "w", encoding="utf-8-sig", newline="") as fo:
    w = csv.writer(fo)
    w.writerow(COLS)
    for line in fi:
        if not line.strip():
            continue
        r = json.loads(line)
        w.writerow([" | ".join(map(str, r[c])) if c in LISTS else ("" if r[c] is None else r[c]) for c in COLS])
        n += 1
print("rows", n, flush=True)
