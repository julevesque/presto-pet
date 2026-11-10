"""The whole life cycle, as on the device: adoption, actions, restarts, late network time."""

import os
import shutil
import tempfile
import unittest

from helpers import NOON, OLD, FakeTime, seeded

from prestopet import engine
from prestopet.game import Game
from prestopet.storage import Storage


class GameTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "save.json")
        self.ft = FakeTime(wall=NOON)

    def tearDown(self):
        shutil.rmtree(self.dir)

    def boot(self):
        game = Game(Storage(self.path), self.ft.ticks, self.ft.diff, wall=self.ft.wall,
                    utc_offset_minutes=60, eu_dst=True, rand=seeded())
        game.start()
        return game

    def run_for(self, game, seconds):
        for _ in range(int(seconds)):
            self.ft.advance(1)
            game.update()

    def test_first_boot_has_no_pet(self):
        game = self.boot()
        self.assertIsNone(game.pet)
        self.assertFalse(os.path.exists(self.path))

    def test_adoption_is_saved_at_once(self):
        game = self.boot()
        game.new_game("croquette")
        self.assertTrue(os.path.exists(self.path))
        again = self.boot()
        self.assertEqual(again.pet.character, "croquette")

    def test_a_save_of_the_old_luna_loads_as_louna(self):
        game = self.boot()
        game.new_game("louna")
        data = Storage(self.path).load()
        data["pet"]["character"] = "luna"
        Storage(self.path).save(data)
        again = self.boot()
        self.assertEqual(again.pet.character, "louna")

    def test_actions_are_saved_after_a_short_delay(self):
        game = self.boot()
        game.new_game("louna")
        game.pet.satiety = 20
        ok, _ = game.feed(engine.MEAL)
        self.assertTrue(ok)
        self.run_for(game, 20)
        self.assertEqual(self.boot().pet.counts["meals"], 1)

    def test_restart_after_hours_off_simulates_the_gap(self):
        game = self.boot()
        game.new_game("louna")
        satiety = game.pet.satiety
        self.ft.advance(5 * 3600)       # switched off for five hours
        again = self.boot()
        self.assertLess(again.pet.satiety, satiety - 10)
        self.assertGreaterEqual(again.pet.age, 5 * 3600)

    def test_restart_without_clock_resumes_then_catches_up(self):
        game = self.boot()
        game.new_game("louna")
        satiety = game.pet.satiety
        self.ft.advance(8 * 3600)       # off for eight hours...
        real = self.ft.w
        self.ft.w = OLD                 # ...and the clock was lost
        again = self.boot()
        self.assertIsNone(again.hour())
        self.assertAlmostEqual(again.pet.satiety, satiety, delta=0.5)
        self.run_for(again, 30)
        self.ft.w = real + 30           # network time arrives
        self.assertTrue(again.update())
        self.assertLess(again.pet.satiety, satiety - 20)
        self.assertIn(engine.EV_REUNION, again.take_events())
        self.assertEqual(again.hour(), 22)   # 20:00 UTC, summer time in Paris

    def test_saved_time_never_goes_backwards_without_clock(self):
        self.ft.w = OLD
        game = self.boot()
        game.new_game("louna")
        self.run_for(game, 700)         # a periodic save happens
        first = Storage(self.path).load()["saved_at"]
        self.assertGreaterEqual(first, 600)
        again = self.boot()
        self.run_for(again, 10)
        self.assertGreaterEqual(again.snapshot()["saved_at"], first)

    def test_game_created_without_clock_does_not_age_when_the_time_arrives(self):
        self.ft.w = OLD
        game = self.boot()
        game.new_game("louna")
        self.run_for(game, 700)
        again = self.boot()             # restarted, still without clock
        self.run_for(again, 5)
        self.ft.w = NOON                # network time arrives
        again.update()
        self.assertLess(again.pet.age, 3600)
        self.assertNotIn(engine.EV_REUNION, again.take_events())
        self.ft.advance(3 * 3600)       # from now on, offline time is known
        third = self.boot()
        self.assertGreaterEqual(third.pet.age, 3 * 3600)

    def test_erase(self):
        game = self.boot()
        game.new_game("louna")
        game.erase()
        self.assertIsNone(game.pet)
        self.assertIsNone(self.boot().pet)

    def test_damaged_save_starts_a_new_game(self):
        with open(self.path, "w") as f:
            f.write('{"pet": {"character": "dragon"}}')
        self.assertIsNone(self.boot().pet)

    def test_falling_asleep_is_saved_at_once(self):
        game = self.boot()
        game.new_game("louna")
        game.pet.energy = 12.05
        self.run_for(game, 61)
        self.assertTrue(game.pet.asleep)
        self.assertEqual(self.boot().pet.activity, engine.SLEEP)


if __name__ == "__main__":
    unittest.main()
