# The screens of the game: title, choice of the pet, the room, statistics, options and new
# game.
#
# A screen draws itself in enter(), reacts to touch() and animates in update(). The App
# switches screens with app.show().

import random

from prestopet import art, engine, font, pets, settings
from prestopet.canvas import CENTER, H, LEFT, RIGHT, W
from prestopet.i18n import LANGUAGE_NAMES
from prestopet.petview import AwakeView, SleepView, Zzz, ticks_add, ticks_diff
from prestopet.scene import (BAR_H, SCENE, SCENE_BOTTOM, ArtItem, Banner, Label,
                             Particles, Popup, Scene, SpeechBubble, draw_room)
from prestopet.touch import DOWN, HOLD, HOLD_MS, TAP

PET_FLOOR = 386            # bottom of the awake pet, on the rug
SLEEP_FLOOR = 398          # bottom of the cushion
BANNER_MS = 2600
TOP = ("feed", "caress", "play")
BOTTOM = ("clean", "sleep", "stats")
PLAY_THROWS = 5
PLAY_TIMEOUT_MS = 25000
NEED_ICONS = {
    engine.NEED_FOOD: "feed",
    engine.NEED_SLEEP: "sleep",
    engine.NEED_CLEAN: "clean",
    engine.NEED_LOVE: "caress",
}
MESS_SLOTS = ((40, 352), (404, 358), (92, 368))
REFUSALS = {
    engine.R_FULL: ({"eyes": "half", "ears": "flat"}, True),
    engine.R_NOT_SLEEPY: ({"eyes": "wide", "mouth": "open"}, True),
    engine.R_TOO_TIRED: ({"eyes": "half", "ears": "flat"}, True),
    engine.R_ALREADY_CLEAN: ({"eyes": "happy"}, False),
    engine.R_PLAY_SULKY: ({"eyes": "half"}, False),
}


def in_rect(x, y, r):
    return r is not None and r[0] <= x < r[0] + r[2] and r[1] <= y < r[1] + r[3]


