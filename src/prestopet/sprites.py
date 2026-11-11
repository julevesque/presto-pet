# Pixel images drawn as runs of the same colour, one rectangle each.
#
# Composite: a base and small patches, the way the original Presto screen saver animated its
# cats: most of the image stays, and a few small zones change (a zone of the back moved by
# one pixel to breathe). Used for the sleeping pet, the icons and the props.
#
# Frames: the awake pet, which changes much more (walking, hopping, pouncing). On the Presto,
# creating objects is slow (composing a frame took up to 300 ms), so its rows come ready to
# draw from tables generated on the computer.


FRAME_CACHE = 128    # composed frames kept per image: lists of rows, the rows are shared

_segments = {}       # patch -> per row, [(x, text)] of the pixels it sets


def _patch_segments(patch):
    """A patch as pieces of text to paste: composing a row is then a few slices, much faster
    in MicroPython than going through it pixel by pixel."""
    segs = _segments.get(patch)
    if segs is None:
        px, _, prows = patch
        segs = []
        for prow in prows:
            row = []
            i = 0
            n = len(prow)
            while i < n:
                if prow[i] == ".":
                    i += 1
                    continue
                j = i
                while j < n and prow[j] != ".":
                    j += 1
                row.append((px + i, prow[i:j].replace("_", ".")))
                i = j
            segs.append(row)
        _segments[patch] = segs
    return segs


class Composite:
    def __init__(self, base, pens):
        """`base` is a tuple of strings of the same length, `pens` maps each code to a pen."""
        self.pens = pens
        # Composing rows and cutting them into runs is slow in MicroPython, and an animation
        # keeps showing the same frames (the breathing...): both are kept.
        self._frames = {}        # (id(base), patches) -> (base, rows)
        self._row_runs = {}      # row -> runs, shared by every frame
        self.set_base(base)

    def set_base(self, base):
        self.base = base
        self.w = len(base[0])
        self.h = len(base)
        self.patches = ()
        self.rows = list(base)

    def set_patches(self, patches):
        """Applies a tuple of patches (x, y, rows): '.' keeps the base, '_' makes a pixel
        transparent. Returns True when the image changed."""
        if patches == self.patches:
            return False
        rows = self._cached(self.base, patches)
        if rows is None:
            rows = self._frame(self.base, patches)
        self.patches = patches
        self.rows = rows
        return True

    def _cached(self, base, patches):
        entry = self._frames.get((id(base), patches))
        return entry[1] if entry is not None and entry[0] is base else None

    def _frame(self, base, patches):
        rows = list(base)
        for patch in patches:
            y0 = patch[1]
            for j, segs in enumerate(_patch_segments(patch)):
                y = y0 + j
                if segs and 0 <= y < len(rows):
                    # One join per row: each new string is costly on the Presto
                    row = rows[y]
                    pieces = []
                    pos = 0
                    for x, text in segs:
                        pieces.append(row[pos:x])
                        pieces.append(text)
                        pos = x + len(text)
                    pieces.append(row[pos:])
                    rows[y] = "".join(pieces)
        if len(self._frames) >= FRAME_CACHE:
            self._frames = {}
        self._frames[(id(base), patches)] = (base, rows)
        return rows

    def runs(self, y):
        row = self.rows[y]
        r = self._row_runs.get(row)
        if r is None:
            r = row_runs(row, self.pens)
            self._row_runs[row] = r
        return r

    def draw(self, display, ox, oy, scale, clip=None):
        """Draws at (ox, oy) in screen pixels. `clip` (x, y, w, h) skips the rows outside it;
        the display clip does the rest."""
        y0 = 0
        y1 = self.h
        if clip is not None:
            top = (clip[1] - oy) // scale
            bottom = (clip[1] + clip[3] - oy + scale - 1) // scale
            if top > y0:
                y0 = top
            if bottom < y1:
                y1 = bottom
        set_pen = display.set_pen
        rectangle = display.rectangle
        last = None
        for y in range(y0, y1):
            sy = oy + y * scale
            for x, w, pen in self.runs(y):
                if pen != last:
                    set_pen(pen)
                    last = pen
                rectangle(ox + x * scale, sy, w * scale, scale)


