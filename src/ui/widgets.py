from __future__ import annotations
import pygame
from typing import Callable

_FONT_CACHE: dict[int, pygame.font.Font] = {}

def draw_rounded_rect(surface: pygame.Surface, rect: pygame.Rect, color: tuple[int, int, int], radius: int = 12) -> None:
    pygame.draw.rect(surface, color, rect, border_radius=radius)

def draw_text(surface: pygame.Surface, text: str, font: pygame.font.Font, color: tuple[int, int, int], pos: tuple[int, int]) -> None:
    img = font.render(text, True, color)
    surface.blit(img, pos)

def draw_text_center(surface: pygame.Surface, text: str, font: pygame.font.Font, color: tuple[int, int, int], center: tuple[int, int]) -> None:
    img = font.render(text, True, color)
    r = img.get_rect(center=center)
    surface.blit(img, r)
    
def _get_bold_font(px: int) -> pygame.font.Font:
    px = max(12, px)
    f = _FONT_CACHE.get(px)
    if f is None:
        f = pygame.font.SysFont("arial", px, bold=True)
        _FONT_CACHE[px] = f
    return f

class Button:
    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        font: pygame.font.Font,
        on_click: Callable[[], None],
    ) -> None:
        self.rect = rect
        self.text = text
        self.font = font
        self.on_click = on_click
        self.hovered = False
        self.enabled = True

    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.enabled:
            return

        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.on_click()

    def draw(self, surface: pygame.Surface) -> None:
        # Enabled should look clickable; disabled should look greyed-out
        bg = (35, 35, 35)          # enabled (dark)
        if not self.enabled:
            bg = (90, 90, 90)      # disabled (greyed out)
        elif self.hovered:
            bg = (55, 55, 55)      # hover (slightly lighter)

        draw_rounded_rect(surface, self.rect, bg, radius=12)
        pygame.draw.rect(surface, (210, 210, 210), self.rect, width=2, border_radius=12)
        draw_text_center(surface, self.text, self.font, (245, 245, 245), self.rect.center)

def draw_card(surface: pygame.Surface, rect: pygame.Rect, label: str, ui=None) -> None:
    draw_rounded_rect(surface, rect, (245, 245, 245), radius=12)
    pygame.draw.rect(surface, (25, 25, 25), rect, width=2, border_radius=12)

    label = (label or "").strip()
    if len(label) < 2:
        return

    rank, suit = label[:-1], label[-1]
    is_red = suit in ("H", "D")
    text_color = (180, 0, 0) if is_red else (25, 25, 25)

    font_px = max(14, int(rect.h * 0.18))
    font = _get_bold_font(font_px)
    pad = max(6, int(rect.w * 0.08))

    # Corner label surface (top-left + bottom-right rotated)
    gap = max(2, pad // 3)

    rank_img = font.render(rank, True, text_color)

    corner_icon_px = max(12, int(rect.w * 0.22))  # <-- key change: size tied to card width
    corner_icon = None
    if ui is not None and hasattr(ui, "get_suit_icon"):
        corner_icon = ui.get_suit_icon(suit, corner_icon_px)

    if corner_icon is None:
        corner_icon = font.render(suit, True, text_color)

    corner_w = rank_img.get_width() + gap + corner_icon.get_width()
    corner_h = max(rank_img.get_height(), corner_icon.get_height())

    corner = pygame.Surface((corner_w, corner_h), pygame.SRCALPHA)
    corner.blit(rank_img, (0, (corner_h - rank_img.get_height()) // 2))
    corner.blit(corner_icon, (rank_img.get_width() + gap, (corner_h - corner_icon.get_height()) // 2))

    # Top-left
    surface.blit(corner, (rect.x + pad, rect.y + pad))

    # Bottom-right (rotated 180°, like real cards)
    corner_rot = pygame.transform.rotate(corner, 180)
    surface.blit(corner_rot, (rect.right - pad - corner_w, rect.bottom - pad - corner_h))
    
    # --- Center art / pips ---
    inner = rect.inflate(-pad * 2, -pad * 2)
    reserve = corner_h + max(2, pad // 2)
    pip_area = pygame.Rect(inner.x, inner.y + reserve, inner.w, max(1, inner.h - (reserve * 2)))

    # Face cards: center art (King.png / Queen.png / Jack.png)
    if rank in ("J", "Q", "K"):
        face = None
        if ui is not None and hasattr(ui, "get_face_art"):
            face = ui.get_face_art(rank, int(inner.w * 0.8), int(inner.h * 0.8))
        if face is not None:
            surface.blit(face, face.get_rect(center=rect.center))
        else:
            # Fallback if art is missing
            big_font = _get_bold_font(max(18, int(rect.h * 0.42)))
            draw_text_center(surface, rank, big_font, text_color, rect.center)
        return

    # Ace: single suit icon in the center
    if rank == "A":
        ace_px = max(22, int(rect.w * 0.62))
        ace = None
        if ui is not None and hasattr(ui, "get_suit_icon"):
            ace = ui.get_suit_icon(suit, ace_px)
        if ace is None:
            ace = font.render(suit, True, text_color)
        surface.blit(ace, ace.get_rect(center=rect.center))
        return

    # Number cards (2-10): pip layouts
    def _pip_layout(n: int) -> list[tuple[float, float]]:
        l, c, r = 0.28, 0.50, 0.72
        y1, y2, y3, y4, y5 = 0.08, 0.30, 0.50, 0.70, 0.92
        yA, yB, yC, yD, yE, yF = 0.05, 0.23, 0.41, 0.59, 0.77, 0.95

        if n == 2:
            return [(c, y1), (c, y5)]
        if n == 3:
            return [(c, y1), (c, y3), (c, y5)]
        if n == 4:
            return [(l, y1), (r, y1), (l, y5), (r, y5)]
        if n == 5:
            return [(l, y1), (r, y1), (c, y3), (l, y5), (r, y5)]
        if n == 6:
            return [(l, y1), (r, y1), (l, y3), (r, y3), (l, y5), (r, y5)]
        if n == 7:
            return [(l, y1), (r, y1), (c, y2), (l, y3), (r, y3), (l, y5), (r, y5)]
        if n == 8:
            return [(l, y1), (r, y1), (c, y2), (l, y3), (r, y3), (c, y4), (l, y5), (r, y5)]
        if n == 9:
            return [(l, y1), (r, y1), (c, y2), (l, y3), (c, y3), (r, y3), (c, y4), (l, y5), (r, y5)]
        if n == 10:
            return [(l, yA), (r, yA), (l, yB), (r, yB), (c, yC), (c, yD), (l, yE), (r, yE), (l, yF), (r, yF)]
        return []

    # Convert rank to a pip count
    count = 0
    if rank == "T":
        count = 10
    else:
        try:
            count = int(rank)
        except ValueError:
            count = 0

    if 2 <= count <= 10:
        if count <= 3:
            pip_px = max(14, int(rect.w * 0.24))
        elif count <= 6:
            pip_px = max(14, int(rect.w * 0.21))
        else:
            pip_px = max(14, int(rect.w * 0.18))

        pip_img = None
        if ui is not None and hasattr(ui, "get_suit_icon"):
            pip_img = ui.get_suit_icon(suit, pip_px)
        if pip_img is None:
            pip_img = font.render(suit, True, text_color)

        for (xp, yp) in _pip_layout(count):
            cx = pip_area.x + int(pip_area.w * xp)
            cy = pip_area.y + int(pip_area.h * yp)
            surface.blit(pip_img, pip_img.get_rect(center=(cx, cy)))