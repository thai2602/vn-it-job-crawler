"""Rebuild careerviet/jobs.jsonl from saved raw HTML (no network)."""
import json, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.core import Store
from crawlers.careerviet import parse, SRC

store = Store(SRC)
urls = list({u["job_id"]: u for u in store.read("urls.jsonl")}.items())


def one(kv):
    jid, item = kv
    f = store.dir / "raw" / f"{jid}.html"
    if not f.exists():
        return None
    rec = parse(f.read_text(encoding="utf8"), item)
    rec["raw_path"] = f"{SRC}/raw/{jid}.html"
    return rec


with ThreadPoolExecutor(16) as ex:
    out = [r for r in ex.map(one, urls) if r]
store.path("jobs.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf8")
print("reparsed", len(out), flush=True)
