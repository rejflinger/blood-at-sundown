"""The Sundown street at dusk: sky, mesas, town, props and the player seen from behind.

Drawn at native resolution into layers the size of the world canvas (the 195 x 422 safe area
plus OVERSCAN on every side). Everything is palette colours, hard edges and whole pixels.

The street is a real little perspective scene: facades, porches, boardwalks, ground detail
and the windmill are placed in metres and projected with one camera, so every line runs to
the same vanishing point. Coordinates in this file are safe-area pixels unless noted.
"""
import math
import random

import numpy as np
from PIL import Image, ImageDraw

import gen_fonts
import palette as P

SAFE_W, SAFE_H = 195, 422
OX, OY = 100, 60                      # overscan (matches WorldBuilder.OVERSCAN)
W, H = SAFE_W + 2 * OX, SAFE_H + 2 * OY

# camera: vanishing point, focal length in px per metre at z = 1, eye height in metres
CX, HY, F, EYE = 101, 214, 100.0, 1.7
BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]])


def col(name):
    return P.rgb(name, 0.0) + (255,)


class Layer:
    def __init__(self):
        self.im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    def px(self, x, y, c):
        x, y = int(x) + OX, int(y) + OY
        if 0 <= x < W and 0 <= y < H:
            self.im.putpixel((x, y), col(c) if isinstance(c, str) else c)

    def get(self, x, y):
        x, y = int(x) + OX, int(y) + OY
        if 0 <= x < W and 0 <= y < H:
            return self.im.getpixel((x, y))
        return (0, 0, 0, 0)

    def rect(self, x0, y0, x1, y1, c):
        self.d.rectangle((x0 + OX, y0 + OY, x1 + OX, y1 + OY), fill=col(c))

    def poly(self, pts, c):
        self.d.polygon([(round(x) + OX, round(y) + OY) for x, y in pts], fill=col(c))

    def line(self, pts, c, w=1):
        self.d.line([(round(x) + OX, round(y) + OY) for x, y in pts], fill=col(c), width=w)

    def ellipse(self, x0, y0, x1, y1, c):
        self.d.ellipse((x0 + OX, y0 + OY, x1 + OX, y1 + OY), fill=col(c))

    def hline(self, x0, x1, y, c):
        for x in range(int(x0), int(x1) + 1):
            self.px(x, y, c)

    def vline(self, x, y0, y1, c):
        for y in range(int(y0), int(y1) + 1):
            self.px(x, y, c)

    def outline(self, c="INK", diag=True, only_below=None):
        a = np.array(self.im)[:, :, 3] > 0
        o = np.zeros_like(a)
        shifts = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        if diag:
            shifts += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        for dy, dx in shifts:
            o |= np.roll(np.roll(a, dy, 0), dx, 1)
        o &= ~a
        ys, xs = np.nonzero(o)
        for y, x in zip(ys, xs):
            if only_below is None or y - OY >= only_below:
                self.im.putpixel((int(x), int(y)), col(c))

    def save(self, path):
        self.im.save(path)


def dith(x, y, level):
    return (BAYER4[y % 4, x % 4] + 0.5) / 16.0 < level


def proj(X, Y, z):
    return CX + F * X / z, HY - F * (Y - EYE) / z


