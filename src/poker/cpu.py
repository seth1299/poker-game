from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
import random

from src.poker.player import Player
from src.poker.rules import Action


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

    def choose_action(
        self,
        *,
        to_call: int,
        current_bet: int,
        big_blind: int,
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

        # Facing a bet: fold/call/occasional raise
        frac = to_call / max(1, self.chips)

        if self.personality == CPUPersonality.DEFENSIVE:
            if frac > 0.25 and self._rng.random() < 0.85:
                return (Action.FOLD, None)
            return (Action.CALL, None)

        if self.personality == CPUPersonality.NEUTRAL:
            if frac > 0.45 and self._rng.random() < 0.75:
                return (Action.FOLD, None)
            if self.chips > to_call + big_blind and self._rng.random() < 0.12:
                return (Action.RAISE, current_bet + big_blind)
            return (Action.CALL, None)

        # AGGRESSIVE
        if frac > 0.65 and self._rng.random() < 0.35:
            return (Action.FOLD, None)
        if self.chips > to_call + big_blind and self._rng.random() < 0.28:
            return (Action.RAISE, current_bet + (big_blind * 2))
        return (Action.CALL, None)