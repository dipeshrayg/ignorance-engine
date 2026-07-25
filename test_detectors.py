from core.corpus import count_fields_and_pairs
from core.detectors.bridges import detect_bridges
from core.detectors.transitive import detect_transitive_links
from core.ranking import rank
from data.sample_papers import SAMPLE_PAPERS

FIELD_COUNTS, PAIR_COUNTS = count_fields_and_pairs(SAMPLE_PAPERS)
N_TOTAL = len(SAMPLE_PAPERS)


def test_bridges():
    candidates = rank(detect_bridges(FIELD_COUNTS, PAIR_COUNTS, N_TOTAL))

    # relative-deficit scoring ties every zero-observed pair at the max score
    # (each is "100% of expected connections missing") — materials_science x
    # pharmacology must be among that top tier, not necessarily uniquely first.
    top_score = candidates[0].score
    tied_for_top = {frozenset((c.field_a, c.field_b)) for c in candidates if c.score == top_score}
    assert frozenset({"materials_science", "pharmacology"}) in tied_for_top, \
        f"expected the materials_science x pharmacology gap tied for top, got {candidates[0]}"

    connected = next(c for c in candidates if {c.field_a, c.field_b} == {"materials_science", "robotics"})
    assert connected.score == 0, "fields already well-connected should not be flagged as ignored"

    return candidates


def test_transitive():
    candidates = detect_transitive_links(FIELD_COUNTS, PAIR_COUNTS)

    assert len(candidates) == 1, f"expected exactly one ABC candidate in the sample corpus, got {candidates}"
    link = candidates[0]
    assert {link.field_a, link.field_b} == {"robotics", "climate_science"}, link
    assert link.evidence["via"] == "materials_science", link

    return candidates


def test_merged_ranking():
    merged = rank(detect_bridges(FIELD_COUNTS, PAIR_COUNTS, N_TOTAL) + detect_transitive_links(FIELD_COUNTS, PAIR_COUNTS))

    top_two_detectors = {c.detector for c in merged[:2]}
    assert "transitive" in top_two_detectors, (
        "transitive's only candidate has raw score 2 vs bridges' 96.7 — without "
        "per-detector normalization it would be buried dead last instead of ranking near the top"
    )

    return merged


if __name__ == "__main__":
    print("-- bridges --")
    for c in test_bridges():
        print(f"{c.score:6.1f}  {c.field_a:18s} x {c.field_b:18s}  "
              f"({c.evidence['n_a']}+{c.evidence['n_b']} papers, {c.evidence['n_ab']} bridges)")

    print("\n-- transitive (Swanson ABC) --")
    for c in test_transitive():
        print(f"{c.score:6.1f}  {c.field_a:18s} x {c.field_b:18s}  via {c.evidence['via']}")

    print("\n-- merged, normalized ranking --")
    for c in test_merged_ranking():
        print(f"[{c.detector:10s}] {c.field_a} x {c.field_b}")

    print("\nself-check passed")
