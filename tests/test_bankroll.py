import pytest

from bankroll import (
    reset,
    initialize_from_amount,
    parse_balance,
    reserve_stake,
    release_stake,
    has_available_allocation,
    get_state,
)


@pytest.fixture(autouse=True)
def clear_bankroll():
    reset()
    yield
    reset()


def test_initialize_from_amount_allocates_daily_budget():
    initialize_from_amount(1000)
    state = get_state()
    assert state["starting_balance"] == 1000
    assert state["allocation_total"] > 0
    assert state["allocation_remaining"] == state["allocation_total"]
    assert state["bets_remaining"] == state["max_bets_per_day"]


def test_reserve_and_release_stake():
    initialize_from_amount(5000, max_bets_per_day=5)
    assert has_available_allocation()
    stake = reserve_stake()
    assert stake is not None
    state = get_state()
    assert state["bets_remaining"] == 4
    release_stake(stake)
    state = get_state()
    assert state["bets_remaining"] == 5


def test_parse_balance_handles_symbols():
    assert parse_balance("₦1,234.50") == 1234.5
    assert parse_balance(None) == 0.0
    assert parse_balance("N/A") == 0.0
