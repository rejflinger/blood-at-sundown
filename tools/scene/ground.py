"""The street and ground: dusty rust dirt in a dark frame, lit by the church door and by a few
patches of low sun, raked into soft horizontal strata, scattered with clods, dry grass, a few
rocks and a pair of soft wagon ruts.

Value story (backlit dusk): colour bands joined by short Bayer seams that the strata break up,
so no seam reads as a ruled stripe. The far street and the right side sit a step darker in the
buildings' shade; the near rows sink to BROWN. The dirt is a streaky height field laid in street
metres (so the strata flatten and shrink with distance), lit where it rises toward the sun and
shaded where it falls toward the camera, then cut at hard thresholds into a shade step, the bare
ground and a lit step. The pools of low sun and the door light lift the dirt in ragged patches
and shift that balance toward the lit step, so the light reads as raked dust, never as a
checkerboard or a glossy sheet. On top: clods and lumps (a lit top, a shade row, a darker cast
row), dry grass with backlit tips, pebbles and rocks. DUST (a swapped entry) marks rock crowns,
pebble tops and a few specks, so the lit ground follows the duel palette from gold to deep red.
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
# seams (first row, length, step): far street up to RUST behind PLAY, then down toward the camera
SEAMS = [(321, 8, +1), (528, 8, -1), (564, 8, -1), (577, 8, -1)]
BOTTOM_ROWS, BOTTOM_LEVEL = 3, 0.25    # last visible rows: BROWN_BLACK at 25 %
SIDE_X, SIDE_EDGE = 4.5, 1.25          # street half width in metres, Bayer edge width
SEAM_JITTER = 3.0                      # how much the strata break up the Bayer seams
# right-hand shade from the porch and the horse: rows, depth in ramp steps
SHADE_Y0, SHADE_Y1, SHADE_SEAM = 314, 400, 8
SHADE_DEPTH, PORCH_X, PORCH_DEPTH, PORCH_SHIFT = 1.0, 212, 1.0, 0.06
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
# the church door: doorstep rows, and the soft warm patch it throws on the street
DOOR_X, DOOR_Y0, DOOR_Y1 = 140, 297, 303
DOOR_PATCH = (140, 300, 22, 18)        # centre x, top row, half width, depth in rows
DOOR_SHIFT, DOOR_CUT = 0.16, 0.55      # how far the door light shifts the strata; where it lifts the base
# rocks: exact bounding boxes x0, y0, x1, y1 (the cast shadow goes below the box)
ROCKS = [(196, 419, 204, 423), (228, 432, 234, 435), (197, 466, 201, 468), (179, 521, 187, 525),
         (114, 529, 119, 531), (202, 545, 210, 549), (168, 317, 171, 318)]
# where the UI and the near props cover the street: no detail is spent there
UI_BOXES = [(78, 322, 193, 359), (78, 366, 193, 395), (78, 402, 193, 431), (78, 454, 193, 483),
            (78, 490, 193, 519), (16, 526, 47, 557), (132, 526, 163, 557), (222, 526, 253, 557)]
CAPTIONS = [(128, 559, 168, 571), (200, 559, 256, 571)]
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


def _shade_edge(y):
    """Left edge of the right-hand shade on row y (it wanders a little)."""
    return 184 + (y - SHADE_Y0) * 0.1 + round(4 * (_noise1(y / 7.0, 91) - 0.5))


def _right_shade(x, y):
    if y < SHADE_Y0 - 6 or y > SHADE_Y1 + SHADE_SEAM:
        return 0.0
    a = _clamp((x - _shade_edge(y) + 0.5) / 5.0)
    a *= 1.0 - _clamp((y - SHADE_Y1 + 0.5) / SHADE_SEAM)
    return a * (SHADE_DEPTH + PORCH_DEPTH * _clamp((x - PORCH_X + 0.5) / 6.0))


def _base_level(x, y):
    """Continuous ramp position of the bare ground (0 = BROWN_BLACK ... 4 = RUST)."""
    v = float(FAR_LEVEL)
    for k, (s, n, d) in enumerate(SEAMS):
        ys = y + round(5 * (_noise1(x / 11.0, 81 + k) - 0.5))   # seams wander like drifted dust
        v += d * _clamp((ys - s + 0.5) / n)
    X, _z = _street(x, y)
    v -= _clamp((abs(X) - SIDE_X) / SIDE_EDGE)
    v -= _right_shade(x, y)
    return max(0.0, v)


def ground_colour(x, y, jitter=0.0):
    """Bare ground colour at a safe pixel (bands, side and porch shade, bottom rows). `jitter`
    nudges the Bayer threshold inside a seam, so a seam breaks up along the raked strata
    instead of reading as a ruled stripe."""
    if y >= SAFE_H:
        return "BROWN_BLACK"
    v = _base_level(x, y)
    i = int(v)
    f = v - i
    if 0.0 < f < 1.0:
        f += jitter
    if i + 1 < len(RAMP) and dith(x + OX, y + OY, f):
        i += 1
    if y >= SAFE_H - BOTTOM_ROWS and dith(x + OX, y + OY, BOTTOM_LEVEL):
        return "BROWN_BLACK"
    return RAMP[i]


def _pool_level(x, y):
    best = 0.0
    for (cx, cy, rx, ry), g in zip(POOLS, POOL_GAIN):
        d = math.hypot((x - cx) / rx, (y - cy) / ry)
        if d < 1.0:
            best = max(best, g * min(1.0, (1.0 - d) / (1.0 - POOL_CORE)))
    return best


def _door(x, y):
    """Strength (0..1) of the church door's warm patch at a pixel."""
    cx, top, hw, depth = DOOR_PATCH
    if y < top - 3 or y > top + depth:
        return 0.0
    t = _clamp((y - top) / depth)
    w = hw * (0.45 + 0.55 * min(1.0, t * 2.2))       # the patch widens out of the door
    d = math.hypot((x - cx) / w, t)
    if d >= 1.0:
        return 0.0
    return min(1.0, (1.0 - d) * 1.6)


