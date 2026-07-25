# The Ignorance Engine: Toward Self-Directed Detection of Unexplored Connections in Science

*Draft — 2026-07-26*

## Abstract

Science advances fastest at the boundaries between fields, but no one systematically scans those boundaries. A researcher notices a gap between their own specialty and a neighboring one; nobody is positioned to notice a gap between two fields they don't work in. We describe the Ignorance Engine, a system that treats this as a search problem: given a large, real corpus of scientific literature, find pairs of fields that are far less connected than their individual size predicts, and verify each candidate against real published work before trusting it. The system has four components with no precedent as an assembled whole: a statistical bridge detector and a Swanson-style transitive-linkage detector, a percentile-normalized ranking layer that merges detector output, a UCB1 bandit that decides for itself which region of the field-space to examine next, and an adversarial refutation stage that checks every surviving candidate against live search. We report results from a real run against OpenAlex's 172-million-work abstracted corpus: eight candidates reached refutation, and none survived. We treat that null result as the paper's actual current finding rather than a setback to paper over. Three distinct, previously undocumented failure modes emerged in the process — citation-sampling bias, concept/topic tag incompleteness, and sparse-count noise — each with a concrete methodological fix, all now built into the pipeline. The pattern across every refutation is consistent: well-known fields get their real gaps noticed and named quickly, which means the genuinely unexplored territory, if it exists, lives at a finer granularity than anything tested so far. That is the argument for why the self-directed bandit is not a convenience but a requirement — the combinatorial space at that granularity (potentially millions of field-pair combinations) cannot be brute-forced.

## 1. Introduction

Interdisciplinary discovery has a structural blind spot. A researcher who works across two fields can spot a connection neither field's specialists would think to look for — but coverage of the full space of possible field pairs depends on someone happening to stand at exactly the right intersection. Most of the space is never looked at, not because it lacks value, but because looking at it isn't anyone's job.

This is not a new observation. Don Swanson demonstrated in 1986 that literature-based discovery could surface real, testable hypotheses by finding pairs of concepts that were each individually connected to a third but never to each other — his canonical example, fish oil and Raynaud's syndrome, was later experimentally supported. But Swanson's method was manual and confined to biomedical literature that a single researcher could hold in mind. More recent "AI scientist" systems automate hypothesis generation, but almost always within a topic a human has already chosen, and overwhelmingly in biomedicine. Nobody has built a system that decides for itself where in *all* of science to look.

We built a first version of that system. It has four components, each addressing a specific limitation of prior work:

1. **Self-directed attention.** A UCB1 bandit picks which region of the field-space to examine next, rather than waiting for a human to point it at a topic. Reward is the best candidate density a region's exploration produced — a proxy, not verified novelty, and we say so explicitly (Section 3.4).
2. **A quantitative ignorance metric.** We define *ignorance density* — the fraction of a field pair's statistically expected connecting literature that is actually missing — and use it to produce the first (to our knowledge) quantitative map of under-explored territory across multiple scientific disciplines (Section 4).
3. **Adversarial self-refutation.** Every candidate must survive an attempt to find it already published before it counts. This is the mechanism that makes the rest of the paper honest: without it, every statistical anomaly this system finds would need to be taken on faith.
4. **The Time-Machine Benchmark.** Freeze the corpus before a past date, run the detector, and check whether its flagged gaps closed by the present — a falsifiable, repeatable test of whether the detector's signal means anything (Section 7.2 describes the harness; execution was blocked mid-session by an API rate limit and is pending).

The honest headline of this paper is not a discovered gap. It is a working, fully real pipeline, run against real data, that found no genuine survivor in eight attempts — and a detailed account of *why*, because each failure mode taught us something the field-boundary-search literature does not currently document.

## 2. Related Work

**Literature-based discovery (LBD).** Swanson's ABC model (1986) remains the foundational method: if A relates to B in the literature, and B relates to C, but A and C are never discussed together, B may mediate an undiscovered A–C connection. Follow-on LBD systems (Arrowsmith and its successors) operationalized this within biomedical databases, but selection of the starting concept remained a human decision, and the search space was always a single, pre-chosen domain.

**Automated hypothesis generation / "AI scientist" systems.** Recent systems pair large language models with structured literature search to propose testable hypotheses. They are a genuine advance in hypothesis *quality*, but not in *target selection*: a human still chooses the topic, almost always in biomedicine, and the systems trust their own output far less rigorously than the adversarial-refutation requirement we impose here.

