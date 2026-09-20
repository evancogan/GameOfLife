"""Turning pointers and keys into board coordinates and speed changes."""

import pygame

from .config import SETTINGS, SPEED


class Viewport:
    """Maps between window pixels and board cells.

    Cell size is fixed, so a bigger window means more cells rather than bigger
    ones - the colony is never squashed by a resize.
    """

    def __init__(self, settings=SETTINGS):
        self.cell_size = settings.cell_size

    def grid_shape(self, window_size):
        """The (rows, cols) that fill a window of this size."""
        w, h = window_size
        return max(1, h // self.cell_size), max(1, w // self.cell_size)

    def cell_at(self, pos):
        """The (row, col) under a pixel position."""
        return pos[1] // self.cell_size, pos[0] // self.cell_size

    def cell_rect(self, r, c):
        """The pixel rect a cell occupies."""
        return pygame.Rect(c * self.cell_size, r * self.cell_size,
                           self.cell_size, self.cell_size)

    def cell_center(self, r, c):
        """The pixel centre of a cell, where its dot is drawn."""
        half = self.cell_size // 2
        return c * self.cell_size + half, r * self.cell_size + half

    @staticmethod
    def line(start, end):
        """Every cell on the straight line between two cells, inclusive.

        Bresenham's algorithm: the mouse can cross several cells between two
        frames, so painting only the cell under the cursor would leave a dotted
        trail on a quick drag.
        """
        (r0, c0), (r1, c1) = start, end
        dr, dc = abs(r1 - r0), abs(c1 - c0)
        sr = 1 if r0 < r1 else -1
        sc = 1 if c0 < c1 else -1
        err = dr - dc
        cells = []
        while True:
            cells.append((r0, c0))
            if (r0, c0) == (r1, c1):
                return cells
            err2 = err * 2
            if err2 > -dc:
                err -= dc
                r0 += sr
            if err2 < dr:
                err += dr
                c0 += sc


class Painter:
    """Draws life with the mouse: left button writes, right button erases."""

    DRAW_BUTTON = 1
    ERASE_BUTTON = 3

    def __init__(self, simulation, viewport):
        self.simulation = simulation
        self.viewport = viewport
        # Which value this drag is writing, and the last cell it touched so a
        # fast drag can be joined up into a line
        self.value = None
        self.last_cell = None

    @property
    def active(self):
        """True while a drag is in progress."""
        return self.value is not None

    def begin(self, pos, button):
        """Start a drag, painting the cell under the pointer straight away.

        Returns the cells the drag actually turned alive, so the caller can
        give hand-drawn cells the same chime as a birth from the rules.
        """
        if button not in (self.DRAW_BUTTON, self.ERASE_BUTTON):
            return []
        self.value = 1 if button == self.DRAW_BUTTON else 0
        self.last_cell = None
        return self.drag_to(pos)

    def end(self):
        """Finish the drag, if there is one."""
        self.value = None
        self.last_cell = None

    def drag_to(self, pos):
        """Paint from the last touched cell up to the one under `pos`.

        Returns the cells that were newly painted alive by this call.
        """
        if self.value is None:
            return []
        cell = self.viewport.cell_at(pos)
        if cell == self.last_cell:
            return []
        if self.last_cell is None:
            cells = [cell]
        else:
            cells = self.viewport.line(self.last_cell, cell)
        painted = [(r, c) for r, c in cells if self.simulation.paint(r, c, self.value)]
        self.last_cell = cell
        return painted if self.value else []


class SpeedController:
    """The generations-per-second number, and the roll when a key is held.

    A press is applied by `nudge`; the roll only starts once the key has been
    down for `hold_delay`, and that gap is what keeps a tap from counting twice.
    """

    UP_KEYS = (pygame.K_UP, pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS)
    DOWN_KEYS = (pygame.K_DOWN, pygame.K_MINUS, pygame.K_KP_MINUS)

    def __init__(self, settings=SPEED):
        self.settings = settings
        self.value = settings.default
        self.held = 0.0       # how long a speed key has been down
        self.owed = 0.0       # leftover time owed to the roll once it starts

    def nudge(self, delta):
        """The one place the speed number moves, pressed or held."""
        self.value = max(self.settings.minimum,
                         min(self.settings.maximum, self.value + delta))

    def set(self, value):
        """Set the speed directly, e.g. from a slider - still clamped to range."""
        self.value = max(self.settings.minimum,
                         min(self.settings.maximum, round(value)))

    def direction_for(self, key):
        """+1, -1 or 0 for a key that was just pressed."""
        if key in self.UP_KEYS:
            return 1
        if key in self.DOWN_KEYS:
            return -1
        return 0

    def release(self):
        """Forget the hold - used when the menu takes over the arrow keys."""
        self.held = 0.0
        self.owed = 0.0

    def update(self, dt, pressed=None):
        """Roll the speed while a speed key is held down.

        The roll accelerates, so a long hold crosses the whole range without
        sixty separate presses. `pressed` defaults to the real keyboard, and
        is there so the ramp can be driven without one.
        """
        keys = pygame.key.get_pressed() if pressed is None else pressed
        up = any(keys[k] for k in self.UP_KEYS)
        down = any(keys[k] for k in self.DOWN_KEYS)
        direction = int(up) - int(down)   # both held cancels out

        if direction == 0:
            self.release()
            return

        self.held += dt
        if self.held < self.settings.hold_delay:
            return   # still within the initial press the key handler applied

        rolling = self.held - self.settings.hold_delay
        ramp = min(1.0, rolling / self.settings.roll_ramp)
        rate = (self.settings.roll_rate
                + (self.settings.roll_max_rate - self.settings.roll_rate) * ramp)

        self.owed += dt
        interval = 1.0 / rate
        while self.owed >= interval:
            self.owed -= interval
            self.nudge(direction)
