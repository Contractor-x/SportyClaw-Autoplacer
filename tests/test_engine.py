import engine


def test_compute_daily_allocation_anchor_points():
    for balance, expected_allocation in engine.DEFAULT_ANCHORS:
        result = engine.compute_daily_allocation(balance)
        assert result.allocation == expected_allocation


def test_compute_daily_allocation_caps_to_balance():
    result = engine.compute_daily_allocation(1000)
    assert result.allocation <= 1000
    assert result.reserve + result.allocation == result.balance


def test_build_stake_plan_divides_across_games():
    plan = engine.build_stake_plan(500, games_today=7, carryover=0)
    assert plan.stake_per_game > 0
    assert plan.used <= 500
    assert round(plan.used + plan.carryover, 2) == 500.0


def test_build_stake_plan_single_game_uses_allocation_and_carryover():
    plan = engine.build_stake_plan(500, games_today=1, carryover=25)
    assert plan.used == 525.0
    assert plan.carryover == 0.0
