# Simulation engine: the state of the pet and the rules of the game.
#
# Pure Python with no hardware dependency: it runs unchanged under MicroPython on the Presto
# and under CPython for the unit tests. Time is always given in seconds by the caller; the
# engine never reads a clock itself.
#
# Golden rule: the pet never dies. A neglected pet gets hungry, sulky or tired, but every
# state can be recovered with a little care.

import random

SAVE_VERSION = 1

MAX = 100.0
LOW = 30.0          # below this, a need is shown as urgent
SULKY = 25.0        # below this happiness, the pet sulks and plays half-heartedly

# Activities. Only SLEEP changes the rules; the others are what the pet is doing right now,
# shown by the user interface.
IDLE = "idle"
WALK = "walk"
GROOM = "groom"
STRETCH = "stretch"
CALL = "call"       # asks for attention
SLEEP = "sleep"
EAT = "eat"
PLAY = "play"
PURR = "purr"
BRUSH = "brush"
ACTIVITIES = (IDLE, WALK, GROOM, STRETCH, CALL, SLEEP, EAT, PLAY, PURR, BRUSH)

# Moods, derived from the needs
HAPPY = "happy"
CONTENT = "content"
HUNGRY = "hungry"
TIRED = "tired"
DIRTY = "dirty"
SULKING = "sulky"
ASLEEP = "asleep"

# Needs, for attention calls
NEED_FOOD = "food"
NEED_SLEEP = "sleep"
NEED_CLEAN = "clean"
NEED_LOVE = "love"

# Feeding
MEAL = "meal"
TREAT = "treat"

# Events returned by tick() and catch_up()
EV_FELL_ASLEEP = "fell_asleep"
EV_WOKE_UP = "woke_up"
EV_MESS = "mess"
EV_REUNION = "reunion"

STEP_S = 60                    # live simulation step
CATCH_UP_STEP_S = 300          # coarser step after the device was off
MAX_CATCH_UP_S = 3 * 86400     # beyond this, needs have long reached their floor
REUNION_S = 6 * 3600           # after such an absence the pet is glad to see you again
REUNION_HAPPINESS = 15.0
STAY_AWAKE_S = 1800            # after being woken up, no bedtime for a while
CARESS_FATIGUE_S = 60          # repeated caresses help less, for about a minute each
TREAT_FATIGUE_S = 1800         # treats help less when given in a row

# Durations of the activities, in seconds: (min, max)
DURATIONS = {
    IDLE: (8, 20),
    WALK: (4, 8),
    GROOM: (4, 7),
    STRETCH: (3, 3),
    CALL: (5, 5),
    EAT: (4, 4),
    PLAY: (3, 3),
    PURR: (3, 3),
    BRUSH: (3, 3),
}


def _clamp(v):
    return 0.0 if v < 0 else (MAX if v > MAX else v)


def _rand(rand, a, b):
    return (rand or random.randint)(a, b)


