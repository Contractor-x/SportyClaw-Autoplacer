import pytest

from bankroll import (
    reset,
    initialize_from_amount,
    parse_balance,
    reserve_chunk,
    release_chunk,
    has_available_chunks,
    get_state,
)


@pytest.fixture(autouse=True)
def clear_bankroll():
    reset()
    yield
    reset()


def test_initialize_from_amount_allocates_quarters():
    initialize_from_amount(1000)
    state = get_state()
    assert state["starting_balance"] == 1000
    assert state["chunk_value"] == 250
    assert state["total_chunks"] == 4
    assert state["chunks_available"] == 4


def test_reserve_and_release_chunk():
    initialize_from_amount(400)
    assert has_available_chunks()
    chunk_value = reserve_chunk()
    assert chunk_value == 100
    state = get_state()
    assert state["chunks_available"] == 3
    release_chunk()
    state = get_state()
    assert state["chunks_available"] == 4


def test_parse_balance_handles_symbols():
    assert parse_balance("₦1,234.50") == 1234.5
    assert parse_balance(None) == 0.0
    assert parse_balance("N/A") == 0.0
