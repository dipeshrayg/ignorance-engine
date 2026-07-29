"""Independent cross-validation of the OpenAlex bridge-density findings
using Semantic Scholar's Graph API -- a completely separate data source
with its own separate rate-limit pool, so it isn't blocked by the OpenAlex
quota this session already exhausted.

Same 8 fields/terms as data/openalex_text_counts.py (imported, not
retyped) run through the same core.detectors.bridges.detect_bridges
formula, saved in the same field_counts/pair_counts/n_total shape as
data/real_text_stats.json for a direct side-by-side comparison.
"""
import json
from itertools import combinations
from pathlib import Path

from core.detectors.bridges import detect_bridges
from data.openalex_text_counts import FIELD_TERMS
from data.semanticscholar_client import bulk_search_total, corpus_total

CACHE_PATH = Path(__file__).parent / "semanticscholar_text_stats.json"
REAL_STATS_PATH = Path(__file__).parent / "real_text_stats.json"


def _s2_term(term: str) -> str:
    """Quote multi-word terms as an exact phrase for bulk search; single
    words pass through unquoted."""
    return f'"{term}"' if " " in term else term


def fetch_text_stats(field_terms: dict[str, str] = FIELD_TERMS) -> tuple[dict[str, int], dict[tuple[str, str], int], int]:
    """(field_counts, pair_counts, n_total) sourced from Semantic Scholar's
    /paper/search/bulk "total" field instead of OpenAlex's meta.count.

    n_total is the whole S2 graph corpus size (see
    semanticscholar_client.corpus_total), *not* restricted to
    abstract-bearing works the way OpenAlex's has_abstract:true choice was
    -- S2's search matches title text too, so a paper without an abstract
    can still be counted, and there's no "has abstract" filter exposed on
    this endpoint to replicate that restriction exactly. Documented here
    since it means the two sources' n_total aren't measuring quite the
    same denominator -- the bridges formula is scale-invariant per pair
    (density is a ratio), so this doesn't bias the comparison, but it's
    worth naming.
    """
    n_total = corpus_total()
    print(f"  S2 corpus total: {n_total:,}")

    field_counts = {}
    for key, term in field_terms.items():
        field_counts[key] = bulk_search_total(_s2_term(term))
        print(f"  {key} ('{term}'): {field_counts[key]:,}")

    pair_counts = {}
    for (a_key, a_term), (b_key, b_term) in combinations(sorted(field_terms.items()), 2):
        n_ab = bulk_search_total(f"{_s2_term(a_term)}+{_s2_term(b_term)}")
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


def compare_to_openalex(s2_candidates) -> None:
    """Print how the S2-sourced bridge ranking compares to the
    OpenAlex-text ranking already cached in real_text_stats.json -- the
    actual cross-validation check this module exists for."""
    if not REAL_STATS_PATH.exists():
        print("  (no real_text_stats.json found -- nothing to compare against)")
        return
    raw = json.loads(REAL_STATS_PATH.read_text())
    oa_field_counts = raw["field_counts"]
    oa_pair_counts = {tuple(k.split("|")): v for k, v in raw["pair_counts"].items()}
    oa_candidates = detect_bridges(oa_field_counts, oa_pair_counts, raw["n_total"])

    oa_sorted = sorted(oa_candidates, key=lambda c: -c.score)
    s2_sorted = sorted(s2_candidates, key=lambda c: -c.score)
    oa_rank = {(c.field_a, c.field_b): i for i, c in enumerate(oa_sorted)}
    s2_rank = {(c.field_a, c.field_b): i for i, c in enumerate(s2_sorted)}
    oa_by_pair = {(c.field_a, c.field_b): c for c in oa_candidates}
    s2_by_pair = {(c.field_a, c.field_b): c for c in s2_candidates}

    print(f"\n{'pair':45s} {'OA rank':>8s} {'S2 rank':>8s} {'OA density':>11s} {'S2 density':>11s}")
    for pair in sorted(oa_rank, key=lambda p: oa_rank[p]):
        a, b = pair
        print(f"{a + '|' + b:45s} {oa_rank[pair]:>8d} {s2_rank[pair]:>8d} "
              f"{oa_by_pair[pair].score:>11.2f} {s2_by_pair[pair].score:>11.2f}")

    top_n = 5
    oa_top = set(sorted(oa_rank, key=lambda p: oa_rank[p])[:top_n])
    s2_top = set(sorted(s2_rank, key=lambda p: s2_rank[p])[:top_n])
    overlap = oa_top & s2_top
    print(f"\n  top-{top_n} overlap: {len(overlap)}/{top_n} pairs agree -- {sorted(overlap)}")


if __name__ == "__main__":
    field_counts, pair_counts, n_total = load_or_fetch_text_stats(refresh=True)
    candidates = detect_bridges(field_counts, pair_counts, n_total)
    candidates.sort(key=lambda c: -c.score)

    print("\nSemantic Scholar bridge-density ranking:")
    for c in candidates:
        ev = c.evidence
        print(f"  {c.field_a} x {c.field_b}: density={c.score:.2f}  "
              f"(n_a={ev['n_a']:,} n_b={ev['n_b']:,} n_ab={ev['n_ab']:,} expected={ev['expected_ab']:,})")

    compare_to_openalex(candidates)
    print(f"\ncached to {CACHE_PATH}")
