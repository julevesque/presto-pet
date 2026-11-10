# Pixel images built from a base and small patches.
#
# The animals are animated the way the original Presto screen saver animated its cats: most of the image
# stays, and a few small zones change (eyes, mouth, tail, a zone of the back moved by one
# pixel to breathe). Only the rows touched by a patch are recomposed, and each row is turned
# into runs of the same colour, drawn as rectangles.


class Composite:
    def __init__(self, base, pens):
        """`base` is a tuple of strings of the same length, `pens` maps each code to a pen."""
        self.pens = pens
        self.set_base(base)

    def set_base(self, base):
        self.base = base
        self.w = len(base[0])
        self.h = len(base)
        self.rows = list(base)
        self.patches = ()
        self._runs = [None] * self.h

    def set_patches(self, patches):
        """Applies a tuple of patches (x, y, rows): '.' keeps the base, '_' makes a pixel
        transparent. Returns True when the image changed."""
        if patches == self.patches:
            return False
        touched = set()
        for _, y, rows in self.patches:
            touched.update(range(y, y + len(rows)))
        for _, y, rows in patches:
            touched.update(range(y, y + len(rows)))
        self.patches = patches
        for y in touched:
            if 0 <= y < self.h:
                self.rows[y] = self._compose(y)
                self._runs[y] = None
        return True

    def _compose(self, y):
        row = None
        for px, py, prow in self.patches:
            j = y - py
            if 0 <= j < len(prow):
                if row is None:
                    row = list(self.base[y])
                for i, c in enumerate(prow[j]):
                    if c != ".":
                        x = px + i
                        if 0 <= x < self.w:
                            row[x] = "." if c == "_" else c
        return self.base[y] if row is None else "".join(row)

    def runs(self, y):
        r = self._runs[y]
        if r is None:
            r = row_runs(self.rows[y], self.pens)
            self._runs[y] = r
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
        for y in range(y0, y1):
            sy = oy + y * scale
            for x, w, pen in self.runs(y):
                set_pen(pen)
                rectangle(ox + x * scale, sy, w * scale, scale)


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
