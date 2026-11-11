# What the pet looks like right now: chooses the frame and the position of the sprite from
# the activity of the engine, plus a few touches of life (blinks, tail flicks, hops, a glance
# at the finger or at a bird), and the little scenes the screen asks for (chasing a toy,
# going to bed).
#
# Nothing here changes the simulation; the views only read the pet.

import random

from prestopet import art, engine, pets
from prestopet.sprites import Composite, Frames, flatten, shifted_patch

try:
    from time import ticks_add, ticks_diff
except ImportError:  # CPython, for the previews and tests
    def ticks_add(a, b):
        return a + b

    def ticks_diff(a, b):
        return a - b

SCALE = 4
# Walking in profile: a four-frame walk cycle, a small bob of the body on each step.
WALK_LEGS = ("w0", "w1", "w2", "w3")
WALK_BOB = (0, -3, 0, -3)           # screen pixels
WALK_STEP_MS = 110
WALK_DX = 8
# Hopping along (sautiller): small leaps, legs gathered on the floor, stretched in the air.
HOP = (0, -6, -11, -14, -14, -11, -6, 0)   # height of a hop, in screen pixels, frame by frame
HOP_STEP_MS = 55
HOP_DX = 5                                  # screen pixels per frame while hopping
HOP_CHANCE = 35                             # % of the walks done hopping
# Chasing the ball: a gallop of long bounds, then a pounce that lands on the ball.
RUN = (0, -7, -13, -17, -17, -13, -7, 0)
RUN_STEP_MS = 45
RUN_DX = 11
POUNCE = (0, -12, -22, -28, -31, -31, -28, -22, -12, 0)
POUNCE_STEP_MS = 50
POUNCE_DIST = 120                           # starts the pounce this close to the ball
PAW_DX = 56                                 # front paws, from the middle of the sprite
AIR_LEGS = ("gather", "stretch", "stretch", "stretch", "stretch", "stretch", "stretch", "gather")
CROUCH_MS = 650                             # crouched, wiggling, before a pounce
WIGGLE_MS = 110
TURN_MS = 170                               # glance aside before turning to profile and back
SETTLE_MS = 350                             # standing in profile after a walk
CATCH_MS = 900                              # holding the ball after a pounce
GAZE_PX = 40                                # looks aside at something further than this
CHATTER_MS = 110                            # the jaw of a cat watching a bird
# Going to bed: onto the cushion, two turns on the spot, kneading, then curled up
BED_LIFT = 44                               # paws on the cushion, above the rug
BED_HOP = (0, -10, -18, -22, -22, -18, -12, -6)
BED_TURN_MS = 520
BED_KNEAD_MS = 2400
KNEAD_MS = 260
SHAKE = (-4, 4, -4, 4, -2, 2, 0)            # a "no" of the head, frame by frame
SHAKE_STEP_MS = 90
MIN_X = 100
MAX_X = 380


def _later(now, low, high):
    return ticks_add(now, random.randint(low, high))


