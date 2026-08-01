import json
import urllib.parse
from datetime import date
from pathlib import Path

from core.detectors.bridges import detect_bridges
from core.detectors.transitive import detect_transitive_links
from core.ranking import rank
from data.openalex_text_counts import FIELD_TERMS, load_or_fetch_text_stats

REPO = "https://github.com/dipeshrayg/ignorance-engine"
DOCS = Path(__file__).parent.parent / "docs"
SUBFIELD_STATS_PATH = Path(__file__).parent / "subfield_text_stats.json"

# Below this, "expected" connecting papers is under 1 -- the density formula
# still assigns these a 1000/1000 score (100% of expected is missing), but
# "we expected 0.04 papers and found 0" isn't a finding, it's an artifact of
# a small field times a small field. Filtering these out rather than letting
# a technically-true-but-meaningless score masquerade as a strong candidate.
MIN_EXPECTED_TO_SURFACE = 1.0


def _openalex_search_url(term_a: str, term_b: str) -> str:
    """Real, clickable OpenAlex works-search URL for a field pair -- lets a
    visitor see the actual papers behind a count with one click instead of
    taking the number on faith. Verified live: the OpenAlex web UI accepts
    the same filter syntax as its API even though it 403s for non-browser
    tools like curl (bot detection, not a URL-format problem)."""
    filter_value = f"abstract.search:{term_a},abstract.search:{term_b}"
    return f"https://openalex.org/works?page=1&filter={urllib.parse.quote(filter_value, safe='')}"


def _questions_from_discipline_matrix() -> list[dict]:
    field_counts, pair_counts, n_total = load_or_fetch_text_stats()
    candidates = rank(detect_bridges(field_counts, pair_counts, n_total))

    verdicts_raw = json.loads((Path(__file__).parent / "refuter_verdicts.json").read_text())
    # only verdicts for pairs actually in this 8-field matrix -- the topic-level
    # drill-down verdicts (e.g. "pharmacology:depression") tested finer-grained
    # candidates outside this matrix and aren't matchable to a row here.
    matrix_verdicts = {frozenset((v["field_a"], v["field_b"])): v for v in verdicts_raw["verdicts"]
                        if v["field_a"] in field_counts and v["field_b"] in field_counts}

    questions = []
    for c in candidates:
        verdict = matrix_verdicts.get(frozenset((c.field_a, c.field_b)))
        questions.append({
            "a": c.field_a.replace("_", " "), "b": c.field_b.replace("_", " "),
            "pool": "discipline", "detector": c.detector, "density": round(c.score, 1),
            "n_ab": c.evidence["n_ab"], "expected": c.evidence["expected_ab"],
            "url": _openalex_search_url(FIELD_TERMS[c.field_a], FIELD_TERMS[c.field_b]),
            "status": "untested" if verdict is None else ("survived" if verdict["survived"] else "refuted"),
            "reasoning": verdict["reasoning"] if verdict else None,
            "sources": verdict["sources"] if verdict else [],
        })
    return questions


def _questions_from_subfield_pool() -> list[dict]:
    if not SUBFIELD_STATS_PATH.exists():
        return []
    raw = json.loads(SUBFIELD_STATS_PATH.read_text())
    field_counts = raw["field_counts"]
    field_terms = raw["field_terms"]
    pair_counts = {tuple(k.split("|")): v for k, v in raw["pair_counts"].items()}
    candidates = rank(detect_bridges(field_counts, pair_counts, raw["n_total"])
                       + detect_transitive_links(field_counts, pair_counts))

    questions, dropped = [], 0
    for c in candidates:
        ev = c.evidence
        expected = ev.get("expected_ab") or ev.get("n_bc")
        if expected is not None and expected < MIN_EXPECTED_TO_SURFACE:
            dropped += 1
            continue
        questions.append({
            "a": c.field_a.replace("_", " "), "b": c.field_b.replace("_", " "),
            "pool": "subfield", "detector": c.detector, "density": round(c.score, 1),
            "n_ab": ev.get("n_ab"), "expected": expected,
            "url": _openalex_search_url(field_terms[c.field_a], field_terms[c.field_b]),
            "status": "untested", "reasoning": None, "sources": [],
        })
    if dropped:
        print(f"  dropped {dropped} subfield candidates with expected<{MIN_EXPECTED_TO_SURFACE} "
              f"(statistically vacuous, not a real finding)")
    return questions


