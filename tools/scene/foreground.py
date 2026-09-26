"""Foreground layer: the props nearest the camera on the right side of the street.

The near right building itself belongs to the town layer; this layer hangs a weathered cow
skull on its facade, perches a crow on its cap beam, stands a barrel beside the hitching rail,
closes the lower right corner with a dark crate and fence block, and scatters backlit
sagebrush over the lower street. Coordinates are safe-area pixels (see scene/common.py).

Light: the sun sits low behind the town at (155, 222), so every face turned to the camera is
in shadow; top edges and edges facing the sun catch a 1 px RIM line with OCHRE inside it.
Props get a 1 px INK outline; the sagebrush, rope, crow legs and cast shadows do not
(selective outline, see FgLayer).
"""
import math

import numpy as np
from PIL import Image, ImageDraw

import palette as P  # noqa: F401
from scene.common import *  # noqa: F401,F403


class FgLayer(Layer):
    """A Layer whose outline() skips the pixels marked as bare (sagebrush blades, rope, legs
    and cast shadows get no INK ring) and never paints over pixels marked no_ink."""

    def __init__(self):
        super().__init__()
        self.bare_src = np.zeros((H, W), dtype=bool)   # pixels that cast no outline
        self.no_ink = np.zeros((H, W), dtype=bool)     # pixels that never receive outline

    def mark(self, grid, x, y):
        X, Y = int(x) + OX, int(y) + OY
        if 0 <= X < W and 0 <= Y < H:
            grid[Y, X] = True

    def outline(self, c="INK", diag=True):
        a = np.array(self.im)[:, :, 3] > 0
        src = a & ~self.bare_src
        o = np.zeros_like(a)
        shifts = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        if diag:
            shifts += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        for dy, dx in shifts:
            o |= np.roll(np.roll(src, dy, 0), dx, 1)
        o &= ~a
        o &= ~self.no_ink
        ys, xs = np.nonzero(o)
        for y, x in zip(ys, xs):
            self.im.putpixel((int(x), int(y)), col(c))


# icon boxes of the title UI and the captions under them: no bright pixels here
QUIET = [(16, 526, 48, 569), (132, 526, 164, 569), (222, 526, 254, 569),
         (14, 559, 50, 571), (130, 559, 166, 571), (205, 559, 256, 571)]
BRIGHT = ("AMBER", "OCHRE", "RUST", "TAN", "SAND", "LEATHER", "RIM", "BROWN_MID", "CREAM")


def quiet(x, y):
    return any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in QUIET)


def _stroke(pts, r0, r1, step=0.2, ease=1.0):
    # the radius follows r1 + (r0 - r1) * (1 - t ** ease): ease > 1 keeps it full for longer
    """Pixels inside a stroke along a polyline whose radius tapers from r0 to r1.
    Returns {(x, y): (t, ox, oy)}: t runs 0 at the base to 1 at the tip, (ox, oy) is the
    offset of the pixel from the nearest point on the centre line."""
    segs = list(zip(pts, pts[1:]))
    lens = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in segs]
    total = sum(lens)
    samples = []
    run = 0.0
    for (a, b), ln in zip(segs, lens):
        n = max(1, int(ln / step))
        for k in range(n):
            f = k / n
            samples.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, (run + ln * f) / total))
        run += ln
    samples.append((pts[-1][0], pts[-1][1], 1.0))
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    got = {}
    for y in range(int(min(ys) - r0 - 1), int(max(ys) + r0 + 2)):
        for x in range(int(min(xs) - r0 - 1), int(max(xs) + r0 + 2)):
            best = None
            for sx, sy, t in samples:
                d = math.hypot(x - sx, y - sy)
                if best is None or d < best[0]:
                    best = (d, t, x - sx, y - sy)
            d, t, ox, oy = best
            r = r1 + (r0 - r1) * (1.0 - t ** ease)
            if d <= r + 0.12:
                got[(x, y)] = (t, ox, oy)
    return got


# --------------------------------------------------------------------------------------------
# cow skull, nailed to the facade

def _skull_span(r):
    """Left and right x of the skull on row r (None outside)."""
    table = {166: (248, 257), 167: (246, 259), 168: (245, 260), 169: (244, 261),
             184: (244, 261), 185: (245, 261), 186: (246, 259), 187: (246, 259),
             188: (246, 259), 208: (249, 255), 209: (249, 255), 210: (249, 255),
             211: (250, 254), 212: (251, 253)}
    if r in table:
        return table[r]
    if 170 <= r <= 178:
        return (244, 261)
    if 179 <= r <= 183:                          # the orbits bulge out a little
        return (243, 262)
    if 189 <= r <= 207:
        w = int(14 - 7 * (r - 188) / 19.0 + 0.5)
        left = 252 - (w - 1) // 2 if w % 2 else 253 - w // 2
        return (left, left + w - 1)
    return None


