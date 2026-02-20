from __future__ import annotations
import pygame

def pct_x(w: int, p: float) -> int:
    return int(w * p)

def pct_y(h: int, p: float) -> int:
    return int(h * p)

def rect_pct(w: int, h: int, x: float, y: float, rw: float, rh: float) -> pygame.Rect:
    return pygame.Rect(pct_x(w, x), pct_y(h, y), pct_x(w, rw), pct_y(h, rh))