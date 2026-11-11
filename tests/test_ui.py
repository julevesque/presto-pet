"""The whole interface with a fake Presto: every screen and action runs without error, and
touches do what they should. No Pillow needed."""

import os
import shutil
import tempfile
import time
import types
import unittest

import helpers  # noqa: F401

_SAVED = {}
_now = [0]


def setUpModule():
    for name in ("ticks_ms", "ticks_diff", "ticks_add", "sleep_ms"):
        _SAVED[name] = getattr(time, name, None)
    time.ticks_ms = lambda: _now[0]
    time.ticks_diff = lambda a, b: a - b
    time.ticks_add = lambda a, b: a + b
    time.sleep_ms = lambda ms: None


def tearDownModule():
    for name, value in _SAVED.items():
        if value is None:
            delattr(time, name)
        else:
            setattr(time, name, value)


class NullDisplay:
    def __init__(self):
        self.calls = 0

    def create_pen(self, r, g, b):
        return (r, g, b)

    def set_pen(self, pen):
        pass

    def set_clip(self, x, y, w, h):
        for v in (x, y, w, h):
            assert isinstance(v, int), (x, y, w, h)

    def remove_clip(self):
        pass

    def rectangle(self, x, y, w, h):
        # PicoGraphics refuses floats: catch them here.
        for v in (x, y, w, h):
            assert isinstance(v, int), (x, y, w, h)
        self.calls += 1


class Board:
    def __init__(self):
        self.display = NullDisplay()
        self.updates = 0

    def update(self):
        self.updates += 1

    def partial_update(self, x, y, w, h):
        assert 0 <= x and 0 <= y and x + w <= 480 and y + h <= 480, (x, y, w, h)
        self.updates += 1

    def set_backlight(self, v):
        self.backlight = v


class Hardware:
    def __init__(self):
        self.board = Board()
        self.display = self.board.display
        self.down = False
        self.x = self.y = 0
        self.lit = True

    def screen_on(self, on):
        self.lit = on

    def set_leds(self, colours):
        self.leds = colours

    def read_touch(self):
        return self.down, self.x, self.y