def _horn(L, pts):
    """A heavy horn along a polyline, 5 px thick at the base tapering to 1 px at the tip.
    LEATHER body with OCHRE inside the lit edge, BROWN_DARK along the underside, a 1 px RIM
    on the edges turned up and toward the sun (AMBER where it meets the skull)."""
    got = _stroke(pts, 2.5, 0.3, ease=2.2)
    sx, sy = 0.55, 0.83                          # shade direction: down and right
    out = {}
    for (x, y), (t, ox, oy) in got.items():
        r = 0.3 + (2.5 - 0.3) * (1.0 - t ** 2.2)
        s = (ox * sx + oy * sy) / max(0.6, r)
        c = "OCHRE" if s < -0.1 else ("LEATHER" if s < 0.45 else "BROWN_MID")
        if (s > 0.1) and ((x, y + 1) not in got or (x + 1, y) not in got):
            c = "BROWN_DARK"
        if s < 0.2 and (x, y - 1) not in got:
            c = "AMBER" if t < 0.12 else "RIM"          # edges turned up catch the sun
        elif s < 0.2 and (x - 1, y) not in got:
            c = "AMBER" if t < 0.6 else "RIM"            # the flank facing the sun, dimmer
        if t > 0.93:
            c = "BROWN_MID" if s > 0 else "OCHRE"
        out[(x, y)] = c
    # the band just inside the lit edge stays OCHRE, so the light rolls round the horn
    for (x, y), c in list(out.items()):
        if c == "LEATHER" and (out.get((x - 1, y)) in ("RIM", "AMBER")
                               or out.get((x, y - 1)) in ("RIM", "AMBER")):
            out[(x, y)] = "OCHRE"
    # a darker ring where the sheath meets the poll
    for (x, y), (t, ox, oy) in got.items():
        if 0.1 <= t <= 0.15 and out[(x, y)] in ("OCHRE", "LEATHER"):
            out[(x, y)] = "BROWN_MID"
    for (x, y), c in out.items():
        L.px(x, y, c)
    return out


