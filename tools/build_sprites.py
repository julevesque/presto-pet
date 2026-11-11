"""Generates the cat sprites from simple shapes, awake and asleep.

    python3 tools/build_sprites.py            # writes src/prestopet/pets/coat_*.py, sleep_*.py
    python3 tools/build_sprites.py --check    # fails if the committed files are out of date

The cat is drawn in semantic colour codes, so every character with the same coat shares the
art and only brings its palette (see src/prestopet/pets/). A coat is the pattern of the fur:
"tuxedo" (black and white, like Louna) or "tabby" (striped, like Croquette).

The awake cat is delivered ready to draw: for each pose and each row, the runs of colour of
that row for every combination of the parts that change it (eyes, mouth, ears, tail, paws or
legs). On the Presto, a frame is then one table lookup per row: composing images and cutting
rows into runs takes hundreds of milliseconds in MicroPython, which made the walk stutter.

Codes:  O outline   B fur   b fur shadow   L fur light   S stripe
        W white fur   w white shadow   P pink   p mouth   E iris   e pupil   K eye shine
"""

import itertools
import math
import os
import sys

W = 40
H = 46
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT_DIR = os.path.join(ROOT, "src", "prestopet", "pets")

FUR = "B"
FUR_SHADOW = "b"
FUR_LIGHT = "L"
WHITE = "W"
WHITE_SHADOW = "w"

# --- Masks ------------------------------------------------------------------------------------


def ellipse(cx, cy, rx, ry):
    m = set()
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            dx = (x + 0.5 - cx) / rx
            dy = (y + 0.5 - cy) / ry
            if dx * dx + dy * dy <= 1.0:
                m.add((x, y))
    return m


def polygon(points):
    m = set()
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    for y in range(int(min(ys)) - 1, int(max(ys)) + 2):
        for x in range(int(min(xs)) - 1, int(max(xs)) + 2):
            px, py = x + 0.5, y + 0.5
            inside = False
            j = len(points) - 1
            for i in range(len(points)):
                xi, yi = points[i]
                xj, yj = points[j]
                if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi) + xi:
                    inside = not inside
                j = i
            if inside:
                m.add((x, y))
    return m


def rect(x, y, w, h):
    return {(i, j) for i in range(x, x + w) for j in range(y, y + h)}


def stroke(points, radius):
    """A thick curve through the points (for the tail). Returns (mask, position along it)."""
    m = {}
    total = 0.0
    for i in range(len(points) - 1):
        (x1, y1), (x2, y2) = points[i], points[i + 1]
        length = math.hypot(x2 - x1, y2 - y1)
        steps = max(1, int(length * 3))
        for s in range(steps + 1):
            t = s / steps
            cx = x1 + (x2 - x1) * t
            cy = y1 + (y2 - y1) * t
            along = total + length * t
            for (x, y) in ellipse(cx, cy, radius, radius):
                if (x, y) not in m:
                    m[(x, y)] = along
        total += length
    return m


def dilate(mask):
    out = set()
    for (x, y) in mask:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            out.add((x + dx, y + dy))
    return out - mask


# --- Image ------------------------------------------------------------------------------------


class Image:
    def __init__(self, w=W, h=H):
        self.w = w
        self.h = h
        self.px = [["."] * w for _ in range(h)]

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.px[y][x]
        return "."

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = c

    def part(self, mask, fill, shadow, light=None, outline=True, mark=None, line="O"):
        """Paints a shape with a one pixel outline around it, a shadow on its lower right
        rim and a highlight on its upper left rim. `mark(x, y, code)` adds the coat pattern."""
        if outline:
            for (x, y) in dilate(mask):
                self.set(x, y, line)
        for (x, y) in mask:
            c = fill
            if (x + 1, y) not in mask or (x, y + 1) not in mask or (x, y + 2) not in mask:
                c = shadow
            elif light and ((x - 1, y) not in mask or (x, y - 1) not in mask):
                c = light
            if mark:
                c = mark(x, y, c)
            self.set(x, y, c)

    def pattern(self, x, y, rows, keep="."):
        for j, row in enumerate(rows):
            for i, c in enumerate(row):
                if c != keep:
                    self.set(x + i, y + j, c)

    def rows(self):
        return ["".join(r) for r in self.px]


