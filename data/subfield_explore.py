import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from core.detectors.bridges import detect_bridges
from core.detectors.transitive import detect_transitive_links
from core.ranking import rank
from data.openalex_client import cooccurrence, work_count
from data.subfield_catalog import load_or_fetch_subfields

CACHE_PATH = Path(__file__).parent / "subfield_text_stats.json"
TOP_N_PER_DOMAIN = 3  # -> 12 subfields across 4 domains, C(12,2)=66 pairs -- fits one quota window


def pick_cross_domain_pool(n_per_domain: int = TOP_N_PER_DOMAIN) -> dict[str, str]:
    """Biggest subfield from each of OpenAlex's top-level domains (Physical
    Sciences, Life Sciences, Health Sciences, Social Sciences), n_per_domain
    each -- finer-grained than the 8 discipline-level fields already tested,
    and deliberately cross-domain since the discipline-level run showed any
    gap within a domain (e.g. two health-sciences fields) tends to already
    be filled and named by someone working across both.
    """
    subfields = load_or_fetch_subfields()
    by_domain = defaultdict(list)
    for s in subfields:
        by_domain[s["domain"]].append(s)

    pool = {}
    for domain, items in by_domain.items():
        items.sort(key=lambda s: s["works_count"], reverse=True)
        for s in items[:n_per_domain]:
            key = s["name"].lower().replace(" ", "_").replace("-", "_")
            pool[key] = s["name"].lower()
    return pool


def fetch_subfield_text_stats(field_terms: dict[str, str]):
    n_total = work_count("has_abstract:true")
    field_counts = {}
    for key, term in field_terms.items():
        field_counts[key] = work_count(f"abstract.search:{term}")
        print(f"  {key}: {field_counts[key]:,}")

    pair_counts = {}
    for (a_key, a_term), (b_key, b_term) in combinations(sorted(field_terms.items()), 2):
        pair_counts[(a_key, b_key)] = cooccurrence(a_term, b_term)

    return field_counts, pair_counts, n_total


def run(n_per_domain: int = TOP_N_PER_DOMAIN):
    field_terms = pick_cross_domain_pool(n_per_domain)
    print(f"cross-domain pool ({len(field_terms)} subfields): {list(field_terms.values())}")

    field_counts, pair_counts, n_total = fetch_subfield_text_stats(field_terms)
    candidates = rank(detect_bridges(field_counts, pair_counts, n_total) + detect_transitive_links(field_counts, pair_counts))

    CACHE_PATH.write_text(json.dumps({
        "field_terms": field_terms, "field_counts": field_counts,
        "pair_counts": {f"{a}|{b}": v for (a, b), v in pair_counts.items()}, "n_total": n_total,
        "top_candidates": [
            {"a": c.field_a, "b": c.field_b, "detector": c.detector, "score": round(c.score, 1), "evidence": c.evidence}
            for c in candidates[:15]
        ],
    }, indent=2))

    print("\ntop 15 candidates:")
    for c in candidates[:15]:
        print(f"  [{c.detector:10s}] {c.score:8.2f}  {c.field_a} x {c.field_b}  {c.evidence}")

    return candidates


if __name__ == "__main__":
    run()