def build_question_list() -> list[dict]:
    questions = _questions_from_discipline_matrix() + _questions_from_subfield_pool()
    questions.sort(key=lambda q: -q["density"])
    return questions


PAGE = """<!doctype html>
<html lang="en" data-theme="auto">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ignorance Engine</title>
<style>
  :root {{ color-scheme: light dark; }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    margin: 0; color: light-dark(#0b0b0b, #ffffff); background: light-dark(#f9f9f7, #0d0d0d);
    line-height: 1.5; min-height: 100vh;
  }}
  a {{ color: light-dark(#2a78d6, #5598e7); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}

  /* ---- hero / search ---- */
  .hero {{
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    padding: 14vh 20px 40px; text-align: center; transition: padding 0.15s;
  }}
  .hero.compact {{ padding: 28px 20px 20px; }}
  .logo {{ font-size: 52px; font-weight: 700; letter-spacing: -0.02em; margin: 0 0 6px; }}
  .logo .accent {{ color: light-dark(#2a78d6, #5598e7); }}
  .tagline {{ color: light-dark(#52514e, #c3c2b7); font-size: 15px; margin: 0 0 28px; }}
  .search-box {{
    width: 100%; max-width: 600px; display: flex; align-items: center; gap: 10px;
    background: light-dark(#fcfcfb, #1a1a19); border: 1px solid light-dark(rgba(11,11,11,.14), rgba(255,255,255,.14));
    border-radius: 26px; padding: 12px 20px; box-shadow: 0 1px 4px light-dark(rgba(11,11,11,.06), rgba(0,0,0,.3));
  }}
  .search-box:focus-within {{ border-color: light-dark(#2a78d6, #5598e7); box-shadow: 0 1px 8px light-dark(rgba(42,120,214,.2), rgba(85,152,229,.25)); }}
  .search-box svg {{ flex: none; opacity: 0.5; }}
  .search-box input {{
    flex: 1; border: none; outline: none; background: transparent; font-size: 16px;
    color: light-dark(#0b0b0b, #ffffff); font-family: inherit;
  }}
  .btn-row {{ display: flex; gap: 12px; margin-top: 22px; }}
  .btn {{
    font-family: inherit; font-size: 13px; padding: 9px 18px; border-radius: 6px; border: none; cursor: pointer;
    background: light-dark(#eeede8, #26261f); color: light-dark(#3c3b38, #e3e2dc);
  }}
  .btn:hover {{ background: light-dark(#e1e0d9, #2f2f28); }}

  /* ---- honest status banner: the actual finding, not hidden in fine print ---- */
  .status-banner {{
    width: 100%; max-width: 600px; margin-bottom: 20px; padding: 14px 18px; border-radius: 12px;
    text-align: left; border: 1px solid;
  }}
  .status-banner.info {{ background: light-dark(#eaf2fb, #132132); border-color: light-dark(#bcd6f2, #1c3a5c); }}
  .status-banner.good {{ background: light-dark(#dff3df, #0f2e0f); border-color: light-dark(#7cc47c, #2e6b2e); }}
  .status-banner-main {{ font-size: 14px; font-weight: 700; margin-bottom: 3px; }}
  .status-banner-sub {{ font-size: 12.5px; color: light-dark(#52514e, #c3c2b7); }}
  .status-banner a {{ font-weight: 600; }}

  /* ---- results ---- */
  main {{ max-width: 680px; margin: 0 auto; padding: 4px 20px 80px; }}
  .result-count {{ font-size: 13px; color: light-dark(#898781, #898781); margin: 10px 0 20px; }}
  .result {{ margin-bottom: 26px; }}
  .result.survived {{ background: light-dark(#f2fbf2, #0f2413); border: 1px solid light-dark(#7cc47c, #2e6b2e); border-radius: 10px; padding: 14px 16px; }}
  .result .breadcrumb {{ font-size: 13px; color: light-dark(#4d7c2f, #7cb85f); margin-bottom: 2px; }}
  .result .breadcrumb .sep {{ color: light-dark(#898781, #898781); margin: 0 4px; }}
  .result h3 {{ margin: 0 0 4px; font-size: 19px; font-weight: 400; }}
  .result h3 a {{ color: light-dark(#1a0dab, #8ab4f8); }}
  .result .snippet {{ font-size: 14px; color: light-dark(#3c3b38, #c3c2b7); margin: 0 0 6px; }}
  .badge {{ display: inline-block; font-size: 11px; padding: 2px 9px; border-radius: 20px; font-weight: 600; letter-spacing: .02em; text-transform: uppercase; }}
  .badge.refuted {{ background: light-dark(#fbe4e4, #3a1f1f); color: light-dark(#a92a2a, #e66767); }}
  .badge.untested {{ background: light-dark(#eeede8, #26261f); color: light-dark(#52514e, #c3c2b7); }}
  .badge.survived {{ background: light-dark(#dff3df, #123a12); color: light-dark(#0ca30c, #4ad24a); }}
  .sources {{ font-size: 12px; margin-top: 4px; }}
  .pinned-header {{ font-size: 13px; font-weight: 700; color: light-dark(#0ca30c, #4ad24a); margin: 0 0 10px; }}
  .empty-state {{ text-align: center; color: light-dark(#898781, #898781); padding: 60px 20px; font-size: 14px; }}

  footer {{ max-width: 680px; margin: 40px auto 0; padding: 20px 20px 40px; font-size: 12px; color: light-dark(#898781, #898781); border-top: 1px solid light-dark(#e1e0d9, #2c2c2a); }}
  footer p {{ max-width: 640px; }}
  code {{ background: light-dark(#eeede8, #26261f); padding: 1px 5px; border-radius: 4px; font-size: 12px; }}
</style>
</head>
<body>
  <div class="hero" id="hero">
    <div class="logo">Ignorance<span class="accent">Engine</span></div>
    <p class="tagline">a search engine for questions science hasn't asked yet</p>
    <div class="status-banner {banner_class}">
      <div class="status-banner-main">{banner_headline}</div>
      <div class="status-banner-sub">{banner_detail} <a href="{repo}/blob/master/paper/ignorance_engine.md#5-experiments">read why →</a></div>
    </div>
    <div class="search-box">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
      <input id="q" type="text" placeholder="try a field name — robotics, pharmacology, climate..." autocomplete="off">
    </div>
    <div class="btn-row">
      <button class="btn" id="ask">Question Me</button>
      <button class="btn" id="surprise">Surprise Me</button>
    </div>
  </div>

  <main>
    <div class="result-count" id="count"></div>
    <div id="results"></div>
    <div class="empty-state" id="empty" style="display:none">no fields match that search</div>
  </main>

  <footer>
    <p>
      Density = how much of the expected co-occurring literature (under a size-based independence
      assumption) is missing, scaled 0&ndash;1000, counted by literal abstract-text mention across
      OpenAlex's 172.5M-work abstracted corpus. Every candidate is checked with live search before
      being trusted — "refuted" means real prior work was found; see
      <a href="{repo}/blob/master/data/refuter_verdicts.json">refuter_verdicts.json</a> for sources,
      and <a href="{repo}/blob/master/paper/ignorance_engine.md">the paper</a> for full methodology.
    </p>
    <p>Generated from real data, {date}. Source: <a href="{repo}">{repo}</a></p>
  </footer>

<script>
const QUESTIONS = {questions_json};

const heroEl = document.getElementById('hero');
const inputEl = document.getElementById('q');
const resultsEl = document.getElementById('results');
const countEl = document.getElementById('count');
const emptyEl = document.getElementById('empty');

function snippetFor(q) {{
  const base = `${{q.n_ab.toLocaleString()}} real papers connect these fields (expected ~${{Math.round(q.expected).toLocaleString()}} if unrelated-by-size).`;
  if (q.status === 'refuted') return `${{base}} Refuted — ${{q.reasoning}}`;
  if (q.status === 'survived') return `${{base}} Survived adversarial search — no prior work found yet.`;
  return `${{base}} Not yet checked against live search.`;
}}

function resultCard(q, pinned) {{
  const div = document.createElement('div');
  div.className = pinned ? 'result survived' : 'result';
  const sources = (q.sources || []).map(s => `<a href="${{s}}" target="_blank" rel="noopener">source</a>`).join(' · ');
  div.innerHTML = `
    <div class="breadcrumb">ignorance-engine <span class="sep">›</span> ${{q.pool}} <span class="sep">›</span> ${{q.detector}} <span class="sep">›</span> density ${{q.density.toFixed(1)}}/1000</div>
    <h3><a href="${{q.url}}" target="_blank" rel="noopener">${{q.a}} &times; ${{q.b}}</a> <span class="badge ${{q.status}}">${{q.status}}</span></h3>
    <p class="snippet">${{snippetFor(q)}}</p>
    ${{sources ? `<div class="sources">${{sources}}</div>` : ''}}
  `;
  return div;
}}

function render(list, query) {{
  resultsEl.innerHTML = '';
  emptyEl.style.display = list.length ? 'none' : 'block';
  countEl.textContent = query
    ? `About ${{list.length}} result${{list.length === 1 ? '' : 's'}} for "${{query}}"`
    : `${{list.length}} candidate questions, ranked by ignorance density`;

  // survived candidates are never buried in the ranked list -- pinned above
  // everything else, unmissable, the moment one exists.
  const survived = list.filter(q => q.status === 'survived');
  const rest = list.filter(q => q.status !== 'survived');

  if (survived.length) {{
    const header = document.createElement('div');
    header.className = 'pinned-header';
    header.textContent = `⭐ ${{survived.length}} candidate${{survived.length === 1 ? '' : 's'}} survived verification — pinned above the rest`;
    resultsEl.appendChild(header);
    survived.forEach(q => resultsEl.appendChild(resultCard(q, true)));
  }}

  for (const q of rest.slice(0, 40)) {{
    resultsEl.appendChild(resultCard(q, false));
  }}
}}

function search(query) {{
  const term = query.trim().toLowerCase();
  heroEl.classList.toggle('compact', term.length > 0);
  if (!term) {{ render(QUESTIONS, ''); return; }}
  const matches = QUESTIONS.filter(q =>
    q.a.toLowerCase().includes(term) || q.b.toLowerCase().includes(term) ||
    q.status.includes(term) || q.pool.includes(term)
  );
  render(matches, query.trim());
}}

inputEl.addEventListener('input', () => search(inputEl.value));
document.getElementById('ask').addEventListener('click', () => search(inputEl.value));
document.getElementById('surprise').addEventListener('click', () => {{
  const pick = QUESTIONS[Math.floor(Math.random() * Math.min(QUESTIONS.length, 15))];
  inputEl.value = pick.a;
  search(pick.a);
  document.querySelector('.result')?.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
}});

render(QUESTIONS, '');
</script>
</body>
</html>
"""


