# Presto-Pet settings. Edit, then copy this file to the Presto next to main.py.

# Language of the game at first start: "fr" or "en". It can then be changed in the game
# (Statistics, then Options); that choice is kept and wins over this line.
LANGUAGE = "fr"

# Local time, used for the pet's nights (21:00 to 07:00) once the clock is known.
# Offset from UTC in minutes, and whether European summer time applies.
UTC_OFFSET_MINUTES = 60
EU_SUMMER_TIME = True

# Brightness and the nap delay are chosen in the game: Statistics, then Options.

# The screen goes dark after this many minutes without touch (0: never, the default: the
# napping pet is the screen saver). The pet keeps living; a touch lights the screen again.
SCREEN_OFF_MINUTES = 0

# Save file on the Presto flash.
SAVE_FILE = "prestopet_save.json"

# Optional: NTP server used when Wi-Fi is configured in secrets.py.
NTP_HOST = None
