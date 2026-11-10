# The 7 LEDs on the back of the Presto: a small pink light show when the pet purrs.
#
# The show is a pure function of time (frame), so it is tested on a computer: the glow
# spreads from the middle LED to both ends, beats twice like a heart, twice more softly,
# then fades out. The LEDs stay off the rest of the time.

COUNT = 7
SHOW_MS = 2800
HEART = (255, 40, 90)          # the deep pink of the hearts
LIGHT = (255, 90, 150)         # a little lighter at the top of a beat
BEATS = ((800, 1.0), (1100, 0.9), (1700, 0.6), (2000, 0.5))   # (ms, strength)
BEAT_MS = 150                  # half width of a beat
SPREAD_MS = 120                # delay between two LEDs while the glow spreads
RISE_MS = 250
FADE_FROM = 2200
OFF = ((0, 0, 0),) * COUNT


def _pulse(t):
    p = 0.0
    for at, strength in BEATS:
        d = abs(t - at)
        if d < BEAT_MS:
            p = max(p, strength * (1.0 - d / BEAT_MS))
    return p


def frame(t, level=1.0):
    """Colours of the LEDs t ms after the start of the show, or None once it is over."""
    if t < 0 or t >= SHOW_MS:
        return None
    middle = COUNT // 2
    beat = _pulse(t)
    fade = 1.0 if t < FADE_FROM else 1.0 - (t - FADE_FROM) / (SHOW_MS - FADE_FROM)
    fade = fade * fade                 # a soft end, with no visible jump to black
    colour = tuple(int(h + (l - h) * beat) for h, l in zip(HEART, LIGHT))
    out = []
    for i in range(COUNT):
        start = abs(i - middle) * SPREAD_MS
        spread = min(1.0, max(0.0, (t - start) / RISE_MS))
        v = spread * (0.45 + 0.55 * beat) * fade * level
        out.append(tuple(int(c * v) for c in colour))
    return tuple(out)


class Leds:
    """Plays the show on the hardware, sending the colours only when they change."""

    def __init__(self, hw, ticks_diff):
        self.hw = hw
        self.diff = ticks_diff
        self.started = None
        self.level = 1.0
        self.shown = None
        self.send(OFF)

    def purr(self, now, level=1.0):
        self.started = now
        self.level = level

    def stop(self):
        self.started = None
        self.send(OFF)

    def update(self, now):
        if self.started is None:
            return
        colours = frame(self.diff(now, self.started), self.level)
        if colours is None:
            self.stop()
        else:
            self.send(colours)

    def send(self, colours):
        if colours != self.shown:
            self.shown = colours
            self.hw.set_leds(colours)
