# Croquette, a grey-brown tabby and white cat.

CHARACTER = {
    "id": "croquette",
    "name": "Croquette",
    "gender": "f",
    "species": "cat",
    # Food-loving and lively: loves treats and games, gets hungry and tired a little faster.
    "personality": {"treat_happiness": 1.3, "play_happiness": 1.25, "satiety_awake": 1.1,
                    "energy_awake": 1.1},
    "coat": "tabby",
    "palette": {
        "O": (72, 40, 44),
        "B": (170, 150, 124),
        "b": (140, 120, 100),
        "L": (198, 180, 150),
        "S": (92, 76, 64),
        "W": (255, 251, 241),
        "w": (226, 218, 214),
        "P": (232, 140, 146),
        "p": (150, 60, 70),
        "E": (140, 184, 90),
        "e": (30, 26, 24),
        "K": (255, 255, 255),
    },
    # Colours of the cushion of the sleeping art: outline, top light, top, side, side shadow
    "cushion": {
        "0": (36, 44, 72),
        "1": (150, 180, 204),
        "2": (112, 144, 178),
        "3": (84, 114, 150),
        "4": (62, 86, 122),
    },
    "traits": {"fr": "Gourmande et pleine d'énergie", "en": "Food-loving and full of energy"},
}
