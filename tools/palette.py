"""Shared palette for Blood at Sundown. Single source of truth.

gen_pixel_art.py writes it to assets/palette.png (32 x 2): row 0 is the palette at
sun_t = 0 (gold dusk), row 1 at sun_t = 1 (deep red). Only the eight SWAP entries differ
between the rows; pixel_art.gd loads the image and blends those entries per duel, so every
frame uses exactly 32 colours.
"""

def hx(s):
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))

# Order matters: pixel_art.gd names these indices.
FIXED = [
    ("INK",        "1b1022"),  # outlines, deepest shadow
    ("CHARCOAL",   "2d2030"),
    ("PLUM",       "4a2843"),
    ("PLUM_LIGHT", "6e3a55"),
    ("WINE",       "5e121c"),  # old blood
    ("BLOOD",      "a3161f"),
    ("RED",        "dc2f2a"),  # fresh blood, primary button
    ("ORANGE",     "d8662e"),
    ("GOLD",       "f0a441"),  # lamps, mustard stripes
    ("CREAM",      "f3e2bd"),  # type, shirts, fringe
    ("BROWN_DARK", "3a2217"),
    ("BROWN",      "5b3620"),
    ("LEATHER",    "86532d"),
    ("OCHRE",      "b3793c"),
    ("TAN",        "d4a266"),
    ("SKIN_LIGHT", "e8b98a"),
    ("SKIN",       "bf7f56"),
    ("SKIN_DARK",  "85503a"),
    ("TEAL_DARK",  "1d3b40"),
    ("TEAL",       "2b6563"),
    ("TEAL_LIGHT", "4f8f86"),
    ("SLATE",      "384868"),  # cool shadow, blue cloth
    ("GREY",       "7a7a92"),
    ("SILVER",     "c4bdb8"),  # gun metal highlight
]

# Swappable ramps: (name, gold dusk, deep red dusk)
SWAP = [
    ("SKY_TOP",  "5c3a6c", "2a1430"),
    ("SKY_HIGH", "a24c68", "5c1a34"),
    ("SKY_MID",  "dc6e48", "9c2a2c"),
    ("SKY_LOW",  "f0a050", "c8402c"),
    ("HORIZON",  "f8c870", "e26a36"),
    ("SUN",      "fff0b4", "f8b060"),
    ("RIM",      "f8c060", "ec7440"),
    ("DUST",     "e2b27a", "b8805a"),
]

NAMES = [n for n, _ in FIXED] + [n for n, _, _ in SWAP]
IDX = {n: i for i, n in enumerate(NAMES)}


def row(t):
    """Palette as a list of RGB tuples at sun_t = t (0 or 1 for the file)."""
    out = [hx(c) for _, c in FIXED]
    for _, a, b in SWAP:
        ca, cb = hx(a), hx(b)
        out.append(tuple(round(ca[i] + (cb[i] - ca[i]) * t) for i in range(3)))
    return out


def rgb(name, t=0.0):
    return row(t)[IDX[name]]


def all_colours():
    return set(row(0.0)) | set(row(1.0))
