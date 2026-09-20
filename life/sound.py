"""A soft procedural instrument: births chime, pitched by row, panned by column
and, via the same left-right position, run for a shorter or longer time.

No audio assets - each note is a short synthesized tone, built once at start-up
and cached, so playing a chord costs nothing more than picking a mixer channel.
"""

import math
import random

import numpy as np
import pygame

from .config import SOUND


class Instrument:
    """Turns newborn cells into a pleasant, self-limiting chime.

    Only births make a sound - a colony dying back is silence, not noise - and
    a screen-filling soup still only ever plays a handful of notes at once, so
    a big reproduction never turns into a wall of sound.
    """

    def __init__(self, settings=SOUND):
        self.settings = settings
        self.enabled = False
        self.notes = []
        self.pending = set()   # births queued since the last chime
        self.cooldown = 0.0    # seconds until another chime is allowed
        # Mutable copies of the config defaults - the settings panel's sliders
        # adjust these directly, without touching the frozen config itself
        self.max_voices = settings.max_voices
        self.max_onset_rate = settings.max_onset_rate
        try:
            pygame.mixer.init(frequency=settings.sample_rate, size=-16,
                               channels=2, buffer=settings.buffer)
            pygame.mixer.set_num_channels(settings.channels)
            # notes[degree][bucket][variant] - a handful of cached lengths
            # spanning duration_range per pitch (see `_pluck`, which picks the
            # bucket from the same left-right position it uses to pan), each
            # with a few detuned unison variants on top (see `unison`)
            buckets = self._duration_buckets()
            self.notes = [[[self._render(i, v, d) for v in range(settings.unison)]
                           for d in buckets]
                          for i in range(settings.note_count)]
            self._ensure_channels()
            self.enabled = True
        except pygame.error:
            # No audio device, or one that refuses these settings - the
            # simulation runs fine silent rather than crashing over sound
            pass

    def toggle(self):
        """Mute or unmute; the tones are already built, so this is instant."""
        self.enabled = not self.enabled and bool(self.notes)
        return self.enabled

    def set_max_voices(self, value):
        """Set how many notes a single chime may play, from the slider."""
        lo, hi = self.settings.max_voices_range
        self.max_voices = max(lo, min(hi, round(value)))
        self._ensure_channels()

    def set_max_onset_rate(self, value):
        """Set how many chimes may fire per second, from the slider."""
        lo, hi = self.settings.max_onset_rate_range
        self.max_onset_rate = max(lo, min(hi, value))
        self._ensure_channels()

    def _duration_buckets(self):
        """The distinct note lengths cached, evenly spanning duration_range."""
        lo, hi = self.settings.duration_range
        n = self.settings.duration_buckets
        if n <= 1:
            return [hi]
        return [lo + (hi - lo) * k / (n - 1) for k in range(n)]

    def _ensure_channels(self):
        """Keep enough mixer channels for every note the sliders now allow.

        A note outlives the chime that started it, so the notes actually
        sounding at any moment are a whole note's worth of chimes, not one:
        `max_voices` times however many chimes fit inside the longest note's
        ring-out. Sized for a single chime instead, the mixer runs out
        mid-swell and every note after that is dropped - which made raising
        the voice slider *reduce* what you heard, since one greedy chime could
        take every channel and leave the next few silent.
        """
        if not self.notes:
            return
        longest = self.settings.duration_range[1]
        overlap = max(1, math.ceil(longest * self.max_onset_rate))
        needed = min(self.max_voices * overlap, self.settings.channel_limit)
        if needed > pygame.mixer.get_num_channels():
            pygame.mixer.set_num_channels(needed)

    def queue_births(self, cells):
        """Remember this generation's newborns for the next chime.

        Chiming on every generation is what made fast speeds all sound the
        same: past ten or so generations a second the notes overlap faster
        than their own decay, so it was always the same fixed, fully-loud
        chord smeared on top of itself. Queuing instead lets `update` fire
        chimes on a steady clock of their own, so a fast colony is heard as a
        richer, louder swell rather than a denser wash of the same swell.
        """
        if self.enabled:
            self.pending.update(cells)

    def update(self, dt, rows, cols):
        """Age the chime cooldown, firing one if it has elapsed and something
        is queued."""
        if not self.enabled:
            return
        self.cooldown -= dt
        if self.cooldown > 0 or not self.pending:
            return
        self.cooldown = 1.0 / self.max_onset_rate
        self._chime(self.pending, rows, cols)
        self.pending = set()

    def _chime(self, cells, rows, cols):
        """Play a batch of newborns, pitched by row and panned by column.

        However many were born, only a few notes actually sound, and each is
        quieter the more there are, so a soup-wide birth is a soft swell
        rather than every voice firing at once - but the swell itself scales
        with how much was actually queued, so a busier colony still sounds
        busier.
        """
        volume = 1.0 / math.sqrt(len(cells))
        cells = list(cells)
        if len(cells) > self.max_voices:
            cells = random.sample(cells, self.max_voices)
        for r, c in cells:
            self._pluck(r, c, rows, cols, volume)

    def pluck(self, r, c, rows, cols):
        """A single note, for one hand-drawn cell."""
        if self.enabled:
            self._pluck(r, c, rows, cols, 1.0)

    def _pluck(self, r, c, rows, cols, volume):
        # Force-steal the longest-playing channel if they are all busy: at the
        # top of both sliders the demand can still outrun `channel_limit`, and
        # cutting the tail off the oldest note is far less audible than
        # dropping the newest one entirely
        channel = pygame.mixer.find_channel(True)
        if channel is None:
            return
        # Column drives both axes at once: where the note sits in the stereo
        # field, and - via bucket - how long it rings for, so a horizontal
        # spread of births is heard as varied note lengths, not one wide
        # blob of identically-timed, identically-pitched sound.
        pan = c / (cols - 1) if cols > 1 else 0.5
        left = math.cos(pan * math.pi / 2) * volume
        right = math.sin(pan * math.pi / 2) * volume
        channel.set_volume(left, right)
        buckets = self.notes[self._degree_for_row(r, rows)]
        variants = buckets[round(pan * (len(buckets) - 1))]
        channel.play(variants[random.randrange(len(variants))])

    def _degree_for_row(self, r, rows):
        """Higher on screen is a higher note, like reading a musical staff."""
        top = len(self.notes) - 1
        if rows <= 1:
            return top
        return round((rows - 1 - r) / (rows - 1) * top)

    def _render(self, degree, variant=0, duration=None):
        """Synthesize one short, warm pluck at the given scale degree.

        `variant` nudges the pitch by a few cents so unison copies of the
        same degree (see `unison` in SoundSettings) aren't bit-identical:
        variant 0 is always exact so a single voice stays in tune, and the
        rest fan out evenly above and below it. `duration` overrides how long
        this particular rendering rings for, defaulting to the longest of
        duration_range; a short duration still fades out cleanly rather than
        cutting off mid-decay, via the tail release below.
        """
        settings = self.settings
        octave, step = divmod(degree, len(settings.scale))
        semitones = settings.scale[step] + octave * 12
        freq = settings.root_freq * (2 ** (semitones / 12))
        if variant:
            spread = settings.unison_detune_cents
            half = (settings.unison - 1) / 2
            cents = (variant - half) / half * spread if half else 0.0
            freq *= 2 ** (cents / 1200)

        if duration is None:
            duration = settings.duration_range[1]
        rate = settings.sample_rate
        length = int(rate * duration)
        attack = max(1, int(rate * settings.attack))
        release = max(1, int(rate * settings.release))

        # Vectorized with numpy rather than one Python loop iteration per
        # sample: with up to note_count * duration_buckets * unison distinct
        # renderings cached at start-up, the plain-Python version of this loop
        # took several seconds to build the whole instrument before a sound
        # could play; array math over the whole buffer at once takes
        # milliseconds.
        i = np.arange(length)
        t = i / rate

        env = np.exp(-(t - settings.attack) * settings.decay)
        env[i < attack] = i[i < attack] / attack
        # However far the natural decay has gotten, force it the rest of the
        # way to silence over the last `release` samples - otherwise the
        # short end of duration_range cuts off mid-decay and clicks
        remaining = length - i
        tail = remaining <= release
        env[tail] *= remaining[tail] / release

        # A touch of the 2nd and 3rd harmonics gives the pluck a warm,
        # bell-like timbre rather than a bare, thin sine tone
        two_pi_f_t = 2 * math.pi * freq * t
        wave = (np.sin(two_pi_f_t)
                + 0.25 * np.sin(2 * two_pi_f_t)
                + 0.1 * np.sin(3 * two_pi_f_t))
        values = np.clip(wave * 0.5, -1.0, 1.0) * env * 32000
        samples = np.repeat(values.astype(np.int16), 2)
        return pygame.mixer.Sound(buffer=samples.tobytes())
