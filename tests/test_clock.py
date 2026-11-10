import calendar
import unittest

from helpers import NOON, OLD, FakeTime

from prestopet.clock import GameClock, local_hour, wall_is_trusted


def make(ft, saved_at):
    return GameClock(saved_at=saved_at, wall=ft.wall, ticks=ft.ticks, diff=ft.diff)


class GameClockTest(unittest.TestCase):
    def test_trusted_clock_knows_the_time_spent_off(self):
        ft = FakeTime(wall=NOON)
        clock = make(ft, NOON - 3 * 3600)
        self.assertTrue(clock.trusted)
        self.assertEqual(clock.boot_gap, 3 * 3600)
        self.assertEqual(clock.now(), NOON)

    def test_clock_going_backwards_is_not_a_gap(self):
        ft = FakeTime(wall=NOON)
        self.assertEqual(make(ft, NOON + 500).boot_gap, 0)

    def test_untrusted_clock_resumes_from_the_save(self):
        ft = FakeTime(wall=OLD)
        saved = NOON - 86400
        clock = make(ft, saved)
        self.assertFalse(clock.trusted)
        self.assertEqual(clock.boot_gap, 0)
        ft.advance(120)
        self.assertEqual(clock.now(), saved + 120)

    def test_network_time_reveals_the_offline_period(self):
        ft = FakeTime(wall=OLD)
        saved = NOON - 5 * 3600
        clock = make(ft, saved)
        ft.advance(600)                 # ten minutes of play before NTP answers
        self.assertEqual(clock.poll(), 0)
        ft.w = NOON                     # NTP sets the clock
        self.assertEqual(clock.poll(), 5 * 3600 - 600)
        self.assertTrue(clock.trusted)
        self.assertEqual(clock.poll(), 0, "reported once")
        self.assertEqual(clock.now(), NOON)

    def test_new_game_without_any_clock(self):
        ft = FakeTime(wall=OLD)
        clock = make(ft, None)
        ft.advance(5)
        self.assertEqual(clock.now(), 5)

    def test_estimate_never_anchored_reveals_no_gap(self):
        # A game created while the clock was unknown: its timestamps start from zero, so the
        # first real time says nothing about how long the device was off.
        ft = FakeTime(wall=OLD)
        clock = GameClock(saved_at=3600, anchored=False, wall=ft.wall, ticks=ft.ticks, diff=ft.diff)
        ft.w = NOON
        self.assertEqual(clock.poll(), 0)
        self.assertTrue(clock.anchored)
        ft.w = NOON
        later = GameClock(saved_at=3600, anchored=False, wall=ft.wall, ticks=ft.ticks, diff=ft.diff)
        self.assertEqual(later.boot_gap, 0)

    def test_counter_wrap_is_handled_by_diff(self):
        period = 1 << 30
        ft = FakeTime(wall=OLD, ticks=period - 500)
        ticks = lambda: ft.t % period  # noqa: E731
        diff = lambda a, b: ((a - b + period // 2) % period) - period // 2  # noqa: E731
        clock = GameClock(saved_at=1000, wall=ft.wall, ticks=ticks, diff=diff)
        ft.advance(2, wall=False)
        self.assertEqual(clock.now(), 1002)

    def test_trust(self):
        self.assertTrue(wall_is_trusted(NOON))
        self.assertFalse(wall_is_trusted(OLD))


class LocalHourTest(unittest.TestCase):
    def test_utc(self):
        self.assertEqual(local_hour(NOON), 12)

    def test_paris_summer_and_winter(self):
        summer = calendar.timegm((2026, 7, 1, 12, 0, 0))
        winter = calendar.timegm((2026, 12, 1, 12, 0, 0))
        self.assertEqual(local_hour(summer, 60, True), 14)
        self.assertEqual(local_hour(winter, 60, True), 13)

    def test_dst_switch_instant(self):
        # 2026: last Sunday of March is the 29th, at 01:00 UTC.
        before = calendar.timegm((2026, 3, 29, 0, 59, 0))
        after = calendar.timegm((2026, 3, 29, 1, 0, 0))
        self.assertEqual(local_hour(before, 60, True), 1)
        self.assertEqual(local_hour(after, 60, True), 3)


if __name__ == "__main__":
    unittest.main()