def draw_tile(c, x, y, w, h, icon, state):
    """A menu button: 'normal', 'pressed' or 'off'."""
    color = {"pressed": art.TILE_PRESSED, "off": art.TILE_OFF}.get(state, art.TILE)
    c.rect(x, y, w, h, art.BAR)
    c.rounded(x + 8, y + 6, w - 16, h - 12, color, 8)
    c.art(art.ICONS[icon], x + (w - 64) // 2, y + (h - 64) // 2, 4, art.PALETTE)


class Screen:
    def __init__(self, app):
        self.app = app
        self.c = app.canvas
        self.t = app.texts
        self.game = app.game

    def enter(self, now):
        pass

    def touch(self, event, x, y, now):
        pass

    def update(self, now):
        pass


class _Idle:
    """A pet that only sits there, for the title and the choice screens."""

    def __init__(self, cid):
        self.pet = engine.Pet(cid, pets.profile(cid))
        self.pet.activity = engine.IDLE
        self.pet.happiness = 90


# --- Title ----------------------------------------------------------------------------------


class TitleScreen(Screen):
    """Shown at boot. With a saved game, goes on by itself to the room."""

    RESUME_MS = 1800

    def enter(self, now):
        self.started = now
        self.blink = 0
        c = self.c
        c.clip((0, 0, W, H))
        draw_room(c, (0, 0, W, H), art.DAY, False)
        c.rect(0, 0, W, BAR_H, art.BAR)
        c.rect(0, SCENE_BOTTOM, W, H - SCENE_BOTTOM, art.BAR)
        c.unclip()
        c.text(self.t.get("title"), W // 2 + 4, 24, 5, art.PALETTE["O"], CENTER)
        c.text(self.t.get("title"), W // 2, 20, 5, art.ACCENT, CENTER)
        self.views = []
        for i, cid in enumerate(pets.CHARACTERS[:2]):
            v = AwakeView(c, cid, PET_FLOOR, 140 + i * 200)
            self.views.append((v, _Idle(cid).pet))
        for v, pet in self.views:
            v.update(now, pet)
            v.draw(c, None)
        self.resume = self.game.pet is not None
        self.footer(True)
        c.full()
        c.present()

    def footer(self, visible):
        c = self.c
        c.rect(0, SCENE_BOTTOM, W, H - SCENE_BOTTOM, art.BAR)
        if visible:
            text = self.t.get("loading" if self.resume else "tap_to_start")
            c.text(text, W // 2, SCENE_BOTTOM + 30, 2, art.TEXT, CENTER)
        c.invalidate((0, SCENE_BOTTOM, W, H - SCENE_BOTTOM))

    def touch(self, event, x, y, now):
        if event == TAP and not self.resume:
            self.app.show(ChooseScreen(self.app), now)

    def update(self, now):
        c = self.c
        for v, pet in self.views:
            old = v.rect
            if v.update(now, pet):
                c.clip(old)
                draw_room(c, old, art.DAY, False)
                v.draw(c, old)
                c.unclip()
                c.invalidate(old)
        if self.resume and ticks_diff(now, self.started) >= self.RESUME_MS:
            self.app.show(MainScreen(self.app), now)
            return
        if not self.resume:
            blink = (ticks_diff(now, self.started) // 700) % 2
            if blink != self.blink:
                self.blink = blink
                self.footer(blink == 0)
        c.present()


# --- Choice of the pet ----------------------------------------------------------------------


class ChooseScreen(Screen):
    CARD_Y = 76
    CARD_H = 316

    def enter(self, now):
        self.selected = None
        self.cards = []
        n = len(pets.CHARACTERS)
        cw = (W - 16 * (n + 1)) // n
        for i, cid in enumerate(pets.CHARACTERS):
            self.cards.append((cid, (16 + i * (cw + 16), self.CARD_Y, cw, self.CARD_H)))
        self.views = []
        for cid, r in self.cards:
            v = AwakeView(self.c, cid, r[1] + 230, r[0] + r[2] // 2)
            self.views.append((v, _Idle(cid).pet, r))
        self.draw_all(now)

    def button_rect(self):
        return (16, 404, W - 32, 64)

    def draw_all(self, now):
        c = self.c
        c.rect(0, 0, W, H, art.BAR)
        c.text(self.t.get("choose"), W // 2, 28, 3, art.TEXT, CENTER)
        for i in range(len(self.cards)):
            self.draw_card(i, now)
        self.draw_button()
        c.full()
        c.present()

    def draw_card(self, i, now):
        c = self.c
        cid, (x, y, w, h) = self.cards[i]
        ch = pets.character(cid)
        border = art.ACCENT if cid == self.selected else art.TILE
        c.panel(x, y, w, h, art.DAY["wall"], border, 12)
        c.rect(x + 8, y + 190, w - 16, h - 198, art.DAY["floor"])
        v, pet, _ = self.views[i]
        v.draw(c, None)
        c.text(ch["name"], x + w // 2, y + 240, 3, art.PALETTE["O"], CENTER)
        traits = ch["traits"].get(self.app.lang) or ch["traits"].get("en", "")
        yy = y + 268
        for line in font.wrap(traits, w - 24, 2)[:2]:
            c.text(line, x + w // 2, yy, 2, art.PALETTE["O"], CENTER)
            yy += 18
        c.invalidate((x, y, w, h))

    def draw_button(self):
        c = self.c
        x, y, w, h = self.button_rect()
        c.rect(x, y, w, h, art.BAR)
        if self.selected:
            name = pets.character(self.selected)["name"]
            c.rounded(x, y, w, h, art.ACCENT, 8)
            c.text(self.t.get("adopt", name), x + w // 2, y + 22, 3, art.PALETTE["O"], CENTER)
        c.invalidate((x, y, w, h))

    def touch(self, event, x, y, now):
        if event != TAP:
            return
        for i, (cid, r) in enumerate(self.cards):
            if in_rect(x, y, r):
                previous = self.selected
                self.selected = cid
                for j, (other, _) in enumerate(self.cards):
                    if other in (cid, previous):
                        self.draw_card(j, now)
                v, pet, _ = self.views[i]
                v.react(now, {"eyes": "happy", "mouth": "open"}, 1200)
                self.draw_button()
                self.c.present()
                return
        if self.selected and in_rect(x, y, self.button_rect()):
            self.game.new_game(self.selected)
            self.app.show(MainScreen(self.app, welcome=True), now)

    def update(self, now):
        c = self.c
        for i, (v, pet, card) in enumerate(self.views):
            if v.update(now, pet):
                r = v.rect
                c.clip(r)
                cid, (x, y, w, h) = self.cards[i]
                c.rect(r[0], r[1], r[2], r[3], art.DAY["wall"])
                c.rect(x + 8, y + 190, w - 16, h - 198, art.DAY["floor"])
                v.draw(c, r)
                c.unclip()
                c.invalidate(r)
        c.present()


# --- The room -------------------------------------------------------------------------------


class MainScreen(Screen):
    PET_SHOWN = True     # the pet may take its nap on this screen

    def __init__(self, app, welcome=False):
        Screen.__init__(self, app)
        self.welcome = welcome

    def enter(self, now):
        pet = self.game.pet
        ch = pets.character(pet.character)
        self.t.set_pet(ch["name"], ch.get("gender", "f"))
        c = self.c
        self.scene = Scene(c)
        self.awake = AwakeView(c, pet.character, PET_FLOOR)
        self.sleeping = SleepView(c, pet.character, SLEEP_FLOOR)
        self.zzz = Zzz(self.sleeping.zzz_rect())
        self.label = Label(14, SCENE[1] + 12, 2)
        self.messes = [ArtItem(art.MESS, 3) for _ in MESS_SLOTS]
        for item, (mx, my) in zip(self.messes, MESS_SLOTS):
            item.x, item.y = mx, my
        self.bowl = ArtItem(art.ICONS["feed"], 4)
        self.ball = ArtItem(art.ICONS["play"], 2)
        self.particles = Particles()
        self.bubble = SpeechBubble()
        self.banner = Banner()
        self.popup = Popup((("meal", "feed", "meal"), ("treat", "treat", "treat")), self.t)
        self.pressed = None          # (row, index, since) of the bar button under the finger
        self.play = None             # the play session, when the ball is out
        self.bowl_until = 0
        self.showing_sleep = None
        self.night_checked = now
        self.scene.night = self.room_night(pet)
        self.items_for(pet)
        self.sync_sleep(now, pet)
        self.sync_messes(pet)
        self.sync_label(pet)
        if self.welcome:
            self.welcome = False     # enter() runs again when the screen lights up
            self.say(self.t.get("welcome"), now)
        for ev in self.game.take_events():
            self.on_event(ev, now)
        self.draw_all()

    def items_for(self, pet):
        view = self.sleeping if pet.asleep else self.awake
        items = [self.label] + self.messes + [view]
        if pet.asleep:
            items.append(self.zzz)
        items += [self.bowl, self.ball, self.particles, self.bubble, self.banner, self.popup]
        self.scene.items = items

    def draw_all(self):
        c = self.c
        self.draw_bar(TOP, 0)
        self.draw_bar(BOTTOM, SCENE_BOTTOM)
        self.scene.mark_all()
        self.scene.flush()
        c.full()
        c.present()

    # --- Bars -------------------------------------------------------------------------------

    def tile_state(self, row, i):
        if self.pressed is not None and self.pressed[0] == row and self.pressed[1] == i:
            return "pressed"
        action = (TOP if row == 0 else BOTTOM)[i]
        if self.game.pet.asleep and action in ("feed", "play"):
            return "off"
        return "normal"

    def draw_bar(self, actions, y):
        row = 0 if actions is TOP else 1
        w = W // len(actions)
        for i, icon in enumerate(actions):
            draw_tile(self.c, i * w, y, w, BAR_H, icon, self.tile_state(row, i))
        self.c.invalidate((0, y, W, BAR_H))

    def redraw_tile(self, row, i):
        actions = TOP if row == 0 else BOTTOM
        w = W // len(actions)
        y = 0 if row == 0 else SCENE_BOTTOM
        draw_tile(self.c, i * w, y, w, BAR_H, actions[i], self.tile_state(row, i))
        self.c.invalidate((i * w, y, w, BAR_H))

    def bar_at(self, x, y):
        if y < BAR_H:
            return 0, min(2, x // (W // 3))
        if y >= SCENE_BOTTOM:
            return 1, min(2, x // (W // 3))
        return None

    # --- Touch ------------------------------------------------------------------------------

    def touch(self, event, x, y, now):
        hit = self.bar_at(x, y)
        if event == DOWN:
            if hit is not None:
                self.press(hit, now)
            elif self.popup.open:
                i = self.popup.hit(x, y)
                if i is not None:
                    self.popup.pressed = i
                    self.scene.mark(self.popup.rect)
            return
        if event != TAP:
            return
        self.release()
        if self.popup.open:
            i = self.popup.hit(x, y)
            self.close_popup()
            if i is not None:
                self.feed(self.popup.choices[i][0], now)
            return
        if hit is not None:
            row, i = hit
            self.action((TOP if row == 0 else BOTTOM)[i], now)
        elif self.play is not None:
            self.throw(x, now)
        elif in_rect(x, y, self.view().rect):
            self.action("caress", now)

    def press(self, hit, now):
        self.release()
        self.pressed = (hit[0], hit[1], now)
        self.redraw_tile(hit[0], hit[1])

    def release(self):
        if self.pressed is not None:
            row, i, _ = self.pressed
            self.pressed = None
            self.redraw_tile(row, i)
        if self.popup.pressed is not None:
            self.popup.pressed = None
            self.scene.mark(self.popup.rect)

    # --- Actions ----------------------------------------------------------------------------

    def action(self, name, now):
        pet = self.game.pet
        if name != "play" and self.play is not None:
            self.end_play(now, None)
        if name == "stats":
            self.app.show(StatsScreen(self.app), now)
            return
        if name == "feed":
            if pet.asleep:
                self.say(self.t.get("r_asleep"), now)
            else:
                self.popup.open = True
                self.scene.mark(self.popup.rect)
            return
        if name == "caress":
            ok, reaction = self.game.caress()
            self.hearts(now)
            self.app.purr_lights(now, pet.asleep)
        elif name == "play":
            if self.play is not None:
                return
            if not engine.can_play(pet):
                self.respond(False, engine.R_ASLEEP if pet.asleep else engine.R_TOO_TIRED, now)
                return
            self.start_play(now)
            return
        elif name == "clean":
            ok, reaction = self.game.clean()
            if ok:
                self.bubbles(now)
                self.sync_messes(pet)
        elif name == "sleep":
            ok, reaction = self.game.toggle_sleep()
            if ok:
                self.sync_sleep(now, pet)
        else:
            return
        self.respond(ok, reaction, now)

    def feed(self, kind, now):
        ok, reaction = self.game.feed(engine.TREAT if kind == "treat" else engine.MEAL)
        if ok:
            self.awake.target = None
            r = self.awake.rect
            self.scene.mark(self.bowl.rect)
            self.bowl.rows = art.ICONS["treat" if kind == "treat" else "feed"]
            self.bowl.visible = True
            self.bowl.x = self.awake.x - 32
            self.bowl.y = PET_FLOOR + 8 - 14 * 4
            self.scene.mark(self.bowl.rect)
            self.bowl_until = ticks_add(now, engine.DURATIONS[engine.EAT][0] * 1000)
            self.scene.mark(r)
        self.respond(ok, reaction, now)

    def respond(self, ok, reaction, now):
        self.say(self.t.get("r_" + reaction), now)
        if not ok and reaction in REFUSALS and not self.game.pet.asleep:
            variants, shake = REFUSALS[reaction]
            self.awake.react(now, variants, 1500, shake)
        elif reaction == engine.R_PLAY_SULKY:
            self.awake.react(now, REFUSALS[reaction][0], 1500)

    def say(self, text, now):
        self.banner.show(self.scene, text, ticks_add(now, BANNER_MS))

    def close_popup(self):
        self.scene.mark(self.popup.rect)
        self.popup.open = False
        self.popup.pressed = None

    def hearts(self, now):
        r = self.view().rect
        for i in range(3):
            x = r[0] + r[2] // 2 - 40 + i * 30 + random.randint(-6, 6)
            self.particles.add(x, r[1] + 20 + i * 14, art.HEART, 4, 10 + i * 2)

    def bubbles(self, now):
        r = self.view().rect
        for i in range(7):
            x = r[0] + random.randint(0, r[2] - 20)
            y = r[1] + random.randint(r[3] // 3, r[3] - 20)
            rows = art.SPARKLE if i % 3 == 0 else art.BUBBLE_SMALL
            self.particles.add(x, y, rows, 4, random.randint(6, 14))

    # --- Play -------------------------------------------------------------------------------

    def start_play(self, now):
        self.play = {"throws": 0, "flying": None, "waiting": False, "last": now}
        self.awake.play_target = self.awake.x
        self.place_ball(self.awake.x + 70)
        self.say(self.t.get("play_hint"), now)

    def place_ball(self, x, y=None):
        self.scene.mark(self.ball.rect)
        self.ball.visible = True
        self.ball.x = int(x) - 16
        self.ball.y = PET_FLOOR - 28 if y is None else int(y)
        self.scene.mark(self.ball.rect)

    def throw(self, x, now):
        p = self.play
        if p["flying"] is not None or p["waiting"]:
            return
        target = max(70, min(410, int(x)))
        start = self.ball.x + 16
        p["flying"] = (start, target, 0)
        p["last"] = now
        p["due"] = now

    def step_play(self, now):
        p = self.play
        pet = self.game.pet
        if pet.asleep:
            self.end_play(now, None)
            return
        if p["flying"] is not None:
            if ticks_diff(now, p["due"]) < 0:
                return
            start, target, step = p["flying"]
            step += 1
            p["due"] = ticks_add(now, 40)
            t = step / 8.0
            x = start + (target - start) * t
            y = PET_FLOOR - 28 - int(120 * t * (1 - t))
            self.place_ball(x, y)
            if step >= 8:
                p["flying"] = None
                p["waiting"] = True
                offset = -50 if target > self.awake.x else 50
                self.awake.play_target = target + offset
                self.awake.walk_to(target + offset, run=True)
            else:
                p["flying"] = (start, target, step)
            return
        if p["waiting"] and self.awake.target is None:
            p["waiting"] = False
            ok, reaction = self.game.play()
            p["throws"] += 1
            p["last"] = now
            self.respond(ok, reaction, now)
            if ok and random.randint(0, 1):
                self.hearts(now)
            if p["throws"] >= PLAY_THROWS or not engine.can_play(pet):
                p["end_at"] = ticks_add(now, 1500)
            return
        if "end_at" in p and ticks_diff(now, p["end_at"]) >= 0:
            done = engine.can_play(pet)
            self.end_play(now, "play_end" if done else "r_too_tired")
            return
        if ticks_diff(now, p["last"]) > PLAY_TIMEOUT_MS:
            self.end_play(now, None)

    def end_play(self, now, message):
        self.play = None
        self.awake.play_target = None
        self.scene.mark(self.ball.rect)
        self.ball.visible = False
        if message:
            self.say(self.t.get(message), now)

    # --- State of the pet -------------------------------------------------------------------

    def view(self):
        return self.sleeping if self.game.pet.asleep else self.awake

    def sync_sleep(self, now, pet):
        if self.showing_sleep == pet.asleep:
            return
        self.showing_sleep = pet.asleep
        self.scene.night = self.room_night(pet)
        if pet.asleep:
            if self.play is not None:
                self.end_play(now, None)
            self.bowl.visible = False
            self.bubble.hide(self.scene)
            self.sleeping.started = False
        else:
            self.awake.x = 240
            self.awake.target = None
        self.items_for(pet)
        self.scene.mark_all()
        self.draw_bar(TOP, 0)   # feeding and playing wait while the pet sleeps

    def room_night(self, pet):
        """The room follows the time of day: a nap in the afternoon keeps the daylight. While
        the time is unknown, the room gets dark when the pet goes to bed (not for a nap)."""
        hour = self.game.hour()
        if hour is None:
            return pet.asleep and not pet.napping
        return engine.is_night(pet.profile, hour)

    def sync_night(self, now, pet):
        if ticks_diff(now, self.night_checked) < 1000:
            return
        self.night_checked = now
        night = self.room_night(pet)
        if night != self.scene.night:
            self.scene.night = night
            self.scene.mark_all()

    def sync_messes(self, pet):
        for i, item in enumerate(self.messes):
            visible = i < pet.messes
            if item.visible != visible:
                item.visible = visible
                self.scene.mark((item.x, item.y, item.w, item.h))

    def sync_label(self, pet):
        ch = pets.character(pet.character)
        text = "%s · %s" % (ch["name"], self.t.get("day", pet.days))
        self.label.set(self.scene, text, self.scene.colors["text"])

    def sync_bubble(self, pet):
        if pet.asleep or pet.activity != engine.CALL or self.play is not None:
            self.bubble.hide(self.scene)
            return
        need = engine.urgent_need(pet)
        icon = NEED_ICONS.get(need, "caress")
        r = self.awake.rect
        x = min(W - SpeechBubble.W - 4, r[0] + r[2] - 36)
        self.bubble.show(self.scene, icon, x, r[1] - 40)

    def on_event(self, ev, now):
        pet = self.game.pet
        if ev == engine.EV_REUNION:
            self.say(self.t.get("reunion"), now)
        elif ev == engine.EV_FELL_ASLEEP:
            self.say(self.t.get("fell_asleep"), now)
        elif ev == engine.EV_WOKE_UP:
            self.say(self.t.get("woke_up"), now)
        self.sync_messes(pet)

    # --- Animation --------------------------------------------------------------------------

    def update(self, now):
        pet = self.game.pet
        if pet is None:
            return
        for ev in self.game.take_events():
            self.on_event(ev, now)
        if self.showing_sleep != pet.asleep:
            self.sync_sleep(now, pet)
        self.sync_night(now, pet)
        if self.pressed is not None and not self.app.tracker.pressed and ticks_diff(now, self.pressed[2]) > 400:
            self.release()

        view = self.view()
        old = view.rect
        if view.update(now, pet):
            self.scene.mark(old)
            self.scene.mark(view.rect)
        if pet.asleep and self.zzz.update(now):
            self.scene.mark(self.zzz.rect)
        if self.play is not None:
            self.step_play(now)
        if self.bowl.visible and (ticks_diff(now, self.bowl_until) >= 0 or pet.activity != engine.EAT):
            self.scene.mark(self.bowl.rect)
            self.bowl.visible = False
        self.particles.step(self.scene, now, ticks_diff, ticks_add)
        self.sync_bubble(pet)
        if self.banner.text is not None and ticks_diff(now, self.banner.until) >= 0:
            self.banner.hide(self.scene)
        self.sync_messes(pet)
        self.sync_label(pet)
        self.scene.flush()
        self.c.present()


# --- Statistics -----------------------------------------------------------------------------


def draw_button(c, rect, label, primary=False, scale=2):
    x, y, w, h = rect
    c.rounded(x, y, w, h, art.ACCENT if primary else art.TILE, 8)
    ty = y + (h - font.CAP * scale) // 2
    c.text(label, x + w // 2, ty, scale, art.PALETTE["O"] if primary else art.TEXT, CENTER)


class StatsScreen(Screen):
    PET_SHOWN = True
    ROWS = (("satiety", "feed"), ("happiness", "caress"), ("energy", "energy"), ("hygiene", "clean"))

    def enter(self, now):
        self.shown = None
        self.draw(now)

    def buttons(self):
        return {"new_game": (16, 404, 160, 64), "options": (184, 404, 128, 64),
                "back": (320, 404, 144, 64)}

    def draw(self, now):
        c = self.c
        pet = self.game.pet
        ch = pets.character(pet.character)
        t = self.t
        c.rect(0, 0, W, H, art.BAR)
        c.text(ch["name"], 20, 24, 4, art.ACCENT, LEFT)
        c.text(t.get("day", pet.days), W - 20, 32, 3, art.TEXT, RIGHT)
        y = 96
        for name, icon in self.ROWS:
            value = getattr(pet, name)
            c.art(art.ICONS[icon], 20, y - 4, 2, art.PALETTE)
            c.text(t.get("stat_" + name), 64, y + 4, 2, art.TEXT, LEFT)
            bx, bw = 216, 244
            c.rounded(bx, y, bw, 24, art.TILE, 4)
            fill = int((bw - 8) * value / 100)
            color = art.PALETTE["G"] if value >= 60 else (art.PALETTE["Y"] if value >= engine.LOW else art.DANGER)
            if fill > 0:
                c.rect(bx + 4, y + 4, fill, 16, color)
            y += 48
        m = engine.mood(pet)
        c.text(t.get("mood", t.get("mood_" + m)), 20, y + 8, 2, art.TEXT, LEFT)
        k = pet.counts
        c.text(t.get("counts", k["meals"] + k["treats"], k["caresses"], k["plays"]), 20, y + 40, 2, art.TEXT_DIM, LEFT)
        if not self.game.clock.trusted:
            c.paragraph(t.get("clock_unknown"), 20, y + 72, W - 40, 2, art.TEXT_DIM)
        b = self.buttons()
        draw_button(c, b["new_game"], t.get("new_game"))
        draw_button(c, b["options"], t.get("options"))
        draw_button(c, b["back"], t.get("back"), primary=True, scale=3)
        self.shown = self.signature(pet)
        c.full()
        c.present()

    @staticmethod
    def signature(pet):
        return (int(pet.satiety), int(pet.happiness), int(pet.energy), int(pet.hygiene), pet.asleep, pet.days)

    def touch(self, event, x, y, now):
        if event != TAP:
            return
        b = self.buttons()
        if in_rect(x, y, b["back"]):
            self.app.show(MainScreen(self.app), now)
        elif in_rect(x, y, b["new_game"]):
            self.app.show(ResetScreen(self.app), now)
        elif in_rect(x, y, b["options"]):
            self.app.show(OptionsScreen(self.app), now)

    def update(self, now):
        if self.signature(self.game.pet) != self.shown:
            self.draw(now)


# --- Options --------------------------------------------------------------------------------


class OptionsScreen(Screen):
    """Brightness, nap delay and language. A choice applies at once and is saved."""

    PET_SHOWN = True
    ROW_Y = (108, 234, 340)     # top of the buttons of each setting
    ROW_H = 56

    def enter(self, now):
        self.draw()

    @staticmethod
    def choice_rect(row, i):
        if row == 2:            # two languages: wider buttons
            return (16 + i * 228, OptionsScreen.ROW_Y[row], 220, OptionsScreen.ROW_H)
        return (16 + i * 152, OptionsScreen.ROW_Y[row], 144, OptionsScreen.ROW_H)

    def back_rect(self):
        return (16, 412, 448, 56)

    def choices(self):
        s = self.app.settings
        t = self.t
        nap = [t.get("minutes", m) if m < 60 else t.get("hours", m // 60) for m in settings.NAP_MINUTES]
        return (
            ([t.get("bright_" + k) for k in settings.BRIGHTNESS_LEVELS],
             settings.BRIGHTNESS_LEVELS.index(s.brightness)),
            (nap, settings.NAP_MINUTES.index(s.nap_minutes)),
            ([LANGUAGE_NAMES[k] for k in settings.LANGUAGES], settings.LANGUAGES.index(s.language)),
        )

    def draw(self):
        self.t = self.app.texts         # the language may just have changed
        c = self.c
        t = self.t
        c.rect(0, 0, W, H, art.BAR)
        c.text(t.get("options"), 20, 20, 4, art.ACCENT, LEFT)
        c.text(t.get("brightness"), 20, 80, 2, art.TEXT, LEFT)
        c.text(t.get("nap_after"), 20, 180, 2, art.TEXT, LEFT)
        c.text(t.get("nap_hint"), 20, 206, 2, art.TEXT_DIM, LEFT)
        c.text(t.get("language"), 20, 312, 2, art.TEXT, LEFT)
        for row, (labels, selected) in enumerate(self.choices()):
            for i, label in enumerate(labels):
                draw_button(c, self.choice_rect(row, i), label, primary=(i == selected))
        draw_button(c, self.back_rect(), t.get("back"), primary=True, scale=3)
        c.full()
        c.present()

    def touch(self, event, x, y, now):
        if event != TAP:
            return
        if in_rect(x, y, self.back_rect()):
            self.app.show(StatsScreen(self.app), now)
            return
        s = self.app.settings
        for i in range(3):
            if in_rect(x, y, self.choice_rect(0, i)):
                level = settings.BRIGHTNESS_LEVELS[i]
                if level != s.brightness:
                    self.app.set_brightness(level)
                    s.save()
                    self.draw()
            elif in_rect(x, y, self.choice_rect(1, i)):
                minutes = settings.NAP_MINUTES[i]
                if minutes != s.nap_minutes:
                    s.nap_minutes = minutes
                    s.save()
                    self.draw()
            elif i < len(settings.LANGUAGES) and in_rect(x, y, self.choice_rect(2, i)):
                lang = settings.LANGUAGES[i]
                if lang != s.language:
                    self.app.set_language(lang)
                    s.save()
                    self.draw()


# --- New game -------------------------------------------------------------------------------


class ResetScreen(Screen):
    """Erasing the game needs the finger held on the button: a child cannot do it by mistake."""

    def enter(self, now):
        self.holding_since = None
        self.progress = -1
        self.draw()

    def buttons(self):
        return {"cancel": (16, 404, 216, 64), "erase": (248, 404, 216, 64)}

    def draw(self):
        c = self.c
        t = self.t
        c.rect(0, 0, W, H, art.BAR)
        c.text(t.get("reset_title"), W // 2, 120, 3, art.ACCENT, CENTER)
        c.paragraph(t.get("reset_text"), W // 2, 190, W - 64, 2, art.TEXT, CENTER)
        c.text(t.get("reset_hold"), W // 2, 330, 2, art.TEXT_DIM, CENTER)
        x, y, w, h = self.buttons()["cancel"]
        c.rounded(x, y, w, h, art.ACCENT, 8)
        c.text(t.get("cancel"), x + w // 2, y + 22, 3, art.PALETTE["O"], CENTER)
        self.draw_erase(0)
        c.full()
        c.present()

    def draw_erase(self, fraction):
        c = self.c
        x, y, w, h = self.buttons()["erase"]
        c.rect(x, y, w, h, art.BAR)
        c.rounded(x, y, w, h, art.TILE, 8)
        if fraction > 0:
            c.rounded(x, y, max(16, int(w * fraction)), h, art.DANGER, 8)
        c.text(self.t.get("erase"), x + w // 2, y + 22, 3, art.TEXT, CENTER)
        c.invalidate((x, y, w, h))

    def touch(self, event, x, y, now):
        b = self.buttons()
        if event == DOWN:
            self.holding_since = now if in_rect(x, y, b["erase"]) else None
        elif event == HOLD and in_rect(x, y, b["erase"]):
            self.game.erase()
            self.app.show(ChooseScreen(self.app), now)
        elif event == TAP:
            self.holding_since = None
            self.draw_erase(0)
            self.c.present()
            if in_rect(x, y, b["cancel"]):
                self.app.show(StatsScreen(self.app), now)

    def update(self, now):
        if self.holding_since is None:
            return
        if not self.app.tracker.pressed:
            self.holding_since = None
            self.draw_erase(0)
            self.c.present()
            return
        step = min(10, ticks_diff(now, self.holding_since) * 10 // HOLD_MS)
        if step != self.progress:
            self.progress = step
            self.draw_erase(step / 10.0)
            self.c.present()
