# What the pet looks like right now: chooses the frame and the position of the sprite from
# the activity of the engine, plus a few touches of life (blinks, tail flicks, hops).
#
# Nothing here changes the simulation; the views only read the pet.

import random

from prestopet import art, engine, pets
from prestopet.sprites import Composite, flatten, shifted_patch

try:
    from time import ticks_add, ticks_diff
except ImportError:  # CPython, for the previews and tests
    def ticks_add(a, b):
        return a + b

    def ticks_diff(a, b):
        return a - b

SCALE = 4
HOP = (0, -6, -11, -14, -14, -11, -6, 0)   # height of a hop, in screen pixels, frame by frame
HOP_STEP_MS = 55
HOP_DX = 5                                  # screen pixels per frame while hopping
RUN_DX = 9                                  # chasing the ball
SHAKE = (-4, 4, -4, 4, -2, 2, 0)            # a "no" of the head, frame by frame
SHAKE_STEP_MS = 90
MIN_X = 100
MAX_X = 380


def _later(now, low, high):
    return ticks_add(now, random.randint(low, high))


class AwakeView:
    """The pet awake: one composite image whose patches change."""

    def __init__(self, canvas, cid, floor_y, x=240):
        c = pets.character(cid)
        self.coat = pets.coat(cid)
        self.comp = Composite(self.coat.POSES["sit"], canvas.pens(c["palette"]))
        self.pose = "sit"
        self.floor_y = floor_y
        self.x = x
        self.dy = 0
        self.dx = 0                    # head shake
        self.target = None             # x to reach by hopping
        self.speed = HOP_DX
        self.hop = 0                   # frame of the current hop, 0 when on the floor
        self.next_hop = 0
        self.activity = None
        self.started = 0
        self.blink_until = 0
        self.next_blink = 0
        self.flick_until = 0
        self.next_flick = 0
        self.lick = 0
        self.shake = None              # (frame, due) of a head shake
        self.forced = None             # (variants, until): expression forced by a reaction
        self.play_target = None        # set by the play session

    @property
    def rect(self):
        s = SCALE
        w = self.comp.w * s
        h = self.comp.h * s
        return (int(self.x + self.dx - w // 2), int(self.floor_y - h + self.dy), w, h)

    def draw(self, canvas, clip):
        r = self.rect
        self.comp.draw(canvas.d, r[0], r[1], SCALE, clip)

    def react(self, now, variants, ms, shake=False):
        """Shows an expression for a while, and shakes the head for a refusal."""
        self.forced = (variants, ticks_add(now, ms))
        if shake:
            self.shake = (0, now)

    def walk_to(self, x, run=False):
        self.target = max(MIN_X, min(MAX_X, int(x)))
        self.speed = RUN_DX if run else HOP_DX

    def update(self, now, pet):
        """Returns True when the image or its position changed."""
        if pet.activity != self.activity:
            self.activity = pet.activity
            self.started = now
            if pet.activity == engine.WALK and self.play_target is None:
                self.walk_to(random.randint(MIN_X, MAX_X))
        before = (self.x, self.dy, self.dx)

        # Hopping towards the target
        if self.target is not None and ticks_diff(now, self.next_hop) >= 0:
            self.next_hop = ticks_add(now, HOP_STEP_MS)
            step = self.target - self.x
            if self.hop == 0 and abs(step) < self.speed:
                self.target = None
            else:
                if step:
                    self.x += max(-self.speed, min(self.speed, step))
                self.hop = (self.hop + 1) % len(HOP)
                self.dy = HOP[self.hop]
        elif self.target is None and self.hop:
            self.hop = 0
            self.dy = 0

        # Head shake
        if self.shake is not None and ticks_diff(now, self.shake[1]) >= 0:
            frame = self.shake[0]
            self.dx = SHAKE[frame]
            self.shake = (frame + 1, ticks_add(now, SHAKE_STEP_MS)) if frame + 1 < len(SHAKE) else None

        pose, variants = self.frame(now, pet)
        changed = before != (self.x, self.dy, self.dx)
        if pose != self.pose:
            self.pose = pose
            self.comp.set_base(self.coat.POSES[pose])
            changed = True
        patches = []
        for key in variants:
            p = self.coat.PATCHES.get((pose,) + key)
            if p is not None:
                patches.append(p)
        if self.comp.set_patches(tuple(patches)):
            changed = True
        return changed

    def frame(self, now, pet):
        """(pose, ((part, variant), ...)) for this moment."""
        m = engine.mood(pet)
        eyes = "open"
        mouth = "neutral"
        ears = "up"
        tail = "rest"
        paws = "down"
        pose = "sit"
        if m == engine.SULKING:
            eyes, ears = "half", "flat"
        elif m == engine.TIRED:
            eyes = "half"

        # Life: blinks and tail flicks, at random moments
        if ticks_diff(now, self.next_blink) >= 0:
            self.blink_until = ticks_add(now, 140)
            self.next_blink = _later(now, 2000, 6000)
        if ticks_diff(now, self.next_flick) >= 0:
            self.flick_until = ticks_add(now, random.randint(200, 500))
            self.next_flick = _later(now, 3000, 9000)
        if ticks_diff(self.flick_until, now) > 0:
            tail = "flick"

        a = pet.activity
        t = ticks_diff(now, self.started)
        alternate = (t // 280) % 2
        if self.play_target is not None or a == engine.PLAY:
            eyes, mouth, tail, ears = "wide", "open", "up", "up"
            if self.target is None and a == engine.PLAY:
                paws = "pounce"
        elif self.target is not None or a == engine.WALK:
            tail = "up"
        elif a == engine.GROOM:
            paws, eyes = "groom", "blink"
            mouth = "yum" if alternate else "neutral"
        elif a == engine.STRETCH:
            if t < 1800:
                eyes, mouth = "blink", "yawn"
        elif a == engine.CALL:
            mouth = "open" if (t // 450) % 2 == 0 else "neutral"
            tail = "up"
        elif a == engine.EAT:
            pose, eyes = "eat", "happy"
            mouth = "yum" if alternate else "neutral"
        elif a == engine.PURR:
            eyes, tail = "happy", "up"
        elif a == engine.BRUSH:
            eyes, tail = "happy", "up"

        if ticks_diff(self.blink_until, now) > 0 and eyes in ("open", "wide", "half"):
            eyes = "blink"
        if self.forced is not None:
            variants, until = self.forced
            if ticks_diff(until, now) > 0:
                eyes = variants.get("eyes", eyes)
                mouth = variants.get("mouth", mouth)
                ears = variants.get("ears", ears)
                tail = variants.get("tail", tail)
            else:
                self.forced = None
        return pose, (("eyes", eyes), ("mouth", mouth), ("ears", ears), ("tail", tail), ("paws", paws))


class SleepView:
    """The pet curled up on its cushion: breathing, an ear and the tail that twitch at random."""

    def __init__(self, canvas, cid, floor_y, x=240):
        a = pets.sleep_art(cid)
        self.art = a
        base = flatten(a.W, a.H, a.LAYERS)
        self.comp = Composite(base, canvas.pens(pets.sleep_palette(cid)))
        self.x = x
        self.floor_y = floor_y
        layer = a.CAT_LAYER

        def frames(zone, shifts):
            return [None if s is None else shifted_patch(a.W, a.H, a.LAYERS, layer, zone, s) for s in shifts]

        zone, shifts, timing = a.BREATH
        self.breath = [frames(zone, shifts), timing, 0, 0]       # frames, timing, step, due
        self.twitches = []
        for zone, shifts, pause, flicks, flick in a.TWITCHES:
            # frames, settings, shown, flicks left, due
            self.twitches.append([frames(zone, shifts), (pause, flicks, flick), 0, 0, 0])
        self.started = False

    @property
    def rect(self):
        w = self.comp.w * SCALE
        h = self.comp.h * SCALE
        return (int(self.x - w // 2), int(self.floor_y - h), w, h)

    def zzz_rect(self):
        r = self.rect
        zx, zy, zw, zh = self.art.ZZZ
        return (r[0] + zx * SCALE, r[1] + zy * SCALE, zw * SCALE, zh * SCALE)

    def draw(self, canvas, clip):
        r = self.rect
        self.comp.draw(canvas.d, r[0], r[1], SCALE, clip)

    def update(self, now, pet=None):
        if not self.started:
            self.started = True
            self.breath[3] = ticks_add(now, self.breath[1][0][1])
            for t in self.twitches:
                pause = t[1][0]
                t[4] = _later(now, pause[0], pause[1])
            return False
        b = self.breath
        changed = False
        if ticks_diff(now, b[3]) >= 0:
            timing = b[1]
            b[2] = (b[2] + 1) % len(timing)
            frame, ms = timing[b[2]]
            b[3] = ticks_add(b[3], ms)  # from the due time: the rhythm never drifts
            changed = True
        for t in self.twitches:
            if ticks_diff(now, t[4]) >= 0:
                self._twitch(t, now)
                changed = True
        if changed:
            patches = []
            frame = b[1][b[2]][0]
            if b[0][frame] is not None:
                patches.append(b[0][frame])
            for t in self.twitches:
                if t[2] and t[0][t[2]] is not None:
                    patches.append(t[0][t[2]])
            return self.comp.set_patches(tuple(patches))
        return False

    @staticmethod
    def _twitch(t, now):
        frames, (pause, flicks, flick), shown, left, _ = t
        if shown:
            # End of a flick: back to rest, then the next flick or a long pause.
            t[2] = 0
            low, high = (120, 500) if left else pause
        else:
            if not left:
                left = random.randint(1, flicks)
            t[3] = left - 1
            t[2] = random.randint(1, len(frames) - 1)
            low, high = flick
        t[4] = _later(now, low, high)


class Zzz:
    """The zZZ rising above the sleeping pet, one logical pixel per step, with a wobble."""

    STEP_MS = 300

    def __init__(self, rect):
        self.rect = rect
        self.w = rect[2] // SCALE
        self.h = rect[3] // SCALE
        self.letters = []          # [age, glyph, phase]
        self.burst = 0
        self.wait = random.randint(0, 7)
        self.due = 0

    def update(self, now, pet=None):
        if ticks_diff(now, self.due) < 0:
            return False
        self.due = ticks_add(now, self.STEP_MS)
        self.letters = [[age + 1, g, ph] for age, g, ph in self.letters if self.h - len(g) - age - 1 >= 0]
        if self.wait > 0:
            self.wait -= 1
        else:
            self.letters.append([0, art.Z_BURST[self.burst], random.randint(0, len(art.Z_WOBBLE) - 1)])
            self.burst = (self.burst + 1) % len(art.Z_BURST)
            self.wait = random.randint(6, 22) if self.burst == 0 else 7
        return True

    def draw(self, canvas, clip):
        x0, y0 = self.rect[0], self.rect[1]
        for age, glyph, phase in self.letters:
            top = self.h - len(glyph) - age
            left = 5 + art.Z_WOBBLE[(age // 3 + phase) % len(art.Z_WOBBLE)] + age // 6
            color = art.ZZZ_DIM if top < 6 else art.ZZZ
            for r, row in enumerate(glyph):
                for c, cell in enumerate(row):
                    if cell != ".":
                        canvas.rect(x0 + (left + c) * SCALE, y0 + (top + r) * SCALE, SCALE, SCALE, color)
