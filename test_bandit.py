from core.bandit import UCB1


def test_bandit():
    b = UCB1(["good", "bad", "mediocre"])

    # bootstrap: every arm gets tried once, in order, before UCB kicks in
    # (select() only looks "untried" until update() records a pull)
    rewards = {"good": 10.0, "bad": 0.0, "mediocre": 5.0}
    first_three = []
    for _ in range(3):
        arm = b.select()
        first_three.append(arm)
        b.update(arm, rewards[arm])
    assert first_three == ["good", "bad", "mediocre"], first_three

    # after bootstrap, a consistently strong arm should get pulled far more
    # than a consistently weak one over many rounds
    for _ in range(50):
        arm = b.select()
        reward = {"good": 10.0, "bad": 0.0, "mediocre": 5.0}[arm]
        b.update(arm, reward)

    report = b.report()
    assert report[0][0] == "good", f"expected 'good' arm to lead, got {report}"
    assert b.pulls["good"] > b.pulls["bad"], \
        f"strong arm should be pulled more than weak arm: {b.pulls}"

    return report


if __name__ == "__main__":
    for arm, pulls, mean_reward in test_bandit():
        print(f"{arm:10s} pulled {pulls:3d}x  mean reward {mean_reward:.2f}")
    print("\nself-check passed")