class AwakeView:
    """The pet awake: a pose and the value of each part, drawn from generated tables."""

    def __init__(self, canvas, cid, floor_y, x=240):
        c = pets.character(cid)
        self.comp = Frames(pets.coat(cid), canvas.pens(c["palette"]))
        self.pose = "sit"
        self.floor_y = floor_y
        self.x = x
        self.dy = 0
        self.dx = 0                    # head shake
        self.target = None             # x to reach, walking, hopping or running
        self.gait = None               # "walk", "hop" or "run"
        self.face = 0                  # 0 facing us, 1 profile to the right, -1 to the left
        self.turn = None               # (direction looked at, until): glancing before a turn
        self.settle_until = 0          # profile kept until then, once arrived
        self.legs = "stand"
        self.step = 0                  # frame of the gait
        self.pounce = None             # [toy x, frame, dx per frame] while pouncing
        self.arc = POUNCE              # heights of the pounce
        self.crouch = None             # end of the crouch before the pounce
        self.x0 = x                    # where the pounce started
        self.lift = 0                  # raised above the floor (on the cushion)
        self.side_act = None           # "lick", "bow" or "knead": an activity done in profile
        self.bed = None                # [phase, due, count] while going to bed
        self.gaze = None               # x the pet looks at, set by the screen
        self.chatter = False           # watching a bird: the jaw chatters
        self.next_step = 0
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
        return (int(self.x + self.dx - w // 2), int(self.floor_y - h + self.dy - self.lift), w, h)

    def draw(self, canvas, clip):
        r = self.rect
        self.comp.draw(canvas.d, r[0], r[1], SCALE, clip)

    def react(self, now, variants, ms, shake=False):
        """Shows an expression for a while, and shakes the head for a refusal."""
        self.forced = (variants, ticks_add(now, ms))
        if shake:
            self.shake = (0, now)

    def walk_to(self, x, run=False, face=0, gait=None):
        """Goes to x in profile: walking or hopping, or running for the ball."""
        self.target = max(MIN_X, min(MAX_X, int(x)))
        if gait is None:
            gait = "run" if run else ("hop" if random.randint(1, 100) <= HOP_CHANCE else "walk")
        self.gait = gait
        if not face:
            face = 1 if self.target >= self.x else -1
        self.face_to(face)
        self.step = 0
        self.pounce = None
        self.crouch = None
        self.side_act = None

    def face_to(self, face):
        if face != self.face:
            self.turn = (face, None)     # the glance starts at the next update
        self.face = face

    def chase(self, toy_x, height=0, run=True):
        """Runs to a toy and pounces on it, landing with the front paws on it; `height`, in
        screen pixels, makes the pounce a leap towards a toy in the air."""
        face = 1 if toy_x >= self.x else -1
        self.walk_to(toy_x - face * PAW_DX, run=run, face=face, gait=None if run else "walk")
        if (self.target - self.x) * face < 0:
            self.target = int(self.x)    # already close: pounces from here, without backing up
        self.pounce = [toy_x, None, 0]
        top = -POUNCE[len(POUNCE) // 2]
        self.arc = POUNCE if height <= top else tuple(v * height // top for v in POUNCE)

    @property
    def busy(self):
        """Moving, about to pounce or going to bed."""
        return self.target is not None or self.bed is not None

    def go_to_bed(self, x):
        """Walks to the cushion at x, hops on it, turns round twice and kneads it; the screen
        then shows the pet curled up (see bed_done)."""
        self.walk_to(x, gait="walk")
        self.bed = ["walk", 0, 0]

    @property
    def bed_done(self):
        return self.bed is not None and self.bed[0] == "done"

    def leave_bed(self):
        self.bed = None
        self.lift = 0
        self.dy = 0
        self.side_act = None
        self.settle_until = 0

    def update(self, now, pet):
        """Returns True when the image or its position changed."""
        if pet.activity != self.activity:
            self.activity = pet.activity
            self.started = now
            if self.side_act in ("lick", "bow"):
                self.side_act = None
                self.settle_until = now
            free = self.play_target is None and self.bed is None and self.target is None
            if pet.activity == engine.WALK and self.play_target is None and self.bed is None:
                self.walk_to(random.randint(MIN_X, MAX_X))
            elif free and (pet.activity == engine.STRETCH or
                           (pet.activity == engine.GROOM and random.randint(0, 1))):
                # Stretching, or licking a paw, in profile
                self.side_act = "bow" if pet.activity == engine.STRETCH else "lick"
                self.face_to(random.choice((-1, 1)))
                self.settle_until = ticks_add(now, 600000)
        before = (self.x, self.dy, self.dx, self.lift)
        if self.bed is not None and self.target is None:
            self._bedtime(now)

        if self.turn is not None and self.turn[1] is None:
            self.turn = (self.turn[0], ticks_add(now, TURN_MS))
            self.next_step = self.turn[1]
        if self.turn is not None and ticks_diff(now, self.turn[1]) >= 0:
            self.turn = None
        if self.target is not None:
            if ticks_diff(now, self.next_step) >= 0:
                self._move(now)
        elif self.face and self.bed is None and ticks_diff(now, self.settle_until) >= 0:
            # Back to facing us, with a glance from the side it was looking at
            self.turn = (self.face, ticks_add(now, TURN_MS))
            self.face = 0
            self.legs = "stand"

        # Head shake
        if self.shake is not None and ticks_diff(now, self.shake[1]) >= 0:
            frame = self.shake[0]
            self.dx = SHAKE[frame]
            self.shake = (frame + 1, ticks_add(now, SHAKE_STEP_MS)) if frame + 1 < len(SHAKE) else None

        pose, variants = self.frame(now, pet)
        self.pose = pose
        moved = before != (self.x, self.dy, self.dx, self.lift)
        return self.comp.set_frame(pose, variants) or moved

    def _move(self, now):
        """One frame of the gait towards the target."""
        left = self.target - self.x
        if self.pounce is not None and self.pounce[1] is not None:
            self._pounce_step(now)
            return
        if self.crouch is not None:
            self.crouch = None           # done wiggling: leap
            self._pounce_step(now)
            return
        if self.gait == "walk":
            self.next_step = ticks_add(now, WALK_STEP_MS)
            if self.pounce is not None and abs(left) <= POUNCE_DIST and self.step % 2 == 0:
                self._crouch(now)
                return
            if abs(left) < WALK_DX and self.step % 2 == 0:
                self._arrive(now, SETTLE_MS)
                return
            self.x += max(-WALK_DX, min(WALK_DX, left))
            self.step = (self.step + 1) % len(WALK_LEGS)
            self.legs = WALK_LEGS[self.step]
            self.dy = WALK_BOB[self.step]
            return
        # Hops and bounds: arrives or pounces only with the paws on the floor
        run = self.gait == "run"
        arc, dx = (RUN, RUN_DX) if run else (HOP, HOP_DX)
        self.next_step = ticks_add(now, RUN_STEP_MS if run else HOP_STEP_MS)
        if self.step == 0:
            if self.pounce is not None and abs(left) <= POUNCE_DIST:
                self._crouch(now)
                return
            if abs(left) < dx:
                self._arrive(now, SETTLE_MS)
                return
        if left:
            self.x += max(-dx, min(dx, left))
        self.step = (self.step + 1) % len(arc)
        self.dy = arc[self.step]
        self.legs = AIR_LEGS[self.step]

    def _crouch(self, now):
        """Flattens and wiggles the hindquarters before leaping, like a real cat."""
        self.crouch = ticks_add(now, CROUCH_MS)
        self.next_step = self.crouch
        self.step = 0
        self.dy = 0

    def _pounce_step(self, now):
        p = self.pounce
        if p[1] is None:
            # Leaps from here, whatever the distance left: lands with the paws on the toy,
            # where it is now (a feather may have moved while the pet was crouching)
            target = max(MIN_X, min(MAX_X, int(p[0] - self.face * PAW_DX)))
            self.target = target if (target - self.x) * self.face >= 0 else int(self.x)
            p[1] = 0
            p[2] = (self.target - self.x) / (len(self.arc) - 1)
            self.x0 = self.x
        p[1] += 1
        self.next_step = ticks_add(now, POUNCE_STEP_MS)
        if p[1] >= len(self.arc) - 1:
            self.x = self.target
            self.dy = 0
            self.legs = "catch"
            self.pounce = None
            self._arrive(now, CATCH_MS, legs="catch")
            return
        self.x = int(self.x0 + p[2] * p[1])
        self.dy = self.arc[p[1]]
        self.legs = "stretch" if p[1] <= 2 else "reach"

    def _bedtime(self, now):
        """The steps of going to bed, once on the spot: hop on the cushion, turn, knead."""
        b = self.bed
        phase = b[0]
        if phase == "done" or ticks_diff(now, b[1]) < 0:
            return
        if phase == "walk":
            b[0], b[2] = "hop", 0
            self.face_to(self.face or 1)
        if b[0] == "hop":
            b[2] += 1
            k = b[2]
            if k < len(BED_HOP):
                self.dy = BED_HOP[k]
                self.lift = BED_LIFT * k // len(BED_HOP)
                self.legs = "stretch" if k < len(BED_HOP) - 2 else "gather"
                b[1] = ticks_add(now, HOP_STEP_MS)
                return
            self.dy = 0
            self.lift = BED_LIFT
            self.legs = "stand"
            b[0], b[2] = "turn", 0
        if b[0] == "turn":
            # Two turns on the spot: profile one way, the other way, and back
            if b[2] < 3:
                self.face_to(-self.face)
                self.legs = WALK_LEGS[b[2] % len(WALK_LEGS)]
                b[2] += 1
                b[1] = ticks_add(now, BED_TURN_MS)
                return
            b[0] = "knead"
            self.side_act = "knead"
            self.legs = "stand"
            b[1] = ticks_add(now, BED_KNEAD_MS)
            return
        if b[0] == "knead":
            b[0] = "done"
            self.side_act = None


    def _arrive(self, now, ms, legs="stand"):
        self.target = None
        self.pounce = None
        self.step = 0
        self.dy = 0
        self.legs = legs
        self.settle_until = ticks_add(now, ms)

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

        if self.chatter and self.target is None:
            # A bird at the window: watches it, the jaw chattering
            mouth = "open" if (now // CHATTER_MS) % 2 else "neutral"
            ears = "up"
            if eyes in ("half", "blink"):
                eyes = "open"
        if ticks_diff(self.blink_until, now) > 0 and eyes in ("open", "wide", "half"):
            eyes = "blink"
        side = "_r" if self.face > 0 else "_l"
        if self.turn is not None and pose == "sit":
            eyes = "look_r" if self.turn[0] > 0 else "look_l"
        elif self.face and self.crouch is not None:
            wiggle = "left" if (now // WIGGLE_MS) % 2 else "right"
            return "crouch" + side, (("eyes", "wide"), ("mouth", mouth if mouth == "open" else "neutral"),
                                     ("wiggle", wiggle))
        elif self.face and self.side_act == "bow" and self.turn is None:
            yawn = t < 1800
            return "bow" + side, (("eyes", "blink" if yawn else "open"), ("mouth", "yawn" if yawn else "neutral"),
                                  ("tail", tail if tail == "flick" else "up"))
        elif not self.face and self.gaze is not None and self.turn is None and pose == "sit" \
                and eyes in ("open", "wide", "half"):
            # Follows the finger, a toy or a bird with the eyes
            if self.gaze < self.x - GAZE_PX:
                eyes = "look_l"
            elif self.gaze > self.x + GAZE_PX:
                eyes = "look_r"
        elif self.face and self.turn is None:
            # In profile: the legs follow the gait, the tail streams behind in the air
            pose = "side" + side
            paws = self.legs
            if self.dy < -4 or self.pounce is not None:
                tail = "back"
            elif tail not in ("flick", "up"):
                tail = "up"
            if eyes not in ("open", "blink", "half", "happy"):
                eyes = "open"
            if mouth != "open":
                mouth = "neutral"
            if self.side_act == "lick":
                paws, eyes = "lick", "blink"
                mouth = "lick" if alternate else "neutral"
            elif self.side_act == "knead":
                paws = "knead_a" if (t // KNEAD_MS) % 2 else "knead_b"
                eyes, mouth = "happy", "neutral"
        if self.forced is not None:
            variants, until = self.forced
            if ticks_diff(until, now) > 0:
                eyes = variants.get("eyes", eyes)
                mouth = variants.get("mouth", mouth)
                ears = variants.get("ears", ears)
                tail = variants.get("tail", tail)
            else:
                self.forced = None
        if pose.startswith("side"):
            return pose, (("eyes", eyes), ("mouth", mouth), ("tail", tail), ("legs", paws))
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