# --- Coats -------------------------------------------------------------------------------------
# A coat decides which fur pixels are white or striped. `mark(part, x, y, code)`.


def _is_fur(c):
    return c in (FUR, FUR_SHADOW, FUR_LIGHT)


def tuxedo(part, x, y, c, ctx):
    """Black and white: white blaze between the eyes, joining the white muzzle."""
    if part == "head" and _is_fur(c):
        top = ctx["head_y"]
        if 19 <= x <= 20 and top + 6 <= y:
            return WHITE
    return c


def tabby(part, x, y, c, ctx):
    """Striped: an M on the forehead, stripes on the cheeks, the flanks, the legs and rings
    around the tail."""
    if not _is_fur(c):
        return c
    top = ctx["head_y"]
    if part == "head":
        fy = y - top
        # The M on the forehead
        if fy in (3, 4, 5) and x in (16, 20, 24):
            return "S"
        if fy == 2 and x in (17, 23):
            return "S"
        # Cheeks
        if fy in (11, 13) and (7 <= x <= 9 or 30 <= x <= 32):
            return "S"
        return c
    if part in ("body", "haunch"):
        if y % 3 == 0 and abs(x - 20) >= 7 and y < 42:
            return "S"
        return c
    if part == "back":
        if (x + y) % 4 == 0:
            return "S"
    if part == "loaf":
        # Curled up: stripes go round the back, from the spine towards the floor
        if x > 30 and int(x - 0.5 * y) % 5 == 0:
            return "S"
    return c


COATS = {"tuxedo": tuxedo, "tabby": tabby}

# --- The cat -----------------------------------------------------------------------------------

EYES = {
    "open": (".OOO.",
             "OKeEO",
             "OeeEO",
             "OEEEO",
             ".OOO."),
    "wide": (".OOO.",
             "OKeeO",
             "OeeeO",
             "OeeeO",
             ".OOO."),
    "blink": (".....",
              ".....",
              ".....",
              "O...O",
              ".OOO."),
    "happy": (".....",
              "..O..",
              ".O.O.",
              "O...O",
              "....."),
    "half": (".....",
             ".....",
             "OOOOO",
             "OeEEO",
             ".OOO."),
    # Glancing aside, just before turning to walk that way
    "look_l": (".OOO.",
               "OeeEO",
               "OeeEO",
               "OEEEO",
               ".OOO."),
    "look_r": (".OOO.",
               "OEeeO",
               "OEeeO",
               "OEEEO",
               ".OOO."),
}

MOUTHS = {
    "neutral": ("......",
                ".O..O.",
                "..OO..",
                "......"),
    "open": ("..OO..",
             ".OppO.",
             ".OpPO.",
             "..OO.."),
    "yum": ("......",
            ".O..O.",
            "..OO..",
            "..PP.."),
    "yawn": (".OOOO.",
             "OppppO",
             "OpPPpO",
             ".OOOO."),
}

DEFAULT = {"eyes": "open", "mouth": "neutral", "ears": "up", "tail": "rest", "paws": "down"}
VARIANTS = {
    "eyes": tuple(EYES),
    "mouth": tuple(MOUTHS),
    "ears": ("up", "flat"),
    "tail": ("rest", "up", "flick"),
    "paws": ("down", "groom", "pounce"),
}
POSES = {"sit": 0, "eat": 5}   # vertical offset of the head