def _near_rock(x, y, m=1):
    return any(x0 - m <= x <= x1 + m and y0 - m <= y <= y1 + 2 + m for x0, y0, x1, y1 in ROCKS)


def _covered(x, y, margin=3):
    """True where the player, the near props or a UI box hide the ground."""
    if x < 80 and y > 330:
        return True
    if (x > 236 and y > 346) or (x > 224 and y > 438):
        return True                                  # rail, barrel, crate
    # the buttons' outer 3 px stay textured, so notched or rounded corners never show bare ground
    return any(x0 + margin <= x <= x1 - margin and y0 + margin <= y <= y1 - margin
               for x0, y0, x1, y1 in UI_BOXES)


def _in_box(x, y, boxes, m=0):
    return any(x0 - m <= x <= x1 + m and y0 - m <= y <= y1 + m for x0, y0, x1, y1 in boxes)


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

    def put(x, y, c):
        X, Y = int(x) + OX, int(y) - y_top
        if 0 <= X < W and 0 <= Y < rows:
            names[Y, X] = c

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
            jit = SEAM_JITTER * (S[y][x - x_lo] - 0.5) if (y in S and x_lo <= x < x_hi) else 0.0
            names[j, x + OX] = ground_colour(x, y, jit)
            if y < SAFE_H and x_lo <= x < x_hi:
                pool[j, x + OX] = _pool_level(x, y)
                shade[j, x + OX] = min(1.0, _right_shade(x, y))
                if y <= DOOR_PATCH[1] + DOOR_PATCH[3]:
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
                - sh * (SHADE_SHIFT + PORCH_SHIFT * _clamp((x - PORCH_X + 0.5) / 6.0)) - (FAR_SHIFT if y < SEAMS[0][0] else 0.0)
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

    # the doorstep: a short spill right under the church door, AMBER only in its first rows
    for y in range(DOOR_Y0, DOOR_Y1 + 1):
        k = y - DOOR_Y0
        hw = (1.5, 2.5, 3.0, 3.5, 3.5, 3.0, 2.0)[k]
        for x in range(int(DOOR_X - hw - 1), int(DOOR_X + hw + 2)):
            dx = abs(x - DOOR_X + 0.5)
            if dx > hw:
                continue
            if k <= 3 and dx <= hw - 1.0:
                put(x, y, "AMBER")
            else:
                put(x, y, "ORANGE")

    def in_door(x, y):
        return y <= DOOR_Y1 + 1 and abs(x - DOOR_X) <= 3 + (y - DOOR_Y0) * 0.6

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
        for x, y in groove:
            c = at(x, y)
            core = (x - 1, y) in groove and (x + 1, y) in groove and _right_shade(x, y) < 0.5
            put(x, y, DARKER.get(DARKER.get(c, "BROWN"), "BROWN_DARK") if core else DARKER.get(c, "BROWN"))
        for x, y in groove:
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
            put(x + i, y + 2, "OCHRE")

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

    # 7: pebbles, more of them toward the camera; a few crowns catch the sun (DUST)
    placed = 0
    tries = 0
    while placed < 40 and tries < 2000:
        tries += 1
        u = rng.random()
        y = int(304 + 278 * (u ** 0.55))
        x = rng.randint(80, 236)
        if blocked(x, y) or blocked(x + 1, y) or y > SAFE_H - 4 or _near_rock(x, y, 3):
            continue
        w = 2 if (y > 420 and rng.random() < 0.6) else 1
        for i in range(w):
            put(x + i, y, "BROWN_DARK")
        put(x + (w - 1 if x < 155 else 0), y - 1, "DUST" if rng.random() < 0.25 else "OCHRE")
        if w == 2:
            put(x + (1 if x >= 155 else 0), y + 1, "BROWN_BLACK")
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
        for x, y in inside:
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
            put(x, y, c)
        tops = sorted((x for x, y in inside if (x, y - 1) not in inside and y == y0), key=lambda x: -x * sun)
        for x in tops[1:2 if w < 7 else 3]:
            put(x, y0, "DUST")
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
            if lit_top and k >= len(pts) // 2:
                put(x, y, tip if last == 0 else tip2)
            else:
                put(x, y, tip if last == 0 else (tip2 if last == 1 and len(pts) >= 6 else col))

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
        if _in_box(x, y, CAPTIONS, 2) or _in_box(x, y - hpx // 2, UI_BOXES):
            continue
        if any(abs(x - a) < 3 + hpx * 0.8 and abs(y - b) < 2 + hpx // 2 for a, b in done):
            continue
        done.append((x, y))
        tuft(x, y, hpx, _h(k, 89) * 1e6)

    # write the grid into the layer in one go
    lut = {n: P.rgb(n, 0.0) + (255,) for n in set(names.ravel())}
    arr = np.zeros((rows, W, 4), dtype=np.uint8)
    for n, c in lut.items():
        arr[names == n] = c
    sub = Image.fromarray(arr, "RGBA")
    L.im.paste(sub, (0, y_top + OY))
