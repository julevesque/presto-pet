"""The pink light show of the LEDs when the pet purrs."""

import unittest

import helpers  # noqa: F401

from prestopet import leds


class FrameTest(unittest.TestCase):
    def test_colours_are_valid_bytes(self):
        for t in range(0, leds.SHOW_MS, 20):
            colours = leds.frame(t)
            self.assertEqual(len(colours), leds.COUNT)
            for c in colours:
                self.assertTrue(all(isinstance(v, int) and 0 <= v <= 255 for v in c), (t, c))

    def test_the_glow_spreads_from_the_middle(self):
        early = leds.frame(150)
        self.assertGreater(sum(early[3]), 0)
        self.assertEqual(early[0], (0, 0, 0))
        self.assertGreater(sum(leds.frame(700)[0]), 0)

    def test_beats_are_brighter_and_pink(self):
        beat = leds.frame(800)[3]
        between = leds.frame(950)[3]
        self.assertGreater(sum(beat), sum(between))
        r, g, b = beat
        self.assertTrue(r > b > g, "pink")

    def test_the_show_fades_out_and_ends(self):
        self.assertLess(sum(map(sum, leds.frame(leds.SHOW_MS - 20))), 10)
        self.assertIsNone(leds.frame(leds.SHOW_MS))

    def test_a_lower_level_is_dimmer(self):
        self.assertLess(sum(leds.frame(800, 0.6)[3]), sum(leds.frame(800, 1.0)[3]))


class FakeHw:
    def __init__(self):
        self.sent = []

    def set_leds(self, colours):
        self.sent.append(colours)


class LedsTest(unittest.TestCase):
    def test_off_at_start_then_show_then_off(self):
        hw = FakeHw()
        l = leds.Leds(hw, lambda a, b: a - b)
        self.assertEqual(hw.sent, [leds.OFF])
        l.purr(1000)
        for now in range(1000, 1000 + leds.SHOW_MS + 100, 20):
            l.update(now)
        self.assertEqual(hw.sent[-1], leds.OFF)
        self.assertGreater(len(hw.sent), 20)
        count = len(hw.sent)
        l.update(9000)
        self.assertEqual(len(hw.sent), count, "nothing is sent while off")


if __name__ == "__main__":
    unittest.main()