def draw_cat(coat, pose="sit", **variant):
    v = dict(DEFAULT)
    v.update(variant)
    hy = POSES[pose]
    ctx = {"head_y": 5 + hy}
    mark_of = COATS[coat]

    def marker(part):
        return lambda x, y, c: mark_of(part, x, y, c, ctx)

    img = Image()

    # Tail, behind the body
    tails = {
        "rest": [(29, 43), (33, 43), (36, 41), (37.5, 38), (37.5, 34), (36.5, 31)],
        "up": [(29, 42), (33, 40), (35.5, 36), (36.5, 31), (36.5, 26), (35, 23)],
        "flick": [(29, 43), (33, 43), (36, 41), (37.5, 38), (37, 34), (34.5, 31)],
    }
    tail = stroke(tails[v["tail"]], 1.6)
    tail_mask = set(tail)
    if coat == "tabby":
        def tail_mark(x, y, c):
            return "S" if _is_fur(c) and int(tail[(x, y)]) % 3 == 0 else c
    else:
        tail_mark = None
    img.part(tail_mask, FUR, FUR_SHADOW, FUR_LIGHT, mark=tail_mark)

    # Body: chest and the two haunches, sitting on the floor
    body = ellipse(20, 33, 9, 10) | ellipse(11.5, 39.5, 6, 5) | ellipse(28.5, 39.5, 6, 5)
    body = {(x, y) for (x, y) in body if y <= 44}
    img.part(body, FUR, FUR_SHADOW, FUR_LIGHT, mark=marker("body"))
    img.part(ellipse(20, 31, 4.6, 6.5), WHITE, WHITE_SHADOW, outline=False)

    # Front legs and paws
    paws = v["paws"]
    if paws in ("down", "groom"):
        img.part(rect(14, 35, 4, 8), FUR, FUR_SHADOW, FUR_LIGHT, mark=marker("leg"))
        img.part(ellipse(16, 43.5, 2.6, 1.6), WHITE, WHITE_SHADOW)
    if paws == "down":
        img.part(rect(22, 35, 4, 8), FUR, FUR_SHADOW, FUR_LIGHT, mark=marker("leg"))
        img.part(ellipse(24, 43.5, 2.6, 1.6), WHITE, WHITE_SHADOW)

    # Head: skull, cheeks and ears, outlined together
    head = ellipse(20, 15.5 + hy, 12.5, 10) | ellipse(20, 19 + hy, 14, 7)
    ear_points = {
        "up": (((7.5, 12), (9.5, 0.5), (17, 7)), ((32.5, 12), (30.5, 0.5), (23, 7))),
        "flat": (((6, 15), (4.5, 6), (15, 8)), ((34, 15), (35.5, 6), (25, 8))),
    }[v["ears"]]
    ears = set()
    for tri in ear_points:
        ears |= polygon([(x, y + hy) for (x, y) in tri])
    img.part(head | ears, FUR, FUR_SHADOW, FUR_LIGHT, mark=marker("head"))
    for tri in ear_points:
        (ax, ay), (bx, by), (cx, cy) = tri
        mx, my = (ax + bx + cx) / 3, (ay + by + cy) / 3
        inner = [(mx + (px - mx) * 0.5, my + (py - my) * 0.5 + hy + 0.8) for (px, py) in tri]
        for (x, y) in polygon(inner):
            img.set(x, y, "P")

    # Muzzle
    img.part(ellipse(20, 21.5 + hy, 5.6, 3.8), WHITE, WHITE_SHADOW, outline=False)

    # Eyes, nose and mouth
    for ex in (12, 24):
        img.pattern(ex, 13 + hy, EYES[v["eyes"]])
    img.set(19, 19 + hy, "P")
    img.set(20, 19 + hy, "P")
    img.pattern(17, 20 + hy, MOUTHS[v["mouth"]])

    # Raised paws, in front of everything
    if paws == "groom":
        img.part(ellipse(25, 27 + hy, 2.8, 2.2), WHITE, WHITE_SHADOW)
        img.part(rect(23, 29 + hy, 4, 8 - hy), FUR, FUR_SHADOW, FUR_LIGHT, mark=marker("leg"))
        img.part(ellipse(25, 27 + hy, 2.8, 2.2), WHITE, WHITE_SHADOW, outline=False)
    elif paws == "pounce":
        for px in (13, 27):
            img.part(ellipse(px, 29, 3, 2.4), WHITE, WHITE_SHADOW)
    return img.rows()


# --- The cat in profile, walking, hopping and leaping -----------------------------------------
# Drawn facing right; "side_l" is the mirror image. The legs are the patches that animate the
# walk: four frames of a walk cycle, gathered and stretched for the hops, reaching for a pounce.

SIDE_EYES = {
    "open": (".OO.",
             "OKeO",
             "OEeO",
             "OEEO",
             ".OO."),
    "blink": ("....",
              "....",
              "....",
              "O..O",
              ".OO."),
    "happy": ("....",
              ".OO.",
              "O..O",
              "....",
              "...."),
    "half": ("....",
             "....",
             "OOOO",
             "OEeO",
             ".OO."),
}
SIDE_EYES["wide"] = SIDE_EYES["open"]

