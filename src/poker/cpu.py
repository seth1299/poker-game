from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
import random
from src.poker.player import Player
from src.poker.rules import Action
from src.poker.card import Card, RANKS, SUITS
from src.poker.hand_evaluator import best_of_7


class CPUPersonality(Enum):
    AGGRESSIVE = auto()
    NEUTRAL = auto()
    DEFENSIVE = auto()


@dataclass
class CPUPlayer(Player):
    personality: CPUPersonality = CPUPersonality.NEUTRAL

    # “thinking” delay range (seconds)
    think_min: float = 0.8
    think_max: float = 1.8

    _rng: random.Random = field(default_factory=random.Random, repr=False)

    def sample_think_time(self) -> float:
        return self._rng.uniform(self.think_min, self.think_max)
    
    def _estimate_strength(self, hole: list[Card], community: list[Card], iters: int = 80) -> float:
        """
        Very simple Monte Carlo strength estimate:
        - uses only hole + currently revealed community
        - randomly completes the board and compares vs 1 random opponent
        Not omniscient; no peeking at deck.
        """
        known = hole + community
        if len(hole) != 2:
            return 0.0

        # Build remaining deck excluding known
        known_set = {(c.rank, c.suit) for c in known}
        remaining = [Card(r, s) for s in SUITS for r in RANKS if (r, s) not in known_set]

        need = max(0, 5 - len(community))
        if need == 0 and len(community) == 5:
            # Full information: just compare vs random opponent on full board
            wins = 0
            for _ in range(iters):
                opp = self._rng.sample(remaining, 2)
                hr1, tb1, _ = best_of_7(hole + community)
                hr2, tb2, _ = best_of_7(opp + community)
                wins += 1 if (hr1, tb1) >= (hr2, tb2) else 0
            return wins / iters

        wins = 0
        for _ in range(iters):
            sample = self._rng.sample(remaining, 2 + need)
            opp = sample[:2]
            board_add = sample[2:]
            board = community + board_add

            hr1, tb1, _ = best_of_7(hole + board)
            hr2, tb2, _ = best_of_7(opp + board)

            wins += 1 if (hr1, tb1) >= (hr2, tb2) else 0

        return wins / iters

    def choose_action(
        self,
        *,
        to_call: int,
        current_bet: int,
        big_blind: int,
        pot: int,
        hole: list,
        community: list,
    ) -> tuple[Action, int | None]:
        """
        Returns: (action, raise_to_total)
        - raise_to_total is the TOTAL bet this seat will have in the street after raising.
        """
        if self.folded or self.chips <= 0:
            return (Action.CHECK, None)

        # No bet to you: check or occasional small bet
        if to_call <= 0:
            if self.personality == CPUPersonality.AGGRESSIVE and self.chips > big_blind and self._rng.random() < 0.35:
                return (Action.BET, max(big_blind, big_blind * 2))
            if self.personality == CPUPersonality.NEUTRAL and self.chips > big_blind and self._rng.random() < 0.15:
                return (Action.BET, max(big_blind, big_blind))
            return (Action.CHECK, None)

                # Facing a bet: use pot odds + estimated hand strength (no omniscience)
        strength = self._estimate_strength(hole, community, iters=70)
        pot_odds = to_call / max(1, (pot + to_call))  # price vs reward

        # Personality shifts folding tolerance
        if self.personality == CPUPersonality.DEFENSIVE:
            fold_bias = 1.10
            raise_bias = 0.55
        elif self.personality == CPUPersonality.AGGRESSIVE:
            fold_bias = 0.85
            raise_bias = 1.35
        else:
            fold_bias = 1.00
            raise_bias = 1.00

        # If our equity is meaningfully below the price, fold sometimes (more often when short)
        short_stack = self.chips <= (big_blind * 8)
        margin = 0.92 if short_stack else 0.98

        if strength < (pot_odds * fold_bias * margin):
            # still sometimes defend (esp. aggressive)
            if self.personality == CPUPersonality.AGGRESSIVE and self._rng.random() < 0.20:
                return (Action.CALL, None)
            return (Action.FOLD, None)

        # Otherwise call or raise depending on strength
        if self.chips > to_call + big_blind and strength > 0.62 and self._rng.random() < (0.22 * raise_bias):
            # Raise sizing scales with strength; table.py will clamp to all-in if needed
            bump = int(big_blind * (2 + strength * 4))
            return (Action.RAISE, current_bet + max(big_blind, bump))

        return (Action.CALL, None)