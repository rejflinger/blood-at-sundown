"""Mesas, buttes and the far ridge along the horizon.

Back to front: a far ridge whose hazy crest line runs under the sun with sunlit valley haze
below it, two far buttes standing on that line, a low saddle hill closing the valley, the
main range of buttes in three depth planes (red-orange next to the sun, crimson in the
middle, dark purple for the nearest rock) with organ-pipe column faces, short rubble talus
and a few hoodoos, then the rolling valley slopes (humped ridges with dark scrub) that
funnel down to the church. Everything is painted into a grid of palette names first and
turned into pixels at the end, so every pixel is a whole palette colour.
"""
import math

import numpy as np
from PIL import Image, ImageDraw

import palette as P
from scene.common import *  # noqa: F401,F403


BASE = 252            # butte skirts end here; the lit edges stop here too
TALUS_END = 262       # short rubble talus below BASE, met by the saddle and the slopes
FLOOR = 300           # the layer is opaque from every silhouette down to this row
X0, X1 = -OX, SAFE_W + OX - 1


class Grid:
    """Palette indices per canvas pixel, addressed in safe coordinates; -1 is transparent."""

    def __init__(self):
        self.a = np.full((H, W), -1, np.int16)

    def set(self, x, y, name):
        X, Y = int(x) + OX, int(y) + OY
        if 0 <= X < W and 0 <= Y < H:
            self.a[Y, X] = P.IDX[name]

    def get(self, x, y):
        X, Y = int(x) + OX, int(y) + OY
        if 0 <= X < W and 0 <= Y < H and self.a[Y, X] >= 0:
            return P.NAMES[self.a[Y, X]]
        return None

    def layer(self):
        L = Layer()
        lut = np.zeros((len(P.NAMES) + 1, 4), np.uint8)
        for i, n in enumerate(P.NAMES):
            lut[i] = col(n)
        idx = np.where(self.a >= 0, self.a, len(P.NAMES))
        L.im = Image.fromarray(lut[idx], "RGBA")
        L.d = ImageDraw.Draw(L.im)
        return L


def D(x, y, level):
    """Bayer test in safe coordinates (the matrix is anchored to the layer canvas)."""
    return dith(x + OX, y + OY, level)


def lerp_pts(pts, x):
    """Piecewise-linear y through (x, y) points sorted by x."""
    if x <= pts[0][0]:
        return pts[0][1]
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        if xa <= x <= xb:
            return ya + (yb - ya) * (x - xa) / (xb - xa)
    return pts[-1][1]


# 1 far ridge -------------------------------------------------------------------------------
# Outside the notch the ridge is SKY_MID with a SKY_WARM crest. Under the sun it settles
# into a thin hazy crest line (the far buttes stand on it) and below that line the valley
# haze glows in stepped bands, brightest just above the saddle hill.
NOTCH = (118, 182)


def ridge_top(x):
    y = 248 + round(3 * math.sin(x / 23.0) + 2 * math.sin(x / 9.0))
    if 112 < x < 188:  # settle into the far crest line under the sun
        t = min(1.0, (x - 112) / 14.0, (188 - x) / 14.0)
        w = t * t * (3 - 2 * t)
        line = 251 + round(math.sin(x / 6.0) * 0.8)
        y = round(y + (line - y) * w)
    return y


def notch_weight(x):
    """0 outside the sunlit notch, 1 inside, stepping across 6 px at each side."""
    return max(0.0, min(1.0, (x - NOTCH[0] + 3) / 6.0, (NOTCH[1] + 3 - x) / 6.0))


def haze(d):
    """Colour of the valley haze d rows under the far crest line: stepped solid bands with
    a single dither row at each change ("a/b" marks the dither rows)."""
    if d <= 1:
        return "SKY_MID"
    if d == 2:
        return "mid/warm"
    if d <= 4:
        return "SKY_WARM"
    if d == 5:
        return "warm/low"
    return "SKY_LOW"


