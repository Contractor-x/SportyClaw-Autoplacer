from dataclasses import dataclass


MAX_BETS_PER_DAY = 30

# (balance, max_daily_allocation)
DEFAULT_ANCHORS = (
    (5_000, 2_000),
    (50_000, 20_000),
    (500_000, 100_000),
    (1_000_000, 200_000),
)


@dataclass
class AllocationResult:
    balance: float
    allocation: float
    reserve: float


@dataclass
class StakePlan:
    stake_per_game: float
    used: float
    carryover: float


def _to_kobo(amount: float) -> int:
    return max(0, int(round(amount * 100)))


def _from_kobo(kobo: int) -> float:
    return round(kobo / 100, 2)


def _interpolate_allocation(balance: float, anchors: tuple[tuple[int, int], ...]) -> float:
    if balance <= 0:
        return 0.0

    sorted_anchors = sorted(anchors, key=lambda x: x[0])
    if balance <= sorted_anchors[0][0]:
        # Scale linearly from 0 to first anchor.
        x1, y1 = sorted_anchors[0]
        return (balance / x1) * y1

    for (x1, y1), (x2, y2) in zip(sorted_anchors, sorted_anchors[1:]):
        if x1 <= balance <= x2:
            slope = (y2 - y1) / (x2 - x1)
            return y1 + slope * (balance - x1)

    # Above last anchor: extend using the last segment's slope.
    (x1, y1), (x2, y2) = sorted_anchors[-2], sorted_anchors[-1]
    slope = (y2 - y1) / (x2 - x1)
    return y2 + slope * (balance - x2)


def compute_daily_allocation(balance: float, anchors: tuple[tuple[int, int], ...] = DEFAULT_ANCHORS) -> AllocationResult:
    allocation = _interpolate_allocation(balance, anchors)
    allocation = min(allocation, balance)
    allocation = max(0.0, allocation)
    reserve = max(0.0, balance - allocation)
    return AllocationResult(balance=round(balance, 2), allocation=round(allocation, 2), reserve=round(reserve, 2))


def build_stake_plan(
    allocation: float,
    games_today: int,
    carryover: float = 0.0,
    max_bets_per_day: int = MAX_BETS_PER_DAY,
) -> StakePlan:
    if games_today <= 0:
        return StakePlan(stake_per_game=0.0, used=0.0, carryover=round(carryover, 2))

    games = min(games_today, max_bets_per_day)
    available_kobo = _to_kobo(allocation + carryover)

    if games == 1:
        return StakePlan(
            stake_per_game=_from_kobo(available_kobo),
            used=_from_kobo(available_kobo),
            carryover=0.0,
        )

    stake_kobo = available_kobo // games
    used_kobo = stake_kobo * games
    carry_kobo = available_kobo - used_kobo

    return StakePlan(
        stake_per_game=_from_kobo(stake_kobo),
        used=_from_kobo(used_kobo),
        carryover=_from_kobo(carry_kobo),
    )


def roll_carryover_into_balance(balance: float, carryover: float) -> float:
    return round(balance + carryover, 2)
