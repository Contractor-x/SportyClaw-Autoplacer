import logging
import re
from dataclasses import dataclass

from engine import compute_daily_allocation, MAX_BETS_PER_DAY

logger = logging.getLogger(__name__)


@dataclass
class _BankrollState:
    starting_balance: float = 0.0
    allocation_total: float = 0.0
    allocation_remaining: float = 0.0
    max_bets_per_day: int = MAX_BETS_PER_DAY
    bets_remaining: int = 0


_state = _BankrollState()


def _normalize_amount(value: float) -> float:
    return round(value, 2)


def parse_balance(raw: str | None) -> float:
    if not raw:
        return 0.0
    cleaned = re.sub(r"[^0-9.]", "", raw)
    if not cleaned:
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        logger.warning("Unable to parse balance string '%s'", raw)
        return 0.0


def reset() -> None:
    _state.starting_balance = 0.0
    _state.allocation_total = 0.0
    _state.allocation_remaining = 0.0
    _state.max_bets_per_day = MAX_BETS_PER_DAY
    _state.bets_remaining = 0

## Computes a daily allocation cap from the account balance and tracks how much can be used today.
## Each bet reserves a stake from the remaining allocation, with a max number of bets per day.
def initialize_from_amount(amount: float, max_bets_per_day: int = MAX_BETS_PER_DAY) -> None:
    amount = max(0.0, float(amount))
    allocation = compute_daily_allocation(amount).allocation
    _state.starting_balance = _normalize_amount(amount)
    _state.allocation_total = _normalize_amount(allocation)
    _state.allocation_remaining = _normalize_amount(allocation)
    _state.max_bets_per_day = max(0, int(max_bets_per_day))
    _state.bets_remaining = _state.max_bets_per_day if allocation > 0 else 0
    logger.info(
        "Bankroll initialized with ₦%0.2f; allocation ₦%0.2f across %s max bets",
        amount,
        allocation,
        _state.max_bets_per_day,
    )

def _to_kobo(amount: float) -> int:
    return max(0, int(round(amount * 100)))


def _from_kobo(kobo: int) -> float:
    return round(kobo / 100, 2)


def reserve_stake() -> float | None:
    if _state.allocation_remaining <= 0 or _state.bets_remaining <= 0:
        return None

    remaining_kobo = _to_kobo(_state.allocation_remaining)
    if remaining_kobo <= 0:
        return None

    if _state.bets_remaining == 1:
        stake_kobo = remaining_kobo
    else:
        stake_kobo = remaining_kobo // _state.bets_remaining
        if stake_kobo <= 0:
            return None

    stake = _from_kobo(stake_kobo)
    _state.allocation_remaining = _normalize_amount(_state.allocation_remaining - stake)
    _state.bets_remaining = max(0, _state.bets_remaining - 1)
    logger.info(
        "Reserved ₦%0.2f stake, ₦%0.2f remaining (%s bets left)",
        stake,
        _state.allocation_remaining,
        _state.bets_remaining,
    )
    return stake


def release_stake(amount: float) -> None:
    amount = max(0.0, float(amount))
    if amount <= 0:
        return
    _state.allocation_remaining = _normalize_amount(_state.allocation_remaining + amount)
    _state.bets_remaining = min(_state.max_bets_per_day, _state.bets_remaining + 1)
    _state.allocation_remaining = min(_state.allocation_remaining, _state.allocation_total)
    logger.info(
        "Released ₦%0.2f stake, ₦%0.2f remaining (%s bets left)",
        amount,
        _state.allocation_remaining,
        _state.bets_remaining,
    )


def has_available_allocation() -> bool:
    return _state.allocation_remaining > 0 and _state.bets_remaining > 0

## gets the starting balance, daily allocation, remaining allocation, and remaining bets for the day.
def get_state() -> dict:
    return {
        "starting_balance": _state.starting_balance,
        "allocation_total": _state.allocation_total,
        "allocation_remaining": _state.allocation_remaining,
        "bets_remaining": _state.bets_remaining,
        "max_bets_per_day": _state.max_bets_per_day,
        "reserve": _normalize_amount(_state.starting_balance - _state.allocation_total),
    }
