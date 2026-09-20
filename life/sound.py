"""A soft procedural instrument: births chime, pitched by row, panned by column.

No audio assets - each note is a short synthesized tone, built once at start-up
and cached, so playing a chord costs nothing more than picking a mixer channel.
"""

import math
import random
from array import array

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
            self.notes = [self._render(i) for i in range(settings.note_count)]
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

    def set_max_onset_rate(self, value):
        """Set how many chimes may fire per second, from the slider."""
        lo, hi = self.settings.max_onset_rate_range
        self.max_onset_rate = max(lo, min(hi, value))

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
        channel = pygame.mixer.find_channel()
        if channel is None:
            return
        pan = c / (cols - 1) if cols > 1 else 0.5
        left = math.cos(pan * math.pi / 2) * volume
        right = math.sin(pan * math.pi / 2) * volume
        channel.set_volume(left, right)
        channel.play(self.notes[self._degree_for_row(r, rows)])

    def _degree_for_row(self, r, rows):
        """Higher on screen is a higher note, like reading a musical staff."""
        top = len(self.notes) - 1
        if rows <= 1:
            return top
        return round((rows - 1 - r) / (rows - 1) * top)

    def _render(self, degree):
        """Synthesize one short, warm pluck at the given scale degree."""
        settings = self.settings
        octave, step = divmod(degree, len(settings.scale))
        semitones = settings.scale[step] + octave * 12
        freq = settings.root_freq * (2 ** (semitones / 12))

        rate = settings.sample_rate
        length = int(rate * settings.duration)
        attack = max(1, int(rate * settings.attack))
        two_pi_f = 2 * math.pi * freq

        samples = array('h')
        for i in range(length):
            t = i / rate
            if i < attack:
                env = i / attack
            else:
                env = math.exp(-(t - settings.attack) * settings.decay)
            # A touch of the 2nd and 3rd harmonics gives the pluck a warm,
            # bell-like timbre rather than a bare, thin sine tone
            wave = (math.sin(two_pi_f * t)
                    + 0.25 * math.sin(2 * two_pi_f * t)
                    + 0.1 * math.sin(3 * two_pi_f * t))
            value = int(max(-1.0, min(1.0, wave * 0.5)) * env * 32000)
            samples.append(value)
            samples.append(value)
        return pygame.mixer.Sound(buffer=samples)
