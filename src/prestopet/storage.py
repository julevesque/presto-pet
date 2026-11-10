# Saving the game on the Presto flash.
#
# - One save file, written atomically: the new content goes to a temporary file, then the
#   previous save becomes the backup and the temporary file takes its place. A power cut at
#   any moment leaves at least one complete save.
# - SavePolicy limits flash writes: actions are grouped, and the state is otherwise written
#   every few minutes. Losing the last minutes is harmless: on restart, the elapsed time is
#   simulated again from the saved timestamp.

import json
import os

SAVE_FILE = "prestopet_save.json"


def _exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def _remove(path):
    try:
        os.remove(path)
    except OSError:
        pass


class Storage:
    def __init__(self, path=SAVE_FILE):
        self.path = path
        self.tmp = path + ".tmp"
        self.bak = path + ".bak"

    def load(self):
        """The saved game as a dict, or None. Falls back on the temporary file (power cut
        between the two renames) then on the backup (damaged save)."""
        for path in (self.path, self.tmp, self.bak):
            try:
                with open(path) as f:
                    data = json.load(f)
            except (OSError, ValueError):
                continue
            if isinstance(data, dict) and isinstance(data.get("pet"), dict):
                return data
        return None

    def save(self, data):
        """Returns True when the game is safely written."""
        try:
            with open(self.tmp, "w") as f:
                json.dump(data, f)
            if _exists(self.path):
                _remove(self.bak)
                os.rename(self.path, self.bak)
            os.rename(self.tmp, self.path)
            return True
        except OSError as e:
            print("Save failed:", repr(e))
            return False

    def erase(self):
        for path in (self.path, self.tmp, self.bak):
            _remove(path)

    def exists(self):
        return self.load() is not None


class SavePolicy:
    """Decides when to write. Times are in milliseconds from any monotonic source; `diff`
    is ticks_diff on MicroPython."""

    def __init__(self, now, diff, periodic_ms=600000, debounce_ms=15000):
        self.diff = diff
        self.periodic_ms = periodic_ms
        self.debounce_ms = debounce_ms
        self.last = now
        self.pending_since = None
        self.urgent = False

    def mark(self, now, urgent=False):
        """Something worth saving happened. Urgent changes (new game, falling asleep) are
        written at the next check; others wait a little so a burst of taps costs one write."""
        if self.pending_since is None:
            self.pending_since = now
        if urgent:
            self.urgent = True

    def due(self, now):
        if self.urgent:
            return True
        if self.pending_since is not None and self.diff(now, self.pending_since) >= self.debounce_ms:
            return True
        return self.diff(now, self.last) >= self.periodic_ms

    def done(self, now):
        self.last = now
        self.pending_since = None
        self.urgent = False
