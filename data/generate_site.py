import json
from datetime import date
from pathlib import Path

from core.detectors.bridges import detect_bridges
from core.detectors.transitive import detect_transitive_links
from core.ranking import rank
from data.openalex_text_counts import load_or_fetch_text_stats

REPO = "https://github.com/dipeshrayg/ignorance-engine"
DOCS = Path(__file__).parent.parent / "docs"
SUBFIELD_STATS_PATH = Path(__file__).parent / "subfield_text_stats.json"


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
    pair_counts = {tuple(k.split("|")): v for k, v in raw["pair_counts"].items()}
    candidates = rank(detect_bridges(field_counts, pair_counts, raw["n_total"])
                       + detect_transitive_links(field_counts, pair_counts))

    questions = []
    for c in candidates:
        ev = c.evidence
        questions.append({
            "a": c.field_a.replace("_", " "), "b": c.field_b.replace("_", " "),
            "pool": "subfield", "detector": c.detector, "density": round(c.score, 1),
            "n_ab": ev.get("n_ab"), "expected": ev.get("expected_ab") or ev.get("n_bc"),
            "status": "untested", "reasoning": None, "sources": [],
        })
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
  .stats-line {{ font-size: 12px; color: light-dark(#898781, #898781); margin-top: 24px; }}

  /* ---- results ---- */
  main {{ max-width: 680px; margin: 0 auto; padding: 4px 20px 80px; }}
  .result-count {{ font-size: 13px; color: light-dark(#898781, #898781); margin: 10px 0 20px; }}
  .result {{ margin-bottom: 26px; }}
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
    <div class="search-box">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
      <input id="q" type="text" placeholder="try a field name — robotics, pharmacology, climate..." autocomplete="off">
    </div>
    <div class="btn-row">
      <button class="btn" id="ask">Question Me</button>
      <button class="btn" id="surprise">Surprise Me</button>
    </div>
    <div class="stats-line">{n_questions} candidate questions indexed · {n_fields} fields · {n_refuted} refuted on live search · {n_survived} survived</div>
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

function render(list, query) {{
  resultsEl.innerHTML = '';
  emptyEl.style.display = list.length ? 'none' : 'block';
  countEl.textContent = query
    ? `About ${{list.length}} result${{list.length === 1 ? '' : 's'}} for "${{query}}"`
    : `${{list.length}} candidate questions, ranked by ignorance density`;

  for (const q of list.slice(0, 40)) {{
    const div = document.createElement('div');
    div.className = 'result';
    const sources = (q.sources || []).map(s => `<a href="${{s}}">source</a>`).join(' · ');
    div.innerHTML = `
      <div class="breadcrumb">ignorance-engine <span class="sep">›</span> ${{q.pool}} <span class="sep">›</span> ${{q.detector}} <span class="sep">›</span> density ${{q.density.toFixed(1)}}/1000</div>
      <h3><a href="#">${{q.a}} &times; ${{q.b}}</a> <span class="badge ${{q.status}}">${{q.status}}</span></h3>
      <p class="snippet">${{snippetFor(q)}}</p>
      ${{sources ? `<div class="sources">${{sources}}</div>` : ''}}
    `;
    resultsEl.appendChild(div);
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


def build():
    questions = build_question_list()
    field_names = {q["a"] for q in questions} | {q["b"] for q in questions}
    n_refuted = sum(1 for q in questions if q["status"] == "refuted")
    n_survived = sum(1 for q in questions if q["status"] == "survived")

    html = PAGE.format(
        n_questions=len(questions), n_fields=len(field_names),
        n_refuted=n_refuted, n_survived=n_survived,
        questions_json=json.dumps(questions),
        repo=REPO, date=date.today().isoformat(),
    )

    DOCS.mkdir(exist_ok=True)
    (DOCS / "index.html").write_text(html, encoding="utf-8")
    print(f"wrote {DOCS / 'index.html'} ({len(questions)} questions, {len(field_names)} fields)")


if __name__ == "__main__":
    build()