SIDE_MOUTHS = {
    "neutral": ("...",
                "OO.",
                "..."),
    "open": (".OO",
             "OpO",
             ".OO"),
    "lick": ("...",
             "OOP",
             "..P"),
    "yawn": (".OOO",
             "OppO",
             "OpPO",
             ".OO."),
}

# Paws relative to their hip: (dx, paw y). Order: far front, far back, near front, near back.
FLOOR = 44
SIDE_LEGS = {
    "stand": ((0, FLOOR), (0, FLOOR), (0, FLOOR), (0, FLOOR)),
    "w0": ((-2, FLOOR), (3, FLOOR), (3, FLOOR), (-2, FLOOR)),
    "w1": ((1, 42), (0.5, FLOOR), (0.5, FLOOR), (1, 42)),
    "w2": ((3, FLOOR), (-2, FLOOR), (-2, FLOOR), (3, FLOOR)),
    "w3": ((0.5, FLOOR), (1, 42), (1, 42), (0.5, FLOOR)),
    "gather": ((-3, FLOOR), (4, FLOOR), (-2, FLOOR), (5, FLOOR)),
    "stretch": ((5, 41), (-6, 42), (6.5, 41.5), (-5, 42.5)),
    "reach": ((6.5, 37), (-6, 42), (8, 38), (-5, 42.5)),
    "catch": ((6, FLOOR), (-1, FLOOR), (7.5, FLOOR), (0, FLOOR)),
    # Licking a front paw, raised to the mouth
    "lick": ((0, FLOOR), (0, FLOOR), (6, 29), (0, FLOOR)),
    # Kneading the cushion, one front paw then the other
    "knead_a": ((0.5, FLOOR), (0, FLOOR), (1.5, 41), (0, FLOOR)),
    "knead_b": ((1.5, 41), (0, FLOOR), (0.5, FLOOR), (0, FLOOR)),
}
SIDE_HIPS = ((23.5, 35), (10.5, 35), (26, 35), (13, 35))
SIDE_DEFAULT = {"eyes": "open", "mouth": "neutral", "tail": "up", "legs": "stand"}
SIDE_VARIANTS = {
    "eyes": tuple(SIDE_EYES),
    "mouth": ("neutral", "open", "lick"),
    "tail": ("up", "flick", "back"),
    "legs": tuple(SIDE_LEGS),
}

# Crouched before a pounce, the hindquarters wiggling from side to side
CROUCH_DEFAULT = {"eyes": "wide", "mouth": "neutral", "wiggle": "mid"}
CROUCH_VARIANTS = {
    "eyes": ("wide", "blink"),
    "mouth": ("neutral", "open"),
    "wiggle": ("mid", "left", "right"),
}
WIGGLE = {"mid": 0, "left": -1, "right": 1}

# Stretching, front paws far ahead and the rear up (a yawn goes with it)
BOW_DEFAULT = {"eyes": "blink", "mouth": "yawn", "tail": "up"}
BOW_VARIANTS = {
    "eyes": ("blink", "open", "happy"),
    "mouth": ("yawn", "neutral"),
    "tail": ("up", "flick"),
}

# Per shape: body ellipses, hips (as SIDE_HIPS), tails, head offset (dx, dy)
SHAPES = {
    "stand": {
        "body": ((18.5, 31.5, 11.5, 6.5), (26, 31, 5.5, 6.5)),
        "chest": (28.5, 33, 3.2, 4.2),
        "hips": SIDE_HIPS,
        "tails": {
            "up": [(9, 31), (5, 29), (3, 25), (3, 20), (4.5, 16)],
            "flick": [(9, 31), (5, 29), (3, 25), (3.5, 20), (6.5, 16.5)],
            "back": [(9, 30), (5, 28.5), (2.5, 26.5), (1.5, 23)],
        },
        "head": (0, 0),
    },
    "crouch": {
        "body": ((19, 36.5, 11, 5), (26.5, 36, 5, 5.5)),
        "chest": (29, 38, 3, 3),
        "hips": ((24, 39), (11.5, 38.5), (26.5, 39), (14, 38.5)),
        "tails": {"low": [(9, 37), (5, 38), (1.5, 39)]},
        "head": (1, 6),
    },
    "bow": {
        "body": ((13, 26, 7, 6), (19.5, 31, 8, 5.5), (25.5, 37, 5.5, 4.5)),
        "chest": (28, 38.5, 3, 3),
        "hips": ((23, 40), (10.5, 29.5), (25.5, 40), (13, 29.5)),
        "tails": {
            "up": [(8, 24.5), (5, 20), (4, 15), (5.5, 10)],
            "flick": [(8, 24.5), (5, 20), (4.5, 15), (7.5, 10.5)],
        },
        "head": (1, 9),
    },
}


