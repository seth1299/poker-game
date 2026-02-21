from __future__ import annotations
import pygame

from src.ui.screens.base_screen import Screen
from src.ui.widgets import Button
from src.ui.screens.table_screen import TableScreen

class MainMenuScreen(Screen):
    def __init__(self, ui, table, on_quit):
        super().__init__()
        self.ui = ui
        self.on_quit = on_quit
        self.table = table
        self.title = self.ui.font_large.render("Poker", True, self.ui.colors["white"])

        self.btn_play = Button(
            pygame.Rect(540, 320, 200, 60),
            "Play",
            self.ui.font_medium,
            on_click=self._start_game,
        )
        self.btn_quit = Button(
            pygame.Rect(540, 400, 200, 60),
            "Quit",
            self.ui.font_medium,
            on_click=self.on_quit,
        )

    def _start_game(self) -> None:
        self.request_screen_change(
            TableScreen(self.ui, table=self.table, on_back=self._back_to_menu)
        )

    def _back_to_menu(self) -> None:
        self.request_screen_change(
            MainMenuScreen(self.ui, table=self.table, on_quit=self.on_quit)
        )

    def handle_event(self, event: pygame.event.Event) -> None:
        self.btn_play.handle_event(event)
        self.btn_quit.handle_event(event)

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.title, self.title.get_rect(center=(640, 180)))
        self.btn_play.draw(surface)
        self.btn_quit.draw(surface)