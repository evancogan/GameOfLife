"""The simulation itself - no pygame, no rendering, no input.

Everything in here is plain Python data, which is what makes the rules
straightforward to unit test without opening a window.
"""

import random

from .config import EFFECTS, SETTINGS


class GameOfLife:
    """A board of live and dead cells that steps by Conway's four rules."""

    def __init__(self, rows, cols, wrap=True, settings=SETTINGS):
        """Create an empty `rows` x `cols` board.

        With `wrap` the board is a torus, so gliders sail off one edge and
        return on the other instead of dying against a wall.
        """
        self.rows = rows
        self.cols = cols
        self.wrap = wrap
        self.settings = settings
        self.grid = [[0] * cols for _ in range(rows)]
        self.generation = 0
        self.born = set()
        self.died = set()

    @classmethod
    def from_grid(cls, grid, wrap=True):
        """Build a game from an existing 2D list of 0s and 1s."""
        rows = len(grid)
        cols = len(grid[0]) if rows > 0 else 0
        game = cls(rows, cols, wrap=wrap)
        game.grid = [list(row) for row in grid]
        return game

    @property
    def population(self):
        """How many cells are currently alive."""
        return sum(sum(row) for row in self.grid)

    def count_neighbors(self, r, c):
        """Count the live neighbours of the cell at (r, c)."""
        count = 0
        for i in range(r - 1, r + 2):
            for j in range(c - 1, c + 2):
                # Skip the cell itself
                if i == r and j == c:
                    continue

                if self.wrap:
                    count += self.grid[i % self.rows][j % self.cols]
                elif 0 <= i < self.rows and 0 <= j < self.cols:
                    count += self.grid[i][j]
        return count

    def next_generation(self):
        """Apply the rules once, recording which cells were born and which died.

        Rather than testing all eight neighbors of every cell, each live cell
        adds one to its neighbors' tally. Empty space then costs nothing, which
        is what keeps a full-screen board smooth.
        """
        rows, cols, wrap = self.rows, self.cols, self.wrap
        counts = [[0] * cols for _ in range(rows)]

        for r in range(rows):
            row = self.grid[r]
            for c in range(cols):
                if not row[c]:
                    continue
                for dr in (-1, 0, 1):
                    i = r + dr
                    if wrap:
                        i %= rows
                    elif not 0 <= i < rows:
                        continue
                    tally = counts[i]
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        j = c + dc
                        if wrap:
                            j %= cols
                        elif not 0 <= j < cols:
                            continue
                        tally[j] += 1

        new_grid = [[0] * cols for _ in range(rows)]
        born, died = set(), set()

        for r in range(rows):
            old_row, new_row, tally = self.grid[r], new_grid[r], counts[r]
            for c in range(cols):
                n = tally[c]
                if old_row[c]:
                    # Survival on 2 or 3 neighbors; under/overpopulation otherwise
                    if n == 2 or n == 3:
                        new_row[c] = 1
                    else:
                        died.add((r, c))
                elif n == 3:
                    # Reproduction
                    new_row[c] = 1
                    born.add((r, c))

        self.grid = new_grid
        self.generation += 1
        self.born, self.died = born, died
        return self.grid

    def toggle(self, r, c):
        """Flip a single cell, returning its new state."""
        if 0 <= r < self.rows and 0 <= c < self.cols:
            self.grid[r][c] ^= 1
            return self.grid[r][c]
        return 0

    def set_cell(self, r, c, value):
        """Set one cell, ignoring anything off the board. True if it changed."""
        if 0 <= r < self.rows and 0 <= c < self.cols and self.grid[r][c] != value:
            self.grid[r][c] = value
            return True
        return False

    def randomize(self, density=None):
        """Fill the board with a random soup and start the count over."""
        if density is None:
            density = self.settings.random_density
        self.grid = [
            [1 if random.random() < density else 0 for _ in range(self.cols)]
            for _ in range(self.rows)
        ]
        self.generation = 0
        self.born = {(r, c) for r in range(self.rows)
                     for c in range(self.cols) if self.grid[r][c]}
        self.died = set()

    def clear(self):
        """Empty the board and start the count over."""
        self.grid = [[0] * self.cols for _ in range(self.rows)]
        self.generation = 0
        self.born = set()
        self.died = set()

    def resize(self, rows, cols):
        """Grow or crop the board, keeping whatever colony already exists."""
        if rows == self.rows and cols == self.cols:
            return
        new_grid = [[0] * cols for _ in range(rows)]
        for r in range(min(rows, self.rows)):
            old_row, new_row = self.grid[r], new_grid[r]
            for c in range(min(cols, self.cols)):
                new_row[c] = old_row[c]
        self.grid = new_grid
        self.rows, self.cols = rows, cols
        self.born = set()
        self.died = set()