def side_mark(coat, part, x, y, c):
    if not _is_fur(c):
        return c
    if coat == "tabby":
        if part == "body" and x % 3 == 0 and 9 <= x <= 25 and y <= 38:
            return "S"
        if part == "head" and ((y in (14, 15, 16) and x in (26, 29)) or (y in (23, 25) and 24 <= x <= 27)):
            return "S"
        if part == "leg" and y % 3 == 0 and y < 42:
            return "S"
    return c


def draw_side(coat, shape="stand", **variant):
    defaults = {"stand": SIDE_DEFAULT, "crouch": CROUCH_DEFAULT, "bow": BOW_DEFAULT}[shape]
    v = dict(defaults)
    v.update(variant)
    g = SHAPES[shape]
    hdx, hdy = g["head"]
    img = Image()

    def marker(part):
        if part == "head" and coat == "tabby":
            return lambda x, y, c: side_mark(coat, part, x - hdx, y - hdy, c)
        return lambda x, y, c: side_mark(coat, part, x, y, c)

    # Crouched, the rump and the tail sway with the wiggle
    sway = WIGGLE[v["wiggle"]] if shape == "crouch" else 0

    # Tail, behind everything
    path = g["tails"]["low" if shape == "crouch" else v["tail"]]
    if sway:
        path = [(x + sway * (i / (len(path) - 1)) * 3, y + abs(sway) * (i / (len(path) - 1)) * 1.5) for i, (x, y) in enumerate(path)]
    tail = stroke(path, 1.6)
    if coat == "tabby":
        def tail_mark(x, y, c):
            return "S" if _is_fur(c) and int(tail[(x, y)]) % 3 == 0 else c
    else:
        tail_mark = None
    img.part(set(tail), FUR, FUR_SHADOW, FUR_LIGHT, mark=tail_mark)

    if shape == "crouch":
        legs = ((2, FLOOR), (3, FLOOR), (2.5, FLOOR), (3, FLOOR))
    elif shape == "bow":
        legs = ((8, FLOOR), (0, FLOOR), (9.5, FLOOR), (0, FLOOR))
    else:
        legs = SIDE_LEGS[v["legs"]]
    hips = g["hips"]

    def leg(i, near):
        hx, hy = hips[i]
        if i in (1, 3):
            hx += sway
        dx, py = legs[i]
        mask = set(stroke([(hx, hy), (hx + dx * 0.6, (hy + py) / 2), (hx + dx, py - 1)], 1.5))
        if near:
            img.part(mask, FUR, FUR_SHADOW, FUR_LIGHT, mark=marker("leg"))
        else:
            img.part(mask, FUR_SHADOW, FUR_SHADOW)
        img.part(ellipse(hx + dx + 0.8, py + 0.3, 2.2, 1.3), WHITE if near else WHITE_SHADOW,
                 WHITE_SHADOW)

    # The far legs, darker, behind the body
    leg(0, False)
    leg(1, False)

    # Body, with the white chest at the front
    body = set()
    for i, (cx, cy, rx, ry) in enumerate(g["body"]):
        body |= ellipse(cx + (sway if i == 0 and shape == "crouch" else 0), cy, rx, ry)
    if shape == "crouch":
        body |= ellipse(12 + sway, 35.5, 6, 5.5)
    img.part(body, FUR, FUR_SHADOW, FUR_LIGHT, mark=marker("body"))
    chest = ellipse(*g["chest"]) & body
    for (x, y) in chest:
        img.set(x, y, WHITE_SHADOW if (x, y + 1) not in body else WHITE)

    # The near legs (a paw raised to lick is drawn after the head)
    lick = shape == "stand" and v["legs"] == "lick"
    if not lick:
        leg(2, True)
    leg(3, True)

    # Head, ears, muzzle, eye, nose and mouth: as big as seen from the front
    def at(points):
        return [(x + hdx, y + hdy) for (x, y) in points]

    head = ellipse(29.5 + hdx, 21 + hdy, 8.5, 7.8) | ellipse(31 + hdx, 24.5 + hdy, 7.5, 4.8)
    far_ear = polygon(at([(23.5, 17), (24, 7), (29.5, 14)]))
    img.part(far_ear, FUR_SHADOW, FUR_SHADOW)
    near_ear = polygon(at([(27, 15), (31, 5.5), (35.5, 15.5)]))
    img.part(head | near_ear, FUR, FUR_SHADOW, FUR_LIGHT, mark=marker("head"))
    for (x, y) in polygon(at([(29.3, 13.8), (31, 9), (33.5, 14.2)])):
        img.set(x, y, "P")
    img.part(ellipse(35 + hdx, 25.5 + hdy, 3.8, 2.8), WHITE, WHITE_SHADOW, outline=False)
    img.pattern(31 + hdx, 18 + hdy, SIDE_EYES[v["eyes"]])
    img.set(38 + hdx, 23 + hdy, "P")
    img.set(37 + hdx, 23 + hdy, "P")
    img.pattern(35 + hdx, 25 + hdy, SIDE_MOUTHS[v["mouth"]])
    if lick:
        leg(2, True)
    return img.rows()


