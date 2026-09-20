"""The application shell: one window, one clock, one current scene."""

import sys

import pygame

from .config import SETTINGS
from .game import Simulation
from .input import SpeedController, Viewport
from .render import BoardRenderer, FontBook, Hud
from .scenes import MenuScene, SimulationScene
from .sound import Instrument

MENU = "menu"
SIM = "sim"
FPS = 60


def _make_dpi_aware():
    """Opt out of Windows' bitmap DPI scaling, which blurs the whole window.

    Without this, an unaware process gets stretched to match the display's
    scale factor instead of rendering at native resolution, so everything -
    text, grid lines, cells - looks soft. Must run before the window exists.
    """
    if sys.platform != "win32":
        return
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)   # per-monitor v2
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()   # system DPI aware
        except (AttributeError, OSError):
            pass


class LifeApp:
    """Owns the window and the shared pieces, and drives the current scene.

    The scene decides what a key or a frame means; this class only pumps
    events, handles the window itself, and hands everything else on.
    """

    def __init__(self, size=None, settings=SETTINGS):
        self.settings = settings
        _make_dpi_aware()
        pygame.init()
        pygame.display.set_caption("Conway's Game of Life")
        self.screen = pygame.display.set_mode(size or settings.default_size,
                                              pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.running = True

        self.fullscreen = False
        self.windowed_size = self.screen.get_size()

        self.viewport = Viewport(settings)
        self.fonts = FontBook()
        self.simulation = Simulation(*self.viewport.grid_shape(self.screen.get_size()))
        self.simulation.randomize()
        # The colony behind the menu is meant to look long-established, so the
        # opening frame shows a settled board rather than a screen of newborns
        self.simulation.effects.clear()
        self.speed = SpeedController()
        self.renderer = BoardRenderer(self.viewport, settings=settings)
        self.renderer.rebuild_background(self.screen.get_size(), self.simulation.game)
        self.hud = Hud(self.fonts)
        self.instrument = Instrument()

        # Both scenes are built once and kept, so speed, pause state and menu
        # selection all survive a trip back to the menu and out again
        self.scenes = {MENU: MenuScene(self), SIM: SimulationScene(self)}
        self.scene = self.scenes[MENU]

    # --- Scene switching, called by the scenes themselves ---

    def set_scene(self, name):
        """Hand over to another scene, letting each side tidy up first."""
        if self.scene is self.scenes[name]:
            return
        self.scene.on_exit()
        self.scene = self.scenes[name]
        self.scene.on_enter()

    def show_menu(self):
        """Back to the title screen."""
        self.set_scene(MENU)

    def start_random(self):
        """Begin from a random soup, already running."""
        self.simulation.randomize()
        self.scenes[SIM].paused = False
        self.set_scene(SIM)

    def start_empty(self):
        """Begin from an empty board, held still.

        An empty board with nothing happening is a canvas, so hold still and
        let them draw before the rules start eating their work.
        """
        self.simulation.clear()
        self.scenes[SIM].paused = True
        self.set_scene(SIM)

    def toggle_grid(self):
        """Show or hide the grid lines, rebuilding the cached background."""
        self.renderer.set_grid_visible(not self.renderer.show_grid,
                                       self.screen.get_size(),
                                       self.simulation.game)

    def quit(self):
        """Leave the loop at the end of this frame."""
        self.running = False

    # --- Loop ---

    def run(self):
        """Run until something asks to quit, then shut pygame down."""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.scene.update(dt)
            self.draw()
        pygame.quit()

    def handle_events(self):
        """Deal with the window's own events; the scene gets the rest."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                if not self.fullscreen:
                    self.on_resize(event.size)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                self.toggle_fullscreen()
            else:
                self.scene.handle_event(event)

    def on_resize(self, size):
        """Grow or shrink the board to match the window, keeping cells the size."""
        w = max(self.settings.min_size[0], size[0])
        h = max(self.settings.min_size[1], size[1])
        self._apply_mode((w, h), pygame.RESIZABLE)

    def toggle_fullscreen(self):
        """Switch between the resizable window and borderless fullscreen.

        The windowed size is remembered across the switch, so coming back out
        of fullscreen restores the size the player had rather than snapping to
        some default.
        """
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.windowed_size = self.screen.get_size()
            self._apply_mode((0, 0), pygame.FULLSCREEN)
        else:
            self._apply_mode(self.windowed_size, pygame.RESIZABLE)

    def _apply_mode(self, size, flags):
        """Re-take the surface at `size` with `flags` and re-flow everything.

        Always re-take the surface rather than trusting the old handle to
        have followed the window; everything below is sized from it.
        """
        self.screen = pygame.display.set_mode(size, flags)
        size = self.screen.get_size()
        self.simulation.resize(*self.viewport.grid_shape(size))
        self.renderer.rebuild_background(size, self.simulation.game)
        # Both scenes re-flow, so the menu is already laid out when it is next
        # shown rather than only when it happens to be on screen
        for scene in self.scenes.values():
            scene.on_resize(size)

    def draw(self):
        """Let the scene paint, then show the frame."""
        self.scene.draw(self.screen)
        pygame.display.flip()
