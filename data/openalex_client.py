import json
import time
import urllib.error
import urllib.parse
import urllib.request

MAILTO = "ray-d@ulster.ac.uk"
API = "https://api.openalex.org"
SAFETY_MARGIN = 20  # stop pacing off remaining=0; leave headroom for retries

# Learned from the last response's rate-limit headers. None until the first
# real response arrives, since OpenAlex doesn't expose "credits used" up
# front -- only "credits remaining" after each call.
_state = {"remaining": None, "reset_at": None}


def _throttle() -> None:
    """Self-pace so a long-running script never bursts into a 429. OpenAlex
    gives an hourly credit budget (1000 by default) via X-RateLimit-Remaining
    and X-RateLimit-Reset on every response. Spread whatever's left evenly
    across the time left in the window, rather than firing as fast as
    possible and hoping -- that's exactly what exhausted the budget in under
    4 minutes earlier this session (0.15-0.2s pacing against a budget that
    only sustains ~3.6s/request).
    """
    remaining, reset_at = _state["remaining"], _state["reset_at"]
    if remaining is None:
        time.sleep(0.5)  # conservative default until we've seen real headers
        return

    seconds_left = max(reset_at - time.time(), 1)
    if remaining <= SAFETY_MARGIN:
        print(f"  [openalex] {remaining} credits left, waiting {seconds_left:.0f}s for quota reset...")
        time.sleep(seconds_left + 2)
        _state["remaining"] = None
        _state["reset_at"] = None
        return

    pace = seconds_left / (remaining - SAFETY_MARGIN)
    time.sleep(max(pace, 0.15))


def _request(path: str, params: dict, retries: int = 4) -> dict:
    _throttle()
    url = f"{API}{path}?{urllib.parse.urlencode({**params, 'mailto': MAILTO})}"
    delay = 5
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                remaining = resp.headers.get("X-RateLimit-Remaining")
                reset = resp.headers.get("X-RateLimit-Reset")
                if remaining is not None and reset is not None:
                    _state["remaining"] = int(remaining)
                    _state["reset_at"] = time.time() + int(reset)
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                retry_after = int(e.headers.get("Retry-After", delay))
                print(f"  [openalex] 429 despite pacing -- waiting {retry_after}s and resyncing...")
                time.sleep(retry_after + 2)
                _state["remaining"] = None  # force a resync from the next response's headers
                _state["reset_at"] = None
                delay *= 2
            else:
                raise
    raise RuntimeError("exhausted retries against OpenAlex")


def work_count(filter_value: str = "") -> int:
    params = {"per-page": "1"}
    if filter_value:
        params["filter"] = filter_value
    return _request("/works", params)["meta"]["count"]


def works_search(filter_value: str, per_page: int = 200, page: int = 1, select: str | None = None) -> dict:
    params = {"filter": filter_value, "per-page": str(per_page), "page": str(page)}
    if select:
        params["select"] = select
    return _request("/works", params)


def concepts_search(filter_value: str, per_page: int = 200, page: int = 1, select: str | None = None,
                     sort: str | None = None) -> dict:
    params = {"filter": filter_value, "per-page": str(per_page), "page": str(page)}
    if select:
        params["select"] = select
    if sort:
        params["sort"] = sort
    return _request("/concepts", params)


def subfields_list(per_page: int = 200, page: int = 1, select: str | None = None) -> dict:
    params = {"per-page": str(per_page), "page": str(page)}
    if select:
        params["select"] = select
    return _request("/subfields", params)


def cooccurrence(term_a: str, term_b: str) -> int:
    return work_count(f"abstract.search:{term_a},abstract.search:{term_b}")


def quota_status() -> str:
    if _state["remaining"] is None:
        return "unknown (no request made yet this run)"
    seconds_left = max(_state["reset_at"] - time.time(), 0)
    return f"{_state['remaining']} credits left, resets in {seconds_left:.0f}s"
