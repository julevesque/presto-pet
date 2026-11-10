import unittest

import helpers  # noqa: F401

from prestopet.touch import DOWN, HOLD, HOLD_MS, TAP, TouchTracker


class Finger:
    def __init__(self):
        self.t = TouchTracker(lambda a, b: a - b)
        self.now = 0
        self.events = []

    def run(self, down, ms, x=100, y=100):
        end = self.now + ms
        while self.now < end:
            self.now += 20
            e = self.t.update(down, x, y, self.now)
            if e:
                self.events.append(e)


class TouchTest(unittest.TestCase):
    def test_tap_on_release(self):
        f = Finger()
        f.run(True, 100, 50, 60)
        self.assertEqual(f.events, [(DOWN, 50, 60)])
        f.run(False, 100)
        self.assertEqual(f.events[-1], (TAP, 50, 60))

    def test_bounce_is_one_press(self):
        f = Finger()
        f.run(True, 100)
        f.run(False, 20)
        f.run(True, 100)
        f.run(False, 100)
        self.assertEqual([e[0] for e in f.events], [DOWN, TAP])

    def test_hold(self):
        f = Finger()
        f.run(True, HOLD_MS + 100)
        self.assertEqual([e[0] for e in f.events], [DOWN, HOLD])
        f.run(False, 100)
        self.assertEqual([e[0] for e in f.events], [DOWN, HOLD], "no tap after a hold")

    def test_tap_uses_the_first_touch_position(self):
        f = Finger()
        f.run(True, 60, 100, 100)
        f.run(True, 40, 130, 110)
        f.run(False, 100)
        self.assertEqual(f.events[-1], (TAP, 100, 100))

    def test_slide_is_not_a_tap(self):
        f = Finger()
        f.run(True, 60, 100, 100)
        f.run(True, 60, 300, 100)
        f.run(False, 100)
        self.assertEqual([e[0] for e in f.events], [DOWN])


if __name__ == "__main__":
    unittest.main()
