import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class _BankrollState:
    starting_balance: float = 0.0
    chunk_value: float = 0.0
    chunks_available: int = 0
    total_chunks: int = 0


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
    _state.chunk_value = 0.0
    _state.chunks_available = 0
    _state.total_chunks = 0

## Splits my money into 4 equal parts (quarters) and tracks how many are currently reserved for bets. When a bet is placed, it reserves one quarter. If the bet wins, that quarter is considered profit and not released back. If the bet loses, that quarter is considered lost and also not released back. This way I can manage risk by only allowing a certain portion of my bankroll to be used at any time.
def initialize_from_amount(amount: float) -> None:
    amount = max(0.0, float(amount))
    _state.starting_balance = _normalize_amount(amount)
    if amount > 0:
        _state.total_chunks = 4
        _state.chunk_value = _normalize_amount(amount / _state.total_chunks)
        _state.chunks_available = _state.total_chunks
    else:
        _state.total_chunks = 0
        _state.chunk_value = 0.0
        _state.chunks_available = 0
    logger.info("Bankroll initialized with ₦%0.2f split across %s quarters", amount, _state.total_chunks)


def reserve_chunk() -> float | None:
    if _state.chunk_value <= 0 or _state.chunks_available <= 0:
        return None
    _state.chunks_available -= 1
    logger.info("Reserved one quarter (₦%0.2f), %s remaining", _state.chunk_value, _state.chunks_available)
    return _state.chunk_value


def release_chunk() -> None:
    if _state.total_chunks > 0 and _state.chunks_available < _state.total_chunks:
        _state.chunks_available += 1
        logger.info("Released one reserved quarter, %s remaining", _state.chunks_available)


def has_available_chunks() -> bool:
    return _state.chunk_value > 0 and _state.chunks_available > 0

## gets the starting balance, chunk value, how many chunks are currently available, and the total number of chunks for the day. This is useful for monitoring the bankroll status and making informed decisions about placing bets.
def get_state() -> dict:
    return {
        "starting_balance": _state.starting_balance,
        "chunk_value": _state.chunk_value,
        "chunks_available": _state.chunks_available,
        "total_chunks": _state.total_chunks,
    }
