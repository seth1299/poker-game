from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
from src.poker.card import Card

@dataclass
class Player:
    name: str
    chips: int = 1000
    hand: List[Card] = field(default_factory=list)
    folded: bool = False

    def reset_for_hand(self) -> None:
        self.hand.clear()
        self.folded = False