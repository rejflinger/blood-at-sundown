"""The street and ground: dusty rust dirt in a dark frame, lit by the church door and by a few
patches of low sun, raked into soft horizontal strata, scattered with clods, dry grass, a few
rocks and a pair of soft wagon ruts.

Value story (backlit dusk): colour bands joined by hard, ragged steps that wander like drifted
dust and follow the raked strata, so no seam reads as a ruled stripe or a dotted row. The street
sides sit a step darker, and the right-hand buildings throw a shade whose edges run toward the
sun's point on the horizon; the near rows sink to BROWN. The dirt is a streaky height field laid
in street metres (so the strata flatten and shrink with distance), lit where it rises toward the
sun and shaded where it falls toward the camera, then cut at hard thresholds into a shade step,
the bare ground and a lit step. The pools of low sun and the door light lift the dirt in ragged
patches and shift that balance toward the lit step, so the light reads as raked dust, never as a
checkerboard or a glossy sheet. The church door lays a stepped path of lamplight (AMBER, OCHRE,
ORANGE) down the middle of the far street. On top: clods and lumps (a lit top, a shade row, a
darker cast row), dry grass with backlit tips, pebbles and rocks. DUST (a swapped entry) marks
rock crowns, pebble tops and a few specks, so the lit ground follows the duel palette from gold to
deep red. A last pass gives every stray lone dirt pixel its neighbours' colour, so the texture is
made of clusters, never salt and pepper.
"""
import math

import numpy as np

import palette as P
from scene.common import *  # noqa: F401,F403


# value ramp of the ground, darkest first
RAMP = ["BROWN_BLACK", "BROWN_DARK", "BROWN", "BROWN_MID", "RUST", "ORANGE"]
LV = {n: i for i, n in enumerate(RAMP)}
LV.update({"OCHRE": 5, "LEATHER": 4, "AMBER": 5, "DUST": 5})
FAR_LEVEL = 3                          # the far street, in the town's shade: BROWN_MID
# seams (first row, length, step): far street up to RUST behind PLAY, then down toward the camera.
# Each is one hard step at its middle row, wandering SEAM_WANDER rows along x and pushed up or
# down by the strata (SEAM_JITTER rows at full strength), so it reads as a ragged drift line.
SEAMS = [(321, 8, +1), (528, 8, -1), (564, 8, -1), (577, 8, -1)]
SEAM_WANDER, SEAM_JITTER = 5, 12.0
BOTTOM_WANDER = 0.6                    # last row BROWN_BLACK; the row above joins it in runs
SIDE_X, SIDE_EDGE = 4.5, 1.25          # street half width in metres, how far its edge wanders
# right-hand shade: the shadows of the long porch roofs run along the street, so their edges are
# street lines through the vanishing point (x at the horizon, slope in px per row): the street
# shade 1.9 m right of the centre line, then the deeper shade under the porch roof at 3.7 m.
# The first crosses PLAY's right edge well above its corner. SHADE_Y0 is the top row.
SHADE_LINES = [(CX, 1.1), (CX, 2.2)]
SHADE_Y0, SHADE_JITTER, PORCH_SHIFT = 318, 10.0, 0.06
# lit dust pools: centre x, centre y, radius x, radius y (safe pixels)
POOLS = [(140, 330, 70, 16), (210, 468, 34, 44), (152, 548, 60, 16)]
POOL_GAIN = [0.6, 1.0, 1.0]            # P1 mostly lights the street behind PLAY: kept dim above it
POOL_CORE = 0.45                       # share of the radius at full strength
# raked strata: (width in metres at the camera, aspect, weight) per octave, and the cut points
STRATA = [(0.13, 4.0, 0.55), (0.45, 4.0, 0.3), (0.04, 2.5, 0.15)]
MIN_CELL = (6.0, 1.4)                  # far away the strata never get finer than this (px)
K_EMBOSS, K_HEIGHT = 1.0, 0.6          # ridge slope and ridge height in the strata score
CUT_DARK, CUT_LIT, CUT_TOP = -0.13, 0.14, 0.26
POOL_SHIFT, SHADE_SHIFT, FAR_SHIFT = 0.12, 0.14, 0.10
POOL_CUT = 0.5                         # where a pool lifts BROWN_MID or BROWN dirt a whole step
POOL_CUT_CORE = 0.8                    # where it lifts RUST dirt to ORANGE
# the church door (town.py stands it on the street with its lit doorway over x 136..144): the
# soft warm patch it throws on the street, and the stepped path of lamplight under it
DOOR_X = 140
# the warm patch: an ellipse on the street in metres, from the doorstep toward the camera
# (half width across, length along), the door standing at the PATH_TOP row
DOOR_RX, DOOR_RZ, DOOR_GAIN = 3.2, 11.0, 1.8
DOOR_SHIFT, DOOR_CUT = 0.16, 0.5       # how far the door light shifts the strata; where it lifts the base
# the path: drawn from under the church (which covers its first rows) down the street. It is as
# wide as the doorway at PATH_TOP and widens toward the camera, in street metres, so it follows
# the perspective: half width PATH_HW + PATH_SPREAD per metre of depth. Bands, brightest first:
# (strength, colour); the strength falls off across the path and along it, slowly while PLAY
# is still above it (y 318) and then fast, so with no buttons (the duel) it tapers out ragged
# before PATH_Y1 instead of ending in a straight cut.
PATH_Y0, PATH_TOP, PATH_Y1 = 300, 308, 332
PATH_HW, PATH_SPREAD, PATH_FADE, PATH_EASE = 0.55, 0.06, 0.85, 2.5
PATH_RAG = 0.5                         # how far the strata fray the band edges
PATH_SYM = 0.75                        # share of that fray mirrored about the door's axis, so the
                                       # path stays centred on the door and only frays unevenly
