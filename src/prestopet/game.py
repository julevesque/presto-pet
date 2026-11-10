# The running game: the pet, game time and saving, glued together.
#
# No display and no touch here, so the whole life cycle (adoption, actions, restart after a
# power cut, late network time) is tested on a computer.

from prestopet import engine, pets
from prestopet.clock import GameClock, local_hour
from prestopet.storage import SavePolicy

TICK_MS = 1000


class Game:
    def __init__(self, storage, ticks, diff, wall=None, utc_offset_minutes=0, eu_dst=False,
                 rand=None, clock_class=GameClock, trusted=None):
        self.storage = storage
        self.ticks = ticks
        self.diff = diff
        self.rand = rand
        self.utc_offset_minutes = utc_offset_minutes
        self.eu_dst = eu_dst
        self._clock_args = {"ticks": ticks, "diff": diff}
        if wall is not None:
            self._clock_args["wall"] = wall
        if trusted is not None:
            self._clock_args["trusted"] = trusted
        self._clock_class = clock_class
        self.pet = None
        self.clock = None
        self.events = []          # events not yet shown by the user interface
        now = ticks()
        self.last_tick = now
        self.policy = SavePolicy(now, diff)

    # --- Life cycle -------------------------------------------------------------------------

    def start(self):
        """Loads the saved game, if any, and simulates the time spent switched off."""
        data = self.storage.load()
        saved_at = None
        anchored = True
        if data is not None:
            try:
                cid = pets.canonical(data["pet"]["character"])
                self.pet = engine.Pet.from_dict(data["pet"], pets.profile(cid))
                self.pet.character = cid
                saved_at = data.get("saved_at")
                if not isinstance(saved_at, (int, float)):
                    saved_at = None
                anchored = data.get("clock_anchored", True) is not False
            except (KeyError, TypeError, ValueError) as e:
                print("Unreadable save, ignored:", repr(e))
                self.pet = None
        self.clock = self._clock_class(saved_at=saved_at, anchored=anchored, **self._clock_args)
        if self.pet is not None and self.clock.boot_gap > 0:
            self._catch_up(self.clock.boot_gap, saved_at)
        self.last_tick = self.ticks()
        return self.pet is not None

    def new_game(self, cid):
        if self.clock is None:
            self.clock = self._clock_class(saved_at=None, **self._clock_args)
        self.pet = engine.Pet(cid, pets.profile(cid))
        self.events = []
        self.policy.mark(self.ticks(), urgent=True)
        self.save_if_due()

    def erase(self):
        """Deletes the game. Only after an explicit confirmation by the player."""
        self.storage.erase()
        self.pet = None
        self.events = []

    # --- Time ---------------------------------------------------------------------------------

    def hour(self, epoch=None):
        """Local hour, or None while the real time is unknown."""
        if self.clock is None or not self.clock.trusted:
            return None
        if epoch is None:
            epoch = self.clock.now()
        return local_hour(epoch, self.utc_offset_minutes, self.eu_dst)

    def _catch_up(self, seconds, start):
        if start is None or not self.clock.trusted:
            hour_at = None
        else:
            def hour_at(offset):
                return local_hour(start + offset, self.utc_offset_minutes, self.eu_dst)
        events = engine.catch_up(self.pet, seconds, hour_at, self.rand)
        print("Caught up %d s offline" % seconds)
        self.events.extend(events)
        self.policy.mark(self.ticks(), urgent=True)

    def update(self):
        """To call from the main loop. Advances the simulation about once a second and saves
        when needed. Returns True when the pet changed state (asleep, awake, new mess)."""
        if self.clock is None:
            return False
        was_trusted = self.clock.trusted
        gap = self.clock.poll()
        changed = False
        if self.clock.trusted and not was_trusted and self.pet is not None:
            # The real time just became known: save it soon, it anchors the next restarts.
            self.policy.mark(self.ticks(), urgent=True)
            if gap:
                # The offline time ended at the last boot.
                self._catch_up(gap, self.clock.now() - gap)
                changed = True
        now = self.ticks()
        elapsed = self.diff(now, self.last_tick)
        if elapsed >= TICK_MS:
            self.last_tick = now
            if self.pet is not None:
                events = engine.tick(self.pet, elapsed / 1000.0, self.hour(), self.rand)
                if events:
                    self.events.extend(events)
                    changed = True
                    urgent = engine.EV_FELL_ASLEEP in events or engine.EV_WOKE_UP in events
                    self.policy.mark(now, urgent=urgent)
        self.save_if_due()
        return changed

    # --- Saving -------------------------------------------------------------------------------

    def save_if_due(self):
        now = self.ticks()
        if self.pet is None or not self.policy.due(now):
            return False
        ok = self.storage.save(self.snapshot())
        # Even after a failed write, wait for the next period rather than retrying each loop.
        self.policy.done(now)
        return ok

    def save_now(self):
        if self.pet is not None:
            self.policy.mark(self.ticks(), urgent=True)
            return self.save_if_due()
        return False

    def snapshot(self):
        return {
            "v": engine.SAVE_VERSION,
            "saved_at": int(self.clock.now()),
            "clock_anchored": self.clock.anchored,
            "pet": self.pet.to_dict(),
        }

    # --- Player actions -----------------------------------------------------------------------

    def _done(self, result, urgent=False):
        self.policy.mark(self.ticks(), urgent=urgent)
        return result

    def feed(self, kind):
        return self._done(engine.feed(self.pet, kind, self.rand))

    def caress(self):
        return self._done(engine.caress(self.pet))

    def play(self):
        return self._done(engine.play(self.pet))

    def clean(self):
        return self._done(engine.clean(self.pet))

    def toggle_sleep(self):
        return self._done(engine.toggle_sleep(self.pet, self.hour()), urgent=True)

    def nap(self):
        return self._done(engine.nap(self.pet), urgent=True)

    def end_nap(self):
        return self._done(engine.end_nap(self.pet, self.hour()), urgent=True)

    def take_events(self):
        events, self.events = self.events, []
        return events
