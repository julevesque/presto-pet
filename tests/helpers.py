"""Shared test helpers: imports from src/ and fake time sources."""

import calendar
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from prestopet import engine, pets  # noqa: E402

# 2026-06-15 12:00 UTC, a trusted date
NOON = calendar.timegm((2026, 6, 15, 12, 0, 0))
# A date of a clock that was never set
OLD = calendar.timegm((2021, 1, 1, 0, 0, 0))


class FakeTime:
    """A wall clock and a millisecond counter moved by hand."""

    def __init__(self, wall=NOON, ticks=1000):
        self.w = wall
        self.t = ticks

    def wall(self):
        return self.w

    def ticks(self):
        return self.t

    @staticmethod
    def diff(a, b):
        return a - b

    def advance(self, seconds, wall=True):
        self.t += int(seconds * 1000)
        if wall:
            self.w += seconds


def new_pet(cid="louna"):
    return engine.Pet(cid, pets.profile(cid))


def seeded(seed=1):
    return random.Random(seed).randint
