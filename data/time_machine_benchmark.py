import json
from itertools import combinations
from pathlib import Path

from core.detectors.bridges import detect_bridges
from data.openalex_client import work_count
from data.openalex_text_counts import FIELD_TERMS

CACHE_PATH = Path(__file__).parent / "time_machine_results.json"


def frozen_stats(before_year: int, field_terms: dict[str, str] = FIELD_TERMS):
    """Field/pair counts using only papers published before `before_year` --
    what the bridges detector would have seen if run at that point in time.
    """
    n_total = work_count(f"has_abstract:true,publication_year:<{before_year}")
    print(f"  corpus before {before_year}: {n_total:,}")

    field_counts = {}
    for key, term in field_terms.items():
        field_counts[key] = work_count(f"abstract.search:{term},publication_year:<{before_year}")
        print(f"  {key}: {field_counts[key]:,}")

    pair_counts = {}
    for (a_key, a_term), (b_key, b_term) in combinations(sorted(field_terms.items()), 2):
        n_ab = work_count(f"abstract.search:{a_term},abstract.search:{b_term},publication_year:<{before_year}")
        pair_counts[(a_key, b_key)] = n_ab

    return field_counts, pair_counts, n_total


def growth_since(term_a: str, term_b: str, since_year: int) -> int:
    """Real new papers connecting two fields, published since `since_year`
    (inclusive). OpenAlex's publication_year filter only supports strict
    `>`/`<`, not `>=`/`<=` (confirmed live: `>=` returns a 400) -- so
    "since Y inclusive" is expressed as `>Y-1`.
    """
    return work_count(f"abstract.search:{term_a},abstract.search:{term_b},publication_year:>{since_year - 1}")


def run_benchmark(freeze_year: int = 2015, field_terms: dict[str, str] = FIELD_TERMS):
    """The Time-Machine Benchmark (upgrade 4 from the pitch): freeze the
    corpus before `freeze_year`, run the detector as if it were that year,
    then check whether the top-flagged gaps got real NEW connecting papers
    published since -- did flagging a gap predict where research actually
    went? Reports every pair's growth, both flagged and not, so the flagged
    group can be compared against the field as a whole rather than cherry-picked.
    """
    print(f"freezing corpus before {freeze_year}...")
    field_counts, pair_counts, n_total = frozen_stats(freeze_year, field_terms)
    candidates = detect_bridges(field_counts, pair_counts, n_total)
    candidates.sort(key=lambda c: c.score, reverse=True)

    results = []
    for c in candidates:
        term_a, term_b = field_terms[c.field_a], field_terms[c.field_b]
        new_papers = growth_since(term_a, term_b, freeze_year)
        results.append({
            "field_a": c.field_a, "field_b": c.field_b,
            "frozen_density": round(c.score, 1), "frozen_n_ab": c.evidence["n_ab"],
            "new_papers_since": new_papers,
        })
        print(f"  {c.field_a} x {c.field_b}: frozen density {c.score:.1f}, {new_papers} new papers since {freeze_year}")

    CACHE_PATH.write_text(json.dumps({"freeze_year": freeze_year, "results": results}, indent=2))
    return results


def verify_syntax() -> bool:
    """Cheap sanity check that the year-range filter operators actually work
    as expected before spending the full ~65-call budget on a real run.
    """
    total = work_count("publication_year:<2015")
    since = work_count("publication_year:>2014")
    all_time = work_count("")
    print(f"before 2015: {total:,}  |  since 2015: {since:,}  |  all time: {all_time:,}")
    ok = abs((total + since) - all_time) / all_time < 0.02
    print("syntax looks right" if ok else "MISMATCH -- filter syntax may be wrong, check before running the full benchmark")
    return ok


if __name__ == "__main__":
    if verify_syntax():
        run_benchmark()
