from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum, auto
from typing import Iterable


class Street(Enum):
    PRE_FLOP = auto()
    FLOP = auto()
    TURN = auto()
    RIVER = auto()
    SHOWDOWN = auto()


class Action(IntEnum):
    # Kept minimal for now; you can expand later.
    FOLD = 0
    CHECK = 1
    CALL = 2
    BET = 3
    RAISE = 4


class HandRank(IntEnum):
    """
    Higher is better.

    Note: In standard poker rules, "Royal Flush" is not a separate rank;
    it's just the highest possible straight flush (A-K-Q-J-T).
    If you want it displayed separately in UI, you can detect it in the evaluator,
    but the ordering below keeps it as top.
    """
    HIGH_CARD = 1
    ONE_PAIR = 2
    TWO_PAIR = 3
    THREE_OF_A_KIND = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    FOUR_OF_A_KIND = 8
    STRAIGHT_FLUSH = 9
    # Optional: ROYAL_FLUSH = 10  # Only if you truly want a separate category


# For UI text, logging, etc.
HAND_RANK_NAME: dict[HandRank, str] = {
    HandRank.HIGH_CARD: "High Card",
    HandRank.ONE_PAIR: "Pair",
    HandRank.TWO_PAIR: "Two Pair",
    HandRank.THREE_OF_A_KIND: "Three of a Kind",
    HandRank.STRAIGHT: "Straight",
    HandRank.FLUSH: "Flush",
    HandRank.FULL_HOUSE: "Full House",
    HandRank.FOUR_OF_A_KIND: "Four of a Kind",
    HandRank.STRAIGHT_FLUSH: "Straight Flush",
    # HandRank.ROYAL_FLUSH: "Royal Flush",
}


@dataclass(frozen=True)
class BlindLevel:
    small_blind: int
    big_blind: int
    hands_per_level: int = 5

    def __post_init__(self) -> None:
        if self.small_blind <= 0 or self.big_blind <= 0:
            raise ValueError("Blinds must be positive.")
        if self.big_blind <= self.small_blind:
            raise ValueError("Big blind must be greater than small blind.")
        if self.hands_per_level <= 0:
            raise ValueError("hands_per_level must be positive.")


@dataclass
class BlindStructure:
    """
    Controls blind escalation over hands.
    - call start_new_game() when a fresh game begins
    - call advance_hand() at the start of each hand
    - call current_blinds() to get (SB, BB) for posting

    By default: increases every 5 hands.
    """
    levels: list[BlindLevel]
    _hand_index: int = 0  # 0-based "hands played in this game"

    def __post_init__(self) -> None:
        if not self.levels:
            raise ValueError("BlindStructure must have at least one level.")

    def start_new_game(self) -> None:
        self._hand_index = 0

    def advance_hand(self) -> None:
        """
        Call once per new hand (before posting blinds).
        """
        self._hand_index += 1

    def current_level_index(self) -> int:
        """
        0-based level index based on hand count.
        Hand #1..hands_per_level => level 0
        """
        # Example: hands_per_level=5
        # hand_index=0 (0 hands played) => next hand is #1 => level 0
        # after advance_hand: _hand_index=1 => still level 0
        hands_played = self._hand_index
        total = 0
        for i, lvl in enumerate(self.levels):
            total += lvl.hands_per_level
            if hands_played <= total:
                return i
        return len(self.levels) - 1  # cap at last level

    def current_blinds(self) -> tuple[int, int]:
        lvl = self.levels[self.current_level_index()]
        return (lvl.small_blind, lvl.big_blind)


@dataclass(frozen=True)
class TexasHoldemRules:
    """
    Pure rules/config for Texas Hold'em.
    This does not store game state; PokerTable/GameState should.
    """
    starting_chips: int = 1000
    max_players: int = 9

    # Hold'em always deals 2 hole cards
    hole_cards: int = 2

    # Community cards by street
    flop_cards: int = 3
    turn_cards: int = 1
    river_cards: int = 1

    def street_order(self) -> tuple[Street, ...]:
        return (Street.PRE_FLOP, Street.FLOP, Street.TURN, Street.RIVER, Street.SHOWDOWN)

    def next_street(self, street: Street) -> Street:
        order = self.street_order()
        idx = order.index(street)
        return order[min(idx + 1, len(order) - 1)]


def default_blind_structure(
    small_blind: int = 10,
    big_blind: int = 20,
    hands_per_level: int = 5,
    levels: int = 10,
    growth: float = 1.5,
) -> BlindStructure:
    """
    Builds a simple escalating blind schedule.
    Example: 10/20, 15/30, 25/50, 40/80 ... rounded to nearest 5.

    You can replace this later with a fixed tournament table if you prefer.
    """
    if small_blind <= 0 or big_blind <= 0:
        raise ValueError("Blinds must be positive.")
    if big_blind <= small_blind:
        raise ValueError("Big blind must be greater than small blind.")
    if hands_per_level <= 0:
        raise ValueError("hands_per_level must be positive.")
    if levels <= 0:
        raise ValueError("levels must be positive.")
    if growth <= 1.0:
        raise ValueError("growth should be > 1.0 for escalation.")

    def round_to_5(x: float) -> int:
        return max(5, int(round(x / 5.0) * 5))

    built: list[BlindLevel] = []
    sb = float(small_blind)
    bb = float(big_blind)

    for _ in range(levels):
        built.append(
            BlindLevel(
                small_blind=round_to_5(sb),
                big_blind=round_to_5(bb),
                hands_per_level=hands_per_level,
            )
        )
        sb *= growth
        bb *= growth

    # Ensure BB > SB in case rounding created ties
    fixed: list[BlindLevel] = []
    for lvl in built:
        sb_i, bb_i = lvl.small_blind, lvl.big_blind
        if bb_i <= sb_i:
            bb_i = sb_i + 5
        fixed.append(BlindLevel(sb_i, bb_i, lvl.hands_per_level))

    return BlindStructure(levels=fixed)


def is_valid_hand_rank_order(order: Iterable[HandRank]) -> bool:
    """
    Utility: confirms an ordering includes each rank once, ascending.
    """
    lst = list(order)
    return sorted(lst) == lst and len(set(lst)) == len(lst)