def mirror(rows):
    return [r[::-1] for r in rows]


# --- The cat asleep, curled up on its cushion -------------------------------------------------
# The same head as awake, eyes closed, resting on the front paws, the body curled behind it
# and the tail wrapped around. Two layers: the cushion (codes 0-4, coloured by each character)
# and the cat.

SLEEP_W = 68
CAT_W = 60
CAT_H = 42
CAT_X = 4             # the cat layer on the sprite
CUSHION_Y = 32        # the cushion layer on the sprite
CUSHION_H = 22
SLEEP_H = CUSHION_Y + CUSHION_H
HEAD_DY = 8           # the head, lower than when sitting
EAR_TIP = (28, HEAD_DY, 6, 5)   # zone of the right ear tip, for the twitches


def draw_cushion():
    img = Image(SLEEP_W, CUSHION_H)
    img.part(ellipse(34, 10.5, 33, 9), "3", "4", line="0")
    img.part(ellipse(34, 7, 31, 6), "2", "3", "1", line="0")
    return img.rows()


def draw_sleeping(coat):
    hy = HEAD_DY
    ctx = {"head_y": 5 + hy}
    mark_of = COATS[coat]

    def marker(part):
        return lambda x, y, c: mark_of(part, x, y, c, ctx)

    img = Image(CAT_W, CAT_H)

    # The body, curled up behind the head: a round back on the right
    body = ellipse(36, 30, 22, 10.5) | ellipse(44, 26, 13, 11)
    body = {(x, y) for (x, y) in body if y <= 40}
    img.part(body, FUR, FUR_SHADOW, FUR_LIGHT, mark=marker("loaf"))

    # White chest between the front paws
    img.part(ellipse(20, 35, 8, 4), WHITE, WHITE_SHADOW)

    # The tail, wrapped around the front of the body
    tail = stroke([(57, 31), (56.5, 36), (51, 39.2), (40, 40), (30, 39.8)], 1.6)
    if coat == "tabby":
        def tail_mark(x, y, c):
            return "S" if _is_fur(c) and int(tail[(x, y)]) % 3 == 0 else c
    else:
        tail_mark = None
    img.part(set(tail), FUR, FUR_SHADOW, FUR_LIGHT, mark=tail_mark)

    # The head, as awake
    head = ellipse(20, 15.5 + hy, 12.5, 10) | ellipse(20, 19 + hy, 14, 7)
    ear_points = (((7.5, 12), (9.5, 0.5), (17, 7)), ((32.5, 12), (30.5, 0.5), (23, 7)))
    ears = set()
    for tri in ear_points:
        ears |= polygon([(x, y + hy) for (x, y) in tri])
    img.part(head | ears, FUR, FUR_SHADOW, FUR_LIGHT, mark=marker("head"))
    for tri in ear_points:
        (ax, ay), (bx, by), (cx, cy) = tri
        mx, my = (ax + bx + cx) / 3, (ay + by + cy) / 3
        inner = [(mx + (px - mx) * 0.5, my + (py - my) * 0.5 + hy + 0.8) for (px, py) in tri]
        for (x, y) in polygon(inner):
            img.set(x, y, "P")
    img.part(ellipse(20, 21.5 + hy, 5.6, 3.8), WHITE, WHITE_SHADOW, outline=False)
    for ex in (12, 24):
        img.pattern(ex, 13 + hy, EYES["blink"])
    img.set(19, 19 + hy, "P")
    img.set(20, 19 + hy, "P")
    img.pattern(17, 20 + hy, MOUTHS["neutral"])

    # The front paws, under the chin
    for px in (13, 27):
        img.part(ellipse(px, 37, 3.4, 2.2), WHITE, WHITE_SHADOW)
    return img.rows()


