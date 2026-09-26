"""The player seen from behind in the lower left (title framing).

Backlit: the sun is to the right of the figure, so every face turned to the camera is dark
(INK, BROWN_BLACK, CHARCOAL, TEAL_DARK) and the shape reads through 1 px RIM lines on its
right-hand and top edges, the rust pattern band of the poncho and the tan fringe. The owner
lets the title buttons (scripts/ui.gd: x 78..193, y 318..511) overlap the figure: the hat
brim tip ends above PLAY (x 85 at most, clear of the lantern and the wagon), the right
shoulder and the sleeve run under the button column, and the gun and holster (x 53..74) and
the gloved fist (x 78..97, from y 512) hang clear of it.
"""
import math

import numpy as np

from scene.common import *  # noqa: F401,F403


# ---------------------------------------------------------------- small helpers
def _lerp_pts(pts, x):
    """Piecewise linear y(x) through pts sorted by x (extrapolates at both ends)."""
    if x <= pts[0][0]:
        (x0, y0), (x1, y1) = pts[0], pts[1]
    elif x >= pts[-1][0]:
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
    else:
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if x0 <= x <= x1:
                break
    return y0 + (y1 - y0) * (x - x0) / float(x1 - x0)


def _alpha(L):
    return np.array(L.im)[:, :, 3] > 0


def _merge(dst, src):
    dst.im.alpha_composite(src.im)


def _rim_right(L, y0, y1, cols=("RIM", "OCHRE"), xmin=-200, xmax=400):
    """Paints the rightmost opaque pixels of each row (the edge facing the sun)."""
    a = _alpha(L)
    lo = max(0, xmin + OX)
    for y in range(y0, y1 + 1):
        xs = np.nonzero(a[y + OY, lo:min(W, xmax + OX + 1)])[0]
        if len(xs) == 0:
            continue
        x = int(xs[-1]) + lo - OX
        for k, c in enumerate(cols):
            if c:
                L.px(x - k, y, c)


def _rim_top(L, x0, x1, cols=("RIM", "OCHRE"), ymin=-200, ymax=800):
    """Paints the topmost opaque pixels of each column."""
    a = _alpha(L)
    lo = max(0, ymin + OY)
    for x in range(x0, x1 + 1):
        ys = np.nonzero(a[lo:min(H, ymax + OY + 1), x + OX])[0]
        if len(ys) == 0:
            continue
        y = int(ys[0]) + lo - OY
        for k, c in enumerate(cols):
            if c:
                L.px(x, y + k, c)


def _clear_poly(L, pts):
    L.d.polygon([(round(x) + OX, round(y) + OY) for x, y in pts], fill=(0, 0, 0, 0))


def _seg_dist(px, py, a, b):
    """Distance from the pixel grids px, py to the segment a-b."""
    (ax, ay), (bx, by) = a, b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = np.clip(((px - ax) * dx + (py - ay) * dy) / L2, 0.0, 1.0)
    qx, qy = ax + t * dx, ay + t * dy
    return np.hypot(px - qx, py - qy)


def _poly_dist(px, py, pts):
    d = np.full(px.shape, 1e9)
    for a, b in zip(pts, pts[1:]):
        d = np.minimum(d, _seg_dist(px, py, a, b))
    return d


def _bez(p0, p1, p2, n=10):
    """A quadratic Bezier arc sampled into a polyline."""
    out = []
    for i in range(n + 1):
        t = i / float(n)
        u = 1 - t
        out.append((u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                    u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]))
    return out


def _crescent(L, pts, w, c, toward=(1.0, -1.0), span=(0.0, 1.0)):
    """A tapered fold: the polyline pts thickened on the side facing `toward` (the light) to
    about w px at its middle and to nothing at both ends, filled as one polygon, so the fold
    is a solid 4-connected shape that steps cleanly. With span=(t0, t1) only the outer edge
    between those fractions of its length is drawn, as a 1 px line (the lit crest)."""
    ls = [0.0]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        ls.append(ls[-1] + math.hypot(x1 - x0, y1 - y0))
    outer = []
    for i, (x, y) in enumerate(pts):
        (ax, ay), (bx, by) = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
        dx, dy = bx - ax, by - ay
        n = math.hypot(dx, dy) or 1.0
        nx, ny = dy / n, -dx / n
        if nx * toward[0] + ny * toward[1] < 0:
            nx, ny = -nx, -ny
        wi = w * math.sin(math.pi * ls[i] / ls[-1])
        outer.append((x + nx * wi, y + ny * wi))
    if span == (0.0, 1.0):
        L.poly(list(pts) + outer[::-1], c)
    else:
        L.line([p for p, s in zip(outer, ls) if span[0] <= s / ls[-1] <= span[1]], c)


def _sprite(L, x0, y0, rows, key):
    """Stamps a small hand-laid pixel map: one character per pixel, '.' is left alone."""
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch != "." and ch in key:
                L.px(x0 + i, y0 + j, key[ch])


def _dz(x, y, level):
    """Ordered dither anchored to the layer canvas (x + OX, y + OY), like every other layer, so
    the player's dithers stay in phase with the street behind it."""
    return dith(x + OX, y + OY, level)


def _vnoise(x, y, cell, seed):
    """Coherent value noise read per pixel: hashed values on a `cell` px grid, blended with a
    smoothstep, so thresholded marks are soft blobs with 1 px stepped edges, never blocks."""
    gx, gy = x / float(cell), y / float(cell)
    ix, iy = int(math.floor(gx)), int(math.floor(gy))
    fx, fy = gx - ix, gy - iy
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = hsh(ix, iy, seed), hsh(ix + 1, iy, seed)
    c, d = hsh(ix, iy + 1, seed), hsh(ix + 1, iy + 1, seed)
    top, bot = a + (b - a) * fx, c + (d - c) * fx
    return top + (bot - top) * fy