class CellEffects:
    """Which cells are still flaring or fading, and how much is left of it.

    Both tables map a cell to an intensity running from 1.0 down to 0. Decay is
    paced by the simulation speed, so one generation of change is always about
    one effect's worth of flicker, at 1 step per second or at 60.
    """

    def __init__(self, settings=EFFECTS):
        self.settings = settings
        self.glow = {}   # cells born recently -> 1.0 fading to 0
        self.fade = {}   # cells died recently -> 1.0 fading to 0

    def record_generation(self, born, died):
        """Flare the newborns and start the freshly dead fading."""
        for cell in born:
            self.glow[cell] = 1.0
        for cell in died:
            self.fade[cell] = 1.0
            self.glow.pop(cell, None)

    def record_paint(self, cell, alive):
        """Give a hand-drawn cell the same flare as a newborn.

        Without it, cells drawn into a running colony would be lost among
        everything else moving on the board.
        """
        if alive:
            self.glow[cell] = 1.0
            self.fade.pop(cell, None)
        else:
            self.fade[cell] = 1.0
            self.glow.pop(cell, None)

    def reset(self, born=()):
        """Drop everything in flight, optionally flaring a fresh colony."""
        self.glow = {cell: 1.0 for cell in born}
        self.fade.clear()

    def clear(self):
        """Drop every effect without flaring anything."""
        self.glow.clear()
        self.fade.clear()

    def decay(self, dt, rate):
        """Age both effects by `dt` seconds at `rate` generations per second."""
        self._decay(self.glow, dt * rate / self.settings.glow_generations)
        self._decay(self.fade, dt * rate / self.settings.fade_generations)

    @staticmethod
    def _decay(effects, amount):
        """Drop what has run out, and thin what is left."""
        for cell in [c for c, v in effects.items() if v <= amount]:
            del effects[cell]
        for cell in effects:
            effects[cell] -= amount


class GenerationClock:
    """Turns elapsed seconds into whole generations at a given rate."""

    def __init__(self, settings=EFFECTS):
        self.settings = settings
        self.accumulator = 0.0

    def advance(self, dt, rate):
        """How many steps are owed after `dt` seconds at `rate` per second.

        The catch-up is capped so a single stalled frame cannot trigger a burst
        of steps that jumps the colony forward.
        """
        self.accumulator += dt
        interval = 1.0 / rate
        steps = min(self.settings.max_catch_up_steps,
                    int(self.accumulator / interval))
        self.accumulator -= steps * interval
        if self.accumulator > interval:
            self.accumulator = 0.0
        return steps

    def reset(self):
        """Forget any part-generation already accumulated."""
        self.accumulator = 0.0


class Simulation:
    """A board, its visual effects and its pacing, kept in step with each other.

    Scenes and the renderer talk to this rather than to a bare `GameOfLife`, so
    nothing has to remember to update the glow and fade tables by hand.
    """

    def __init__(self, rows, cols, wrap=True):
        self.game = GameOfLife(rows, cols, wrap=wrap)
        self.effects = CellEffects()
        self.clock = GenerationClock()

    def step(self):
        """Advance exactly one generation and flare whatever changed."""
        self.game.next_generation()
        self.effects.record_generation(self.game.born, self.game.died)

    def advance(self, dt, rate):
        """Run however many generations `dt` bought, then age the effects."""
        for _ in range(self.clock.advance(dt, rate)):
            self.step()
        self.effects.decay(dt, rate)

    def randomize(self):
        """Reseed with a random soup, flaring the whole colony into life."""
        self.game.randomize()
        self.effects.reset(self.game.born)
        self.clock.reset()

    def clear(self):
        """Wipe the board back to empty."""
        self.game.clear()
        self.effects.reset()
        self.clock.reset()

    def resize(self, rows, cols):
        """Reshape the board, dropping effects that may no longer have a cell."""
        self.game.resize(rows, cols)
        self.effects.clear()

    def paint(self, r, c, alive):
        """Draw or erase one cell by hand. True if the board changed."""
        if not self.game.set_cell(r, c, alive):
            return False
        self.effects.record_paint((r, c), alive)
        return True
