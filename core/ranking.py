from core.schema import Candidate


def rank(candidates: list[Candidate]) -> list[Candidate]:
    """Merge candidates from any number of detectors into one ranked list.

    ponytail: sorts on raw score, which is only valid while there's one
    detector. Add per-detector normalization (e.g. percentile rank) before
    a second detector's scores get merged in, or ranking will just reflect
    whichever detector happens to produce bigger numbers.
    """
    return sorted(candidates, key=lambda c: c.score, reverse=True)
