from __future__ import annotations
import pygame
from abc import ABC, abstractmethod
from typing import Optional

class Screen(ABC):
    def __init__(self) -> None:
        self._next_screen: Optional["Screen"] = None

    def request_screen_change(self, next_screen: "Screen") -> None:
        self._next_screen = next_screen

    def pop_requested_screen(self) -> Optional["Screen"]:
        ns = self._next_screen
        self._next_screen = None
        return ns

    @abstractmethod
    def handle_event(self, event: pygame.event.Event) -> None:
        raise NotImplementedError

    @abstractmethod
    def update(self, dt: float) -> None:
        raise NotImplementedError

    @abstractmethod
    def draw(self, surface: pygame.Surface) -> None:
        raise NotImplementedError