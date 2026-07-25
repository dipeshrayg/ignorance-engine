import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from core.schema import Paper

API = "https://api.openalex.org/works"
MAILTO = "ray-d@ulster.ac.uk"  # OpenAlex "polite pool": faster, more reliable responses
SCORE_THRESHOLD = 0.3          # keep only meaningfully-tagged concepts, drop near-zero noise tags
PER_FIELD = 200                # papers pulled per field, ranked by citation count

FIELDS = {
    "materials_science": "C192562407",
    "pharmacology": "C98274493",
    "immunology": "C203014093",
    "robotics": "C34413123",
    "climatology": "C49204034",
    "linguistics": "C41895202",
    "neuroscience": "C169760540",
    "sociology": "C144024400",
}

CACHE_PATH = Path(__file__).parent / "real_papers.json"


def _fetch_field(concept_id: str) -> list[dict]:
    params = {
        "filter": f"concepts.id:{concept_id}",
        "sort": "cited_by_count:desc",
        "per-page": str(PER_FIELD),
        "select": "id,title,publication_year,concepts",
        "mailto": MAILTO,
    }
    url = f"{API}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)["results"]


def ingest() -> list[Paper]:
    """Pull real papers from OpenAlex for FIELDS, tag each with whichever of
    our target fields it's meaningfully associated with (concept score >=
    threshold), and dedupe by work id — a paper pulled under two fields
    keeps both tags, since that IS a real bridge paper, not a duplicate.

    ponytail: samples the top-cited papers per field, not a random or
    representative sample — biased toward old landmark papers and review
    articles. Fine for a first real run; switch to stratified/random
    sampling if that bias shows up in detector results.
    """
    concept_url_to_key = {f"https://openalex.org/{code}": key for key, code in FIELDS.items()}
    papers: dict[str, Paper] = {}

    for key, concept_id in FIELDS.items():
        print(f"  fetching {key}...")
        for work in _fetch_field(concept_id):
            matched = frozenset(
                concept_url_to_key[c["id"]]
                for c in work["concepts"]
                if c["id"] in concept_url_to_key and c["score"] >= SCORE_THRESHOLD
            )
            if not matched:
                continue
            wid = work["id"]
            if wid in papers:
                papers[wid] = Paper(wid, papers[wid].title, papers[wid].year, papers[wid].fields | matched)
            else:
                papers[wid] = Paper(wid, work["title"] or "(untitled)", work["publication_year"] or 0, matched)
        time.sleep(0.2)  # stay polite even in the mailto pool

    return list(papers.values())


def load_or_ingest(refresh: bool = False) -> list[Paper]:
    if not refresh and CACHE_PATH.exists():
        raw = json.loads(CACHE_PATH.read_text())
        return [Paper(p["id"], p["title"], p["year"], frozenset(p["fields"])) for p in raw]

    papers = ingest()
    CACHE_PATH.write_text(json.dumps([
        {"id": p.id, "title": p.title, "year": p.year, "fields": sorted(p.fields)}
        for p in papers
    ], indent=2))
    return papers


if __name__ == "__main__":
    result = load_or_ingest(refresh=True)
    print(f"{len(result)} papers cached to {CACHE_PATH}")
