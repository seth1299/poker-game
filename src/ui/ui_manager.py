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
            
        def _load_any(names: list[str]):
            for n in names:
                img = _load_png(n)
                if img is not None:
                    return img
            return None

        self._suit_base = {
            "C": _load_png("club.png"),
            "D": _load_png("diamond.png"),
            "H": _load_png("heart.png"),
            "S": _load_png("spade.png"),
        }
        self._suit_scaled: dict[tuple[str, int], pygame.Surface] = {}
        # Face art (optional; will fall back gracefully if missing)
        self._face_base = {
            "J": _load_any(["Jack.png", "jack.png"]),
            "Q": _load_any(["Queen.png", "queen.png"]),
            "K": _load_any(["King.png", "king.png"]),
        }
        self._face_trimmed: dict[str, pygame.Surface] = {}
        for r, s in self._face_base.items():
            if s is not None:
                self._face_trimmed[r] = self._trim_alpha(s, min_alpha=10, pad_ratio=0.03)
        self._face_scaled: dict[tuple[str, int, int], pygame.Surface] = {}
        
    @staticmethod
    def _trim_alpha(surf: pygame.Surface, *, min_alpha: int = 1, pad_ratio: float = 0.03) -> pygame.Surface:
        """
        Crop away transparent borders so scaling is based on visible pixels.
        pad_ratio re-adds a small consistent margin after trimming.
        """
        rect = surf.get_bounding_rect(min_alpha=min_alpha)
        if rect.w <= 0 or rect.h <= 0:
            return surf

        pad = max(0, int(min(rect.w, rect.h) * pad_ratio))
        rect = rect.inflate(pad * 2, pad * 2)
        rect.clamp_ip(surf.get_rect())

        out = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        out.blit(surf, (0, 0), rect)
        return out
    
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
    def get_face_art(self, rank: str, max_w: int, max_h: int) -> pygame.Surface | None:
        """Return a scaled face-card surface (J/Q/K) that fits inside max_w x max_h."""
        if max_w <= 0 or max_h <= 0:
            return None

        base = self._face_trimmed.get(rank) or self._face_base.get(rank)
        if base is None:
            return None

        bw, bh = base.get_size()
        if bw <= 0 or bh <= 0:
            return None

        scale = min(max_w / bw, max_h / bh)
        tw = max(1, int(bw * scale))
        th = max(1, int(bh * scale))

        key = (rank, tw, th)
        cached = self._face_scaled.get(key)
        if cached is None:
            cached = pygame.transform.smoothscale(base, (tw, th))
            self._face_scaled[key] = cached
        return cached