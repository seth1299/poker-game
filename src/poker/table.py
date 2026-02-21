from __future__ import annotations

from typing import List, Dict
from dataclasses import dataclass
import random

from src.poker.deck import Deck
from src.poker.player import Player
from src.poker.cpu import CPUPlayer, CPUPersonality
from src.poker.card import Card
from src.poker.rules import TexasHoldemRules, default_blind_structure, Street, Action


class PokerTable:
    """
    Holds the state for a single poker table and drives betting + streets.
    NOTE: side pots / split pots are not implemented yet (all-ins are “safe” but not fully correct).
    """

    def __init__(self) -> None:
        self.rules = TexasHoldemRules()
        self.blinds = default_blind_structure(small_blind=10, big_blind=20, hands_per_level=5)
        self.deck = Deck()

        self.players: List[Player] = [
            Player("You", chips=self.rules.starting_chips),
            CPUPlayer("AI-1", chips=self.rules.starting_chips, personality=CPUPersonality.NEUTRAL),
            CPUPlayer("AI-2", chips=self.rules.starting_chips, personality=CPUPersonality.DEFENSIVE),
            CPUPlayer("AI-3", chips=self.rules.starting_chips, personality=CPUPersonality.AGGRESSIVE),
            CPUPlayer("AI-4", chips=self.rules.starting_chips, personality=CPUPersonality.NEUTRAL),
        ]

        self.community: List[Card] = []
        self.hand_number = 0

        # Positions / round state
        self.big_blind_index: int = 0  # NEW GAME: "You" starts as Big Blind
        self.street: Street = Street.PRE_FLOP

        # Betting bookkeeping (per street)
        self.pot: int = 0
        self.current_bets: Dict[int, int] = {}  # seat_index -> amount in current street
        self.current_bet_amount: int = 0

        # Turn engine
        self.hand_active: bool = False
        self.to_act_index: int | None = None
        self.pending_to_act: set[int] = set()

        # AI “thinking”
        self._ai_timer: float = 0.0

        # Cached blinds for the current hand (used by AI sizing / min-raise)
        self.sb_amount: int = 10
        self.bb_amount: int = 20

        # Optional: helpful for UI/debug
        self.last_action_text: str = ""
        self.last_actions: Dict[int, str] = {}  # seat_index -> short action string for UI

        self._rng = random.Random()

    # ---------- Game lifecycle ----------

    def start_new_game(self) -> None:
        self.hand_number = 0
        self.big_blind_index = 0
        self.blinds.start_new_game()

        self._reset_hand_state()

        for p in self.players:
            p.chips = self.rules.starting_chips
            p.reset_for_hand()

    def start_new_hand(self) -> None:
        self.hand_number += 1
        self.blinds.advance_hand()

        self._reset_hand_state()

        for p in self.players:
            p.reset_for_hand()

        if self.hand_number > 1:
            self.big_blind_index = (self.big_blind_index + 1) % len(self.players)

        self._post_blinds()

        # Deal 2 hole cards each, starting left of dealer (standard)
        dealer = self.dealer_index()
        first_to_receive = (dealer + 1) % len(self.players)
        self._deal_hole_cards(start_index=first_to_receive)

        # Start preflop betting (UTG = left of BB)
        self.hand_active = True
        self._begin_betting_round()

    def _reset_hand_state(self) -> None:
        self.deck.reset()
        self.community.clear()
        self.street = Street.PRE_FLOP

        self.pot = 0
        self.current_bets.clear()
        self.current_bet_amount = 0

        self.hand_active = False
        self.to_act_index = None
        self.pending_to_act.clear()
        self._ai_timer = 0.0
        self.last_action_text = ""
        self.last_actions.clear()

    # ---------- Position helpers ----------

    def small_blind_index(self) -> int:
        return (self.big_blind_index - 1) % len(self.players)

    def dealer_index(self) -> int:
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

    def _burn(self) -> None:
        if self.deck.remaining() > 0:
            _ = self.deck.draw()

    def _deal_community(self, count: int) -> None:
        for _ in range(count):
            self.community.append(self.deck.draw())

    def _take_chips(self, seat_index: int, amount: int) -> int:
        p = self.players[seat_index]
        taken = min(amount, p.chips)
        p.chips -= taken
        return taken

    def _post_blinds(self) -> None:
        self.sb_amount, self.bb_amount = self.blinds.current_blinds()
        sb_seat = self.small_blind_index()
        bb_seat = self.big_blind_index

        sb_paid = self._take_chips(sb_seat, self.sb_amount)
        bb_paid = self._take_chips(bb_seat, self.bb_amount)

        self.current_bets[sb_seat] = sb_paid
        self.current_bets[bb_seat] = bb_paid
        self.pot += sb_paid + bb_paid
        self.current_bet_amount = max(self.current_bets.values(), default=0)

        self.last_action_text = f"Posted blinds: SB {self.sb_amount} (seat {sb_seat}), BB {self.bb_amount} (seat {bb_seat})"

    # ---------- Betting / actions ----------

    def active_seats(self) -> list[int]:
        return [i for i, p in enumerate(self.players) if not p.folded]

    def seats_can_act(self) -> list[int]:
        return [i for i in self.active_seats() if self.players[i].chips > 0]

    def to_call(self, seat_index: int) -> int:
        return max(0, self.current_bet_amount - self.current_bets.get(seat_index, 0))

    def human_can_act(self) -> bool:
        return self.hand_active and self.to_act_index == 0 and not self.players[0].folded and self.players[0].chips >= 0

    def human_action(self, action: Action, raise_to_total: int | None = None) -> None:
        self.apply_action(0, action, raise_to_total=raise_to_total)

    def apply_action(self, seat_index: int, action: Action, *, raise_to_total: int | None = None) -> None:
        if not self.hand_active:
            return
        if self.to_act_index != seat_index:
            return
        if self.players[seat_index].folded:
            return

        call_amt = self.to_call(seat_index)
        prev_bet = self.current_bets.get(seat_index, 0)

        # Helper: put chips in so that seat's total street bet becomes `target_total`
        def bet_to(target_total: int) -> int:
            nonlocal prev_bet
            target_total = max(target_total, prev_bet)
            delta = target_total - prev_bet
            if delta <= 0:
                return 0
            paid = self._take_chips(seat_index, delta)
            self.pot += paid
            self.current_bets[seat_index] = prev_bet + paid
            prev_bet = self.current_bets[seat_index]
            self.current_bet_amount = max(self.current_bets.values(), default=0)
            return paid

        # --- Resolve action ---
        if action == Action.FOLD:
            self.players[seat_index].folded = True
            self.last_action_text = f"{self.players[seat_index].name} folds"
            self.last_actions[seat_index] = "Folded"
            # folded player no longer pending
            self.pending_to_act.discard(seat_index)

            # if only one remains, award pot and end hand
            alive = self.active_seats()
            if len(alive) == 1:
                self._award_pot(alive[0])
                return

            self._advance_turn(from_seat=seat_index)
            return

        if action in (Action.CHECK, Action.CALL):
            if call_amt > 0:
                # CHECK becomes CALL when facing a bet
                paid = bet_to(prev_bet + call_amt)
                self.last_action_text = f"{self.players[seat_index].name} calls {paid}"
                self.last_actions[seat_index] = f"Called {paid}"
            else:
                self.last_action_text = f"{self.players[seat_index].name} checks"
                self.last_actions[seat_index] = "Checked"

            self.pending_to_act.discard(seat_index)
            self._advance_turn(from_seat=seat_index)
            return

        if action in (Action.BET, Action.RAISE):
            # Minimal min-raise rule: at least +BB
            min_raise_to = self.current_bet_amount + max(1, self.bb_amount)

            target = raise_to_total if raise_to_total is not None else min_raise_to
            target = max(target, min_raise_to)

            # Cap to what the player can actually reach (all-in)
            max_total = prev_bet + self.players[seat_index].chips
            target = min(target, max_total)

            paid = bet_to(target)
            new_total = self.current_bets.get(seat_index, 0)

            if action == Action.BET:
                self.last_action_text = f"{self.players[seat_index].name} bets {paid}"
                self.last_actions[seat_index] = f"Bet {paid}"
            else:
                self.last_action_text = f"{self.players[seat_index].name} raises to {new_total} (+{paid})"
                self.last_actions[seat_index] = f"Raised +{paid} (to {new_total})"

            # If this didn't increase the table bet (e.g., all-in short), treat it like a call
            if self.current_bets.get(seat_index, 0) <= self.current_bet_amount and paid <= call_amt:
                self.pending_to_act.discard(seat_index)
                self._advance_turn(from_seat=seat_index)
                return

            # Aggressive action: everyone else who can act becomes pending again
            self.pending_to_act = set(self.seats_can_act())
            self.pending_to_act.discard(seat_index)

            self._advance_turn(from_seat=seat_index)
            return

    def _begin_betting_round(self) -> None:
        # Decide first to act
        if self.street == Street.PRE_FLOP:
            first = (self.big_blind_index + 1) % len(self.players)  # UTG
        else:
            first = (self.dealer_index() + 1) % len(self.players)  # SB

        self.pending_to_act = set(self.seats_can_act())
        self.to_act_index = first
        self._ai_timer = 0.0

        # If first seat can't act (folded/all-in), advance immediately
        if self.to_act_index not in self.pending_to_act:
            self._advance_turn(from_seat=(first - 1) % len(self.players))

    def _advance_turn(self, *, from_seat: int) -> None:
        # If betting round ended, advance street
        if not self.pending_to_act:
            self._on_betting_round_complete()
            return

        n = len(self.players)
        idx = from_seat
        for _ in range(n):
            idx = (idx + 1) % n
            if idx in self.pending_to_act and not self.players[idx].folded and self.players[idx].chips > 0:
                self.to_act_index = idx
                self._ai_timer = 0.0
                return

        # No valid next actor -> end betting round
        self.pending_to_act.clear()
        self._on_betting_round_complete()

    def _on_betting_round_complete(self) -> None:
        # If only one remains, end immediately
        alive = self.active_seats()
        if len(alive) == 1:
            self._award_pot(alive[0])
            return

        # Move to next street + deal community
        if self.street == Street.PRE_FLOP:
            self.street = Street.FLOP
            self._burn()
            self._deal_community(self.rules.flop_cards)
        elif self.street == Street.FLOP:
            self.street = Street.TURN
            self._burn()
            self._deal_community(self.rules.turn_cards)
        elif self.street == Street.TURN:
            self.street = Street.RIVER
            self._burn()
            self._deal_community(self.rules.river_cards)
        elif self.street == Street.RIVER:
            self.street = Street.SHOWDOWN
            self._showdown_placeholder()
            return
        else:
            return

        # New street: reset bets
        self.current_bets.clear()
        self.current_bet_amount = 0

        self._begin_betting_round()

    def _award_pot(self, winner_seat: int) -> None:
        winner = self.players[winner_seat]
        winner.chips += self.pot
        self.last_action_text = f"{winner.name} wins pot {self.pot}"
        self.pot = 0
        self.hand_active = False
        self.to_act_index = None
        self.pending_to_act.clear()

    def _showdown_placeholder(self) -> None:
        # TODO: plug in real hand evaluator when hand_evaluator.py is implemented
        alive = self.active_seats()
        winner_seat = alive[0] if alive else 0
        self._award_pot(winner_seat)

    # ---------- Pygame loop integration ----------

    def update(self, dt: float) -> None:
        if not self.hand_active:
            return
        if self.to_act_index is None:
            return

        # Human turn: wait for UI/buttons
        if self.to_act_index == 0:
            return

        seat = self.to_act_index
        p = self.players[seat]
        if not isinstance(p, CPUPlayer):
            return

        # Non-blocking “thinking” delay
        if self._ai_timer <= 0.0:
            self._ai_timer = p.sample_think_time()

        self._ai_timer -= dt
        if self._ai_timer > 0.0:
            return

        call_amt = self.to_call(seat)
        action, raise_to = p.choose_action(to_call=call_amt, current_bet=self.current_bet_amount, big_blind=self.bb_amount)
        self.apply_action(seat, action, raise_to_total=raise_to)

    # ---------- Debug ----------

    def debug_string(self) -> str:
        sb, bb = self.blinds.current_blinds()
        parts = [
            f"Hand #{self.hand_number} | Street {self.street.name} | Blinds {sb}/{bb} | Pot {self.pot} | Deck {self.deck.remaining()}",
            f"D:{self.dealer_index()} SB:{self.small_blind_index()} BB:{self.big_blind_index} | ToAct:{self.to_act_index}",
            f"Last: {self.last_action_text}",
        ]
        for i, p in enumerate(self.players):
            hand = " ".join(c.short_name() for c in p.hand) or "(no cards)"
            bet = self.current_bets.get(i, 0)
            parts.append(f"[{i}] {p.name} chips:{p.chips} bet:{bet} folded:{p.folded} hand:{hand}")
        return "    ".join(parts)