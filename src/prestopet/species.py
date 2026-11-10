# Species rules: how fast needs change and how much each action helps.
#
# A species is a plain dict of numbers. A character (see prestopet/pets) picks a species and
# may tweak some of these numbers with personality multipliers, so new animals never need
# changes to the simulation engine.
#
# Rates are in points per hour on a 0..100 scale. Negative values decrease the stat.

CAT = {
    "id": "cat",

    # Natural evolution
    "satiety_awake": -5.0,        # 100 -> 30 in about 14 hours awake
    "satiety_asleep": -2.0,
    "happiness_awake": -2.5,
    "happiness_asleep": -0.5,
    "energy_awake": -6.0,
    "energy_asleep": 14.0,        # a full night restores everything
    "hygiene": -2.0,
    "hygiene_per_mess": -3.0,     # each mess left on the floor
    "sad_when_hungry": -2.0,      # extra happiness loss while satiety is low
    "sad_when_dirty": -1.5,       # extra happiness loss while hygiene is low or messes remain

    # Actions
    "meal": 40.0,                 # satiety gained by a meal
    "meal_happiness": 3.0,
    "treat_satiety": 8.0,
    "treat_happiness": 10.0,
    "caress": 7.0,                # happiness gained by a caress (less when repeated quickly)
    "play_happiness": 6.0,        # per throw of the ball
    "play_energy": 3.0,
    "play_satiety": 1.5,
    "play_hygiene": 1.0,
    "clean": 50.0,                # hygiene gained by a brush

    # Thresholds
    "full": 90.0,                 # refuses a meal above this satiety
    "play_min_energy": 15.0,      # too tired to play below this energy
    "exhausted": 12.0,            # falls asleep wherever she is
    "bedtime_energy": 75.0,       # at night, goes to bed below this energy
    "sleepy_energy": 80.0,        # accepts to be put to bed below this energy (any time)
    "wake_min_energy": 30.0,      # can be woken up above this energy
    "morning_energy": 60.0,       # wakes up by herself in the day above this energy
    "night_start": 21,            # local hours, used only when the clock is known
    "night_end": 7,

    # Litter: a meal leads to a mess after a while
    "mess_delay_min": 2 * 3600,
    "mess_delay_max": 4 * 3600,
    "max_messes": 3,
}


SPECIES = {"cat": CAT}


def make_profile(species, personality=None):
    """The numbers used by the engine for one animal: the species rules, with each value
    named in `personality` multiplied by its factor."""
    profile = dict(species)
    if personality:
        for key in personality:
            if key not in profile:
                raise KeyError("unknown personality trait: " + key)
            profile[key] = profile[key] * personality[key]
    return profile
