from __future__ import annotations
import pygame

from src.ui.screens.base_screen import Screen
from src.ui.widgets import Button, Slider, draw_rounded_rect, draw_text, draw_text_center, draw_card
from src.poker.table import PokerTable
from src.poker.rules import Action

class TableScreen(Screen):
    def __init__(self, ui, table: PokerTable, on_back):
        super().__init__()
        self.ui = ui
        self.on_back = on_back
        self.table = table

        self.show_debug = False

        self.btn_back = Button(
            pygame.Rect(24, 20, 140, 44),
            "Back",
            self.ui.font_small,
            on_click=self.on_back,
        )

        self.btn_deal = Button(
            pygame.Rect(24, 74, 140, 44),
            "New Hand",
            self.ui.font_small,
            on_click=self.table.start_new_hand,
        )
        
        self.btn_fold = Button(
            pygame.Rect(24, 128, 140, 44),
            "Fold",
            self.ui.font_small,
            on_click=lambda: self.table.human_action(Action.FOLD),
        )

        self.btn_check = Button(
            pygame.Rect(24, 182, 140, 44),
            "Check",
            self.ui.font_small,
            on_click=lambda: self.table.human_action(Action.CHECK),
        )

        # Raise slider (percentage of your stack used as your "put in" amount)
        self.raise_slider = Slider(pygame.Rect(24, 236, 140, 18), value=0.5)

        self.btn_raise = Button(
            pygame.Rect(24, 260, 140, 44),
            "Raise",
            self.ui.font_small,
            on_click=self._on_raise,
        )

        self.btn_all_in = Button(
            pygame.Rect(24, 314, 140, 44),
            "All In",
            self.ui.font_small,
            on_click=self._on_all_in,
        )

    def handle_event(self, event: pygame.event.Event) -> None:
        self.btn_back.handle_event(event)
        self.btn_deal.handle_event(event)
        self.btn_fold.handle_event(event)
        self.btn_check.handle_event(event)
        self.btn_raise.handle_event(event)
        self.raise_slider.handle_event(event)
        self.btn_all_in.handle_event(event)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_d:
                self.show_debug = not self.show_debug
            elif event.key == pygame.K_n:
                self.table.start_new_hand()
            elif event.key == pygame.K_f:
                self.table.human_action(Action.FOLD)
            elif event.key == pygame.K_c:
                self.table.human_action(Action.CHECK)
            elif event.key == pygame.K_r:
                self._on_raise()
                
    def _on_raise(self) -> None:
        you = self.table.players[0]
        prev_bet = self.table.current_bets.get(0, 0)
        to_call = self.table.to_call(0)

        put_in = int(you.chips * self.raise_slider.value)
        put_in = max(0, put_in)

        # If slider is 0, default to a minimum raise attempt
        if put_in == 0:
            raise_to = self.table.current_bet_amount + max(1, self.table.bb_amount)
            self.table.human_action(Action.RAISE, raise_to_total=raise_to)
            return

        target_total = prev_bet + max(put_in, to_call)

        # If our target doesn't exceed the table bet, it's just a call
        if target_total <= self.table.current_bet_amount:
            self.table.human_action(Action.CALL)
            return

        self.table.human_action(Action.RAISE, raise_to_total=target_total)
        
    def _on_all_in(self) -> None:
        you = self.table.players[0]
        prev_bet = self.table.current_bets.get(0, 0)
        to_call = self.table.to_call(0)

        # All-in means "put in everything you can"
        target_total = prev_bet + you.chips

        # If we can't beat the current bet, it's an all-in call
        if target_total <= self.table.current_bet_amount:
            self.table.human_action(Action.CALL)
            return

        self.table.human_action(Action.RAISE, raise_to_total=target_total)

    def update(self, dt: float) -> None:
        self.table.update(dt)

        # Disable "New Hand" mid-hand
        self.btn_deal.enabled = not self.table.hand_active

        # Only allow action buttons on the human's turn
        human_turn = self.table.human_can_act()
        self.btn_fold.enabled = human_turn
        self.btn_check.enabled = human_turn
        self.btn_raise.enabled = human_turn
        self.raise_slider.enabled = human_turn
        self.btn_all_in.enabled = human_turn

        # Dynamic label: Check vs Call X
        if self.table.hand_active:
            to_call = self.table.to_call(0)
            self.btn_check.text = f"Call {to_call}" if to_call > 0 else "Check"
        else:
            self.btn_check.text = "Check"

    def draw(self, surface: pygame.Surface) -> None:
        w, h = surface.get_size()

        # --- Responsive layout constants ---
        pad = int(min(w, h) * 0.02)           # 2% padding
        sidebar_w = int(w * 0.14)             # 14% left column
        topbar_h = int(h * 0.08)              # 8% height

        # Left controls area
        # (optional: you can also reposition buttons using these values later)
        self.btn_back.draw(surface)
        self.btn_deal.draw(surface)
        self.btn_fold.draw(surface)
        self.btn_check.draw(surface)
        self.btn_raise.draw(surface)
        
        self.raise_slider.draw(surface)

        # Slider label: "Bet N" where N is % of your current chips
        you = self.table.players[0]
        bet_amt = int(you.chips * self.raise_slider.value)
        draw_text(surface, f"Bet {bet_amt}", self.ui.font_small, (245, 245, 245), (24, 216))

        # Content area (everything right of the sidebar)
        content_x = pad + sidebar_w + pad
        content_w = w - content_x - pad

        top_bar = pygame.Rect(content_x, pad, content_w, topbar_h)
        
        showdown_active = (not self.table.hand_active) and bool(self.table.showdown_summary)

        table_rect = pygame.Rect(
            content_x,
            top_bar.bottom + pad,
            content_w,
            h - (top_bar.bottom + pad) - pad,
        )

        # Cards scale with table area
        # Cards scale with table area
        card_w = int(min(table_rect.w * 0.08, table_rect.h * 0.16))
        card_h = int(card_w * 1.4)
        gap = int(card_w * 0.18)

        # Player panel scales with card size (instead of fixed 220x52)
        panel_w = int(card_w * 2.6)
        panel_h = int(card_h * 0.45)

        # --- Player topbar row (You, AI-1..AI-4) ---
        playerbar_h = max(int(table_rect.h * 0.18), self.ui.font_small.get_height() * 4)
        playerbar = pygame.Rect(table_rect.x + pad, table_rect.y + pad, table_rect.w - (pad * 2), playerbar_h)

        # Community row starts below the player bar
                # Mini hole cards sit directly under each player box during showdown.
        # So: reserve vertical space and push the community cards DOWN.
        community_y = playerbar.bottom + pad

        if showdown_active:
            n = len(self.table.players)
            gap_bar = max(8, int(playerbar.w * 0.012))
            box_w = (playerbar.w - (gap_bar * (n - 1))) // n

            mini_w, mini_h, _mini_gap = self._showdown_mini_sizes(card_w, gap, box_w, pad)
            label_h = self.ui.font_small.get_height()

            # Space for: mini cards + label + padding
            community_y += mini_h + label_h + pad

        hint_y = table_rect.bottom - pad - (self.ui.font_small.get_height() // 2)
        hole_y = hint_y - pad - card_h

        y_top = community_y - pad - (panel_h // 2)
        y_bottom = hole_y - pad - (panel_h // 2)

        # --- Top bar ---
        draw_rounded_rect(surface, top_bar, (10, 40, 26), radius=16)
        pygame.draw.rect(surface, (28, 80, 54), top_bar, width=2, border_radius=16)

        sb, bb = self.table.blinds.current_blinds()
        header_left = f"Hand {self.table.hand_number}"
        header_mid = f"Blinds {sb}/{bb}"
        header_right = f"Pot {self.table.pot}"

        draw_text(surface, header_left, self.ui.font_medium, (240, 240, 240),
                (top_bar.x + pad, top_bar.y + int(topbar_h * 0.22)))
        draw_text_center(surface, header_mid, self.ui.font_medium, (240, 240, 240),
                        (top_bar.centerx, top_bar.centery))
        draw_text(surface, header_right, self.ui.font_medium, (240, 240, 240),
                (top_bar.right - int(content_w * 0.16), top_bar.y + int(topbar_h * 0.22)))

        # --- Table background ---
        draw_rounded_rect(surface, table_rect, (14, 58, 38), radius=24)
        pygame.draw.rect(surface, (30, 92, 62), table_rect, width=2, border_radius=24)

        draw_text_center(surface, "Community", self.ui.font_small, (230, 230, 230),
                        (table_rect.centerx, table_rect.y + int(table_rect.h * 0.08)))

        # --- Community cards ---
        community = self.table.community
        total_w = (card_w * 5) + (gap * 4)
        start_x = table_rect.centerx - total_w // 2

        for i in range(5):
            rect = pygame.Rect(start_x + i * (card_w + gap), community_y, card_w, card_h)

            if i < len(community):
                draw_card(surface, rect, community[i].short_name(), self.ui)
            else:
                # card back / placeholder
                draw_rounded_rect(surface, rect, (15, 30, 55), radius=12)
                pygame.draw.rect(surface, (230, 230, 230), rect, width=2, border_radius=12)

        # --- Player topbar (uniform row) ---
        n = len(self.table.players)
        gap_bar = max(8, int(playerbar.w * 0.012))
        box_w = (playerbar.w - (gap_bar * (n - 1))) // n
        box_h = playerbar.h

        x = playerbar.x
        for seat_idx in range(n):
            p = self.table.players[seat_idx]
            status = self._seat_status_text(seat_idx)

            r = pygame.Rect(x, playerbar.y, box_w, box_h)
            self._draw_player_panel_rect(surface, r, seat_idx, p.name, p.chips, p.folded, status)

            x += box_w + gap_bar
            
        showdown_active = (not self.table.hand_active) and bool(self.table.showdown_summary)
        
        if not showdown_active:
            # --- Hole cards (seat 0) ---
            you = self.table.players[0]
            hole = you.hand
            
            # --- Hole cards (seat 0) ---
            hole_total_w = (card_w * 2) + gap
            hole_start_x = table_rect.centerx - hole_total_w // 2

            for i in range(2):
                rect = pygame.Rect(hole_start_x + i * (card_w + gap), hole_y, card_w, card_h)

                if i < len(hole):
                    draw_card(surface, rect, hole[i].short_name(), self.ui)
                else:
                    draw_rounded_rect(surface, rect, (15, 30, 55), radius=12)
                    pygame.draw.rect(surface, (230, 230, 230), rect, width=2, border_radius=12)

        draw_text_center(surface, "Press D to toggle debug", self.ui.font_small, (220, 220, 220),
            (table_rect.centerx, hint_y))
        
        # --- Showdown overlay ---
        if showdown_active:
            self._draw_showdown_overlay(surface, table_rect, playerbar, pad, card_w, card_h, gap, community_y)

        if self.show_debug:
            dbg = pygame.Rect(content_x, top_bar.bottom + pad, content_w, int(h * 0.10))
            draw_rounded_rect(surface, dbg, (0, 0, 0), radius=16)
            pygame.draw.rect(surface, (220, 220, 220), dbg, width=1, border_radius=16)
            draw_text(surface, self.table.debug_string(), self.ui.font_small, (245, 245, 245),
                    (dbg.x + pad, dbg.y + pad))
            
    def _draw_showdown_overlay(
        self,
        surface: pygame.Surface,
        table_rect: pygame.Rect,
        playerbar: pygame.Rect,
        pad: int,
        card_w: int,
        card_h: int,
        gap: int,
        community_y: int,
    ) -> None:
        s = self.table.showdown_summary or {}
        rows = s.get("rows", [])
        winner = s.get("winner_name", "Unknown")
        winner_desc = s.get("winner_desc", "N/A")
        pot = s.get("pot", 0)

        # Compact result banner (not a giant modal)
        mw = int(table_rect.w * 0.72)
        line_h = self.ui.font_small.get_height()
        mh = (pad * 2) + (line_h * 2)  # title + hint

        modal = pygame.Rect(0, 0, mw, mh)

        # Place it BELOW the showdown mini-cards row, without covering community cards too much.
        modal.centerx = table_rect.centerx
        # Place banner under the community cards row (community_y is lowered during showdown)
        modal.top = community_y + card_h + pad

        # Safety clamp (stay inside table)
        if modal.bottom > table_rect.bottom - pad:
            modal.bottom = table_rect.bottom - pad

        draw_rounded_rect(surface, modal, (10, 40, 26), radius=20)
        pygame.draw.rect(surface, (230, 230, 230), modal, width=2, border_radius=20)

        title = f"Result: {winner} wins ({winner_desc}) | Pot {pot}"
        draw_text(surface, self._truncate_to_width(title, self.ui.font_small, modal.w - pad * 2),
                  self.ui.font_small, (245, 245, 245), (modal.x + pad, modal.y + pad))

        # Draw each player's revealed hole cards UNDER their topbar box,
        # with the evaluated hand text underneath the two cards.
        n = len(self.table.players)
        gap_bar = max(8, int(playerbar.w * 0.012))
        box_w = (playerbar.w - (gap_bar * (n - 1))) // n
        box_h = playerbar.h

        # Showdown reveal row: make cards bigger, but clamp so 2 cards always fit within the player box.
        max_pair_w = box_w - (pad * 2)
        mini_gap = max(6, int(gap * 0.60))
        mini_w, mini_h, mini_gap = self._showdown_mini_sizes(card_w, gap, box_w, pad)

        # Vertical placement: below playerbar, above community cards area
        cards_y = playerbar.bottom + max(6, int(pad * 0.6))

        # Make a quick lookup: seat -> row dict
        row_by_seat = {int(r.get("seat", 0)): r for r in rows}

        x = playerbar.x
        for seat_idx in range(n):
            r = row_by_seat.get(seat_idx, {})
            cards = r.get("cards", []) or []
            desc = (r.get("hand_name", "N/A") or "").strip()

            # 2 cards centered under that player's box
            total_cards_w = (mini_w * 2) + mini_gap
            cx = x + (box_w // 2)
            start_x = cx - (total_cards_w // 2)

            for i in range(2):
                cr = pygame.Rect(start_x + i * (mini_w + mini_gap), cards_y, mini_w, mini_h)
                if i < len(cards):
                    draw_card(surface, cr, cards[i], self.ui)
                else:
                    draw_rounded_rect(surface, cr, (15, 30, 55), radius=10)
                    pygame.draw.rect(surface, (230, 230, 230), cr, width=2, border_radius=10)

            # Evaluated hand text under the cards, bounded to the player's box width
            max_w = box_w - (pad * 2)
            desc_fit = self._truncate_to_width(desc, self.ui.font_small, max_w)
            draw_text_center(
                surface,
                desc_fit,
                self.ui.font_small,
                (245, 245, 245),
                (cx, cards_y + mini_h + max(10, int(pad * 0.55))),
            )

            x += box_w + gap_bar

        hint = "Press New Hand to continue"
        draw_text(surface, hint, self.ui.font_small, (245, 245, 245),
                  (modal.x + pad, modal.y + pad + line_h))
        
    def _showdown_mini_sizes(self, card_w: int, gap: int, box_w: int, pad: int) -> tuple[int, int, int]:
        # Bigger mini cards, clamped so two always fit under the box
        max_pair_w = box_w - (pad * 2)
        mini_gap = max(6, int(gap * 0.60))
        mini_w = min(int(card_w * 0.70), int((max_pair_w - mini_gap) / 2))
        mini_w = max(26, mini_w)
        mini_h = int(mini_w * 1.4)
        return mini_w, mini_h, mini_gap

    def _truncate_to_width(self, text: str, font: pygame.font.Font, max_w: int) -> str:
        text = (text or "").strip()
        if max_w <= 0 or not text:
            return ""

        if font.size(text)[0] <= max_w:
            return text

        ell = "..."
        # leave room for ellipsis
        max_w2 = max(0, max_w - font.size(ell)[0])
        if max_w2 <= 0:
            return ell

        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi) // 2
            if font.size(text[:mid])[0] <= max_w2:
                lo = mid + 1
            else:
                hi = mid
        cut = max(0, lo - 1)
        return text[:cut] + ell

    def _draw_player_panel_rect(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        seat: int,
        name: str,
        chips: int,
        folded: bool,
        status: str,
    ) -> None:
        draw_rounded_rect(surface, rect, (8, 34, 22), radius=16)
        pygame.draw.rect(surface, (30, 92, 62), rect, width=2, border_radius=16)

        label = f"[{seat}] {name}"

        # Blind badges (current hand)
        if self.table.hand_number > 0:
            if seat == self.table.small_blind_index():
                label += " [SB]"
            if seat == self.table.big_blind_index:
                label += " [BB]"

        if folded:
            label += " (Fold)"

        x_pad = max(10, int(rect.w * 0.05))
        y_pad = max(8, int(rect.h * 0.18))
        line_h = self.ui.font_small.get_height()
        max_text_w = max(0, rect.w - (x_pad * 2))

        lines = [label, f"Chips: {chips}"]
        status = (status or "").strip()
        if status:
            lines.append(status)

        # If height is tight, drop the 3rd line first
        max_lines = max(1, (rect.h - (y_pad * 2)) // max(1, line_h))
        lines = lines[:max_lines]

        y = rect.y + y_pad
        for i, t in enumerate(lines):
            t_fit = self._truncate_to_width(t, self.ui.font_small, max_text_w)
            draw_text(surface, t_fit, self.ui.font_small, (240, 240, 240), (rect.x + x_pad, y + i * line_h))
    
    def _draw_player_panel(self, surface: pygame.Surface, seat: int, name: str, chips: int, folded: bool, status: str, cx: int, cy: int, panel_w: int, panel_h: int) -> None:
        rect = pygame.Rect(cx - (panel_w // 2), cy - (panel_h // 2), panel_w, panel_h)
        draw_rounded_rect(surface, rect, (8, 34, 22), radius=16)
        pygame.draw.rect(surface, (30, 92, 62), rect, width=2, border_radius=16)

        label = f"[{seat}] {name}"
        if folded:
            label += " (Fold)"
        x_pad = max(10, int(panel_w * 0.05))
        line_h = self.ui.font_small.get_height()

        lines = [label, f"Chips: {chips}"]
        status = (status or "").strip()
        if status:
            lines.append(status)

        total_h = len(lines) * line_h
        y = rect.y + max(6, (panel_h - total_h) // 2)

        for i, text in enumerate(lines):
            draw_text(surface, text, self.ui.font_small, (240, 240, 240), (rect.x + x_pad, y + i * line_h))
        
    def _seat_status_text(self, seat: int) -> str:
        # Turn / thinking
        if self.table.hand_active and self.table.to_act_index == seat:
            if seat == 0:
                return "Your turn"
            # CPU turn: show “Thinking…” while its timer is running (or until action fires)
            if getattr(self.table, "_ai_timer", 0.0) > 0.0:
                return "Thinking..."

            # If timer not set yet, still show turn ownership
            return "CPU turn"

        # Last action (per-seat)
        return self.table.last_actions.get(seat, "")

    def _seat_positions(self, table_rect: pygame.Rect, n: int, y_top: int, y_bottom: int) -> list[tuple[int, int]]:
        cx = table_rect.centerx
        left = table_rect.left
        right = table_rect.right
        top = table_rect.top
        bottom = table_rect.bottom

        # tuned for 5 players
        # tuned for 5 players
        return [
            (cx, y_bottom),                                              # 0 You
            (left + int(table_rect.w * 0.20), y_bottom),                  # 1
            (left + int(table_rect.w * 0.28), y_top),                     # 2
            (right - int(table_rect.w * 0.28), y_top),                    # 3
            (right - int(table_rect.w * 0.20), y_bottom),                 # 4
        ]