def draw_ridge(g):
    for x in range(X0, X1 + 1):
        top = ridge_top(x)
        nw = notch_weight(x)
        for y in range(top, FLOOR + 1):
            d = y - top
            c = "SKY_WARM" if d < 2 else "SKY_MID"
            if nw > 0 and D(x, y, nw) and d >= 0:
                h = haze(d)
                if h == "mid/warm":
                    h = "SKY_WARM" if D(x, y, 0.5) else "SKY_MID"
                elif h == "warm/low":
                    h = "SKY_LOW" if D(x, y, 0.5) else "SKY_WARM"
                c = h
            g.set(x, y, c)


# 2 far buttes against the lower sun, standing on the far crest line ------------------------
FAR_BUTTES = [  # (top, sun side, [(row, x0, x1), ...]): the outline widens at each listed row
    (240, "R", [(240, 131, 137), (242, 130, 138), (244, 129, 139), (246, 128, 140)]),
    (236, "L", [(236, 162, 168), (238, 161, 168), (240, 161, 169), (242, 160, 169),
                (244, 160, 170)]),
]
FAR_NOTCH = {240: (134,), 236: (165, 166)}   # small bites out of the flat tops


def draw_far_buttes(g):
    for top, sun, steps in FAR_BUTTES:
        x0 = x1 = None
        for y in range(top, 262):
            for sy, a, b in steps:
                if y == sy:
                    x0, x1 = a, b
            for x in range(x0, x1 + 1):
                if y >= ridge_top(x):   # merged into the far crest line
                    continue
                edge = x == (x1 if sun == "R" else x0)
                c = "SKY_MID"
                if y == top:
                    if x in FAR_NOTCH[top]:
                        continue
                    c = "SKY_LOW" if edge or (x > (x0 + x1) / 2) == (sun == "R") else "SKY_WARM"
                elif edge and y < top + 9:
                    c = "SKY_WARM"
                elif y == top + 1 and x in FAR_NOTCH[top]:
                    c = "SKY_WARM"
                g.set(x, y, c)
            # the far crest line under the butte is solid SKY_MID, so it stands on it
            for x in range(x0 - 1, x1 + 2):
                r = ridge_top(x)
                if y >= r and y <= r + 1:
                    g.set(x, y, "SKY_MID")


# 3 saddle hill closing the valley -------------------------------------------------------------
def saddle_top(x):
    return 259 + round(((x - 143) / 21.0) ** 2 * 6 + 0.8 * math.sin(x / 5.0))


def draw_saddle(g):
    """A low hill across the valley, lit red by the haze behind it (lighter than the slopes
    in front, so the valley reads as a glowing V)."""
    for x in range(104, 184):
        top = saddle_top(x)
        peak = abs(x - 143) < 9
        for y in range(top, FLOOR + 1):
            d = y - top
            if d == 0:
                c = "RED_LIGHT" if peak and (x % 5) < 3 else "MESA_LIT"
            elif d <= 3:
                c = "SKY_MID"
            elif d == 4:
                c = "SKY_HIGH" if D(x, y, 0.5) else "SKY_MID"
            else:
                c = "SKY_HIGH"
            g.set(x, y, c)


