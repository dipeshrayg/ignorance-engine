from collections import defaultdict
from itertools import combinations

from core.schema import Paper


def count_fields_and_pairs(papers: list[Paper]) -> tuple[dict[str, int], dict[tuple[str, str], int]]:
    """Shared corpus stats every detector needs: papers per field, and papers per field pair."""
    field_counts = defaultdict(int)
    pair_counts = defaultdict(int)
    for paper in papers:
        for f in paper.fields:
            field_counts[f] += 1
        for a, b in combinations(sorted(paper.fields), 2):
            pair_counts[(a, b)] += 1
    return field_counts, pair_counts
