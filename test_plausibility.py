from core.plausibility import is_recognized_field, plausibility_score


def test_plausibility():
    # Known plausible pairs -- real, established interdisciplinary
    # connections per data/refuter_verdicts.json's refutation searches.
    ms_pharma = plausibility_score("materials_science", "pharmacology")
    clim_robo = plausibility_score("climatology", "robotics")

    # Known noise/implausible pairs -- real documented false positives.
    # "leech biology and applications" x robotics: paper/ignorance_engine.md
    # Section 7. "apelin" x robotics: refuter_verdicts.json noise_findings
    # (the single co-occurring paper was an unrelated ophthalmology editorial).
    leech_robo = plausibility_score("leech biology and applications", "robotics")
    apelin_robo = plausibility_score("apelin", "robotics")

    assert ms_pharma > 0.5, f"materials_science x pharmacology should clear the 'both real fields' floor, got {ms_pharma}"
    assert clim_robo > 0.5, f"climatology x robotics should clear the 'both real fields' floor, got {clim_robo}"
    assert leech_robo < 0.3, f"leech x robotics (documented false positive) should score low, got {leech_robo}"
    assert apelin_robo < 0.3, f"apelin x robotics (documented noise finding) should score low, got {apelin_robo}"
    assert leech_robo < ms_pharma and leech_robo < clim_robo, "leech pair should score well below real field pairs"
    assert apelin_robo < ms_pharma and apelin_robo < clim_robo, "apelin pair should score well below real field pairs"

    # Known ceiling, tested honestly rather than hidden: linguistics and
    # materials_science are BOTH genuine, well-established academic fields
    # -- the type check correctly says so for each individually -- but the
    # PAIRING is the implausible one. No Wikidata graph-distance signal
    # tried while building this (see core/plausibility.py's ponytail note)
    # can tell "two real fields with no real connection" apart from "two
    # real fields with a real connection". This mechanism does not claim
    # to solve that case, so this asserts what is actually true rather
    # than fabricate a passing threshold for it.
    assert is_recognized_field("linguistics"), "linguistics is a real field -- type check should say so"
    assert is_recognized_field("materials_science"), "materials_science is a real field -- type check should say so"
    ling_ms = plausibility_score("linguistics", "materials_science")
    assert ling_ms > 0.5, (
        "known ceiling, not a bug: both terms are genuine disciplines so the "
        "type-check floor applies regardless of pairing -- this is exactly the "
        "case this mechanism does NOT solve (documented in the module docstring)"
    )

    return {
        "materials_science x pharmacology (plausible)": ms_pharma,
        "climatology x robotics (plausible)": clim_robo,
        "leech x robotics (documented false positive)": leech_robo,
        "apelin x robotics (documented noise finding)": apelin_robo,
        "linguistics x materials_science (known ceiling, not caught)": ling_ms,
    }


if __name__ == "__main__":
    for label, score in test_plausibility().items():
        print(f"{score:.3f}  {label}")
    print("\nself-check passed -- catches the two real false-field noise cases;")
    print("does NOT catch two-genuine-fields-no-real-connection (see ponytail note)")
