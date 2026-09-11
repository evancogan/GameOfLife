"""Everything that puts pixels on the screen: fonts, the board, the HUD."""

import pygame

from .config import MENU, SETTINGS, THEME


class FontBook:
    """Hands out monospace fonts, and picks the largest size that fits."""

    def __init__(self, theme=THEME):
        self.theme = theme
        self._cache = {}

    def mono(self, size, bold=False):
        """A monospace font at `size`, reused once built."""
        key = (size, bold)
        if key not in self._cache:
            self._cache[key] = pygame.font.SysFont(self.theme.font_name, size,
                                                   bold=bold)
        return self._cache[key]

    def best_fit(self, lines, max_width, sizes, bold=False):
        """The largest of `sizes` that renders every line within `max_width`."""
        font = None
        for size in sizes:
            font = self.mono(size, bold=bold)
            if all(font.size(line)[0] <= max_width for line in lines):
                return font
        return font   # nothing fit; the smallest is the best we can do


class BoardRenderer:
    """Draws the colony, its grid lines and the cell under the pointer."""

    def __init__(self, viewport, theme=THEME, settings=SETTINGS):
        self.viewport = viewport
        self.theme = theme
        self.cell_size = settings.cell_size
        self.show_grid = True
        self.background = None
        # A steady live cell always looks the same, so draw that dot once and
        # blit copies of it. Only the handful of glowing or fading cells need
        # a real circle drawn per frame.
        self.dot = self._make_dot(theme.live)

    def _make_dot(self, color):
        """A single lifeform, pre-drawn on a transparent square."""
        surface = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
        half = self.cell_size // 2
        pygame.draw.circle(surface, color, (half, half), self._radius)
        return surface

    @property
    def _radius(self):
        """The radius of a steady live cell."""
        return max(1, self.cell_size // 2 - 1)

    def set_grid_visible(self, show, size, game):
        """Turn the grid lines on or off and redraw the cached background."""
        self.show_grid = show
        self.rebuild_background(size, game)

    def rebuild_background(self, size, game):
        """Cache the empty board so grid lines aren't redrawn every frame."""
        self.background = pygame.Surface(size)
        self.background.fill(self.theme.bg)
        if not self.show_grid:
            return
        w, h = self.background.get_size()
        for c in range(game.cols + 1):
            x = c * self.cell_size
            pygame.draw.line(self.background, self.theme.grid, (x, 0), (x, h))
        for r in range(game.rows + 1):
            y = r * self.cell_size
            pygame.draw.line(self.background, self.theme.grid, (0, y), (w, y))

    def draw_background(self, surface):
        """Lay down the cached empty board."""
        surface.blit(self.background, (0, 0))

    def draw_cells(self, surface, simulation):
        """Draw the dying, the steady and the newborn, in that order."""
        radius = self._radius
        glow, fade = simulation.effects.glow, simulation.effects.fade
        cell_size = self.cell_size
        half = cell_size // 2

        # Cells that just died linger for a moment as a dimming dot
        for (r, c), amount in fade.items():
            center = (c * cell_size + half, r * cell_size + half)
            color = self.theme.blend(self.theme.bg, self.theme.dying, amount)
            pygame.draw.circle(surface, color, center, max(1, int(radius * amount)))

        steady = []
        add = steady.append
        dot = self.dot
        for r, row in enumerate(simulation.game.grid):
            y = r * cell_size
            for c, alive in enumerate(row):
                if not alive:
                    continue
                amount = glow.get((r, c))
                if amount is None:
                    add((dot, (c * cell_size, y)))
                else:
                    # A newborn flares pale green, then settles into the colony
                    pygame.draw.circle(
                        surface,
                        self.theme.blend(self.theme.live, self.theme.newborn, amount),
                        (c * cell_size + half, y + half),
                        radius + (1 if amount > 0.5 else 0),
                    )
        if steady:
            surface.blits(steady, doreturn=False)

    def draw_cursor(self, surface, game):
        """Outline the cell under the pointer so drawing has a clear target."""
        if not pygame.mouse.get_focused():
            return
        r, c = self.viewport.cell_at(pygame.mouse.get_pos())
        if 0 <= r < game.rows and 0 <= c < game.cols:
            pygame.draw.rect(surface, self.theme.cursor,
                             self.viewport.cell_rect(r, c), width=1)


class Hud:
    """The status line and the key hint along the edges of the board."""

    HINT = ("DRAG draw   RIGHT-DRAG erase   SPACE play/pause   N step   "
            "R random   C clear   G grid   UP/DOWN speed   ESC menu")

    def __init__(self, fonts, theme=THEME):
        self.theme = theme
        self.font = fonts.mono(15)
        self.hint = self.font.render(self.HINT, True, theme.text_dim)
        self._cache = (None, None)

    def draw(self, surface, game, speed, paused):
        """Draw both bands, re-rendering the status only when it changes."""
        key = (game.generation, paused, speed, game.cols, game.rows)
        if self._cache[0] != key:
            state = "PAUSED" if paused else "RUNNING"
            status = (
                f"GEN {game.generation:<6} POP {game.population:<6} "
                f"{game.cols}x{game.rows}  {speed}/s  {state}"
            )
            self._cache = (key, self.font.render(status, True, self.theme.text))
        # The colony is busy enough that bare text gets lost in it, so each
        # line sits on a dark band
        self._blit_banded(surface, self._cache[1], 4)
        self._blit_banded(surface, self.hint, surface.get_height() - 26)

    def _blit_banded(self, surface, text, y):
        """Blit one line of text on a translucent band across the window."""
        w = surface.get_width()
        band = pygame.Surface((w, text.get_height() + 8), pygame.SRCALPHA)
        band.fill((*self.theme.bg, 215))
        surface.blit(band, (0, y))
        surface.blit(text, (10, y + 4))


class MenuPanel:
    """Lays out and draws the menu's dialog panel.

    Rather than guessing breakpoints, `build` tries the fullest version of the
    screen first and falls back - shorter wording, then smaller type - until
    something actually fits. The three rules always survive; they are the point
    of the screen.
    """

    def __init__(self, fonts, theme=THEME, settings=MENU):
        self.fonts = fonts
        self.theme = theme
        self.settings = settings
        self.title_surface = None
        self.blurb = []
        self.footer = None
        self.item_font = None
        self.panel = pygame.Rect(0, 0, 0, 0)
        self.item_rects = []
        self.required_h = 0

    def panel_width(self, w):
        """Reads as a dialog, not a band stretched across a wide monitor."""
        return min(max(360, w - 48), self.settings.panel_max_w, w - 16)

    def build(self, size, title, versions, items):
        """Pick the fullest wording and largest type that fit this window.

        `versions` is an ordered list of (lines, footer) pairs, fullest first.
        """
        w, h = size
        inner = self.panel_width(w) - self.settings.pad * 2
        avail_h = h - 16
        body_sizes = self.settings.body_sizes
        title_sizes = self.settings.title_sizes
        item_sizes = self.settings.item_sizes

        for lines, footer in versions:
            for cut in range(len(body_sizes)):
                body_font = self.fonts.best_fit(
                    [ln for ln in lines if ln] + [footer], inner, body_sizes[cut:])
                title_font = self.fonts.best_fit(
                    [title], inner,
                    title_sizes[min(cut, len(title_sizes) - 1):], bold=True)
                self.item_font = self.fonts.best_fit(
                    items, inner - 24,
                    item_sizes[min(cut, len(item_sizes) - 1):])

                self.title_surface = title_font.render(title, True, self.theme.title)
                self.blurb = [body_font.render(ln, True, self.theme.text)
                              for ln in lines]
                self.footer = body_font.render(footer, True, self.theme.text_dim)
                self.layout(size, items)

                widest = max([s.get_width() for s in self.blurb]
                             + [self.title_surface.get_width(),
                                self.footer.get_width()])
                if widest <= inner and self.required_h <= avail_h:
                    return
        # Nothing fit even at the smallest; the last attempt is the best there is

    def layout(self, size, items):
        """Work out the panel rect and where each clickable item sits."""
        w, h = size
        pad = self.settings.pad
        line_h = self.blurb[0].get_height()
        item_h = self.item_font.get_height() + 12

        body_h = (self.title_surface.get_height() + 14
                  + len(self.blurb) * line_h + 16
                  + len(items) * (item_h + 6) + 10
                  + self.footer.get_height())
        # What the content actually wants, before the window clamps it - this
        # is what `build` tests its fallbacks against
        self.required_h = body_h + pad * 2
        panel_w = self.panel_width(w)
        panel_h = min(self.required_h, h - 16)
        self.panel = pygame.Rect(0, 0, panel_w, panel_h)
        self.panel.center = (w // 2, h // 2)

        y = self.panel.top + pad + self.title_surface.get_height() + 14
        y += len(self.blurb) * line_h + 16
        self.item_rects = []
        for _ in items:
            rect = pygame.Rect(self.panel.left + pad, y, panel_w - pad * 2, item_h)
            self.item_rects.append(rect)
            y += item_h + 6

    def draw(self, surface, items, selected):
        """Dim the colony, then draw the panel, its copy and its items."""
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill((*self.theme.bg, 205))
        surface.blit(veil, (0, 0))

        pygame.draw.rect(surface, self.theme.panel, self.panel, border_radius=10)
        pygame.draw.rect(surface, self.theme.panel_edge, self.panel, width=1,
                         border_radius=10)

        pad = self.settings.pad
        cx = self.panel.centerx
        y = self.panel.top + pad
        surface.blit(self.title_surface,
                     self.title_surface.get_rect(midtop=(cx, y)))
        y += self.title_surface.get_height() + 14
        for line in self.blurb:
            surface.blit(line, line.get_rect(midtop=(cx, y)))
            y += line.get_height()

        for i, (label, rect) in enumerate(zip(items, self.item_rects)):
            chosen = i == selected
            if chosen:
                pygame.draw.rect(surface, self.theme.selected, rect, border_radius=6)
                pygame.draw.rect(surface, self.theme.panel_edge, rect, width=1,
                                 border_radius=6)
            text = self.item_font.render(
                label, True, self.theme.title if chosen else self.theme.text)
            surface.blit(text, text.get_rect(center=rect.center))

        surface.blit(
            self.footer,
            self.footer.get_rect(midbottom=(cx, self.panel.bottom - pad + 6)))

    def item_at(self, pos):
        """The index of the menu item under a pixel position, or None."""
        for i, rect in enumerate(self.item_rects):
            if rect.collidepoint(pos):
                return i
        return None