def cow_skull(L):
    """Weathered skull facing the viewer, turned a little right. Box x 233..269, y 150..213.
    Dirty warm bone: TAN on the sun side, OCHRE, then SKIN_DARK and BROWN_MID on the shaded
    right third, grime and cracks in BROWN_MID. SAND on the lit dome, CREAM only on the crown
    and a few glints."""
    # rope loop behind the skull, hung from a nail
    rope = []
    for (a, b) in (((252, 161), (247, 166)), ((253, 161), (258, 166))):
        n = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
        rope += [(a[0] + (b[0] - a[0]) * i // n, a[1] + (b[1] - a[1]) * i // n) for i in range(n + 1)]
    for p in rope:
        L.px(p[0], p[1], "BROWN")
        L.mark(L.bare_src, *p)
    for p in ((252, 161), (253, 161), (252, 160)):
        L.px(p[0], p[1], "GREY_DARK")
    # horns: out sideways, then curling up into crescents
    _horn(L, [(245, 172.5), (240, 173.5), (236, 172.5), (233.5, 168.5), (233.5, 162.5), (235, 156)])
    _horn(L, [(260, 171), (264, 171.5), (266.5, 168), (267.5, 162), (267.5, 156), (267, 150)])
    rows = {r: _skull_span(r) for r in range(166, 213)}
    m = {}
    for r, (a, b) in rows.items():
        w = b - a + 1
        for x in range(a, b + 1):
            f = (x - a) / max(1, w - 1)
            if f < 0.44:
                c = "TAN"
            elif f < 0.72:
                c = "OCHRE"
            else:
                c = "SKIN_DARK"
            m[(x, r)] = c
        m[(b, r)] = "BROWN_MID"                              # right edge in shade
    # the lit dome: SAND along the upper left, CREAM only on the crown
    for x in range(249, 254):
        m[(x, 166)] = "CREAM"
    for x in range(247, 253):
        m[(x, 167)] = "SAND"
    for x in range(253, 256):
        m[(x, 167)] = "TAN"
    for r in range(168, 176):
        a, _b = rows[r]
        for x in range(a + 1, a + (4 if r < 172 else 3)):
            m[(x, r)] = "SAND"
    for p in ((244, 169), (244, 170), (245, 169), (261, 169), (261, 170), (260, 169)):
        m[p] = "OCHRE"
    # brow ridge, lit on top, then shade under it across the orbits
    for x in range(245, 261):
        m[(x, 176)] = "SAND" if x < 248 else ("TAN" if x < 256 else "OCHRE")
    for r in (177, 178, 179):
        a, b = rows[r]
        for x in range(a + 1, b):
            if 251 <= x <= 253:
                continue
            m[(x, r)] = "OCHRE" if x < 255 else "SKIN_DARK"
    # eye sockets: slanted INK holes with a shaded ring
    sockets = {180: [(247, 250), (255, 257)], 181: [(246, 250), (255, 258)],
               182: [(246, 250), (255, 258)], 183: [(246, 250), (255, 258)],
               184: [(246, 250), (255, 258)], 185: [(246, 249), (256, 258)],
               186: [(247, 249)]}
    hole = {(x, y) for y, runs in sockets.items() for a, b in runs for x in range(a, b + 1)}
    for (x, y) in hole:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1, 2):
                q = (x + dx, y + dy)
                if q in m and q not in hole:
                    m[q] = "BROWN_MID" if (dy > 0 or dx > 0) and x > 252 else (
                        "SKIN_DARK" if dy > 0 else "OCHRE")
    for (x, y) in hole:
        m[(x, y)] = "INK"
    m[(247, 181)] = "BROWN_BLACK"
    m[(248, 181)] = "BROWN_BLACK"
    # bridge between the orbits and the nasal ridge
    for y in range(180, 188):
        m[(251, y)] = "TAN"
        m[(252, y)] = "TAN"
        m[(253, y)] = "OCHRE"
    for y in range(188, 203):
        m[(251, y)] = "TAN"
        m[(252, y)] = "SAND" if y in (189, 190) else "TAN"
        m[(253, y)] = "OCHRE"
    # nostrils: INK slits with a shaded rim, the tip rounded and shaded underneath
    for y in range(203, 207):
        m[(250, y)] = "INK"
        m[(254, y)] = "INK"
        m[(251, y)] = "OCHRE"
        m[(255, y)] = "BROWN_MID"
    for x in range(249, 256):
        m[(x, 208)] = "TAN" if x < 252 else ("OCHRE" if x < 254 else "SKIN_DARK")
    for x in range(249, 256):
        if (x, 210) in m:
            m[(x, 210)] = "OCHRE" if x < 253 else "SKIN_DARK"
    for x in range(250, 255):
        m[(x, 211)] = "SKIN_DARK" if x < 253 else "BROWN_MID"
    for x in range(251, 254):
        m[(x, 212)] = "BROWN_MID"
    # grime: BROWN_MID and SKIN_DARK clusters in the cheeks, on the muzzle and the dome
    for p in ((248, 190), (249, 190), (249, 191), (256, 191), (256, 192), (257, 192),
              (248, 196), (248, 197), (250, 199), (251, 199), (255, 197), (255, 198),
              (249, 202), (253, 205), (252, 206), (256, 188), (257, 189),
              (247, 172), (248, 172), (257, 173), (258, 173), (255, 170), (256, 170),
              (250, 185), (250, 186)):
        if p in m and m[p] not in ("INK",):
            m[p] = "BROWN_MID"
    for p in ((250, 193), (250, 194), (249, 186), (249, 187), (250, 208), (251, 209),
              (253, 170), (254, 170), (249, 174), (250, 174), (248, 200), (249, 200),
              (254, 174), (254, 175), (247, 193), (248, 193)):
        if p in m and m[p] in ("TAN", "SAND"):
            m[p] = "OCHRE"
    for p in ((254, 192), (254, 193), (255, 201), (256, 201), (258, 176), (259, 176),
              (252, 197), (252, 198)):
        if p in m and m[p] not in ("INK",):
            m[p] = "SKIN_DARK"
    # hairline cracks, 1 px runs
    for p in ((251, 168), (251, 169), (252, 170), (252, 171), (251, 172), (251, 173),
              (257, 169), (258, 170), (258, 171), (253, 189), (253, 190), (252, 191),
              (253, 197), (253, 198), (252, 199), (252, 200), (247, 191), (246, 192)):
        if p in m and m[p] not in ("INK",):
            m[p] = "BROWN_MID"
    # the sun-facing left contour catches a 1 px RIM, down the cranium and the muzzle
    for r in range(169, 205):
        a, _b = rows[r]
        if m.get((a, r)) not in ("INK",):
            m[(a, r)] = "RIM" if r < 198 else "OCHRE"
    # a few glints of clean bone
    for p in ((246, 170), (245, 182), (252, 189), (251, 207)):
        m[p] = "CREAM"
    for (x, y), c in m.items():
        L.px(x, y, c)


# --------------------------------------------------------------------------------------------
# crow on the cap beam

def crow(L):
    """Crow perched on the cap beam of the near right building, facing left.
    Box x 233..266, y 92..126."""
    spans = {92: (245, 249), 93: (243, 251), 94: (242, 252), 95: (241, 252), 96: (241, 252),
             97: (241, 252), 98: (241, 252), 99: (242, 252), 100: (243, 252), 101: (244, 253),
             102: (244, 254),
             103: (244, 256), 104: (244, 257), 105: (244, 258), 106: (243, 259), 107: (243, 260),
             108: (243, 260), 109: (243, 261), 110: (243, 261), 111: (243, 262), 112: (244, 262),
             113: (244, 262), 114: (245, 263), 115: (245, 263), 116: (246, 263), 117: (247, 264),
             118: (248, 264), 119: (249, 265), 120: (250, 265), 121: (251, 265), 122: (258, 266),
             123: (259, 266), 124: (260, 266), 125: (261, 266), 126: (263, 266)}
    m = {}
    for y, (a, b) in spans.items():
        for x in range(a, b + 1):
            m[(x, y)] = "INK"
    body = set(m)
    # folded wing, CHARCOAL, from the shoulder back to the tail
    wing = [(248, 103), (255, 102), (260, 106), (263, 112), (265, 119), (265, 122), (261, 121),
            (255, 116), (250, 110)]
    im = Image.new("L", (40, 40), 0)
    ImageDraw.Draw(im).polygon([(x - 235, y - 90) for x, y in wing], fill=1)
    for yy, xx in zip(*np.nonzero(np.array(im))):
        p = (int(xx) + 235, int(yy) + 90)
        if p in body:
            m[p] = "CHARCOAL"
    # the back above the wing stays INK, as does the contour
    for (x, y) in body:
        if (x + 1, y) not in body or (x, y - 1) not in body:
            m[(x, y)] = "INK"
    # three rows of feather edges on the wing
    for k, (a, b) in enumerate((((250, 106), (257, 107)), ((252, 110), (261, 114)),
                                ((255, 115), (264, 121)))):
        n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1])))
        for i in range(n + 1):
            if (i + k) % 4 == 3:
                continue
            x = int(round(a[0] + (b[0] - a[0]) * i / n))
            y = int(round(a[1] + (b[1] - a[1]) * i / n))
            if m.get((x, y)) == "CHARCOAL":
                m[(x, y)] = "GREY_DARK"
    # belly mid-tone
    for (x, y) in body:
        if 111 <= y <= 120 and 245 <= x <= 251 and m[(x, y)] == "INK":
            if (x - 1, y) in body and (x, y + 1) in body and (x - 1, y + 1) in body:
                m[(x, y)] = "CHARCOAL"
    # cool sheen on the crown, the nape and along the back
    for x, y in ((246, 92), (247, 92), (244, 93), (245, 93), (249, 93), (250, 94), (251, 95),
                 (251, 96), (251, 99), (252, 100), (252, 101), (253, 102), (255, 103),
                 (256, 104), (258, 105), (259, 106)):
        m[(x, y)] = "GREY_DARK"
    for x, y in ((246, 93), (247, 93), (248, 93), (249, 104), (250, 104), (251, 103),
                 (250, 95), (250, 96)):
        m[(x, y)] = "CHARCOAL"
    # tail feathers
    for x, y in ((262, 122), (263, 123), (264, 124), (264, 125), (265, 126)):
        m[(x, y)] = "CHARCOAL"
    # long heavy beak: GREY_DARK upper mandible with a pale ridge, CHARCOAL lower edge,
    # the tip hooked down one pixel
    beak = {95: "....GSSG", 96: "..GSSGGG", 97: ".GGGGGGG", 98: "GCCCCCCC", 99: "G...CCCC"}
    for y, row in beak.items():
        for i, ch in enumerate(row):
            if ch != ".":
                m[(233 + i, y)] = {"G": "GREY_DARK", "S": "SILVER", "C": "CHARCOAL"}[ch]
    m[(241, 97)] = "CHARCOAL"                   # gape line into the head
    m[(245, 95)] = "AMBER"                      # eye
    # legs and toes gripping the cap
    legs = []
    for y in range(121, 126):
        legs += [(251, y), (254, y)]
    legs += [(x, 126) for x in (249, 250, 251, 252, 253, 254, 255, 256)]
    for p in legs:
        m[p] = "CHARCOAL"
    # 1 px RIM only on the throat and the breast, the contour turned to the sun
    rim = [(x, y) for (x, y) in body if (x - 1, y) not in m and 100 <= y <= 114]
    for (x, y) in rim:
        m[(x, y)] = "RIM" if y <= 109 else "OCHRE"
    for (x, y), c in m.items():
        L.px(x, y, c)
    # the legs stay thin
    for (x, y) in legs:
        L.mark(L.bare_src, x, y)


