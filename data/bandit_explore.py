import json
from pathlib import Path

from core.bandit import UCB1
from data.openalex_client import concepts_search, work_count
from data.openalex_counts import load_or_fetch_real_stats
from data.openalex_ingest import FIELDS

LEVEL0 = {
    "art": "C142362112", "biology": "C86803240", "business": "C144133560",
    "chemistry": "C185592680", "computer_science": "C41008148", "economics": "C162324750",
    "engineering": "C127413603", "environmental_science": "C39432304", "geography": "C205649164",
    "geology": "C127313418", "history": "C95457728", "materials_science": "C192562407",
    "mathematics": "C33923547", "medicine": "C71924100", "philosophy": "C138885662",
    "physics": "C121332964", "political_science": "C17744445", "psychology": "C15744967",
    "sociology": "C144024400",
}

CACHE_PATH = Path(__file__).parent / "bandit_run.json"


def child_concepts(parent_id: str, level: int = 2, limit: int = 5) -> list[tuple[str, str, int]]:
    """(concept_id, display_name, works_count) for a parent's children at `level`, biggest first."""
    data = concepts_search(f"ancestors.id:{parent_id},level:{level}", per_page=limit,
                            select="id,display_name,works_count", sort="works_count:desc")
    return [(r["id"].rsplit("/", 1)[-1], r["display_name"], r["works_count"]) for r in data["results"]]


def explore():
    """Self-directed attention: instead of a human picking which broad
    discipline to check next (which is literally how the original 8 fields
    got chosen), a UCB1 bandit decides — trying every untried discipline
    once (bootstrap), then would favor whichever kept paying off. Reward =
    best relative-deficit density a discipline's new pairs produced against
    the fields already active.
    """
    field_counts, pair_counts, n_total = load_or_fetch_real_stats()
    active_ids = dict(FIELDS)

    arms = [k for k in LEVEL0 if k not in active_ids]
    bandit = UCB1(arms)
    trace = []

    for _ in range(len(arms)):
        arm = bandit.select()
        concept_id = LEVEL0[arm]
        print(f"exploring '{arm}'...")
        n_new = work_count(f"concepts.id:{concept_id}")
        field_counts[arm] = n_new

        best_density = 0.0
        for existing_key, existing_id in list(active_ids.items()):
            a, b = sorted((arm, existing_key))
            n_ab = work_count(f"concepts.id:{concept_id},concepts.id:{existing_id}")
            pair_counts[(a, b)] = n_ab
            expected_ab = field_counts[a] * field_counts[b] / n_total
            if expected_ab > 0:
                density = max(expected_ab - n_ab, 0) / expected_ab * 1000
                best_density = max(best_density, density)

        bandit.update(arm, best_density)
        active_ids[arm] = concept_id
        trace.append({"arm": arm, "reward": round(best_density, 2)})
        print(f"  reward: {best_density:.2f}")

    return bandit, field_counts, pair_counts, n_total, trace


if __name__ == "__main__":
    bandit, field_counts, pair_counts, n_total, trace = explore()

    print("\n-- final ranking, best mean reward first --")
    for arm, pulls, mean_reward in bandit.report():
        print(f"  {arm:22s} mean reward {mean_reward:8.2f}")

    CACHE_PATH.write_text(json.dumps({
        "field_counts": field_counts,
        "pair_counts": {f"{a}|{b}": v for (a, b), v in pair_counts.items()},
        "n_total": n_total,
        "trace": trace,
    }, indent=2))
    print(f"\ncached full run to {CACHE_PATH}")
