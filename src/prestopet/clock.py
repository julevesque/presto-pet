# Game time.
#
# The Presto has no battery-backed clock: after a power cut its clock restarts at an old date
# until it is set by NTP (or by mpremote). The game must work either way:
#
# - When the wall clock is trusted at boot, the time spent switched off is known at once and
#   simulated (catch-up).
# - When it is not, the game resumes from the saved timestamp as if no time had passed, and
#   counts time with the monotonic millisecond counter. If the clock becomes trusted later
#   (network time), the missing offline time is discovered and returned once by poll().
# - A game created while the clock was unknown has timestamps that start from nothing: they
#   are not "anchored" to real time, so the first real time cannot tell how long the device
#   was off. The gap is then taken as zero, and the timeline becomes anchored from there.
#
# All sources are injected, so this module is tested on a computer.

import time

try:
    from calendar import timegm as _utc_mktime   # CPython: time.mktime would use local time
except ImportError:
    _utc_mktime = time.mktime                    # MicroPython: no time zones, mktime is UTC

MIN_YEAR = 2025   # an earlier date means the clock was never set


def ticks_source():
    """(ticks_ms, ticks_diff) of the running Python."""
    if hasattr(time, "ticks_ms"):
        return time.ticks_ms, time.ticks_diff
    return (lambda: int(time.monotonic() * 1000)), (lambda a, b: a - b)


def wall_is_trusted(epoch):
    try:
        return time.gmtime(int(epoch))[0] >= MIN_YEAR
    except (OverflowError, ValueError, OSError):
        return False


class GameClock:
    def __init__(self, saved_at=None, anchored=True, wall=time.time, ticks=None, diff=None,
                 trusted=wall_is_trusted):
        if ticks is None:
            ticks, diff = ticks_source()
        self._wall = wall
        self._ticks = ticks
        self._diff = diff
        self._is_trusted = trusted
        self._last = ticks()
        self._elapsed_ms = 0          # since the base, accumulated: ticks wrap after ~12 days
        now = wall()
        self.trusted = trusted(now)
        known = saved_at is not None and anchored
        if self.trusted:
            self._base = now
            gap = now - saved_at if known else 0
        else:
            self._base = saved_at if saved_at is not None else 0
            gap = 0
        # True when now() is real time, or an estimate built on a real time.
        self.anchored = self.trusted or known
        self.boot_gap = gap if gap > 0 else 0   # offline time known at boot, in seconds

    def _advance(self):
        t = self._ticks()
        d = self._diff(t, self._last)
        self._last = t
        if d > 0:
            self._elapsed_ms += d

    def now(self):
        """Seconds since the epoch: the real time when trusted, else an estimate that never
        goes backwards."""
        self._advance()
        if self.trusted:
            return self._wall()
        return self._base + self._elapsed_ms // 1000

    def poll(self):
        """To call regularly (at least every few days, in practice every loop). Returns the
        offline time discovered when the wall clock has just become trusted, else 0."""
        self._advance()
        if self.trusted:
            return 0
        real = self._wall()
        if not self._is_trusted(real):
            return 0
        estimate = self._base + self._elapsed_ms // 1000
        self.trusted = True
        gap = real - estimate if self.anchored else 0
        self.anchored = True
        return gap if gap > 0 else 0


# --- Local time --------------------------------------------------------------------------------


def _last_sunday_1h_utc(year, month):
    # Last Sunday of March or October (both have 31 days), 01:00 UTC: the moment clocks
    # change everywhere in the European Union.
    t = _utc_mktime((year, month, 31, 1, 0, 0, 0, 0, 0))
    weekday = time.gmtime(t)[6]  # Monday = 0, Sunday = 6
    return t - ((weekday + 1) % 7) * 86400


def utc_offset(epoch, offset_minutes, eu_dst):
    """Offset of local time in seconds."""
    offset = offset_minutes * 60
    if eu_dst:
        year = time.gmtime(int(epoch))[0]
        if _last_sunday_1h_utc(year, 3) <= epoch < _last_sunday_1h_utc(year, 10):
            offset += 3600
    return offset


def local_hour(epoch, offset_minutes=0, eu_dst=False):
    return time.gmtime(int(epoch + utc_offset(epoch, offset_minutes, eu_dst)))[3]
