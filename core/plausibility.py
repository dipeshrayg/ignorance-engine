"""Plausibility/relevance filter for candidate field pairs.

WHY THIS EXISTS: core/detectors/bridges.py flags field pairs by size and
co-occurrence absence alone -- it has zero signal for whether a connection
would be scientifically plausible at all. Two real documented failure
modes: an early synthetic-data test ranked linguistics x materials_science
as a top "gap" (see the ponytail comment in bridges.py); real topic-level
testing flagged "leech biology and applications" x robotics as a top
zero-count gap, and separately "apelin" x robotics turned out to be a
single unrelated ophthalmology editorial, not a real connection (both in
data/refuter_verdicts.json's noise_findings). This module screens a
candidate pair BEFORE it's surfaced, using Wikidata as the signal --
independent of both OpenAlex's paper corpus and any embeddings API.

MECHANISM, verified empirically against live data before committing to it
(not assumed to work): resolve each field name to an OpenAlex concept,
take its linked Wikidata ID, then ask Wikidata's free SPARQL endpoint
whether that entity's type chain (P31 instance-of, expanded through P279
subclass-of) reaches any of a small set of generic "this is a recognized
branch of knowledge" root nodes (academic discipline, branch of science,
natural/social science, humanities, interdisciplinary science). This
directly tests a premise the statistical detector never checks: is the
flagged "field" actually a scientific field at all?

Verified against live Wikidata this session:
  - materials science, pharmacology, climatology, robotics, linguistics
    all resolve into that root set (through 1-2 hops of instance-of then
    subclass-of -- pharmacology, for example, is "instance of" medical
    specialty / branch of biology, neither of which is itself a root, but
    both climb to "branch of science" one hop further).
  - "leech biology and applications" resolves (via OpenAlex's own concept
    search) to a non-field Wikidata entity -- not a recognized discipline
    at all. The term itself was never a real field, just a fine-grained
    topic label OpenAlex generated.
  - "apelin" resolves to a protein (Wikidata: instance of protein
    precursor/protein), also not a discipline. Same failure class.

ponytail: this reliably separates "not a real field" cases (the two above)
from real disciplines. It does NOT solve the harder case where BOTH terms
are genuine, well-established disciplines but the PAIRING is still
implausible (linguistics x materials_science). Every Wikidata graph-
distance signal tried this session for THAT case -- shared-ancestor
Jaccard, shortest subclass-of path, direct dual-parent "bridge concept"
search, even Wikipedia summary-text and full-text overlap -- either failed
to separate it from real connections or actively pointed the wrong way:
linguistics x materials_science scored a HIGHER shared-ancestor Jaccard
(0.82) than the real materials_science x pharmacology connection (0.81),
and climatology x robotics (a real, refuted-as-genuine connection) sits
taxonomically FARTHER apart (shortest path 7) than the fake linguistics
pair (5). Taxonomic closeness just doesn't track real-world
interdisciplinary relevance -- genuine bridges often span distant
branches, and nearby branches are often still unconnected. Upgrade path:
curated named-subfield data (does a "computational linguistics"-style
bridge term exist for this pair?) or real abstract-text embeddings once
the corpus has them -- not more Wikidata graph traversal.

ponytail: uses its own minimal, bounded-retry HTTP calls rather than
data/openalex_client.py's shared paced client. That client's pacing model
spreads N *known* remaining calls evenly across the rest of an hourly
window -- right for a bulk corpus-counting script, wrong here: it shares
global module state, so a plausibility check made moments after some
other bulk fetch exhausted the hourly quota would inherit that state and
could block for up to an hour before running a single lookup. A one-off
screening call should fail fast (or degrade to "unknown") instead.
"""

import functools
import json
import time
import urllib.error
import urllib.parse
import urllib.request

MAILTO = "ray-d@ulster.ac.uk"
OPENALEX_API = "https://api.openalex.org"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
USER_AGENT = f"ignorance-engine-plausibility/0.1 ({MAILTO})"

# Generic Wikidata nodes meaning "this is a recognized branch of
# knowledge" -- found by inspecting what five real, unrelated fields
# (materials science, pharmacology, climatology, robotics, linguistics)
# actually resolve to this session, not hand-picked per test pair.
FIELD_TYPE_ROOTS = frozenset({
    "Q11862829",  # academic discipline
    "Q2465832",   # branch of science
    "Q12015335",  # technical sciences
    "Q34749",     # social science
    "Q80083",     # humanities
    "Q336",       # science
    "Q7991",      # natural science
    "Q1665984",   # interdisciplinary science
})


