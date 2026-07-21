from collections import defaultdict

from core.schema import Candidate


def rank(candidates: list[Candidate]) -> list[Candidate]:
    """Merge candidates from any number of detectors into one ranked list.

    Each detector's score lives on its own scale (bridges: deficit per 1000
    papers; transitive: raw shared-paper count) so raw scores aren't
    comparable across detectors. Rank each detector's candidates by
    percentile within its own output, then merge on that — a detector
    doesn't win just by emitting bigger numbers. Raw c.score is left
    untouched for reporting.
    """
    by_detector = defaultdict(list)
    for c in candidates:
        by_detector[c.detector].append(c)

    scored = []
    for group in by_detector.values():
        group.sort(key=lambda c: c.score)
        n = len(group)
        for i, c in enumerate(group):
            percentile = i / (n - 1) if n > 1 else 1.0
            scored.append((percentile, c))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [c for _, c in scored]
