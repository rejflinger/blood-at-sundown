"""The player seen from behind in the lower left (title framing).

Backlit: the sun is to the right of the figure, so every face turned to the camera is dark
(INK, BROWN_BLACK, CHARCOAL, TEAL_DARK) and the shape reads through 1 px RIM lines on its
right-hand and top edges, the rust pattern band of the poncho and the tan fringe. The owner
lets the title buttons (x 78..193, y 322..519) overlap the figure: the hat brim ends just
above PLAY, while the right shoulder, the muzzle end of the holster and the gloved arm run
under the button column.
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


def _sprite(L, x0, y0, rows, key):
    """Stamps a small hand-laid pixel map: one character per pixel, '.' is left alone."""
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch != "." and ch in key:
                L.px(x0 + i, y0 + j, key[ch])


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
    is mottled BROWN_DARK on BROWN_BLACK, denser where a form turns up toward the light."""
    L = Layer()
    L.poly([(-60, 486), (84, 486), (85, 520), (87, 560), (89, 640), (-60, 640)], "BROWN_BLACK")
    gap = [(53, 543), (56, 560), (61, 584), (66, 640), (44, 640), (47, 584), (50, 560)]
    _clear_poly(L, gap)

    # rounded forms, each lit on its upper right: the seat, the left thigh, the right leg
    forms = [(28, 508, 46, 26, 1.0), (14, 566, 34, 26, 0.7), (70, 540, 15, 44, 0.75),
             (-30, 540, 22, 40, 0.4), (72, 604, 12, 34, 0.5), (16, 616, 28, 26, 0.45)]

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
        n = hsh(x // 2, (y + (x // 2) % 2) // 2, 41)
        val = lit + (n - 0.5) * 0.4
        if val > 0.95 and hsh(x, y, 44) < 0.35:
            return "BROWN"
        if val > 0.56:
            return "BROWN_DARK"
        return None
    L.recolour(-60, 486, 92, 640, form_shade)

    # creases: INK valleys with a CHARCOAL lip on their upper side, curving round the forms
    creases = [
        ([(-24, 528), (-6, 536), (14, 540), (34, 540), (50, 536)], 1),   # under the seat
        ([(56, 528), (62, 536), (72, 540), (82, 536)], 1),
        ([(-8, 588), (6, 592), (20, 592), (34, 588)], 0),               # behind the knee
        ([(8, 494), (12, 506), (13, 518)], 1),
        ([(60, 500), (63, 512), (64, 524)], 1),
        ([(66, 566), (68, 590), (72, 620)], 1),
        ([(-30, 514), (-26, 540), (-22, 566)], 0),
        ([(30, 604), (34, 624), (36, 640)], 0),
    ]
    for pts, lit in creases:
        L.line([(round(x), round(y)) for x, y in pts], "INK")
        L.line([(round(x), round(y) - 1) for x, y in pts[1:-1]], "CHARCOAL")
        if lit:
            L.line([(round(x) + 1, round(y) - 2) for x, y in pts[1:-1]], "BROWN_DARK")
    # the seam where the legs part, running down from the seat into the gap
    L.line([(50, 510), (51, 526), (52, 543)], "INK")
    L.line([(49, 516), (50, 540)], "CHARCOAL")
    # the seat's upper edge catches light just under the belt
    for x in range(8, 84):
        y = int(round(488 + (x + 40) * 2.0 / 118.0)) + 1
        if L.get(x, y)[3] and hsh(x // 2, 7) < 0.3 + x / 150.0:
            L.px(x, y, "OCHRE" if x > 40 else "LEATHER")
    # the left leg's inner edge faces the lit gap: RIM with OCHRE inside
    _rim_right(L, 546, 640, ("RIM", "OCHRE"), xmin=30, xmax=52)
    # the right leg's outer contour
    _rim_right(L, 522, 640, ("OCHRE", None), xmin=70)
    return L


def _arm(rng):
    """Right arm hanging past the poncho, mostly behind the title buttons: a dark sleeve and
    a gloved fist whose knuckles show under the last button."""
    L = Layer()
    L.poly([(82, 392), (97, 396), (102, 444), (104, 492), (89, 496), (85, 452), (80, 412)], "BROWN_DARK")
    L.line([(91, 404), (96, 488)], "BROWN_BLACK")
    L.line([(86, 444), (89, 490)], "BROWN_BLACK")
    L.line([(88, 472), (102, 468)], "BROWN_BLACK")      # cuff
    # gauntlet cuff, then the fist: dark leather, BROWN_DARK where it turns to the light
    L.poly([(87, 490), (104, 486), (106, 498), (89, 502)], "BROWN_DARK")
    L.line([(88, 493), (105, 489)], "INK")
    L.poly([(88, 502), (105, 498), (107, 510), (106, 526), (102, 533), (92, 533), (88, 520)],
           "BROWN_BLACK")
    L.recolour(95, 498, 107, 533, lambda x, y, c: "BROWN_DARK" if c == "BROWN_BLACK" and x > 98 and y < 524 else None)
    for x0 in (91, 96, 101):                              # curled fingers, INK between them
        L.line([(x0 + 4, 524), (x0 + 4, 532)], "INK")
        L.hline(x0, x0 + 2, 525, "BROWN_DARK")
        L.px(x0 + 1, 526, "BROWN_DARK")
        L.px(x0 + 1, 524, "OCHRE")                        # knuckle glints
    L.px(104, 523, "OCHRE")
    L.line([(89, 520), (104, 522)], "INK")
    L.line([(91, 504), (91, 518)], "INK")              # thumb
    _rim_right(L, 396, 532, ("RIM", "OCHRE"))
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
            if lv > 0.15 and dith(x, y, lv):
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


# the revolver, seated grip-up: a dark gunmetal grip hooking up and back with a SILVER
# backstrap and a GOLD screw, the hammer spur, the frame and trigger guard, a fluted cylinder
# lit down its right side, then the barrel into the holster.
# K INK, C CHARCOAL, G GREY_DARK, S SILVER, R RIM, g GOLD
_GUN = [
    "..KKKK............",   # 459  butt
    ".KCSSSK...........",
    "KCCGSSSK..........",
    "KCCCCGSK..........",
    "KCCCCgGSK.........",
    ".KCCCCGSK.........",
    ".KCCCCCGSK........",
    "..KCCCCGSK........",
    "..KCCCCCGSK.......",
    "...KCCCgGSK.......",
    "...KCCCCCGSK......",
    "....KCCCCGSK......",
    "....KCCCCCGSKK....",
    ".....KCCCCGSSSK...",   # hammer spur
    ".....KCCCCKGSGK...",
    "....KKKCCKGGGSK...",   # frame
    "...KGGKKKGGSSGSK..",
    "...KGK.KCGSSGCSRK.",   # cylinder: dark flutes, two bright lands, RIM on the sun side
    "...KGK.KCGSSGCSRK.",
    "...KGKKKCGSSGCSRK.",
    "....KGGKCGSSGCSRK.",
    ".....KKKCCGSGCGRK.",
    ".......KCCGSGCGRK.",
    ".......KCGSSGCSRK.",
    ".......KCGSSGCSRK.",
    ".......KCCGGCCGRK.",
    "........KCGSSRK...",   # barrel and ejector rod
    "........KCGSSRK...",
    "........KCGSGRK...",
    "........KCGSGRK...",
    "........KCGSGRK...",
    "........KCGSGRK...",
    "........KCGSGRK...",
    "........KCGSGRK...",
]
_GUN_KEY = {"K": "INK", "C": "CHARCOAL", "G": "GREY_DARK", "S": "SILVER", "R": "RIM", "g": "GOLD"}


def _holster_and_gun():
    L = Layer()
    _sprite(L, 58, 459, _GUN, _GUN_KEY)
    # the holster on the right hip, drawn over the barrel: dark leather with a BROWN sheen
    # toward the sun, a LEATHER lip at the mouth, a RIM edge and its own INK outline
    H_ = Layer()
    H_.poly([(65, 493), (83, 490), (85, 516), (81, 530), (74, 533), (69, 518)], "BROWN_BLACK")
    H_.recolour(64, 490, 86, 534, lambda x, y, c: "BROWN_DARK" if x > 73 and not (x > 79 and y > 506 and dith(x, y, 0.5)) else None)
    H_.recolour(75, 495, 81, 526, lambda x, y, c: "BROWN" if x in (77, 78) and y % 4 != 3 else None)
    H_.line([(65, 493), (83, 490)], "LEATHER")
    H_.line([(66, 494), (83, 491)], "BROWN")
    H_.line([(70, 505), (72, 522)], "INK")
    H_.line([(71, 504), (73, 521)], "BROWN_DARK")
    _rim_right(H_, 491, 530, ("RIM", "OCHRE"), xmin=64, xmax=87)
    H_.outline("INK")
    _merge(L, H_)
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
    # the one solid INK core, down the deepest fold; every other valley is dithered
    core = _poly_dist(PXf, PYf, deep[2:-2]) < 0.8

    def knit(x, y, c):
        """Value field to knit: INK in the valleys, TEAL_DARK body, TEAL on the ridges, with
        the steps dithered through 1x2 vertical stitches (staggered column to column)."""
        if c != "TEAL_DARK":
            return None
        if core[y - Y0, x - X0]:
            return "INK"
        v = s[y - Y0, x - X0]
        # ordered 1x2 stitches: a 4x4 Bayer threshold over stitch cells staggered by column
        t = (BAYER4[((y + (x % 2)) // 2) % 4, x % 4] + 0.5) / 16.0
        if v < -0.45:
            return "INK" if t < 0.15 + 0.75 * min(1.0, (-0.45 - v) / 0.55) else None
        if v < 0.05:
            # the dark body: a sparse sprinkle of lit stitches keeps the knit alive
            return "TEAL" if t < 0.05 + 0.1 * (v + 0.45) / 0.5 else None
        if v < 0.7:
            return "TEAL" if t < 0.08 + 0.4 * (v - 0.05) / 0.65 else None
        # ridges: TEAL stitches, TEAL_LIGHT only on the sunlit right shoulder and edge
        if t < 0.55:
            if x > 72 and v > 1.05 and dith(x, y, 0.4):
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
    onto the collar, combed through by wavy strands whose right-hand bends catch a C-shaped
    BROWN_MID or RUST highlight; the sunward strands light up OCHRE and RIM."""
    L = Layer()
    for y in range(312, 339):
        xl = 28 + int(round(2.0 * math.sin(y * 0.55) + (hsh(y // 3, 51) - 0.5) * 3))
        xr = 72 - (1 if y > 330 else 0) - (1 if y > 335 else 0)
        L.hline(xl, xr, y, "BROWN_BLACK")
    locks = ((28, 35, 344), (39, 46, 341), (50, 58, 345), (62, 68, 341))
    for (x0, x1, y1) in locks:
        for y in range(337, y1 + 1):
            t = (y - 337) / float(y1 - 337 + 1)
            a = x0 + int(round(t * 2))
            b = x1 - int(round(t * 4))
            if a <= b:
                L.hline(a, b, y, "BROWN_BLACK")
    # the shadow right under the brim and down the shaded left edge
    L.recolour(20, 312, 75, 346, lambda x, y, c: "INK" if c == "BROWN_BLACK" and (
        y < 315 or (x < 30 and dith(x, y, 0.5)) or (y > 340 and dith(x, y, 0.5))) else None)
    # wavy strands at uneven spacing, in two tiers (under the brim, and the locks on the
    # collar); each is a short run whose right-hand bends catch the light
    sx = 29.0
    n = 0
    while sx < 71:
        for tier, (ya, yb) in enumerate(((315, 330), (325, 346))):
            per = 7.0 + hsh(n, tier, 71) * 3.0
            ph = hsh(n, tier, 72) * 6.28
            y0 = ya + int(hsh(n, tier, 73) * 4)
            y1 = yb - int(hsh(n, tier, 74) * 5)
            x0 = int(sx) + tier * 2 - 1
            lit_side = x0 >= 63
            for y in range(y0, y1):
                ang = 6.2832 * (y - y0) / per + ph
                sn = math.sin(ang)
                x = x0 + int(round(1.3 * sn))
                if not L.get(x, y)[3]:
                    continue
                if lit_side:
                    c = ("RIM" if sn > 0.8 and x0 >= 66 else "OCHRE") if sn > 0.35 else "BROWN"
                elif sn > 0.5:
                    c = "BROWN_MID" if x0 >= 38 else "RUST"
                    if math.cos(ang) > 0.5:
                        c = "BROWN" if x0 >= 38 else "BROWN_MID"
                elif sn > -0.4:
                    c = "BROWN_DARK"
                else:
                    continue
                L.px(x, y, c)
        sx += 4 + hsh(n, 75) * 3
        n += 1
    # sunlit strands down the right-hand edge of the mass
    for y in range(315, 342):
        x = 70 + int(round(math.sin((y - 312) * 0.7) * 1.2)) - (1 if y > 331 else 0) - (1 if y > 336 else 0)
        if (y // 3) % 3 != 2 and L.get(x, y)[3]:
            L.px(x, y, "OCHRE")
            if (y // 3) % 3 == 0 and L.get(x + 1, y)[3]:
                L.px(x + 1, y, "RIM")
    # the ear and cheek of a head turned slightly right, just past the right-hand locks
    for (x, y) in [(71, 318), (72, 318), (71, 319), (72, 319), (73, 319), (72, 320), (73, 320),
                   (72, 321), (73, 321), (72, 322), (73, 322), (72, 323)]:
        L.px(x, y, "SKIN_DEEP")
    L.px(73, 320, "SKIN_DARK")
    L.px(73, 321, "SKIN_DARK")
    return L


def _felt(x, y, seed):
    """Felt texture: warm BROWN_BLACK felt with 2 px CHARCOAL flecks (about a quarter)."""
    return hsh(x // 2, y, seed) < 0.74


def _hat(rng):
    L = Layer()
    # brim: the near edge droops to its lowest point near x 36, its far upper surface shows
    # as a sliver on the left, and the right tip curls up into the sun just short of PLAY
    upper = [(3, 311), (4, 306), (7, 302), (12, 299), (19, 297), (30, 296), (72, 299), (78, 300),
             (83, 300), (89, 299), (94, 297), (97, 296), (99, 297), (99, 300)]
    lower = [(97, 302), (94, 304), (89, 307), (80, 311), (70, 314), (58, 316), (46, 318),
             (36, 318), (26, 317), (17, 316), (10, 315), (5, 313), (3, 311)]
    L.poly(upper + lower, "CHARCOAL")

    def near_y(x):
        return _lerp_pts(lower[::-1], x)

    def brim(x, y, c):
        if c != "CHARCOAL":
            return None
        ny = near_y(x)
        if y >= ny - 1:
            return "INK"                       # underside and thickness of the near edge
        if y >= ny - 4 and 8 < x < 76:
            return "BROWN_BLACK"
        # the far upper surface, a SHADOW sliver close to the crown
        if y <= 300 and 9 < x < 30 and dith(x, y, 0.2 + (300 - y) / 10.0):
            return "SHADOW"
        return "BROWN_BLACK" if _felt(x, y, 5) or (x < 20 and dith(x, y, 0.5)) else None
    L.recolour(2, 290, 100, 320, brim)
    L.recolour(64, 294, 99, 310, lambda x, y, c: "BROWN_DARK" if c in ("CHARCOAL", "BROWN_BLACK") and
               hsh(x // 2, y, 23) < 0.12 and y < near_y(x) - 2 else None)
    # a lit lip along the upper-left edge (dull) and the sunward right edge (bright)
    for x in range(4, 100):
        for y in range(290, 320):
            if L.get(x, y)[3]:
                if x > 72:
                    L.px(x, y, "RIM")
                    L.px(x, y + 1, "OCHRE")
                elif x > 60:
                    L.px(x, y, "OCHRE")
                elif x < 28:
                    # the far edge picks up a dull, broken glint from the sky
                    L.px(x, y, "LEATHER" if x % 3 == 0 else ("BROWN" if x % 3 == 1 else "SHADOW"))
                break
    L.px(99, 299, "RIM")
    L.px(98, 301, "OCHRE")
    L.px(97, 302, "RIM")
    L.px(96, 302, "OCHRE")

    # crown: tapering sides, a broad rounded shoulder on the left, a flat top with a pinch
    crown = Layer()
    crown.poly([(30, 305), (31, 296), (33, 290), (35, 286), (38, 282), (42, 280), (48, 279),
                (58, 279), (66, 278), (70, 279), (73, 281), (75, 285), (76, 292), (76, 305)],
               "CHARCOAL")
    crown.recolour(28, 276, 78, 306, lambda x, y, c: "BROWN_BLACK" if c == "CHARCOAL" and (
        _felt(x, y, 7) or (x < 36 and dith(x, y, 0.5))) else None)
    # worn felt catching a little light on the sunward half: sparse 2 px BROWN_DARK flecks
    crown.recolour(46, 276, 76, 297, lambda x, y, c: "BROWN_DARK" if c in ("CHARCOAL", "BROWN_BLACK") and
                   hsh(x // 2, y, 21) < 0.06 + (x - 46) / 200.0 else None)
    # the pinch: a soft crease across the top, and the side dimples
    crown.line([(40, 284), (48, 285), (58, 285), (68, 283)], "SHADOW")
    crown.line([(42, 285), (50, 286), (58, 286), (66, 285)], "INK")
    crown.line([(35, 289), (34, 296)], "BROWN_BLACK")
    crown.line([(71, 288), (72, 296)], "SHADOW")
    # band: leather segments (LEATHER and RUST alternating) with BROWN_BLACK seams, a dull
    # BROWN_MID top edge that warms toward the sun, BROWN and BROWN_DARK underneath
    seg = 0
    for x in range(30, 77):
        p = (x - 30) % 7
        if p == 6:
            crown.vline(x, 298, 303, "BROWN_BLACK")
            seg += 1
            continue
        body = "RUST" if seg % 2 else "LEATHER"
        top = "BROWN_MID" if x < 46 else ("OCHRE" if x < 60 else ("ORANGE" if x < 67 else "AMBER"))
        if p == 0:
            body = "BROWN"                      # the shaded left end of each segment
        crown.px(x, 298, top)
        crown.px(x, 299, body if x < 60 or p == 0 else "OCHRE")
        crown.px(x, 300, body)
        crown.px(x, 301, body)
        crown.px(x, 302, "BROWN")
        crown.px(x, 303, "BROWN_DARK")
        crown.px(x, 304, "BROWN_BLACK")
    _rim_right(crown, 279, 305, ("RIM", "OCHRE"), xmin=56)
    _rim_top(crown, 50, 75, ("RIM", "OCHRE"), ymax=292)
    _rim_top(crown, 34, 49, ("OCHRE", None), ymax=292)
    for (x, y) in ((34, 287), (32, 291), (31, 295)):    # a broken glint down the left side
        crown.px(x, y, "BROWN_MID")
    for x in range(64, 71):
        crown.px(x, 278, "RIM_HOT")
    _merge(L, crown)
    return L


# ---------------------------------------------------------------- the whole figure
def draw_player(rng):
    """The player from behind, title framing: hat top at y 279, poncho over the shoulders,
    fringe hanging to about y 505, gun on the right hip at x 58..84, legs to the bottom."""
    L = Layer()
    for part in (_legs(rng), _arm(rng), _torso(), _belt(), _holster_and_gun(), _poncho(rng),
                 _fringe(rng), _hair(rng), _hat(rng)):
        _merge(L, part)
    L.outline("INK")
    return L