def back_zone(rows):
    """Zone of the back that rises to breathe: the top rim of the body, right of the head."""
    x0, x1 = 34, 56
    top = min(y for y, row in enumerate(rows) for x in range(x0, x1) if row[x] != ".")
    return (x0, top - 1, x1 - x0, 6)


def sleep_module(coat):
    cat = draw_sleeping(coat)
    zx, zy, zw, zh = back_zone(cat)
    breath = ((zx, zy, zw, zh),
              (None, (zx + 4, zy, zw - 8, zh, 0, -1), (zx, zy, zw, zh, 0, -1)),
              ((0, 1900), (1, 1300), (2, 1700), (1, 1300)))
    ex, ey, ew, eh = EAR_TIP
    tail_tip = (27, 37, 6, 5)
    tx, ty, tw, th = tail_tip
    twitches = (
        (EAR_TIP, (None, (ex, ey, ew, eh, 1, 0), (ex, ey, ew, eh, -1, 0), (ex, ey, ew, eh, 0, 1)),
         (8000, 75000), 3, (150, 550)),
        (tail_tip, (None, (tx, ty, 3, th, -1, 0), (tx, ty, tw, th, -1, 0), (tx, ty, tw, th, 0, -1)),
         (12000, 120000), 4, (250, 800)),
    )
    zzz = (CAT_X + 30, -18, 16, 26)
    return draw_cushion(), cat, breath, twitches, zzz


def render_sleep_module(coat):
    cushion, cat, breath, twitches, zzz = sleep_module(coat)
    out = []
    out.append("# Generated by tools/build_sprites.py from the %r coat: do not edit by hand." % coat)
    out.append("# The cat asleep on its cushion. Layers are drawn in order, '.' is transparent;")
    out.append("# the cushion uses the codes 0-4, coloured by each character (\"cushion\").")
    out.append("")
    out.append("W = %d" % SLEEP_W)
    out.append("H = %d" % SLEEP_H)
    out.append("")
    for name, rows in (("CUSHION", cushion), ("CAT", cat)):
        out.append("%s = (" % name)
        for r in rows:
            out.append("    %r," % r)
        out.append(")")
        out.append("")
    out.append("CAT_LAYER = 1")
    out.append("LAYERS = ((0, %d, CUSHION), (%d, 0, CAT))" % (CUSHION_Y, CAT_X))
    out.append("")
    out.append("# Breathing: a zone of the cat layer moved by one pixel. (zone, shifts, timing);")
    out.append("# zone (x, y, w, h) relative to the cat layer, a shift is None or (x, y, w, h, dx, dy).")
    out.append("BREATH = %r" % (breath,))
    out.append("")
    out.append("# Ear and tail, at random: (zone, shifts, (pause ms), flicks at most, (flick ms)).")
    out.append("TWITCHES = (")
    for t in twitches:
        out.append("    %r," % (t,))
    out.append(")")
    out.append("")
    out.append("# Where the zZZ rise, relative to the sprite: (x, y, w, h).")
    out.append("ZZZ = %r" % (zzz,))
    out.append("")
    return "\n".join(out)


RUN_ORIGIN = 48      # a run is three bytes: 48 + x, 48 + width, colour code (printable)


def runs_of(row):
    """A row as its runs of the same colour, transparent ones left out, encoded as text."""
    out = []
    x = 0
    n = len(row)
    while x < n:
        c = row[x]
        end = x + 1
        while end < n and row[end] == c:
            end += 1
        if c != ".":
            out.append(chr(RUN_ORIGIN + x) + chr(RUN_ORIGIN + end - x) + c)
        x = end
    return "".join(out).encode("ascii")