def _despeckle(L, x0, y0, x1, y1, names, passes=2):
    """Clusters, not salt and pepper: a pixel of one of `names` with no 8-neighbour of its own
    colour takes the most common colour around it (ties go to the earlier palette entry)."""
    rev = {P.rgb(n): n for n in P.NAMES}
    for _ in range(passes):
        arr = np.array(L.im)
        changes = []
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                X, Y = x + OX, y + OY
                if not (1 <= X < W - 1 and 1 <= Y < H - 1) or arr[Y, X, 3] == 0:
                    continue
                cur = rev.get(tuple(int(v) for v in arr[Y, X, :3]))
                if cur not in names:
                    continue
                count = {}
                alone = True
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        p = arr[Y + dy, X + dx]
                        if p[3] == 0:
                            continue
                        n = rev.get(tuple(int(v) for v in p[:3]))
                        if n == cur:
                            alone = False
                            break
                        count[n] = count.get(n, 0) + 1
                    if not alone:
                        break
                if alone and count:
                    best = sorted(count.items(), key=lambda kv: (-kv[1], P.IDX[kv[0]]))[0][0]
                    changes.append((x, y, best))
        for x, y, n in changes:
            L.px(x, y, n)


# ---------------------------------------------------------------- figure geometry
# top contour of the poncho (neck, shoulders, the right side under the buttons) and the hem,
# which runs from the back point up to the right, steepening as it wraps round the arm
PONCHO_TOP = [(-60, 366), (-40, 358), (-20, 352), (0, 348), (10, 344), (20, 340), (32, 336),
              (44, 334), (58, 333), (68, 334), (76, 337), (84, 342), (91, 350), (95, 358),
              (97, 368), (98, 382), (98, 392)]
HEM = [(10, 462), (20, 457), (35, 449), (50, 438), (65, 424), (80, 410), (98, 394)]
HEM_TIP = HEM[0]


def hem_y(x):
    """Lower edge of the poncho: up to the right from the back point, and rising again to
    the left of it (the second half of the V)."""
    if x >= HEM_TIP[0]:
        return _lerp_pts(HEM, x)
    return HEM_TIP[1] - (HEM_TIP[0] - x) * 0.75


def top_y(x):
    return _lerp_pts(PONCHO_TOP[:13], x)


def chevron_y(x):
    """The shoulder pattern row: low on the shaded left, arching up over the right shoulder."""
    return _lerp_pts([(-60, 392), (-30, 380), (0, 372), (15, 373), (30, 370), (45, 365),
                      (60, 359), (75, 355), (86, 357), (95, 363)], x)


