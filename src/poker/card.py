from __future__ import annotations
from dataclasses import dataclass

RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
SUITS = ["C", "D", "H", "S"]  # Clubs, Diamonds, Hearts, Spades

@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    def __post_init__(self) -> None:
        if self.rank not in RANKS:
            raise ValueError(f"Invalid rank: {self.rank}")
        if self.suit not in SUITS:
            raise ValueError(f"Invalid suit: {self.suit}")

    def short_name(self) -> str:
        return f"{self.rank}{self.suit}"

    def __str__(self) -> str:
        return self.short_name()