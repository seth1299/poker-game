from __future__ import annotations
import pygame
from pathlib import Path

class UIManager:
    """
    Central place for UI resources (fonts, common colors, shared helpers).
    """
    def __init__(self) -> None:
        pygame.font.init()
        self.font_large = pygame.font.SysFont("arial", 48)
        self.font_medium = pygame.font.SysFont("arial", 28)
        self.font_small = pygame.font.SysFont("arial", 20)

        self.colors = {
            "white": (245, 245, 245),
            "black": (20, 20, 20),
            "gold": (220, 180, 40),
            "panel": (0, 0, 0, 120),
        }
        
        root = Path(__file__).resolve().parents[2]          # project root (…/src/ui/ui_manager.py -> …/)
        img_dir = root / "assets" / "images"
        
        def _load_png(name: str):
            try:
                return pygame.image.load(str(img_dir / name)).convert_alpha()
            except Exception as e:
                print(f"[UI] Could not load {name}: {e}")
                return None

        self._suit_base = {
            "C": _load_png("club.png"),
            "D": _load_png("diamond.png"),
            "H": _load_png("heart.png"),
            "S": _load_png("spade.png"),
        }
        self._suit_scaled: dict[tuple[str, int], pygame.Surface] = {}
        
    def get_suit_icon(self, suit: str, px: int) -> pygame.Surface | None:
        if px <= 0:
            return None
        base = self._suit_base.get(suit)
        if base is None:
            return None

        key = (suit, px)
        cached = self._suit_scaled.get(key)
        if cached is None:
            cached = pygame.transform.smoothscale(base, (px, px))
            self._suit_scaled[key] = cached
        return cached