def _status_banner(n_tested: int, n_refuted: int, n_survived: int, n_untested: int) -> tuple[str, str, str]:
    """(css_class, headline, detail) for the honest-status banner -- the
    actual current finding, stated plainly near the top of the page rather
    than left for a visitor to compute from a table of badges themselves."""
    if n_survived > 0:
        return (
            "good",
            f"{n_survived} candidate{'s' if n_survived != 1 else ''} survived adversarial verification",
            f"Checked against live search, no prior work found for {'it' if n_survived == 1 else 'them'}. "
            f"{n_refuted} others were refuted; {n_untested} more haven't been checked yet.",
        )
    return (
        "info",
        f"Honest status: 0 of {n_tested} tested candidates have survived so far",
        f"Every candidate checked against live search turned out to have real prior work "
        f"({n_refuted} refuted). {n_untested} more below haven't been checked yet — the search isn't over.",
    )


def build():
    questions = build_question_list()
    n_refuted = sum(1 for q in questions if q["status"] == "refuted")
    n_survived = sum(1 for q in questions if q["status"] == "survived")
    n_untested = sum(1 for q in questions if q["status"] == "untested")
    n_tested = n_refuted + n_survived
    banner_class, banner_headline, banner_detail = _status_banner(n_tested, n_refuted, n_survived, n_untested)

    html = PAGE.format(
        banner_class=banner_class, banner_headline=banner_headline, banner_detail=banner_detail,
        questions_json=json.dumps(questions),
        repo=REPO, date=date.today().isoformat(),
    )

    field_names = {q["a"] for q in questions} | {q["b"] for q in questions}
    DOCS.mkdir(exist_ok=True)
    (DOCS / "index.html").write_text(html, encoding="utf-8")
    print(f"wrote {DOCS / 'index.html'} ({len(questions)} questions, {len(field_names)} fields)")


if __name__ == "__main__":
    build()
