# Pixel art of the interface: colours, menu icons and the props of the room.
# Same format as the animals: one character per pixel, "." is transparent.

# --- Colours -----------------------------------------------------------------------------------

PALETTE = {
    "O": (52, 34, 44),      # outline
    "W": (255, 248, 236),
    "R": (232, 86, 96),
    "r": (170, 50, 66),
    "Y": (252, 206, 84),
    "y": (212, 156, 48),
    "B": (112, 172, 228),
    "b": (66, 116, 182),
    "G": (124, 204, 112),
    "g": (72, 150, 82),
    "N": (176, 116, 68),
    "n": (126, 78, 44),
    "P": (242, 152, 182),
    "p": (198, 98, 140),
    "C": (186, 226, 246),
    "K": (204, 200, 214),
}

# Frame around the room, menu bars
BAR = (58, 40, 62)
TILE = (86, 62, 90)
TILE_PRESSED = (150, 112, 150)
TILE_OFF = (62, 44, 66)
TEXT = (255, 246, 230)
TEXT_DIM = (176, 160, 176)
ACCENT = (252, 206, 84)
DANGER = (232, 86, 96)

# The room, by day and by night (when the pet sleeps, the light is off)
DAY = {
    "wall": (244, 226, 196),
    "wall_dots": (234, 212, 178),
    "floor": (204, 150, 106),
    "floor_line": (180, 128, 88),
    "skirting": (156, 104, 72),
    "frame": (156, 104, 72),
    "sky": (150, 206, 240),
    "sky_far": (190, 228, 248),
    "rug": (232, 120, 112),
    "rug_edge": (198, 86, 86),
    "text": (90, 60, 70),
}
NIGHT = {
    "wall": (44, 46, 78),
    "wall_dots": (52, 54, 88),
    "floor": (64, 54, 76),
    "floor_line": (54, 46, 66),
    "skirting": (40, 36, 56),
    "frame": (40, 36, 56),
    "sky": (22, 26, 52),
    "sky_far": (30, 34, 66),
    "rug": (98, 64, 88),
    "rug_edge": (80, 52, 74),
    "text": (200, 206, 234),
}

ZZZ = (0xC8, 0xCE, 0xEA)
ZZZ_DIM = (0x6E, 0x74, 0x96)
BUBBLE = (255, 252, 244)

# --- Menu icons, 16 x 16 ----------------------------------------------------------------------

ICONS = {
    "feed": (
        "................",
        "................",
        "................",
        "................",
        ".....nNn.nNn....",
        "...nNNnNNnNNn...",
        "..nNnNNnNNNnNn..",
        ".OOOOOOOOOOOOOO.",
        ".ORRRRRRRRRRRRO.",
        ".ORWWRRRRRRRRRO.",
        "..ORRRRRRRRRRO..",
        "..ORRRRRRRRRrO..",
        "...OrRRRRRRrO...",
        "....OOOOOOOO....",
        "................",
        "................",
    ),
    "caress": (
        "................",
        "................",
        "...OOO....OOO...",
        "..ORRRO..ORRRO..",
        ".ORWWRROORRRRRO.",
        ".ORWRRRRRRRRRRO.",
        ".ORRRRRRRRRRRRO.",
        ".ORRRRRRRRRRRrO.",
        "..ORRRRRRRRRrO..",
        "...ORRRRRRRrO...",
        "....ORRRRRrO....",
        ".....ORRRrO.....",
        "......ORrO......",
        ".......OO.......",
        "................",
        "................",
    ),
    "play": (
        "................",
        ".....OOOOO......",
        "...OOPPPPPOO....",
        "..OPPWWPPPPPO...",
        "..OPWPPPpPPPO...",
        ".OPPPPPpPPPPPO..",
        ".OPPPPpPPPPpPO..",
        ".OPPPpPPPPpPPO..",
        ".OPPpPPPPpPPPO..",
        ".OPPPPPPpPPPpO..",
        "..OPPPPPpPPpO...",
        "..OpPPPpPPppO...",
        "...OOpppppOO....",
        ".....OOOOO..p...",
        "............p.p.",
        ".............p..",
    ),
    "clean": (
        "..........OO....",
        ".........OCWO...",
        "....OO...OCCO...",
        "...OCWO...OO.OO.",
        "...OCCO.....OCWO",
        "....OO......OCCO",
        ".............OO.",
        "..OOOOOOOOOOO...",
        ".OPPPPPPPPPPPO..",
        ".OPWWPPPPPPPpO..",
        ".OPPPPPPPPPPpO..",
        ".OPPPPPPPPPPpO..",
        ".OpppppppppppO..",
        "..OOOOOOOOOOO...",
        "................",
        "................",
    ),
    "sleep": (
        "................",
        ".....OO....WWW..",
        "...OOYyO.....W..",
        "..OYYyO.....W...",
        ".OYYYyO....WWW..",
        ".OYYyO..........",
        "OYYYyO..........",
        "OYYYyO..........",
        "OYYYYyO.........",
        "OYYYYyO.........",
        "OyYYYYyOO.......",
        ".OYYYYYYyOOO....",
        ".OyYYYYYYYYyO...",
        "..OyyYYYYyyO....",
        "...OOyyyyOO.....",
        ".....OOOO.......",
    ),
    "stats": (
        "................",
        "...........OOOO.",
        "...........OGGO.",
        "......OOOO.OGGO.",
        "......OBBO.OGGO.",
        "......OBBO.OGGO.",
        ".OOOO.OBBO.OGGO.",
        ".ORRO.OBBO.OGGO.",
        ".ORRO.OBBO.OGGO.",
        ".ORRO.OBBO.OGGO.",
        ".ORRO.OBBO.OGGO.",
        ".ORrO.OBbO.OGgO.",
        ".OOOO.OOOO.OOOO.",
        "................",
        "WWWWWWWWWWWWWWWW",
        "................",
    ),
    "treat": (
        "................",
        "................",
        "................",
        ".....OOO........",
        "...OOBBbOO....O.",
        "..OBBBBBBbO.OObO",
        ".OBBBWBBBBbOBBbO",
        "OBBOBBBBBBBBBBbO",
        "ObBBBBBBBbBbBBbO",
        ".ObBBBBBbBbObbbO",
        "..ObbBBBbbO.OObO",
        "...OObbbOO....O.",
        ".....OOO........",
        "................",
        "................",
        "................",
    ),
    "energy": (
        "................",
        ".........OOOO...",
        "........OYYYO...",
        ".......OYYYO....",
        "......OYYYO.....",
        ".....OYYYOOOOO..",
        "....OYYYYYYYYO..",
        "...OOOOOYYYYO...",
        ".......OYYYO....",
        "......OYYYO.....",
        ".....OYYYO......",
        "....OYyO........",
        "....OyO.........",
        "....OO..........",
        "................",
        "................",
    ),
    "feather": (
        "...........OO...",
        "..........OPPO..",
        ".........OPPpO..",
        "........OPPpPO..",
        ".......OPPpPPO..",
        "......OPPpPPO...",
        ".....OPPpPPO....",
        ".....OPpPPO.....",
        "....OPpPPO......",
        "....OpPPO.......",
        "...OpOOO........",
        "...OnO..........",
        "..OnO...........",
        "..OnO...........",
        ".OnO............",
        ".OO.............",
    ),
}

