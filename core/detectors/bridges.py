from itertools import combinations

from core.schema import Candidate


def detect_bridges(field_counts: dict[str, int], pair_counts: dict[tuple[str, str], int], n_total: int) -> list[Candidate]:
    """Flag field pairs that are under-connected relative to their size.

    For fields A and B, expected co-occurring ("bridge") papers under
    independence is n_A * n_B / N. ignorance density is the fraction of
    those expected bridge papers that are missing, scaled to permille:

        density = max(expected_ab - observed_ab, 0) / expected_ab * 1000

    This is a relative (not absolute) deficit deliberately: at real-world
    scale, field sizes span orders of magnitude (150K to 35M works in our
    OpenAlex pull), and an absolute-count deficit is dominated by whichever
    two fields are individually largest — e.g. materials_science x
    sociology "misses" ~2.2M expected papers in absolute terms despite
    170K+ papers actually connecting them, which is not an ignored pair by
    any reasonable definition. The relative version is scale-invariant: a
    field pair missing 99% of its expected connections is equally alarming
    whether the fields have 500 papers or 5 million.

    High density = two well-studied fields far less connected than their
    size predicts — the signature of a genuinely unasked question, not
    just a small field.

    Takes corpus stats directly (not a paper list) so counts can come from
    a small local sample (tests, core.corpus.count_fields_and_pairs) or
    true global counts from a full literature index — see
    data/openalex_counts.py. Sample-based n_ab systematically undercounts:
    a small independently-drawn-per-field sample is biased against ever
    catching the (rarer) interdisciplinary papers that would prove a
    connection real. Prefer true global counts when available.

    ponytail: this scores every field pair by size and absence alone, so a
    real question (materials_science x pharmacology) and a nonsense pair
    (linguistics x materials_science) can score similarly — co-occurrence
    absence doesn't imply plausibility. Upgrade path: filter candidates by
    a relevance signal (embedding similarity once real abstracts exist) or
    let the bandit narrow the search space instead of scoring every C(n,2)
    pair uniformly.
    """
    if n_total == 0:
        return []

    candidates = []
    for a, b in combinations(sorted(field_counts), 2):
        n_a, n_b = field_counts[a], field_counts[b]
        n_ab = pair_counts.get((a, b), 0)
        expected_ab = n_a * n_b / n_total
        density = max(expected_ab - n_ab, 0) / expected_ab * 1000 if expected_ab > 0 else 0.0
        candidates.append(Candidate(
            field_a=a, field_b=b, detector="bridges", score=density,
            evidence={"n_a": n_a, "n_b": n_b, "n_ab": n_ab, "expected_ab": round(expected_ab, 2)},
        ))
    return candidates