def _get_json(url: str, headers: dict, retries: int = 4) -> dict | None:
    """Bounded-retry GET with 429 backoff. Returns None on any failure
    (network down, exhausted retries) rather than raising -- a plausibility
    check degrading to "unknown" beats crashing the pipeline that called it.
    """
    req = urllib.request.Request(url, headers=headers)
    delay = 3
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                wait = int(e.headers.get("Retry-After", delay))
                time.sleep(wait + 1)
                delay *= 2
            else:
                return None
        except urllib.error.URLError:
            return None
    return None


@functools.lru_cache(maxsize=256)
def resolve_wikidata_id(field: str) -> str | None:
    """Field label -> its best-match Wikidata QID, via OpenAlex's own
    concept search (each concept links to Wikidata when one exists).
    "materials_science" and "pharmacology:depression" style labels get
    their underscores/colons turned back into spaces first.

    OpenAlex's relevance ranking is not reliable enough to trust hits[0]
    blindly: searching "robotics" returns "Robot" (the device concept)
    ranked ABOVE "Robotics" (the discipline) -- verified live, not a
    hypothetical. Fetch a few candidates and prefer an exact (case-
    insensitive) name match over OpenAlex's own ranking; this is a
    general string-matching rule, not a lookup table of known terms, so
    it still generalizes to fields not tested here.
    """
    term = field.replace("_", " ").replace(":", " ")
    params = {
        "filter": f"display_name.search:{term}",
        "per-page": "5",
        "select": "display_name,wikidata",
        "mailto": MAILTO,
    }
    url = f"{OPENALEX_API}/concepts?{urllib.parse.urlencode(params)}"
    data = _get_json(url, {"User-Agent": USER_AGENT})
    if data is None:
        return None
    hits = [h for h in data.get("results", []) if h.get("wikidata")]
    if not hits:
        return None
    exact = next((h for h in hits if h["display_name"].lower() == term.lower()), None)
    best = exact or hits[0]
    return best["wikidata"].rsplit("/", 1)[-1]


@functools.lru_cache(maxsize=256)
def _field_closure(qid: str) -> frozenset[str]:
    """All Wikidata IDs reachable from qid via subclass-of (P279*), plus
    the subclass-of closure of qid's instance-of (P31) types. Two-part
    because many real disciplines aren't directly P279-linked to
    "academic discipline" -- they're an *instance of* something narrower
    (pharmacology: "medical specialty") that itself climbs there via
    subclass-of. Closures for real fields run ~45-75 nodes; cheap.
    """
    query = f"""SELECT DISTINCT ?anc WHERE {{
      {{ wd:{qid} wdt:P279* ?anc }}
      UNION
      {{ wd:{qid} wdt:P31 ?t . ?t wdt:P279* ?anc }}
    }}"""
    url = f"{WIKIDATA_SPARQL}?{urllib.parse.urlencode({'query': query, 'format': 'json'})}"
    data = _get_json(url, {"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"})
    if data is None:
        return frozenset()
    return frozenset(b["anc"]["value"].rsplit("/", 1)[-1] for b in data["results"]["bindings"])


def is_recognized_field(field: str) -> bool:
    """True if `field` resolves to a Wikidata entity that is itself, or a
    subclass/instance of, a recognized branch of knowledge. False both for
    "couldn't resolve at all" and "resolved to something that isn't a
    field" (a protein, a species, a slang term) -- both are red flags for
    a candidate that's supposed to be a scientific discipline.
    """
    qid = resolve_wikidata_id(field)
    if qid is None:
        return False
    return bool(_field_closure(qid) & FIELD_TYPE_ROOTS)


def _closure_jaccard(field_a: str, field_b: str) -> float:
    qa, qb = resolve_wikidata_id(field_a), resolve_wikidata_id(field_b)
    if qa is None or qb is None:
        return 0.0
    ca, cb = _field_closure(qa), _field_closure(qb)
    union = ca | cb
    return len(ca & cb) / len(union) if union else 0.0


def plausibility_score(field_a: str, field_b: str) -> float:
    """0..1 estimate of whether field_a x field_b could plausibly be a
    real scientific connection, independent of any co-occurrence count.

    Dominated by whether BOTH terms resolve to a genuine Wikidata "branch
    of knowledge" entity (is_recognized_field) -- that's the validated,
    generalizing part of this signal (see module docstring). The Wikidata
    subclass-closure Jaccard is folded in only as a small, explicitly-weak
    secondary nudge within whichever tier the type check assigns -- see
    the ponytail note above for why it can't be trusted to rank two
    genuine disciplines against each other.
    """
    both_fields = is_recognized_field(field_a) and is_recognized_field(field_b)
    jaccard = _closure_jaccard(field_a, field_b)
    if both_fields:
        return round(0.55 + 0.40 * jaccard, 3)
    return round(0.05 + 0.15 * jaccard, 3)
