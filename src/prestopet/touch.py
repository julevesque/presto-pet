# Touch gestures, from raw samples of the Presto touch panel.
#
# A child taps buttons: a tap is reported when the finger is lifted, at the place where it
# first touched, so a sliding finger still hits the intended button. Holding the finger
# reports HOLD once, used where a deliberate action is required (erasing the game).

DOWN = "down"   # finger just touched: used to highlight the button under it
TAP = "tap"
HOLD = "hold"

HOLD_MS = 1500
BOUNCE_MS = 40      # a shorter lift is contact bounce: same press
MOVE_PX = 60        # a press that travels further is not a tap


class TouchTracker:
    def __init__(self, diff):
        self.diff = diff
        self.down = False
        self.held = False
        self.x = self.y = 0
        self.lx = self.ly = 0
        self.pressed_at = 0
        self.released_at = None

    def update(self, down, x, y, now):
        """Returns (event, x, y) or None."""
        if down:
            self.lx, self.ly = x, y
            if not self.down:
                self.down = True
                if self.released_at is not None and self.diff(now, self.released_at) < BOUNCE_MS:
                    self.released_at = None
                    return None  # bounce: the press goes on
                self.held = False
                self.x, self.y = x, y
                self.pressed_at = now
                return DOWN, x, y
            if not self.held and self.diff(now, self.pressed_at) >= HOLD_MS:
                self.held = True
                return HOLD, self.x, self.y
            return None
        if self.down:
            self.down = False
            self.released_at = now
            return None
        if self.released_at is not None and self.diff(now, self.released_at) >= BOUNCE_MS:
            self.released_at = None
            if self.held:
                return None
            if abs(self.lx - self.x) > MOVE_PX or abs(self.ly - self.y) > MOVE_PX:
                return None
            return TAP, self.x, self.y
        return None

    @property
    def pressed(self):
        return self.down