PATH_EDGE = 2                          # off-path OCHRE this close to the path drops to ORANGE
PATH_BANDS = [(0.72, "AMBER"), (0.48, "OCHRE"), (0.28, "ORANGE")]
# rocks: exact bounding boxes x0, y0, x1, y1 (the cast shadow goes below the box)
ROCKS = [(196, 419, 204, 423), (228, 432, 234, 435), (197, 466, 201, 468), (179, 521, 187, 525),
         (92, 556, 97, 558), (156, 546, 164, 550)]
# where the UI and the near props cover the street: no detail is spent there (scripts/ui.gd:
# the button column, the icon row, and the caption and daily status text over the street)
UI_BOXES = [(78, 318, 193, 355), (78, 362, 193, 391), (78, 398, 193, 427), (78, 446, 193, 475),
            (78, 482, 193, 511), (32, 528, 63, 559), (119, 528, 150, 559), (206, 528, 237, 559)]
# the icon captions, then the daily status slot under DAILY DUEL: its label spans x 18..253 and
# after a daily run carries "TODAY: n DUELS · $n · BACK TOMORROW" (up to about 215 px in body_ol,
# centred on x 136), so none of this layer's grass stands behind any of that line
CAPTIONS = [(31, 561, 63, 571), (118, 561, 150, 571), (189, 561, 253, 571), (26, 428, 248, 441)]
# one step darker / lighter on the ground ramp (lit tops cap at ORANGE, then turn OCHRE)
DARKER = {"ORANGE": "RUST", "OCHRE": "RUST", "LEATHER": "BROWN_MID", "RUST": "BROWN_MID",
          "BROWN_MID": "BROWN", "BROWN": "BROWN_DARK", "BROWN_DARK": "BROWN_BLACK",
          "BROWN_BLACK": "BROWN_BLACK", "AMBER": "ORANGE", "DUST": "OCHRE"}
LIGHTER = {"BROWN_BLACK": "BROWN_DARK", "BROWN_DARK": "BROWN", "BROWN": "BROWN_MID",
           "BROWN_MID": "RUST", "RUST": "ORANGE", "LEATHER": "ORANGE", "ORANGE": "OCHRE",
           "OCHRE": "OCHRE", "AMBER": "AMBER", "DUST": "DUST"}


def _h(*v):
    """hsh with an avalanche finish, so neighbouring integer inputs give unrelated values."""
    x = int(hsh(*v) * 0xFFFFFFFF)
    x ^= x >> 16
    x = (x * 0x7FEB352D) & 0xFFFFFFFF
    x ^= x >> 15
    x = (x * 0x846CA68B) & 0xFFFFFFFF
    x ^= x >> 16
    return x / 0xFFFFFFFF


def _clamp(v, a=0.0, b=1.0):
    return a if v < a else (b if v > b else v)


def _street(x, y):
    """Street coordinate X (metres across) and depth z for a ground pixel."""
    z = F * EYE / max(0.5, y - HY)
    return (x - CX) * z / F, z


def _noise1(t, seed):
    i = math.floor(t)
    f = t - i
    f = f * f * (3 - 2 * f)
    a, b = _h(i, seed), _h(i + 1, seed)
    return a + (b - a) * f


def _noise2(u, v, seed):
    iu, iv = math.floor(u), math.floor(v)
    fu, fv = u - iu, v - iv
    fu, fv = fu * fu * (3 - 2 * fu), fv * fv * (3 - 2 * fv)
    a, b = _h(iu, iv, seed), _h(iu + 1, iv, seed)
    c, d = _h(iu, iv + 1, seed), _h(iu + 1, iv + 1, seed)
    return (a + (b - a) * fu) * (1 - fv) + (c + (d - c) * fu) * fv


def _cells(y, width, aspect):
    """Cell size in pixels of a strata octave on row y: width metres seen at depth z."""
    _X, z = _street(CX, y)
    cw = max(MIN_CELL[0], width * F / z)
    return cw, max(MIN_CELL[1], cw / aspect)


# the vertical noise coordinate of each octave, summed row by row (cells shrink with distance)
_VROW = {}


