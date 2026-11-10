import os
import subprocess
import sys
import unittest

from helpers import ROOT

from prestopet import art, font, pets
from prestopet.sprites import Composite, flatten, row_runs, shifted_patch


class GeneratedArtTest(unittest.TestCase):
    def test_coats_are_up_to_date(self):
        result = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build_sprites.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_patches_fit_their_pose(self):
        for cid in pets.CHARACTERS:
            coat = pets.coat(cid)
            for rows in coat.POSES.values():
                self.assertEqual(len(rows), coat.H)
                self.assertTrue(all(len(r) == coat.W for r in rows))
            for (pose, part, variant), (x, y, rows) in coat.PATCHES.items():
                self.assertIn(pose, coat.POSES)
                self.assertTrue(0 <= x and x + len(rows[0]) <= coat.W, (pose, part, variant))
                self.assertTrue(0 <= y and y + len(rows) <= coat.H, (pose, part, variant))

    def test_sleep_layers_fit(self):
        for cid in pets.CHARACTERS:
            a = pets.sleep_art(cid)
            for x, y, rows in a.LAYERS:
                self.assertLessEqual(x + len(rows[0]), a.W)
                self.assertLessEqual(y + len(rows), a.H)

    def test_interface_art_is_rectangular(self):
        for name, rows in art.ICONS.items():
            self.assertEqual((len(rows), len(set(map(len, rows)))), (16, 1), name)
        for rows in (art.MESS, art.HEART, art.BUBBLE_SMALL, art.SPARKLE):
            self.assertEqual(len(set(map(len, rows))), 1)
            self.assertFalse(set("".join(rows)) - set(art.PALETTE) - {"."})


class CompositeTest(unittest.TestCase):
    PENS = {"a": 1, "b": 2}

    def test_patch_and_restore(self):
        c = Composite(("aaaa", "aaaa"), self.PENS)
        patch = (1, 1, ("b_",))
        self.assertTrue(c.set_patches((patch,)))
        self.assertEqual(c.rows, ["aaaa", "ab.a"])
        self.assertFalse(c.set_patches((patch,)))
        c.set_patches(())
        self.assertEqual(c.rows, ["aaaa", "aaaa"])

    def test_runs(self):
        self.assertEqual(row_runs("aab..a", self.PENS), [(0, 2, 1), (2, 1, 2), (5, 1, 1)])

    def test_shifted_zone(self):
        layers = ((0, 0, ("....", ".aa.", ".aa.")),)
        base = flatten(4, 3, layers)
        # The shifted zone includes the row the content moves into.
        patch = shifted_patch(4, 3, layers, 0, (0, 0, 4, 3), (0, 0, 4, 3, 0, -1))
        c = Composite(base, self.PENS)
        c.set_patches((patch,))
        self.assertEqual(c.rows, [".aa.", ".aa.", "...."])


class FontTest(unittest.TestCase):
    def test_every_character_of_the_texts_exists(self):
        from prestopet.i18n import LANGUAGE_NAMES, TEXTS
        missing = set()
        for table in list(TEXTS.values()) + [LANGUAGE_NAMES]:
            for value in table.values():
                for text in (value if isinstance(value, tuple) else (value,)):
                    for ch in text:
                        if ch not in font._GLYPHS and ch not in font._ACCENTED and ch != "%":
                            missing.add(ch)
        self.assertFalse(missing)

    def test_glyph_rows_have_one_width(self):
        for c, spec in font._GLYPHS.items():
            self.assertEqual(len(set(len(r) for r in spec.split(" "))), 1, c)

    def test_wrap(self):
        lines = font.wrap("un deux trois quatre", font.width("un deux", 2), 2)
        self.assertEqual(lines, ["un deux", "trois", "quatre"])


if __name__ == "__main__":
    unittest.main()