def hsh(*v):
    h = 2166136261
    for n in v:
        h = ((h ^ (int(n) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    return h / 0xFFFFFFFF


# ----------------------------------------------------------------------------------------
# sky

def draw_sky(rng):
    L = Layer()
    bands = [("SKY_TOP", -OY), ("SKY_HIGH", 36), ("SKY_MID", 92), ("SKY_LOW", 156), ("HORIZON", 188)]
    for i, (name, y0) in enumerate(bands):
        y1 = bands[i + 1][1] if i + 1 < len(bands) else SAFE_H + OY
        L.rect(-OX, y0, SAFE_W + OX, y1, name)
    # streaky seams: each band frays into its neighbours as thin horizontal cloud strips
    for i in range(1, len(bands)):
        up, b = bands[i - 1][0], bands[i][1]
        low = bands[i][0]
        for _ in range(26):
            y = b + rng.randint(-12, 9)
            x = rng.randint(-OX, SAFE_W + OX)
            ln = rng.randint(10, 70)
            c = low if y < b else up
            th = 1 if rng.random() < 0.7 else 2
            for t in range(th):
                L.hline(x + t * 2, x + ln - t * 3, y + t, c)
    # sun, then long dark clouds with lit bellies over it and across the upper sky
    sx, sy, sr = 112, 160, 20
    L.ellipse(sx - sr, sy - sr, sx + sr, sy + sr, "SUN")
    for y, x0, x1 in ((166, 84, 150), (171, 94, 131), (175, 70, 118)):
        L.hline(x0, x1, y, "SKY_LOW")
        L.hline(x0 + 6, x1 - 8, y + 1, "HORIZON")
    for _ in range(9):
        y = rng.randint(22, 128)
        x = rng.randint(-OX, SAFE_W)
        ln = rng.randint(40, 120)
        th = rng.randint(2, 4)
        body = "PLUM" if y < 70 else "SKY_HIGH"
        belly = "SKY_MID" if y < 70 else "SKY_LOW"
        for k in range(ln):
            t = k / ln
            h = max(1, round(th * math.sin(math.pi * t)))
            for j in range(h):
                L.px(x + k, y - j, body)
            L.px(x + k, y + 1, belly)
    return L


# ----------------------------------------------------------------------------------------
# mesas and far hills

MESAS = [
    # (silhouette, x of the face lit by the sun)
    ([(-80, 214), (-66, 180), (-50, 176), (-40, 186), (-12, 190), (6, 172), (10, 162), (28, 161), (32, 172), (46, 214)], 30),
    ([(30, 214), (42, 200), (50, 192), (56, 180), (60, 166), (64, 158), (88, 156), (92, 164), (96, 178), (103, 194), (112, 214)], 92),
    ([(118, 214), (123, 196), (127, 176), (130, 160), (134, 154), (152, 153), (155, 164), (160, 182), (172, 198), (190, 214)], 132),
    ([(168, 214), (174, 176), (178, 166), (198, 164), (202, 178), (232, 186), (262, 214)], 176),
]


def draw_mesas(rng):
    L = Layer()
    # distant hills in haze
    for x in range(-OX, SAFE_W + OX):
        top = 204 + round(3 * math.sin(x / 13.0) + 2 * math.sin(x / 5.3 + 1))
        for y in range(top, HY + 2):
            L.px(x, y, "SKY_HIGH" if y < top + 3 and dith(x + OX, y, 0.6) else "PLUM_LIGHT")
    for pts, lit_x in MESAS:
        M = Layer()
        M.poly(pts, "SKY_HIGH")
        a = np.array(M.im)[:, :, 3] > 0
        xs = [p[0] for p in pts]
        for x in range(min(xs), max(xs) + 1):
            X = x + OX
            if not (0 <= X < W):
                continue
            ys = np.nonzero(a[:, X])[0]
            if len(ys) == 0:
                continue
            top = ys[0]
            for y in ys:
                sy = y - OY
                c = "SKY_HIGH"
                # the face toward the sun catches red light, the rest sinks into plum
                dist = abs(x - lit_x)
                toward = (x >= lit_x - 1) if lit_x < 112 else (x <= lit_x + 1)
                depth = (sy - top + OY)
                if toward and dist < 8 and dith(X, y, 0.95 - dist * 0.1 - depth * 0.01):
                    c = "SKY_MID"
                elif not toward and dith(X, y, 0.25 + depth * 0.012):
                    c = "PLUM_LIGHT"
                if sy > HY - 12 and dith(X, y, (sy - HY + 12) / 14):
                    c = "PLUM_LIGHT"
                M.im.putpixel((X, y), col(c))
            M.im.putpixel((X, top), col("SKY_LOW"))
            if hsh(x, 7) < 0.22:
                run = int(4 + hsh(x, 9) * 16)
                for y in range(top + 3, min(top + 3 + run, HY + OY)):
                    M.im.putpixel((X, y), col("PLUM"))
        L.im.alpha_composite(M.im)
    return L


# ----------------------------------------------------------------------------------------
# ground

def ground_colour(x, y):
    z = F * EYE / (y - HY)
    X = (x - CX) * z / F
    d = (y - HY) / (SAFE_H + OY - HY)
    street = abs(X) < 6.0
    v = 0.66 - 0.78 * d - 0.30 * min(1.0, (abs(X) / 6.0) ** 2)
    if not street:
        v -= 0.22
    # wagon ruts, only where they are wide enough to draw
    if z < 30:
        for rx in (-1.6, 1.5):
            dx = abs(X - rx)
            if dx < 0.13:
                v -= 0.28
            elif dx < 0.22 and X > rx:
                v += 0.08
    ramp = ["BROWN_DARK", "BROWN", "LEATHER", "OCHRE", "ORANGE", "DUST"]
    edges = [0.08, 0.26, 0.44, 0.62, 0.78]
    i = 0
    while i < len(edges) and v > edges[i]:
        i += 1
    # dither the last stretch of each band into the next one up
    if i < len(edges):
        lo = edges[i - 1] if i > 0 else edges[0] - 0.18
        f = (v - lo) / (edges[i] - lo)
        if f > 0.62 and dith(x + OX, y + OY, (f - 0.62) / 0.38 * 0.5):
            return ramp[i + 1]
    return ramp[i]


def draw_ground(L, rng):
    for y in range(HY + 1, SAFE_H + OY):
        for x in range(-OX, SAFE_W + OX):
            L.px(x, y, ground_colour(x, y))
    # foreground rocks and cracks, larger toward the camera
    for _ in range(46):
        y = rng.randint(262, SAFE_H + OY - 4)
        x = rng.randint(-OX, SAFE_W + OX)
        k = (y - 262) / 200
        if rng.random() < 0.55:
            r = 1 + int(k * 3 * rng.random())
            L.ellipse(x - r - 1, y - r, x + r + 1, y + r // 2, "BROWN")
            L.hline(x - r, x + r - 1, y - r, "TAN")
            L.hline(x - r, x + r + 1, y + r // 2 + 1, "BROWN_DARK")
        else:
            ln = 3 + int(k * 10)
            pts = [(x, y)]
            for i in range(3):
                pts.append((pts[-1][0] + rng.randint(1, ln), pts[-1][1] + rng.randint(-1, 1)))
            L.line(pts, "BROWN")
    # pebbles, hoof prints and scuffs placed in world metres so they shrink with distance
    cell = 0.45
    for iz in range(int(1.0 / cell), int(28 / cell)):
        for ix in range(int(-8 / cell), int(8 / cell)):
            h = hsh(ix, iz, 11)
            z = (iz + hsh(ix, iz, 2)) * cell
            X = (ix + hsh(ix, iz, 5)) * cell
            x, y = proj(X, 0, z)
            s = F / z
            if h < 0.05:     # pebble
                r = max(0, round(0.05 * s))
                for dx in range(-r, r + 1):
                    L.px(x + dx, y, "BROWN_DARK")
                L.px(x, y - 1, "TAN")
            elif h < 0.075 and abs(X) < 2.5:  # hoof print
                w = max(1, round(0.09 * s))
                L.hline(x - w, x + w, y, "BROWN")
                L.px(x - w, y - 1, "BROWN")
                L.px(x + w, y - 1, "BROWN")
            elif h < 0.10:   # boot scuff
                w = max(1, round(0.16 * s))
                L.hline(x, x + w, y, "LEATHER")
                L.hline(x + 1, x + w + 1, y + 1, "DUST")


# ----------------------------------------------------------------------------------------
# facades

LEFT = [  # (z0, z1, height, kind)
    (2.6, 16.0, 9.8, "saloon"), (16.6, 23.0, 6.0, "store"), (23.6, 30.0, 5.2, "hotel"),
    (30.6, 38.0, 4.5, "shack"), (38.6, 48.0, 5.0, "store"), (48.6, 62.0, 4.0, "shack"),
]
RIGHT = [
    (3.0, 10.5, 12.0, "bank"), (11.0, 17.0, 10.0, "hotel"), (17.6, 24.0, 7.0, "store"),
    (24.6, 32.0, 8.5, "sheriff"), (32.6, 42.0, 6.0, "shack"), (42.6, 60.0, 7.0, "barn"),
]
FACADE_X = 7.5


def window_at(kind, z, Y, z0):
    """Returns 'lit', 'dark', 'frame', 'bar' or None for a point on a facade."""
    u = z - z0
    rows = [(0.9, 2.7)]
    if kind in ("hotel", "bank"):
        rows.append((5.0, 7.2))
    elif kind == "saloon":
        rows.append((4.4, 6.0))
    for (y0, y1) in rows:
        if not (y0 - 0.15 <= Y <= y1 + 0.15):
            continue
        k = int(u // 3.0)
        cu = k * 3.0 + 1.5
        if abs(u - cu) > 0.95:
            continue
        if abs(u - cu) > 0.8 or Y < y0 or Y > y1:
            return "frame"
        lit = hsh(int(z0 * 10), k, int(y0)) < (0.9 if y0 < 3 else 0.55)
        if abs(u - cu) < 0.09 or abs(Y - (y0 + y1) / 2) < 0.09:
            return "bar"
        return "lit" if lit else "dark"
    return None


SIGN_TEXT = "SALOON"


def sign_pixel(z, Y):
    """The SALOON board on the saloon's false front."""
    z0, z1, y0, y1 = 8.0, 15.2, 6.6, 8.6
    if not (z0 <= z <= z1 and y0 <= Y <= y1):
        return None
    if z - z0 < 0.18 or z1 - z < 0.18 or Y - y0 < 0.18 or y1 - Y < 0.18:
        return "LEATHER"
    # letters: map (z, Y) onto the bold glyph grid
    rows = gen_fonts.BODY_ROWS - 2
    glyphs = [gen_fonts.embolden(gen_fonts.pad(gen_fonts.BODY[c], gen_fonts.BODY_ROWS)) for c in SIGN_TEXT]
    total = sum(len(g[0]) + 1 for g in glyphs) - 1
    u = (z - z0 - 0.45) / (z1 - z0 - 0.9) * total
    v = (y1 - 0.4 - Y) / (y1 - y0 - 0.8) * rows
    if 0 <= u < total and 0 <= v < rows:
        x = int(u)
        for g in glyphs:
            w = len(g[0])
            if x < w:
                return "TAN" if g[int(v)][x] == "#" else "BROWN_DARK"
            x -= w + 1
    return "BROWN_DARK"


def facade_pixel(side, seg, z, Y, zc_prev, zc_next, y_px_h):
    z0, z1, h, kind = seg
    wall = "BROWN" if side < 0 else "BROWN_DARK"
    siding = "BROWN_DARK" if side < 0 else "CHARCOAL"
    if kind == "saloon":
        s = sign_pixel(z, Y)
        if s:
            return s
    # cap and rim light along the top of the false front
    if h - Y < 0.3:
        return "RIM" if h - Y < y_px_h else "LEATHER"
    # the porch shades the ground floor
    under_porch = Y < 3.7 and kind in ("saloon", "store", "bank", "hotel")
    w = window_at(kind, z, Y, z0)
    if w == "lit":
        return "GOLD" if hsh(int(z * 4), int(Y * 4)) > 0.2 else "HORIZON"
    if w == "dark":
        return "CHARCOAL"
    if w in ("frame", "bar"):
        return "BROWN_DARK" if w == "bar" else "LEATHER"
    if kind == "saloon" and 12.2 <= z <= 13.6 and Y < 2.6:  # swinging doors
        if 0.5 < Y < 2.0:
            return "LEATHER" if int((z - 12.2) * 6) % 2 == 0 else "BROWN"
        return "GOLD"
    if kind == "barn" and Y < 4 and 46 < z < 52:
        return "BROWN_DARK"
    # siding lines where a board edge falls inside this pixel (skip when boards < 1 px)
    if y_px_h < 0.2 and int((Y + y_px_h) / 0.34) != int(Y / 0.34):
        return siding
    if side < 0 and y_px_h < 0.12 and int((Y + 2 * y_px_h) / 0.34) != int((Y + y_px_h) / 0.34):
        return "LEATHER"
    if zc_prev is not None and int(zc_prev / 2.4) != int(z / 2.4) and z < 20:
        return siding
    if under_porch:
        return "BROWN_DARK" if side < 0 else "CHARCOAL"
    if z > 34 and side < 0:
        return "BROWN_DARK"
    return wall


def draw_facades(L, side, segs):
    """side -1 = left of the street, +1 = right."""
    X = side * FACADE_X
    xs = range(-OX, SAFE_W + OX)
    prev_z = None
    for x in (xs if side < 0 else reversed(xs)):
        dx = x + 0.5 - CX
        if dx * side <= 0.5:
            prev_z = None
            continue
        z = F * X / dx
        seg = next((s for s in segs if s[0] <= z <= s[1]), None)
        if seg is None:
            prev_z = z
            continue
        top = HY - F * (seg[2] - EYE) / z
        bot = HY + F * EYE / z
        y_px_h = z / F
        for y in range(int(math.floor(top)), int(math.ceil(bot))):
            Y = EYE + (HY - (y + 0.5)) * z / F
            L.px(x, y, facade_pixel(side, seg, z, Y, prev_z, None, y_px_h))
        # vertical rim on the near corner of each building
        prev_z = z


def porch(L, side, z0, z1, posts):
    """Porch roof, posts and boardwalk in front of a facade."""
    Xw, Xp = side * FACADE_X, side * 5.6
    # boardwalk top and front
    L.poly([proj(Xw, 0.45, z0), proj(Xp, 0.45, z0), proj(Xp, 0.45, z1), proj(Xw, 0.45, z1)], "BROWN")
    L.poly([proj(Xp, 0.45, z0), proj(Xp, 0.0, z0), proj(Xp, 0.0, z1), proj(Xp, 0.45, z1)], "BROWN_DARK")
    for k in range(int(z0 * 3), int(z1 * 3)):  # plank seams
        z = k / 3.0
        if z < 9:
            a, b = proj(Xw, 0.45, z), proj(Xp, 0.45, z)
            L.line([a, b], "BROWN_DARK")
    # underside of the roof (in shadow), posts, beam, then the sloped roof top
    L.poly([proj(Xw, 3.6, z0), proj(Xp, 3.6, z0), proj(Xp, 3.6, z1), proj(Xw, 3.6, z1)], "CHARCOAL")
    for z in posts:
        if not (z0 <= z <= z1):
            continue
        x0, y0 = proj(Xp, 0.45, z)
        x1, y1 = proj(Xp, 3.6, z)
        w = max(1, round(F * 0.22 / z))
        L.rect(x0 - w // 2, y1, x0 - w // 2 + w - 1, y0, "LEATHER")
        L.vline(x0 - w // 2 + (w - 1 if side < 0 else 0), y1, y0, "RIM" if z < 12 else "OCHRE")
        L.vline(x0 - w // 2 + (0 if side < 0 else w - 1), y1, y0, "BROWN_DARK")
    L.poly([proj(Xp, 3.6, z0), proj(Xp, 3.95, z0), proj(Xp, 3.95, z1), proj(Xp, 3.6, z1)], "LEATHER")
    L.poly([proj(Xp, 3.95, z0), proj(Xw, 4.45, z0), proj(Xw, 4.45, z1), proj(Xp, 3.95, z1)], "BROWN")
    L.line([proj(Xp, 3.95, z0), proj(Xp, 3.95, z1)], "RIM")


# ----------------------------------------------------------------------------------------
# far town, church, windmill, water tower

def far_town(L, rng):
    # low buildings at the end of the street, backlit
    for X0, X1, z, h in ((-9, -3.2, 64, 5.0), (3.4, 8.0, 66, 6.0), (-16, -9.5, 70, 4.0), (8.5, 15, 72, 4.5)):
        x0, y0 = proj(X0, h, z)
        x1, y1 = proj(X1, 0, z)
        L.rect(x0, y0, x1, y1, "BROWN_DARK")
        L.hline(x0, x1, y0, "RIM")
        for k in range(int(x0) + 2, int(x1) - 1, 4):
            if hsh(k, z) < 0.5:
                L.px(k, (y0 + y1) // 2 + 1, "GOLD")
    # church, centred at the end of the street
    z = 74
    bx0, by0 = proj(-3.8, 5.5, z)
    bx1, by1 = proj(3.8, 0, z)
    L.rect(bx0, by0, bx1, by1, "BROWN_DARK")
    L.poly([(bx0 - 1, by0), (CX, by0 - 5), (bx1 + 1, by0)], "BROWN_DARK")
    L.line([(bx0 - 1, by0), (CX, by0 - 5)], "RIM")
    L.line([(CX, by0 - 5), (bx1 + 1, by0)], "RIM")
    tx0, ty0 = proj(-1.0, 14.0, z)
    tx1, ty1 = proj(1.0, 6.0, z)
    L.rect(tx0, ty0, tx1, ty1 + 3, "BROWN_DARK")
    L.poly([(tx0 - 1, ty0), (CX, ty0 - 5), (tx1 + 1, ty0)], "CHARCOAL")
    L.vline(CX, ty0 - 10, ty0 - 5, "CHARCOAL")
    L.hline(CX - 2, CX + 2, ty0 - 8, "CHARCOAL")
    L.vline(tx0, ty0, ty1 + 3, "RIM")
    L.px(CX, ty0 + 2, "GOLD")
    L.rect(CX - 1, by1 - 3, CX + 1, by1 - 1, "GOLD")
    L.px(bx0 + 2, by0 + 2, "GOLD")
    L.px(bx1 - 2, by0 + 2, "GOLD")


def water_tower(L):
    X, z = -12.5, 40.0
    x, yb = proj(X, 0, z)
    _, yt = proj(X, 11.0, z)
    _, ym = proj(X, 7.5, z)
    w = F * 3.4 / z
    for lx in (x - w / 2, x + w / 2 - 1):
        L.vline(round(lx), ym, yb, "CHARCOAL")
    L.line([(x - w / 2, yb), (x + w / 2, ym)], "CHARCOAL")
    L.line([(x + w / 2, yb), (x - w / 2, ym)], "CHARCOAL")
    L.rect(x - w / 2 - 1, yt, x + w / 2, ym, "BROWN_DARK")
    L.poly([(x - w / 2 - 2, yt), (x, yt - 3), (x + w / 2 + 1, yt)], "CHARCOAL")
    L.vline(round(x + w / 2), yt, ym, "RIM")
    L.hline(x - w / 2 - 1, x + w / 2, round((yt + ym) / 2), "CHARCOAL")


def windmill(L):
    X, z = 11.5, 24.0
    xb, yb = proj(X, 0, z)
    _, yt = proj(X, 17.5, z)
    wb = F * 3.0 / z
    wt = F * 0.8 / z
    lx0, lx1 = xb - wb / 2, xb + wb / 2
    tx0, tx1 = xb - wt / 2, xb + wt / 2
    L.line([(lx0, yb), (tx0, yt)], "CHARCOAL")
    L.line([(lx1, yb), (tx1, yt)], "CHARCOAL")
    L.line([(lx1 + 1, yb), (tx1 + 1, yt)], "RIM")
    # cross bracing
    n = 5
    for i in range(n):
        ya = yb + (yt - yb) * i / n
        yb2 = yb + (yt - yb) * (i + 1) / n
        fa = i / n
        fb = (i + 1) / n
        xa0, xa1 = lx0 + (tx0 - lx0) * fa, lx1 + (tx1 - lx1) * fa
        xb0, xb1 = lx0 + (tx0 - lx0) * fb, lx1 + (tx1 - lx1) * fb
        L.line([(xa0, ya), (xb1, yb2)], "CHARCOAL")
        L.line([(xa1, ya), (xb0, yb2)], "CHARCOAL")
        L.line([(xb0, yb2), (xb1, yb2)], "CHARCOAL")
    # platform, fan and tail vane
    cx, cy = xb, yt - 2
    L.rect(cx - 3, yt - 1, cx + 3, yt, "CHARCOAL")
    r = 9
    for k in range(16):
        a = k * math.pi * 2 / 16 + 0.1
        ex, ey = cx + r * math.cos(a), cy + r * math.sin(a)
        L.line([(cx, cy), (ex, ey)], "CHARCOAL")
        # blades: widen the outer half
        mx, my = cx + r * 0.55 * math.cos(a + 0.12), cy + r * 0.55 * math.sin(a + 0.12)
        L.line([(mx, my), (ex, ey)], "CHARCOAL")
    for k in range(64):
        a = k * math.pi * 2 / 64
        L.px(round(cx + r * math.cos(a)), round(cy + r * math.sin(a)), "CHARCOAL")
        L.px(round(cx + 4 * math.cos(a)), round(cy + 4 * math.sin(a)), "CHARCOAL")
    L.ellipse(cx - 1, cy - 1, cx + 1, cy + 1, "INK")
    L.line([(cx, cy), (cx + 11, cy - 1)], "CHARCOAL")
    L.poly([(cx + 8, cy - 5), (cx + 14, cy - 4), (cx + 14, cy + 2), (cx + 9, cy + 1)], "CHARCOAL")
    L.hline(cx + 9, cx + 13, cy - 4, "RIM")
    for k in range(40):  # rim light on the sun side of the wheel
        a = -1.2 + k * 0.06
        L.px(round(cx + r * math.cos(a)), round(cy + r * math.sin(a)), "RIM" if k % 3 else "CHARCOAL")


# ----------------------------------------------------------------------------------------
# sprites drawn as shapes: horses, wagon wheel, barrel, crate, post, skull, crow, lantern

def horse(L, ox, oy, s=1.0, facing=-1, coat="LEATHER", shade="BROWN", blanket=None):
    """A standing horse, 40 x 36 design units scaled by s (whole pixels, no resampling).
    ox, oy = top-left; facing -1 looks left."""
    S = Layer()
    wd = 40 * s

    def P_(x, y):
        return (ox + (x * s if facing < 0 else wd - x * s), oy + y * s)

    def poly(pts, c):
        S.poly([P_(x, y) for x, y in pts], c)

    def dot(x, y, c):
        S.px(round(P_(x, y)[0]), round(P_(x, y)[1]), c)

    for x0, x1 in ((13, 15.2), (31, 33.2)):                               # far legs
        poly([(x0, 20), (x1, 20), (x1, 35), (x0, 35)], shade)
    poly([(9, 17), (14, 10), (27, 9), (34, 10), (38, 14), (37, 22), (31, 25), (14, 25), (9, 22)], coat)
    poly([(9, 18), (14, 11), (11, 4), (8, 2), (6, 5), (8, 13)], coat)     # neck
    poly([(8, 2), (4, 1), (0, 7), (0, 12), (3, 13), (5, 10), (7, 6)], coat)  # head
    poly([(6, 1), (7, -1), (8, 1)], coat)                                  # ear
    for x0, x1 in ((10, 12.2), (16, 18.2), (28, 30.2), (34, 36.2)):
        poly([(x0, 22), (x1, 22), (x1, 32), (x1 - 0.4, 35), (x0, 35)], coat)
    S.outline("INK")
    top_y = {}
    arr = np.array(S.im)
    for X in range(W):
        ys = np.nonzero(arr[:, X, 3])[0]
        if len(ys):
            top_y[X] = ys[0]
    cc = P.rgb(coat)
    for X, ty in top_y.items():
        ys = np.nonzero(arr[:, X, 3])[0]
        by = ys[-1]
        for Y in ys:
            if tuple(arr[Y, X, :3]) != cc:
                continue
            rel = (Y - (oy + 19 * s) - OY) / (6 * s)
            if rel > 0 and dith(X, Y, rel):
                S.im.putpixel((X, Y), col(shade))
            if Y == ty + 1 and (Y - OY) < oy + 12 * s:
                S.im.putpixel((X, Y), col("RIM"))
    for t in range(12):   # mane
        x, y = 12.5 - t * 0.45, 10 - t * 0.8
        dot(x, y, "BROWN_DARK")
        dot(x + 1, y + 0.5, "BROWN_DARK")
    dot(3, 5, "INK")
    dot(1, 11, "BROWN_DARK")
    for t in range(int(17 * s)):  # tail
        y = 12 * s + t
        x = 38 + t / (6 * s) * 1.0
        S.px(round(P_(x, 0)[0]), round(oy + y), "BROWN_DARK")
        S.px(round(P_(x + 1 / s, 0)[0]), round(oy + y), "INK")
    for x0 in (10, 16, 28, 34):
        for k in range(3):
            dot(x0 + k * 0.8, 35, "INK")
    if blanket:
        for y in range(9, 16):
            for x in np.arange(18, 27, 1 / s):
                dot(x, y, blanket if y > 9 else "RIM")
        for x in np.arange(18, 27, 1 / s):
            dot(x, 15.5, "WINE")
    L.im.alpha_composite(S.im)


def wagon_wheel(L, cx, cy, r):
    for k in range(8):
        a = k * math.pi / 4
        L.line([(cx, cy), (cx + r * math.cos(a), cy + r * math.sin(a))], "LEATHER")
    for k in range(48):
        a = k * math.pi * 2 / 48
        L.px(round(cx + r * math.cos(a)), round(cy + r * math.sin(a)), "BROWN_DARK")
        L.px(round(cx + (r - 1) * math.cos(a)), round(cy + (r - 1) * math.sin(a)), "LEATHER")
    L.px(cx, cy, "INK")


def barrel(L, x, y, w=14, h=18):
    L.rect(x + 1, y, x + w - 2, y + h - 1, "LEATHER")
    L.rect(x, y + 2, x + w - 1, y + h - 3, "LEATHER")
    for sx in range(x + 2, x + w - 1, 3):
        L.vline(sx, y + 1, y + h - 2, "BROWN")
    L.vline(x + w - 3, y + 2, y + h - 3, "RIM")
    L.vline(x + w - 4, y + 2, y + h - 3, "OCHRE")
    for hy in (y + 3, y + h - 5):
        L.hline(x, x + w - 1, hy, "CHARCOAL")
        L.hline(x + w - 4, x + w - 2, hy, "GREY")
    L.hline(x + 1, x + w - 2, y, "BROWN_DARK")
    L.hline(x + 2, x + w - 3, y + 1, "BROWN")


def lantern(L, x, y):
    L.vline(x + 2, y - 6, y - 1, "CHARCOAL")
    L.rect(x, y, x + 4, y + 1, "CHARCOAL")
    L.rect(x, y + 2, x + 4, y + 7, "GOLD")
    L.rect(x + 1, y + 3, x + 3, y + 6, "SUN")
    L.vline(x, y + 2, y + 7, "CHARCOAL")
    L.vline(x + 4, y + 2, y + 7, "CHARCOAL")
    L.rect(x, y + 8, x + 4, y + 8, "CHARCOAL")
    L.px(x + 2, y + 9, "CHARCOAL")


def cow_skull(L, x, y):
    rows = [
        "##...........##",
        ".##.........##.",
        "..###.....###..",
        "...#########...",
        "...#oo###oo#...",
        "....#o###o#....",
        ".....#####.....",
        ".....#####.....",
        "......###......",
        "......#n#......",
        "......###......",
    ]
    for ry, r in enumerate(rows):
        for rx, c in enumerate(r):
            if c == "#":
                L.px(x + rx, y + ry, "CREAM" if rx < 9 else "TAN")
            elif c in "on":
                L.px(x + rx, y + ry, "INK")
    L.px(x, y, "TAN")
    L.px(x + 14, y, "TAN")


def crow(L, x, y):
    rows = [
        "....###....",
        "...#####...",
        "..g#####...",
        "...######..",
        "...#######.",
        "....#######",
        "....######.",
        ".....####..",
        "......#.#..",
        "......#.#..",
    ]
    for ry, r in enumerate(rows):
        for rx, c in enumerate(r):
            if c == "#":
                L.px(x + rx, y + ry, "INK" if (rx + ry) % 5 else "CHARCOAL")
            elif c == "g":
                L.px(x + rx, y + ry, "GREY")
    L.px(x + 4, y + 1, "GOLD")
    L.hline(x + 5, x + 7, y, "SLATE")


def crate(L, x0, y0, x1, y1):
    L.rect(x0, y0, x1, y1, "BROWN_DARK")
    L.rect(x0, y0, x1, y0 + 5, "BROWN")
    L.hline(x0, x1, y0, "RIM")
    L.hline(x0, x1, y0 + 5, "BROWN_DARK")
    for x in range(x0 + 5, x1, 7):
        L.vline(x, y0 + 6, y1, "BROWN_DARK")
        L.vline(x + 1, y0 + 6, y1, "BROWN")
    L.vline(x0, y0, y1, "LEATHER")
    for y in range(y0 + 14, y1, 22):
        L.hline(x0, x1, y, "BROWN_DARK")
    # cross brace on the front face
    L.line([(x0 + 2, y0 + 8), (x1, y0 + 8 + (x1 - x0) * 2)], "BROWN", 2)
    L.line([(x0 + 3, y0 + 7), (x1 + 1, y0 + 7 + (x1 - x0) * 2)], "LEATHER")
    L.outline("INK")


def tufts(L, rng, x0, x1, y0, y1, n):
    for _ in range(n):
        x = rng.randint(x0, x1)
        y = rng.randint(y0, y1)
        h = rng.randint(3, 7)
        for k in range(-2, 3):
            top = y - h + abs(k) * 2
            L.line([(x, y), (x + k * 2, top)], "BROWN_DARK" if k % 2 else "BROWN")
        L.px(x, y - h, "OCHRE")


# ----------------------------------------------------------------------------------------
# the player from behind, title framing (lower left, about 215 px tall)

def draw_player(rng):
    L = Layer()
    # legs and trousers
    L.poly([(-30, 422), (-24, 348), (44, 348), (50, 422)], "CHARCOAL")
    L.poly([(8, 372), (14, 368), (18, 422), (6, 422)], "INK")
    for y in range(350, 422, 3):
        L.px(40 - (y - 350) // 8, y, "SLATE")
    # gun belt with cartridges
    L.poly([(-20, 334), (46, 330), (48, 342), (-20, 348)], "BROWN_DARK")
    for x in range(-18, 46, 3):
        yy = 333 + (x + 20) * -4 // 66 + 4
        L.vline(x, yy - 1, yy + 2, "GOLD")
        L.px(x, yy - 2, "OCHRE")
    # holster on the right hip with the revolver seated in it, grip up and back
    L.poly([(41, 340), (53, 337), (58, 390), (47, 394)], "LEATHER")
    L.line([(53, 338), (58, 389)], "RIM")
    L.line([(44, 346), (49, 390)], "BROWN")
    for y in range(346, 388, 4):
        L.px(51 + (y - 346) // 9, y, "TAN")
    L.poly([(42, 334), (54, 332), (55, 342), (43, 344)], "BROWN_DARK")        # holster mouth
    L.poly([(44, 322), (53, 320), (55, 336), (46, 338)], "SILVER")          # frame and cylinder
    L.hline(46, 53, 326, "GREY")
    L.hline(46, 53, 330, "GREY")
    L.vline(54, 321, 336, "GREY")
    L.poly([(38, 312), (45, 308), (49, 322), (42, 326)], "BROWN")           # wooden grip
    L.line([(40, 312), (44, 324)], "LEATHER")
    L.px(46, 318, "SILVER")                                                  # hammer
    L.px(47, 317, "SILVER")
    # right arm hanging down past the poncho
    L.poly([(46, 282), (60, 288), (66, 330), (58, 340), (48, 330)], "BROWN")
    L.poly([(52, 330), (64, 328), (68, 352), (56, 356)], "SKIN_DARK")
    L.poly([(54, 348), (68, 346), (70, 364), (58, 368)], "CHARCOAL")       # glove
    L.vline(65, 290, 330, "RIM")
    L.vline(66, 332, 350, "SKIN")
    # poncho: big teal blanket over the shoulders, shaded left, lit on the right
    pon = [(-30, 244), (-6, 236), (18, 232), (40, 236), (56, 246), (66, 272), (70, 300), (64, 318), (-30, 338)]
    L.poly(pon, "TEAL")
    arr = np.array(L.im)
    teal = P.rgb("TEAL")
    for y in range(230, 340):
        for x in range(-30, 72):
            X, Y = x + OX, y + OY
            if tuple(arr[Y, X, :3]) != teal or arr[Y, X, 3] == 0:
                continue
            fold = math.sin((x * 0.22) + (y - 230) * 0.05)
            if x < 6 and dith(X, Y, (6 - x) / 40):
                L.px(x, y, "TEAL_DARK")
            elif fold > 0.82 and y > 250:
                L.px(x, y, "TEAL_DARK")
            elif x > 44 and y < 290 and dith(X, Y, (x - 44) / 22):
                L.px(x, y, "TEAL_LIGHT")

    def hem(x):
        return 338 + (x + 30) * (318 - 338) // 100

    for x in range(-30, 70):
        h = hem(x)
        b = h - 13
        # mustard band with teal diamonds cut out of it
        for k in range(4):
            L.px(x, b + k, "GOLD")
        m = (x + 30) % 8
        if m in (3, 4):
            L.px(x, b + 1, "TEAL_DARK")
            L.px(x, b + 2, "TEAL_DARK")
        elif m in (2, 5):
            L.px(x, b + 1 + (1 if m == 2 else 0), "TEAL_DARK")
        L.px(x, b - 2, "CREAM" if x % 3 else "TEAL")
        L.px(x, b + 5, "TEAL_DARK")
        L.px(x, h - 3, "GOLD")
        L.px(x, h - 2, "TEAL_DARK")
        L.px(x, h - 1, "TEAL_DARK")
        # fringe, strands of uneven length
        if x % 2 == 0:
            ln = 4 + int(hsh(x, 5) * 5)
            L.vline(x, h, h + ln, "CREAM" if x % 4 else "TAN")
    for x in range(-28, 44):  # shoulder band
        y = 247 + (x + 28) // 9
        L.px(x, y, "GOLD")
        if (x // 3) % 2 == 0:
            L.px(x, y + 1, "GOLD")
        if x % 5 == 0:
            L.px(x, y - 2, "CREAM")
    L.line([(40, 236), (56, 246), (66, 272), (70, 298)], "RIM")
    # neck, curly hair, hat
    L.poly([(10, 228), (30, 228), (32, 238), (8, 238)], "SKIN_DARK")
    for (x, y) in [(8, 226), (12, 230), (16, 227), (20, 231), (24, 227), (28, 230), (32, 227), (34, 232), (6, 232), (10, 234)]:
        L.ellipse(x - 2, y - 2, x + 2, y + 2, "BROWN_DARK")
        L.px(x, y - 1, "BROWN")
    L.ellipse(-12, 214, 58, 228, "CHARCOAL")                               # brim
    L.hline(4, 56, 215, "RIM")
    L.ellipse(-10, 216, 56, 226, "INK")
    L.ellipse(-10, 215, 56, 224, "CHARCOAL")
    L.poly([(4, 218), (6, 200), (12, 194), (22, 197), (34, 194), (40, 200), (42, 218)], "CHARCOAL")  # crown
    L.poly([(5, 210), (41, 210), (42, 216), (4, 216)], "LEATHER")         # band
    L.hline(5, 41, 211, "OCHRE")
    L.line([(22, 197), (34, 194), (40, 200), (42, 216)], "RIM")
    L.line([(12, 196), (20, 199)], "BROWN_DARK")
    L.outline("INK")
    return L


# ----------------------------------------------------------------------------------------

def build(out_dir):
    rng = random.Random(1873)
    sky = draw_sky(rng)
    mesas = draw_mesas(rng)

    town = Layer()
    far_town(town, rng)
    water_tower(town)
    draw_ground(town, rng)
    windmill(town)
    draw_facades(town, -1, LEFT)
    draw_facades(town, 1, RIGHT)
    porch(town, -1, 2.6, 23.0, [3.4, 6.4, 9.4, 12.4, 15.4, 18.4, 21.4])
    porch(town, 1, 3.0, 17.0, [3.8, 6.8, 9.8, 12.8, 15.8])
    lx, ly = proj(5.4, 3.5, 7.0)
    lantern(town, round(lx) - 2, round(ly))
    wagon_wheel(town, 60, 226, 6)
    wagon_wheel(town, 52, 229, 7)
    town.rect(50, 219, 66, 223, "BROWN_DARK")
    town.hline(50, 66, 219, "RIM")
    horse(town, 136, 204, s=1.25, facing=-1, coat="BROWN", shade="BROWN_DARK")
    horse(town, 118, 208, s=1.35, facing=-1, coat="LEATHER", shade="BROWN", blanket="BLOOD")
    rx0, ry = proj(3.6, 1.0, 5.0)
    town.line([(128, 244), (196, 256)], "LEATHER", 2)
    town.line([(128, 243), (196, 255)], "RIM")
    for px_ in (130, 176):
        town.rect(px_, 243, px_ + 2, 262 + (px_ - 130) // 8, "BROWN")

    fg = Layer()
    # corner post of the near building with its roof beam, a skull nailed on, a crow on top
    fg.rect(177, 70, 184, 262, "BROWN")
    fg.vline(177, 70, 262, "RIM")
    fg.vline(178, 70, 262, "OCHRE")
    fg.vline(184, 70, 262, "BROWN_DARK")
    fg.rect(176, 90, 200, 96, "BROWN")
    fg.hline(176, 200, 90, "RIM")
    fg.hline(176, 200, 96, "BROWN_DARK")
    cow_skull(fg, 173, 122)
    crow(fg, 175, 60)
    barrel(fg, 168, 236, 16, 20)
    crate(fg, 174, 300, 205, 430)
    tufts(fg, rng, 118, 196, 392, 420, 9)
    tufts(fg, rng, 70, 120, 404, 421, 4)
    tufts(fg, rng, 150, 170, 262, 270, 3)
    fg.outline("INK", only_below=None)

    player = draw_player(rng)

    for name, layer in (("sky", sky), ("mesas", mesas), ("town", town), ("fg", fg), ("player_back", player)):
        layer.save("%s/%s.png" % (out_dir, name))
    comp = Image.new("RGBA", (W, H))
    for layer in (sky, mesas, town, fg, player):
        comp.alpha_composite(layer.im)
    return comp
