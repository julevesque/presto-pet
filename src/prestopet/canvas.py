# Drawing on the Presto screen with PicoGraphics: rectangles only, for crisp pixels.
#
# The screen is redrawn by regions: a region is cleared, drawn again, then only that
# rectangle is sent to the panel with partial_update when the firmware offers it (as in
# the screen saver the sleeping cats come from). Without partial_update, the whole frame is sent once per flush.

from prestopet import font
from prestopet.sprites import Composite

W = 480
H = 480

LEFT = 0
CENTER = 1
RIGHT = 2


def intersects(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def union(a, b):
    x = min(a[0], b[0])
    y = min(a[1], b[1])
    return (x, y, max(a[0] + a[2], b[0] + b[2]) - x, max(a[1] + a[3], b[1] + b[3]) - y)


def clamp_rect(r):
    x = max(0, r[0])
    y = max(0, r[1])
    x2 = min(W, r[0] + r[2])
    y2 = min(H, r[1] + r[3])
    if x2 <= x or y2 <= y:
        return None
    return (x, y, x2 - x, y2 - y)


class Canvas:
    def __init__(self, display, presto):
        self.d = display
        self.presto = presto
        self.partial = hasattr(presto, "partial_update")
        self._pens = {}
        self._art = {}
        self._dirty = []
        self._full = False

    # --- Colours and shapes -------------------------------------------------------------------

    def pen(self, rgb):
        p = self._pens.get(rgb)
        if p is None:
            p = self.d.create_pen(rgb[0], rgb[1], rgb[2])
            self._pens[rgb] = p
        return p

    def pens(self, palette):
        return {code: self.pen(rgb) for code, rgb in palette.items()}

    def rect(self, x, y, w, h, rgb):
        self.d.set_pen(self.pen(rgb))
        self.d.rectangle(int(x), int(y), int(w), int(h))

    def rounded(self, x, y, w, h, rgb, r=4):
        """A rectangle with stepped pixel corners."""
        self.d.set_pen(self.pen(rgb))
        rect = self.d.rectangle
        rect(x + r, y, w - 2 * r, h)
        rect(x, y + r, w, h - 2 * r)
        half = r // 2
        rect(x + half, y + half, w - 2 * half, h - 2 * half)

    def panel(self, x, y, w, h, fill, border, r=8):
        self.rounded(x, y, w, h, border, r)
        self.rounded(x + 4, y + 4, w - 8, h - 8, fill, max(2, r - 4))

    def clip(self, r):
        self.d.set_clip(r[0], r[1], r[2], r[3])

    def unclip(self):
        self.d.remove_clip()

    # --- Pixel art ----------------------------------------------------------------------------

    def art(self, rows, x, y, scale, palette, clip=None):
        """Draws a small static image (icon, prop). Its runs are cached."""
        key = (id(rows), id(palette))
        comp = self._art.get(key)
        if comp is None:
            comp = Composite(rows, self.pens(palette))
            self._art[key] = comp
        comp.draw(self.d, int(x), int(y), scale, clip)

    # --- Text ---------------------------------------------------------------------------------

    def text(self, text, x, y, scale, rgb, align=LEFT):
        """Writes `text` with the top of the capitals at y. Returns its width."""
        w = font.width(text, scale)
        if align == CENTER:
            x -= w // 2
        elif align == RIGHT:
            x -= w
        self.d.set_pen(self.pen(rgb))
        rect = self.d.rectangle
        cx = x
        for c in text:
            gw, runs = font.glyph(c)
            for gx, gy, rw in runs:
                rect(cx + gx * scale, y + gy * scale, rw * scale, scale)
            cx += (gw + font.SPACING) * scale
        return w

    def paragraph(self, text, x, y, max_width, scale, rgb, align=LEFT, spacing=None):
        """Wrapped text. Returns the y below the last line."""
        step = spacing or (font.LINE - 1) * scale
        for line in font.wrap(text, max_width, scale):
            self.text(line, x, y, scale, rgb, align)
            y += step
        return y

    # --- Sending to the panel -----------------------------------------------------------------

    def invalidate(self, r):
        """Marks a region to send at the next present()."""
        r = clamp_rect(r)
        if r is None:
            return
        for i, d in enumerate(self._dirty):
            if intersects(d, r):
                self._dirty[i] = union(d, r)
                return
        self._dirty.append(r)

    def full(self):
        self._full = True
        self._dirty = []

    def present(self):
        if self._full or (self._dirty and not self.partial):
            self.presto.update()
        else:
            for r in self._dirty:
                self.presto.partial_update(r[0], r[1], r[2], r[3])
        self._full = False
        self._dirty = []