class Frames:
    """The awake pet, from tables generated on the computer (see tools/build_sprites.py): a
    frame is a pose and the value of each part, and each of its rows is found in a table as
    bytes, drawn as they are. Nothing is composed or decoded on the Presto, where creating
    objects is slow: a new frame costs a few lookups, then it is kept."""

    def __init__(self, coat, pens):
        self.coat = coat
        self.pens = pens
        self._pens = {ord(code): pen for code, pen in pens.items()}
        self.w = coat.W
        self.h = coat.H
        self.key = None
        self.rows = None
        self._frames = {}        # (pose, variants) -> rows
        self._parts = {}         # pose -> ([part], [{value: index}], [count])
        self.set_frame("sit", ())

    def set_frame(self, pose, variants):
        """`variants`: ((part, value), ...); missing parts and unknown values take the
        default. Returns True when the image changed."""
        key = (pose, variants)
        if key == self.key:
            return False
        rows = self._frames.get(key)
        if rows is None:
            rows = self._frame(pose, variants)
        # Another key can give the same image (a part that does not show in this pose)
        changed = self.rows is None or rows != self.rows
        self.key = key
        self.rows = rows
        return changed

    def _frame(self, pose, variants):
        parts = self._parts.get(pose)
        if parts is None:
            names = [p for p, _ in self.coat.PARTS[pose]]
            index = [{v: i for i, v in enumerate(values)} for _, values in self.coat.PARTS[pose]]
            counts = [len(values) for _, values in self.coat.PARTS[pose]]
            parts = (names, index, counts)
            self._parts[pose] = parts
        names, index, counts = parts
        choice = [0] * len(names)
        for part, value in variants:
            if part in names:
                i = names.index(part)
                choice[i] = index[i].get(value, 0)
        runsets = self.coat.RUNSETS[pose]
        rows = []
        for deps, table in self.coat.ROWS[pose]:
            k = 0
            for i in deps:
                k = k * counts[i] + choice[i]
            rows.append(runsets[table[k]])
        if len(self._frames) >= FRAME_CACHE:
            self._frames = {}
        self._frames[(pose, variants)] = rows
        return rows

    def runs(self, y):
        """The runs of a row as (x, width, pen), as Composite gives them (for the tests)."""
        t = self.rows[y]
        return [(t[j] - 48, t[j + 1] - 48, self._pens[t[j + 2]]) for j in range(0, len(t), 3)]

    def draw(self, display, ox, oy, scale, clip=None):
        y0 = 0
        y1 = self.h
        if clip is not None:
            top = (clip[1] - oy) // scale
            bottom = (clip[1] + clip[3] - oy + scale - 1) // scale
            if top > y0:
                y0 = top
            if bottom < y1:
                y1 = bottom
        set_pen = display.set_pen
        rectangle = display.rectangle
        pens = self._pens
        bx = ox - 48 * scale
        last = None
        for y in range(y0, y1):
            t = self.rows[y]
            sy = oy + y * scale
            for j in range(0, len(t), 3):
                pen = pens[t[j + 2]]
                if pen != last:
                    set_pen(pen)
                    last = pen
                rectangle(bx + t[j] * scale, sy, (t[j + 1] - 48) * scale, scale)


def row_runs(row, pens):
    runs = []
    n = len(row)
    x = 0
    while x < n:
        c = row[x]
        end = x + 1
        while end < n and row[end] == c:
            end += 1
        if c != ".":
            runs.append((x, end - x, pens[c]))
        x = end
    return runs


def flatten(w, h, layers):
    """Merges layers (x, y, rows), drawn in order, into one image of w x h."""
    grid = [["."] * w for _ in range(h)]
    for ox, oy, rows in layers:
        for j, row in enumerate(rows):
            line = grid[oy + j]
            for i, c in enumerate(row):
                if c != ".":
                    line[ox + i] = c
    return tuple("".join(r) for r in grid)


def shifted_patch(w, h, layers, target, zone, shift):
    """Patch for `zone` (x, y, w, h) of layer `target` with a sub-zone moved by (dx, dy):
    shift = (x, y, w, h, dx, dy), relative to the layer. Same technique as the original
    screen saver, which breathes by lifting the back by one pixel."""
    lx, ly, _ = layers[target]
    zx, zy, zw, zh = zone
    rows = []
    for y in range(ly + zy, ly + zy + zh):
        row = []
        for x in range(lx + zx, lx + zx + zw):
            c = "."
            for i in range(len(layers) - 1, -1, -1):
                ox, oy, lrows = layers[i]
                sx = x - ox
                sy = y - oy
                if i == target and shift[0] <= sx < shift[0] + shift[2] and shift[1] <= sy < shift[1] + shift[3]:
                    sx -= shift[4]
                    sy -= shift[5]
                if 0 <= sy < len(lrows) and 0 <= sx < len(lrows[0]):
                    v = lrows[sy][sx]
                    if v != ".":
                        c = v
                        break
            row.append("_" if c == "." else c)
        rows.append("".join(row))
    return (lx + zx, ly + zy, tuple(rows))
