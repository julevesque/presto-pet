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

    def test_tables_fit_their_pose(self):
        for cid in pets.CHARACTERS:
            coat = pets.coat(cid)
            for pose, rows in coat.ROWS.items():
                counts = [len(values) for _, values in coat.PARTS[pose]]
                self.assertEqual(len(rows), coat.H, pose)
                for deps, table in rows:
                    size = 1
                    for i in deps:
                        size *= counts[i]
                    self.assertEqual(len(table), size, pose)
                    for k in table:
                        text = coat.RUNSETS[pose][k]
                        self.assertEqual(len(text) % 3, 0)
                        for j in range(0, len(text), 3):
                            x, w = text[j] - 48, text[j + 1] - 48
                            self.assertTrue(0 <= x and w > 0 and x + w <= coat.W, (pose, text))

    def test_frames_match_the_drawings(self):
        """The rows looked up in the tables are the cat as the generator draws it."""
        import itertools
        import random
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import build_sprites as b
        from prestopet.sprites import Frames
        rnd = random.Random(4)
        for cid in pets.CHARACTERS:
            name = pets.character(cid)["coat"]
            coat = pets.coat(cid)
            frames = Frames(coat, {code: code for code in pets.character(cid)["palette"]})
            for pose, parts in coat.PARTS.items():
                combos = list(itertools.product(*(values for _, values in parts)))
                for combo in rnd.sample(combos, min(25, len(combos))) + [combos[0]]:
                    variants = tuple((part, v) for (part, _), v in zip(parts, combo))
                    kwargs = dict(variants)
                    shape = pose[:-2]
                    if pose[-2:] in ("_r", "_l"):
                        image = b.draw_side(name, "stand" if shape == "side" else shape, **kwargs)
                        if pose.endswith("_l"):
                            image = b.mirror(image)
                    else:
                        image = b.draw_cat(name, pose, **kwargs)
                    frames.set_frame(pose, variants)
                    for y, row in enumerate(image):
                        self.assertEqual(row_runs(row, frames.pens), list(frames.runs(y)), (cid, variants, y))

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


class AwakeMotionTest(unittest.TestCase):
    """The pet turns to profile to move, and back to face us once arrived."""

    class Canvas:
        def pens(self, palette):
            return dict(palette)

    def run_until_settled(self, view, pet, now, ms=8000):
        poses = set()
        end = now + ms
        while now < end:
            now += 20
            view.update(now, pet)
            poses.add(view.pose)
        return poses

    def setUp(self):
        from prestopet import engine
        from prestopet.petview import AwakeView
        self.pet = engine.Pet("louna", pets.profile("louna"))
        self.pet.activity = engine.IDLE
        self.pet.happiness = 90
        self.view = AwakeView(self.Canvas(), "louna", 200, 140)

    def test_walks_in_profile_then_faces_us(self):
        self.view.walk_to(300)
        poses = self.run_until_settled(self.view, self.pet, 0)
        self.assertIn("side_r", poses)
        self.assertNotIn("side_l", poses)
        self.assertEqual((self.view.pose, self.view.face, self.view.target), ("sit", 0, None))
        self.assertLess(abs(self.view.x - 300), 10)

    def test_pounces_with_the_paws_on_the_ball(self):
        from prestopet import petview
        self.view.x = 360
        self.view.chase(150)
        self.view.update(20, self.pet)
        self.assertEqual(self.view.face, -1)
        poses = self.run_until_settled(self.view, self.pet, 20)
        self.assertIn("side_l", poses)
        self.assertEqual(self.view.x, 150 + petview.PAW_DX)
        self.assertEqual(self.view.pose, "sit")

    def test_crouches_and_wiggles_before_pouncing(self):
        self.view.x = 140
        self.view.chase(330)
        poses = []
        now = 0
        for _ in range(200):
            now += 20
            self.view.update(now, self.pet)
            poses.append(self.view.pose)
        self.assertIn("crouch_r", poses)
        first = poses.index("crouch_r")
        self.assertIn("side_r", poses[first:])          # the leap comes after

    def test_licks_a_paw_or_stretches_in_profile(self):
        from prestopet import engine
        self.pet.activity = engine.STRETCH
        poses = self.run_until_settled(self.view, self.pet, 0, 1000)
        self.assertTrue({"bow_r", "bow_l"} & poses)
        self.pet.activity = engine.IDLE
        self.run_until_settled(self.view, self.pet, 1000, 1000)
        self.assertEqual(self.view.pose, "sit")

    def test_goes_to_bed_on_the_cushion(self):
        self.view.go_to_bed(240)
        poses = set()
        legs = set()
        now = 0
        while now < 8000:
            now += 20
            self.view.update(now, self.pet)
            poses.add(self.view.pose)
            legs.update(v for part, v in self.view.comp.key[1] if part == "legs")
        self.assertTrue(self.view.bed_done)
        self.assertEqual(self.view.lift, 44)
        self.assertTrue({"side_r", "side_l"} <= poses)       # turns round on the cushion
        self.assertTrue({"knead_a", "knead_b"} <= legs)      # then kneads it