# --- Props ------------------------------------------------------------------------------------

MESS = (
    "......O.....",
    ".....OnO....",
    "....OOnO....",
    "...ONNNnO...",
    "..OOWNNnOO..",
    ".ONNNNNNNnO.",
    ".ONWNNNNNnO.",
    ".ONNNNNNNnO.",
    "ONNNNNNNNNnO",
    "OnnnNNNNnnnO",
    ".OOOnnnnOOO.",
)

HEART = (
    ".RR.RR.",
    "RWRRRRR",
    "RRRRRRR",
    ".RRRRR.",
    "..RRR..",
    "...R...",
)

BUBBLE_SMALL = (
    ".CCC.",
    "CWCCC",
    "CCCCC",
    "CCCCC",
    ".CCC.",
)

SPARKLE = (
    "..Y..",
    "..Y..",
    "YYWYY",
    "..Y..",
    "..Y..",
)

# The feather at the end of its string, for the second toy
FEATHER = (
    "...O...",
    "..OPO..",
    ".OPPPO.",
    ".OPpPO.",
    "OPPpPPO",
    "OPPpPPO",
    "OPPpPPO",
    ".OPpPO.",
    ".OPpPO.",
    "..OpO..",
    "...O...",
    "...O...",
)
STRING = (90, 60, 70)

# Visitors at the window: a butterfly flapping its wings, a bird gliding (two frames each)
BUTTERFLY = (
    (
        "YY.....YY",
        "YYY.O.YYY",
        "YRYYOYYRY",
        ".YYYOYYY.",
        ".YY.O.YY.",
        "..Y...Y..",
    ),
    (
        "...Y.Y...",
        "...YOY...",
        "..YYOYY..",
        "...YOY...",
        "....O....",
        ".........",
    ),
)
BIRD = (
    (
        "O.......O",
        ".O.....O.",
        "..O.O.O..",
        "...OOO...",
        "....O....",
    ),
    (
        ".........",
        "...O.O...",
        "OOO.O.OOO",
        "....O....",
        ".........",
    ),
)

# The zZZ of the sleeping pet, rising letter by letter (from the original screen saver)
Z_SMALL = ("ZZZZ", "..ZZ", "ZZ..", "ZZZZ")
Z_BIG = ("ZZZZZ", "...Z.", "..Z..", ".Z...", "ZZZZZ")
Z_BURST = (Z_SMALL, Z_BIG, Z_BIG, Z_SMALL)
Z_WOBBLE = (0, 1, 2, 2, 1, 0, -1, -1)