class Pet:
    """Everything that is saved about the pet."""

    def __init__(self, character, profile):
        self.character = character      # id of the character (see prestopet.pets)
        self.profile = profile          # rules of its species, with its personality
        self.satiety = 80.0
        self.happiness = 80.0
        self.energy = 90.0
        self.hygiene = 100.0
        self.messes = 0
        self.mess_timers = []           # seconds until each upcoming mess
        self.age = 0.0                  # seconds of game time since adoption
        self.activity = IDLE
        self.activity_left = 5.0        # seconds before choosing another activity
        self.stay_awake = 0.0           # seconds of protection against bedtime
        self.napping = False            # asleep because nobody came by: a touch wakes it
        self.caress_fatigue = 0.0
        self.treat_fatigue = 0.0
        self.counts = {"meals": 0, "treats": 0, "caresses": 0, "plays": 0, "cleans": 0}

    @property
    def asleep(self):
        return self.activity == SLEEP

    @property
    def days(self):
        """Age shown to the player: day 1 is the day of adoption."""
        return int(self.age // 86400) + 1

    def to_dict(self):
        return {
            "v": SAVE_VERSION,
            "character": self.character,
            "satiety": round(self.satiety, 2),
            "happiness": round(self.happiness, 2),
            "energy": round(self.energy, 2),
            "hygiene": round(self.hygiene, 2),
            "messes": self.messes,
            "mess_timers": [int(t) for t in self.mess_timers],
            "age": int(self.age),
            "activity": self.activity,
            "activity_left": int(self.activity_left),
            "stay_awake": int(self.stay_awake),
            "napping": self.napping,
            "caress_fatigue": round(self.caress_fatigue, 2),
            "treat_fatigue": round(self.treat_fatigue, 2),
            "counts": dict(self.counts),
        }

    @classmethod
    def from_dict(cls, data, profile):
        """Rebuilds a pet from saved data. Missing or invalid values fall back to defaults,
        so an old or damaged save still loads."""
        pet = cls(data["character"], profile)
        for name in ("satiety", "happiness", "energy", "hygiene"):
            setattr(pet, name, _clamp(_number(data.get(name), getattr(pet, name))))
        pet.messes = int(max(0, min(profile["max_messes"], _number(data.get("messes"), 0))))
        timers = data.get("mess_timers")
        if isinstance(timers, list):
            pet.mess_timers = [max(0.0, _number(t, 0)) for t in timers][:profile["max_messes"]]
        pet.age = max(0.0, _number(data.get("age"), 0))
        activity = data.get("activity")
        pet.activity = activity if activity in ACTIVITIES else IDLE
        pet.activity_left = max(0.0, _number(data.get("activity_left"), 5))
        pet.stay_awake = max(0.0, _number(data.get("stay_awake"), 0))
        pet.napping = data.get("napping") is True and pet.asleep
        pet.caress_fatigue = max(0.0, _number(data.get("caress_fatigue"), 0))
        pet.treat_fatigue = max(0.0, _number(data.get("treat_fatigue"), 0))
        counts = data.get("counts")
        if isinstance(counts, dict):
            for key in pet.counts:
                pet.counts[key] = int(max(0, _number(counts.get(key), 0)))
        return pet


def _number(value, default):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    if value != value:  # NaN
        return default
    return float(value)


# --- Derived state ---------------------------------------------------------------------------


def is_night(profile, hour):
    """True during the night hours; always False when the time of day is unknown."""
    if hour is None:
        return False
    start = profile["night_start"]
    end = profile["night_end"]
    if start > end:
        return hour >= start or hour < end
    return start <= hour < end


def mood(pet):
    if pet.asleep:
        return ASLEEP
    if pet.happiness < SULKY:
        return SULKING
    if pet.satiety < LOW:
        return HUNGRY
    if pet.energy < LOW:
        return TIRED
    if pet.hygiene < LOW or pet.messes >= 2:
        return DIRTY
    if pet.happiness >= 70 and pet.satiety >= 50 and pet.energy >= 40 and pet.hygiene >= 50:
        return HAPPY
    return CONTENT


def urgent_need(pet):
    """The most pressing need, or None when everything is fine."""
    candidates = []
    if pet.satiety < LOW:
        candidates.append((pet.satiety, NEED_FOOD))
    if not pet.asleep and pet.energy < LOW:
        candidates.append((pet.energy, NEED_SLEEP))
    if pet.hygiene < LOW:
        candidates.append((pet.hygiene, NEED_CLEAN))
    elif pet.messes:
        candidates.append((LOW - pet.messes, NEED_CLEAN))
    if pet.happiness < LOW:
        candidates.append((pet.happiness, NEED_LOVE))
    if not candidates:
        return None
    candidates.sort()
    return candidates[0][1]


# --- Time ------------------------------------------------------------------------------------


def tick(pet, seconds, hour=None, rand=None):
    """Advances the simulation while the game runs. Returns the list of events."""
    events = []
    while seconds > 0:
        step = STEP_S if seconds > STEP_S else seconds
        _step(pet, step, hour, rand, events)
        seconds -= step
    return events


def catch_up(pet, seconds, hour_at=None, rand=None):
    """Advances the simulation over a period while the game was not running: the device was
    off, or the time was only discovered later. `hour_at(offset)` gives the local hour
    `offset` seconds after the beginning of the period, or None when unknown.

    Very long absences are not simulated in full: the pet ages normally, but only the last
    MAX_CATCH_UP_S are played, which is enough for every need to settle."""
    events = []
    if seconds <= 0:
        return events
    offset = 0
    if seconds > MAX_CATCH_UP_S:
        offset = seconds - MAX_CATCH_UP_S
        pet.age += offset
    while offset < seconds:
        step = seconds - offset
        if step > CATCH_UP_STEP_S:
            step = CATCH_UP_STEP_S
        hour = hour_at(offset) if hour_at else None
        _step(pet, step, hour, rand, events)
        offset += step
    if seconds >= REUNION_S:
        pet.happiness = _clamp(pet.happiness + REUNION_HAPPINESS)
        if not pet.asleep:
            pet.activity = CALL
            pet.activity_left = DURATIONS[CALL][0]
        events.append(EV_REUNION)
    return events


def _step(pet, dt, hour, rand, events):
    p = pet.profile
    h = dt / 3600.0
    asleep = pet.asleep
    pet.age += dt

    pet.satiety = _clamp(pet.satiety + p["satiety_asleep" if asleep else "satiety_awake"] * h)
    pet.energy = _clamp(pet.energy + p["energy_asleep" if asleep else "energy_awake"] * h)
    pet.hygiene = _clamp(pet.hygiene + (p["hygiene"] + p["hygiene_per_mess"] * pet.messes) * h)
    mood_rate = p["happiness_asleep" if asleep else "happiness_awake"]
    if pet.satiety < LOW:
        mood_rate += p["sad_when_hungry"]
    if pet.hygiene < LOW or pet.messes:
        mood_rate += p["sad_when_dirty"]
    pet.happiness = _clamp(pet.happiness + mood_rate * h)

    pet.caress_fatigue = max(0.0, pet.caress_fatigue - dt / CARESS_FATIGUE_S)
    pet.treat_fatigue = max(0.0, pet.treat_fatigue - dt / TREAT_FATIGUE_S)
    pet.stay_awake = max(0.0, pet.stay_awake - dt)

    if pet.mess_timers:
        left = []
        for t in pet.mess_timers:
            t -= dt
            if t > 0:
                left.append(t)
            elif pet.messes < p["max_messes"]:
                pet.messes += 1
                events.append(EV_MESS)
        pet.mess_timers = left

    night = is_night(p, hour)
    if asleep and pet.napping:
        if night:
            pet.napping = False     # the nap becomes the night's sleep, ended by the morning
    elif asleep:
        if not night and (pet.energy >= MAX or (hour is not None and pet.energy >= p["morning_energy"])):
            _wake(pet)
            events.append(EV_WOKE_UP)
            return
    elif pet.energy <= p["exhausted"] or (night and pet.stay_awake <= 0 and pet.energy < p["bedtime_energy"]):
        _fall_asleep(pet)
        events.append(EV_FELL_ASLEEP)
        return

    if not pet.asleep:
        pet.activity_left -= dt
        if pet.activity_left <= 0:
            choose_activity(pet, rand)


def _fall_asleep(pet):
    pet.activity = SLEEP
    pet.activity_left = 0.0


def _wake(pet):
    pet.napping = False
    pet.activity = STRETCH
    pet.activity_left = DURATIONS[STRETCH][0]


def _start(pet, activity, rand=None):
    low, high = DURATIONS[activity]
    pet.activity = activity
    pet.activity_left = float(low if low == high else _rand(rand, low, high))


def choose_activity(pet, rand=None):
    """Autonomous behaviour: what the pet does next when nobody plays with it."""
    need = urgent_need(pet)
    if need is not None and _rand(rand, 0, 99) < 45:
        _start(pet, CALL, rand)
        return
    m = mood(pet)
    if m == HAPPY:
        weights = ((IDLE, 4), (WALK, 4), (GROOM, 2), (STRETCH, 1))
    elif m in (SULKING, TIRED):
        weights = ((IDLE, 7), (WALK, 1), (GROOM, 1), (STRETCH, 2))
    else:
        weights = ((IDLE, 5), (WALK, 3), (GROOM, 2), (STRETCH, 1))
    total = 0
    for _, w in weights:
        total += w
    pick = _rand(rand, 1, total)
    for activity, w in weights:
        pick -= w
        if pick <= 0:
            _start(pet, activity, rand)
            return


# --- Player actions --------------------------------------------------------------------------
# Each action returns (accepted, reaction). The reaction names what the user interface should
# show; a refusal is never a punishment, just the pet expressing itself.

R_ASLEEP = "asleep"            # sleeping: the action waits
R_EAT = "eat"
R_TREAT = "treat"
R_FULL = "full"
R_PURR = "purr"
R_PURR_ASLEEP = "purr_asleep"
R_PLAY = "play"
R_PLAY_SULKY = "play_sulky"    # plays, but half-heartedly
R_TOO_TIRED = "too_tired"
R_CLEAN = "clean"
R_ALREADY_CLEAN = "already_clean"
R_GO_TO_BED = "go_to_bed"
R_NOT_SLEEPY = "not_sleepy"
R_WAKE = "wake"
R_TOO_SLEEPY = "too_sleepy"


def feed(pet, kind, rand=None):
    p = pet.profile
    if pet.asleep:
        return False, R_ASLEEP
    if kind == TREAT:
        if pet.satiety >= MAX - 1:
            return False, R_FULL
        gain = p["treat_happiness"] / (1.0 + pet.treat_fatigue)
        pet.treat_fatigue += 1.0
        pet.satiety = _clamp(pet.satiety + p["treat_satiety"])
        pet.happiness = _clamp(pet.happiness + gain)
        pet.counts["treats"] += 1
        _start(pet, EAT)
        return True, R_TREAT
    if pet.satiety >= p["full"]:
        return False, R_FULL
    pet.satiety = _clamp(pet.satiety + p["meal"])
    pet.happiness = _clamp(pet.happiness + p["meal_happiness"])
    pet.counts["meals"] += 1
    if len(pet.mess_timers) + pet.messes < p["max_messes"]:
        pet.mess_timers.append(float(_rand(rand, int(p["mess_delay_min"]), int(p["mess_delay_max"]))))
    _start(pet, EAT)
    return True, R_EAT


def caress(pet):
    gain = pet.profile["caress"] / (1.0 + 0.5 * pet.caress_fatigue)
    pet.caress_fatigue += 1.0
    pet.counts["caresses"] += 1
    if pet.asleep:
        pet.happiness = _clamp(pet.happiness + gain * 0.5)
        return True, R_PURR_ASLEEP
    pet.happiness = _clamp(pet.happiness + gain)
    _start(pet, PURR)
    return True, R_PURR


def can_play(pet):
    return not pet.asleep and pet.energy >= pet.profile["play_min_energy"]


def play(pet):
    """One throw of the ball. A play session is a few throws in a row."""
    p = pet.profile
    if pet.asleep:
        return False, R_ASLEEP
    if pet.energy < p["play_min_energy"]:
        return False, R_TOO_TIRED
    sulky = pet.happiness < SULKY
    gain = p["play_happiness"] * (0.5 if sulky else 1.0)
    pet.happiness = _clamp(pet.happiness + gain)
    pet.energy = _clamp(pet.energy - p["play_energy"])
    pet.satiety = _clamp(pet.satiety - p["play_satiety"])
    pet.hygiene = _clamp(pet.hygiene - p["play_hygiene"])
    pet.counts["plays"] += 1
    _start(pet, PLAY)
    return True, R_PLAY_SULKY if sulky else R_PLAY


def clean(pet):
    if pet.messes == 0 and pet.hygiene >= 90:
        return False, R_ALREADY_CLEAN
    pet.messes = 0
    pet.hygiene = _clamp(pet.hygiene + pet.profile["clean"])
    pet.counts["cleans"] += 1
    if not pet.asleep:
        pet.happiness = _clamp(pet.happiness + 2)
        _start(pet, BRUSH)
    return True, R_CLEAN


def nap(pet):
    """Curls up after a while without anyone around. Only a touch ends the nap (or the
    night, which turns it into a normal sleep). Returns True when the pet lay down."""
    if pet.asleep:
        return False
    _fall_asleep(pet)
    pet.napping = True
    return True


def end_nap(pet, hour=None):
    """Someone is back: the napping pet wakes up and stretches. Returns True if it woke."""
    if not pet.napping:
        return False
    pet.napping = False
    if is_night(pet.profile, hour):
        return False
    _wake(pet)
    return True


def toggle_sleep(pet, hour=None):
    """The bed button: puts the pet to bed, or wakes it up gently."""
    p = pet.profile
    if pet.asleep:
        if pet.energy < p["wake_min_energy"]:
            return False, R_TOO_SLEEPY
        _wake(pet)
        pet.stay_awake = STAY_AWAKE_S
        return True, R_WAKE
    if pet.energy < p["sleepy_energy"] or is_night(p, hour):
        _fall_asleep(pet)
        return True, R_GO_TO_BED
    return False, R_NOT_SLEEPY
