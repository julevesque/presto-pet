# The main loop: touch, simulation, animation, and what happens when nobody plays: the pet
# curls up for a nap, and the screen may go dark (SCREEN_OFF_MINUTES).

import gc
import time

from prestopet.canvas import Canvas
from prestopet.game import Game
from prestopet.i18n import Texts
from prestopet.leds import Leds
from prestopet.screens import MainScreen, TitleScreen
from prestopet.settings import Settings, path_next_to
from prestopet.storage import Storage
from prestopet.touch import DOWN, TouchTracker

LOOP_MS = 20             # while the screen is on
DARK_LOOP_MS = 100       # while it is off: touch is still read, the pet keeps living
MAX_ERRORS = 10


def _setting(config, name, default):
    return getattr(config, name, default) if config is not None else default


class App:
    def __init__(self, hw, config=None, time_sync=None):
        self.hw = hw
        self.time_sync = time_sync
        self.screen_off_ms = int(_setting(config, "SCREEN_OFF_MINUTES", 0) * 60000)
        self.canvas = Canvas(hw.display, hw.board)
        self.tracker = TouchTracker(time.ticks_diff)
        save_file = _setting(config, "SAVE_FILE", "prestopet_save.json")
        self.settings = Settings(path_next_to(save_file), _setting(config, "LANGUAGE", "fr"))
        self.settings.load()
        self.lang = self.settings.language
        self.texts = Texts(self.lang)
        hw.backlight = self.settings.backlight
        self.leds = Leds(hw, time.ticks_diff)
        self.game = Game(Storage(save_file),
                         time.ticks_ms, time.ticks_diff,
                         utc_offset_minutes=_setting(config, "UTC_OFFSET_MINUTES", 60),
                         eu_dst=_setting(config, "EU_SUMMER_TIME", True))
        self.screen = None
        self.dark = False
        self.wake_swallow = False
        self.last_touch = time.ticks_ms()
        self.napped = False          # one nap per absence: set again by the next touch

    def set_brightness(self, level):
        self.settings.brightness = level
        self.hw.backlight = self.settings.backlight
        if not self.dark:
            self.hw.screen_on(True)

    def set_language(self, lang):
        old = self.texts
        self.settings.language = lang
        self.lang = lang
        self.texts = Texts(lang)
        self.texts.set_pet(old.name, old.gender)

    def purr_lights(self, now, asleep=False):
        self.leds.purr(now, self.settings.led_level * (0.6 if asleep else 1.0))

    def show(self, screen, now):
        self.screen = screen
        gc.collect()
        screen.enter(now)

    def run(self):
        self.game.start()
        now = time.ticks_ms()
        self.hw.screen_on(True)
        self.show(TitleScreen(self), now)
        errors = 0
        while True:
            try:
                self.step(time.ticks_ms())
                errors = 0
            except KeyboardInterrupt:
                self.game.save_now()
                raise
            except Exception as e:
                # No error may stop the pet; a series of them restarts the device.
                errors += 1
                print("Error:", repr(e))
                if errors >= MAX_ERRORS:
                    self.game.save_now()
                    import machine
                    machine.reset()
                gc.collect()
                time.sleep_ms(500)
            time.sleep_ms(DARK_LOOP_MS if self.dark else LOOP_MS)

    def step(self, now):
        down, x, y = self.hw.read_touch()
        event = self.tracker.update(down, x, y, now)
        if down:
            self.last_touch = now
            self.napped = False
        pet = self.game.pet
        if event is not None and event[0] == DOWN and pet is not None and pet.napping:
            # The touch that wakes the pet does nothing else.
            self.game.end_nap()
            self.wake_swallow = True
        if self.dark:
            if event is not None and event[0] == DOWN:
                self.wake(now)
            self.game.update()
            self.check_nap(now)
            if self.time_sync is not None:
                self.time_sync.poll(now)
            return
        if event is not None:
            if self.wake_swallow:
                # The touch that lit the screen does nothing else.
                if event[0] != DOWN:
                    self.wake_swallow = False
            else:
                self.screen.touch(event[0], event[1], event[2], now)
        self.game.update()
        self.check_nap(now)
        self.screen.update(now)
        self.leds.update(now)
        if self.time_sync is not None and not self.tracker.pressed:
            self.time_sync.poll(now)
        if self.screen_off_ms and time.ticks_diff(now, self.last_touch) > self.screen_off_ms:
            self.dark = True
            self.hw.screen_on(False)
            self.leds.stop()

    def check_nap(self, now):
        if not self.napped and time.ticks_diff(now, self.last_touch) > self.settings.nap_ms:
            self.nap(now)

    def nap(self, now):
        self.napped = True
        pet = self.game.pet
        if pet is None or not getattr(self.screen, "PET_SHOWN", False):
            return
        if not isinstance(self.screen, MainScreen):
            self.show(MainScreen(self), now)
        self.game.nap()

    def wake(self, now):
        self.dark = False
        self.wake_swallow = True
        self.hw.screen_on(True)
        self.screen.enter(now)   # the pet may have changed in the dark
