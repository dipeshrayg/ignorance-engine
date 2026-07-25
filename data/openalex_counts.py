import json
from itertools import combinations
from pathlib import Path

from data.openalex_client import work_count
from data.openalex_ingest import FIELDS

CACHE_PATH = Path(__file__).parent / "real_field_stats.json"


def fetch_real_stats() -> tuple[dict[str, int], dict[tuple[str, str], int], int]:
    """True global field/pair counts from OpenAlex — no local sampling, no
    sampling bias. Each number is an exact count over the full ~250M-work
    index, not an estimate from a downloaded subset.
    """
    n_total = work_count()
    print(f"  total corpus: {n_total:,} works")

    field_counts = {}
    for key, concept_id in FIELDS.items():
        field_counts[key] = work_count(f"concepts.id:{concept_id}")
        print(f"  {key}: {field_counts[key]:,}")

    pair_counts = {}
    for (a_key, a_id), (b_key, b_id) in combinations(sorted(FIELDS.items()), 2):
        n_ab = work_count(f"concepts.id:{a_id},concepts.id:{b_id}")
        pair_counts[(a_key, b_key)] = n_ab
        print(f"  {a_key} x {b_key}: {n_ab:,}")

    return field_counts, pair_counts, n_total


def load_or_fetch_real_stats(refresh: bool = False) -> tuple[dict[str, int], dict[tuple[str, str], int], int]:
    if not refresh and CACHE_PATH.exists():
        raw = json.loads(CACHE_PATH.read_text())
        pair_counts = {tuple(k.split("|")): v for k, v in raw["pair_counts"].items()}
        return raw["field_counts"], pair_counts, raw["n_total"]

    field_counts, pair_counts, n_total = fetch_real_stats()
    CACHE_PATH.write_text(json.dumps({
        "field_counts": field_counts,
        "pair_counts": {f"{a}|{b}": v for (a, b), v in pair_counts.items()},
        "n_total": n_total,
    }, indent=2))
    return field_counts, pair_counts, n_total


if __name__ == "__main__":
    load_or_fetch_real_stats(refresh=True)
    print(f"cached to {CACHE_PATH}")
