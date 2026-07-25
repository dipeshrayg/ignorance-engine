import json
from itertools import combinations
from pathlib import Path

from data.openalex_client import cooccurrence, work_count

CACHE_PATH = Path(__file__).parent / "real_text_stats.json"

# One representative search term per field. Deliberately simple single
# words/phrases, not full field names — abstracts say "robot" far more
# than "robotics". ponytail: crude proxy for "papers about X"; upgrade
# path is a short OR-list of synonyms per field if single terms prove too
# noisy (e.g. "robot OR robotic OR autonomous agent").
FIELD_TERMS = {
    "materials_science": "materials science",
    "pharmacology": "pharmacology",
    "immunology": "immunology",
    "robotics": "robot",
    "climatology": "climate",
    "linguistics": "linguistics",
    "neuroscience": "neuroscience",
    "sociology": "sociology",
}


def fetch_text_stats(field_terms: dict[str, str] = FIELD_TERMS) -> tuple[dict[str, int], dict[tuple[str, str], int], int]:
    """Same (field_counts, pair_counts, n_total) shape as
    data/openalex_counts.py, but counted by literal abstract-text mention
    instead of OpenAlex's concept/topic classifier tags.

    Built because tag-based counting was verified unreliable: every one of
    13 "zero tag co-occurrence" candidates from the topic drill-down turned
    out to have real (sometimes hundreds of) papers on text search --
    OpenAlex's classifier just hadn't co-tagged them. See
    data/refuter_verdicts.json and core/refuter.py.

    n_total is works with an abstract (172.5M of 321M total) rather than
    the whole corpus, since abstract.search can only match works that have
    an abstract at all -- using the full corpus as N would understate
    every expected_ab.
    """
    n_total = work_count("has_abstract:true")
    print(f"  corpus with abstracts: {n_total:,}")

    field_counts = {}
    for key, term in field_terms.items():
        field_counts[key] = work_count(f"abstract.search:{term}")
        print(f"  {key} ('{term}'): {field_counts[key]:,}")

    pair_counts = {}
    for (a_key, a_term), (b_key, b_term) in combinations(sorted(field_terms.items()), 2):
        n_ab = cooccurrence(a_term, b_term)
        pair_counts[(a_key, b_key)] = n_ab
        print(f"  {a_key} x {b_key}: {n_ab:,}")

    return field_counts, pair_counts, n_total


def load_or_fetch_text_stats(refresh: bool = False) -> tuple[dict[str, int], dict[tuple[str, str], int], int]:
    if not refresh and CACHE_PATH.exists():
        raw = json.loads(CACHE_PATH.read_text())
        pair_counts = {tuple(k.split("|")): v for k, v in raw["pair_counts"].items()}
        return raw["field_counts"], pair_counts, raw["n_total"]

    field_counts, pair_counts, n_total = fetch_text_stats()
    CACHE_PATH.write_text(json.dumps({
        "field_counts": field_counts,
        "pair_counts": {f"{a}|{b}": v for (a, b), v in pair_counts.items()},
        "n_total": n_total,
    }, indent=2))
    return field_counts, pair_counts, n_total


if __name__ == "__main__":
    load_or_fetch_text_stats(refresh=True)
    print(f"cached to {CACHE_PATH}")
