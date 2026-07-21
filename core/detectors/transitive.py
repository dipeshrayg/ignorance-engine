from collections import defaultdict
from itertools import combinations

from core.corpus import count_fields_and_pairs
from core.schema import Candidate, Paper


def detect_transitive_links(papers: list[Paper]) -> list[Candidate]:
    """Swanson-style ABC linkage: A and C both connect to B, but never to each other.

    Classic literature-based discovery (Swanson 1986): if A relates to B and
    B relates to C, but nobody has connected A and C directly, B is a
    candidate mediator for an unexplored A-C link. Score is the weaker of
    the two legs (A-B, B-C) — the bottleneck strength of the implied
    connection.

    ponytail: "connects" means >=1 shared paper. Fine at this corpus size;
    a real corpus needs a minimum-strength threshold or single coincidental
    co-authorships will flood this with noise.
    """
    field_counts, pair_counts = count_fields_and_pairs(papers)

    def weight(a: str, b: str) -> int:
        return pair_counts.get(tuple(sorted((a, b))), 0)

    neighbors = defaultdict(set)
    for a, b in pair_counts:
        neighbors[a].add(b)
        neighbors[b].add(a)

    seen = set()
    candidates = []
    for b, linked in neighbors.items():
        for a, c in combinations(sorted(linked), 2):
            if weight(a, c) > 0:
                continue  # already directly connected, not a gap
            key = tuple(sorted((a, c)))
            if key in seen:
                continue
            seen.add(key)
            n_ab, n_bc = weight(a, b), weight(b, c)
            candidates.append(Candidate(
                field_a=key[0], field_b=key[1], detector="transitive",
                score=min(n_ab, n_bc),
                evidence={"via": b, "n_ab": n_ab, "n_bc": n_bc},
            ))
    return candidates
