# The room where the pet lives, and the small compositor that redraws only what changed.
#
# Every visible thing is an item with a `rect` (screen pixels, or None when hidden) and a
# `draw(canvas, clip)` method. When something changes, its old and new rectangles are marked;
# flush() redraws each marked region (room, then items in order) inside a clip, and the
# canvas sends just those regions to the panel.

from prestopet import art, font
from prestopet.canvas import CENTER, LEFT, W, intersects, union

BAR_H = 80
SCENE = (0, BAR_H, W, 320)
SKIRTING_Y = 318
FLOOR_Y = 326
SCENE_BOTTOM = BAR_H + 320


def _clip_to_scene(r):
    x = max(0, r[0])
    y = max(SCENE[1], r[1])
    x2 = min(W, r[0] + r[2])
    y2 = min(SCENE_BOTTOM, r[1] + r[3])
    if x2 <= x or y2 <= y:
        return None
    return (x, y, x2 - x, y2 - y)


def draw_room(c, clip, colors, night):
    """The wall, a window, the floor and a rug. PicoGraphics clips the big fills; small
    details outside the clip are skipped here."""
    c.rect(0, SCENE[1], W, SKIRTING_Y - SCENE[1], colors["wall"])
    # Wallpaper: small diamonds
    for row, y in enumerate(range(SCENE[1] + 20, SKIRTING_Y - 8, 36)):
        if y + 8 < clip[1] or y > clip[1] + clip[3]:
            continue
        for x in range(20 + (row % 2) * 24, W, 48):
            if x + 8 < clip[0] or x > clip[0] + clip[2]:
                continue
            c.rect(x + 2, y, 4, 8, colors["wall_dots"])
            c.rect(x, y + 2, 8, 4, colors["wall_dots"])
    # Window
    wx, wy, ww, wh = 300, 112, 140, 108
    if intersects(clip, (wx, wy, ww, wh)):
        c.rect(wx, wy, ww, wh, colors["frame"])
        c.rect(wx + 8, wy + 8, ww - 16, wh - 16, colors["sky"])
        c.rect(wx + 8, wy + 8, ww - 16, 24, colors["sky_far"])
        if night:
            mx, my = wx + 96, wy + 24
            c.rect(mx, my, 16, 24, art.PALETTE["Y"])
            c.rect(mx - 4, my + 4, 4, 16, art.PALETTE["Y"])
            c.rect(mx + 4, my + 4, 12, 12, colors["sky"])
            for sx, sy in ((wx + 24, wy + 20), (wx + 56, wy + 52), (wx + 36, wy + 76), (wx + 104, wy + 72)):
                c.rect(sx, sy, 4, 4, art.PALETTE["W"])
        else:
            cx, cy = wx + 28, wy + 44
            c.rect(cx, cy + 8, 56, 12, art.PALETTE["W"])
            c.rect(cx + 12, cy, 24, 8, art.PALETTE["W"])
            c.rect(wx + 92, wy + 64, 28, 8, art.PALETTE["W"])
        c.rect(wx + ww // 2 - 4, wy + 8, 8, wh - 16, colors["frame"])
        c.rect(wx + 8, wy + wh // 2 - 4, ww - 16, 8, colors["frame"])
        c.rect(wx - 8, wy + wh, ww + 16, 8, colors["skirting"])
    # Skirting board and floor
    c.rect(0, SKIRTING_Y, W, FLOOR_Y - SKIRTING_Y, colors["skirting"])
    c.rect(0, FLOOR_Y, W, SCENE_BOTTOM - FLOOR_Y, colors["floor"])
    for i, y in enumerate((FLOOR_Y + 22, FLOOR_Y + 48)):
        c.rect(0, y, W, 4, colors["floor_line"])
        for x in range(60 + i * 70, W, 140):
            c.rect(x, y - 22, 4, 22, colors["floor_line"])
    # Rug under the pet
    if intersects(clip, (110, 366, 260, 34)):
        c.rect(150, 366, 180, 34, colors["rug_edge"])
        c.rect(118, 374, 244, 26, colors["rug_edge"])
        c.rect(158, 370, 164, 30, colors["rug"])
        c.rect(126, 378, 228, 22, colors["rug"])


class Scene:
    def __init__(self, canvas):
        self.c = canvas
        self.items = []
        self.dirty = []
        self.night = False

    @property
    def colors(self):
        return art.NIGHT if self.night else art.DAY

    def mark(self, r):
        if r is None:
            return
        r = _clip_to_scene(r)
        if r is None:
            return
        for i, d in enumerate(self.dirty):
            if intersects(d, r):
                self.dirty[i] = union(d, r)
                return
        self.dirty.append(r)

    def mark_all(self):
        self.dirty = [SCENE]

    def flush(self):
        if not self.dirty:
            return False
        # Regions merged while being added may now overlap each other.
        regions = []
        for r in self.dirty:
            for i, d in enumerate(regions):
                if intersects(d, r):
                    regions[i] = union(d, r)
                    break
            else:
                regions.append(r)
        self.dirty = []
        c = self.c
        colors = self.colors
        for r in regions:
            c.clip(r)
            draw_room(c, r, colors, self.night)
            for item in self.items:
                ir = item.rect
                if ir is not None and intersects(ir, r):
                    item.draw(c, r)
            c.unclip()
            c.invalidate(r)
        return True


# --- Items -----------------------------------------------------------------------------------


class ArtItem:
    """A static image (prop, mess) that can be shown, hidden and moved."""

    def __init__(self, rows, scale, palette=art.PALETTE):
        self.rows = rows
        self.scale = scale
        self.palette = palette
        self.w = len(rows[0]) * scale
        self.h = len(rows) * scale
        self.x = self.y = 0
        self.visible = False

    @property
    def rect(self):
        return (int(self.x), int(self.y), self.w, self.h) if self.visible else None

    def draw(self, c, clip):
        c.art(self.rows, int(self.x), int(self.y), self.scale, self.palette, clip)


class Label:
    """A line of text on the wall."""

    def __init__(self, x, y, scale):
        self.x = x
        self.y = y
        self.scale = scale
        self.text = ""
        self.color = (0, 0, 0)
        self.w = 0

    @property
    def rect(self):
        return (self.x, self.y, self.w, 7 * self.scale + 2) if self.text else None

    def set(self, scene, text, color):
        if text == self.text and color == self.color:
            return
        scene.mark(self.rect)
        self.text = text
        self.color = color
        self.w = font.width(text, self.scale)
        scene.mark(self.rect)

    def draw(self, c, clip):
        c.text(self.text, self.x, self.y, self.scale, self.color, LEFT)


class Banner:
    """A short message at the top of the room."""

    Y = 132
    H = 44

    def __init__(self):
        self.text = None
        self.scale = 3
        self.w = 0
        self.until = 0

    @property
    def rect(self):
        if self.text is None:
            return None
        return ((W - self.w) // 2, self.Y, self.w, self.H)

    def show(self, scene, text, until):
        scene.mark(self.rect)
        self.text = text
        self.scale = 3 if font.width(text, 3) <= 400 else 2
        self.w = font.width(text, self.scale) + 40
        self.until = until
        scene.mark(self.rect)

    def hide(self, scene):
        scene.mark(self.rect)
        self.text = None

    def draw(self, c, clip):
        x, y, w, h = self.rect
        c.panel(x, y, w, h, art.BUBBLE, art.PALETTE["O"], 8)
        ty = y + (h - 7 * self.scale) // 2
        c.text(self.text, x + w // 2, ty, self.scale, art.PALETTE["O"], CENTER)


class SpeechBubble:
    """A bubble with an icon, above the pet's head, when it asks for something."""

    W = 72
    H = 64

    def __init__(self):
        self.icon = None
        self.x = self.y = 0

    @property
    def rect(self):
        return (self.x, self.y, self.W, self.H) if self.icon else None

    def show(self, scene, icon, x, y):
        if (icon, x, y) == (self.icon, self.x, self.y):
            return
        scene.mark(self.rect)
        self.icon, self.x, self.y = icon, int(x), int(y)
        scene.mark(self.rect)

    def hide(self, scene):
        if self.icon:
            scene.mark(self.rect)
            self.icon = None

    def draw(self, c, clip):
        x, y = self.x, self.y
        o = art.PALETTE["O"]
        c.panel(x, y, self.W, self.H - 12, art.BUBBLE, o, 8)
        # The tail of the bubble, towards the head
        c.rect(x + 12, y + self.H - 16, 16, 8, o)
        c.rect(x + 16, y + self.H - 16, 8, 4, art.BUBBLE)
        c.rect(x + 8, y + self.H - 8, 8, 8, o)
        c.art(art.ICONS[self.icon], x + (self.W - 32) // 2, y + 10, 2, art.PALETTE, clip)


class Particles:
    """Hearts or bubbles floating up."""

    STEP_MS = 70

    def __init__(self):
        self.items = []     # [x, y, rows, scale, steps left]
        self.due = 0

    @property
    def rect(self):
        if not self.items:
            return None
        r = None
        for x, y, rows, s, _ in self.items:
            ir = (int(x), int(y), len(rows[0]) * s, len(rows) * s)
            r = ir if r is None else union(r, ir)
        return r

    def add(self, x, y, rows, scale, steps):
        self.items.append([x, y, rows, scale, steps])

    def step(self, scene, now, diff, add):
        if not self.items or diff(now, self.due) < 0:
            return
        self.due = add(now, self.STEP_MS)
        scene.mark(self.rect)
        alive = []
        for p in self.items:
            p[1] -= 4
            p[4] -= 1
            if p[4] > 0:
                alive.append(p)
        self.items = alive
        scene.mark(self.rect)

    def draw(self, c, clip):
        for x, y, rows, s, _ in self.items:
            c.art(rows, int(x), int(y), s, art.PALETTE, clip)


class Popup:
    """Choices over the room: (key, icon, label) buttons side by side."""

    def __init__(self, choices, texts):
        self.choices = choices
        self.texts = texts
        n = len(choices)
        self.bw = 150
        self.bh = 140
        self.w = n * self.bw + (n + 1) * 16
        self.h = self.bh + 32
        self.x = (W - self.w) // 2
        self.y = SCENE[1] + (SCENE[3] - self.h) // 2
        self.open = False
        self.pressed = None

    @property
    def rect(self):
        return (self.x, self.y, self.w, self.h) if self.open else None

    def button(self, i):
        return (self.x + 16 + i * (self.bw + 16), self.y + 16, self.bw, self.bh)

    def hit(self, x, y):
        for i in range(len(self.choices)):
            bx, by, bw, bh = self.button(i)
            if bx <= x < bx + bw and by <= y < by + bh:
                return i
        return None

    def draw(self, c, clip):
        c.panel(self.x, self.y, self.w, self.h, art.TILE, art.BAR, 12)
        for i, (key, icon, label) in enumerate(self.choices):
            bx, by, bw, bh = self.button(i)
            c.rounded(bx, by, bw, bh, art.TILE_PRESSED if i == self.pressed else art.BAR, 8)
            c.art(art.ICONS[icon], bx + (bw - 64) // 2, by + 14, 4, art.PALETTE, clip)
            c.text(self.texts.get(label), bx + bw // 2, by + bh - 34, 2, art.TEXT, CENTER)
