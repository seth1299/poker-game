from dataclasses import dataclass

@dataclass(frozen=True)
class GameConfig:
    title: str = "Poker (Pygame)"
    width: int = 1280
    height: int = 720
    fps: int = 60
    bg_color: tuple[int, int, int] = (18, 92, 52)  # table green

CONFIG = GameConfig()