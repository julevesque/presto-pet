"""Generates the cat sprites from simple shapes, awake and asleep.

    python3 tools/build_sprites.py            # writes src/prestopet/pets/coat_*.py, sleep_*.py
    python3 tools/build_sprites.py --check    # fails if the committed files are out of date

The cat is drawn in semantic colour codes, so every character with the same coat shares the
art and only brings its palette (see src/prestopet/pets/). A coat is the pattern of the fur:
"tuxedo" (black and white, like Louna) or "tabby" (striped, like Croquette).

For each pose, the generator draws a base image, then each variant (eyes, mouth, ears, tail,
paws) and keeps only the pixels that differ: on the Presto, a frame is the base with a few
small patches on top.

Codes:  O outline   B fur   b fur shadow   L fur light   S stripe
        W white fur   w white shadow   P pink   p mouth   E iris   e pupil   K eye shine
"""

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


def diff(base, other):
    """The pixels of `other` that differ from `base`, as (x, y, rows) with '.' for unchanged.
    Pixels that become transparent are written as '_'."""
    cells = [(x, y) for y in range(H) for x in range(W) if base[y][x] != other[y][x]]
    if not cells:
        return None
    x0 = min(x for x, _ in cells)
    x1 = max(x for x, _ in cells)
    y0 = min(y for _, y in cells)
    y1 = max(y for _, y in cells)
    rows = []
    for y in range(y0, y1 + 1):
        row = ""
        for x in range(x0, x1 + 1):
            if base[y][x] == other[y][x]:
                row += "."
            else:
                row += "_" if other[y][x] == "." else other[y][x]
        rows.append(row)
    return (x0, y0, tuple(rows))


def build_coat(coat):
    poses = {}
    patches = {}
    for pose in POSES:
        base = draw_cat(coat, pose)
        poses[pose] = tuple(base)
        for group, values in VARIANTS.items():
            for value in values:
                if value == DEFAULT[group]:
                    continue
                d = diff(base, draw_cat(coat, pose, **{group: value}))
                if d is not None:
                    patches[(pose, group, value)] = d
    return poses, patches


def render_module(coat):
    poses, patches = build_coat(coat)
    out = []
    out.append("# Generated by tools/build_sprites.py from the %r coat: do not edit by hand." % coat)
    out.append("# A frame is a pose with patches on top; '.' keeps the pixel below, '_' clears it.")
    out.append("")
    out.append("W = %d" % W)
    out.append("H = %d" % H)
    out.append("")
    out.append("POSES = {")
    for pose, rows in poses.items():
        out.append("    %r: (" % pose)
        for r in rows:
            out.append("        %r," % r)
        out.append("    ),")
    out.append("}")
    out.append("")
    out.append("# (pose, part, variant): (x, y, rows)")
    out.append("PATCHES = {")
    for key, (x, y, rows) in patches.items():
        out.append("    %r: (%d, %d, (" % (key, x, y))
        for r in rows:
            out.append("        %r," % r)
        out.append("    )),")
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
