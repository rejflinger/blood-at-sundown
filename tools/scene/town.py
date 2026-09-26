"""The town: the saloon block and the second left building, the far rows on both sides, the near
right building with its porch and lantern, the church at the end of the street, the windmill,
the water tower, telegraph poles and the wagon.

The sun sits behind the town, so every face turned to the camera is dark umber; light arrives as
1 px rims (RIM over OCHRE) on top edges and on the vertical edges that face the sun, and from
lamps and lit windows. The three near buildings (saloon, L2, N1) are drawn in screen space along
sloped lines that cheat the perspective the way the concept does; the far rows follow the street
camera loosely. All coordinates are safe-area pixels; sloped lines run on into the overscan."""
import contextlib
import math

import palette as P
from scene.common import *  # noqa: F401,F403


X0, X1 = -OX, SAFE_W + OX - 1     # the whole layer, overscan included
# The cluster at the end of the street (church, far rows, water tower, far poles) is drawn in
# its own coordinates and set this many whole pixels lower, so the purple valley shows above it.
FAR_DY = 7

_RGBA = {n: P.rgb(n, 0.0) + (255,) for n in P.NAMES}
_NAME = {v[:3]: n for n, v in _RGBA.items()}
_DY = [0]                          # vertical offset of whatever is being drawn (see far())


@contextlib.contextmanager
def far():
    """Everything drawn inside `with far():` lands FAR_DY px lower (whole pixels only)."""
    _DY[0] = FAR_DY
    try:
        yield
    finally:
        _DY[0] = 0


# raster helpers ------------------------------------------------------------------------------
def put(L, x, y, c):
    X, Y = int(x) + OX, int(y) + OY + _DY[0]
    if c and 0 <= X < W and 0 <= Y < H:
        L.im.putpixel((X, Y), _RGBA[c])


def at(L, x, y):
    X, Y = int(x) + OX, int(y) + OY + _DY[0]
    if 0 <= X < W and 0 <= Y < H:
        p = L.im.getpixel((X, Y))
        if p[3]:
            return _NAME.get(p[:3])
    return None


def poly(L, pts, c):
    L.poly([(x, y + _DY[0]) for x, y in pts], c)


def line(L, pts, c):
    L.line([(x, y + _DY[0]) for x, y in pts], c)


def fy(line, x):
    """y of a sloped line ((xa, ya), (xb, yb)) at column x, carried on past its ends."""
    (xa, ya), (xb, yb) = line
    return ya + (yb - ya) * (x - xa) / (xb - xa)


def ry(line, x):
    return int(math.floor(fy(line, x) + 0.5))


def band(L, line, xa, xb, rows):
    """A sloped strip: rows[k] painted k pixels under the line in every column xa..xb."""
    for x in range(xa, xb + 1):
        y = ry(line, x)
        for k, c in enumerate(rows):
            put(L, x, y + k, c)


def hband(L, xa, xb, y, c):
    for x in range(int(xa), int(xb) + 1):
        put(L, x, y, c)


def vband(L, x, ya, yb, c):
    for y in range(int(ya), int(yb) + 1):
        put(L, x, y, c)


def box(L, xa, ya, xb, yb, c):
    for y in range(int(ya), int(yb) + 1):
        for x in range(int(xa), int(xb) + 1):
            put(L, x, y, c)


WINDOWS = []                       # lit window rects (with their warm band): lamp dither skips them


def in_window(x, y):
    y += _DY[0]
    return any(a <= x <= c and b <= y <= d for a, b, c, d in WINDOWS)


# one step warmer along the wood ramp, for surfaces a lamp lights up
WARM = {"INK": "BROWN_BLACK", "CHARCOAL": "BROWN_BLACK", "BROWN_BLACK": "BROWN_DARK",
        "SHADOW": "BROWN_DARK", "BROWN_DARK": "BROWN", "BROWN": "BROWN_MID", "BROWN_MID": "LEATHER"}


def warm(L, cx, cy, r_in, r_out, clip=None, sy=1.15):
    """Stepped lamplight: two ramp steps warmer inside r_in, one step out to r_out. The band
    edges are hard and wander by up to a pixel from row to row, so the light reads as warm
    wood in solid runs, never as a dotted halo."""
    for y in range(int(cy - r_out) - 2, int(cy + r_out) + 3):
        j_in = 2.0 * hsh(y, int(cx), int(cy), 71) - 1.0
        j_out = 2.0 * hsh(y, int(cx), int(cy), 72) - 1.0
        for x in range(int(cx - r_out) - 2, int(cx + r_out) + 3):
            if clip and not (clip[0] <= x <= clip[2] and clip[1] <= y <= clip[3]):
                continue
            d = math.hypot(x - cx, (y - cy) * sy)
            n = 2 if d <= r_in + j_in else (1 if d <= r_out + j_out else 0)
            c = at(L, x, y)
            if not n or c not in WARM or in_window(x, y):
                continue
            for _ in range(n):
                c = WARM.get(c, c)
            put(L, x, y, c)


def lamp_glow(L, cx, cy, k=1.0, clip=None):
    """Lamplight on the wood round a lantern: solid warm steps only, no dotted spill."""
    warm(L, cx, cy, 13 * k, 24 * k, clip=clip)


def siding(y, top, bot, h0, step=3):
    """Board index at row y and whether y is a seam row, for boards that fan out between two
    sloped lines (their y at this column); h0 is the nominal height the step is measured in."""
    t0 = (y - top) / (bot - top) * h0
    t1 = (y + 1 - top) / (bot - top) * h0
    k = int(math.floor(t0 / step))
    return k, int(math.floor(t1 / step)) != k


