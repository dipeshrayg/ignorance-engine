import math


class UCB1:
    """Upper-confidence-bound bandit: picks which arm (field/concept region)
    to explore next, balancing arms with a strong track record (exploit)
    against arms not yet tried (explore). Untried arms are always picked
    first — standard UCB1 bootstrap.

    ponytail: reward here is a PROXY (best new candidate density an arm's
    pull produced), not "this arm led to a verified real discovery" — real
    reward only comes from refutation, which is slow and manual right now
    (see data/refuter_verdicts.json). If this proxy starts just rewarding
    "biggest field" instead of genuinely under-explored regions, that's the
    circularity risk flagged before building this — revisit reward design.
    """

    def __init__(self, arms: list[str], exploration: float = 2.0):
        self.arms = arms
        self.exploration = exploration
        self.pulls = {a: 0 for a in arms}
        self.total_reward = {a: 0.0 for a in arms}
        self.round = 0

    def select(self) -> str:
        untried = [a for a in self.arms if self.pulls[a] == 0]
        if untried:
            return untried[0]
        self.round += 1

        def ucb(a: str) -> float:
            mean = self.total_reward[a] / self.pulls[a]
            bonus = self.exploration * math.sqrt(math.log(self.round) / self.pulls[a])
            return mean + bonus

        return max(self.arms, key=ucb)

    def update(self, arm: str, reward: float) -> None:
        self.pulls[arm] += 1
        self.total_reward[arm] += reward

    def report(self) -> list[tuple[str, int, float]]:
        """(arm, times pulled, mean reward), best mean reward first."""
        scored = [(a, self.pulls[a], self.total_reward[a] / self.pulls[a] if self.pulls[a] else 0.0)
                  for a in self.arms if self.pulls[a] > 0]
        return sorted(scored, key=lambda t: t[2], reverse=True)