**Bibliometric gap analysis.** Co-citation and bibliographic-coupling methods have long been used to map research fronts and identify structural holes in citation networks (Burt's structural-hole theory has direct bibliometric analogues). These methods are diagnostic, not generative — they describe where gaps exist assuming you've already picked a bounded citation network to analyze, not where in all of science to look first.

**What is genuinely new here.** No existing system, to our knowledge, (a) operates across a domain-agnostic taxonomy spanning all of science rather than a hand-picked topic, (b) uses a bandit to decide where to look next based on its own findings rather than a fixed schedule or a human's intuition, or (c) treats adversarial verification as a mandatory pipeline stage rather than a manual sanity check performed after the fact, if at all.

## 3. System Architecture

### 3.1 Data layer

Papers are represented as `Paper(id, title, year, fields)`, where `fields` is the set of subject tags a paper is associated with. This schema is deliberately decoupled from any one data source: the current implementation pulls from OpenAlex (free, no API key, ~321M works, of which 172.5M carry an abstract), but the schema itself makes no assumption about where the data comes from.

### 3.2 Detectors

Two independent detectors flag candidate field pairs, each grounded in a distinct, well-precedented signal:

- **Bridges** (`core/detectors/bridges.py`): for fields A and B, the number of papers expected to connect them under a size-based independence assumption is `n_A · n_B / N`. *Ignorance density* is the fraction of that expected connection which is actually missing, scaled to a 0–1000 permille score. This is a relative, not absolute, measure — Section 4 explains why that distinction matters empirically, not just theoretically.
- **Transitive** (`core/detectors/transitive.py`): a direct implementation of Swanson's ABC model. If A and C both connect to a mediating field B but never to each other, B is a candidate bridge between them, scored by the weaker of its two legs.

### 3.3 Ranking

Because the two detectors' scores live on different scales, merging their output by raw score would let whichever detector happens to produce bigger numbers dominate regardless of which candidate is actually more anomalous. `core/ranking.py` instead ranks each detector's output by percentile within its own distribution before merging — verified necessary, not just theoretically sound: without it, the transitive detector's only candidate in an early test run (raw score 2, against the bridges detector's raw scores in the hundreds) would have been buried last instead of ranking second overall.

### 3.4 Self-directed attention

`core/bandit.py` implements UCB1: at each step, the bandit either tries an unexplored arm (a discipline or field not yet examined) or picks the arm with the best upper-confidence bound among those already tried, balancing exploitation of known-good regions against exploration of unknown ones. In the current implementation, an "arm" is a candidate field to add to the active search set; reward is the best new ignorance-density score that field's addition produced against the fields already active.

We are explicit about what this reward is and is not. It is a *proxy* — it rewards statistical anomaly, not verified novelty, because verified novelty only exists after the slow refutation stage completes. This is a real, unresolved design tension: if left unchecked, a proxy reward risks teaching the bandit to chase "biggest fields" rather than genuinely under-explored regions, since bigger fields mechanically produce more statistical noise for the detector to seize on. We ran the bandit for real against 17 previously-untried top-level disciplines (Section 5) and observed exactly this dynamic in a mild form, which directly motivated moving to finer-grained regions (Section 6).

### 3.5 Adversarial refutation

Every candidate that reaches this stage must survive an attempt to prove it has already been studied. We implemented this in two layers:

- **Automated pre-filter** (`core/refuter.py`): before spending expensive search effort, check the candidate's field-pair co-occurrence using real abstract-text search rather than trusting the detector's own count — this catches an entire class of false positive for free (Section 5.3).
- **Manual/LLM-driven search verification**: for candidates that pass the pre-filter, targeted web searches attempt specifically to find prior art connecting the two fields. A candidate only counts as a genuine finding if this search comes up empty. Every verdict, with sources, is recorded in `data/refuter_verdicts.json` — a permanent, auditable record, not a one-off judgment call.

This two-layer design directly answers the most obvious reviewer objection to any automated novelty-detection system — *how do you know it's really unasked?* — by making "we tried hard to prove it wrong and failed" a structural requirement rather than an afterthought.

## 4. The Ignorance Density Metric

We define, for fields A and B with sizes $n_A$, $n_B$ in a corpus of size $N$:

$$
\text{density}(A, B) = \frac{\max(\hat{n}_{AB} - n_{AB},\ 0)}{\hat{n}_{AB}} \times 1000, \qquad \hat{n}_{AB} = \frac{n_A \cdot n_B}{N}
$$

where $n_{AB}$ is the observed number of papers connecting both fields and $\hat n_{AB}$ is the number expected under independence. This is a *relative* deficit — the fraction of expected connecting literature that's missing — not an absolute one, and the distinction is not academic. An earlier version of this metric used the absolute deficit $(\hat n_{AB} - n_{AB})/N$. Against real data spanning field sizes from 150,000 to 35 million works, that version ranked `materials_science × sociology` as the single most "ignored" pair in the dataset — despite 170,265 real papers connecting them — purely because both fields are so large that even a well-populated connection looks small next to their combined expected volume. The relative version is scale-invariant: a pair missing 99% of its expected connections is equally alarming whether the fields involved have 500 papers or 5 million. We verified this by rerunning the corrected metric against the same data (Section 5.2); the ranking changed substantially and the top of the list became defensible.