class UiTest(unittest.TestCase):
    def setUp(self):
        from prestopet.app import App
        from prestopet.screens import TitleScreen
        self.dir = tempfile.mkdtemp()
        self.hw = Hardware()
        config = types.SimpleNamespace(LANGUAGE="fr", SAVE_FILE=os.path.join(self.dir, "s.json"),
                                       SCREEN_OFF_MINUTES=1)
        self.app = App(self.hw, config)
        self.app.game.start()
        self.app.show(TitleScreen(self.app), _now[0])

    def tearDown(self):
        shutil.rmtree(self.dir)

    def wait(self, ms):
        end = _now[0] + ms
        while _now[0] < end:
            _now[0] += 20
            self.app.step(_now[0])

    def tap(self, x, y):
        self.hw.down, self.hw.x, self.hw.y = True, x, y
        self.wait(80)
        self.hw.down = False
        self.wait(100)

    def screen(self):
        return type(self.app.screen).__name__

    def adopt(self, x=120):
        self.wait(200)
        self.tap(240, 240)
        self.tap(x, 200)
        self.tap(240, 430)
        self.assertEqual(self.screen(), "MainScreen")
        return self.app.game.pet

    def test_adoption_and_care(self):
        pet = self.adopt(360)
        self.assertEqual(pet.character, "croquette")
        pet.satiety = 30
        self.tap(80, 40)            # feed
        self.tap(160, 240)          # meal
        self.assertGreater(pet.satiety, 60)
        self.wait(5000)
        before = pet.counts["caresses"]
        r = self.app.screen.view().rect     # the pet itself, wherever her walk took her
        self.tap(r[0] + r[2] // 2, r[1] + r[3] // 2)
        self.assertEqual(pet.counts["caresses"], before + 1)
        self.tap(240, 40)           # caress button
        self.assertEqual(pet.counts["caresses"], before + 2)
        pet.messes = 2
        self.wait(200)
        self.tap(80, 440)           # clean
        self.assertEqual(pet.messes, 0)

    def test_play_session(self):
        pet = self.adopt()
        self.tap(400, 40)
        self.tap(160, 240)          # the ball
        for x in (100, 400, 150, 380, 120):
            self.tap(x, 360)
            self.wait(3500)
        self.assertEqual(pet.counts["plays"], 5)
        self.wait(2000)
        self.assertIsNone(self.app.screen.play)

    def test_feather_session(self):
        pet = self.adopt()
        self.tap(400, 40)
        self.tap(320, 240)          # the feather
        screen = self.app.screen
        self.assertTrue(screen.wand.visible)
        for x in (120, 380, 130, 370, 140, 360):
            # The finger waves the feather near the floor, on one side then the other
            self.hw.down, self.hw.x, self.hw.y = True, x, 330
            self.wait(3000)
            self.hw.down = False
            self.wait(1500)
        self.assertGreaterEqual(pet.counts["plays"], 3)

    def test_woken_while_going_to_bed(self):
        pet = self.adopt()
        pet.energy = 50
        self.tap(240, 440)
        screen = self.app.screen
        self.assertTrue(screen.bedtime)
        self.wait(1500)
        cushion = screen.cushion.rect
        marked = []
        mark = screen.scene.mark
        screen.scene.mark = lambda r: (marked.append(r), mark(r))
        self.tap(240, 440)          # awake again before curling up
        self.wait(500)
        self.assertFalse(screen.bedtime)
        self.assertFalse(screen.cushion.visible)
        self.assertEqual(screen.awake.lift, 0)
        # The whole cushion is redrawn away: nothing of it is left on the screen
        self.assertIn(cushion, marked)

    def test_eyes_follow_the_finger_and_the_birds(self):
        self.adopt()
        self.wait(500)
        screen = self.app.screen
        view = screen.awake
        self.hw.down, self.hw.x, self.hw.y = True, 40, 200
        self.wait(200)
        self.assertEqual(view.gaze, 40)
        self.hw.down = False
        self.wait(200)
        self.assertIsNone(view.gaze)
        screen.next_visit = 0
        self.wait(100)
        self.assertTrue(screen.visitor.visible)
        self.assertTrue(view.chatter)
        self.wait(10000)
        self.assertFalse(screen.visitor.visible)

    def test_sleep_and_wake(self):
        pet = self.adopt()
        pet.energy = 50
        self.app.game.hour = lambda epoch=None: 22
        self.tap(240, 440)
        self.assertTrue(pet.asleep)
        screen = self.app.screen
        self.assertTrue(screen.bedtime)        # first onto the cushion, turning and kneading
        self.assertIs(screen.view(), screen.awake)
        self.wait(1000)
        self.assertGreater(screen.awake.lift, 0)
        self.wait(6000)
        self.assertFalse(screen.bedtime)
        self.assertIs(screen.view(), screen.sleeping)
        self.assertTrue(screen.scene.night)
        self.wait(3000)             # breathing, zZZ
        self.tap(80, 40)            # feeding waits
        self.assertTrue(pet.asleep)
        self.app.game.hour = lambda epoch=None: 12
        self.tap(240, 440)
        self.assertFalse(pet.asleep)
        self.wait(1100)
        self.assertFalse(self.app.screen.scene.night)

    def test_a_caress_lights_the_leds_in_pink(self):
        self.adopt()
        self.wait(3000)
        self.tap(240, 40)                    # caress button
        self.wait(700)
        r, g, b = self.hw.leds[3]
        self.assertTrue(r > b > g, self.hw.leds)
        self.wait(3000)
        self.assertEqual(self.hw.leds, ((0, 0, 0),) * 7)

    def test_the_room_follows_the_time_of_day_not_the_nap(self):
        pet = self.adopt()
        self.app.game.hour = lambda epoch=None: 14
        self.app.settings.nap_minutes = 5
        self.app.screen_off_ms = 0
        pet.energy = 90
        self.wait(5 * 60000 + 1500)
        self.assertTrue(pet.napping)
        self.assertFalse(self.app.screen.scene.night, "an afternoon nap keeps the daylight")
        self.app.game.hour = lambda epoch=None: 21
        self.wait(1500)
        self.assertTrue(self.app.screen.scene.night, "the evening comes during the nap")

    def test_stats_and_erase_needs_a_hold(self):
        self.adopt()
        self.tap(400, 440)
        self.assertEqual(self.screen(), "StatsScreen")
        self.tap(110, 430)
        self.assertEqual(self.screen(), "ResetScreen")
        self.tap(350, 430)          # a simple tap does not erase
        self.assertIsNotNone(self.app.game.pet)
        self.hw.down, self.hw.x, self.hw.y = True, 350, 430
        self.wait(1700)
        self.hw.down = False
        self.wait(100)
        self.assertIsNone(self.app.game.pet)
        self.assertEqual(self.screen(), "ChooseScreen")

    def test_restart_resumes_the_game(self):
        from prestopet.app import App
        from prestopet.screens import TitleScreen
        self.adopt()
        config = types.SimpleNamespace(LANGUAGE="en", SAVE_FILE=self.app.game.storage.path,
                                       SCREEN_OFF_MINUTES=0)
        app2 = App(self.hw, config)
        app2.game.start()
        app2.show(TitleScreen(app2), _now[0])
        self.app = app2
        self.wait(2500)
        self.assertEqual(self.screen(), "MainScreen")
        self.assertEqual(app2.game.pet.character, "louna")

    def test_the_pet_naps_when_alone_and_the_waking_touch_does_nothing_else(self):
        pet = self.adopt()
        self.tap(400, 440)                   # statistics: the nap brings back the room
        self.app.settings.nap_minutes = 5
        self.app.screen_off_ms = 0
        pet.energy = 90
        self.wait(5 * 60000 + 500)
        self.assertEqual(self.screen(), "MainScreen")
        self.assertTrue(pet.asleep and pet.napping)
        self.wait(30 * 60000)
        self.assertTrue(pet.asleep, "no one came back")
        before = pet.counts["caresses"]
        r = self.app.screen.view().rect
        self.tap(r[0] + r[2] // 2, r[1] + r[3] // 2)
        self.assertFalse(pet.asleep)
        self.assertEqual(pet.counts["caresses"], before)
        self.wait(5 * 60000 - 1000)
        self.assertFalse(pet.asleep, "the delay starts again from the last touch")

    def test_the_pet_also_naps_while_the_screen_is_dark(self):
        pet = self.adopt()
        self.app.settings.nap_minutes = 5
        pet.energy = 90
        self.wait(6 * 60000)
        self.assertFalse(self.hw.lit)
        self.assertTrue(pet.napping)
        self.tap(240, 300)
        self.assertTrue(self.hw.lit)
        self.assertFalse(pet.asleep)

    def test_options_change_brightness_and_nap_and_are_kept(self):
        from prestopet.app import App
        from prestopet.settings import BRIGHTNESS
        self.adopt()
        self.tap(400, 440)                   # statistics
        self.tap(248, 436)                   # options
        self.assertEqual(self.screen(), "OptionsScreen")
        self.tap(392, 136)                   # brightness: high
        self.assertEqual(self.hw.backlight, BRIGHTNESS["high"])
        self.tap(88, 262)                    # nap after 5 min
        self.tap(240, 440)                   # back
        self.assertEqual(self.screen(), "StatsScreen")
        config = types.SimpleNamespace(LANGUAGE="fr", SAVE_FILE=self.app.game.storage.path)
        app2 = App(self.hw, config)
        self.assertEqual(app2.settings.brightness, "high")
        self.assertEqual(app2.settings.nap_minutes, 5)
        self.assertEqual(app2.hw.backlight, BRIGHTNESS["high"])

    def test_language_is_chosen_in_the_options_and_kept(self):
        from prestopet.app import App
        self.adopt()
        self.tap(400, 440)                   # statistics
        self.tap(248, 436)                   # options
        self.tap(352, 368)                   # English
        self.assertEqual(self.app.lang, "en")
        self.assertEqual(self.app.texts.get("back"), "Back")
        self.assertTrue(self.app.texts.name, "the pet name is kept for the messages")
        self.tap(240, 440)                   # back
        self.assertEqual(self.screen(), "StatsScreen")
        self.assertEqual(self.app.screen.t.get("options"), "Options")
        config = types.SimpleNamespace(LANGUAGE="fr", SAVE_FILE=self.app.game.storage.path)
        self.assertEqual(App(self.hw, config).lang, "en", "the choice wins over config.LANGUAGE")
        self.tap(248, 436)                   # options
        self.tap(124, 368)                   # Français
        self.assertEqual(self.app.texts.get("back"), "Retour")

    def test_screen_goes_dark_and_the_waking_touch_does_nothing(self):
        pet = self.adopt()
        self.wait(61000)
        self.assertFalse(self.hw.lit)
        before = pet.counts["caresses"]
        self.tap(240, 300)
        self.assertTrue(self.hw.lit)
        self.assertEqual(pet.counts["caresses"], before)


if __name__ == "__main__":
    unittest.main()
