from dataclasses import dataclass


@dataclass(frozen=True)
class Paper:
    id: str
    title: str
    year: int
    fields: frozenset[str]  # topic/field tags, e.g. {"materials_science"}


@dataclass
class Candidate:
    """One candidate unasked question: a pair of fields a detector flagged."""
    field_a: str
    field_b: str
    detector: str   # which detector produced this, e.g. "bridges"
    score: float    # ignorance density — higher means more ignored
    evidence: dict  # detector-specific numbers backing the score