def build_pose(draw, variants, default):
    """(parts, rows, runsets) of a pose. `parts` lists (part, values), the default first;
    each row is (indices of the parts that change it, runset of every combination of their
    values, numbered in mixed radix); `runsets` are the distinct encoded rows."""
    parts = tuple((g, (default[g],) + tuple(v for v in variants[g] if v != default[g])) for g in variants)
    images = {}

    def image(**v):
        key = tuple(sorted(v.items()))
        if key not in images:
            images[key] = draw(**v)
        return images[key]

    base = image()
    changed_by = [set() for _ in base]
    for i, (g, values) in enumerate(parts):
        for value in values[1:]:
            other = image(**{g: value})
            for y in range(len(base)):
                if other[y] != base[y]:
                    changed_by[y].add(i)
    runsets = []
    index = {}
    rows = []
    for y in range(len(base)):
        deps = tuple(sorted(changed_by[y]))
        table = []
        for combo in itertools.product(*(parts[i][1] for i in deps)):
            runs = runs_of(image(**{parts[i][0]: v for i, v in zip(deps, combo)})[y])
            if runs not in index:
                index[runs] = len(runsets)
                runsets.append(runs)
            table.append(index[runs])
        rows.append((deps, tuple(table)))
    return parts, rows, runsets


def build_coat(coat):
    poses = [(pose, VARIANTS, DEFAULT, lambda pose=pose, **v: draw_cat(coat, pose, **v)) for pose in POSES]
    for shape, variants, default in (("side", SIDE_VARIANTS, SIDE_DEFAULT),
                                     ("crouch", CROUCH_VARIANTS, CROUCH_DEFAULT),
                                     ("bow", BOW_VARIANTS, BOW_DEFAULT)):
        name = "stand" if shape == "side" else shape
        poses.append((shape + "_r", variants, default,
                      lambda name=name, **v: draw_side(coat, name, **v)))
        poses.append((shape + "_l", variants, default,
                      lambda name=name, **v: mirror(draw_side(coat, name, **v))))
    return {pose: build_pose(draw, variants, default) for pose, variants, default, draw in poses}


def render_module(coat):
    built = build_coat(coat)
    out = []
    out.append("# Generated by tools/build_sprites.py from the %r coat: do not edit by hand." % coat)
    out.append("#")
    out.append("# The awake cat, ready to draw. For each pose:")
    out.append("#   PARTS   (part, values): the parts that change, default value first")
    out.append("#   ROWS    per row: (indices of the parts that change it, runset of each combination")
    out.append("#           of their values, numbered in mixed radix in that order)")
    out.append("#   RUNSETS the rows as runs of three bytes: %d + x, %d + width, colour code;" % (RUN_ORIGIN, RUN_ORIGIN))
    out.append("#           bytes, drawn as they are: reading them creates no object on the Presto")
    out.append("")
    out.append("W = %d" % W)
    out.append("H = %d" % H)
    out.append("")
    for name, i in (("PARTS", 0), ("ROWS", 1)):
        out.append("%s = {" % name)
        for pose, data in built.items():
            out.append("    %r: (" % pose)
            for item in data[i]:
                out.append("        %r," % (item,))
            out.append("    ),")
        out.append("}")
        out.append("")
    out.append("RUNSETS = {")
    for pose, data in built.items():
        out.append("    %r: (" % pose)
        for runs in data[2]:
            out.append("        %r," % runs)
        out.append("    ),")
    out.append("}")
    out.append("")
    return "\n".join(out)


def main():
    check = "--check" in sys.argv
    stale = []
    for name, render in (("coat", render_module), ("sleep", render_sleep_module)):
        for coat in COATS:
            path = os.path.join(OUT_DIR, "%s_%s.py" % (name, coat))
            text = render(coat)
            if check:
                try:
                    with open(path) as f:
                        if f.read() != text:
                            stale.append(path)
                except OSError:
                    stale.append(path)
            else:
                with open(path, "w") as f:
                    f.write(text)
                print("wrote", os.path.relpath(path, ROOT))
    if stale:
        print("out of date:", ", ".join(stale))
        sys.exit(1)


if __name__ == "__main__":
    main()
