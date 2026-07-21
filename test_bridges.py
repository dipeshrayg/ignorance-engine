from core.detectors.bridges import detect_bridges
from core.ranking import rank
from data.sample_papers import SAMPLE_PAPERS


def test_bridges():
    candidates = rank(detect_bridges(SAMPLE_PAPERS))

    top = candidates[0]
    assert {top.field_a, top.field_b} == {"materials_science", "pharmacology"}, \
        f"expected the materials_science x pharmacology gap on top, got {top}"

    connected = next(c for c in candidates if {c.field_a, c.field_b} == {"materials_science", "robotics"})
    assert connected.score == 0, "fields already well-connected should not be flagged as ignored"

    return candidates


if __name__ == "__main__":
    for c in test_bridges():
        print(f"{c.score:6.1f}  {c.field_a:18s} x {c.field_b:18s}  "
              f"({c.evidence['n_a']}+{c.evidence['n_b']} papers, {c.evidence['n_ab']} bridges)")
    print("\nself-check passed")