def _vrow(y, k):
    key = (y, k)
    if key not in _VROW:
        width, aspect, _w = STRATA[k]
        v = 0.0
        for yy in range(HY + 1, y):
            v += 1.0 / _cells(yy, width, aspect)[1]
        _VROW[key] = v
    return _VROW[key]


def _strata(x, y):
    t = 0.0
    for k, (width, aspect, wgt) in enumerate(STRATA):
        cw, _ch = _cells(y, width, aspect)
        t += wgt * _noise2((x - CX) / cw + 17.3 * k, _vrow(y, k), 30 + k)
    return t


def _shade_edge(y, k):
    """Left edge of shade k on row y: a street line toward the vanishing point, wandering a
    little like the porch's ragged roofline."""
    vx, slope = SHADE_LINES[k]
    return vx + slope * (y - HY) + round(4 * (_noise1(y / 7.0, 91 + k) - 0.5))


def _right_shade(x, y, jitter=0.0):
    """Steps of right-hand shade at a pixel: 0 in the open, 1 in the street shade, 2 under the
    porch. `jitter` (the strata, -0.5..0.5) pushes the edges along the raked streaks."""
    if y < SHADE_Y0 + round(3 * (_noise1(x / 6.0, 93) - 0.5)):
        return 0
    return sum(1 for k in range(len(SHADE_LINES)) if x + SHADE_JITTER * jitter >= _shade_edge(y, k))


def _base_level(x, y, jitter=0.0):
    """Ramp position of the bare ground (0 = BROWN_BLACK ... 4 = RUST): whole steps only, so
    every change of colour is a hard, ragged edge."""
    v = FAR_LEVEL
    for k, (s, n, d) in enumerate(SEAMS):
        edge = s + n / 2.0 + round(SEAM_WANDER * (_noise1(x / 11.0, 81 + k) - 0.5)) - SEAM_JITTER * jitter
        if y >= edge:                                    # seams wander like drifted dust
            v += d
    X, _z = _street(x, y)
    if abs(X) > SIDE_X + SIDE_EDGE * (0.5 + 1.6 * jitter):
        v -= 1
    v -= _right_shade(x, y, jitter)
    return max(0, v)


def ground_colour(x, y, jitter=0.0):
    """Bare ground colour at a safe pixel (bands, side and porch shade, bottom rows). `jitter`
    (the strata, -0.5..0.5) pushes the band edges up or down along the raked streaks, so a seam
    reads as drifted dust, never as a ruled stripe."""
    if y >= SAFE_H - 1 or (y == SAFE_H - 2 and _noise1(x / 5.0, 84) > BOTTOM_WANDER):
        return "BROWN_BLACK"
    return RAMP[_base_level(x, y, jitter)]


def _path(x, y, jitter=0.0):
    """Strength (0..1) of the church door's path of lamplight at a pixel; 0 off the path."""
    if not PATH_Y0 <= y <= PATH_Y1:
        return 0.0
    X, z = _street(x, y)
    _X, z_top = _street(CX, PATH_TOP)
    _X, z_end = _street(CX, PATH_Y1)
    dz = max(0.0, z_top - z)
    u = abs(X) / (PATH_HW + PATH_SPREAD * dz)
    if u >= 1.0:
        return 0.0
    return (1.0 - u * u) * (1.0 - PATH_FADE * (dz / (z_top - z_end)) ** PATH_EASE) + PATH_RAG * jitter


def _path_colour(s):
    for cut, c in PATH_BANDS:
        if s > cut:
            return c
    return None


def _pool_level(x, y):
    best = 0.0
    for (cx, cy, rx, ry), g in zip(POOLS, POOL_GAIN):
        d = math.hypot((x - cx) / rx, (y - cy) / ry)
        if d < 1.0:
            best = max(best, g * min(1.0, (1.0 - d) / (1.0 - POOL_CORE)))
    return best


def _door(x, y):
    """Strength (0..1) of the church door's warm patch at a pixel: the lamplight spreads over
    the street in metres, so it follows the perspective like the path inside it."""
    if y < PATH_Y0:
        return 0.0
    X, z = _street(x, y)
    _X, z_door = _street(CX, PATH_TOP)
    d = math.hypot(X / DOOR_RX, max(0.0, z_door - z) / DOOR_RZ)
    return _clamp((1.0 - d) * DOOR_GAIN)


def _near_rock(x, y, m=1):
    return any(x0 - m <= x <= x1 + m and y0 - m <= y <= y1 + 2 + m for x0, y0, x1, y1 in ROCKS)


def _covered(x, y, margin=3):
    """True where the player, the near props or a UI box hide the ground."""
    if x < 80 and y > 330:
        return True
    if (x > 236 and y > 346) or (x > 228 and y > 438):
        return True                                  # rail, barrel, crate (left edge x 216..228)
    # the buttons' outer 3 px stay textured, so notched or rounded corners never show bare ground
    return any(x0 + margin <= x <= x1 - margin and y0 + margin <= y <= y1 - margin
               for x0, y0, x1, y1 in UI_BOXES)


