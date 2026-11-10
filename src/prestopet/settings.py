# Player settings (brightness, nap delay, language), changed in the Options screen. They live in their own small file, so
# starting a new game keeps them. The file is written only when a setting changes.

import json
import os

FILE_NAME = "prestopet_settings.json"

# Levels passed to presto.set_backlight(): small values are already bright on the Presto.
BRIGHTNESS = {"low": 0.01, "medium": 0.2, "high": 1.0}
BRIGHTNESS_LEVELS = ("low", "medium", "high")
LED_LEVEL = {"low": 0.8, "medium": 0.9, "high": 1.0}   # the LEDs follow the brightness

# Languages of the game, chosen in the Options; config.LANGUAGE is only the first default.
LANGUAGES = ("fr", "en")

# Minutes without a touch before the pet curls up for a nap.
NAP_MINUTES = (5, 15, 60)

DEFAULTS = {"brightness": "low", "nap_minutes": 15}


def path_next_to(save_file):
    """The settings file in the same folder as the save file."""
    i = save_file.rfind("/")
    return save_file[:i + 1] + FILE_NAME


class Settings:
    def __init__(self, path=FILE_NAME, language="fr"):
        self.path = path
        self.language = language if language in LANGUAGES else "fr"
        self.brightness = DEFAULTS["brightness"]
        self.nap_minutes = DEFAULTS["nap_minutes"]

    def load(self):
        data = None
        for path in (self.path, self.path + ".tmp"):   # .tmp: power cut during save()
            try:
                with open(path) as f:
                    data = json.load(f)
                break
            except (OSError, ValueError):
                pass
        if not isinstance(data, dict):
            return
        if data.get("brightness") in BRIGHTNESS:
            self.brightness = data["brightness"]
        if data.get("nap_minutes") in NAP_MINUTES:
            self.nap_minutes = data["nap_minutes"]
        if data.get("language") in LANGUAGES:
            self.language = data["language"]

    def save(self):
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump({"brightness": self.brightness, "nap_minutes": self.nap_minutes,
                           "language": self.language}, f)
            try:
                os.remove(self.path)
            except OSError:
                pass
            os.rename(tmp, self.path)
            return True
        except OSError as e:
            print("Settings not saved:", repr(e))
            return False

    @property
    def backlight(self):
        return BRIGHTNESS[self.brightness]

    @property
    def led_level(self):
        return LED_LEVEL[self.brightness]

    @property
    def nap_ms(self):
        return self.nap_minutes * 60000
