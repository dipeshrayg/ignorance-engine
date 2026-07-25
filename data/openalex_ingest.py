import json
from pathlib import Path

from core.schema import Paper
from data.openalex_client import works_search

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
        result = works_search(f"concepts.id:{concept_id}", per_page=PER_FIELD,
                               select="id,title,publication_year,concepts")
        for work in result["results"]:
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
