import json
import time
import urllib.parse
import urllib.request

API = "https://api.openalex.org/works"


def abstract_cooccurrence(term_a: str, term_b: str, mailto: str) -> int:
    """True count of papers whose abstract mentions both terms.

    This exists because concept/topic tag co-occurrence undercounts real
    connections: OpenAlex's classifier doesn't reliably co-tag papers that
    are genuinely about both fields (verified 2026-07-25 — "robot" and
    "depression" tag-co-occurrence was 0, text co-occurrence is 1494; see
    data/refuter_verdicts.json). Screening candidates against this BEFORE
    spending real search/refuter effort on them catches tagging-artifact
    false positives for free.
    """
    params = {
        "filter": f"abstract.search:{term_a},abstract.search:{term_b}",
        "per-page": "1",
        "mailto": mailto,
    }
    url = f"{API}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)["meta"]["count"]


def screen(candidates: list[tuple[str, str, str]], mailto: str, delay: float = 0.15) -> list[dict]:
    """candidates: list of (label, term_a, term_b). Returns each with its
    real text co-occurrence count, tagging-artifact pairs first (highest
    count = most obviously a tagging gap, not a real absence).
    """
    results = []
    for label, term_a, term_b in candidates:
        n_text = abstract_cooccurrence(term_a, term_b, mailto)
        results.append({"label": label, "term_a": term_a, "term_b": term_b, "text_cooccurrence": n_text})
        time.sleep(delay)
    return sorted(results, key=lambda r: r["text_cooccurrence"], reverse=True)
