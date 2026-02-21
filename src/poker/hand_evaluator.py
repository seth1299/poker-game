from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

from src.poker.card import Card, RANKS
from src.poker.rules import HandRank, HAND_RANK_NAME

_RANK_TO_VAL = {r: i + 2 for i, r in enumerate(RANKS)}  # 2..14
_VAL_TO_RANK = {v: r for r, v in _RANK_TO_VAL.items()}
def _r(v: int) -> str:
    return _VAL_TO_RANK.get(v, str(v))


def _is_straight(vals_desc: list[int]) -> tuple[bool, int]:
    """
    vals_desc: unique ranks sorted high->low
    Returns (is_straight, high_card_of_straight)
    Handles wheel A-2-3-4-5 (high=5).
    """
    if len(vals_desc) < 5:
        return (False, 0)

    # normal
    for i in range(len(vals_desc) - 4):
        window = vals_desc[i : i + 5]
        if window[0] - window[4] == 4 and len(set(window)) == 5:
            return (True, window[0])

    # wheel: A,5,4,3,2
    wheel = {14, 5, 4, 3, 2}
    if wheel.issubset(set(vals_desc)):
        return (True, 5)

    return (False, 0)


def _score_5(cards: list[Card]) -> tuple[HandRank, tuple[int, ...], str]:
    vals = sorted((_RANK_TO_VAL[c.rank] for c in cards), reverse=True)
    suits = [c.suit for c in cards]
    is_flush = len(set(suits)) == 1

    uniq_vals = sorted(set(vals), reverse=True)
    is_straight, straight_high = _is_straight(uniq_vals)

    # counts: (count, value) sorted by count desc then value desc
    counts: dict[int, int] = {}
    for v in vals:
        counts[v] = counts.get(v, 0) + 1
    groups = sorted(((cnt, v) for v, cnt in counts.items()), reverse=True)

    # Straight Flush
    if is_flush and is_straight:
        hr = HandRank.STRAIGHT_FLUSH
        tb = (straight_high,)
        desc = f"{HAND_RANK_NAME[hr]} ({straight_high}-high)"
        return (hr, tb, desc)

    # Four of a Kind
    if groups[0][0] == 4:
        quad = groups[0][1]
        kicker = max(v for v in vals if v != quad)
        hr = HandRank.FOUR_OF_A_KIND
        tb = (quad, kicker)
        desc = f"{HAND_RANK_NAME[hr]} ({_r(quad)}s, with a {_r(kicker)} kicker.)"
        return (hr, tb, desc)

    # Full House
    if groups[0][0] == 3 and len(groups) > 1 and groups[1][0] >= 2:
        trips = groups[0][1]
        pair = groups[1][1]
        hr = HandRank.FULL_HOUSE
        tb = (trips, pair)
        desc = f"{HAND_RANK_NAME[hr]} ({trips}s full of {pair}s)"
        return (hr, tb, desc)

    # Flush
    if is_flush:
        hr = HandRank.FLUSH
        tb = tuple(vals)
        desc = f"{HAND_RANK_NAME[hr]} ({' '.join(_r(v) for v in vals)})"
        return (hr, tb, desc)

    # Straight
    if is_straight:
        hr = HandRank.STRAIGHT
        tb = (straight_high,)
        desc = f"{HAND_RANK_NAME[hr]} ({straight_high}-high)"
        return (hr, tb, desc)

    # Three of a Kind
    if groups[0][0] == 3:
        trips = groups[0][1]
        kickers = sorted((v for v in vals if v != trips), reverse=True)[:2]
        hr = HandRank.THREE_OF_A_KIND
        tb = (trips, *kickers)
        desc = f"{HAND_RANK_NAME[hr]} ({_r(trips)}s, with {' '.join(_r(v) for v in kickers)} kickers.)"
        return (hr, tb, desc)

    # Two Pair
    if groups[0][0] == 2 and len(groups) > 1 and groups[1][0] == 2:
        pair_hi = max(groups[0][1], groups[1][1])
        pair_lo = min(groups[0][1], groups[1][1])
        kicker = max(v for v in vals if v != pair_hi and v != pair_lo)
        hr = HandRank.TWO_PAIR
        tb = (pair_hi, pair_lo, kicker)
        desc = f"{HAND_RANK_NAME[hr]} ({_r(pair_hi)}s and {_r(pair_lo)}s, with a {_r(kicker)} kicker.)"
        return (hr, tb, desc)

    # One Pair
    if groups[0][0] == 2:
        pair = groups[0][1]
        kickers = sorted((v for v in vals if v != pair), reverse=True)[:3]
        hr = HandRank.ONE_PAIR
        tb = (pair, *kickers)
        desc = f"{HAND_RANK_NAME[hr]} ({_r(pair)}s, with {' '.join(_r(v) for v in kickers)} kickers.)"
        return (hr, tb, desc)

    # High Card
    hr = HandRank.HIGH_CARD
    tb = tuple(vals)
    desc = f"{HAND_RANK_NAME[hr]} ({' '.join(_r(v) for v in vals)})"
    return (hr, tb, desc)


def best_of_7(cards7: Iterable[Card]) -> tuple[HandRank, tuple[int, ...], str]:
    best: tuple[HandRank, tuple[int, ...], str] | None = None
    cards = list(cards7)
    for combo in combinations(cards, 5):
        scored = _score_5(list(combo))
        if best is None:
            best = scored
            continue
        if (scored[0], scored[1]) > (best[0], best[1]):
            best = scored
    assert best is not None
    return best