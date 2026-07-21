from itertools import combinations

from core.corpus import count_fields_and_pairs
from core.schema import Candidate, Paper


def detect_bridges(papers: list[Paper]) -> list[Candidate]:
    """Flag field pairs that are under-connected relative to their size.

    For fields A and B, expected co-occurring ("bridge") papers under
    independence is n_A * n_B / N. ignorance density is how many of those
    expected bridge papers are missing, per 1000 papers in the corpus:

        density = max(expected_ab - observed_ab, 0) / N * 1000

    High density = two well-studied fields nobody has connected — the
    signature of a genuinely unasked question, not just a small field.

    ponytail: this scores every field pair by size and absence alone, so a
    real question (materials_science x pharmacology) and a nonsense pair
    (linguistics x materials_science) can score similarly — co-occurrence
    absence doesn't imply plausibility. Upgrade path: filter candidates by
    a relevance signal (embedding similarity once real abstracts exist) or
    let the bandit narrow the search space instead of scoring every C(n,2)
    pair uniformly.
    """
    n_total = len(papers)
    if n_total == 0:
        return []

    field_counts, pair_counts = count_fields_and_pairs(papers)

    candidates = []
    for a, b in combinations(sorted(field_counts), 2):
        n_a, n_b = field_counts[a], field_counts[b]
        n_ab = pair_counts.get((a, b), 0)
        expected_ab = n_a * n_b / n_total
        density = max(expected_ab - n_ab, 0) / n_total * 1000
        candidates.append(Candidate(
            field_a=a, field_b=b, detector="bridges", score=density,
            evidence={"n_a": n_a, "n_b": n_b, "n_ab": n_ab, "expected_ab": round(expected_ab, 2)},
        ))
    return candidates
