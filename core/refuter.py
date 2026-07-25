from data.openalex_client import cooccurrence


def abstract_cooccurrence(term_a: str, term_b: str) -> int:
    """True count of papers whose abstract mentions both terms.

    This exists because concept/topic tag co-occurrence undercounts real
    connections: OpenAlex's classifier doesn't reliably co-tag papers that
    are genuinely about both fields (verified 2026-07-25 — "robot" and
    "depression" tag-co-occurrence was 0, text co-occurrence is 1494; see
    data/refuter_verdicts.json). Screening candidates against this BEFORE
    spending real search/refuter effort on them catches tagging-artifact
    false positives for free.
    """
    return cooccurrence(term_a, term_b)


def screen(candidates: list[tuple[str, str, str]]) -> list[dict]:
    """candidates: list of (label, term_a, term_b). Returns each with its
    real text co-occurrence count, tagging-artifact pairs first (highest
    count = most obviously a tagging gap, not a real absence).
    """
    results = [
        {"label": label, "term_a": term_a, "term_b": term_b,
         "text_cooccurrence": abstract_cooccurrence(term_a, term_b)}
        for label, term_a, term_b in candidates
    ]
    return sorted(results, key=lambda r: r["text_cooccurrence"], reverse=True)
