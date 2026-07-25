import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from data.openalex_ingest import MAILTO

API = "https://api.openalex.org/subfields"
CACHE_PATH = Path(__file__).parent / "subfields.json"


def fetch_subfields() -> list[dict]:
    """All 252 OpenAlex subfields with their parent domain/field and size —
    metadata only, no per-pair queries. This is the pool the bandit picks
    from at finer granularity than the 19 top-level disciplines already
    explored (which turned out too coarse: any real gap between two famous
    disciplines gets noticed and reviewed fast, see refuter_verdicts.json).
    """
    results = []
    page = 1
    while True:
        params = {"per-page": "200", "page": str(page),
                   "select": "id,display_name,field,domain,works_count", "mailto": MAILTO}
        url = f"{API}?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.load(resp)
        results.extend(data["results"])
        if len(results) >= data["meta"]["count"]:
            break
        page += 1
        time.sleep(0.15)
    return [{
        "id": r["id"].rsplit("/", 1)[-1],
        "name": r["display_name"],
        "field": r["field"]["display_name"],
        "domain": r["domain"]["display_name"],
        "works_count": r["works_count"],
    } for r in results]


def load_or_fetch_subfields(refresh: bool = False) -> list[dict]:
    if not refresh and CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    subfields = fetch_subfields()
    CACHE_PATH.write_text(json.dumps(subfields, indent=2))
    return subfields


if __name__ == "__main__":
    subfields = load_or_fetch_subfields(refresh=True)
    print(f"{len(subfields)} subfields cached to {CACHE_PATH}")