# --------------------------------------------------------------------------------------------
# barrel beside the hitching rail

def _barrel_span(r):
    """Left and right x of the barrel body on row r: 20 px at the ends, 24 at the belly."""
    t = (r - 380) / 36.0
    b = math.sin(math.pi * min(1.0, max(0.0, t)))
    w = 24 if b >= 0.72 else (22 if b >= 0.3 else 20)
    return 257 - w // 2, 256 + w // 2


def barrel(L):
    """Dark oak barrel standing beside the rail, x 245..268, y 376..416, bulging at the belly."""
    top, bot = 380, 416
    for r in range(top, bot + 1):
        a, b = _barrel_span(r)
        for x in range(a, b + 1):
            u = (x - a) / float(b - a)
            if x == a:
                c = "RIM"
            elif x <= a + 2:
                c = "LEATHER"
            elif u < 0.42:
                c = "BROWN_MID"
            elif u < 0.74:
                c = "BROWN"
            elif x < b:
                c = "BROWN_DARK"
            else:
                c = "BROWN_BLACK"
            L.px(x, r, c)
        # stave seams every 4 px, bending with the belly
        for k in range(1, 6):
            x = a + int(round(k * (b - a) / 6.0))
            if x > a + 2:
                L.px(x, r, "BROWN_BLACK")
    # grain on the staves, short runs
    for x, ya, yb in ((253, 386, 390), (257, 399, 403), (261, 386, 389), (253, 401, 405),
                      (249, 399, 402), (264, 390, 393), (260, 402, 405)):
        for y in range(ya, yb + 1):
            a, b = _barrel_span(y)
            if a + 2 < x < b - 2 and not L.is_(x, y, "BROWN_BLACK"):
                L.px(x, y, "BROWN" if x < 258 else "BROWN_DARK")
    # hoops: dark iron, a warm glint along the top edge on the lit left third
    for hy in (383, 396, 410):
        a, b = _barrel_span(hy)
        L.hline(a, b, hy, "CHARCOAL")
        a2, b2 = _barrel_span(hy + 1)
        L.hline(a2, b2, hy + 1, "BROWN_BLACK")
        third = a + (b - a) // 3
        L.hline(a + 1, third, hy, "OCHRE")
        L.px(a, hy, "RIM")
        L.px(a + 2, hy, "RIM")
        L.px(a + 3, hy, "RIM")
        L.px(a, hy + 1, "OCHRE")
    # contact shadow, falling toward the camera
    for y, xa, xb in ((417, 247, 269), (418, 251, 269)):
        for x in range(xa, xb + 1):
            L.px(x, y, "BROWN_BLACK")
            L.mark(L.bare_src, x, y)
    # lid: an ellipse seen from a little above, its far rim lit
    L.ellipse(247, 376, 266, 381, "BROWN_DARK")
    for x in range(247, 267):
        topy = None
        for y in range(376, 382):
            if L.is_(x, y, "BROWN_DARK"):
                topy = y
                break
        if topy is not None:
            L.px(x, topy, "RIM" if x < 253 else ("OCHRE" if x < 262 else "LEATHER"))
    L.hline(250, 263, 378, "BROWN")                 # lid boards
    L.px(256, 377, "BROWN_BLACK")
    L.px(256, 378, "BROWN_BLACK")
    L.px(256, 379, "BROWN_BLACK")
    L.hline(248, 265, 380, "BROWN_MID")             # near chime, lit left
    L.hline(248, 250, 380, "OCHRE")
    L.px(247, 380, "RIM")
    L.px(247, 379, "RIM")
    L.hline(262, 265, 380, "BROWN")


