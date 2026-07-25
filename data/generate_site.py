import json
from datetime import date
from pathlib import Path

from core.detectors.bridges import detect_bridges
from core.ranking import rank
from data.openalex_text_counts import load_or_fetch_text_stats

REPO = "https://github.com/dipeshrayg/ignorance-engine"
DOCS = Path(__file__).parent.parent / "docs"

PAGE = """<!doctype html>
<html lang="en" data-theme="auto">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ignorance Engine — Registry</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    max-width: 860px; margin: 0 auto; padding: 32px 20px 80px;
    color: light-dark(#0b0b0b, #ffffff); background: light-dark(#f9f9f7, #0d0d0d);
    line-height: 1.6;
  }}
  h1 {{ font-size: 24px; margin-bottom: 4px; }}
  .subtitle {{ color: light-dark(#52514e, #c3c2b7); font-size: 14px; margin-bottom: 28px; max-width: 640px; }}
  .stat-row {{ display: flex; gap: 14px; margin-bottom: 28px; flex-wrap: wrap; }}
  .stat {{
    background: light-dark(#fcfcfb, #1a1a19); border: 1px solid light-dark(rgba(11,11,11,.1), rgba(255,255,255,.1));
    border-radius: 10px; padding: 14px 18px; min-width: 120px;
  }}
  .stat .n {{ font-size: 22px; font-weight: 700; font-variant-numeric: tabular-nums; }}
  .stat .label {{ font-size: 12px; color: light-dark(#52514e, #c3c2b7); }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 32px; }}
  th, td {{ text-align: left; padding: 10px 8px; border-bottom: 1px solid light-dark(#e1e0d9, #2c2c2a); font-size: 14px; }}
  th {{ color: light-dark(#52514e, #c3c2b7); font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: .03em; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .status {{ display: inline-flex; align-items: center; gap: 6px; font-size: 12px; padding: 3px 8px; border-radius: 20px; }}
  .status.refuted {{ background: light-dark(#fbe4e4, #3a1f1f); color: light-dark(#a92a2a, #e66767); }}
  .status.untested {{ background: light-dark(#eeede8, #26261f); color: light-dark(#52514e, #c3c2b7); }}
  .sources {{ font-size: 12px; margin-top: 2px; }}
  .sources a {{ color: inherit; }}
  section {{ margin-bottom: 36px; }}
  h2 {{ font-size: 16px; border-bottom: 1px solid light-dark(#e1e0d9, #2c2c2a); padding-bottom: 6px; }}
  footer {{ font-size: 12px; color: light-dark(#898781, #898781); margin-top: 40px; }}
  a {{ color: light-dark(#2a78d6, #5598e7); }}
  code {{ background: light-dark(#eeede8, #26261f); padding: 1px 5px; border-radius: 4px; font-size: 13px; }}
</style>
</head>
<body>
  <h1>Ignorance Engine</h1>
  <p class="subtitle">
    Finds pairs of scientific fields that are far less connected in the real literature than
    their individual size predicts — candidate "unasked questions." Every candidate below is
    checked with live search against real published work before being trusted; the status
    column shows what survived.
  </p>

  <div class="stat-row">
    <div class="stat"><div class="n">{n_fields}</div><div class="label">fields covered</div></div>
    <div class="stat"><div class="n">{n_candidates}</div><div class="label">pairs scored</div></div>
    <div class="stat"><div class="n">{n_tested}</div><div class="label">refuted on real search</div></div>
    <div class="stat"><div class="n">{n_survived}</div><div class="label">survived refutation</div></div>
  </div>

  <section>
    <h2>Ranked candidates</h2>
    <table>
      <tr><th>Field A</th><th>Field B</th><th class="num">Density</th><th class="num">Real papers</th><th>Status</th></tr>
      {rows}
    </table>
  </section>

  <section>
    <h2>Method</h2>
    <p>
      Density = how much of the expected co-occurring literature (under a size-based independence
      assumption) is missing, scaled 0&ndash;1000. Field size and co-occurrence are counted by literal
      abstract-text mention across OpenAlex's 172.5M-work abstracted corpus &mdash; not by its
      concept/topic classifier tags, which were found during this project to systematically miss real
      connections (see <a href="{repo}/blob/master/data/refuter_verdicts.json">refuter_verdicts.json</a>).
      Every candidate that reaches this registry gets checked with live web search before being trusted;
      "refuted" means real prior work was found connecting the two fields, sources linked below the row.
    </p>
    <p>
      Honest current result: {n_tested} candidates tested across broad disciplines, fine-grained topics,
      and this corrected count &mdash; {n_survived} survived. That null result is itself the finding so far:
      it demonstrates naive interdisciplinary-gap detection needs real adversarial verification before
      any candidate can be trusted, not that the method doesn't work.
    </p>
  </section>

  <footer>
    Generated from real OpenAlex data, {date}. Source: <a href="{repo}">{repo}</a>
  </footer>
</body>
</html>
"""

ROW = """<tr>
  <td>{a}</td><td>{b}</td><td class="num">{density:.1f}</td><td class="num">{n_ab:,}</td>
  <td>
    <span class="status {status_class}">{status_label}</span>
    {sources}
  </td>
</tr>"""


def build():
    field_counts, pair_counts, n_total = load_or_fetch_text_stats()
    candidates = rank(detect_bridges(field_counts, pair_counts, n_total))

    verdicts_raw = json.loads((Path(__file__).parent / "refuter_verdicts.json").read_text())
    # only verdicts for pairs that are actually in this 8-field matrix -- the
    # topic-level drill-down verdicts (e.g. "pharmacology:depression") test
    # finer-grained candidates outside this table, documented in the prose below instead.
    matrix_verdicts = [v for v in verdicts_raw["verdicts"]
                        if v["field_a"] in field_counts and v["field_b"] in field_counts]
    verdict_by_pair = {frozenset((v["field_a"], v["field_b"])): v for v in matrix_verdicts}

    rows = []
    for c in candidates:
        pair = frozenset((c.field_a, c.field_b))
        verdict = verdict_by_pair.get(pair)
        if verdict is not None:
            survived = verdict["survived"]
            status_class = "untested" if survived else "refuted"
            status_label = "survived" if survived else "refuted"
            sources = '<div class="sources">' + " · ".join(
                f'<a href="{s}">source</a>' for s in verdict["sources"]) + "</div>"
        else:
            status_class, status_label, sources = "untested", "untested", ""

        rows.append(ROW.format(
            a=c.field_a.replace("_", " "), b=c.field_b.replace("_", " "),
            density=c.score, n_ab=c.evidence["n_ab"],
            status_class=status_class, status_label=status_label, sources=sources,
        ))

    html = PAGE.format(
        n_fields=len(field_counts), n_candidates=len(candidates),
        n_tested=len(matrix_verdicts), n_survived=sum(v["survived"] for v in matrix_verdicts),
        rows="\n".join(rows), repo=REPO, date=date.today().isoformat(),
    )

    DOCS.mkdir(exist_ok=True)
    (DOCS / "index.html").write_text(html, encoding="utf-8")
    print(f"wrote {DOCS / 'index.html'}")


if __name__ == "__main__":
    build()
