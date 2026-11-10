"""Runs the real game on a computer with a fake Presto, for previews and checks.

    python3 tools/simulator.py --play                      # play in a window (Pillow, Tk)
    python3 tools/simulator.py --lang en                    # scripted screenshots and the README
                                                            # banner, in docs/ (Pillow)

In the window, the mouse is the finger: click to tap, keep the button down to hold. The 7 LEDs
of the back are shown under the screen.
Keys: H moves time forward by one hour, D by one day. The game is saved in .sim/ and the
time spent with the window closed is caught up on the next launch, as on the Presto.

The fake display keeps two images, like the Presto: the frame buffer drawn by PicoGraphics,
and the panel, which only changes on update() or partial_update(). Screenshots show the
panel, so a region the game forgets to send shows up as stale. A scripted scenario plays
through adoption, care, play, sleep and the statistics.
"""

import argparse
import os
import shutil
import sys
import tempfile
import time
import types

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

_now = [0]
_skip = [0]                      # seconds added to the wall clock by the time keys
_real_time = time.time
time.time = lambda: _real_time() + _skip[0]
time.ticks_ms = lambda: _now[0]
time.ticks_diff = lambda a, b: a - b
time.ticks_add = lambda a, b: a + b
time.sleep_ms = lambda ms: None

from PIL import Image, ImageDraw  # noqa: E402

from prestopet import engine  # noqa: E402
from prestopet.app import App  # noqa: E402

SIZE = 480


class FakeDisplay:
    def __init__(self):
        self.buffer = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
        self.draw = ImageDraw.Draw(self.buffer)
        self.pen = (0, 0, 0)
        self.clip = None
        self.calls = 0

    def create_pen(self, r, g, b):
        # RGB565, as on the Presto: shows the colours as they will really be.
        return ((r >> 3) << 3, (g >> 2) << 2, (b >> 3) << 3)

    def set_pen(self, pen):
        self.pen = pen

    def set_clip(self, x, y, w, h):
        self.clip = (x, y, x + w, y + h)

    def remove_clip(self):
        self.clip = None

    def rectangle(self, x, y, w, h):
        self.calls += 1
        x2, y2 = x + w, y + h
        if self.clip:
            cx, cy, cx2, cy2 = self.clip
            x, y, x2, y2 = max(x, cx), max(y, cy), min(x2, cx2), min(y2, cy2)
        x, y, x2, y2 = max(0, x), max(0, y), min(SIZE, x2), min(SIZE, y2)
        if x2 > x and y2 > y:
            self.draw.rectangle((x, y, x2 - 1, y2 - 1), fill=self.pen)


class FakeBoard:
    def __init__(self):
        self.display = FakeDisplay()
        self.panel = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
        self.pixels_sent = 0

    def update(self):
        self.panel.paste(self.display.buffer)
        self.pixels_sent += SIZE * SIZE

    def partial_update(self, x, y, w, h):
        box = (x, y, x + w, y + h)
        self.panel.paste(self.display.buffer.crop(box), box)
        self.pixels_sent += w * h

    def set_backlight(self, value):
        pass


class FakeHardware:
    def __init__(self):
        self.board = FakeBoard()
        self.display = self.board.display
        self.down = False
        self.x = self.y = 0
        self.lit = True
        self.leds = ((0, 0, 0),) * 7

    def screen_on(self, on):
        self.lit = on

    def set_leds(self, colours):
        self.leds = colours

    def read_touch(self):
        return self.down, self.x, self.y


class Simulator:
    def __init__(self, save_file, lang="fr", screen_off=0):
        self.hw = FakeHardware()
        config = types.SimpleNamespace(LANGUAGE=lang, SAVE_FILE=save_file,
                                       SCREEN_OFF_MINUTES=screen_off,
                                       UTC_OFFSET_MINUTES=60, EU_SUMMER_TIME=True)
        self.app = App(self.hw, config)
        self.app.game.start()
        from prestopet.screens import TitleScreen
        self.app.show(TitleScreen(self.app), _now[0])
        self.frames = []

    def wait(self, ms):
        end = _now[0] + ms
        while _now[0] < end:
            _now[0] += 20
            before = self.hw.display.calls
            self.app.step(_now[0])
            self.frames.append(self.hw.display.calls - before)

    def tap(self, x, y, hold=80):
        self.hw.down, self.hw.x, self.hw.y = True, x, y
        self.wait(hold)
        self.hw.down = False
        self.wait(100)

    def shot(self, path):
        self.hw.board.panel.save(path)
        stale = self.hw.board.panel.tobytes() != self.hw.display.buffer.tobytes()
        print("%-34s %s" % (os.path.basename(path), "STALE PANEL" if stale else "ok"))
        return not stale


