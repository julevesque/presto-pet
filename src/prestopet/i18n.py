# Texts of the game. A value is either a string, or a pair (feminine, masculine) chosen
# with the gender of the pet. "%s" is the name of the pet.

TEXTS = {
    "fr": {
        "title": "Presto-Pet",
        "tap_to_start": "Touche l'écran pour commencer",
        "loading": "Chargement...",
        "choose": "Choisis ton animal",
        "adopt": "Adopter %s",
        "welcome": "Bienvenue %s !",
        "day": "Jour %d",
        "meal": "Repas",
        "treat": "Friandise",
        "play_hint": "Touche le sol pour lancer la pelote",
        "play_feather_hint": "Fais bouger la plume avec ton doigt",
        "ball": "Pelote",
        "feather": "Plume",
        "play_end": "Merci pour le jeu !",
        "reunion": ("%s est contente de te revoir !", "%s est content de te revoir !"),
        "r_asleep": ("Chut, elle dort...", "Chut, il dort..."),
        "r_eat": "Miam !",
        "r_treat": "Une friandise !",
        "r_full": "Plus faim !",
        "r_purr": "Ronron...",
        "r_purr_asleep": "Ronron... zzz",
        "r_play": "Youpi !",
        "r_play_sulky": "Bof...",
        "r_too_tired": ("Trop fatiguée pour jouer", "Trop fatigué pour jouer"),
        "r_clean": ("Toute propre !", "Tout propre !"),
        "r_already_clean": ("Déjà toute propre !", "Déjà tout propre !"),
        "r_go_to_bed": "Bonne nuit !",
        "r_not_sleepy": "Pas sommeil !",
        "r_wake": "Bonjour !",
        "r_too_sleepy": "Encore cinq minutes...",
        "fell_asleep": ("%s s'est endormie", "%s s'est endormi"),
        "woke_up": ("%s est réveillée", "%s est réveillé"),
        "stat_satiety": "Repas",
        "stat_happiness": "Bonheur",
        "stat_energy": "Énergie",
        "stat_hygiene": "Propreté",
        "mood": "Humeur : %s",
        "mood_happy": ("Très heureuse", "Très heureux"),
        "mood_content": ("Contente", "Content"),
        "mood_hungry": "A faim",
        "mood_tired": ("Fatiguée", "Fatigué"),
        "mood_dirty": "Veut un brossage",
        "mood_sulky": "Boude un peu",
        "mood_asleep": "Dort",
        "counts": "Repas %d · Câlins %d · Jeux %d",
        "clock_unknown": "Heure inconnue : le temps hors ligne sera compté plus tard",
        "back": "Retour",
        "new_game": "Recommencer",
        "options": "Options",
        "brightness": "Luminosité",
        "bright_low": "Minimum",
        "bright_medium": "Moyen",
        "bright_high": "Maximum",
        "nap_after": "Sieste après",
        "nap_hint": ("sans câlin, elle se met en boule", "sans câlin, il se met en boule"),
        "minutes": "%d min",
        "hours": "%d h",
        "language": "Langue",
        "reset_title": "Nouvelle partie ?",
        "reset_text": "Toute la progression de %s sera effacée.",
        "reset_hold": "Maintenir pour effacer",
        "cancel": "Annuler",
        "erase": "Effacer",
    },
    "en": {
        "title": "Presto-Pet",
        "tap_to_start": "Touch the screen to start",
        "loading": "Loading...",
        "choose": "Choose your pet",
        "adopt": "Adopt %s",
        "welcome": "Welcome %s!",
        "day": "Day %d",
        "meal": "Meal",
        "treat": "Treat",
        "play_hint": "Touch the floor to throw the ball",
        "play_feather_hint": "Move the feather with your finger",
        "ball": "Ball",
        "feather": "Feather",
        "play_end": "Thanks for playing!",
        "reunion": "%s is happy to see you again!",
        "r_asleep": "Shh, sleeping...",
        "r_eat": "Yummy!",
        "r_treat": "A treat!",
        "r_full": "Not hungry!",
        "r_purr": "Purr...",
        "r_purr_asleep": "Purr... zzz",
        "r_play": "Yay!",
        "r_play_sulky": "Meh...",
        "r_too_tired": "Too tired to play",
        "r_clean": "All clean!",
        "r_already_clean": "Already clean!",
        "r_go_to_bed": "Good night!",
        "r_not_sleepy": "Not sleepy!",
        "r_wake": "Good morning!",
        "r_too_sleepy": "Five more minutes...",
        "fell_asleep": "%s fell asleep",
        "woke_up": "%s woke up",
        "stat_satiety": "Food",
        "stat_happiness": "Happiness",
        "stat_energy": "Energy",
        "stat_hygiene": "Cleanliness",
        "mood": "Mood: %s",
        "mood_happy": "Very happy",
        "mood_content": "Content",
        "mood_hungry": "Hungry",
        "mood_tired": "Tired",
        "mood_dirty": "Wants a brush",
        "mood_sulky": "Sulking a bit",
        "mood_asleep": "Asleep",
        "counts": "Meals %d · Cuddles %d · Games %d",
        "clock_unknown": "Unknown time: offline time will be counted later",
        "back": "Back",
        "new_game": "Start over",
        "options": "Options",
        "brightness": "Brightness",
        "bright_low": "Low",
        "bright_medium": "Medium",
        "bright_high": "High",
        "nap_after": "Nap after",
        "nap_hint": ("with no touch, she curls up", "with no touch, he curls up"),
        "minutes": "%d min",
        "hours": "%d h",
        "language": "Language",
        "reset_title": "New game?",
        "reset_text": "All of %s's progress will be erased.",
        "reset_hold": "Hold to erase",
        "cancel": "Cancel",
        "erase": "Erase",
    },
}


# Each language is named in itself on the Options screen.
LANGUAGE_NAMES = {"fr": "Français", "en": "English"}


class Texts:
    def __init__(self, lang="fr"):
        self.table = TEXTS.get(lang) or TEXTS["en"]
        self.fallback = TEXTS["en"]
        self.gender = "f"
        self.name = ""

    def set_pet(self, name, gender):
        self.name = name
        self.gender = gender

    def get(self, key, *args):
        value = self.table.get(key)
        if value is None:
            value = self.fallback.get(key, key)
        if isinstance(value, tuple):
            value = value[0] if self.gender == "f" else value[1]
        if "%" in value:
            if not args:
                args = (self.name,)
            try:
                return value % args
            except TypeError:
                return value
        return value
