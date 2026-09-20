"""Tunable values for the whole program, grouped by what they configure.

Each group is a frozen dataclass with a module-level default instance, so call
sites read `SETTINGS.cell_size` or `THEME.live`. Anything that wants different
values - a test, a second theme - builds its own instance and passes it in.
"""

from dataclasses import dataclass

Color = tuple[int, int, int]


@dataclass(frozen=True)
class Settings:
    """The board's scale and the window it lives in."""

    cell_size: int = 14
    default_size: tuple[int, int] = (960, 680)
    min_size: tuple[int, int] = (320, 240)
    random_density: float = 0.22


@dataclass(frozen=True)
class SpeedSettings:
    """Generations per second, and how holding a speed key rolls the number.

    The first step comes from the key press itself; the roll only starts once
    the key has been down for `hold_delay`, so a quick tap moves by exactly one.
    """

    default: int = 5
    minimum: int = 1
    maximum: int = 60
    menu_speed: int = 6             # generations per second behind the menu panel
    hold_delay: float = 0.35        # seconds held before the number starts rolling
    roll_rate: float = 10           # steps per second when the roll begins
    roll_max_rate: float = 55       # ...and once it is up to full tilt
    roll_ramp: float = 1.0          # seconds of holding to get from one to the other


@dataclass(frozen=True)
class EffectSettings:
    """How long newborns glow and the dead linger.

    Effects are measured in generations, not seconds, so they read the same at
    1 step per second as at 60. Much over one generation and the whole board
    looks like newborns and ghosts instead of a green colony.
    """

    glow_generations: float = 0.9   # how long a newborn stays pale
    fade_generations: float = 1.1   # how long a dead cell lingers
    max_catch_up_steps: int = 4     # steps a single stalled frame may make up


@dataclass(frozen=True)
class SoundSettings:
    """The instrument the colony plays on: one soft pluck per birth.

    Pitch runs a major pentatonic scale - no two notes in it clash - so however
    many cells are born at once, the chord they make is always consonant.
    """

    sample_rate: int = 44100
    buffer: int = 512
    channels: int = 64            # mixer channels allocated at start-up
    channel_limit: int = 512      # ceiling on channels grown for the sliders
    scale: tuple[int, ...] = (0, 2, 4, 7, 9)   # major pentatonic, in semitones
    octaves: int = 4
    root_freq: float = 196.0      # G3; the scale runs upward from here
    # A birth's column sets where it sits left-to-right AND how long it rings
    # for, so a horizontal spread of births is heard as a spread of note
    # lengths, not just a wide, identically-pitched stereo image - panning
    # alone wasn't enough for the ear to hear simultaneous same-pitch notes
    # as separate voices rather than one louder note.
    duration_range: tuple[float, float] = (0.15, 1.2)   # left column, right column
    duration_buckets: int = 6     # distinct cached lengths spanning that range
    release: float = 0.02         # fade-out at the tail, so short notes don't click
    attack: float = 0.006
    decay: float = 6.0            # exponential decay rate after the attack

    # Two or more voices landing on the same scale degree at once (common,
    # since there are only note_count distinct pitches) would otherwise play
    # the exact same cached waveform in phase - which sums to a louder copy
    # of one voice, not an audibly denser chord. A few detuned variants per
    # degree let repeats chorus/beat against each other instead, so raising
    # max_voices is actually audible as more voices, not just more volume.
    unison: int = 4
    unison_detune_cents: float = 8.0

    # Starting point for the two live sliders in the settings panel: how many
    # notes a single chime may play, and how many chimes may fire per second.
    # Both are adjustable at runtime, so these are just where the knobs start.
    max_voices: int = 10
    max_onset_rate: float = 10.0
    max_voices_range: tuple[int, int] = (1, 60)
    max_onset_rate_range: tuple[float, float] = (1.0, 40.0)

    @property
    def note_count(self):
        return len(self.scale) * self.octaves


@dataclass(frozen=True)
class MenuSettings:
    """Panel geometry and the type sizes the menu falls back through."""

    panel_max_w: int = 640
    pad: int = 22
    title_sizes: tuple[int, ...] = (34, 28, 22, 18, 15, 13)
    body_sizes: tuple[int, ...] = (15, 14, 13, 12, 11, 10, 9, 8)
    item_sizes: tuple[int, ...] = (19, 17, 15, 13, 12, 11)


@dataclass(frozen=True)
class Theme:
    """The colour palette, plus the blend used by the glow and fade effects."""

    bg: Color = (8, 14, 10)
    grid: Color = (18, 32, 23)
    live: Color = (60, 220, 90)
    newborn: Color = (150, 250, 175)
    dying: Color = (30, 84, 44)
    text: Color = (110, 190, 130)
    text_dim: Color = (60, 110, 75)
    panel: Color = (10, 20, 14)
    panel_edge: Color = (46, 120, 66)
    title: Color = (150, 250, 175)
    selected: Color = (26, 58, 36)
    cursor: Color = (90, 170, 115)
    font_name: str = "consolas,dejavusansmono,monospace"

    @staticmethod
    def blend(a: Color, b: Color, t: float) -> Color:
        """Blend between two colours; t of 0 gives `a`, 1 gives `b`."""
        t = max(0.0, min(1.0, t))
        return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


SETTINGS = Settings()
SPEED = SpeedSettings()
EFFECTS = EffectSettings()
SOUND = SoundSettings()
MENU = MenuSettings()
THEME = Theme()
