import unittest

from helpers import new_pet, seeded

from prestopet import engine, pets, species


class NeedsTest(unittest.TestCase):
    def test_needs_decrease_while_awake(self):
        pet = new_pet()
        pet.energy = 100
        before = (pet.satiety, pet.happiness, pet.energy, pet.hygiene)
        engine.tick(pet, 3600, rand=seeded())
        after = (pet.satiety, pet.happiness, pet.energy, pet.hygiene)
        for b, a in zip(before, after):
            self.assertLess(a, b)

    def test_sleep_restores_energy_and_slows_hunger(self):
        awake = new_pet()
        asleep = new_pet()
        asleep.activity = engine.SLEEP
        awake.energy = asleep.energy = 40
        engine.tick(awake, 1800, rand=seeded())
        engine.tick(asleep, 1800, rand=seeded())
        self.assertGreater(asleep.energy, 40)
        self.assertLess(awake.energy, 40)
        self.assertGreater(asleep.satiety, awake.satiety)

    def test_stats_stay_within_bounds(self):
        pet = new_pet()
        engine.catch_up(pet, 10 * 86400, rand=seeded())
        for v in (pet.satiety, pet.happiness, pet.energy, pet.hygiene):
            self.assertGreaterEqual(v, 0)
            self.assertLessEqual(v, 100)

    def test_age_counts_real_time(self):
        pet = new_pet()
        engine.tick(pet, 90, rand=seeded())
        self.assertEqual(pet.age, 90)
        self.assertEqual(pet.days, 1)
        engine.catch_up(pet, 2 * 86400, rand=seeded())
        self.assertEqual(pet.days, 3)


class NeverDiesTest(unittest.TestCase):
    """The golden rule: whatever happens, care always brings the pet back."""

    def test_recovers_after_a_month_of_neglect(self):
        pet = new_pet()
        engine.catch_up(pet, 30 * 86400, rand=seeded())
        self.assertEqual(pet.days, 31)
        rand = seeded(2)
        while pet.asleep and not engine.toggle_sleep(pet)[0]:
            engine.tick(pet, 600, rand=rand)    # too sleepy: let her rest a little
        for _ in range(3):
            engine.clean(pet)
            engine.feed(pet, engine.MEAL, rand)
            for _ in range(5):
                engine.caress(pet)
            pet.caress_fatigue = 0
        while engine.can_play(pet) and pet.happiness < 80:
            engine.play(pet)
        self.assertGreaterEqual(pet.satiety, 60)
        self.assertGreaterEqual(pet.hygiene, 90)
        self.assertGreaterEqual(pet.happiness, 60)
        self.assertNotEqual(engine.mood(pet), engine.SULKING)

    def test_exhausted_pet_falls_asleep_and_wakes_rested(self):
        pet = new_pet()
        pet.energy = 12.5
        events = engine.tick(pet, 600, rand=seeded())
        self.assertIn(engine.EV_FELL_ASLEEP, events)
        for _ in range(12 * 60):
            if engine.EV_WOKE_UP in engine.tick(pet, 60, rand=seeded()):
                break
        self.assertFalse(pet.asleep)
        self.assertGreaterEqual(pet.energy, 99)


class NapTest(unittest.TestCase):
    def test_a_nap_lasts_until_someone_comes_back(self):
        pet = new_pet()
        pet.energy = 95
        self.assertTrue(engine.nap(pet))
        self.assertTrue(pet.asleep)
        for _ in range(6):
            engine.tick(pet, 600, hour=14, rand=seeded())
        self.assertTrue(pet.asleep, "rested, but waits for a touch")
        self.assertTrue(engine.end_nap(pet, hour=14))
        self.assertFalse(pet.asleep)
        self.assertFalse(pet.napping)

    def test_a_nap_at_night_becomes_the_night(self):
        pet = new_pet()
        engine.nap(pet)
        engine.tick(pet, 60, hour=22, rand=seeded())
        self.assertFalse(pet.napping)
        self.assertFalse(engine.end_nap(pet, hour=22))
        engine.tick(pet, 9 * 3600, hour=3, rand=seeded())
        self.assertIn(engine.EV_WOKE_UP, engine.tick(pet, 60, hour=8, rand=seeded()))

    def test_a_sleeping_pet_does_not_nap(self):
        pet = new_pet()
        engine.nap(pet)
        self.assertFalse(engine.nap(pet))

    def test_the_nap_is_saved(self):
        pet = new_pet()
        engine.nap(pet)
        again = engine.Pet.from_dict(pet.to_dict(), pet.profile)
        self.assertTrue(again.napping)
        data = pet.to_dict()
        data["activity"] = engine.IDLE
        self.assertFalse(engine.Pet.from_dict(data, pet.profile).napping)