def scenario(out, lang="fr"):
    os.makedirs(out, exist_ok=True)
    tmp = tempfile.mkdtemp()
    ok = True
    try:
        sim = Simulator(os.path.join(tmp, "save.json"), lang)
        sim.wait(300)
        ok &= sim.shot(os.path.join(out, "01-title.png"))
        sim.tap(240, 240)
        sim.wait(300)
        sim.tap(120, 200)                     # Louna
        sim.wait(300)
        ok &= sim.shot(os.path.join(out, "02-choose.png"))
        sim.tap(240, 430)                     # adopt
        sim.wait(3000)
        ok &= sim.shot(os.path.join(out, "03-room.png"))
        pet = sim.app.game.pet
        pet.satiety = 40
        sim.tap(80, 40)                       # feed
        sim.wait(300)
        ok &= sim.shot(os.path.join(out, "04-feed-menu.png"))
        sim.tap(160, 240)                     # meal
        sim.wait(700)
        ok &= sim.shot(os.path.join(out, "05-eating.png"))
        sim.wait(4500)
        sim.tap(240, 300)                     # caress the pet
        sim.wait(250)
        ok &= sim.shot(os.path.join(out, "06-caress.png"))
        sim.wait(3000)
        sim.tap(400, 40)                      # play
        sim.wait(400)
        sim.tap(400, 360)                     # throw the ball
        sim.wait(1400)
        ok &= sim.shot(os.path.join(out, "07-play.png"))
        sim.wait(4000)
        sim.tap(240, 440)                     # sleep: not sleepy
        sim.wait(500)
        ok &= sim.shot(os.path.join(out, "08-not-sleepy.png"))
        sim.wait(3000)
        pet.energy = 50
        day_hour = sim.app.game.hour
        sim.app.game.hour = lambda epoch=None: 22   # bedtime, for the night room
        sim.tap(240, 440)                     # sleep
        sim.wait(4000)
        ok &= sim.shot(os.path.join(out, "09-asleep.png"))
        sim.app.game.hour = day_hour
        sim.tap(400, 440)                     # statistics
        sim.wait(300)
        ok &= sim.shot(os.path.join(out, "10-stats.png"))
        sim.tap(248, 436)                     # options
        sim.wait(200)
        sim.tap(240, 172)                     # brightness: medium
        sim.wait(200)
        ok &= sim.shot(os.path.join(out, "11-options.png"))
        sim.tap(240, 436)                     # back to the statistics
        sim.tap(96, 436)                      # start over
        sim.hw.down, sim.hw.x, sim.hw.y = True, 350, 430
        sim.wait(900)
        ok &= sim.shot(os.path.join(out, "12-reset-hold.png"))
        sim.hw.down = False
        sim.wait(200)
        sim.tap(120, 430)                     # cancel
        sim.tap(350, 430)                     # back to the room
        sim.wait(500)

        # Croquette, a few days later, neglected: messes and a call for food.
        sim2 = Simulator(os.path.join(tmp, "save2.json"), lang)
        sim2.wait(200)
        sim2.app.game.new_game("croquette")
        from prestopet.screens import MainScreen
        p2 = sim2.app.game.pet
        p2.age = 3 * 86400 + 100
        p2.satiety = 12
        p2.messes = 2
        p2.happiness = 45
        sim2.app.show(MainScreen(sim2.app), _now[0])
        p2.activity = engine.CALL
        p2.activity_left = 5
        sim2.wait(600)
        ok &= sim2.shot(os.path.join(out, "13-croquette-calls.png"))
        frames = [f for f in sim.frames + sim2.frames if f]
        print("rectangles per frame: max %d, average %d" % (max(frames), sum(frames) // len(frames)))
        print("pixels sent (first run): %d full screens" % (sim.hw.board.pixels_sent // (SIZE * SIZE)))
    finally:
        shutil.rmtree(tmp)
    return ok


HERO_SHOTS = ("02-choose.png", "05-eating.png", "07-play.png", "09-asleep.png")


def hero(shots, path, gap=32, radius=28):
    """The banner at the top of the README: a few screenshots side by side, with rounded
    corners on a transparent background, so it suits GitHub's light and dark themes."""
    from PIL import Image, ImageDraw
    images = [Image.open(os.path.join(shots, name)).convert("RGBA") for name in HERO_SHOTS]
    w = len(images) * SIZE + (len(images) - 1) * gap
    out = Image.new("RGBA", (w, SIZE), (0, 0, 0, 0))
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, SIZE - 1, SIZE - 1), radius, fill=255)
    for i, im in enumerate(images):
        out.paste(im, (i * (SIZE + gap), 0), mask)
    out.save(path, optimize=True)
    print("%-34s ok" % os.path.relpath(path, ROOT))


def play(lang="fr", zoom=1, save_file=None):
    """The game in a window, in real time."""
    import tkinter
    from PIL import ImageTk

    if save_file is None:
        folder = os.path.join(ROOT, ".sim")
        os.makedirs(folder, exist_ok=True)
        save_file = os.path.join(folder, "save.json")
    _now[0] = int(_real_time() * 1000) & 0x3FFFFFFF
    sim = Simulator(save_file, lang)
    hw = sim.hw
    size = SIZE * zoom

    root = tkinter.Tk()
    root.title("Presto-Pet")
    root.resizable(False, False)
    view = tkinter.Label(root, borderwidth=0, background="black", cursor="hand2")
    view.pack()
    # The 7 LEDs of the back of the Presto, shown under the screen
    strip = tkinter.Canvas(root, width=size, height=28, background="#1c1420", highlightthickness=0)
    strip.pack()
    gap = size // 7
    dots = [strip.create_oval(i * gap + gap // 2 - 9, 5, i * gap + gap // 2 + 9, 23,
                              fill="#000000", outline="#3a2e40") for i in range(7)]
    lit_leds = [None]
    status = tkinter.Label(root, anchor="w", font=("TkFixedFont", 10),
                           text="clic = toucher · H = +1 heure · D = +1 jour")
    status.pack(fill="x")
    shown = [None, None]       # last pixels_sent and screen state drawn in the window
    black = Image.new("RGB", (size, size), (0, 0, 0))

    def touch(event, down):
        hw.down = down
        hw.x = max(0, min(SIZE - 1, event.x // zoom))
        hw.y = max(0, min(SIZE - 1, event.y // zoom))

    def skip(seconds):
        # The wall clock and the counter move together: the game sees time passing,
        # like a device left running.
        _skip[0] += seconds
        _now[0] += seconds * 1000
        sim.app.step(_now[0])
        days = _skip[0] / 86400
        status.config(text="avance : %.2f jour(s) · clic = toucher · H = +1 h · D = +1 jour" % days)

    view.bind("<ButtonPress-1>", lambda e: touch(e, True))
    view.bind("<B1-Motion>", lambda e: touch(e, True))
    view.bind("<ButtonRelease-1>", lambda e: touch(e, False))
    for key, seconds in (("h", 3600), ("d", 86400)):
        root.bind("<Key-%s>" % key, lambda e, s=seconds: skip(s))
        root.bind("<Key-%s>" % key.upper(), lambda e, s=seconds: skip(s))

    last = [_real_time()]

    def frame():
        t = _real_time()
        ms = int(min(0.25, max(0.0, t - last[0])) * 1000)
        last[0] = t
        for _ in range(max(1, ms // 20)):
            _now[0] += 20
            sim.app.step(_now[0])
        if hw.leds != lit_leds[0]:
            lit_leds[0] = hw.leds
            for dot, (r, g, b) in zip(dots, hw.leds):
                strip.itemconfig(dot, fill="#%02x%02x%02x" % (r, g, b))
        state = (hw.board.pixels_sent, hw.lit)
        if state != shown[:2]:
            shown[:] = state
            img = hw.board.panel if hw.lit else black
            if zoom != 1 and hw.lit:
                img = img.resize((size, size), Image.NEAREST)
            view.image = ImageTk.PhotoImage(img)
            view.config(image=view.image)
        root.after(20, frame)

    def close():
        sim.app.game.save_now()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", close)
    frame()
    root.mainloop()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--play", action="store_true", help="play in a window")
    parser.add_argument("--zoom", type=int, default=1, help="window scale (--play)")
    parser.add_argument("--save", help="save file (--play), default .sim/save.json")
    parser.add_argument("--shots", default=os.path.join(ROOT, "docs", "screenshots"))
    parser.add_argument("--hero", default=os.path.join(ROOT, "docs", "hero.png"),
                        help="banner made from the screenshots ('' to skip)")
    parser.add_argument("--lang", default="fr")
    args = parser.parse_args()
    if args.play:
        play(args.lang, args.zoom, args.save)
        return
    ok = scenario(args.shots, args.lang)
    if ok and args.hero:
        hero(args.shots, args.hero)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