# ---------------------------------------------------------------- parts
def _legs(rng):
    """Dark trousers: a big rounded seat, the left thigh under it, the right leg with its lit
    outer contour, and a wedge of street between the legs right of the STATS icon. The cloth
    is BROWN_BLACK with soft BROWN_DARK light where a form turns up toward the sun (coherent
    noise read per pixel, so the marks are blobs on the 1 px grid), curved fold ridges and INK
    creases, and a RIM line down the sunward leg."""
    L = Layer()
    L.poly([(-60, 486), (84, 486), (85, 520), (87, 560), (89, 640), (-60, 640)], "BROWN_BLACK")
    gap = [(53, 543), (56, 560), (61, 584), (66, 640), (44, 640), (47, 584), (50, 560)]
    _clear_poly(L, gap)

    # rounded forms, each lit on its upper right: the seat, the left thigh, the right leg
    forms = [(28, 508, 46, 26, 1.0), (14, 566, 34, 26, 0.85), (72, 546, 15, 44, 0.85),
             (-30, 540, 22, 40, 0.4), (74, 604, 12, 34, 0.55), (16, 616, 28, 26, 0.5)]

    def form_shade(x, y, c):
        if c != "BROWN_BLACK":
            return None
        lit = 0.0
        for (cx, cy, rx, ry, k) in forms:
            u, v = (x - cx) / float(rx), (y - cy) / float(ry)
            r = u * u + v * v
            if r > 1.0:
                continue
            lit = max(lit, k * (1.0 - r) * (0.5 + 0.9 * max(0.0, (u - v) * 0.5)))
        if lit <= 0.0:
            return None
        # worn cloth: a fine weave of soft blobs over a broad swell, both read per pixel
        n = 0.7 * _vnoise(x, y, 3, 41) + 0.3 * _vnoise(x, y, 7, 42)
        val = lit * 1.1 + (n - 0.5) * 0.4
        if val > 0.98 and _vnoise(x, y, 2, 44) > 0.55:
            return "BROWN"
        if val > 0.52:
            return "BROWN_DARK"
        return None
    L.recolour(-60, 486, 92, 640, form_shade)
    # the gloved hand shades the thigh beside it, so the dark glove reads against dark cloth
    L.recolour(72, 506, 92, 548, lambda x, y, c: "BROWN_BLACK" if c == "BROWN_DARK" and
               ((x - 82) / 9.0) ** 2 + ((y - 526) / 20.0) ** 2 < 1.0 else None)

    # fold ridges: tapered BROWN_DARK crescents lit on the side facing the sun, with a BROWN
    # crest along their middle. They run on the diagonal (the cloth pulled from the seam up
    # round the seat, across the thigh, down the right leg), so no crest lies flat for long.
    ridges = [
        (_bez((47, 528), (36, 513), (17, 506), 12), 3, 1),        # seam up round the seat
        (_bez((56, 517), (50, 503), (38, 494), 10), 2, 1),        # the seat turning to the hip
        (_bez((28, 562), (14, 556), (-4, 546), 12), 3, 1),        # left thigh, below the icon
        (_bez((24, 584), (12, 574), (-2, 568), 10), 2, 0),
        (_bez((68, 530), (72, 548), (74, 568), 10), 2, 1),        # right leg, under the holster
        (_bez((78, 542), (82, 560), (82, 586), 10), 2, 1),
    ]
    for pts, w, crest in ridges:
        _crescent(L, pts, w, "BROWN_DARK")
        if crest:
            _crescent(L, pts, w, "BROWN", span=(0.3, 0.7))
    # creases: INK valleys, each a curve on the diagonal or round a form, with a CHARCOAL lip
    # on the side away from the light
    creases = [
        (_bez((50, 537), (26, 546), (-8, 528), 14), 1),           # under the seat, round it
        (_bez((34, 580), (16, 584), (-6, 592), 10), 0),           # toward the knee
        (_bez((8, 494), (13, 506), (12, 520), 8), 0),             # down the left of the seat
        (_bez((46, 530), (26, 523), (6, 508), 10), 1),            # a pull round the seat
        (_bez((60, 526), (64, 540), (64, 558), 8), 1),
        (_bez((66, 572), (68, 590), (72, 620), 8), 1),
    ]
    for pts, lip in creases:
        ip = [(round(x), round(y)) for x, y in pts]
        L.line(ip, "INK")
        if lip:
            L.line([(x, y + 1) for x, y in ip[2:-2]], "CHARCOAL")
    # the seam where the legs part, running down from the seat into the gap
    L.line([(50, 510), (51, 526), (52, 543)], "INK")
    L.line([(49, 516), (50, 540)], "CHARCOAL")
    _despeckle(L, -60, 486, 92, 640, ("BROWN_DARK", "BROWN", "CHARCOAL"))
    # the seat's upper edge catches light just under the belt
    for x in range(8, 84):
        y = int(round(488 + (x + 40) * 2.0 / 118.0)) + 1
        if L.get(x, y)[3] and hsh(x // 3, 7) < 0.3 + x / 150.0:
            L.px(x, y, "OCHRE" if x > 40 else "LEATHER")
    # the left leg's inner edge faces the lit gap: RIM with OCHRE inside
    _rim_right(L, 546, 640, ("RIM", "OCHRE"), xmin=30, xmax=52)
    # the right leg's outer contour takes the sun all the way down
    _rim_right(L, 518, 640, ("RIM", "OCHRE"), xmin=70)
    return L


# the gloved right fist hanging beside the thigh, seen from behind, in near-black warm leather:
# a flared gauntlet whose stitched hem shows under the last button, the back of the hand
# BROWN_BLACK with a BROWN_DARK sheen turning to the sun and BROWN on the knuckles, the thumb
# pressed in on the left, then four curled fingers under an INK knuckle crease. The right-hand
# edge catches the sun (RIM, OCHRE inside).
# K INK, b BROWN_BLACK, d BROWN_DARK, B BROWN, L LEATHER, O OCHRE, R RIM
_FIST_X, _FIST_Y = 78, 500
_FIST = [
    "..KbbbbbbbbbbddddBOK",   # 500  gauntlet, hidden under OUTLAWS
    "..KbbbbbbbbbbddddBOK",
    "..KbbbbbbbbbbddddBOK",
    "..KbbbbbbbbbbddddBOK",
    "..KbbbbbbbbbbddddBOK",
    "..KbbbbbbbbbbddddBOK",
    "..KbbbbbbbbbbdddBORK",
    "..KbbbbbbbbbbdddBORK",
    "..KbbbbbbbbbbdddBORK",
    "..KbbbbbbbbbbdddBORK",
    "..KbbbbbbbbbbdddBORK",
    "..KbbbbbbbbbbdddBORK",   # 511  last row under the button
    "..KbbbbbbbbbddddBORK",   # 512  the flare shows below it
    "..KbbbbbbbbddddBBORK",
    "...KbbbbbbbddddBBORK",
    "...KbbbbbbddddBBBOK.",
    "....KbbbbbbddddBBORK",
    "....KBBBBBBBBBBBLLOK",   # 517  stitched leather hem, lit toward the sun
    "....KKKKKKKKKKKKKKK.",
    ".....KbbbbbbddddBRK.",   # 519  the wrist
    "....KbbbbbbdddddBORK",
    "...KbbbbbbdddddBBORK",
    "..KbbKbbbbddddBBBORK",   # 522  the thumb, pressed in on the left
    ".KbbdKbbbdddddBBBORK",
    ".KbbdKbbbddddBBBBORK",
    ".KbbdKbbbddddBBBBORK",
    ".KbbbdKbbdddddBBBORK",
    ".KbbbdKbbddddBBBBORK",
    "..KbbbKbbdddBBBBBORK",
    "..KbbbKbbdddBBBBORK.",
    "...KbbKKKKKKKKKKKRK.",   # 530  knuckle crease
    "...KbbKbBBKdBBKBBOK.",   # 531  four curled fingers, lit on the knuckles
    "....KbKbdBKbdBKdBBOK",
    "....KKKbbdKbddKdBBOK",
    ".....KKbbdKbbdKdBBOK",
    "......KbbdKbbdKddBOK",
    "......KbbdKbbdKddBK.",
    "......KbbKKbbKKdBK..",
    ".......KKK.KKK.KK...",   # 538  finger tips
]
_FIST_KEY = {"K": "INK", "b": "BROWN_BLACK", "d": "BROWN_DARK", "B": "BROWN", "L": "LEATHER",
             "O": "OCHRE", "R": "RIM"}


def _arm(rng):
    """Right arm hanging past the poncho, mostly behind the title buttons: a dark sleeve out to
    the elbow and back in to the hip, then the gloved fist, which hangs clear under the last
    button beside the holster."""
    L = Layer()
    L.poly([(82, 392), (97, 396), (102, 424), (103, 452), (98, 482), (96, 504), (80, 506),
            (84, 480), (86, 450), (80, 412)], "BROWN_DARK")
    L.line([(91, 404), (95, 452), (90, 500)], "BROWN_BLACK")
    L.line([(86, 446), (84, 498)], "BROWN_BLACK")
    L.line([(88, 470), (100, 468)], "BROWN_BLACK")      # the rolled sleeve at the elbow
    _rim_right(L, 396, 506, ("RIM", "OCHRE"))
    F = Layer()
    _sprite(F, _FIST_X, _FIST_Y, _FIST, _FIST_KEY)
    _merge(L, F)
    return L


def _torso():
    """Dark shirt between the hem and the belt: the ground the fringe hangs over, with a few
    soft BROWN_DARK folds toward the lit side."""
    L = Layer()
    L.poly([(-60, 410), (98, 396), (96, 440), (90, 490), (-60, 490)], "BROWN_BLACK")
    folds = [((30, 470), (60, 440), 0.7), ((56, 470), (80, 430), 0.9), ((74, 474), (92, 440), 0.8),
             ((6, 480), (24, 458), 0.5)]

    def shade(x, y, c):
        if c != "BROWN_BLACK":
            return None
        for (a, b, k) in folds:
            d = _seg_dist(np.array(float(x)), np.array(float(y)), a, b)
            lv = k * max(0.0, 1.0 - float(d) / 3.5)
            if lv > 0.55:
                return "BROWN_DARK"
            if lv > 0.15 and _dz(x, y, lv):
                return "BROWN_DARK"
        return None
    L.recolour(-60, 396, 98, 490, shade)
    return L


def _belt():
    L = Layer()

    def by(x):
        return 474 + (x + 40) * 2.0 / 118.0
    for x in range(-60, 84):
        y = int(round(by(x)))
        L.vline(x, y, y + 13, "BROWN_DARK")
        L.px(x, y, "LEATHER" if x > 20 else "BROWN")
        L.px(x, y + 1, "BROWN")
        L.px(x, y + 11, "BROWN_BLACK")
        L.px(x, y + 12, "BROWN_BLACK")
        L.px(x, y + 13, "INK")
    # cartridge loops: copper-cased rounds, 3 px wide, in dark leather loops; their tops
    # glint more toward the sun
    for x in range(-58, 62, 5):
        y = int(round(by(x)))
        lit = x > 28
        L.vline(x - 1, y + 2, y + 10, "BROWN_BLACK")
        L.vline(x, y + 3, y + 8, "RUST")
        L.vline(x + 1, y + 3, y + 8, "OCHRE" if lit else "LEATHER")
        L.vline(x + 2, y + 3, y + 8, "LEATHER" if lit else "BROWN")
        L.hline(x, x + 2, y + 2, "OCHRE" if lit else "LEATHER")
        if lit:
            L.px(x + 1, y + 2, "AMBER")
        L.hline(x, x + 2, y + 9, "BROWN_DARK")
        L.hline(x, x + 2, y + 10, "BROWN_BLACK")
    return L


# the revolver, seated muzzle-down: a short dark bird's-head grip curling up and back over the
# belt, the hammer spur, the silver frame, a fluted cylinder lit down its sun side, then the
# long barrel and ejector rod running straight down the holster.
# K INK, C CHARCOAL, G GREY_DARK, g GREY, S SILVER, R RIM
_GUN_X, _GUN_Y = 53, 462
_GUN_TOP = [
    "...KKKK..........",   # 462  the rounded butt of the bird's-head grip
    "..KCGggK.........",
    ".KCCCGggK........",
    "KCCCCCGgK........",
    "KCCCCCCGgK.......",
    ".KCCCCCCGgK......",
    "..KKCCCCCGgK.....",   # 468  the beak tucks in under the butt
    "....KCCCCCGgK....",
    ".....KCCCCCGK....",
    ".....KCCCCCGKKK..",   # 471  hammer spur
    "......KCCCCGKgGK.",
    "......KCCCCKGGK..",
    ".....KKKKKKKKGK..",   # 474  frame
    "....KGgSSSSggGK..",
    "...KKGggSSgggGCK.",
    "...K.KCGSgGCGSRK.",   # 477  trigger guard loop, fluted cylinder
    "...KKKCGSgGCGSRK.",
    "....KCCGSgGCGSRK.",
    "....KCCGSgGCGSRK.",
    "....KCCGSgGCGSRK.",
    "....KCCGSgGCGSRK.",
    "....KCCGSgGCGSRK.",
    "....KCCGSgGCGSRK.",
    "....KCCGSgGCGSRK.",
    ".....KKGSgGCGRK..",   # 486  front of the frame
]
_GUN_KEY = {"K": "INK", "C": "CHARCOAL", "G": "GREY_DARK", "g": "GREY", "S": "SILVER", "R": "RIM"}
_BARREL = "KCGSgRK"            # shadow, ejector rod, bright land, barrel, sun edge
_BARREL_X = _GUN_X + 7         # one straight column of stripes, x 60..66
_BARREL_ROWS = (487, 517)      # the muzzle and front sight at the bottom


def _holster_and_gun():
    L = Layer()
    # the holster on the right hip, behind the gun: tan LEATHER turning to OCHRE toward the
    # sun, a BROWN shaded left side with a stitch line, a lit mouth, a RIM edge and its own
    # INK outline, so it separates from the dark trousers. Its right edge, outline included,
    # stays at x 74 or less, well clear of the OUTLAWS frame at x 78.
    H_ = Layer()
    H_.poly([(56, 486), (72, 484), (73, 496), (73, 512), (72, 521), (69, 527), (64, 529),
             (60, 525), (58, 513), (57, 498)], "LEATHER")
    a = _alpha(H_)
    rx = {}
    for y in range(484, 530):
        xs = np.nonzero(a[y + OY, :])[0]
        if len(xs):
            rx[y] = int(xs[-1]) - OX

    def hol(x, y, c):
        if c != "LEATHER":
            return None
        lx = 57 + max(0, y - 498) * 0.1               # the shaded left edge
        if x < lx + 2:
            return "BROWN"
        if x < lx + 3.5:
            return "BROWN_MID"
        if x >= rx.get(y, 99) - 2:
            return "OCHRE"
        return None
    H_.recolour(55, 484, 75, 530, hol)
    H_.line([(58, 490), (59, 508), (62, 523)], "BROWN_DARK")     # stitching down the seam
    H_.line([(56, 486), (72, 484)], "OCHRE")                      # the lit mouth
    H_.line([(57, 487), (72, 485)], "BROWN")
    _rim_right(H_, 486, 528, ("RIM", None), xmin=55, xmax=76)
    H_.outline("INK")
    _merge(L, H_)
    # the gun on top: grip, frame and cylinder, then the straight barrel down the holster
    G = Layer()
    _sprite(G, _GUN_X, _GUN_Y, _GUN_TOP, _GUN_KEY)
    y0, y1 = _BARREL_ROWS
    for y in range(y0, y1 + 1):
        for i, ch in enumerate(_BARREL):
            G.px(_BARREL_X + i, y, _GUN_KEY[ch])
    G.hline(_BARREL_X, _BARREL_X + len(_BARREL) - 1, y1 + 1, "INK")        # the muzzle
    G.px(_BARREL_X + 1, y1 + 1, "GREY_DARK")
    G.px(_BARREL_X + 2, y1 + 1, "GREY_DARK")
    _merge(L, G)
    return L


# main band motifs, 11 rows tall, sheared along the hem: a stepped diamond with an eye and a
# stepped arrow pointing up the band toward the sun. '#' OCHRE (AMBER on the sunward half),
# 'o' the eye
_DIAMOND = [
    ".....#.....",
    "....###....",
    "...#####...",
    "..###.###..",
    ".###...###.",
    "###..o..###",
    ".###...###.",
    "..###.###..",
    "...#####...",
    "....###....",
    ".....#.....",
]
_ARROW = [
    "##.....",
    "###....",
    ".###...",
    "..###..",
    "...###.",
    "....###",
    "...###.",
    "..###..",
    ".###...",
    "###....",
    "##.....",
]
_MOTIFS = [(_DIAMOND, 2), (_ARROW, 3)]          # (map, gap after it)


def _motif_at(u):
    """(map, column, width) of the band motif under band column u, or None in a gap."""
    period = sum(len(m[0]) + g for m, g in _MOTIFS)
    u %= period
    for m, g in _MOTIFS:
        w = len(m[0])
        if u < w:
            return m, u, w
        u -= w + g
        if u < 0:
            return None
    return None


def _poncho(rng):
    L = Layer()
    pts = list(PONCHO_TOP)
    for x in range(98, -61, -2):
        pts.append((x, hem_y(x)))
    L.poly(pts, "TEAL_DARK")
    a = _alpha(L)

    def inside(x, y):
        X, Y = x + OX, y + OY
        return 0 <= X < W and 0 <= Y < H and a[Y, X]

    # ---- value field s: about -1.3 in the deepest fold valleys .. +1.3 on sunlit ridges
    X0, Y0, X1, Y1 = -60, 330, 100, 470
    xs = np.arange(X0, X1 + 1)
    ys = np.arange(Y0, Y1 + 1)
    PX, PY = np.meshgrid(xs, ys)
    PXf, PYf = PX.astype(float), PY.astype(float)
    topv = np.array([top_y(x) for x in xs])[None, :]
    chev = np.array([chevron_y(x) for x in xs])[None, :]

    def band(d, c, hw):
        return np.clip(1 - np.abs(d - c) / hw, 0, 1)

    def fade(lo, hi):
        """1 left of lo, 0 right of hi."""
        return np.clip((hi - PXf) / float(hi - lo), 0, 1)
    # lighter toward the sun, and the drape over the shoulders faces up into the sky light
    s = -0.88 + 0.6 * np.clip((PXf + 10) / 100.0, 0, 1)
    s += 0.2 * np.clip((380 - PYf) / 25.0, -0.3, 1)
    # rolled collar: shaded right under the hair, a lit roll below it, a dark valley under that
    d_top = PYf - topv
    s -= 0.5 * band(d_top, 0.0, 3.0) * fade(62, 74)
    s += 1.1 * band(d_top, 6.0, 4.5)
    s -= 0.9 * band(d_top, 13.0, 4.0) * fade(58, 72)
    # the drape over the left shoulder: arcs stacked parallel to the shoulder row, which
    # rides on a ridge; a deep valley under it, a lower ridge and a second valley
    d_ch = PYf - chev
    wob = 0.75 + 0.25 * np.sin(PXf * 0.11 + 1.3)          # folds deepen and ease along x
    wob2 = 0.7 + 0.3 * np.sin(PXf * 0.08 + 4.0)
    s += 0.95 * band(d_ch, -2.0, 7.0)
    s -= 0.9 * band(d_ch, 10.0 + 1.5 * np.sin(PXf * 0.07), 5.0) * fade(50, 66) * wob
    s += 0.65 * band(d_ch, 18.0, 5.0) * fade(36, 52)
    s -= 0.7 * band(d_ch, 26.0 + 2.0 * np.sin(PXf * 0.09 + 2.0), 5.5) * fade(26, 42) * wob2
    s += 0.45 * band(d_ch, 35.0, 5.0) * fade(16, 32)
    # right shoulder, broad and sunlit
    s += 0.7 * np.clip(1 - np.hypot(PXf - 84, PYf - 360) / 24.0, 0, 1)
    # folds hanging from the right shoulder: arcs that start steep and swing left as they
    # fall, each a broad valley with a lit ridge on its sunward side
    deep = _bez((81, 360), (78, 392), (50, 416), 12)
    folds = [
        (_bez((64, 354), (60, 382), (32, 404), 12), 0.8),
        (deep, 1.0),
        (_bez((94, 374), (92, 398), (70, 416), 12), 0.8),
        (_bez((40, 394), (30, 410), (6, 432), 10), 0.7),         # the lower back, left
        (_bez((20, 398), (8, 410), (-14, 424), 10), 0.6),
    ]
    for pl, k in folds:
        d = _poly_dist(PXf, PYf, pl)
        s -= 1.0 * k * np.clip(1 - d / 4.5, 0, 1)
        d2 = _poly_dist(PXf - 5.5, PYf, pl)
        s += 0.8 * k * np.clip(1 - d2 / 5.0, 0, 1)
    # away from the sun the far left sinks into shadow
    s -= 0.3 * np.clip((0 - PXf) / 40.0, 0, 1)
    # the one solid INK core, down the deepest fold; every other valley is solid NAVY
    core = _poly_dist(PXf, PYf, deep[2:-2]) < 0.8

    def valley(x, y):
        """How far (x, y) lies inside a fold valley (> 0 inside), read per pixel so valley
        edges are clean stepped curves rather than a comb of stitches; the edge wanders in
        2..4 px ticks along x."""
        y = min(Y1, max(Y0, y))
        return -0.72 - (s[y - Y0, x - X0] + 0.3 * (_vnoise(x + OX, 0, 3, 77) - 0.5))

    def knit(x, y, c):
        """Value field to knit: solid NAVY in the valleys (INK only down the deepest fold),
        TEAL_DARK body, TEAL on the ridges, the body and ridge steps dithered through 1x2
        vertical stitches (staggered column to column)."""
        if c != "TEAL_DARK":
            return None
        if core[y - Y0, x - X0]:
            return "INK"
        X, Y = x + OX, y + OY
        # ordered 1x2 stitches: a 4x4 Bayer threshold over stitch cells staggered by column,
        # anchored to the canvas like dith(); both pixels of a stitch (yt, yt + 1) read the
        # value at its top pixel, so a stitch never splits into two colours
        cell = (Y + (X % 2)) // 2
        t = (BAYER4[cell % 4, X % 4] + 0.5) / 16.0
        yt = min(Y1, max(Y0, 2 * cell - (X % 2) - OY))
        dv = valley(x, y)
        whole = min(valley(x, yt), valley(x, yt + 1))       # the whole stitch in the valley
        if dv > 0:
            # a few TEAL_DARK stitches stay near the valley edge, so the knit runs on through
            return None if whole > 0 and t < 0.13 - 0.3 * whole else "NAVY"
        if max(valley(x, yt), valley(x, yt + 1)) > 0:
            return None                                     # half a stitch: leave it plain
        v = max(-0.45, s[yt - Y0, x - X0])
        if v < 0.05:
            # the dark body: a sparse sprinkle of lit stitches keeps the knit alive
            return "TEAL" if t < 0.05 + 0.1 * (v + 0.45) / 0.5 else None
        if v < 0.7:
            return "TEAL" if t < 0.08 + 0.4 * (v - 0.05) / 0.65 else None
        # ridges: TEAL stitches, TEAL_LIGHT only on the sunlit right shoulder and edge
        if t < 0.55:
            if x > 72 and v > 1.05 and _dz(x, yt, 0.4):
                return "TEAL_LIGHT"
            return "TEAL"
        return None
    L.recolour(X0, Y0, X1, Y1, knit)

    # a faint broken RUST line along the collar roll on the shaded left
    for x in range(-40, 36):
        y = round(top_y(x) + 9)
        if (x // 3) % 3 == 0 and inside(x, y):
            L.px(x, y, "RUST")

    # shoulder row: woven glyphs along the arch (an arrowhead, a cross, a stepped dash), OCHRE
    # warming to ORANGE toward the sun, AMBER hearts, RUST feet, RUST and OCHRE in the shade
    glyphs = [
        ["O...O", ".O.O.", "..A.."],                    # v
        ["O.O", ".A.", "R.O"],                          # x
        ["..O..", "OAAO.", "..R.."],                    # stepped dash with a tick
        ["O....", ".OO..", "..AO.", ".OO..", "O...."],  # arrowhead pointing to the sun
    ]
    n = 0
    x = -40
    while x < 74:
        g = glyphs[n % 4]
        y = round(chevron_y(x)) - len(g) // 2
        shade = x < 4
        for j, row in enumerate(g):
            for i, ch in enumerate(row):
                if ch == ".":
                    continue
                col_ = {"O": "RUST" if shade else ("ORANGE" if x > 30 else "OCHRE"),
                        "A": "OCHRE" if shade else "AMBER", "R": "RUST"}[ch]
                xx, yy = x + i - len(row) // 2, y + j
                if inside(xx, yy):
                    L.px(xx, yy, col_)
        x += 8 if n % 2 else 7
        n += 1

    # main band parallel to the hem: 2 px OCHRE borders with RUST inside them, a chain of
    # stepped diamonds and arrows between, a dark strip, then the knot row the fringe hangs from
    for x in range(-60, 100):
        hi = int(round(hem_y(x)))
        if not inside(x, hi - 2):
            continue
        sun = x > 56
        for yy in range(hi - 18, hi - 2):
            if inside(x, yy):
                L.px(x, yy, "TEAL_DARK")
        for yy, c in ((hi - 21, "OCHRE"), (hi - 20, "OCHRE"), (hi - 19, "RUST"), (hi - 7, "RUST"),
                      (hi - 6, "OCHRE"), (hi - 5, "OCHRE"), (hi - 3, "INK" if x % 2 else "TEAL_DARK")):
            if inside(x, yy):
                if c == "OCHRE" and sun and (x + yy) % 2 == 0:
                    c = "AMBER"
                elif c == "OCHRE" and x < -6 and yy in (hi - 20, hi - 5):
                    c = "RUST"
                L.px(x, yy, c)
        u = x - HEM_TIP[0] if x >= HEM_TIP[0] else HEM_TIP[0] - x
        mo = _motif_at(u + 3)
        if mo:
            m, i, w = mo
            for k in range(11):
                ch = m[k][i]
                yy = hi - 18 + k
                if ch == "." or not inside(x, yy):
                    continue
                if ch == "o":
                    c = "TAN" if x > 0 else "OCHRE"
                elif x < -6:
                    c = "RUST" if i < w // 2 else "OCHRE"
                elif x < 16:
                    c = "OCHRE"
                else:
                    c = "AMBER" if i > (w - 1) // 2 else "OCHRE"
                L.px(x, yy, c)
        # knot row along the hem, the fringe's bound top
        for yy, c in ((hi - 2, "OCHRE" if x % 3 else "LEATHER"),
                      (hi - 1, ("TAN" if x > 0 else "OCHRE") if x % 3 == 1 else "OCHRE")):
            if inside(x, yy):
                L.px(x, yy, c)
    # rim along the shoulder top and the right contour, with TEAL_LIGHT inside it
    _rim_top(L, 60, 98, ("RIM", "TEAL_LIGHT"), ymax=372)
    _rim_top(L, 42, 59, ("OCHRE", None), ymax=372)
    _rim_right(L, 338, 392, ("RIM", "TEAL_LIGHT"), xmin=60)
    return L


def _fringe(rng):
    """Tassels hanging from the hem in clumps (two or three touching strands, 2..4 px) with
    dark gaps between the clumps that open a few pixels below the knot row: OCHRE bodies, a
    TAN lit column on the upper part of every other clump and a rare SAND glint, darkening to
    LEATHER and BROWN at the tips. Clump ends vary; the fringe is longest at the back point
    and RUST only on the shaded far left."""
    L = Layer()
    x = -60
    ci = 0
    while x < 97:
        w = (2, 3, 3, 4)[int(hsh(ci, 5) * 4)]
        gap = 1 if hsh(ci, 6) < 0.4 else 2
        # longest at the back point, short across the hip so the cartridge belt shows
        base = _lerp_pts([(0, 44), (45, 24), (95, 22)], min(95, max(0, x)))
        if x < HEM_TIP[0]:
            base -= (HEM_TIP[0] - x) * 0.3
        base += (hsh(ci, 7) - 0.5) * 8
        sway = 1 if hsh(ci, 8) > 0.72 else 0
        shade = x < 0
        # the gap after this clump stays bound (ochre) for a few rows under the knot row
        bound = 2 + int(hsh(ci, 10) * 5)
        for g in range(gap):
            xx = x + w + g
            h = int(round(hem_y(xx)))
            for i in range(bound):
                L.px(xx, h + i, ("RUST" if shade else "OCHRE") if i < bound - 1 else
                     ("BROWN" if shade else "LEATHER"))
        for j in range(w):
            xx = x + j
            h = int(round(hem_y(xx)))
            edge = j == 0 or j == w - 1
            ln = int(round(base - (2 if edge and w > 2 else 0) + (hsh(ci, j, 9) - 0.5) * 3))
            lit = j == w - 2 if w > 2 else j == w - 1
            for i in range(ln):
                if shade:
                    c = "OCHRE" if lit and i < ln * 0.6 else "RUST"
                else:
                    c = "OCHRE"
                    if lit and ci % 3 == 0 and i < ln * 0.4:
                        c = "SAND" if ci % 6 == 0 and 2 <= i < 2 + ln // 6 else "TAN"
                    elif j == 0 and i > ln * 0.35:
                        c = "LEATHER"
                    elif i > ln * 0.7:
                        c = "LEATHER" if (i + j) % 3 else "OCHRE"
                if i >= ln - 4:
                    c = "BROWN" if shade else "LEATHER"
                if i >= ln - 2:
                    c = "BROWN_MID" if lit and not shade else "BROWN"
                # a 4 px clump parts into two strands low down
                if w == 4 and j == 1 and i > ln * 0.55:
                    continue
                L.px(xx + (sway if i > ln * 0.6 else 0), h + i, c)
        x += w + gap
        ci += 1
    return L


def _hair(rng):
    """Long curly hair under the brim: a near-black mass with ragged edges and locks hanging
    onto the collar. The shaded left two thirds carry only a few low BROWN_DARK curls (runs of
    2 or 3 px); the sunward strands on the right light up OCHRE and RIM beside the ear."""
    L = Layer()
    for y in range(310, 339):
        # ragged curls on both sides, the mass spreading a little as it falls onto the collar
        xl = 25 + int(round(2.0 * math.sin(y * 0.55) + (hsh(y // 3, 51) - 0.5) * 3
                            - max(0, y - 326) * 0.25))
        xr = 65 + int(round(0.9 * math.sin(y * 0.7 + 2.0))) - (1 if 316 <= y <= 324 else 0)
        L.hline(xl, xr, y, "BROWN_BLACK")
    locks = ((22, 29, 343), (31, 38, 345), (41, 47, 341), (49, 56, 346), (58, 65, 342))
    tips = []
    for (x0, x1, y1) in locks:
        for y in range(337, y1 + 1):
            t = (y - 337) / float(y1 - 337 + 1)
            a = x0 + int(round(t * 2))
            b = x1 - int(round(t * 4))
            if a <= b:
                L.hline(a, b, y, "BROWN_BLACK")
                if y >= y1 - 2 - int(hsh(x0, 52) * 2):
                    tips.append((a, b, y))
    # the shadow right under the brim and down the shaded left edge: solid INK up to a column
    # that wanders with the curls, and solid INK points on the lock tips
    def edge(y):
        return 27 + int(round(1.5 * math.sin(y * 0.4 + 1.0) + (hsh(y // 4, 53) - 0.5) * 2))
    L.recolour(18, 310, 70, 346, lambda x, y, c: "INK" if c == "BROWN_BLACK" and (
        y < 314 or x <= edge(y)) else None)
    for (a, b, y) in tips:
        L.hline(a, b, y, "INK")
    # low curls in the shade: short C-shaped BROWN_DARK runs, stacked so every mark is 2+ px
    for n, (cx, cy) in enumerate(((31, 318), (37, 326), (43, 317), (48, 331), (52, 321),
                                  (40, 338), (29, 330), (51, 339))):
        h = 3 if hsh(n, 54) < 0.5 else 2
        L.vline(cx, cy, cy + h - 1, "BROWN_DARK")
        L.px(cx + 1, cy + h, "BROWN_DARK")
        L.px(cx + 1, cy + h + 1, "BROWN_DARK")
    # sunward strands down the right of the mass: wavy runs that catch OCHRE, RIM at the bends
    for k, x0 in enumerate((56, 59, 62)):
        for y in range(314 + k, 341 - k):
            x = x0 + int(round(1.2 * math.sin((y - 312) * 0.55 + k * 1.7)))
            if not L.get(x, y)[3] or L.is_(x, y, "INK"):
                continue
            ph = ((y - 312) // 3 + k) % 3
            if ph == 2:
                continue
            c = "OCHRE" if x0 >= 59 else "BROWN"
            if ph == 0 and x0 == 62:
                c = "RIM"
            L.px(x, y, c)
    for y in range(315, 342):
        x = 64 - (1 if y > 331 else 0) - (1 if y > 336 else 0)
        if L.get(x, y)[3] and (y // 3) % 3 != 2:
            L.px(x, y, "OCHRE")
    # the ear and cheek of a head turned slightly right, just past the right-hand locks
    for (x, y) in [(64, 318), (65, 318), (64, 319), (65, 319), (66, 319), (65, 320), (66, 320),
                   (65, 321), (66, 321), (65, 322), (66, 322), (65, 323)]:
        L.px(x, y, "SKIN_DEEP")
    L.px(66, 320, "SKIN_DARK")
    L.px(66, 321, "SKIN_DARK")
    _despeckle(L, 18, 310, 70, 346, ("BROWN_DARK", "BROWN", "OCHRE", "RIM"))
    return L


def _hat(rng):
    L = Layer()
    # brim: the near edge droops to its lowest point left of centre, its far upper surface
    # shows as a sliver on the left, and the right tip curls up into the sun short of PLAY,
    # clear of the lantern above it and of the wagon to the right
    upper = [(2, 306), (4, 302), (8, 299), (14, 297), (22, 296), (30, 296), (66, 298), (72, 298),
             (77, 297), (80, 296), (82, 294), (84, 293), (84, 295)]
    lower = [(84, 296), (82, 298), (78, 301), (73, 304), (66, 307), (56, 310), (46, 312),
             (38, 314), (30, 314), (22, 313), (14, 312), (8, 310), (4, 308), (2, 306)]
    L.poly(upper + lower, "BROWN_BLACK")

    def near_y(x):
        return _lerp_pts(lower[::-1], x)

    # the underside and thickness of the near edge, with a dull lit lip along its front
    L.recolour(0, 290, 90, 320, lambda x, y, c: "INK" if y >= near_y(x) - 1 else None)
    for x in range(6, 64):
        y = int(math.ceil(near_y(x) - 1)) - 1
        if L.is_(x, y, "BROWN_BLACK"):
            L.px(x, y, "BROWN" if x > 44 else "BROWN_DARK")
    # a soft BROWN_DARK sheen where the sunward brim turns up to the light
    L.recolour(58, 292, 86, 312, lambda x, y, c: "BROWN_DARK" if c == "BROWN_BLACK" and
               y < near_y(x) - 2 and _vnoise(x, y, 4, 23) + (x - 58) / 60.0 > 0.95 else None)
    # the lit lip: a dull far edge on the left in runs of LEATHER and BROWN with a solid
    # SHADOW sliver of sky under it, OCHRE on top toward the crown, the sunward edge bright
    for x in range(2, 88):
        ys = [y for y in range(288, 320) if L.get(x, y)[3]]
        if not ys:
            continue
        y = ys[0]
        if x > 72:
            L.px(x, y, "RIM")
            L.px(x, y + 1, "OCHRE")
        elif x > 60:
            L.px(x, y, "OCHRE")
        elif x < 28:
            seg = x // 4
            if hsh(seg, 24) < 0.12 and x % 4 < 2:
                L.px(x, y, "SHADOW")
            else:
                L.px(x, y, "LEATHER" if hsh(seg, 25) < 0.55 else "BROWN")
            if 8 < x < 26 and L.is_(x, y + 1, "BROWN_BLACK") and y + 1 < near_y(x) - 2:
                L.px(x, y + 1, "SHADOW")
    L.vline(84, 293, 296, "RIM")                 # the curled tip, end on to the sun
    L.px(83, 296, "OCHRE")
    L.px(82, 297, "OCHRE")

    # crown: tapering sides, a broad rounded shoulder on the left, a flat top with a pinch;
    # solid warm-black felt with one BROWN_DARK sheen on the sunward top
    crown = Layer()
    crown.poly([(27, 305), (28, 296), (30, 290), (32, 286), (35, 282), (39, 280), (45, 279),
                (55, 279), (61, 278), (64, 279), (66, 281), (67, 285), (67, 292), (67, 305)],
               "BROWN_BLACK")
    crown.recolour(44, 278, 67, 297, lambda x, y, c: "BROWN_DARK" if c == "BROWN_BLACK" and
                   ((x - 57) / 9.0) ** 2 + ((y - 287) / 6.0) ** 2 + (_vnoise(x, y, 3, 21) - 0.5) * 0.8 < 1.0
                   else None)
    # the pinch: a soft crease across the top, and the side dimples
    crown.line([(37, 284), (45, 285), (54, 285), (62, 283)], "SHADOW")
    crown.line([(39, 285), (46, 286), (54, 286), (60, 285)], "INK")
    crown.line([(32, 289), (31, 296)], "INK")
    crown.line([(62, 288), (63, 296)], "SHADOW")
    # band: leather segments (LEATHER and RUST alternating) with BROWN_BLACK seams, a dull
    # BROWN_MID top edge that warms toward the sun, BROWN and BROWN_DARK underneath
    seg = 0
    for x in range(27, 68):
        p = (x - 27) % 7
        if p == 6:
            crown.vline(x, 298, 303, "BROWN_BLACK")
            seg += 1
            continue
        body = "RUST" if seg % 2 else "LEATHER"
        top = "BROWN_MID" if x < 41 else ("OCHRE" if x < 53 else ("ORANGE" if x < 60 else "AMBER"))
        if p == 0:
            body = "BROWN"                      # the shaded left end of each segment
        crown.px(x, 298, top)
        crown.px(x, 299, body if x < 53 or p == 0 else "OCHRE")
        crown.px(x, 300, body)
        crown.px(x, 301, body)
        crown.px(x, 302, "BROWN")
        crown.px(x, 303, "BROWN_DARK")
        crown.px(x, 304, "BROWN_BLACK")
    _rim_right(crown, 279, 305, ("RIM", "OCHRE"), xmin=52)
    _rim_top(crown, 46, 66, ("RIM", "OCHRE"), ymax=292)
    _rim_top(crown, 31, 45, ("OCHRE", None), ymax=292)
    crown.line([(31, 290), (30, 293)], "BROWN")         # a dull glint down the shaded side
    for x in range(55, 64):
        ys = [y for y in range(276, 290) if crown.get(x, y)[3]]
        if ys:
            crown.px(x, ys[0], "RIM_HOT")
    _merge(L, crown)
    _despeckle(L, 0, 276, 90, 316, ("BROWN_DARK", "SHADOW"))
    return L


# ---------------------------------------------------------------- the whole figure
def draw_player(rng):
    """The player from behind, title framing: hat top at y 278 (crown x 27..67, brim x 2..84),
    poncho over the shoulders, fringe hanging to about y 505, gun and holster on the right hip
    at x 53..74, the fist below OUTLAWS, legs to the bottom. rng is unused: every mark comes
    from hsh(), so the figure is the same on every build."""
    L = Layer()
    for part in (_legs(rng), _arm(rng), _torso(), _belt(), _holster_and_gun(), _poncho(rng),
                 _fringe(rng), _hair(rng), _hat(rng)):
        _merge(L, part)
    L.outline("INK")
    return L