class DayNightTest(unittest.TestCase):
    def test_goes_to_bed_at_night_and_wakes_in_the_morning(self):
        pet = new_pet()
        pet.energy = 60
        events = engine.tick(pet, 60, hour=22, rand=seeded())
        self.assertIn(engine.EV_FELL_ASLEEP, events)
        engine.tick(pet, 6 * 3600, hour=3, rand=seeded())
        self.assertTrue(pet.asleep, "stays asleep during the night, even rested")
        events = engine.tick(pet, 60, hour=7, rand=seeded())
        self.assertIn(engine.EV_WOKE_UP, events)

    def test_stays_awake_for_a_while_after_being_woken(self):
        pet = new_pet()
        pet.energy = 60
        engine.tick(pet, 60, hour=23, rand=seeded())
        self.assertTrue(pet.asleep)
        ok, reaction = engine.toggle_sleep(pet, hour=23)
        self.assertTrue(ok)
        self.assertEqual(reaction, engine.R_WAKE)
        engine.tick(pet, 600, hour=23, rand=seeded())
        self.assertFalse(pet.asleep)
        engine.tick(pet, engine.STAY_AWAKE_S, hour=23, rand=seeded())
        self.assertTrue(pet.asleep)

    def test_unknown_hour_means_no_night(self):
        p = pets.profile("louna")
        self.assertFalse(engine.is_night(p, None))
        self.assertTrue(engine.is_night(p, 23))
        self.assertTrue(engine.is_night(p, 2))
        self.assertFalse(engine.is_night(p, 12))


class ActionsTest(unittest.TestCase):
    def test_meal(self):
        pet = new_pet()
        pet.satiety = 20
        ok, reaction = engine.feed(pet, engine.MEAL, seeded())
        self.assertTrue(ok)
        self.assertEqual(reaction, engine.R_EAT)
        self.assertEqual(pet.satiety, 60)
        self.assertEqual(pet.activity, engine.EAT)
        self.assertEqual(len(pet.mess_timers), 1)

    def test_full_pet_refuses_a_meal(self):
        pet = new_pet()
        pet.satiety = 95
        self.assertEqual(engine.feed(pet, engine.MEAL), (False, engine.R_FULL))
        self.assertEqual(pet.satiety, 95)

    def test_treats_please_less_in_a_row(self):
        pet = new_pet()
        pet.happiness = 10
        engine.feed(pet, engine.TREAT)
        first = pet.happiness - 10
        before = pet.happiness
        engine.feed(pet, engine.TREAT)
        self.assertLess(pet.happiness - before, first)

    def test_meal_leads_to_a_mess_and_cleaning_removes_it(self):
        pet = new_pet()
        pet.satiety = 20
        engine.feed(pet, engine.MEAL, seeded())
        events = engine.tick(pet, 5 * 3600, rand=seeded())
        self.assertIn(engine.EV_MESS, events)
        self.assertEqual(pet.messes, 1)
        ok, _ = engine.clean(pet)
        self.assertTrue(ok)
        self.assertEqual(pet.messes, 0)

    def test_already_clean(self):
        pet = new_pet()
        self.assertEqual(engine.clean(pet), (False, engine.R_ALREADY_CLEAN))

    def test_caress_diminishes_when_repeated(self):
        pet = new_pet()
        pet.happiness = 10
        gains = []
        for _ in range(4):
            before = pet.happiness
            engine.caress(pet)
            gains.append(pet.happiness - before)
        self.assertEqual(gains, sorted(gains, reverse=True))
        engine.tick(pet, 600, rand=seeded())
        self.assertEqual(pet.caress_fatigue, 0)

    def test_sleeping_pet_purrs_but_does_not_eat_or_play(self):
        pet = new_pet()
        pet.activity = engine.SLEEP
        self.assertEqual(engine.feed(pet, engine.MEAL), (False, engine.R_ASLEEP))
        self.assertEqual(engine.play(pet), (False, engine.R_ASLEEP))
        self.assertEqual(engine.caress(pet), (True, engine.R_PURR_ASLEEP))
        self.assertTrue(pet.asleep)

    def test_play_costs_energy_and_tired_pet_refuses(self):
        pet = new_pet()
        ok, _ = engine.play(pet)
        self.assertTrue(ok)
        self.assertLess(pet.energy, 90)
        pet.energy = 10
        self.assertEqual(engine.play(pet), (False, engine.R_TOO_TIRED))

    def test_sulky_pet_plays_half_heartedly(self):
        happy = new_pet()
        sulky = new_pet()
        sulky.happiness = 10
        engine.play(happy)
        ok, reaction = engine.play(sulky)
        self.assertTrue(ok)
        self.assertEqual(reaction, engine.R_PLAY_SULKY)
        self.assertLess(sulky.happiness - 10, happy.happiness - 80)

    def test_bed_needs_some_tiredness_by_day(self):
        pet = new_pet()
        pet.energy = 95
        self.assertEqual(engine.toggle_sleep(pet, hour=14), (False, engine.R_NOT_SLEEPY))
        self.assertEqual(engine.toggle_sleep(pet, hour=22), (True, engine.R_GO_TO_BED))
        pet.energy = 10
        self.assertEqual(engine.toggle_sleep(pet), (False, engine.R_TOO_SLEEPY))


