from __future__ import annotations

from typing import List, Dict, Optional

from src.poker.deck import Deck
from src.poker.player import Player
from src.poker.card import Card
from src.poker.rules import TexasHoldemRules, default_blind_structure, Street


class PokerTable:
    """
    Holds the state for a single poker table.
    Now includes:
      - 1 human + 4 AI
      - rotating blinds (Big Blind moves clockwise each hand)
      - pot + per-player current bets (minimal foundation for betting later)
    """

    def __init__(self) -> None:
        self.rules = TexasHoldemRules()
        self.blinds = default_blind_structure(small_blind=10, big_blind=20, hands_per_level=5)

        self.deck = Deck()
        self.players: List[Player] = [
            Player("You", chips=self.rules.starting_chips),
            Player("AI-1", chips=self.rules.starting_chips),
            Player("AI-2", chips=self.rules.starting_chips),
            Player("AI-3", chips=self.rules.starting_chips),
            Player("AI-4", chips=self.rules.starting_chips),
        ]

        self.community: List[Card] = []
        self.hand_number = 0

        # Positions / round state
        self.big_blind_index: int = 0  # NEW GAME: "You" starts as Big Blind
        self.street: Street = Street.PRE_FLOP

        # Betting bookkeeping (very light for now)
        self.pot: int = 0
        self.current_bets: Dict[int, int] = {}  # seat_index -> amount in current street

    # ---------- Game lifecycle ----------

    def start_new_game(self) -> None:
        """
        Resets blinds/hand counter and forces "You" to be Big Blind on the first hand.
        """
        self.hand_number = 0
        self.big_blind_index = 0
        self.blinds.start_new_game()

        self.pot = 0
        self.current_bets.clear()
        self.community.clear()

        for p in self.players:
            p.chips = self.rules.starting_chips
            p.reset_for_hand()

    def start_new_hand(self) -> None:
        self.hand_number += 1
        self.blinds.advance_hand()

        self.deck.reset()
        self.community.clear()
        self.street = Street.PRE_FLOP

        self.pot = 0
        self.current_bets.clear()

        for p in self.players:
            p.reset_for_hand()

        # Rotate blinds clockwise each hand, but for Hand #1 in a new game,
        # big_blind_index should already be 0 ("You").
        if self.hand_number > 1:
            self.big_blind_index = (self.big_blind_index + 1) % len(self.players)

        self._post_blinds()

        # Deal 2 hole cards each, starting left of dealer (standard)
        dealer = self.dealer_index()
        first_to_receive = (dealer + 1) % len(self.players)
        self._deal_hole_cards(start_index=first_to_receive)

    # ---------- Position helpers ----------

    def small_blind_index(self) -> int:
        return (self.big_blind_index - 1) % len(self.players)

    def dealer_index(self) -> int:
        # Standard full-ring: dealer is one seat right of small blind
        return (self.small_blind_index() - 1) % len(self.players)

    def _next_seat(self, seat_index: int) -> int:
        return (seat_index + 1) % len(self.players)

    # ---------- Dealing / blinds ----------

    def _deal_hole_cards(self, start_index: int) -> None:
        for _ in range(self.rules.hole_cards):
            idx = start_index
            for _ in range(len(self.players)):
                self.players[idx].hand.append(self.deck.draw())
                idx = self._next_seat(idx)

    def _take_chips(self, seat_index: int, amount: int) -> int:
        """
        Remove up to `amount` chips from a player's stack (all-in safe).
        Returns the amount actually taken.
        """
        p = self.players[seat_index]
        taken = min(amount, p.chips)
        p.chips -= taken
        return taken

    def _post_blinds(self) -> None:
        sb, bb = self.blinds.current_blinds()
        sb_seat = self.small_blind_index()
        bb_seat = self.big_blind_index

        sb_paid = self._take_chips(sb_seat, sb)
        bb_paid = self._take_chips(bb_seat, bb)

        self.current_bets[sb_seat] = sb_paid
        self.current_bets[bb_seat] = bb_paid
        self.pot += sb_paid + bb_paid

    # ---------- Pygame loop integration ----------

    def update(self, dt: float) -> None:
        # placeholder: later, drive AI decision timers / animations / betting phases
        pass

    # ---------- Debug ----------

    def debug_string(self) -> str:
        sb, bb = self.blinds.current_blinds()
        parts = [
            f"Hand #{self.hand_number} | Blinds {sb}/{bb} | Pot {self.pot} | Deck {self.deck.remaining()}",
            f"D:{self.dealer_index()} SB:{self.small_blind_index()} BB:{self.big_blind_index}",
        ]
        for i, p in enumerate(self.players):
            hand = " ".join(c.short_name() for c in p.hand) or "(no cards)"
            bet = self.current_bets.get(i, 0)
            parts.append(f"[{i}] {p.name} chips:{p.chips} bet:{bet} hand:{hand}")
        return "    ".join(parts)