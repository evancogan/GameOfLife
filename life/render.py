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
            "R random   C clear   G grid   M mute   UP/DOWN speed   ESC menu")
    MARGIN = 10   # smallest gap from the left edge, centred or not

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
        self._blit_banded(surface, self.hint, surface.get_height() - 26, center=True)

    def _blit_banded(self, surface, text, y, center=False):
        """Blit one line of text on a translucent band across the window.

        A centred line stays centred at any window size, but never starts
        further left than the margin - on a window too narrow for the whole
        hint, it runs off the right rather than off both edges at once.
        """
        w = surface.get_width()
        band = pygame.Surface((w, text.get_height() + 8), pygame.SRCALPHA)
        band.fill((*self.theme.bg, 215))
        surface.blit(band, (0, y))
        x = max(self.MARGIN, (w - text.get_width()) // 2) if center else self.MARGIN
        surface.blit(text, (x, y + 4))


class Slider:
    """A horizontal drag-to-set control over a numeric range.

    A slider never owns the value it shows - `get` and `set` read and write
    whatever it controls, so the same widget serves the sim speed and the
    instrument's knobs without a subclass for each.
    """

    TRACK_H = 6
    HANDLE_R = 8

    def __init__(self, label, minimum, maximum, get, set_, fmt="{:.0f}", hint=""):
        self.label = label
        self.minimum = minimum
        self.maximum = maximum
        self.get = get
        self.set = set_
        self.fmt = fmt
        self.hint = hint
        self.track = pygame.Rect(0, 0, 0, 0)

    def layout(self, rect):
        """Place the track inside `rect`, vertically centred."""
        self.track = pygame.Rect(rect.left, rect.centery - self.TRACK_H // 2,
                                 rect.width, self.TRACK_H)

    def _t(self, value):
        """Where `value` falls between 0 and 1 across the range."""
        return (value - self.minimum) / (self.maximum - self.minimum)

    def _handle_pos(self, value):
        x = self.track.left + int(self._t(value) * self.track.width)
        return (x, self.track.centery)

    def drag_to(self, x):
        """Set the value from a pixel position, clamped to the track."""
        t = max(0.0, min(1.0, (x - self.track.left) / self.track.width))
        self.set(self.minimum + t * (self.maximum - self.minimum))

    def hit(self, pos):
        """A generous strip around the track, not just the thin bar itself."""
        x, y = pos
        return (self.track.left - 10 <= x <= self.track.right + 10
                and self.track.top - 14 <= y <= self.track.bottom + 14)

    def draw(self, surface, font, theme):
        value = self.get()
        label = font.render(f"{self.label}: {self.fmt.format(value)}", True, theme.text)
        surface.blit(label, (self.track.left, self.track.top - label.get_height() - 6))

        pygame.draw.rect(surface, theme.grid, self.track, border_radius=3)
        filled = pygame.Rect(self.track.left, self.track.top,
                             max(0, int(self._t(value) * self.track.width)),
                             self.track.height)
        pygame.draw.rect(surface, theme.live, filled, border_radius=3)
        pos = self._handle_pos(value)
        pygame.draw.circle(surface, theme.newborn, pos, self.HANDLE_R)
        pygame.draw.circle(surface, theme.panel_edge, pos, self.HANDLE_R, width=1)


class SettingsPanel:
    """A corner button that opens live sliders over the board, under headings.

    `sections` is an ordered list of (heading, [Slider, ...]) pairs - here
    "Simulation" and "Sound" - so it reads at a glance which controls affect
    the colony itself and which affect the instrument it plays on.
    """

    BUTTON_SIZE = (86, 28)
    MARGIN = 10
    WIDTH = 260
    ROW_H = 54
    HEADING_GAP = 22
    PAD = 16
    HOVER_DELAY_MS = 500   # a hint only appears once the pointer has settled

    def __init__(self, fonts, sections, theme=THEME):
        self.theme = theme
        self.font = fonts.mono(13)
        self.title_font = fonts.mono(15, bold=True)
        self.heading_font = fonts.mono(12, bold=True)
        self.sections = sections
        self.sliders = [slider for _, group in sections for slider in group]
        self.open = False
        self.dragging = None
        self.hovered = None
        self.hover_since = 0
        self.button = pygame.Rect(0, 0, *self.BUTTON_SIZE)
        self.panel = pygame.Rect(0, 0, 0, 0)
        self.on_resize((0, 0))

    def on_resize(self, size):
        """Re-anchor the button and panel to the bottom-right corner."""
        w, h = size
        self.button.bottomright = (w - self.MARGIN, h - self.MARGIN)
        panel_h = (self.PAD * 2 + self.title_font.get_height() + 10
                  + len(self.sections) * self.HEADING_GAP
                  + len(self.sliders) * self.ROW_H)
        self.panel = pygame.Rect(0, 0, self.WIDTH, panel_h)
        self.panel.bottomright = (self.button.right, self.button.top - 8)

        y = self.panel.top + self.PAD + self.title_font.get_height() + 10
        self.heading_positions = []
        for heading, group in self.sections:
            self.heading_positions.append((heading, (self.panel.left + self.PAD, y)))
            y += self.HEADING_GAP
            for slider in group:
                rect = pygame.Rect(self.panel.left + self.PAD, y,
                                   self.panel.width - self.PAD * 2, self.ROW_H - 18)
                slider.layout(rect)
                y += self.ROW_H

    def toggle(self):
        self.open = not self.open
        self.dragging = None

    def handle_down(self, pos):
        """True if this click was the panel's business, whatever it did with it."""
        if self.button.collidepoint(pos):
            self.toggle()
            return True
        if not self.open:
            return False
        for slider in self.sliders:
            if slider.hit(pos):
                self.dragging = slider
                slider.drag_to(pos[0])
                return True
        self.open = False   # a click outside the panel dismisses it
        return True

    def handle_motion(self, pos):
        """True if the board should ignore this motion - dragging or just open."""
        if self.dragging:
            self.dragging.drag_to(pos[0])
            return True
        return self.open

    def handle_up(self):
        """True if this release ended a drag the panel owned."""
        had = self.dragging is not None
        self.dragging = None
        return had

    def draw(self, surface):
        theme = self.theme
        pygame.draw.rect(surface, theme.panel, self.button, border_radius=6)
        pygame.draw.rect(surface, theme.panel_edge, self.button, width=1,
                         border_radius=6)
        label = self.font.render("CLOSE" if self.open else "SETTINGS", True,
                                 theme.text)
        surface.blit(label, label.get_rect(center=self.button.center))

        if not self.open:
            return
        pygame.draw.rect(surface, theme.panel, self.panel, border_radius=10)
        pygame.draw.rect(surface, theme.panel_edge, self.panel, width=1,
                         border_radius=10)
        title = self.title_font.render("Live controls", True, theme.title)
        surface.blit(title, (self.panel.left + self.PAD, self.panel.top + self.PAD))
        for heading, pos in self.heading_positions:
            text = self.heading_font.render(heading.upper(), True, theme.text_dim)
            surface.blit(text, pos)
        for slider in self.sliders:
            slider.draw(surface, self.font, theme)

        # A hint only appears once the pointer has sat on a slider for a
        # moment, so a hand just passing over the panel to reach the sliders
        # below it doesn't flash text the whole way down
        pos = pygame.mouse.get_pos()
        hovered = next((s for s in self.sliders if s.hint and s.hit(pos)), None)
        if hovered is not self.hovered:
            self.hovered = hovered
            self.hover_since = pygame.time.get_ticks()
        if hovered and pygame.time.get_ticks() - self.hover_since >= self.HOVER_DELAY_MS:
            self._draw_tooltip(surface, hovered.hint, pos)

    def _draw_tooltip(self, surface, text, pos):
        """A small label that follows the cursor, clamped onto the window."""
        theme = self.theme
        label = self.font.render(text, True, theme.text)
        pad = 6
        box = label.get_rect().inflate(pad * 2, pad * 2)
        box.topleft = (pos[0] + 16, pos[1] + 16)
        box.right = min(box.right, surface.get_width() - 4)
        box.bottom = min(box.bottom, surface.get_height() - 4)

        pygame.draw.rect(surface, theme.panel, box, border_radius=6)
        pygame.draw.rect(surface, theme.panel_edge, box, width=1, border_radius=6)
        surface.blit(label, (box.left + pad, box.top + pad))


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
