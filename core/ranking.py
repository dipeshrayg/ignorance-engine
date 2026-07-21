from core.schema import Candidate


def rank(candidates: list[Candidate]) -> list[Candidate]:
    """Merge candidates from any number of detectors into one ranked list."""
    return sorted(candidates, key=lambda c: c.score, reverse=True)
