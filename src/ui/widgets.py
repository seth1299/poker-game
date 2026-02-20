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
        # Clean, less “placeholder”
        bg = (52, 52, 52)
        if not self.enabled:
            bg = (35, 35, 35)
        elif self.hovered:
            bg = (72, 72, 72)

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

    # Bigger center "pip" (optional but makes the card feel less empty)
    pip_px = max(18, int(rect.w * 0.55))
    pip = None
    if ui is not None and hasattr(ui, "get_suit_icon"):
        pip = ui.get_suit_icon(suit, pip_px)
    if pip is not None:
        pip_img = pip.copy()
        pip_img.set_alpha(70)  # subtle
        surface.blit(pip_img, pip_img.get_rect(center=rect.center))

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