# 4 main buttes -------------------------------------------------------------------------------
# anchors: (row, x) points of one wall, top to bottom. Between anchors the wall is vertical,
# stepping 1..2 px at ledges every 8..12 rows so it arrives exactly at the next anchor.
# skirt: x at BASE; the wall flares out to it from its last anchor, then a short rubble
# talus continues to TALUS_END. plane: "sun" (next to the sun, red-orange and flat),
# "mid" (crimson, column faces) or "near" (the nearest rock, dark purple).
# Later entries are nearer and cover the feet of earlier ones.
BUTTES = [
    dict(name="M8", plane="near", top=208, sun="L",
         left=[(208, 214), (228, 212), (240, 210)], lskirt=205,
         right=[(208, 238), (214, 238)], rskirt=238,
         extra_right=[(214, 240, 410)]),
    dict(name="M6", plane="mid", top=224, sun="L",
         left=[(224, 178), (231, 178), (232, 172), (244, 171)], lskirt=170,
         right=[(224, 199), (242, 200)], rskirt=206),
    dict(name="M7", plane="sun", top=231, sun="L", cap="round",
         left=[(231, 170), (244, 169)], lskirt=166,
         right=[(231, 174), (244, 175)], rskirt=178),
    dict(name="M5", plane="sun", top=222, sun="R", cap="round",
         left=[(222, 121), (244, 120)], lskirt=118,
         right=[(222, 124), (244, 125)], rskirt=128),
    dict(name="M4", plane="mid", top=214, sun="R", crack=(110, 214, 224),
         left=[(214, 102), (236, 101)], lskirt=96,
         right=[(214, 119), (236, 120)], rskirt=126),
    dict(name="M3", plane="mid", top=205, sun="R", cap="round",
         left=[(205, 93), (245, 91)], lskirt=89,
         right=[(205, 97), (224, 97), (225, 99), (245, 100)], rskirt=103),
    dict(name="M2", plane="mid", top=197, sun="R", cap="round",
         left=[(197, 86), (240, 84)], lskirt=81,
         right=[(197, 90), (212, 90), (213, 92), (240, 93)], rskirt=96),
    dict(name="M1", plane="near", top=186, sun="R",
         left=[(186, 42), (240, 38)], lskirt=30,
         right=[(186, 78), (213, 80), (214, 84), (240, 86)], rskirt=90),
]

# tone sets per depth plane: face levels index RAMP (lit column, dark column, 1 px gap);
# the lower 40% of a butte sinks one level
RAMP = ["MESA_LIT", "SKY_MID", "SKY_HIGH", "PLUM_LIGHT", "PLUM", "SHADOW"]
PLANES = {
    "near": dict(lit=2, dark=3, gap=4, edge_hi="MESA_LIT", edge="SKY_MID", edge_low="SKY_HIGH",
                 top_rest="SKY_MID", ledge="SKY_HIGH", lit_bias=(0.45, 0.35)),
    "mid": dict(lit=1, dark=2, gap=3, edge_hi="MESA_LIT", edge="SKY_MID", edge_low="SKY_MID",
                top_rest="SKY_LOW", ledge="SKY_MID", lit_bias=(0.1, 0.65)),
    "sun": dict(lit=1, dark=1, gap=None, edge_hi="SKY_WARM", edge="SKY_WARM", edge_low="SKY_MID",
                top_rest="SKY_WARM", ledge="SKY_WARM", lit_bias=(1.0, 0.0)),
}


def wall(anchors, seed, skirt):
    out = {}
    x = anchors[0][1]
    out[anchors[0][0]] = x
    for (ya, xa), (yb, xb) in zip(anchors, anchors[1:]):
        rows, r, k = [], ya, 0
        while True:
            r += 8 + int(hsh(seed, ya, k) * 5)
            k += 1
            if r >= yb:
                break
            rows.append(r)
        rows.append(yb)
        rem = xb - xa
        steps = {}
        for i, r in enumerate(rows):
            if i == len(rows) - 1:
                s = rem
            else:
                s = int(math.copysign(min(abs(rem), 1 + (hsh(seed, r, 5) < 0.4)), rem)) if rem else 0
            steps[r] = s
            rem -= s
        for y in range(ya + 1, yb + 1):
            x += steps.get(y, 0)
            out[y] = x
    yw, xw = anchors[-1]
    for y in range(yw + 1, BASE + 1):
        t = (y - yw) / float(BASE - yw)
        out[y] = round(xw + (skirt - xw) * t * t)
    return out