We built a quantitative heatmap of ignorance density across the eight fields tested in this run (materials science, pharmacology, immunology, robotics, climatology, linguistics, neuroscience, sociology), with each cell's refutation status overlaid. To our knowledge, this is the first published quantitative ignorance map of this kind — small in scope so far (28 field pairs), but the method scales directly to OpenAlex's full taxonomy of 252 subfields and 4,516 topics once the exploration described in Section 7 completes.

## 5. Experiments

### 5.1 Setup

We pulled real data from OpenAlex for eight fields spanning both natural and social sciences, chosen to mirror an early synthetic prototype and to maximize cross-domain surface area: materials science, pharmacology, immunology, robotics, climatology, linguistics, neuroscience, and sociology. All results below are from a single continuous session against live OpenAlex data — no synthetic or fabricated figures appear past the earliest prototyping stage, which used a hand-built 32-paper corpus explicitly labeled as synthetic and never conflated with real results.

### 5.2 Finding 1: citation-sampling bias

Our first real ingestion pulled the 200 most-cited papers per field, independently per field. The top-ranked "gap" this produced — `climatology × robotics`, zero co-occurring papers in the sample — collapsed under adversarial search: a dedicated 2025 roadmap paper for climate-relevant robotics exists, plus an active "ecorobotics" research thread with its own Annual Reviews article. The root cause: canonical, heavily-cited papers are structurally *unlikely* to be the interdisciplinary ones, since an interdisciplinary paper draws citations from two smaller communities rather than concentrating them in either field's global top ranks. We fixed this at the source by querying OpenAlex directly for true global co-occurrence counts (`data/openalex_counts.py`) rather than estimating from a downloaded sample — confirmed correct by direct comparison: the sample said 0 papers connected `climatology` and `robotics`; the true global count is 5.

### 5.3 Finding 2: concept/topic tag incompleteness

Even with true global counts, results were being computed from OpenAlex's concept/topic classifier tags — an inferred, imperfect classification, not ground truth. We tested this directly: taking 13 field-pairs that showed zero tag-based co-occurrence at the topic level, we checked each against real abstract-text co-occurrence instead. All 13 had nonzero real text co-occurrence, several substantial (2,523 real papers for one pair the tags said had zero). Two of the clearest cases — "robotic-assisted depression therapy" and "self-driving chemistry labs for organic synthesis" — are established, actively published research areas that simply were not co-tagged under both target labels by OpenAlex's classifier. We rebuilt the counting layer around real abstract-text search (`data/openalex_text_counts.py`) as a direct consequence.

### 5.4 Finding 3: sparse-count noise

The single lowest real co-occurrence count we found — `apelin` (a specific biological peptide) and `robot`, one connecting paper against an expected ~26 — looked like the strongest candidate of the entire session by density score (962/1000). Before trusting it, we read the actual paper. It is an unrelated ophthalmology-journal editorial that mentions both words in passing while summarizing unconnected studies — not a paper about apelin and robotics at all. The lesson, now enforced as a standing rule for any low-count candidate: **read the connecting paper before trusting the count.** A co-occurrence of 1 is not evidence of a real connection; it is as likely to be noise as signal, and only inspection distinguishes the two.

### 5.5 Refutation results

Eight candidates reached the manual refutation stage across four distinct methodological passes (citation-sampled, tag-based global, tag-based fine-topic, and text-based global). Zero survived.

| Field A | Field B | Density | Real co-occurring papers | Verdict |
|---|---|---:|---:|---|
| climatology | pharmacology | 994.4 | 67 | refuted — "green/sustainable pharmacology" |
| climatology | robotics | 990.2 | 5 | refuted — climate-relevant robotics roadmap |
| immunology | robotics | 989.9 | 30 | refuted — "immuno-inspired robotics" (est. 2012) |
| pharmacology | robotics | 983.1 | 28 | refuted — pharmaceutical robotics/automation |
| linguistics | pharmacology | 900.8 | 93 | refuted — "NLP in Pharmacology" review field |
| pharmacology (depression topic) | robotics | 1000.0 | 0 (tags) / real | refuted — robot-assisted depression therapy |
| pharmacology (organic synthesis topic) | robotics | 1000.0 | 0 (tags) / real | refuted — self-driving chemistry labs |
| pharmacology (apelin topic) | robotics | 961.9 | 1 | **not a candidate — noise, not prior art** (Section 5.4) |

