"""The screens the app can show, behind one common interface.

`LifeApp` drives whichever scene is current without knowing which it is, so a
screen's keys, drawing and pacing all live in one class instead of being spread
across branches in the event loop.
"""

from abc import ABC, abstractmethod

import pygame

from .config import SPEED
from .input import Painter
from .render import MenuPanel


class Scene(ABC):
    """One screen: it handles its own events, updates and drawing."""

    def __init__(self, app):
        self.app = app

    @abstractmethod
    def handle_event(self, event):
        """React to a single pygame event."""

    @abstractmethod
    def update(self, dt):
        """Advance by `dt` seconds."""

    @abstractmethod
    def draw(self, surface):
        """Paint a frame."""

    def on_resize(self, size):
        """Re-do any layout that depends on the window size."""

    def on_enter(self):
        """Called when this scene becomes the current one."""

    def on_exit(self):
        """Called when another scene is about to take over."""


class MenuScene(Scene):
    """The title screen: the rules, three choices, and a colony behind it."""

    TITLE = "CONWAY'S GAME OF LIFE"
    ITEMS = ("Start with a random soup",
             "Start from an empty board",
             "Quit")

    INTRO = ["A zero-player game: you plant the first cells,",
             "and four rules decide everything that follows.",
             ""]
    RULES = ["A live cell with 2 or 3 live neighbours survives.",
             "A dead cell with exactly 3 neighbours comes to life.",
             "Anything else dies of loneliness or overcrowding."]
    OUTRO = ["",
             "From those rules alone come gliders, oscillators",
             "and colonies that look uncannily alive."]
    RULES_SHORT = ["2 or 3 neighbours: survive.",
                   "Exactly 3 neighbours: born.",
                   "Anything else: die."]
    FOOTER = "Click and drag to draw life - even while it is running."
    FOOTER_SHORT = "Drag to draw life."

    def __init__(self, app, settings=SPEED):
        super().__init__(app)
        self.settings = settings
        self.selected = 0
        self.panel = MenuPanel(app.fonts)
        self.on_resize(app.screen.get_size())

    @property
    def _versions(self):
        """The wordings to try, fullest first, as (lines, footer) pairs."""
        return (
            (self.INTRO + self.RULES + self.OUTRO, self.FOOTER),
            (self.INTRO + self.RULES, self.FOOTER),
            (self.RULES, self.FOOTER),
            (self.RULES, self.FOOTER_SHORT),
            (self.RULES_SHORT, self.FOOTER_SHORT),
        )

    def on_resize(self, size):
        """Re-flow the panel for the new window size."""
        self.panel.build(size, self.TITLE, self._versions, self.ITEMS)

    def handle_event(self, event):
        """Arrow keys and clicks pick an item; enter or space runs it."""
        if event.type == pygame.KEYDOWN:
            self._on_key(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            index = self.panel.item_at(event.pos)
            if index is not None:
                self.activate(index)

    def _on_key(self, key):
        if key in (pygame.K_ESCAPE, pygame.K_q):
            self.app.quit()
        elif key in (pygame.K_DOWN, pygame.K_TAB):
            self.selected = (self.selected + 1) % len(self.ITEMS)
        elif key == pygame.K_UP:
            self.selected = (self.selected - 1) % len(self.ITEMS)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.activate(self.selected)

    def activate(self, index):
        """Run whichever menu item was chosen."""
        if index == 0:
            self.app.start_random()
        elif index == 1:
            self.app.start_empty()
        else:
            self.app.quit()

    def update(self, dt):
        """Keep a colony ticking over behind the panel, and follow the mouse."""
        # UP/DOWN pick menu items here rather than speed, so hold nothing over
        self.app.speed.release()
        self.app.simulation.advance(dt, self.settings.menu_speed)
        hovered = self.panel.item_at(pygame.mouse.get_pos())
        if hovered is not None:
            self.selected = hovered

    def draw(self, surface):
        """The colony keeps running behind the panel, dimmed down."""
        renderer = self.app.renderer
        renderer.draw_background(surface)
        renderer.draw_cells(surface, self.app.simulation)
        self.panel.draw(surface, self.ITEMS, self.selected)


class SimulationScene(Scene):
    """The board itself: keys, mouse drawing, the HUD and the cursor."""

    def __init__(self, app):
        super().__init__(app)
        self.paused = False
        self.painter = Painter(app.simulation, app.viewport)

    def on_exit(self):
        """Drop any drag in progress, or it would resume on the way back."""
        self.painter.end()

    def on_resize(self, size):
        """The board is reshaped under the pointer, so end any drag."""
        self.painter.end()

    def handle_event(self, event):
        """Route keys to the key map and mouse buttons to the painter."""
        if event.type == pygame.KEYDOWN:
            self._on_key(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._chime(self.painter.begin(event.pos, event.button))
        elif event.type == pygame.MOUSEBUTTONUP:
            self.painter.end()
        elif event.type == pygame.MOUSEMOTION:
            self._chime(self.painter.drag_to(event.pos))

    def _on_key(self, key):
        app = self.app
        if key == pygame.K_ESCAPE:
            app.show_menu()
        elif key == pygame.K_q:
            app.quit()
        elif key == pygame.K_SPACE:
            self.paused = not self.paused
        elif key == pygame.K_n and self.paused:
            app.simulation.step()
            self._chime_births()
        elif key == pygame.K_r:
            app.simulation.randomize()
        elif key == pygame.K_c:
            app.simulation.clear()
        elif key == pygame.K_g:
            app.toggle_grid()
        elif key == pygame.K_m:
            app.instrument.toggle()
        else:
            direction = app.speed.direction_for(key)
            if direction:
                app.speed.nudge(direction)

    def update(self, dt):
        """Roll the speed if a key is held, then run the colony unless paused."""
        self.app.speed.update(dt)
        rate = self.app.speed.value
        if self.paused:
            # Still age the glow and fade so a pause does not freeze them mid-flare
            self.app.simulation.effects.decay(dt, rate)
        else:
            generation = self.app.simulation.game.generation
            self.app.simulation.advance(dt, rate)
            if self.app.simulation.game.generation != generation:
                self._chime_births()

    def _chime_births(self):
        """Let this generation's newborns sound, pitched by row and column."""
        game = self.app.simulation.game
        self.app.instrument.play_births(game.born, game.rows, game.cols)

    def _chime(self, painted_cells):
        """Give hand-drawn cells the same chime as a birth from the rules."""
        game = self.app.simulation.game
        for r, c in painted_cells:
            self.app.instrument.pluck(r, c, game.rows, game.cols)

    def draw(self, surface):
        """Board, pointer outline, then the HUD bands on top."""
        app = self.app
        app.renderer.draw_background(surface)
        app.renderer.draw_cells(surface, app.simulation)
        app.renderer.draw_cursor(surface, app.simulation.game)
        app.hud.draw(surface, app.simulation.game, app.speed.value, self.paused)
