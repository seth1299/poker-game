import pygame
from src.config import CONFIG
from src.ui.ui_manager import UIManager
from src.ui.screens.main_menu import MainMenuScreen
from src.poker.table import PokerTable

class GameApp:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(CONFIG.title)

        self.screen = pygame.display.set_mode((CONFIG.width, CONFIG.height), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.running = True

        self.ui = UIManager()
        self.table = PokerTable()
        self.table.start_new_game()
        self.ui.table = self.table  # type: ignore[attr-defined]
        self.active_screen = MainMenuScreen(self.ui, table=self.table, on_quit=self.quit)
        setattr(self.active_screen, "table", self.table)

    def quit(self) -> None:
        self.running = False

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(CONFIG.fps) / 1000.0
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                else:
                    self.active_screen.handle_event(event)

            self.active_screen.update(dt)
            next_screen = self.active_screen.pop_requested_screen()
            if next_screen is not None:
                setattr(next_screen, "table", self.table)
                self.active_screen = next_screen

            self.screen.fill(CONFIG.bg_color)
            self.active_screen.draw(self.screen)
            pygame.display.flip()

        pygame.quit()