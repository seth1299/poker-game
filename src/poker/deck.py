from __future__ import annotations
import random
from typing import List

from src.poker.card import Card, RANKS, SUITS

class Deck:
    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._cards: List[Card] = []
        self.reset()

    def reset(self) -> None:
        self._cards = [Card(r, s) for s in SUITS for r in RANKS]
        self.shuffle()

    def shuffle(self) -> None:
        self._rng.shuffle(self._cards)

    def draw(self) -> Card:
        if not self._cards:
            raise RuntimeError("Deck is empty")
        return self._cards.pop()

    def remaining(self) -> int:
        return len(self._cards)