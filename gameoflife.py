"""Conway's Game of Life - pygame edition.

Run it with `python gameoflife.py`. The window is resizable: the grid grows
and shrinks with it, keeping the cell size constant so the colony is never
squashed. Live cells are drawn as green dots.
"""

import random
import sys

import pygame

# --- Configuration ---
CELL_SIZE = 14
DEFAULT_SIZE = (960, 680)
MIN_SIZE = (320, 240)

COLOR_BG = (8, 14, 10)
COLOR_GRID = (18, 32, 23)
COLOR_LIVE = (60, 220, 90)
COLOR_NEWBORN = (150, 250, 175)
COLOR_DYING = (30, 84, 44)
COLOR_TEXT = (110, 190, 130)
COLOR_TEXT_DIM = (60, 110, 75)
COLOR_PANEL = (10, 20, 14)
COLOR_PANEL_EDGE = (46, 120, 66)
COLOR_TITLE = (150, 250, 175)
COLOR_SELECTED = (26, 58, 36)
COLOR_CURSOR = (90, 170, 115)

SCENE_MENU = "menu"
SCENE_SIM = "sim"
MENU_SPEED = 6              # generations per second behind the menu panel
MENU_PANEL_MAX_W = 640
MENU_PAD = 22
TITLE_SIZES = (34, 28, 22, 18, 15, 13)
BODY_SIZES = (15, 14, 13, 12, 11, 10, 9, 8)
ITEM_SIZES = (19, 17, 15, 13, 12, 11)

DEFAULT_SPEED = 10          # generations per second
MIN_SPEED, MAX_SPEED = 1, 60

# Holding the speed keys rolls the number. The first step comes from the key
# press itself; the roll only starts once the key has been down this long, so
# a quick tap moves by exactly one.
SPEED_HOLD_DELAY = 0.35     # seconds held before the number starts rolling
SPEED_ROLL_RATE = 10        # steps per second when the roll begins
SPEED_ROLL_MAX_RATE = 55    # ...and once it is up to full tilt
SPEED_ROLL_RAMP = 1.0       # seconds of holding to get from one to the other
SPEED_UP_KEYS = (pygame.K_UP, pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS)
SPEED_DOWN_KEYS = (pygame.K_DOWN, pygame.K_MINUS, pygame.K_KP_MINUS)
RANDOM_DENSITY = 0.22

# Effects are measured in generations, not seconds, so they read the same at
# 1 step per second as at 60. Much over one generation and the whole board
# looks like newborns and ghosts instead of a green colony.
GLOW_GENERATIONS = 0.9      # how long a newborn stays pale
FADE_GENERATIONS = 1.1      # how long a dead cell lingers


