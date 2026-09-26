"""Shared palette for Blood at Sundown. Single source of truth.

gen_pixel_art.py writes it to assets/palette.png (64 x 2): row 0 is the palette at
sun_t = 0 (gold dusk), row 1 at sun_t = 1 (deep red). Only the 16 SWAP entries differ
between the rows; pixel_art.gd loads the image and blends those entries per duel, so the
master palette is always exactly 64 colours (DESIGN.md section 15).
"""

def hx(s):
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))

# Order matters: pixel_art.gd names these indices.
FIXED = [
    # ink and shadow
    ("INK",         "1f0e16"), ("CHARCOAL",   "2d2030"), ("SHADOW",     "3b2a3e"),
    ("PLUM",        "4a2843"), ("PLUM_LIGHT", "6e3a55"), ("MAUVE",      "8f5068"),
    # blood and reds
    ("WINE_DARK",   "3e0c14"), ("WINE",       "5e121c"), ("MAROON",     "7c1a24"),
    ("BLOOD",       "a3161f"), ("RED",        "dc2f2a"), ("RED_LIGHT",  "f0604a"),
    # oranges, golds, lamp light
    ("RUST",        "9a3a22"), ("ORANGE",     "d8662e"), ("AMBER",      "ea8c3a"),
    ("GOLD",        "d49a30"), ("LAMP",       "f6c35a"), ("LAMP_HOT",   "fff0b8"),
    # creams
    ("CREAM",       "f3e2bd"), ("CREAM_SHADE", "d8c098"), ("PALE",      "fbf3dc"),
    # browns: wood, leather, ground
    ("BROWN_BLACK", "24140e"), ("BROWN_DARK", "3a2217"), ("BROWN",      "5b3620"),
    ("BROWN_MID",   "703f24"), ("LEATHER",    "874a2b"), ("OCHRE",      "b26a36"),
    ("TAN",         "d4a266"), ("SAND",       "e6be86"),
    # skin
    ("SKIN_DEEP",   "5e3526"), ("SKIN_DARK",  "85503a"), ("SKIN",       "bf7f56"),
    ("SKIN_LIGHT",  "e8b98a"),
    # teal (the poncho)
    ("TEAL_DARK",   "1d3b40"), ("TEAL",       "2b6563"), ("TEAL_LIGHT", "4f8f86"),
    ("TEAL_PALE",   "80b4a4"),
    # cool blues
    ("NAVY",        "22283e"), ("SLATE",      "384868"), ("BLUE",       "52699a"),
    ("BLUE_LIGHT",  "7e96bd"),
    # metal and greys
    ("GREY_DARK",   "4a4656"), ("GREY",       "7a7a92"), ("SILVER",     "c4bdb8"),
    ("STEEL_HI",    "ebe7e0"),
    # sage and cactus
    ("OLIVE_DARK",  "2f3323"), ("OLIVE",      "505631"), ("SAGE",       "7b804b"),
]

# Swappable ramps: (name, gold dusk at duel 1, deep red dusk from duel 8)
SWAP = [
    ("SKY_TOP",     "3a2046", "1e0c20"),
    ("SKY_UPPER",   "5a2a54", "341230"),
    ("SKY_HIGH",    "8c2f4a", "5a1428"),
    ("SKY_MID",     "b53a36", "7a1a22"),
    ("SKY_WARM",    "d24e30", "9c2622"),
    ("SKY_LOW",     "e8702e", "b83224"),
    ("HORIZON",     "f59a3a", "d2502a"),
    ("HORIZON_HOT", "f9bb52", "e46e34"),
    ("SUN",         "fdd66a", "f4924a"),
    ("SUN_CORE",    "fff2b0", "fcc27a"),
    ("RIM",         "f8bf5a", "e0602e"),
    ("RIM_HOT",     "ffe08e", "f28a4a"),
    ("DUST",        "e0a468", "b87a50"),
    ("DUST_LIGHT",  "f0c890", "d09a6a"),
    ("HAZE",        "c86a58", "8a3438"),
    ("MESA_LIT",    "d2604a", "a03030"),
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