# --------------------------------------------------------------------------------------------
# crate and fence block in the lower right

BOARDS = [7, 5, 8, 6, 7, 5, 8, 6, 7, 6, 8, 5]


def crate(L):
    """Dark crate and fence block closing the lower right corner, x 220..300 from y 445:
    a squat knob, a thick cap beam lit along its top and overhanging on the left, and a dark
    board body."""
    x0, x1 = 224, 300
    # squat knob on the cap: a sawn-off post stub, rounded, lit along its top
    kx0, kx1, ky0 = 241, 250, 445
    for y in range(ky0, 452):
        a, b = kx0, kx1
        if y == ky0:
            a, b = kx0 + 2, kx1 - 2
        elif y == ky0 + 1:
            a, b = kx0 + 1, kx1 - 1
        L.hline(a, b, y, "BROWN_DARK")
    L.hline(kx0 + 2, kx1 - 2, ky0, "RIM")
    L.px(kx0 + 1, ky0 + 1, "RIM")
    L.hline(kx0 + 2, kx1 - 4, ky0 + 1, "OCHRE")
    L.hline(kx1 - 3, kx1 - 2, ky0 + 1, "BROWN_MID")
    L.vline(kx0, ky0 + 2, ky0 + 3, "OCHRE")                   # the flank turned to the sun
    L.vline(kx0, ky0 + 4, 451, "BROWN")
    L.vline(kx1, ky0 + 2, 451, "BROWN_BLACK")
    L.vline(kx0 + 4, ky0 + 3, ky0 + 5, "BROWN_BLACK")          # splits in the stub
    L.vline(kx0 + 7, ky0 + 4, ky0 + 6, "BROWN_BLACK")
    L.vline(kx0 + 2, ky0 + 3, ky0 + 4, "BROWN")
    # cap beam: lit top, mid-dark grained front, overhanging 4 px on the left
    bx0, by0, by1 = x0 - 4, 452, 472
    L.rect(bx0, by0, x1, by1, "BROWN")
    L.hline(bx0, x1, by0, "RIM")                              # lit edge, worn in places
    L.hline(bx0 + 1, x1, by0 + 1, "AMBER")
    for nx, nw, dark in ((229, 2, False), (238, 3, True), (256, 2, False), (263, 3, True),
                         (277, 2, True)):
        L.hline(nx, nx + nw - 1, by0, "BROWN_MID" if dark else "AMBER")
        L.hline(nx, nx + nw - 1, by0 + 1, "BROWN" if dark else "BROWN_MID")
    for nx in (233, 251, 268):
        L.hline(nx, nx + 2, by0 + 1, "OCHRE")
    x = bx0 + 4
    while x <= x1:                                            # the light fading down the face
        ln = 3 + int(hsh(x, 34) * 9)
        c = ("OCHRE", "BROWN_MID", "BROWN_MID", "BROWN", "BROWN", "BROWN")[int(hsh(x, 35) * 6)]
        if c == "OCHRE":
            ln = min(ln, 3)
        L.hline(x, min(x1, x + ln - 1), by0 + 2, c)
        x += ln
    for y in range(by0 + 3, by1 - 1):                         # grain in horizontal streaks
        x = bx0 + 4 + int(hsh(y, 40) * 5)
        while x <= x1:
            ln = 3 + int(hsh(x, y, 41) * 10)
            h = hsh(x, y, 42)
            if h < 0.4 + 0.03 * (y - by0 - 3):             # darker toward the bottom
                c = "BROWN_DARK"
            elif h < 0.5 and y < by0 + 9:
                c = "BROWN_MID" if h < 0.47 else "OCHRE"
                if c == "OCHRE":
                    ln = min(ln, 3)
            elif h < 0.44:
                c = "BROWN_MID"
            else:
                c = None
            if c:
                L.hline(x, min(x1, x + ln - 1), y, c)
            x += ln
    for k in range(3):                                        # long checks in the wood
        gx = bx0 + 6 + int(hsh(k, 51) * 60)
        gy = by0 + 5 + int(hsh(k, 52) * 11)
        ln = 8 + int(hsh(k, 53) * 12)
        L.hline(gx, gx + ln, gy, "BROWN_BLACK")
        L.hline(gx + 1, gx + ln - 2, gy - 1, "BROWN_DARK")
    x = bx0 + 4                                               # shade gathers under the beam
    while x <= x1:
        ln = 3 + int(hsh(x, 36) * 8)
        L.hline(x, min(x1, x + ln - 1), by1 - 1, "BROWN_DARK")
        if hsh(x, 37) < 0.5:
            L.hline(x + 1, min(x1, x + ln - 2), by1 - 2, "BROWN_DARK")
        x += ln + 2 + int(hsh(x, 38) * 4)
    L.hline(bx0, x1, by1, "BROWN_DARK")
    # end grain of the overhang, turned to the sun
    L.vline(bx0, by0, by0 + 9, "RIM")
    L.vline(bx0, by0 + 10, by1 - 3, "OCHRE")
    L.vline(bx0, by1 - 2, by1 - 1, "BROWN_MID")
    L.vline(bx0 + 1, by0 + 1, by0 + 12, "OCHRE")
    L.vline(bx0 + 1, by0 + 13, by1 - 1, "LEATHER")
    L.vline(bx0 + 2, by0 + 2, by1 - 1, "LEATHER")
    L.vline(bx0 + 3, by0 + 2, by1 - 1, "BROWN_MID")
    for y in (by0 + 5, by0 + 6, by0 + 12, by0 + 13):          # growth rings
        L.px(bx0 + 2, y, "BROWN_MID")
    L.vline(bx0 + 1, by0 + 7, by0 + 8, "LEATHER")
    L.vline(bx0 + 3, by1 - 4, by1 - 1, "BROWN_DARK")
    L.hline(bx0, bx0 + 3, by1, "BROWN_BLACK")
    # body: left side face, then boards of uneven width
    top = by1 + 1
    L.rect(x0, top, x0 + 2, 600, "BROWN_BLACK")
    y = top + 1
    while y <= 600:                                           # a dull lit edge in runs
        ln = 6 + int(hsh(y, 61) * 18)
        if hsh(y, 62) < 0.6:
            L.vline(x0 + 1, y, min(600, y + ln), "BROWN_DARK")
        y += ln + 2
    L.rect(x0 + 3, top, x1, 600, "BROWN_DARK")
    edges = []
    bx = x0 + 3
    k = 0
    while bx <= x1:
        edges.append((bx, BOARDS[k % len(BOARDS)]))
        bx += BOARDS[k % len(BOARDS)]
        k += 1
    for bx, bw in edges:
        L.vline(bx, top, 600, "BROWN_BLACK")                  # seam
        y = top + 1                                           # lit left edge, in worn runs
        while y <= 600:
            ln = 6 + int(hsh(bx, y, 1) * 20)
            if hsh(bx, y, 2) < 0.62:
                L.vline(bx + 1, y, min(600, y + ln), "BROWN")
            y += ln + 1 + int(hsh(bx, y, 4) * 4)
        for g in range(3):                                    # grain streaks
            gx = bx + 2 + int(hsh(bx, g, 5) * max(1, bw - 3))
            gy = top + 4 + int(hsh(bx, g, 9) * 110)
            ln = 4 + int(hsh(bx, g, 3) * 9)
            L.vline(gx, gy, gy + ln, "BROWN_BLACK")
        ky = top + 12 + int(hsh(bx, 77) * 90)                 # knot
        L.px(bx + 3, ky, "BROWN_BLACK")
        L.px(bx + 4, ky, "BROWN_BLACK")
        L.px(bx + 3, ky + 1, "BROWN")
    # shadow under the overhanging cap
    L.hline(x0, x1, top, "BROWN_BLACK")
    # one batten across the boards, its lit top worn into runs
    by = 500
    L.rect(x0 + 3, by, x1, by + 4, "BROWN")
    L.hline(x0 + 3, x1, by + 4, "BROWN_BLACK")
    L.hline(x0 + 3, x1, by + 3, "BROWN_DARK")
    x = x0 + 3
    while x <= x1:
        ln = 3 + int(hsh(x, 81) * 9)
        c = "OCHRE" if hsh(x, 82) < 0.55 else "BROWN_MID"
        L.hline(x, min(x1, x + ln), by, c)
        x += ln + 1 + int(hsh(x, 83) * 3)
    L.hline(x0, x0 + 2, by, "BROWN_DARK")
    for bx, bw in edges:
        L.px(bx + bw // 2, by + 2, "GREY_DARK")               # nail heads
    # nails near the top of each board
    for bx, bw in edges:
        L.px(bx + bw // 2, top + 3, "GREY_DARK")
    # a fence post in front of the lower left corner of the crate
    fx0, fx1, fy0 = 211, 221, 543
    L.rect(fx0, fy0, fx1, 600, "BROWN_DARK")
    L.hline(fx0 + 1, fx1 - 1, fy0, "RIM")
    L.hline(fx0 + 1, fx1 - 2, fy0 + 1, "OCHRE")
    L.px(fx1 - 1, fy0 + 1, "BROWN_MID")
    L.vline(fx0, fy0 + 1, fy0 + 2, "RIM")
    L.vline(fx0, fy0 + 3, 557, "OCHRE")
    L.vline(fx0, 558, 600, "BROWN")
    L.vline(fx0 + 1, fy0 + 2, 600, "BROWN")
    L.vline(fx1, fy0 + 1, 600, "BROWN_BLACK")
    for gx, gy, ln in ((fx0 + 3, fy0 + 5, 9), (fx0 + 6, fy0 + 12, 12), (fx0 + 4, fy0 + 24, 8),
                       (fx0 + 7, fy0 + 30, 7), (fx0 + 5, fy0 + 2, 4)):
        L.vline(gx, gy, gy + ln, "BROWN_BLACK")
    L.px(fx0 + 3, fy0 + 3, "GREY_DARK")
    # the icon and caption over the lower crate: keep it dark there
    for yy in range(526, 572):
        for xx in range(fx0, 271):
            if quiet(xx, yy) and (L.is_(xx, yy, "BROWN") or L.is_(xx, yy, "OCHRE")):
                L.px(xx, yy, "BROWN_DARK")


# --------------------------------------------------------------------------------------------
# sagebrush

def _curve(p0, p1, p2):
    """Pixels of a quadratic curve, in order, without repeats."""
    out = []
    n = int(4 * (abs(p2[0] - p0[0]) + abs(p2[1] - p0[1]))) + 4
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
        q = (int(round(x)), int(round(y)))
        if not out or out[-1] != q:
            out.append(q)
    return out


def sagebrush(L, rng, bx, by, w, h, lit=True):
    """A backlit clump: 9..13 spiky blades fanning up from (bx, by), about -55..55 degrees.
    Blades are 2 px wide over most of their length with a BROWN_BLACK shaded right side.
    On the sun-side blades the left pixel catches the light up the blade (BROWN_MID, then
    LEATHER), the top 2..3 px turn TAN or SAND and a few tips burn AMBER. No outline."""
    n = max(9, min(13, int(round(w / 2.2)) + rng.randint(-1, 1)))
    blades = []
    for i in range(n):
        f = (i + 0.5) / n
        ang = math.radians(-55 + 110 * f + rng.uniform(-6, 6))
        reach = (w / 2.0 - 0.5) * math.sin(ang) / math.sin(math.radians(55))
        ex = bx + reach * rng.uniform(0.85, 1.05)
        ey = by - h * (0.5 + 0.5 * abs(math.cos(ang)) ** 1.5) * rng.uniform(0.68, 1.0)
        sx = bx + (f - 0.5) * w * 0.3
        ctrl = (sx + (ex - sx) * 0.1, by - (by - ey) * 0.62)
        blades.append((ang, _curve((sx, by), ctrl, (ex, ey))))
    pix = {}

    def put(q, c, rank):
        if q not in pix or pix[q][1] <= rank:
            pix[q] = (c, rank)

    # small dark crown where the blades meet the ground
    half = max(2, int(w * 0.16))
    for x in range(bx - half, bx + half + 1):
        put((x, by), "BROWN_BLACK", 0)
    for x in range(bx - half + 1, bx + half):
        put((x, by - 1), "BROWN_BLACK", 0)
    order = sorted(range(n), key=lambda i: abs(blades[i][0]), reverse=True)   # outer first
    wide = 0.72 if h >= 16 else 0.3            # small clumps keep 1 px blades
    tips = []
    for rank, i in enumerate(order):
        ang, seg = blades[i]
        sun = ang < 0.3 and lit
        L_ = len(seg)
        top = rng.randint(2, 3)
        for j, q in enumerate(seg):
            t = j / max(1, L_ - 1)
            c = "BROWN_BLACK" if t < 0.28 else "BROWN_DARK"
            if sun and t >= 0.3:
                c = "BROWN_MID" if t < 0.62 else ("LEATHER" if t < 0.8 else "OCHRE")
            if sun and j >= L_ - top:
                c = "SAND" if (j == L_ - 2 and ang < -0.35) else "TAN"
            if not sun and lit and j >= L_ - 2:
                c = "BROWN_MID"
            put(q, c, 1 + rank)
            if t < wide:                                     # 2 px wide below the tip
                put((q[0] + 1, q[1]), "BROWN_BLACK" if t < 0.3 or not sun else "BROWN_DARK", 1 + rank)
        if sun:
            tips.append((seg[-1][1], seg[-1], 1 + rank))
    tips.sort()
    for _y, q, rank in tips[:rng.randint(3, 6)]:
        put(q, "AMBER", rank)
    # shadow falling toward the camera
    half = int(w * 0.3)
    for x in range(bx - half, bx + half + 1):
        if (x, by + 1) not in pix:
            put((x, by + 1), "BROWN_BLACK", 0)
    for (x, y), (c, _r) in pix.items():
        if quiet(x, y) and c in BRIGHT:
            c = "BROWN_DARK"
        L.px(x, y, c)
        L.mark(L.bare_src, x, y)


# base centre x, base y, width, height, lit
CLUMPS = [
    (212, 520, 28, 24, True),      # right of the button column, before the crate
    (202, 494, 17, 15, True),
    (207, 468, 13, 12, True),
    (198, 443, 13, 11, True),
    (112, 551, 30, 28, True),      # right of the player, left of the middle icon
    (186, 553, 28, 24, True),      # between the middle and the right icon
    (150, 530, 20, 14, True),      # tips peeking between the buttons and the middle icon
    (100, 584, 20, 16, True),
    (197, 584, 20, 16, True),
    (170, 584, 16, 11, False),
]


def draw_foreground(rng):
    """Foreground layer: skull and crow on the near right building, barrel, crate, sagebrush."""
    fg = FgLayer()
    # sagebrush first: the crate stands in front of anything that reaches it
    for bx, by, w, h, lit in CLUMPS:
        sagebrush(fg, rng, bx, by, w, h, lit)
    cow_skull(fg)
    crow(fg)
    barrel(fg)
    crate(fg)
    fg.outline("INK")
    return fg
