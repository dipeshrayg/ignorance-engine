import json
from pathlib import Path

from data.openalex_client import subfields_list

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
        data = subfields_list(per_page=200, page=page, select="id,display_name,field,domain,works_count")
        results.extend(data["results"])
        if len(results) >= data["meta"]["count"]:
            break
        page += 1
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