def butte_rows(b, seed):
    L = wall(b["left"], seed, b["lskirt"])
    R = wall(b["right"], seed + 1, b["rskirt"])
    rows = {}
    for y in range(b["top"], BASE + 1):
        xl, xr = L[y], R[y]
        if y == b["top"] and b.get("cap") == "round":
            xl, xr = xl + 1, xr - 1
        rows[y] = [xl, xr]
    for y0, x0, x1 in b.get("extra_right", ()):  # a lower shoulder running off to the side
        for y in range(y0, BASE + 1):
            if y in rows:
                rows[y][1] = max(rows[y][1], x1)
    # short rubble talus: spreads a little, with a lumpy edge made of 2-row steps
    xl, xr = rows[BASE]
    for y in range(BASE + 1, TALUS_END + 1):
        k = (y - BASE) * 0.6
        bl = int(hsh(seed, (y - BASE) // 2, 41) * 2)
        br = int(hsh(seed, (y - BASE) // 2, 42) * 2)
        rows[y] = [int(xl - k) + bl, int(xr + k) - br]
    return rows


def column_map(b, rows, seed, pl):
    """Organ-pipe columns 2..4 px wide separated by 1 px gaps: x -> (kind, index)."""
    xs = [r[0] for r in rows.values()] + [r[1] for r in rows.values()]
    x_lo, x_hi = min(xs), max(xs)
    t_lo, t_hi = rows[b["top"]]
    sun_r = b["sun"] == "R"
    cmap = {}
    x, i = x_lo + int(hsh(seed, 61) * 3), 0
    for xx in range(x_lo, x):
        cmap[xx] = ("dark", -1)
    while x <= x_hi:
        w = 2 + int(hsh(seed, i, 62) * 3)
        mid = x + w / 2.0
        pos = (mid - t_lo) / max(1.0, t_hi - t_lo)   # 0 at the left edge, 1 at the right
        pos = min(1.0, max(0.0, pos if sun_r else 1.0 - pos))  # 1 at the sun side
        a0, a1 = pl["lit_bias"]
        lit = hsh(seed, i, 63) < a0 + a1 * pos
        if i > 0 and cmap.get(x - 2, ("", 0))[0] == ("lit" if lit else "dark") and hsh(seed, i, 64) < 0.5:
            lit = not lit   # prefer alternating columns
        for k in range(w):
            cmap[x + k] = ("lit" if lit else "dark", i)
        cmap[x + w] = ("gap", i)
        x += w + 1
        i += 1
    return cmap


def draw_butte(g, b, seed):
    rows = butte_rows(b, seed)
    pl = PLANES[b["plane"]]
    top = b["top"]
    span = BASE - top
    y_dark = top + 0.6 * span            # the lower 40% sinks one tone darker
    y_hi = top + span / 3.0              # the upper third of the sun edge is hottest
    sun_r = b["sun"] == "R"
    wall_end = max(b["left"][-1][0], b["right"][-1][0])
    t_lo, t_hi = rows[top]
    width = t_hi - t_lo + 1
    columns = width > 10 and pl["gap"] is not None
    cmap = column_map(b, rows, seed, pl) if columns else {}

    def inside(x, y):
        r = rows.get(y)
        return r is not None and r[0] <= x <= r[1]

    # per column: how far down the lit tone hangs, and the extent of the gap crack
    def col_info(i):
        lit_len = span * (0.45 + 0.25 * hsh(seed, i, 71))
        g0 = top + 1 + int(hsh(seed, i, 72) * 3)
        g1 = top + span * (0.2 + 0.4 * hsh(seed, i, 73))
        if hsh(seed, i, 74) < 0.35:        # not every column is split by a crack
            g1 = g0 - 1
        return lit_len, g0, g1

    # strata: at most one short dash per 6 rows on each column, only on wide faces
    strata = set()
    if columns and width >= 12:
        for i in range(0, 40):
            for j in range(0, span // 6):
                if hsh(seed, i, j, 81) < 0.28:
                    strata.add((i, top + 6 * j + 3 + int(hsh(seed, i, j, 82) * 3)))

    for y, (xl, xr) in rows.items():
        wide = xr - xl + 1
        band = 2 + (hsh(seed, y // 9, 7) < 0.5)
        band = max(1, min(band, wide // 3))
        talus = y > BASE
        skirt = y > wall_end
        lower = y > y_dark - 3
        for x in range(xl, xr + 1):
            din = (xr - x) if sun_r else (x - xl)
            # face tone from the column map; each column sinks at its own row
            kind, i = cmap.get(x, ("dark", -1)) if columns else ("dark", -1)
            jit = hsh(seed, i, 75) * 8 - 4 if columns else 0
            yd = y_dark + jit                    # lit columns sink here ...
            yd2 = top + (0.82 if b["plane"] != "near" else 1.2) * span + jit / 2   # ... then the foot
            # stepped: solid below the change, a single 50% dither row at it
            low = talus or y > int(yd2) or (y == int(yd2) and D(x, y, 0.5))
            if kind == "lit" and (y > int(yd) or (y == int(yd) and D(x, y, 0.5))):
                kind = "dark"
            lit_len, g0, g1 = col_info(i)
            if kind == "gap" and not (g0 <= y <= g1):
                kind = "dark"
            if kind == "lit" and (y - top > lit_len or (y - top == int(lit_len) and D(x, y, 0.5))):
                kind = "dark"
            lvl = pl[kind] + low
            if (i, y) in strata and kind == "lit":
                lvl += 1
            c = RAMP[min(lvl, 5)]
            # the sun-side band down the wall (it stops at BASE)
            if not talus and din < band:
                if y < y_hi or (int(y_hi) == y and D(x, y, 0.5)):
                    c = pl["edge_hi"]
                elif not low:
                    c = pl["edge"]
                elif din == 0:
                    c = pl["edge_low"]
            if talus:   # rubble: the dark tone with lumps one level lighter
                lump = hsh(seed, x // 2, (y - BASE) // 2, 91) < 0.18 and y < TALUS_END - 1
                c = RAMP[min(5, pl["dark"] + 1 - lump)]
            # tops and ledges catch the sun
            sun_half = (x >= (xl + xr) / 2.0) if sun_r else (x <= (xl + xr) / 2.0)
            if not inside(x, y - 1) and not skirt and not talus:
                if y == top:
                    c = "RED_LIGHT" if sun_half or wide <= 6 else pl["top_rest"]
                elif din <= 1 and sun_half:
                    c = "RED_LIGHT" if din == 0 else pl["edge_hi"]
                elif sun_half:
                    c = pl["edge_hi"]
                else:
                    c = pl["ledge"]
            elif y - 1 == top and sun_half and din > 0:
                c = pl["edge_hi"]
            elif (din == 0 and y - 1 > top and not skirt and not talus
                  and not inside(x, y - 2)):
                c = "RED_LIGHT"   # a ledge tip glints over two rows
            g.set(x, y, c)
    if "crack" in b:
        cx, cy0, cy1 = b["crack"]
        for y in range(cy0 + 1, cy1 + 1):
            g.set(cx, y, "PLUM")
    return rows


# hoodoos: small capped pillars at the feet of the buttes, (x0, x1, top, sun side)
HOODOOS = [(99, 102, 239, "R"), (126, 128, 245, "R"), (207, 210, 239, "L")]


def draw_hoodoos(g):
    for x0, x1, top, sun in HOODOOS:
        for y in range(top, TALUS_END + 1):
            d = y - top
            a, b = x0, x1                       # the cap rock
            if d == 0:
                a, b = x0 + 1, x1 - 1           # rounded cap
            elif 3 <= d <= 6:                   # the neck is undercut on the shaded side,
                if sun == "R" and g.get(x0, y):  # only where rock stands behind it
                    a = x0 + 1
                elif sun == "L" and g.get(x1, y):
                    b = x1 - 1
            elif d > 6:
                k = (d - 6) // 3
                a, b = x0 - k, x1 + k           # widening base
            for x in range(a, b + 1):
                din = (b - x) if sun == "R" else (x - a)
                if d == 0:
                    c = "RED_LIGHT" if din == 0 else "MESA_LIT"
                elif din == 0 and d < 8:
                    c = "MESA_LIT" if d < 4 else "SKY_MID"
                else:
                    c = "SKY_HIGH" if d < 9 else "PLUM_LIGHT"
                if d == 3 and din > 0 and (x == x0 or x == x1):
                    c = "PLUM_LIGHT"            # shadow under the cap rock
                g.set(x, y, c)


# 5 valley slopes ----------------------------------------------------------------------------
LEFT_SLOPE = [(-140, 232), (20, 238), (60, 244), (95, 248), (125, 264), (133, 270), (140, 276)]
RIGHT_SLOPE = [(140, 276), (147, 272), (155, 268), (185, 256), (215, 246), (250, 236), (410, 228)]
SUN_X = 155


def crest_base(x):
    return lerp_pts(LEFT_SLOPE if x <= 140 else RIGHT_SLOPE, x)


def crest(x):
    """The front crest of the valley slopes, with low humps."""
    return round(crest_base(x) - 2 * abs(math.sin(x / 7.0 + 0.4)))


def crest_sunward(x):
    s = math.sin(x / 7.0 + 0.4)
    slope = -math.copysign(1.0, s) * math.cos(x / 7.0 + 0.4)
    return slope > 0 if x < SUN_X else slope < 0


def mounds():
    """Rounded foothills in staggered rows under the crest: (cy, cx, half width, height)."""
    out = []
    for side, (xa, xb) in enumerate(((X0, 141), (139, X1 + 1))):
        for r in range(5):
            off = 8 + 8 * r + int(hsh(side, r, 50) * 3)
            x = xa - int(hsh(side, r, 51) * 12)
            i = 0
            while x < xb:
                w = 7 + int(hsh(side, r, i, 52) * 7) + r
                h = 3 + int(hsh(side, r, i, 53) * 2) + (r >= 2)
                cx = min(max(x + w, xa), xb - 1)
                cy = round(crest_base(cx)) + off + int(hsh(side, r, i, 54) * 3) - 1
                out.append((cy, cx, w, h, side * 100 + r * 20 + i, r))
                x += int(w * (1.1 + 0.6 * hsh(side, r, i, 55)))
                i += 1
    out.sort()
    return out


def mound_top(x, cx, w, h, cy):
    return round(cy - h * (0.5 + 0.5 * math.cos(math.pi * (x - cx) / w)))


def slope_base_colour(x, y, top):
    d = y - top
    sun = crest_sunward(x)
    if d == 0:
        if 95 <= x <= 185 and sun and abs(math.sin(x / 7.0 + 0.4)) > 0.8:
            return "RED_LIGHT"              # hot tips on the humps nearest the sun
        return "MESA_LIT" if sun else "SKY_MID"
    if d == 1:
        return "SKY_MID" if sun else "SKY_HIGH"
    if d < 6:
        return "SKY_HIGH"
    if d == 6:
        return "PLUM_LIGHT" if D(x, y, 0.5) else "SKY_HIGH"
    return "PLUM_LIGHT"


def mound_colour(x, y, cx, w, top, r):
    """Rim-lit hump tops on the sun half; nearer rows (larger r) sit deeper in shadow."""
    d = y - top
    u = (x - cx) / float(w)                      # -1 .. 1 across the mound
    sun = (u > 0) if cx < SUN_X else (u < 0)
    peak = abs(u) < 0.55
    rim = ["MESA_LIT", "SKY_MID", "SKY_MID", "SKY_HIGH", "SKY_HIGH"][min(r, 4)]
    under = ["SKY_MID", "SKY_HIGH", "SKY_HIGH", "PLUM_LIGHT", "PLUM_LIGHT"][min(r, 4)]
    body = "SKY_HIGH" if r < 3 else "PLUM_LIGHT"
    if d == 0:
        if sun and peak:
            return rim
        return under if sun and abs(u) < 0.8 else body
    if d == 1:
        return under if sun and abs(u) < 0.35 else body
    deep = 5 if r < 3 else 3                     # rows of lit body before the shade
    if d < deep:
        return "SKY_HIGH" if abs(u) < 0.85 else "PLUM_LIGHT"
    if d == deep:
        return "PLUM_LIGHT" if D(x, y, 0.5) or abs(u) >= 0.7 else "SKY_HIGH"
    return "PLUM_LIGHT"


LIGHTER = {"PLUM_LIGHT": "SKY_HIGH", "SKY_HIGH": "SKY_MID", "SKY_MID": "SKY_MID",
           "MESA_LIT": "MESA_LIT", "RED_LIGHT": "RED_LIGHT", "PLUM": "PLUM", "SHADOW": "SHADOW"}


def valley_glow(x, y, c):
    """The slopes nearest the glowing V sit lighter: two tones in the heart of the V, one
    tone around it, each change a single dithered ring."""
    r = math.hypot((x - 143) / 42.0, (y - 268) / 14.0)
    steps = 0
    if r < 0.55 or (r < 0.65 and D(x, y, 0.5)):
        steps = 2
    elif r < 1.0 or (r < 1.1 and D(x, y, 0.5)):
        steps = 1
    for _ in range(steps):
        c = LIGHTER.get(c, c)
    return c


def draw_slopes(g):
    tops = {}
    for x in range(X0, X1 + 1):
        top = crest(x)
        tops[x] = [top]
        for y in range(top, FLOOR + 1):
            g.set(x, y, valley_glow(x, y, slope_base_colour(x, y, top)))

    def bush(x, y, shape, x_sun, lines):
        pts = {"2x1": [(0, 0), (1, 0)],
               "2x2": [(0, -1), (1, -1), (0, 0), (1, 0)],
               "3x2": [(1, -1), (0, 0), (1, 0), (2, 0)] if hsh(x, y, 5) < 0.5 else
                      [(0, -1), (1, -1), (0, 0), (1, 0), (2, 0)],
               "tree": [(1, -3), (1, -2), (0, -1), (1, -1), (2, -1), (0, 0), (1, 0), (2, 0)]}[shape]
        w = max(p[0] for p in pts) + 1
        for dx, dy in pts:   # never in the two rows under any ridge line, never low down
            ls = lines.get(x + dx)
            if ls is None or y + dy >= 290 or any(0 <= y + dy - l <= 1 for l in ls):
                return
        away = 0 if x_sun else w - 1
        for dx, dy in pts:
            c = "SHADOW" if (dy == 0 and dx == away) else "PLUM"
            g.set(x + dx, y + dy, c)

    for cy, cx, w, h, sid, r in mounds():
        x0, x1 = cx - w + 1, cx + w - 1
        for x in range(x0, x1 + 1):
            if x not in tops:
                continue
            top = mound_top(x, cx, w, h, cy)
            if top < tops[x][0] + 3:     # stay under the front crest
                continue
            tops[x].append(top)
            for y in range(top, FLOOR + 1):
                c = valley_glow(x, y, mound_colour(x, y, cx, w, top, r))
                if y >= 290:
                    c = "PLUM" if D(x, y, (y - 289) / 6.0) else c
                g.set(x, y, c)
        # a clump of scrub at the foot of the mound, on its shaded side, denser near the V
        near = 1.0 - min(1.0, abs(cx - 140) / 120.0)
        n = 1 + int(hsh(sid, 60) * (2 + 3 * near))
        shade = -1 if cx < SUN_X else 1
        bx = cx + shade * int(w * (0.3 + 0.5 * hsh(sid, 61)))
        y = cy + 1 + int(hsh(sid, 62) * 2)
        for j in range(n):   # blobs touch, so the clump reads as one dark patch
            shape = ("2x2", "3x2", "2x1")[int(hsh(sid, j, 63) * 2.7)]
            if near > 0.6 and hsh(sid, j, 66) < 0.35:
                shape = "tree"
            bush(bx, y + int(hsh(sid, j, 67) * 2) - (j % 2), shape, cx < SUN_X, tops)
            bx += (2 if shape == "2x1" or shape == "2x2" else 3) * -shade
    # scrub along the front crest band as well, sparse
    x = X0
    while x <= X1:
        near = 1.0 - min(1.0, abs(x - 140) / 120.0)
        if hsh(x, 71) < 0.15 + 0.35 * near:
            y = crest(x) + 3 + int(hsh(x, 72) * 4)
            bush(x, y, ("2x2", "2x1", "3x2")[int(hsh(x, 73) * 2.8)], x < SUN_X, tops)
        x += 4 + int(hsh(x, 74) * 4)


def draw_mesas(rng):
    """The mesa layer. Fully deterministic (hsh and Bayer only); rng is kept for the shared
    signature so the other modules' seeds stay untouched."""
    g = Grid()
    draw_ridge(g)
    draw_far_buttes(g)
    draw_saddle(g)
    for i, b in enumerate(BUTTES):
        draw_butte(g, b, 500 + i * 17)
    draw_hoodoos(g)
    draw_slopes(g)
    return g.layer()