class MoodTest(unittest.TestCase):
    def test_moods(self):
        pet = new_pet()
        pet.happiness = 90
        self.assertEqual(engine.mood(pet), engine.HAPPY)
        pet.satiety = 10
        self.assertEqual(engine.mood(pet), engine.HUNGRY)
        self.assertEqual(engine.urgent_need(pet), engine.NEED_FOOD)
        pet.happiness = 10
        self.assertEqual(engine.mood(pet), engine.SULKING)
        pet.activity = engine.SLEEP
        self.assertEqual(engine.mood(pet), engine.ASLEEP)

    def test_no_need_when_all_is_well(self):
        self.assertIsNone(engine.urgent_need(new_pet()))


class AutonomyTest(unittest.TestCase):
    def test_pet_changes_activity_by_itself(self):
        pet = new_pet()
        seen = set()
        rand = seeded(3)
        for _ in range(300):
            engine.tick(pet, 5, hour=12, rand=rand)
            seen.add(pet.activity)
        self.assertTrue({engine.IDLE, engine.WALK, engine.GROOM} <= seen, seen)

    def test_pet_calls_for_attention_when_in_need(self):
        pet = new_pet()
        pet.satiety = 5
        calls = 0
        rand = seeded(4)
        for _ in range(100):
            pet.activity_left = 0
            engine.choose_activity(pet, rand)
            calls += pet.activity == engine.CALL
        self.assertGreater(calls, 20)


class CatchUpTest(unittest.TestCase):
    def test_long_absence_is_capped_but_ages(self):
        pet = new_pet()
        engine.catch_up(pet, 60 * 86400, rand=seeded())
        self.assertEqual(int(pet.age), 60 * 86400)

    def test_reunion_after_a_long_absence(self):
        pet = new_pet()
        events = engine.catch_up(pet, 8 * 3600, rand=seeded())
        self.assertIn(engine.EV_REUNION, events)
        events = engine.catch_up(pet, 3600, rand=seeded())
        self.assertNotIn(engine.EV_REUNION, events)

    def test_catch_up_matches_live_play(self):
        live = new_pet()
        later = new_pet()
        engine.tick(live, 4 * 3600, hour=12, rand=seeded())
        engine.catch_up(later, 4 * 3600, hour_at=lambda offset: 12, rand=seeded())
        self.assertAlmostEqual(live.satiety, later.satiety, places=3)
        self.assertAlmostEqual(live.energy, later.energy, places=3)


class SaveFormatTest(unittest.TestCase):
    def test_round_trip(self):
        pet = new_pet("croquette")
        pet.satiety = 42.5
        pet.messes = 2
        pet.mess_timers = [1200.0]
        pet.counts["meals"] = 7
        pet.activity = engine.SLEEP
        data = pet.to_dict()
        back = engine.Pet.from_dict(data, pets.profile("croquette"))
        self.assertEqual(back.to_dict(), data)

    def test_damaged_values_fall_back_to_defaults(self):
        data = {"character": "louna", "satiety": "lots", "happiness": 250, "energy": None,
                "messes": 99, "activity": "flying", "counts": {"meals": -3}}
        pet = engine.Pet.from_dict(data, pets.profile("louna"))
        self.assertEqual(pet.satiety, 80)
        self.assertEqual(pet.happiness, 100)
        self.assertEqual(pet.messes, 3)
        self.assertEqual(pet.activity, engine.IDLE)
        self.assertEqual(pet.counts["meals"], 0)


class CharactersTest(unittest.TestCase):
    def test_personalities_differ(self):
        louna = pets.profile("louna")
        croquette = pets.profile("croquette")
        self.assertGreater(louna["caress"], croquette["caress"])
        self.assertGreater(croquette["play_happiness"], louna["play_happiness"])
        self.assertLess(croquette["energy_awake"], louna["energy_awake"])   # drains faster
        self.assertGreater(croquette["treat_happiness"], louna["treat_happiness"])

    def test_unknown_trait_is_rejected(self):
        with self.assertRaises(KeyError):
            species.make_profile(species.CAT, {"flying": 2})

    def test_every_character_is_complete(self):
        for cid in pets.CHARACTERS:
            c = pets.character(cid)
            self.assertEqual(c["id"], cid)
            coat = pets.coat(cid)
            used = set()
            for runsets in coat.RUNSETS.values():
                for text in runsets:
                    used.update(chr(c) for c in text[2::3])
            missing = used - set(c["palette"])
            self.assertFalse(missing, "%s palette lacks %s" % (cid, missing))
            art = pets.sleep_art(cid)
            palette = pets.sleep_palette(cid)
            for _, _, rows in art.LAYERS:
                self.assertFalse(set("".join(rows)) - set(palette) - {"."})


if __name__ == "__main__":
    unittest.main()
