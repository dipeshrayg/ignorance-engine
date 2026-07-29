"""Self-pacing client for Semantic Scholar's Graph API -- a second, fully
separate data source used to cross-validate the OpenAlex bridge-density
findings (separate corpus, separate rate-limit pool from OpenAlex's, which
this session already exhausted).

API shape verified empirically with curl before writing this:
- /paper/search (relevance search) returned 429 on every attempt from this
  environment's IP, even after waiting -- its unauthenticated quota looks
  like a small pool shared globally and already exhausted by other traffic.
- /paper/search/bulk works instead and returns {"total": N, "token", "data"}.
  total is the match count, analogous to OpenAlex's meta.count.
- An intentionally-unconstrained bulk query (e.g. query="") 400s with
  {"error": "Search returned too many hits (236855826 of 10000000) ..."} --
  that number is the whole S2 corpus size. Used here to get n_total in one
  call since there's no dedicated stats endpoint.
- No X-RateLimit-* headers on either 200 or 429 responses (checked with
  curl -i), unlike OpenAlex -- so pacing here is a fixed conservative
  interval instead of header-driven, plus retry-with-backoff on 429.
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.semanticscholar.org/graph/v1"
MIN_INTERVAL = 3.5  # seconds between requests; conservative vs ~100 req/5min unauth budget

_last_call = 0.0


def _throttle() -> None:
    global _last_call
    wait = MIN_INTERVAL - (time.time() - _last_call)
    if wait > 0:
        time.sleep(wait)
    _last_call = time.time()


def _get(path: str, params: dict, retries: int = 5) -> tuple[dict | None, str | None]:
    """Returns (json_body, error_body). error_body is set only for the 400
    "too many hits" overflow response, whose message carries the corpus
    size we want out of it; every other non-2xx status retries or raises.
    """
    _throttle()
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    delay = 10
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return json.load(resp), None
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code == 400 and "too many hits" in body:
                return None, body
            if e.code == 429 and attempt < retries - 1:
                print(f"  [s2] 429 -- backing off {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, 120)
                continue
            raise RuntimeError(f"S2 {e.code} for {url}: {body}") from e
    raise RuntimeError(f"exhausted retries against Semantic Scholar: {url}")


def bulk_search_total(query: str) -> int:
    """Match count for a bulk-search query -- analogous to OpenAlex's
    work_count. Quote multi-word phrases before calling, e.g. '"materials
    science"'. Join two terms with '+' for AND (co-occurrence), e.g.
    '"materials science"+pharmacology'."""
    body, err = _get("/paper/search/bulk", {"query": query, "limit": "1"})
    if body is not None:
        return body["total"]
    raise RuntimeError(f"unexpected 'too many hits' for real query {query!r}: {err}")


def cooccurrence(term_a: str, term_b: str) -> int:
    return bulk_search_total(f"{term_a}+{term_b}")


def corpus_total() -> int:
    """Total papers in the S2 graph, read off the "too many hits" overflow
    error for a maximally broad (empty) query. There's no dedicated stats
    endpoint, but the search cap (10,000 hits) makes the endpoint report
    the true total whenever a query blows past it."""
    _, err = _get("/paper/search/bulk", {"query": ""})
    m = re.search(r"too many hits \((\d+) of", err or "")
    if not m:
        raise RuntimeError(f"couldn't parse corpus total from: {err}")
    return int(m.group(1))
