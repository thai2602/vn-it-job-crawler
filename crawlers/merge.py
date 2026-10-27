"""Concatenate per-site jobs.jsonl into data/all_jobs.jsonl and data/all_jobs.csv (no value changes)."""
import csv, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.core import ROOT, FIELDS, LIST_FIELDS

SOURCES = ["itviec", "topcv", "vietnamworks", "glints", "careerviet"]
JSON_FIELDS = {"jsonld", "extra"}


def cell(field, v):
    if v is None:
        return ""
    if field in LIST_FIELDS:
        return " | ".join(map(str, v))
    if field in JSON_FIELDS:
        return json.dumps(v, ensure_ascii=False)
    return v


n = {}
with open(ROOT / "all_jobs.jsonl", "w", encoding="utf8") as fj, \
        open(ROOT / "all_jobs.csv", "w", encoding="utf-8-sig", newline="") as fc:
    w = csv.DictWriter(fc, fieldnames=FIELDS, quoting=csv.QUOTE_MINIMAL)
    w.writeheader()
    for s in SOURCES:
        p = ROOT / s / "jobs.jsonl"
        if not p.exists():
            continue
        for line in open(p, encoding="utf8"):
            if not line.strip():
                continue
            r = json.loads(line)
            fj.write(line if line.endswith("\n") else line + "\n")
            w.writerow({f: cell(f, r.get(f)) for f in FIELDS})
            n[s] = n.get(s, 0) + 1
print(n, "total", sum(n.values()))