def board(x, k, base="BROWN_DARK", light="BROWN", seam="BROWN_BLACK", run=31):
    """Colour of a siding board k at column x: butt joints every `run` px, one plank in six light."""
    u = x + k * 13
    if u % run == 0:
        return seam
    return light if hsh(k, u // run, 5) < 0.17 else base


def wall_spill(L, x0, y0, x1, y1):
    """Window light on the wall: a solid band one ramp step warmer, one pixel wide, round the
    frame (a warm pixel cluster, never a dotted halo)."""
    for y in range(y0 - 1, y1 + 2):
        for x in range(x0 - 1, x1 + 2):
            if x0 <= x <= x1 and y0 <= y <= y1:
                continue
            cur = at(L, x, y)
            if cur in WARM and cur not in ("BROWN_MID", "BROWN"):
                put(L, x, y, WARM[cur])


def pane_colour(x, y, px0, py0, px1, py1, first_row):
    """A lit pane in deep warm glass like the concept: AMBER, ORANGE along the bottom (two rows
    on tall panes), and in the top panes only a small LAMP cluster in the upper corner where the
    lamp inside shows through. LAMP_HOT is kept for the lantern flames."""
    h = py1 - py0 + 1
    i, j = y - py0, x - px0
    if first_row:
        if h > 2 and px1 > px0:
            hot = i + j <= 1                            # 3 px: the corner and its two neighbours
        elif px1 > px0:
            hot = i == 0 and j <= 1
        else:
            hot = j == 0 and i <= 1
        if hot:
            return "LAMP"
    if h > 2 and (y == py1 or (h > 7 and y == py1 - 1)):
        return "ORANGE"
    return "AMBER"


def lit_window(L, x0, y0, x1, y1, mull_x=(), mull_y=(), spill_c="RUST", tops=None):
    """1 px BROWN frame, deep AMBER and ORANGE panes (see pane_colour), BROWN_BLACK mullions
    and a solid warm band on the wall around it. `tops` (optional) maps column -> top row for
    windows sheared along a sloped facade."""
    sh = (tops[x0] - y0) if tops else 0
    dy = _DY[0]
    WINDOWS.append((x0 - 1, y0 + sh - 1 + dy, x1 + 1, y1 + sh + 1 + dy + (x1 - x0 if tops else 0)))
    if spill_c:
        wall_spill(L, x0, y0 + sh, x1, y1 + sh)
    xs = [x0] + sorted(mull_x) + [x1]
    ys = [y0] + sorted(mull_y) + [y1]
    for x in range(x0, x1 + 1):
        s = (tops[x] - y0) if tops else 0
        for y in range(y0, y1 + 1):
            if x in (x0, x1) or y in (y0, y1):
                c = "BROWN"
            elif x in mull_x or y in mull_y:
                c = "BROWN_BLACK"
            else:
                px0 = max(v for v in xs if v < x) + 1
                px1 = min(v for v in xs if v > x) - 1
                py0 = max(v for v in ys if v < y) + 1
                py1 = min(v for v in ys if v > y) - 1
                c = pane_colour(x, y, px0, py0, px1, py1, py0 == y0 + 1)
            put(L, x, y + s, c)


def small_window(L, x, y, w=2, h=3, lit=True):
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            if lit:
                c = "AMBER" if yy == y + h - 1 and h > 2 else "LAMP"
                put(L, xx, yy, c)
            else:
                put(L, xx, yy, "CHARCOAL" if yy > y else "SHADOW")


def post(L, x, ya, yb, w, lit_side, hot=True):
    """Porch post: BROWN with a rim (RIM, then OCHRE inside it) on the side facing the sun."""
    rim, inner = ("RIM", "OCHRE") if hot else ("OCHRE", "BROWN")
    for y in range(int(ya), int(yb) + 1):
        for k in range(w):
            c = "BROWN"
            if w >= 3 and k == (0 if lit_side > 0 else w - 1):
                c = "BROWN_DARK"
            put(L, x + k, y, c)
        if w > 1:
            e = x + w - 1 if lit_side > 0 else x
            put(L, e, y, rim)
            if w >= 3:
                put(L, e - lit_side, y, inner)


def hanging_lantern(L, xa, ya, xb, yb, g0, g1, core, bars=()):
    """A lantern xa..xb wide: a stepped hood ya..g0-1 (RIM on top, INK outline), glass g0..g1
    with bevelled corners, banded ORANGE at the frame through AMBER and LAMP to a LAMP_HOT
    flame (the core box), CHARCOAL cage bars, a base that narrows to g1+1..yb, a finial."""
    cx = (core[0] + core[1]) / 2.0
    cy = (core[2] + core[3]) / 2.0
    hw = (core[1] - core[0] + 1) / 2.0
    hh = (core[3] - core[2] + 1) / 2.0
    mx = (xa + xb) / 2.0
    half = (xb - xa) / 2.0
    n = g0 - ya
    for i, y in enumerate(range(ya, g0)):             # hood: widens row by row
        hwid = half - max(0, (n - 2 - i)) * (half / max(1, n))
        if i == 0:
            hwid = min(hwid, max(1.5, half * 0.35))
        x0, x1 = int(math.floor(mx - hwid + 0.5)), int(math.floor(mx + hwid + 0.5))
        hband(L, x0, x1, y, "RIM" if i == 0 else "CHARCOAL")
        put(L, x0, y, "INK")
        put(L, x1, y, "INK")
        if 0 < i < n - 1:
            put(L, x0 + 1, y, "RIM")
            put(L, x1 - 1, y, "RIM")
    hband(L, xa, xb, g0 - 1, "INK")
    put(L, int(math.floor(mx)), ya - 1, "CHARCOAL")
    put(L, int(math.floor(mx)) + 1, ya - 1, "CHARCOAL")
    tall = g1 - g0 > 20
    for y in range(g0, g1 + 1):                        # glass
        bev = 1 if (y - g0 < (2 if tall else 1) or g1 - y < (2 if tall else 1)) else 0
        for x in range(xa + bev, xb - bev + 1):
            ee = min(x - xa, xb - x) - bev
            u = (x - cx) / max(1.0, hw * 0.7)
            w = (y - cy) / max(1.0, hh * 0.6)
            e = math.sqrt(u * u + w * w)
            v = (y - g0) / max(1.0, g1 - g0)
            if ee == 0:
                c = "INK"
            elif x in bars and not e <= 1.0:
                c = "CHARCOAL"
            elif ee == 1 or y == g1 or (tall and y >= g1 - 1):
                c = "ORANGE"
            elif e <= 1.0:
                c = "LAMP_HOT"
            elif e <= 1.3 or (e <= 1.7 and dith(x + OX, y + OY, (1.7 - e) / 0.4 * 0.5)):
                c = "LAMP"
            elif y == g0 or (v > 0.75 and dith(x + OX, y + OY, (v - 0.75) * 2.0)):
                c = "ORANGE"
            else:
                c = "AMBER"
            put(L, x, y, c)
    m = yb - g1
    for i, y in enumerate(range(g1 + 1, yb + 1)):     # base
        inset = 0 if i == 0 else int(round(i * half / (m + 1)))
        hband(L, xa + inset, xb - inset, y, "INK" if i == 0 else "CHARCOAL")
        put(L, xa + inset, y, "INK")
        put(L, xb - inset, y, "INK")
    fx = int(math.floor(mx))
    put(L, fx, yb + 1, "CHARCOAL")
    put(L, fx + 1, yb + 1, "CHARCOAL")
    if yb - ya > 30:
        put(L, fx, yb + 2, "CHARCOAL")
        put(L, fx + 1, yb + 2, "INK")
        put(L, fx, yb + 3, "INK")


# centre: church, windmill, water tower, poles -----------------------------------------------
def church(L):
    """A small white-steepled church at the end of the street, backlit: dark planked body,
    rim-lit gable, a tower rising off the ridge with a lit belfry, spire and cross, and an open
    door pouring lamplight into the street."""
    # body with vertical planks, the bottom rows in shadow; it stands on the street at y 298
    # (305 on screen, FAR_DY lower) so the lit door ends there and the street's lit path runs
    # straight on from its step
    for x in range(127, 154):
        for y in range(285, 299):
            c = "BROWN" if (x - 127) % 4 == 2 else "BROWN_DARK"
            if y >= 296:
                c = "SHADOW"
            put(L, x, y, c)
    vband(L, 153, 285, 295, "OCHRE")
    # tower first: the gable roof covers its foot
    box(L, 137, 266, 143, 284, "BROWN_DARK")
    vband(L, 138, 273, 284, "BROWN")
    vband(L, 141, 273, 284, "BROWN")
    vband(L, 143, 266, 284, "RIM")
    vband(L, 142, 267, 284, "OCHRE")
    vband(L, 137, 266, 284, "BROWN_BLACK")
    for y, xa, xb in ((268, 140, 140), (269, 139, 141), (270, 139, 141), (271, 139, 141)):
        hband(L, xa, xb, y, "LAMP")
    put(L, 140, 269, "LAMP_HOT")
    hband(L, 139, 141, 272, "AMBER")
    hband(L, 136, 144, 273, "BROWN")
    hband(L, 136, 144, 274, "BROWN_BLACK")
    put(L, 144, 273, "RIM")
    # a slim spire and the cross, standing clear below the sun
    for y in range(257, 265):
        hw = (y - 257) * 3 // 7
        hband(L, 140 - hw, 140 + hw, y, "CHARCOAL")
        put(L, 140 + hw, y, "RIM")
    hband(L, 136, 144, 265, "BROWN_BLACK")
    put(L, 144, 265, "RIM")
    put(L, 136, 265, "INK")
    vband(L, 140, 250, 256, "CHARCOAL")
    hband(L, 138, 142, 252, "CHARCOAL")
    put(L, 141, 253, "RIM")
    put(L, 141, 254, "RIM")
    put(L, 143, 252, "RIM")
    # the front gable, dark with shingle rows, rim-lit on both slopes (hotter on the sun side)
    poly(L, [(125, 287), (140, 277), (155, 287)], "BROWN_BLACK")
    for y in range(280, 288, 3):
        for x in range(125, 156):
            if at(L, x, y) == "BROWN_BLACK" and at(L, x, y - 1) == "BROWN_BLACK":
                put(L, x, y, "BROWN_DARK")
    line(L, [(125, 287), (140, 277)], "RIM")
    line(L, [(140, 277), (155, 287)], "RIM_HOT")
    line(L, [(126, 287), (140, 278)], "OCHRE")
    line(L, [(140, 278), (154, 287)], "OCHRE")
    put(L, 140, 277, "RIM_HOT")
    hband(L, 126, 154, 288, "BROWN_BLACK")
    # windows
    for wx in (130, 149):
        box(L, wx, 290, wx + 1, 294, "AMBER")
        put(L, wx, 290, "LAMP")
        put(L, wx + 1, 290, "LAMP")
        put(L, wx, 291, "LAMP")
    # the open door, light pouring out
    for y in range(290, 299):
        for x in range(136, 145):
            dx = abs(x - 140)
            edge = {290: 2, 291: 3}.get(y, 4)
            if dx > edge:
                continue
            c = "BROWN_BLACK" if dx == edge or y == 290 else "LAMP"
            if c == "LAMP" and 139 <= x <= 141 and 293 <= y <= 296:
                c = "LAMP_HOT"
            put(L, x, y, c)
    vband(L, 140, 292, 298, "BROWN")
    warm(L, 140, 294, 4, 8, clip=(127, 285, 153, 298))
    # a flat step in front of the door, its tread catching the light; no riser under it, so the
    # lit path on the street starts right below the tread
    hband(L, 134, 146, 299, "LEATHER")
    hband(L, 136, 144, 299, "AMBER")


def windmill(L):
    cx, cy, r = 205, 192, 11
    box(L, 199, 204, 211, 206, "CHARCOAL")
    hband(L, 199, 211, 204, "BROWN_DARK")
    put(L, 199, 205, "RIM")
    # lattice tower: two legs splaying out, horizontal struts every 10 rows, X braces between
    la, lb = ((201, 206), (192, 275)), ((209, 206), (218, 275))

    def lx(line, y):
        (xa, ya), (xb, yb) = line
        return xa + (xb - xa) * (y - ya) / (yb - ya)
    struts = list(range(215, 276, 10))
    prev = 206
    for y in struts:
        L.line([(lx(la, prev), prev), (lx(lb, y), y)], "CHARCOAL")
        L.line([(lx(lb, prev), prev), (lx(la, y), y)], "CHARCOAL")
        L.line([(lx(la, y), y), (lx(lb, y), y)], "CHARCOAL")
        prev = y
    L.line(list(la), "CHARCOAL")
    L.line(list(lb), "CHARCOAL")
    for y in range(206, 276):
        put(L, int(math.floor(lx(la, y) + 0.5)) - 1, y, "RIM")
    # tail: a thin arm and a small tapered fin behind the wheel, with sky all round it
    L.line([(cx + 2, cy), (215, 191)], "CHARCOAL")
    for x in range(215, 222):
        ya = 190 - (x - 215) * 2 // 6
        yb = 193 + (x - 215) * 2 // 6
        vband(L, x, ya, yb, "CHARCOAL")
        put(L, x, yb, "RIM")
    vband(L, 221, 189, 194, "BROWN_DARK")
    # wheel: 12 broad dark sails that widen towards their tips, sky between them; the sails on
    # the sun side (lower left) catch the light on one edge and at the tip
    sun = math.atan2(222 - cy, 155 - cx)
    slot = 2 * math.pi / 12
    for y in range(cy - r - 1, cy + r + 2):
        for x in range(cx - r - 1, cx + r + 2):
            dx, dy = x - cx, y - cy
            d = math.hypot(dx, dy)
            if d >= r + 0.5:
                continue
            a = math.atan2(dy, dx)
            k = int(math.floor((a - slot / 2) / slot + 0.5))
            ak = k * slot + slot / 2
            da = (a - ak + math.pi) % (2 * math.pi) - math.pi
            off = da * d                                # signed distance across the sail
            half = 0.5 + max(0.0, d - 3.0) * 0.16       # 1 px at the hub, 4 px at the tip
            if d >= 3.0 and abs(off) > half:
                continue
            lit = math.cos(ak - sun) > 0.2
            deg = math.degrees(a) % 360
            if d < 3.0:
                c = "CHARCOAL"
            elif d >= r - 0.5 and 110 <= deg <= 220:
                c = "RIM"
            elif lit and off > half - 1.0 and d > 5:
                c = "RUST"
            elif lit:
                c = "BROWN_DARK"
            else:
                c = "CHARCOAL"
            put(L, x, y, c)
    box(L, cx - 1, cy - 1, cx + 1, cy + 1, "INK")


def water_tower(L, x=99):
    """A small water tank on stilts behind the far left row (x is its left edge), kept low so it
    stays under the church tower, and narrow so it stands clear of L2's corner on the left and
    of the telegraph pole's crossbar on the right (2..3 px of sky each side)."""
    for x0, x1 in ((2, 0), (5, 5), (8, 8), (10, 12)):                 # legs
        line(L, [(x + x0, 271), (x + x1, 292)], "CHARCOAL")
    line(L, [(x + 2, 274), (x + 10, 286)], "CHARCOAL")
    line(L, [(x + 10, 274), (x + 2, 286)], "CHARCOAL")
    hband(L, x + 1, x + 11, 274, "CHARCOAL")
    for xx in range(x + 1, x + 12):
        for y in range(261, 271):
            put(L, xx, y, "BROWN" if (xx - x) % 2 == 0 else "BROWN_DARK")
    vband(L, x + 11, 261, 270, "RIM")
    vband(L, x + 10, 262, 270, "OCHRE")
    for y in (263, 268):
        hband(L, x + 1, x + 9, y, "CHARCOAL")
    hband(L, x + 1, x + 11, 270, "BROWN_BLACK")
    poly(L, [(x, 261), (x + 6, 257), (x + 12, 261)], "CHARCOAL")
    line(L, [(x + 6, 257), (x + 12, 261)], "RIM")


def telegraph_pole(L, x, y0, y1, bar):
    vband(L, x, y0, y1, "CHARCOAL")
    hband(L, x - 4, x + 4, bar, "CHARCOAL")
    for k in (-4, -2, 2, 4):
        put(L, x + k, bar - 1, "RIM")
    put(L, x + 1, y0 + 1, "RIM")


# left side ----------------------------------------------------------------------------------
ROOF = ((0, 88), (31, 104))        # saloon roof line
BEAM = ((0, 148), (60, 186))       # balcony beam
PBEAM = ((0, 229), (48, 241))      # porch beam under the sign
TOP2 = ((48, 206), (96, 235))      # second left building
RAIL2 = ((48, 222), (96, 251))
ROOF2 = ((50, 246), (124, 287))    # its porch roof, running on over the far row


def base_l(x):
    return int(math.floor(296 + 0.227 * (140 - x) + 0.5))


def walk_l(x):
    return int(math.floor(296 + 0.4 * (140 - x) + 0.5))


def far_row_roof(x):
    """The far left row's porch roofs: L2's roof line carried on, stepping 1 px per building."""
    return ry(ROOF2, x) + (0 if x <= 106 else 1)


def doorway(L, x, y0, y1, w=3):
    """A far open doorway: lamplight with a hot top and a warm sill."""
    for y in range(y0, y1 + 1):
        for xx in range(x, x + w):
            c = "LAMP" if y < y1 - 1 else "AMBER"
            if y <= y0 + 1 and xx == x + w // 2:
                c = "LAMP_HOT"
            put(L, xx, y, c)
    put(L, x - 1, y1, "OCHRE")
    put(L, x + w, y1, "OCHRE")


def far_left_row(L):
    """L3..L5: small far buildings, flat dark walls with rim-lit tops, lit doorways and a few
    windows under the porch that runs on from L2."""
    for x in range(96, 125):
        if x <= 106:                                   # L3, a gable
            top = 266 + int(round(abs(x - 101) * 1.2))
            hot = x > 101
        elif x <= 116:                                 # L4, false front with a raised centre
            top = 277 if 109 <= x <= 113 else 280
            hot = True
        else:                                          # L5
            top = 286
            hot = True
        roof = far_row_roof(x)
        for y in range(top, base_l(x) + 1):
            if y == top:
                c = "RIM_HOT" if hot else "RIM"
            elif y == top + 1:
                c = "OCHRE"
            elif y > roof + 2 and y <= roof + 4:        # the shade right under the porch roof
                c = "SHADOW"
            elif y > roof:
                c = "BROWN_BLACK"
            else:
                c = "BROWN_DARK"
            put(L, x, y, c)
    # dark joints where the fronts meet
    vband(L, 106, 280, 305, "INK")
    vband(L, 116, 286, 302, "INK")
    # a gable window, windows under the porch, and open doorways at porch level
    for x, y, w, h, lit in ((100, 269, 2, 2, True), (98, 283, 2, 3, True), (103, 283, 2, 3, False),
                            (108, 287, 2, 3, True), (113, 287, 2, 3, True), (122, 291, 2, 3, True)):
        small_window(L, x, y, w, h, lit)
    # (L3's own door and the low windows at x 97 and 108 are left out: the spare wheel leans
    # in front of them, and their lamplight would only show as scraps round its rim)
    for x, h, w in ((112, 8, 3), (120, 6, 2)):
        b = base_l(x + 1)
        doorway(L, x, b - h, b - 1, w)


def second_left(L):
    """L2: two storeys with a balcony, a porch whose roof runs on over the far row, lantern LB."""
    for x in range(48, 97):
        top = ry(TOP2, x)
        roof = ry(ROOF2, x)
        for y in range(top, base_l(x) + 1):
            if y == top:
                c = "RIM"
            elif y == top + 1:
                c = "OCHRE"
            elif y < roof:
                k, seam = siding(y, fy(TOP2, x) + 2, fy(ROOF2, x), 40, step=4)
                c = "BROWN_BLACK" if seam else board(x, k)
                if x == 96:
                    c = "RIM"
                elif x == 95:
                    c = "OCHRE"
            else:
                c = "BROWN_BLACK"
            put(L, x, y, c)
    # upper windows, dark, sheared along the top line, one catching a streak of sky
    for wx0, wx1 in ((55, 61), (70, 75)):
        for x in range(wx0, wx1 + 1):
            t = ry(TOP2, x) + 3
            for k in range(10):
                if x in (wx0, wx1) or k in (0, 9):
                    c = "BROWN"
                elif k == 5 or x == (wx0 + wx1) // 2:
                    c = "BROWN_BLACK"
                else:
                    c = "SHADOW" if k < 5 else "CHARCOAL"
                put(L, x, t + k, c)
            put(L, x, t + 10, "LEATHER")
        for k in range(3):
            put(L, wx0 + 1 + k, ry(TOP2, wx0 + 1 + k) + 3 + 3 - k, "RUST")
    # balcony rail with balusters
    for x in range(48, 96):                            # a covered gallery down to the porch roof
        r = ry(RAIL2, x)
        floor = ry(ROOF2, x) - 3
        put(L, x, r, "OCHRE")
        for y in range(r + 1, floor):
            if y <= r + 7:
                c = "BROWN_DARK" if x % 3 == 0 else "BROWN_BLACK"
            else:
                c = "BROWN_BLACK" if (x % 9 != 0) else "BROWN"
            put(L, x, y, c)
        put(L, x, r + 7, "BROWN")
        put(L, x, floor, "BROWN")
        put(L, x, floor + 1, "BROWN_DARK")
        put(L, x, floor + 2, "BROWN_BLACK")
    # the boardwalk deck in front of L2..L5
    for x in range(48, 125):
        with (far() if x > 96 else contextlib.nullcontext()):
            for y in range(base_l(x) + 1, walk_l(x) + 1):
                put(L, x, y, "OCHRE" if y == walk_l(x) else ("BROWN" if (y + x // 4) % 3 == 0 else "BROWN_DARK"))
            put(L, x, walk_l(x) + 1, "BROWN_BLACK")
            put(L, x, walk_l(x) + 2, "BROWN_BLACK")
    # lower windows under the porch
    lit_window(L, 54, 258, 62, 284, mull_x=(58,), mull_y=(270,))
    lit_window(L, 76, 280, 82, 296, mull_x=(79,), mull_y=(288,))
    lit_window(L, 89, 284, 92, 298, mull_y=(291,))                # 2 px clear of post 95
    # porch roof: rim, ochre, dark edge
    band(L, ROOF2, 50, 97, ["RIM", "OCHRE", "BROWN_DARK", "BROWN_BLACK"])
    with far():
        for x in range(98, 125):                       # the far row's own roofs, one each
            if x in (106, 116):
                continue
            y = far_row_roof(x)
            put(L, x, y, "RIM")
            put(L, x, y + 1, "OCHRE" if x < 106 else "BROWN_DARK")
            put(L, x, y + 2, "BROWN_BLACK")
        # no posts of their own: at 100 and 110 they would stand on the spare wheel's crown or
        # graze its rim, and the telegraph pole at 118 stands where the last one would be
    # none at 74 (lantern LB hangs alone there) and none by the hat brim's tip: the second post
    # stands at L2's corner, where the roof steps down to the far row, and the wheel leans on it
    for x in (60, 95):
        post(L, x, ry(ROOF2, x + 1) + 4, walk_l(x), 2, 1, hot=False)
    # lantern LB hanging from the porch roof
    lamp_glow(L, 76, 281, 0.7)
    vband(L, 76, ry(ROOF2, 76) + 4, 271, "CHARCOAL")
    hanging_lantern(L, 73, 272, 79, 290, 275, 287, core=(76, 77, 278, 284))


def saloon(L):
    # upper storey: horizontal siding that fans between the roof line and the balcony beam
    for x in range(X0, 32):
        top = ry(ROOF, x)
        for y in range(top, ry(BEAM, x)):
            if y == top:
                c = "RIM"
            elif y == top + 1:
                c = "OCHRE"
            elif y == top + 2:
                c = "BROWN_DARK"
            elif y == top + 3:
                c = "BROWN_BLACK"
            else:
                k, seam = siding(y, fy(ROOF, x) + 4, fy(BEAM, x), 56, step=4)
                c = "BROWN_BLACK" if seam else board(x, k)
            put(L, x, y, c)
    # corner post with its cap
    for y in range(104, ry(BEAM, 31) + 1):
        for x, c in ((27, "BROWN_BLACK"), (28, "BROWN"), (29, "BROWN"), (30, "OCHRE"), (31, "RIM")):
            put(L, x, y, c)
    for y in range(99, 106):
        for x in range(28, 33):
            c = "BROWN" if x < 31 else ("OCHRE" if x == 31 else "RIM")
            if x == 28:
                c = "BROWN_DARK"
            if y == 99:
                c = "RIM"
            elif y == 105:
                c = "BROWN_BLACK"
            put(L, x, y, c)
    # the upper window: dark panes with a warm reflection
    wt, wb = ((5, 111), (20, 119)), ((5, 139), (20, 146))
    for x in range(5, 21):
        t, b = ry(wt, x), ry(wb, x)
        m1, m2 = t + (b - t) // 3, t + 2 * (b - t) // 3
        for y in range(t, b + 1):
            if x in (5, 20) or y in (t, b):
                c = "BROWN"
            elif x == 12 or y in (m1, m2):
                c = "BROWN_DARK"
            else:
                c = "SHADOW" if y < m1 else "CHARCOAL"
            put(L, x, y, c)
        put(L, x, t - 1, "BROWN_BLACK")
        put(L, x, b + 1, "LEATHER")
        put(L, x, b + 2, "BROWN_BLACK")
    for x in (4, 21):
        put(L, x, ry(wb, x) + 1, "LEATHER")
        put(L, x, ry(wb, x) + 2, "BROWN_BLACK")
    for k in range(4):                                # one warm reflection streak
        put(L, 14 + k, ry(wt, 14 + k) + 6 - k, "RUST")
    # stovepipes against the sky, behind the beam
    for xa, xb, ya in ((33, 38, 150), (43, 48, 158)):
        for y in range(ya, ry(BEAM, xb) + 1):
            for x in range(xa, xb + 1):
                put(L, x, y, "RIM" if x == xb else ("OCHRE" if x == xb - 1 and y > ya + 2 else "CHARCOAL"))
        hband(L, xa - 1, xb + 1, ya, "INK")
        hband(L, xa - 1, xb + 1, ya + 1, "CHARCOAL")
        put(L, xb + 1, ya + 1, "RIM")
        hband(L, xa, xb - 1, ya + 6, "INK")
    # lower storey
    for x in range(X0, 51):
        bt = ry(BEAM, x) + 4
        pb = ry(PBEAM, x)
        for y in range(bt, base_l(x) + 1):
            if y < pb:
                k, seam = siding(y, fy(BEAM, x) + 4, fy(PBEAM, x), 74)
                c = "BROWN_BLACK" if seam else board(x, k)
                if x == 50:
                    c = "RIM"
                elif x == 49:
                    c = "OCHRE"
            else:
                # under the porch: shaded boards fanning from the porch beam down to the base
                # line, so the seams run to the vanishing point; each seam is a faint lit lip
                # broken at staggered butt joints
                k, seam = siding(y, fy(PBEAM, x) + 4, 296 + 0.227 * (140 - x), 96, step=4)
                c = "BROWN_DARK" if seam and (x + k * 13) % 23 > 1 else "BROWN_BLACK"
            put(L, x, y, c)
    for x in range(X0, 48):                           # the boardwalk, carried on from L2's
        for y in range(base_l(x) + 1, walk_l(x) + 1):
            put(L, x, y, "OCHRE" if y == walk_l(x) else ("BROWN" if (y + x // 4) % 3 == 0 else "BROWN_DARK"))
        put(L, x, walk_l(x) + 1, "BROWN_BLACK")
        put(L, x, walk_l(x) + 2, "BROWN_BLACK")
    # balcony beam and rafter ends
    band(L, BEAM, X0, 60, ["RIM", "OCHRE", "BROWN", "BROWN_BLACK"])
    knob = ((".RRR", "DBBO", "DBBO", ".KKD"))           # log ends under the beam, lit top and right
    cols = {"R": "RIM", "O": "OCHRE", "B": "BROWN", "D": "BROWN_DARK", "K": "BROWN_BLACK"}
    for x in range(X0 + 3, 56, 7):
        y = ry(BEAM, x + 2) + 4
        for dy, row in enumerate(knob):
            for dx, ch in enumerate(row):
                if ch in cols:
                    put(L, x + dx, y + dy, cols[ch])
    saloon_sign(L)
    # porch beam and posts
    band(L, PBEAM, X0, 48, ["RIM", "OCHRE", "BROWN_DARK"])
    band(L, PBEAM, X0, 48, [None, None, None, "BROWN_BLACK"])
    for x, hot in ((28, False), (46, True)):
        post(L, x, ry(PBEAM, x + 3) + 3, walk_l(x + 2), 4, 1, hot)
    # lit windows and the lantern
    lit_window(L, 13, 246, 23, 290, mull_x=(18,), mull_y=(257, 268, 279))
    lit_window(L, 34, 253, 42, 285, mull_x=(38,), mull_y=(263, 274))    # runs on behind the hat
    lamp_glow(L, 11.5, 250)
    vband(L, 12, ry(PBEAM, 12) + 3, 236, "CHARCOAL")
    put(L, 11, 235, "GREY_DARK")
    hanging_lantern(L, 6, 237, 17, 262, 241, 258, core=(10, 13, 245, 252), bars=(9, 14))


SIGN_X0, SIGN_X1, SIGN_TOP, SIGN_H, SIGN_CAP, SIGN_STEP = 5, 54, 180, 29, 13, 2

# hand-drawn 13-row capitals for the SALOON board: 2 px stems, 1 px steps on the curves
SIGN_GLYPHS = {
    "S": [".####.", "######", "##..##", "##....", "###...", ".####.", "..####",
          "...###", "....##", "....##", "##..##", "######", ".####."],
    "A": ["..##..", ".####.", ".####.", "##..##", "##..##", "##..##", "##..##",
          "######", "######", "##..##", "##..##", "##..##", "##..##"],
    "L": ["##...", "##...", "##...", "##...", "##...", "##...", "##...",
          "##...", "##...", "##...", "##...", "#####", "#####"],
    "O": [".####.", "######", "##..##", "##..##", "##..##", "##..##", "##..##",
          "##..##", "##..##", "##..##", "##..##", "######", ".####."],
    "N": ["###..##", "###..##", "###..##", "###..##", "####.##", "####.##", "####.##",
          "##.####", "##.####", "##.####", "##..###", "##..###", "##..###"],
}
SIGN_SHEAR = {"N": [0, 0, 1, 1, 2, 3, 3]}   # per-column drop where a stem is not on an even column


def saloon_sign(L):
    """The SALOON board: a parallelogram whose columns step down 1 px every 2 px, lettered in
    hand-drawn 13-row capitals sheared the same way, with an INK drop shadow."""
    def top(x):
        return SIGN_TOP + (x - SIGN_X0) // SIGN_STEP
    last = SIGN_H - 1
    for x in range(SIGN_X0, SIGN_X1 + 1):
        t = top(x)
        for r in range(SIGN_H):
            if x in (SIGN_X0, SIGN_X1) or r in (0, last):
                c = "INK"
            elif r == 1 or x == SIGN_X1 - 1:
                c = "OCHRE"
            elif r in (2, last - 2, last - 1) or x in (SIGN_X0 + 1, SIGN_X0 + 2, SIGN_X1 - 2):
                c = "LEATHER"
            elif r == 3 or x == SIGN_X0 + 3:
                c = "BROWN_BLACK"
            elif r in (10, 17) and (x + r) % 11 != 0:
                c = "BROWN"
            else:
                c = "BROWN_DARK"
            put(L, x, t + r, c)
    # letters sheared with the board, but a whole 2 px stem always steps together
    glyphs = [SIGN_GLYPHS[ch] for ch in "SALOON"]
    width = sum(len(g[0]) + 1 for g in glyphs) - 1
    pix = []
    x = (SIGN_X0 + SIGN_X1 + 1 - width) // 2
    for ch, g in zip("SALOON", glyphs):
        steps = SIGN_SHEAR.get(ch) or [gx // 2 for gx in range(len(g[0]))]
        base = top(x) + 7
        for gy, row in enumerate(g):
            for gx, c in enumerate(row):
                if c == "#":
                    pix.append((x + gx, base + steps[gx] + gy, gy))
        x += len(g[0]) + 1
    for x, y, gy in pix:
        put(L, x + 1, y + 1, "INK")
    for x, y, gy in pix:
        put(L, x, y, "CREAM_SHADE" if gy < 5 else ("TAN" if gy < SIGN_CAP - 3 else "OCHRE"))


# right side ---------------------------------------------------------------------------------
PROOF_R = ((226, 282), (158, 294))   # porch roof front edge of the mid right row
RBEAM = ((222, 243), (270, 221))     # near right porch roof


def base_r(x):
    return int(math.floor(296 + 0.227 * (x - 140) + 0.5))


def walk_r(x):
    return int(math.floor(296 + 0.61 * (x - 140) + 0.5))


RA_TOP = ((226, 249), (201, 257))
RC_TOP = ((182, 271), (168, 273))


def mid_right_row(L):
    """RA..RD: low buildings under the windmill with fronts of different heights and dark gaps
    between them, a porch roof running down towards the church, lit windows and a lantern."""
    fronts = (                 # name, x0, x1, top(x), wall, seam every n px (0: siding)
        ("RD", 160, 168, lambda x: 267, "BROWN_DARK", 3),
        ("RC", 170, 182, lambda x: ry(RC_TOP, x), "BROWN_BLACK", 4),
        ("RB", 184, 199, lambda x: 263, "BROWN_DARK", 3),
        ("RA", 201, 226, lambda x: ry(RA_TOP, x), "BROWN_DARK", 0),
    )
    for name, x0, x1, top, wall, seam in fronts:
        for x in range(x0, x1 + 1):
            t = top(x)
            roof = ry(PROOF_R, x)
            for y in range(t, base_r(x) + 1):
                if y == t:
                    c = "RIM_HOT" if name in ("RC", "RD") else "RIM"
                elif y == t + 1:
                    c = "OCHRE"
                elif y >= roof:
                    c = "BROWN_BLACK"
                elif seam == 0:
                    k, sm = siding(y, t + 2, fy(PROOF_R, x), 30)
                    c = "BROWN_BLACK" if sm else "BROWN_DARK"
                elif (x - x0) % seam == seam - 1 and y > t + 3:
                    c = "BROWN_BLACK" if wall == "BROWN_DARK" else "BROWN_DARK"
                else:
                    c = wall
                put(L, x, y, c)
        # the sun-facing (left) edge of each front, where it stands clear of its neighbour
        ya, yb = top(x0), (top(x0 - 2) if name != "RD" else 281)
        vband(L, x0, ya, yb, "RIM")
        vband(L, x0 + 1, ya + 1, yb, "OCHRE")
    # square false fronts: a cornice one pixel proud on each side, shadow under it
    for x0, x1, t in ((160, 168, 267), (184, 199, 263)):
        hband(L, x0 - 1, x1 + 1, t, "RIM_HOT" if x0 < 170 else "RIM")
        hband(L, x0 - 1, x1 + 1, t + 1, "BROWN")
        put(L, x0 - 1, t + 1, "OCHRE")
        hband(L, x0 + 2, x1, t + 2, "BROWN_BLACK")
        put(L, x0 - 1, t + 2, "INK")
        put(L, x1 + 1, t + 2, "INK")
    # dark gaps between the buildings
    for x, ya in ((169, 272), (183, 268), (200, 258)):
        vband(L, x, ya, base_r(x), "BROWN_BLACK")
    # RA balcony rail
    for x in range(201, 227):
        r = ry(((226, 272), (201, 279)), x)
        put(L, x, r, "OCHRE")
        put(L, x, r + 1, "BROWN_BLACK")
        if x % 3 == 0:
            vband(L, x, r + 2, r + 4, "BROWN_BLACK")
    # windows: upper storeys, then porch level
    lit_window(L, 205, 263, 209, 271)
    lit_window(L, 216, 260, 220, 269)
    # (none at porch level left of this one: the horse's head stands against dark wall there)
    lit_window(L, 214, 288, 220, 297, mull_x=(217,))
    lit_window(L, 187, 268, 190, 275)
    lit_window(L, 194, 268, 197, 275)
    for x, y, w, h, lit in ((172, 277, 2, 3, True), (176, 277, 2, 3, True), (179, 283, 2, 3, False),
                            (172, 284, 2, 3, True),
                            (172, 297, 2, 3, True), (176, 296, 3, 5, True), (180, 295, 2, 4, True),
                            (162, 272, 2, 3, True), (166, 272, 2, 3, False), (162, 280, 2, 3, True),
                            (166, 280, 2, 3, True), (162, 298, 2, 2, True), (166, 298, 2, 2, True)):
        small_window(L, x, y, w, h, lit)
    # boardwalk deck
    for x in range(158, 227):
        for y in range(base_r(x) + 1, walk_r(x) + 1):
            put(L, x, y, "OCHRE" if y == walk_r(x) else ("BROWN" if (y - x // 4) % 3 == 0 else "BROWN_DARK"))
        put(L, x, walk_r(x) + 1, "BROWN_BLACK")
        put(L, x, walk_r(x) + 2, "BROWN_BLACK")
    band(L, PROOF_R, 158, 226, ["RIM", "OCHRE", "BROWN_DARK", "BROWN_BLACK"])
    for x in (214, 182, 174, 167, 161):               # none by the horse's head (192, 203)
        w = 2 if x >= 190 else 1
        post(L, x, ry(PROOF_R, x) + 4, walk_r(x), w, -1)
    # a small lantern hanging from the porch roof on a short rod, clear of the horse's head
    # (in far() coordinates the roof band ends at y 292 here, the rod runs 293..294 and the
    # lantern's ring sits at 295; on screen that is 7 px lower, the lantern spanning y 302..312)
    lamp_glow(L, 187, 299, 0.45, clip=(158, 283, 226, 320))
    vband(L, 187, ry(PROOF_R, 187) + 4, 294, "CHARCOAL")
    hanging_lantern(L, 185, 296, 189, 304, 298, 302, core=(187, 187, 299, 301))


def near_right(L):
    """N1, the near right building, and its porch (N2) with lantern LC."""
    box(L, 229, 126, X1, 352, "BROWN_BLACK")
    # vertical boards down to the porch roof
    for x in range(238, X1 + 1):
        k, c0 = (x - 238) // 5, (x - 238) % 5
        for y in range(135, ry(RBEAM, x)):
            if c0 == 0:
                c = "INK"
            elif k % 5 == 3:
                c = "BROWN_BLACK"
            elif c0 == 1:
                c = "BROWN"
            else:
                c = "BROWN_DARK"
            if c0 == 1 and k % 5 != 3 and hsh(k, y // 6, 3) < 0.45:
                c = "BROWN_DARK"
            if c0 == 2 and k % 5 != 3 and hsh(k, y // 9, 4) < 0.12:
                c = "BROWN"
            put(L, x, y, c)
        if c0 == 3 and k % 5 != 3:
            for y in (140, 181, 216):
                put(L, x, y, "GREY_DARK")
                put(L, x, y + 1, "BROWN_BLACK")
    # cap beam and the post end above it
    for y, c in ((126, "RIM"), (127, "OCHRE"), (128, "BROWN"), (129, "BROWN"), (130, "BROWN"),
                 (131, "BROWN"), (132, "BROWN_DARK"), (133, "INK"), (134, "INK")):
        hband(L, 229, X1, y, c)
    vband(L, 229, 127, 132, "OCHRE")
    box(L, 230, 119, 237, 125, "BROWN_DARK")
    vband(L, 234, 121, 125, "BROWN")
    hband(L, 230, 237, 119, "RIM")
    vband(L, 230, 119, 125, "RIM")
    vband(L, 231, 120, 125, "OCHRE")
    vband(L, 237, 120, 125, "INK")
    # back wall of the porch
    for x in range(227, X1 + 1):
        for y in range(243, 346):
            put(L, x, y, "BROWN_DARK" if (x - 227) % 6 == 0 else "BROWN_BLACK")
    # corner post
    for y in range(135, 353):
        put(L, 230, y, "RIM" if y <= 243 else "OCHRE")
        put(L, 231, y, "OCHRE")
        for x in range(232, 237):
            put(L, x, y, "BROWN_DARK")
        put(L, 237, y, "INK")
    for k, y in enumerate(range(138, 350, 9)):
        vband(L, 232 + (k * 2) % 5, y, y + 3, "BROWN")
    # beam ends sticking out of the corner
    for xa, ya, xb, yb in ((223, 169, 237, 176), (226, 183, 237, 188)):
        box(L, xa, ya, xb, yb, "BROWN")
        hband(L, xa, xb, ya, "RIM")
        hband(L, xa, xb, yb, "BROWN_BLACK")
        vband(L, xa, ya + 1, yb - 1, "OCHRE")
        for y in range(ya + 1, yb):
            for x in (xa + 1, xa + 2, xa + 3):
                ring = y in (ya + 1, yb - 1) or x in (xa + 1, xa + 3)
                put(L, x, y, "BROWN_DARK" if ring else "LEATHER")
        put(L, xb - 1, ya + 2, "BROWN_DARK")
        put(L, xb - 4, yb - 2, "BROWN_DARK")
    # porch post P1
    for y in range(243, 353):
        put(L, 222, y, "RIM" if y <= 300 else "OCHRE")
        for x in (223, 224, 225):
            put(L, x, y, "BROWN")
        put(L, 226, y, "BROWN_BLACK")
    for y in range(252, 350, 11):
        vband(L, 224, y, y + 2, "BROWN_DARK")
    # lit window on the back wall
    lit_window(L, 257, 262, 267, 302, mull_x=(262,), mull_y=(275, 289))
    # porch roof beam over everything, running up into the overscan
    band(L, RBEAM, 222, X1, ["RIM", "OCHRE", "BROWN", "BROWN_BLACK"])
    vband(L, 222, 244, 246, "OCHRE")
    # boardwalk front
    for x in range(214, X1 + 1):
        put(L, x, 346, "OCHRE")
        for y in range(347, 352):
            put(L, x, y, "BROWN_DARK" if (x - 214) % 6 == 5 else "BROWN")
        put(L, x, 352, "BROWN_BLACK")
        for y in (353, 354):
            if dith(x + OX, y + OY, 0.5):
                put(L, x, y, "BROWN_BLACK")
    # lantern LC on its bracket
    warm(L, 247, 270, 16, 30, clip=(222, 222, X1, 345))
    lamp_glow(L, 247, 270, clip=(222, 222, X1, 345))
    hband(L, 238, 247, 245, "CHARCOAL")
    put(L, 239, 246, "CHARCOAL")
    vband(L, 247, 246, 253, "CHARCOAL")
    hanging_lantern(L, 239, 254, 254, 286, 259, 282, core=(244, 249, 263, 277), bars=(243, 250))
    for y in range(254, 259):
        put(L, 239, y, "INK")
        put(L, 254, y, "INK")


def wagon_wheel(L, cx, cy, r):
    """A spare wheel leaning on the boardwalk front. Its own shadow on the boards behind it
    fills the wheel with plain BROWN_BLACK, so nothing lit shows between the spokes; ten
    LEATHER spokes catch the lamplight, the felloe is BROWN inside a lit outer edge (RIM on
    the upper right towards the sun, OCHRE round the top and sides, BROWN_DARK underneath),
    and the hub is a small lit boss round an INK axle."""
    for y in range(cy - r - 1, cy + r + 2):
        for x in range(cx - r - 1, cx + r + 2):
            if math.hypot(x - cx, y - cy) < r - 1.5:
                put(L, x, y, "BROWN_BLACK")
    for k in range(10):                                # one spoke straight up, none level
        a = k * math.pi / 5 + math.pi / 10
        for t in range(3, r - 1):
            put(L, int(round(cx + t * math.cos(a))), int(round(cy + t * math.sin(a))), "LEATHER")
    for y in range(cy - r - 1, cy + r + 2):
        for x in range(cx - r - 1, cx + r + 2):
            d = math.hypot(x - cx, y - cy)
            if r - 1.5 <= d < r + 0.5:
                a = math.degrees(math.atan2(y - cy, x - cx)) % 360
                if d < r - 0.5:
                    c = "BROWN"
                elif 250 <= a <= 340:
                    c = "RIM"
                elif a >= 160 or a <= 20:
                    c = "OCHRE"
                else:
                    c = "BROWN_DARK"
                put(L, x, y, c)
    for dy in (-2, -1, 0, 1, 2):                       # hub: a 5 px boss, lit top right
        for dx in (-2, -1, 0, 1, 2):
            if abs(dx) + abs(dy) > 3:
                continue
            c = "BROWN_MID"
            if abs(dx) == 2 or abs(dy) == 2 or abs(dx) + abs(dy) == 3:
                c = "OCHRE" if dx - dy > 0 else "BROWN_DARK"
            put(L, cx + dx, cy + dy, c)
    put(L, cx, cy, "INK")


def wagon(L):
    """One big spare wheel leaning on the boardwalk, clear of the hat brim; PLAY covers its foot."""
    wagon_wheel(L, 100, 313, 10)


def draw_town_back(L, rng):
    """Things that stand above the street's horizon: the small water tower."""
    with far():
        water_tower(L)


def draw_town_front(L, rng):
    """Everything that stands on the street, back to front."""
    del WINDOWS[:]
    with far():
        church(L)
        far_left_row(L)
    windmill(L)
    with far():
        mid_right_row(L)
        telegraph_pole(L, 172, 266, 307, 269)
        telegraph_pole(L, 118, 266, 305, 269)
    second_left(L)
    saloon(L)
    near_right(L)
    wagon(L)