def _in_box(x, y, boxes, m=0):
    return any(x0 - m <= x <= x1 + m and y0 - m <= y <= y1 + m for x0, y0, x1, y1 in boxes)


def _overlaps(r, boxes):
    return any(r[0] <= x1 and x0 <= r[2] and r[1] <= y1 and y0 <= r[3] for x0, y0, x1, y1 in boxes)


def _step_colour(base, step, pick, p):
    """The bare colour moved by a strata step (-1 shade, 0 bare, 1 lit, 2 lit top); `pick`
    (0..1, one value per streak) chooses between the dusty and the sunlit variant."""
    if step == 0 or base == "BROWN_BLACK":
        return base
    if step < 0:
        return DARKER[base]
    if base == "ORANGE":                             # already sunlit: only the crests turn OCHRE
        return "OCHRE" if step == 2 else base
    lit = LIGHTER[base]
    if lit == "ORANGE" and p < 0.2 and pick < 0.6:
        lit = "LEATHER"                              # bare dirt: dusty tops, not sparkle
    if step == 2 and lit == "ORANGE":
        return "OCHRE"
    return lit


def draw_ground(L, rng):
    y_top, y_bot = HY + 1, SAFE_H + OY           # safe rows drawn: the whole layer below the horizon
    xs = range(-OX, SAFE_W + OX)
    rows = y_bot - y_top
    names = np.empty((rows, W), dtype=object)
    pool = np.zeros((rows, W))
    keep = np.zeros((rows, W), dtype=bool)       # deliberate lone highlights the tidy leaves alone

    def put(x, y, c, hold=False):
        X, Y = int(x) + OX, int(y) - y_top
        if 0 <= X < W and 0 <= Y < rows:
            names[Y, X] = c
            keep[Y, X] = hold

    def at(x, y):
        X, Y = int(x) + OX, int(y) - y_top
        if 0 <= X < W and 0 <= Y < rows:
            return names[Y, X]
        return None

    def pool_at(x, y):
        X, Y = int(x) + OX, int(y) - y_top
        if 0 <= X < W and 0 <= Y < rows:
            return pool[Y, X]
        return 0.0

    # 1-3: bands, side and porch shade, the bottom rows
    x_lo, x_hi = -12, SAFE_W + 12                 # beyond these the overscan stays bare
    shade = np.zeros((rows, W))
    door = np.zeros((rows, W))
    ys_s = range(y_top - 1, SAFE_H + 1)
    S = {y: [_strata(x, y) for x in range(x_lo, x_hi)] for y in ys_s}
    for j in range(rows):
        y = y_top + j
        for x in xs:
            jit = (S[y][x - x_lo] - 0.5) if (y in S and x_lo <= x < x_hi) else 0.0
            names[j, x + OX] = ground_colour(x, y, jit)
            if y < SAFE_H and x_lo <= x < x_hi:
                pool[j, x + OX] = _pool_level(x, y)
                shade[j, x + OX] = _right_shade(x, y, jit)
                door[j, x + OX] = _door(x, y)

    # the raked strata: a streaky height field, lit where it rises toward the sun (the far
    # side of each ridge) and shaded where it falls toward the camera, so every ridge is a lit
    # streak over a dark one. Pools of low sun and the door light shift the cut toward lit,
    # the porch shade toward dark.
    for j in range(rows):
        y = y_top + j
        if y >= SAFE_H:
            break
        _cw, ch = _cells(y, *STRATA[0][:2])
        steps = []
        for i, x in enumerate(range(x_lo, x_hi)):
            e = (S[y + 1][i] - S[y - 1][i]) * min(ch, 2.0) * 0.5
            c = names[j, x + OX]
            p, sh, d = pool[j, x + OX], shade[j, x + OX], door[j, x + OX]
            score = K_EMBOSS * e + K_HEIGHT * (S[y][i] - 0.5) + POOL_SHIFT * p + DOOR_SHIFT * d \
                - (SHADE_SHIFT if sh >= 1 else 0.0) - (PORCH_SHIFT if sh >= 2 else 0.0) \
                - (FAR_SHIFT if y < SEAMS[0][0] else 0.0)
            if d > 0 and LV.get(c, 0) < LV["RUST"] and d * 0.9 + score > DOOR_CUT:
                names[j, x + OX] = c = LIGHTER[c]        # the door's warm patch, ragged like the dirt
            elif p > 0 and LV.get(c, 0) < LV["RUST"] and c != "BROWN_BLACK" and p * 0.8 + score > POOL_CUT:
                names[j, x + OX] = c = LIGHTER[c]        # sun on the darker bands lifts the dirt a step
            elif c == "RUST" and p * 0.8 + score > POOL_CUT_CORE:
                names[j, x + OX] = c = "ORANGE"          # the heart of a pool: sunlit dust underneath
            steps.append(-1 if score < CUT_DARK else (2 if score > CUT_TOP else (1 if score > CUT_LIT else 0)))
        # no lone pixels: a step shorter than 2 px takes its neighbours' value
        for i in range(1, len(steps) - 1):
            if steps[i] != steps[i - 1] and steps[i] != steps[i + 1]:
                steps[i] = steps[i - 1]
        run = 0
        for i, x in enumerate(range(x_lo, x_hi)):
            if i and steps[i] != steps[i - 1]:
                run += 1
            if steps[i]:
                names[j, x + OX] = _step_colour(names[j, x + OX], steps[i], _h(run, y, 37), pool[j, x + OX])

    # the church door's path of lamplight: stepped bands, ragged along the strata like the dirt,
    # no band narrower than 2 px in a row
    onpath = np.zeros((rows, W), dtype=bool)
    for y in range(PATH_Y0, PATH_Y1 + 1):
        cols = []
        for x in range(DOOR_X - 40, DOOR_X + 41):
            jit = 0.0
            if y in S:
                a, b = S[y][x - x_lo], S[y][2 * DOOR_X - x - x_lo]
                jit = PATH_SYM * 0.5 * (a + b) + (1.0 - PATH_SYM) * a - 0.5
            cols.append(_path_colour(_path(x, y, jit)))
        # a band 1 px wide takes the value on its outer side, the same rule on both halves
        for i in range(1, len(cols) - 1):
            if cols[i] != cols[i - 1] and cols[i] != cols[i + 1]:
                cols[i] = cols[i - 1] if i <= 40 else cols[i + 1]
        for i, c in enumerate(cols):
            if c:
                put(DOOR_X - 40 + i, y, c)
                onpath[y - y_top, DOOR_X - 40 + i + OX] = True
        # the door patch's lit streaks stop a step short of the path, so its outline stays its own
        on = [i for i, c in enumerate(cols) if c]
        if on:
            for x in list(range(DOOR_X - 40 + on[0] - PATH_EDGE, DOOR_X - 40 + on[0])) + \
                    list(range(DOOR_X - 40 + on[-1] + 1, DOOR_X - 40 + on[-1] + 1 + PATH_EDGE)):
                if at(x, y) == "OCHRE":
                    put(x, y, "ORANGE")

    def in_door(x, y):
        """On the door's path of light or right beside it: no clods, ruts or grass there."""
        if not PATH_Y0 <= y <= PATH_Y1 + 2:
            return False
        X = int(x) + OX
        return any(0 <= Y < rows and onpath[Y, max(0, X - 2):X + 3].any() for Y in (y - y_top, y - y_top - 2))

    def blocked(x, y):
        return _covered(x, y) or in_door(x, y) or _near_rock(x, y)

    # 4: clods and lumps, jittered in screen bands so no two share a row by design:
    # a short lit top, a shade row under it and a darker cast row toward the camera
    def clod(mx, my, n, h, near):
        c0 = at(mx + n // 2, my + 1)
        if c0 is None or c0 in ("BROWN_BLACK", "AMBER", "DUST"):
            return
        lit = LIGHTER.get(c0, "RUST")
        if lit == "ORANGE" and pool_at(mx, my) < 0.2 and _h(h, 7) < 0.6:
            lit = "LEATHER"
        shade = DARKER.get(c0, "BROWN")
        deep = "BROWN" if LV.get(c0, 3) >= 4 else ("BROWN_DARK" if c0 == "BROWN_MID" else
                                                   ("BROWN_BLACK" if near else "BROWN_DARK"))
        if deep == "BROWN" and pool_at(mx, my) > 0.3 and _h(h, 9) < 0.5:
            deep = "BROWN_DARK"                        # sunlit dust throws the hardest little shadows

        def run(x0, x1, y, c):
            for x in range(x0, x1):
                if not blocked(x, y):
                    put(x, y, c)

        if _h(h, 1) < 0.55:                            # clod: lit top, shade, cast row
            run(mx + 1, mx + n - 1, my, lit)
            run(mx, mx + n, my + 1, shade)
            k = max(2, min(4, n - 2))
            s = mx + (n - k) // 2 + (1 if _h(h, 2) < 0.5 else 0)
            run(s, s + k, my + 2 if n >= 4 else my + 1, deep)
        else:                                          # a pit or furrow: shade with a dark core
            run(mx, mx + n, my + 1, shade)
            k = max(2, min(4, n - 2))
            s = mx + (n - k) // 2
            run(s, s + k, my + 1, deep)
            run(mx + 1, mx + n, my + 2, shade) if n >= 5 and _h(h, 3) < 0.4 else None

    y0 = y_top + 3
    band = 0
    while y0 < SAFE_H - 3:
        _X, z = _street(CX, y0)
        hb = 3 if z > 6 else (4 if z > 2.4 else 6)
        lo, hi = (4, 8) if z < 3 else ((3, 5) if z < 10 else (2, 3))
        area = 150.0 - 80.0 * _clamp((y0 - HY) / (SAFE_H - HY))
        cw = area / hb
        x = -8 - _h(band, 50) * cw
        i = 0
        while x < SAFE_W + 8:
            for rep in range(2):                     # the pools get a second, darker helping
                h = _h(band, i, rep, 51) * 1e6
                mx = int(x + _h(h, 52) * cw * 0.7)
                my = y0 + int(_h(h, 53) * hb)
                n = lo + int(_h(h, 54) * (hi - lo + 1))
                if rep and pool_at(mx, my) < 0.35:
                    break
                _X, zz = _street(mx, my)
                if my < SAFE_H - 2 and not blocked(mx, my) and not blocked(mx + n - 1, my):
                    if not (_right_shade(mx, my) > 0.5 and _h(h, 55) < 0.5):   # sparse in the shade
                        clod(mx, my, n, h, zz < 1.6)
            x += cw
            i += 1
        y0 += hb
        band += 1

    # 5: wagon ruts, z 2..30 m only: a faint shade line far away, a soft patchy track near,
    # wandering a pixel either way
    for rx in (-1.6, 1.5):
        groove = set()
        for y in range(int(proj(0, 0, 30)[1]) + 1, int(proj(0, 0, 2)[1]) + 1):
            _X, z = _street(CX, y)
            xm = CX + F * rx / z + round(2 * (_noise1(y / 9.0, 47 + rx * 10) - 0.5))
            if z > 10:
                x = round(xm)
                c = at(x, y)
                if c and _h(y, rx * 10, 45) < 0.6 and not in_door(x, y):
                    put(x, y, DARKER.get(c, "BROWN"))
                continue
            if _h(y // 3, rx * 10, 44) < 0.45:
                continue                                  # the track is patchy, not ruled
            w = 2 if z > 4.5 else 3
            xa = int(round(xm - w / 2))
            for x in range(xa, xa + w):
                if not _covered(x, y) and not _near_rock(x, y):
                    groove.add((x, y))
        for x, y in sorted(groove):
            c = at(x, y)
            core = (x - 1, y) in groove and (x + 1, y) in groove and _right_shade(x, y) < 0.5
            put(x, y, DARKER.get(DARKER.get(c, "BROWN"), "BROWN_DARK") if core else DARKER.get(c, "BROWN"))
        for x, y in sorted(groove):
            if not any((x, y - k) in groove for k in (1, 2, 3)) and _h(x, y, 46) < 0.5 \
                    and _right_shade(x, y) < 0.5:
                c = at(x, y - 1)
                if c:
                    put(x, y - 1, LIGHTER.get(c, "RUST"))

    # 6: hoof prints by the hitching rail and down the street: a dark crescent with a lit lip
    for k in range(9):
        X = 0.9 + _h(k, 71) * 1.6
        z = 1.9 + _h(k, 72) * 5.5
        x, y = proj(X, 0, z)
        x, y = int(round(x)), int(round(y))
        if y > 505 or blocked(x, y) or blocked(x - 2, y) or blocked(x + 2, y):
            continue
        c = at(x, y)
        if c is None:
            continue
        w = 1 if z > 3.2 else 2
        dark = "BROWN_DARK" if LV.get(c, 4) <= 4 else "BROWN"
        for i in range(-w + 1, w):
            put(x + i, y, dark)
        put(x - w, y + 1, dark)
        put(x + w, y + 1, dark)
        for i in range(-w + 1, w):
            put(x + i, y + 1, DARKER.get(c, "BROWN"))
            put(x + i, y + 2, "OCHRE", hold=True)

    # a handful of the brightest specks in the pool cores catch the sun full on (DUST)
    for cx, cy, rx, ry in POOLS[1:]:
        for k in range(4):
            x = int(cx + (_h(cx, k, 91) - 0.5) * rx * 0.9)
            y = int(cy + (_h(cx, k, 92) - 0.5) * ry * 0.9)
            for dy in range(4):
                if at(x, y + dy) in ("ORANGE", "OCHRE") and at(x + 1, y + dy) in ("ORANGE", "OCHRE") \
                        and not blocked(x, y + dy) and not blocked(x + 1, y + dy):
                    put(x, y + dy, "DUST")
                    put(x + 1, y + dy, "DUST")
                    break

    # 7: pebbles, more of them toward the camera: a dark body two or three pixels wide, its
    # crown on the side facing the sun (a few catch it full on: DUST), the bigger ones with a
    # BROWN_BLACK shadow toward the camera
    placed = 0
    tries = 0
    while placed < 40 and tries < 2000:
        tries += 1
        u = rng.random()
        y = int(304 + 278 * (u ** 0.55))
        x = rng.randint(80, 236)
        if blocked(x, y) or blocked(x + 2, y) or y > SAFE_H - 4 or _near_rock(x, y, 3):
            continue
        w = 3 if (y > 420 and rng.random() < 0.6) else 2
        crown = "DUST" if rng.random() < 0.25 else "OCHRE"
        for i in range(w):
            put(x + i, y, "BROWN_DARK", hold=True)
        for i in range(w - 1):
            put(x + i + (1 if x < 155 else 0), y - 1, crown, hold=True)
        if w == 3:
            for i in range(2):
                put(x + i + (1 if x >= 155 else 0), y + 1, "BROWN_BLACK", hold=True)
        placed += 1

    # 8: rocks: backlit mounds. The face toward the camera is in shade (BROWN_MID on the sun
    # side, BROWN away from it), the top edge catches the low sun (OCHRE, a DUST crown, ORANGE
    # down the flank facing x 155 where the sun sits), the bottom and far flank close in
    # BROWN_DARK, and a BROWN_BLACK shadow falls straight toward the camera.
    for x0, y0, x1, y1 in ROCKS:
        w, h = x1 - x0 + 1, y1 - y0 + 1
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        rx, ry = w / 2.0, h / 2.0 + 0.35
        sun = 1 if cx < 155 else -1                 # which flank faces the sun: +1 right
        inside = set()
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                u, v = (x - cx) / rx, (y - cy) / ry
                if u * u + v * v <= 1.0 or (y == y1 and abs(u) < 0.85) or (y > cy and abs(u) < 0.7):
                    inside.add((x, y))
        for x, y in sorted(inside):
            top = (x, y - 1) not in inside
            bottom = (x, y + 1) not in inside
            s_side = (x + sun, y) not in inside
            a_side = (x - sun, y) not in inside
            lit_half = (x - cx) * sun > -0.5
            if bottom:
                c = "BROWN_DARK"
            elif top:
                c = "OCHRE"
            elif s_side:
                c = "ORANGE"
            elif a_side:
                c = "BROWN_DARK" if h >= 4 else "BROWN"
            elif (x, y - 2) not in inside and lit_half:
                c = "ORANGE" if h >= 4 else "BROWN_MID"
            else:
                c = "BROWN_MID" if lit_half else "BROWN"
            put(x, y, c, hold=True)
        tops = sorted((x for x, y in inside if (x, y - 1) not in inside and y == y0), key=lambda x: -x * sun)
        for x in tops[1:2 if w < 7 else 3]:
            put(x, y0, "DUST", hold=True)
        for j in range(2 if h >= 4 else 1):
            a, b = x0 + j - sun, x1 - j - sun - (1 if j == 0 and w < 6 else 0)
            for x in range(min(a, b), max(a, b) + 1):
                put(x, y1 + 1 + j, "BROWN_BLACK" if j == 0 else "BROWN_DARK")

    # 9: dry grass: tufts of 1 px blades fanning out of a black root, BROWN_DARK and BROWN_BLACK
    # blades in front of BROWN ones, backlit tips, a dark row of shadow toward the camera
    def blade(bx, by, dx, hgt, col, tip, tip2, lit_top=False):
        pts = []
        n = max(hgt, abs(dx)) * 2
        for i in range(n + 1):
            t = i / float(n)
            x = bx + round(dx * t * t * 0.6 + dx * t * 0.4)
            y = by - round(hgt * t)
            if not pts or pts[-1] != (x, y):
                pts.append((x, y))
        for k, (x, y) in enumerate(pts):
            if _covered(x, y, 0) or in_door(x, y):
                continue
            last = len(pts) - 1 - k
            tip_px = 1 if len(pts) >= 4 else 0             # the tip is two pixels long when it can be
            if lit_top and k >= len(pts) // 2:
                put(x, y, tip if last <= tip_px else tip2, hold=True)
            else:
                c = tip if last <= tip_px else (tip2 if last == tip_px + 1 and len(pts) >= 6 else col)
                put(x, y, c, hold=True)

    def tuft(bx, by, hpx, h):
        c0 = at(bx, by)
        if c0 is None:
            return
        lit_ground = pool_at(bx, by) > 0.3 or LV.get(c0, 3) >= 4
        nb = 4 + int(_h(h, 1) * 3) + hpx // 2 + hpx // 4 * 2
        spread = hpx * (0.5 + 0.3 * _h(h, 5))
        # the root: a dark mound under the blades, its shadow a row lower
        rw = max(2, int(hpx * 0.6))
        for x in range(bx - rw // 2, bx - rw // 2 + rw):
            if not _covered(x, by, 0):
                put(x, by, "BROWN_BLACK")
                if hpx >= 5 and not _covered(x, by + 1, 0):
                    put(x, by + 1, "BROWN_DARK")
            if hpx >= 8 and abs(x - bx + 0.5) < rw / 2 - 1 and not _covered(x, by - 1, 0):
                put(x, by - 1, "BROWN_BLACK")
        order = sorted(range(nb), key=lambda b: _h(h, b, 4))
        for r, b in enumerate(order):
            f = b / max(1, nb - 1) * 2 - 1                  # -1 .. 1 across the fan
            dx = round(f * spread + (_h(h, b, 2) - 0.5) * 2)
            hgt = max(2, round(hpx * (0.55 + 0.45 * _h(h, b, 3)) * (1.0 - 0.35 * abs(f))))
            front = r >= nb // 2
            if not front and _h(h, b, 8) < 0.45:         # a backlit straw: lit along its top half
                col = "BROWN_MID" if lit_ground else "BROWN"
                tip, tip2 = ("OCHRE", "ORANGE") if lit_ground else ("ORANGE", "RUST")
                blade(bx + round(f * rw * 0.4), by - 1, dx, hgt, col, tip, tip2, lit_top=True)
                continue
            col = ("BROWN_BLACK" if _h(h, b, 6) < 0.5 else "BROWN_DARK") if front else "BROWN"
            tip = "RUST" if (not lit_ground or _h(h, b, 7) < 0.5) else "ORANGE"
            blade(bx + round(f * rw * 0.4), by - 1, dx, hgt, col, tip, col)

    spots = []
    for k in range(14):                          # the right verge, from under the horse to the crate
        spots.append((int(197 + _h(k, 82) * 38), int(340 + _h(k, 81) * 176), 1))
    for k in range(26):                          # the near band between the buttons and icons
        spots.append((int(84 + _h(k, 84) * 138), int(508 + (_h(k, 83) ** 0.7) * 74), 1))
    for k in range(10):                          # the far verges, small
        y = int(300 + _h(k, 85) * 30)
        X = (3.2 + _h(k, 86) * 3.0) * (1 if _h(k, 87) < 0.5 else -1)
        spots.append((int(round(proj(X, 0, _street(CX, y)[1])[0])), y, 0))
    done = []
    for k, (x, y, big) in enumerate(spots):
        _X, z = _street(x, y)
        hpx = max(2, min(21, round((0.06 + (0.07 if big else 0.03) * _h(k, 88)) * F / z)))
        if y >= SAFE_H - 1 or _covered(x, y, 0) or _near_rock(x, y, 3) or in_door(x, y):
            continue
        reach = int(hpx * 0.8) + 2               # how far the blades fan out to the sides
        fan = (x - reach, y - hpx - 1, x + reach, y + 1)
        if _in_box(x, y, CAPTIONS, 2) or _in_box(x, y - hpx // 2, UI_BOXES) or \
                _overlaps(fan, CAPTIONS) or _overlaps(fan, ROCKS):
            continue                                 # no blades over a caption or a rock
        if any(abs(x - a) < 3 + hpx * 0.8 and abs(y - b) < 2 + hpx // 2 for a, b in done):
            continue
        done.append((x, y))
        tuft(x, y, hpx, _h(k, 89) * 1e6)

    # 10: tidy: a lone pixel (no neighbour of its colour, diagonals included) that is not a
    # deliberate highlight (a blade, a pebble, a rock, a hoof print's lip) takes the colour most
    # of its four neighbours share, the row neighbours first on a tie, so every texture mark is
    # a cluster of two or more pixels
    order = sorted(set(names.ravel()))
    grid = np.zeros((rows, W), dtype=np.int32)
    for i, n in enumerate(order):
        grid[names == n] = i
    for _pass in range(2):
        pad = np.pad(grid, 1, mode="edge")
        same = np.zeros((rows, W), dtype=np.int32)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy or dx:
                    same += pad[1 + dy:1 + dy + rows, 1 + dx:1 + dx + W] == grid
        new = grid.copy()
        for Y, X in zip(*np.nonzero((same == 0) & ~keep)):
            nb = [pad[Y + 1, X], pad[Y + 1, X + 2], pad[Y, X + 1], pad[Y + 2, X + 1]]
            new[Y, X] = max(nb, key=lambda v: (nb.count(v), -nb.index(v)))
        grid = new
    # two simultaneous passes can leave a pair of lone neighbours that swapped colours: a last
    # pass in reading order settles each against the grid as it already stands (giving a lone
    # pixel its neighbour's colour never leaves another pixel alone, so one pass is enough)
    pad = np.pad(grid, 1, mode="edge")
    same = np.zeros((rows, W), dtype=np.int32)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy or dx:
                same += pad[1 + dy:1 + dy + rows, 1 + dx:1 + dx + W] == grid
    for Y, X in zip(*np.nonzero((same == 0) & ~keep)):
        if (pad[Y:Y + 3, X:X + 3] == pad[Y + 1, X + 1]).sum() > 1:
            continue                                 # an earlier fix already joined it up
        nb = [pad[Y + 1, X], pad[Y + 1, X + 2], pad[Y, X + 1], pad[Y + 2, X + 1]]
        pad[Y + 1, X + 1] = max(nb, key=lambda u: (nb.count(u), -nb.index(u)))
    grid = pad[1:-1, 1:-1].copy()

    # write the grid into the layer in one go
    arr = np.zeros((rows, W, 4), dtype=np.uint8)
    for i, n in enumerate(order):
        arr[grid == i] = P.rgb(n, 0.0) + (255,)
    sub = Image.fromarray(arr, "RGBA")
    L.im.paste(sub, (0, y_top + OY))