class GameOfLife:
    """The simulation itself - no rendering, no pygame."""

    def __init__(self, rows, cols, wrap=True):
        """Create an empty `rows` x `cols` board.

        With `wrap` the board is a torus, so gliders sail off one edge and
        return on the other instead of dying against a wall.
        """
        self.rows = rows
        self.cols = cols
        self.wrap = wrap
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
        return sum(sum(row) for row in self.grid)

    def count_neighbors(self, r, c):
        """Counts the number of live neighbors for a cell at (r, c)."""
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
        """Applies the rules of Conway's Game of Life to create the next state.

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

    def randomize(self, density=RANDOM_DENSITY):
        self.grid = [
            [1 if random.random() < density else 0 for _ in range(self.cols)]
            for _ in range(self.rows)
        ]
        self.generation = 0
        self.born = {(r, c) for r in range(self.rows)
                     for c in range(self.cols) if self.grid[r][c]}
        self.died = set()

    def clear(self):
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


class LifeApp:
    """Draws the simulation and handles input."""

    def __init__(self, size=DEFAULT_SIZE):
        pygame.init()
        pygame.display.set_caption("Conway's Game of Life")
        self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas,dejavusansmono,monospace", 15)

        rows, cols = self._grid_shape(self.screen.get_size())
        self.game = GameOfLife(rows, cols)
        self.game.randomize()

        self.speed = DEFAULT_SPEED
        self.paused = False
        self.show_grid = True
        self.accumulator = 0.0
        self.glow = {}   # cells born recently -> 1.0 fading to 0
        self.fade = {}   # cells died recently -> 1.0 fading to 0
        self.running = True

        self.scene = SCENE_MENU
        self.selected = 0
        self.item_rects = []
        # Painting: which value the drag is writing, and the last cell it
        # touched so a fast drag can be joined up into a line
        self.painting = None
        self.last_painted = None
        # How long the speed key has been held, and the leftover time owed to
        # the roll once it starts
        self.speed_held = 0.0
        self.roll_owed = 0.0

        # A steady live cell always looks the same, so draw that dot once and
        # blit copies of it. Only the handful of glowing or fading cells need
        # a real circle drawn per frame.
        self.dot = self._make_dot(COLOR_LIVE)
        self.background = None
        self.hud_cache = (None, None)
        self.keys_hint = self.font.render(
            "DRAG draw   RIGHT-DRAG erase   SPACE play/pause   N step   "
            "R random   C clear   G grid   UP/DOWN speed   ESC menu",
            True,
            COLOR_TEXT_DIM,
        )
        self.rebuild_background()
        self.build_menu()

    @staticmethod
    def _grid_shape(size):
        w, h = size
        return max(1, h // CELL_SIZE), max(1, w // CELL_SIZE)

    @staticmethod
    def _make_dot(color):
        """A single lifeform, pre-drawn on a transparent square."""
        surface = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
        half = CELL_SIZE // 2
        pygame.draw.circle(surface, color, (half, half), max(1, CELL_SIZE // 2 - 1))
        return surface

    # --- Menu ---

    MENU_ITEMS = ("Start with a random soup",
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

    def build_menu(self):
        """Lay the menu out for the current window size.

        Rather than guessing breakpoints, this tries the fullest version of the
        screen first and falls back - shorter wording, then smaller type - until
        something actually fits. The three rules always survive; they are the
        point of the screen.
        """
        w, h = self.screen.get_size()
        inner = self.panel_width(w) - MENU_PAD * 2
        avail_h = h - 16
        title = "CONWAY'S GAME OF LIFE"

        versions = (
            (self.INTRO + self.RULES + self.OUTRO, self.FOOTER),
            (self.INTRO + self.RULES, self.FOOTER),
            (self.RULES, self.FOOTER),
            (self.RULES, self.FOOTER_SHORT),
            (self.RULES_SHORT, self.FOOTER_SHORT),
        )
        for lines, footer in versions:
            for cut in range(len(BODY_SIZES)):
                body_font = fit_font([ln for ln in lines if ln] + [footer],
                                     inner, BODY_SIZES[cut:])
                title_font = fit_font([title], inner,
                                      TITLE_SIZES[min(cut, len(TITLE_SIZES) - 1):],
                                      bold=True)
                self.item_font = fit_font(
                    self.MENU_ITEMS, inner - 24,
                    ITEM_SIZES[min(cut, len(ITEM_SIZES) - 1):])

                self.menu_title = title_font.render(title, True, COLOR_TITLE)
                self.menu_blurb = [body_font.render(ln, True, COLOR_TEXT)
                                   for ln in lines]
                self.menu_footer = body_font.render(footer, True, COLOR_TEXT_DIM)
                self.layout_menu()

                widest = max([s.get_width() for s in self.menu_blurb]
                             + [self.menu_title.get_width(),
                                self.menu_footer.get_width()])
                if widest <= inner and self.required_h <= avail_h:
                    return
        # Nothing fit even at the smallest; the last attempt is the best there is

    @staticmethod
    def panel_width(w):
        """Reads as a dialog, not a band stretched across a wide monitor."""
        return min(max(360, w - 48), MENU_PANEL_MAX_W, w - 16)

    def layout_menu(self):
        """Work out the panel rect and where each clickable item sits."""
        w, h = self.screen.get_size()
        pad = MENU_PAD
        line_h = self.menu_blurb[0].get_height()
        item_h = self.item_font.get_height() + 12

        body_h = (self.menu_title.get_height() + 14
                  + len(self.menu_blurb) * line_h + 16
                  + len(self.MENU_ITEMS) * (item_h + 6) + 10
                  + self.menu_footer.get_height())
        # What the content actually wants, before the window clamps it - this
        # is what build_menu tests its fallbacks against
        self.required_h = body_h + pad * 2
        panel_w = self.panel_width(w)
        panel_h = min(self.required_h, h - 16)
        self.panel = pygame.Rect(0, 0, panel_w, panel_h)
        self.panel.center = (w // 2, h // 2)

        y = self.panel.top + pad + self.menu_title.get_height() + 14
        y += len(self.menu_blurb) * line_h + 16
        self.item_rects = []
        for _ in self.MENU_ITEMS:
            rect = pygame.Rect(self.panel.left + pad, y, panel_w - pad * 2, item_h)
            self.item_rects.append(rect)
            y += item_h + 6

    def draw_menu(self):
        """The colony keeps running behind the panel, dimmed down."""
        self.screen.blit(self.background, (0, 0))
        self.draw_cells()
        veil = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        veil.fill((*COLOR_BG, 205))
        self.screen.blit(veil, (0, 0))

        pygame.draw.rect(self.screen, COLOR_PANEL, self.panel, border_radius=10)
        pygame.draw.rect(self.screen, COLOR_PANEL_EDGE, self.panel, width=1,
                         border_radius=10)

        pad = 22
        cx = self.panel.centerx
        y = self.panel.top + pad
        self.screen.blit(self.menu_title,
                         self.menu_title.get_rect(midtop=(cx, y)))
        y += self.menu_title.get_height() + 14
        for line in self.menu_blurb:
            self.screen.blit(line, line.get_rect(midtop=(cx, y)))
            y += line.get_height()

        mouse = pygame.mouse.get_pos()
        for i, (label, rect) in enumerate(zip(self.MENU_ITEMS, self.item_rects)):
            if rect.collidepoint(mouse):
                self.selected = i
            chosen = i == self.selected
            if chosen:
                pygame.draw.rect(self.screen, COLOR_SELECTED, rect, border_radius=6)
                pygame.draw.rect(self.screen, COLOR_PANEL_EDGE, rect, width=1,
                                 border_radius=6)
            text = self.item_font.render(
                label, True, COLOR_TITLE if chosen else COLOR_TEXT)
            self.screen.blit(text, text.get_rect(center=rect.center))

        self.screen.blit(
            self.menu_footer,
            self.menu_footer.get_rect(midbottom=(cx, self.panel.bottom - pad + 6)))

    def menu_key(self, key):
        if key in (pygame.K_ESCAPE, pygame.K_q):
            self.running = False
        elif key in (pygame.K_DOWN, pygame.K_TAB):
            self.selected = (self.selected + 1) % len(self.MENU_ITEMS)
        elif key == pygame.K_UP:
            self.selected = (self.selected - 1) % len(self.MENU_ITEMS)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.activate(self.selected)

    def activate(self, index):
        """Run whichever menu item was chosen."""
        self.stop_painting()
        if index == 0:
            self.game.randomize()
            self.reset_effects(self.game.born)
            self.paused = False
            self.scene = SCENE_SIM
        elif index == 1:
            self.game.clear()
            self.reset_effects()
            # An empty board with nothing happening is a canvas, so hold still
            # and let them draw before the rules start eating their work
            self.paused = True
            self.scene = SCENE_SIM
        else:
            self.running = False

    def rebuild_background(self):
        """Cache the empty board so grid lines aren't redrawn every frame."""
        self.background = pygame.Surface(self.screen.get_size())
        self.background.fill(COLOR_BG)
        if self.show_grid:
            w, h = self.background.get_size()
            for c in range(self.game.cols + 1):
                x = c * CELL_SIZE
                pygame.draw.line(self.background, COLOR_GRID, (x, 0), (x, h))
            for r in range(self.game.rows + 1):
                y = r * CELL_SIZE
                pygame.draw.line(self.background, COLOR_GRID, (0, y), (w, y))

    # --- Loop ---

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                self.on_resize(event.size)
            elif event.type == pygame.KEYDOWN:
                if self.scene == SCENE_MENU:
                    self.menu_key(event.key)
                else:
                    self.on_key(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if self.scene == SCENE_MENU:
                    if event.button == 1:
                        for i, rect in enumerate(self.item_rects):
                            if rect.collidepoint(event.pos):
                                self.activate(i)
                                break
                else:
                    self.start_painting(event.pos, event.button)
            elif event.type == pygame.MOUSEBUTTONUP:
                self.stop_painting()
            elif event.type == pygame.MOUSEMOTION and self.scene == SCENE_SIM:
                self.paint_to(event.pos)

    def on_resize(self, size):
        w = max(MIN_SIZE[0], size[0])
        h = max(MIN_SIZE[1], size[1])
        # Always re-take the surface rather than trusting the old handle to
        # have followed the window; everything below is sized from it
        self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
        self.game.resize(*self._grid_shape((w, h)))
        self.glow.clear()
        self.fade.clear()
        self.stop_painting()
        self.rebuild_background()
        self.build_menu()

    def on_key(self, key):
        if key == pygame.K_ESCAPE:
            # Drop any drag in progress, or it would resume on the way back
            self.stop_painting()
            self.scene = SCENE_MENU
        elif key == pygame.K_q:
            self.running = False
        elif key == pygame.K_SPACE:
            self.paused = not self.paused
        elif key == pygame.K_n and self.paused:
            self.step()
        elif key == pygame.K_r:
            self.game.randomize()
            self.reset_effects(self.game.born)
        elif key == pygame.K_c:
            self.game.clear()
            self.reset_effects()
        elif key == pygame.K_g:
            self.show_grid = not self.show_grid
            self.rebuild_background()
        elif key in SPEED_UP_KEYS:
            self.adjust_speed(1)
        elif key in SPEED_DOWN_KEYS:
            self.adjust_speed(-1)

    def adjust_speed(self, delta):
        """The one place the speed number moves, pressed or held."""
        self.speed = max(MIN_SPEED, min(MAX_SPEED, self.speed + delta))

    def update_speed_hold(self, dt):
        """Roll the speed while a speed key is held down.

        `on_key` already applied the initial press, so nothing happens here
        until the key has been down for SPEED_HOLD_DELAY - that gap is what
        keeps a tap from counting twice. The roll then accelerates, so a long
        hold crosses the whole range without sixty separate presses.
        """
        keys = pygame.key.get_pressed()
        up = any(keys[k] for k in SPEED_UP_KEYS)
        down = any(keys[k] for k in SPEED_DOWN_KEYS)
        direction = int(up) - int(down)   # both held cancels out

        if direction == 0:
            self.speed_held = 0.0
            self.roll_owed = 0.0
            return

        self.speed_held += dt
        if self.speed_held < SPEED_HOLD_DELAY:
            return   # still within the initial press that on_key handled

        rolling = self.speed_held - SPEED_HOLD_DELAY
        ramp = min(1.0, rolling / SPEED_ROLL_RAMP)
        rate = SPEED_ROLL_RATE + (SPEED_ROLL_MAX_RATE - SPEED_ROLL_RATE) * ramp

        self.roll_owed += dt
        interval = 1.0 / rate
        while self.roll_owed >= interval:
            self.roll_owed -= interval
            self.adjust_speed(direction)

    # --- Drawing life with the mouse ---

    def cell_at(self, pos):
        return pos[1] // CELL_SIZE, pos[0] // CELL_SIZE

    def start_painting(self, pos, button):
        if button not in (1, 3):
            return
        self.painting = 1 if button == 1 else 0
        self.last_painted = None
        self.paint_to(pos)

    def stop_painting(self):
        self.painting = None
        self.last_painted = None

    def paint_to(self, pos):
        """Paint from the last touched cell up to this one.

        The mouse can cross several cells between two frames, so painting only
        the cell under the cursor would leave a dotted trail on a quick drag.
        """
        if self.painting is None:
            return
        cell = self.cell_at(pos)
        if cell == self.last_painted:
            return
        if self.last_painted is None:
            cells = [cell]
        else:
            cells = bresenham(self.last_painted, cell)
        for r, c in cells:
            if self.game.set_cell(r, c, self.painting):
                # Give drawn cells the same flare as newborns, so they show up
                # even while the simulation is running
                if self.painting:
                    self.glow[(r, c)] = 1.0
                    self.fade.pop((r, c), None)
                else:
                    self.fade[(r, c)] = 1.0
                    self.glow.pop((r, c), None)
        self.last_painted = cell

    def reset_effects(self, born=()):
        self.glow = {cell: 1.0 for cell in born}
        self.fade.clear()
        self.accumulator = 0.0

    def step(self):
        self.game.next_generation()
        for cell in self.game.born:
            self.glow[cell] = 1.0
        for cell in self.game.died:
            self.fade[cell] = 1.0
            self.glow.pop(cell, None)

    def update(self, dt):
        if self.scene == SCENE_SIM:
            self.update_speed_hold(dt)
        else:
            # UP/DOWN pick menu items rather than speed, so hold nothing over
            self.speed_held = 0.0
            self.roll_owed = 0.0

        # The menu keeps a colony ticking over behind its panel
        rate = MENU_SPEED if self.scene == SCENE_MENU else self.speed
        if self.scene == SCENE_MENU or not self.paused:
            self.accumulator += dt
            interval = 1.0 / rate
            # Cap the catch-up so a stalled frame can't trigger a burst of steps
            steps = min(4, int(self.accumulator / interval))
            for _ in range(steps):
                self.accumulator -= interval
                self.step()
            if self.accumulator > interval:
                self.accumulator = 0.0

        # Decay is paced by the sim speed, so one generation of change is
        # always about one effect's worth of flicker
        self.decay(self.glow, dt * rate / GLOW_GENERATIONS)
        self.decay(self.fade, dt * rate / FADE_GENERATIONS)

    @staticmethod
    def decay(effects, amount):
        for cell in [c for c, v in effects.items() if v <= amount]:
            del effects[cell]
        for cell in effects:
            effects[cell] -= amount

    # --- Drawing ---

    def draw(self):
        if self.scene == SCENE_MENU:
            self.draw_menu()
        else:
            self.screen.blit(self.background, (0, 0))
            self.draw_cells()
            self.draw_cursor()
            self.draw_hud()
        pygame.display.flip()

    def draw_cursor(self):
        """Outline the cell under the pointer so drawing has a clear target."""
        if not pygame.mouse.get_focused():
            return
        r, c = self.cell_at(pygame.mouse.get_pos())
        if 0 <= r < self.game.rows and 0 <= c < self.game.cols:
            rect = pygame.Rect(c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(self.screen, COLOR_CURSOR, rect, width=1)

    def draw_cells(self):
        radius = max(1, CELL_SIZE // 2 - 1)
        half = CELL_SIZE // 2
        glow, fade = self.glow, self.fade

        # Cells that just died linger for a moment as a dimming dot
        for (r, c), amount in fade.items():
            center = (c * CELL_SIZE + half, r * CELL_SIZE + half)
            color = lerp(COLOR_BG, COLOR_DYING, amount)
            pygame.draw.circle(self.screen, color, center, max(1, int(radius * amount)))

        steady = []
        add = steady.append
        dot = self.dot
        for r, row in enumerate(self.game.grid):
            y = r * CELL_SIZE
            for c, alive in enumerate(row):
                if not alive:
                    continue
                amount = glow.get((r, c))
                if amount is None:
                    add((dot, (c * CELL_SIZE, y)))
                else:
                    # A newborn flares pale green, then settles into the colony
                    pygame.draw.circle(
                        self.screen,
                        lerp(COLOR_LIVE, COLOR_NEWBORN, amount),
                        (c * CELL_SIZE + half, y + half),
                        radius + (1 if amount > 0.5 else 0),
                    )
        if steady:
            self.screen.blits(steady, doreturn=False)

    def draw_hud(self):
        state = "PAUSED" if self.paused else "RUNNING"
        key = (self.game.generation, self.paused, self.speed,
               self.game.cols, self.game.rows)
        if self.hud_cache[0] != key:
            status = (
                f"GEN {self.game.generation:<6} POP {self.game.population:<6} "
                f"{self.game.cols}x{self.game.rows}  {self.speed}/s  {state}"
            )
            self.hud_cache = (key, self.font.render(status, True, COLOR_TEXT))
        # The colony is busy enough that bare text gets lost in it, so each
        # line sits on a dark band
        self.blit_banded(self.hud_cache[1], 4)
        self.blit_banded(self.keys_hint, self.screen.get_height() - 26)

    def blit_banded(self, text, y):
        w = self.screen.get_width()
        band = pygame.Surface((w, text.get_height() + 8), pygame.SRCALPHA)
        band.fill((*COLOR_BG, 215))
        self.screen.blit(band, (0, y))
        self.screen.blit(text, (10, y + 4))


def fit_font(lines, max_width, sizes, bold=False):
    """The largest of `sizes` that renders every line within `max_width`."""
    font = None
    for size in sizes:
        font = pygame.font.SysFont("consolas,dejavusansmono,monospace", size, bold=bold)
        if all(font.size(line)[0] <= max_width for line in lines):
            return font
    return font   # nothing fit; the smallest is the best we can do


def bresenham(start, end):
    """Every cell on the straight line between two cells, inclusive."""
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


def lerp(a, b, t):
    """Blend between two colors; t of 0 gives `a`, 1 gives `b`."""
    t = max(0.0, min(1.0, t))
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


if __name__ == "__main__":
    LifeApp().run()
    sys.exit()