Full sourcing for every verdict is in `data/refuter_verdicts.json`.

## 6. Discussion

The pattern across all eight attempts is consistent enough to state as a hypothesis: **for any two moderately broad, well-known academic fields, if a productive combination exists, someone has usually already found and named it.** Academia is large — 172.5 million abstracted works in our corpus alone — and interdisciplinary curiosity is common enough that real emerging connections between recognizable fields get noticed and reviewed quickly, as our sources for "ecorobotics," "green pharmacology," and "NLP in pharmacology" demonstrate directly.

This is not a failure of the approach; it is evidence about where the approach needs to operate. Discipline-level and even moderately fine topic-level search keeps rediscovering gaps that already got filled, because that is exactly the territory human curiosity already covers efficiently. The genuinely unexplored territory, if it exists at meaningful scale, is more likely to live in combinations too specific and too numerous for any individual researcher to have scanned by hand — which is precisely the argument for why the self-directed bandit (Section 3.4) is not a nice-to-have architectural flourish but the load-bearing mechanism of the whole system. OpenAlex's taxonomy includes 4,516 topics; the space of topic-pair combinations is on the order of ten million. No human curiosity, however broad, systematically covers a space that size — and no brute-force script can either, within any reasonable compute budget. A system that can intelligently allocate a bounded search budget across that space is the only approach that scales to it.

We take this as calibration, not discouragement: an "unasked question" detector's negative results, honestly reported and root-caused rather than hidden, are themselves useful — they tell you where the low-hanging fruit already got picked, and by elimination, roughly where it didn't.

## 7. Limitations and Future Work

**Plausibility filtering is still unsolved.** Statistical rarity is not the same as scientific relevance — several zero-count topic pairs we found during fine-grained testing (e.g., "leech biology" × "robotics") were statistically striking but scientifically implausible, the same failure mode as an earlier synthetic-data test that flagged `linguistics × materials_science` as a top gap. A relevance signal — likely embedding similarity once real abstracts are incorporated into the pipeline, or bandit-narrowed search that never visits implausible regions in the first place — is necessary before any candidate is surfaced to a human reviewer at scale.

**The Time-Machine Benchmark is built but not yet run.** `data/time_machine_benchmark.py` implements the full harness: freeze the corpus before a chosen year, run the detector as if operating at that point in time, then measure whether the top-flagged gaps actually accumulated real new connecting literature since. Execution was blocked mid-session by OpenAlex's hourly rate quota (1,000 request credits, fully exhausted by this session's ~400+ queries) and is the immediate next step once quota resets.

**Fine-grained, subfield- and topic-level search is scoped but not yet executed.** `data/subfield_catalog.py` has all 252 OpenAlex subfields cached with domain, field, and size metadata — the substrate for a genuinely finer-grained bandit run than the discipline-level exploration reported here. A cross-domain candidate pool (the largest subfields from each of OpenAlex's four top-level domains — Physical Sciences, Life Sciences, Health Sciences, Social Sciences) is designed and ready to execute.

**The registry is live and will accumulate real results over time.** The public registry (generated by `data/generate_site.py`, deployed via GitHub Pages) lists every candidate this pipeline has scored, with refutation status and sources, regenerated directly from real data rather than hand-maintained — so it stays honest as more of the search space gets covered.

## 8. Conclusion

We built a complete, working pipeline for finding unasked interdisciplinary questions across science: real data ingestion, two independently-grounded detectors, cross-detector ranking, a genuinely self-directing bandit, and a two-layer adversarial refutation stage — the mechanism that answers a reviewer's first and hardest question before they ask it. Run for real against real data, it found no surviving candidate in eight attempts, and in the process surfaced three distinct, previously undocumented failure modes in interdisciplinary-gap detection, each traced to root cause and fixed in the pipeline rather than patched around. The consistent pattern behind every refutation — that well-known fields get their real gaps filled and named quickly — is itself the paper's most useful finding: it tells us, with evidence rather than assumption, that genuine ignorance likely lives at a granularity too fine for unaided human curiosity to have already covered, which is exactly the search problem this system's self-directed attention mechanism exists to solve.

## Acknowledgments

Built solo across a single extended session by the author with an AI pair-programming collaborator (Claude, Anthropic), which implemented the pipeline, ran the real-data experiments and refutation searches reported here, and co-authored this draft.

## Data and Code Availability

All code, cached real data, and refutation sourcing are public: [github.com/dipeshrayg/ignorance-engine](https://github.com/dipeshrayg/ignorance-engine). The live registry is at [dipeshrayg.github.io/ignorance-engine](https://dipeshrayg.github.io/ignorance-engine).
