"""The Sundown street at dusk: sky, mesas, town, props and the player seen from behind.

Drawn at native resolution (270 x 584, DESIGN.md section 15) into layers the size of the world
canvas: the safe area plus OVERSCAN on every side. Everything is palette colours, hard edges and
whole pixels; glows and haze are dithered palette pixels, never blended.

The street is a small perspective scene: facades, porches, boardwalks, ground detail and the
windmill are placed in metres and projected with one camera, so every line runs to the same
vanishing point. Coordinates in this file are safe-area pixels unless noted.
"""
import math
import random

import numpy as np
from PIL import Image, ImageDraw

import gen_fonts
import palette as P

SAFE_W, SAFE_H = 270, 584
OX, OY = 140, 150                     # overscan (matches WorldBuilder.OVERSCAN)
W, H = SAFE_W + 2 * OX, SAFE_H + 2 * OY

# camera: vanishing point, focal length in px per metre at z = 1, eye height in metres
CX, HY, F, EYE = 140, 296, 138.0, 1.7
SUN = (155, 222, 27)                  # centre x, centre y, radius
BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]])


def col(name):
    return P.rgb(name, 0.0) + (255,)


class Layer:
    def __init__(self):
        self.im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    def px(self, x, y, c):
        x, y = int(round(x)) + OX, int(round(y)) + OY
        if 0 <= x < W and 0 <= y < H:
            self.im.putpixel((x, y), col(c) if isinstance(c, str) else c)

    def get(self, x, y):
        x, y = int(x) + OX, int(y) + OY
        if 0 <= x < W and 0 <= y < H:
            return self.im.getpixel((x, y))
        return (0, 0, 0, 0)

    def is_(self, x, y, name):
        p = self.get(x, y)
        return p[3] > 0 and p[:3] == P.rgb(name)

    def rect(self, x0, y0, x1, y1, c):
        self.d.rectangle((round(x0) + OX, round(y0) + OY, round(x1) + OX, round(y1) + OY), fill=col(c))

    def poly(self, pts, c):
        self.d.polygon([(round(x) + OX, round(y) + OY) for x, y in pts], fill=col(c))

    def line(self, pts, c, w=1):
        self.d.line([(round(x) + OX, round(y) + OY) for x, y in pts], fill=col(c), width=w)

    def ellipse(self, x0, y0, x1, y1, c):
        self.d.ellipse((round(x0) + OX, round(y0) + OY, round(x1) + OX, round(y1) + OY), fill=col(c))

    def hline(self, x0, x1, y, c):
        for x in range(int(round(x0)), int(round(x1)) + 1):
            self.px(x, y, c)

    def vline(self, x, y0, y1, c):
        for y in range(int(round(y0)), int(round(y1)) + 1):
            self.px(x, y, c)

    def recolour(self, x0, y0, x1, y1, fn):
        """fn(x, y, current_name_or_None) -> new name or None, over opaque pixels."""
        arr = np.array(self.im)
        rev = {P.rgb(n): n for n in P.NAMES}
        for y in range(int(y0), int(y1) + 1):
            for x in range(int(x0), int(x1) + 1):
                X, Y = x + OX, y + OY
                if not (0 <= X < W and 0 <= Y < H) or arr[Y, X, 3] == 0:
                    continue
                cur = rev.get(tuple(arr[Y, X, :3]))
                new = fn(x, y, cur)
                if new and new != cur:
                    self.im.putpixel((X, Y), col(new))

    def outline(self, c="INK", diag=True):
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
            self.im.putpixel((int(x), int(y)), col(c))

    def glow(self, cx, cy, r0, r1, c, density=0.55, over=None):
        """Dithered halo: pixels between r0 and r1 thin out with distance. Only paints over
        existing opaque pixels when `over` is True (light spilling onto a surface)."""
        for y in range(int(cy - r1), int(cy + r1) + 1):
            for x in range(int(cx - r1), int(cx + r1) + 1):
                d = math.hypot((x - cx), (y - cy) * 1.15)
                if r0 <= d <= r1:
                    lvl = density * (1.0 - (d - r0) / max(1.0, r1 - r0))
                    if dith(x + OX, y + OY, lvl):
                        if over and self.get(x, y)[3] == 0:
                            continue
                        self.px(x, y, c)

    def save(self, path):
        self.im.save(path)


def dith(x, y, level):
    return (BAYER4[int(y) % 4, int(x) % 4] + 0.5) / 16.0 < level


def proj(X, Y, z):
    return CX + F * X / z, HY - F * (Y - EYE) / z


def hsh(*v):
    h = 2166136261
    for n in v:
        h = ((h ^ (int(n) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    return h / 0xFFFFFFFF


# ----------------------------------------------------------------------------------------
# sky: eight dithered bands, streaky cloud strata, a banded sun with a stepped halo

SKY_BANDS = [("SKY_TOP", -OY), ("SKY_UPPER", 22), ("SKY_HIGH", 62), ("SKY_MID", 110),
             ("SKY_WARM", 158), ("SKY_LOW", 200), ("HORIZON", 236), ("HORIZON_HOT", 266)]


def draw_sky(rng):
    L = Layer()
    for i, (name, y0) in enumerate(SKY_BANDS):
        y1 = SKY_BANDS[i + 1][1] if i + 1 < len(SKY_BANDS) else SAFE_H + OY
        L.rect(-OX, y0, SAFE_W + OX, y1, name)
        if i > 0:  # dithered seam: the band above reaches down in thinning Bayer steps
            above = SKY_BANDS[i - 1][0]
            for k in range(6):
                for x in range(-OX, SAFE_W + OX):
                    if dith(x + OX, y0 + k + OY, 0.85 - k * 0.15):
                        L.px(x, y0 + k, above)
    # streaks fraying each seam
    for i in range(1, len(SKY_BANDS)):
        up, b = SKY_BANDS[i - 1][0], SKY_BANDS[i][1]
        low = SKY_BANDS[i][0]
        for _ in range(30):
            y = b + rng.randint(-14, 12)
            x = rng.randint(-OX, SAFE_W + OX)
            ln = rng.randint(14, 90)
            c = low if y < b else up
            L.hline(x, x + ln, y, c)
            if rng.random() < 0.35:
                L.hline(x + 3, x + ln - 5, y + 1, c)
    # sun: core, disc, stepped halo into the horizon glow
    sx, sy, sr = SUN
    L.glow(sx, sy, sr, sr + 16, "HORIZON_HOT", 0.6)
    L.glow(sx, sy, sr + 6, sr + 30, "HORIZON", 0.35)
    L.ellipse(sx - sr, sy - sr, sx + sr, sy + sr, "SUN")
    L.ellipse(sx - sr + 5, sy - sr + 5, sx + sr - 5, sy + sr - 5, "SUN_CORE")
    for k in range(3):  # dithered edge between core and disc
        r = sr - 5 + k
        for a in range(0, 360, 2):
            x = sx + r * math.cos(math.radians(a))
            y = sy + r * math.sin(math.radians(a))
            if dith(x + OX, y + OY, 0.6 - k * 0.2):
                L.px(x, y, "SUN_CORE")
    # thin strata crossing the lower sun
    for y, x0, x1 in ((sy + 6, sx - 46, sx + 58), (sy + 12, sx - 30, sx + 34), (sy + 17, sx - 70, sx + 20),
                      (sy + 22, sx - 20, sx + 70)):
        L.hline(x0, x1, y, "SKY_LOW")
        L.hline(x0 + 8, x1 - 10, y + 1, "HORIZON")
        L.hline(x0 + 16, x1 - 22, y - 1, "HORIZON_HOT")
    # cloud strata: dark bodies with lit bellies
    for _ in range(14):
        y = rng.randint(28, 185)
        x = rng.randint(-OX, SAFE_W + 20)
        ln = rng.randint(50, 170)
        th = rng.randint(2, 6)
        if y < 70:
            body, dark, belly = "SKY_TOP", "PLUM", "SKY_HIGH"
        elif y < 130:
            body, dark, belly = "SKY_UPPER", "PLUM", "SKY_WARM"
        else:
            body, dark, belly = "SKY_HIGH", "SKY_UPPER", "SKY_LOW"
        for k in range(ln):
            t = k / ln
            h = max(1, round(th * math.sin(math.pi * t) ** 0.7))
            for j in range(h):
                L.px(x + k, y - j, dark if j == h - 1 and h > 2 else body)
            if dith(x + k + OX, y + OY, 0.8):
                L.px(x + k, y + 1, belly)
            if h > 2 and dith(x + k + OX, y + 2 + OY, 0.3):
                L.px(x + k, y + 2, belly)
    return L


# ----------------------------------------------------------------------------------------
# mesas and far hills

MESAS = [
    # (silhouette, x of the face lit by the sun, far?)
    ([(-140, 296), (-110, 250), (-86, 244), (-70, 258), (-20, 262), (6, 240), (12, 226), (40, 224), (46, 238), (64, 296)], 42, True),
    ([(34, 296), (46, 282), (60, 276), (66, 268), (74, 262), (78, 246), (82, 232), (88, 222), (92, 218), (118, 216), (122, 222), (125, 236), (128, 250), (136, 256), (140, 268), (150, 282), (160, 296)], 124, False),
    ([(158, 296), (166, 280), (174, 272), (178, 256), (181, 238), (185, 224), (190, 216), (208, 214), (212, 222), (216, 240), (226, 256), (240, 262), (250, 276), (268, 296)], 181, False),
    ([(232, 296), (241, 244), (246, 230), (274, 228), (279, 246), (320, 258), (362, 296)], 241, True),
]


def draw_mesas(rng):
    L = Layer()
    # distant hills in haze, dithered into the sky
    for x in range(-OX, SAFE_W + OX):
        top = 282 + round(4 * math.sin(x / 18.0) + 3 * math.sin(x / 7.3 + 1))
        for y in range(top - 3, HY + 3):
            if y < top:
                if dith(x + OX, y + OY, 0.3 * (y - top + 4) / 4):
                    L.px(x, y, "HAZE")
            else:
                L.px(x, y, "HAZE" if y < top + 3 and dith(x + OX, y + OY, 0.6) else "MAUVE")
    for pts, lit_x, far in MESAS:
        M = Layer()
        M.poly(pts, "HAZE")
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
            toward = (x >= lit_x - 1) if lit_x < SUN[0] else (x <= lit_x + 1)
            dist = abs(x - lit_x)
            for y in ys:
                sy = y - OY
                depth = y - top
                c = "HAZE"
                if far and dith(X, y, 0.3):
                    c = "SKY_WARM"
                if toward and dist < 14 and dith(X, y, 1.0 - dist * 0.065 - depth * 0.005):
                    c = "MESA_LIT"
                elif not toward and not far and dith(X, y, 0.35 + depth * 0.008):
                    c = "MAUVE"
                # horizontal strata bands and ledges on the near buttes
                if not far and hsh(sy // 6, 3) < 0.3 and depth > 6:
                    if dith(X, y, 0.55):
                        c = "MAUVE" if c == "HAZE" else ("HAZE" if c == "MESA_LIT" else "PLUM_LIGHT")
                if sy > HY - 16 and dith(X, y, (sy - HY + 16) / 18):  # haze at the base
                    c = "HAZE"
                M.im.putpixel((X, y), col(c))
            M.im.putpixel((X, top), col("HORIZON" if toward else "SKY_LOW"))
            if len(ys) > 4:
                M.im.putpixel((X, top + 1), col("SKY_LOW" if toward else "MESA_LIT"))
            if not far and hsh(x, 7) < 0.2:  # erosion gullies
                run = int(6 + hsh(x, 9) * 26)
                for y in range(top + 4, min(top + 4 + run, HY + OY - 10)):
                    M.im.putpixel((X, y), col("MAUVE" if toward else "PLUM_LIGHT"))
        L.im.alpha_composite(M.im)
    # sparse pixel haze drifting over the mesa feet
    for _ in range(26):
        y = rng.randint(270, 292)
        x = rng.randint(-OX, SAFE_W + OX)
        for k in range(rng.randint(10, 40)):
            if dith(x + k + OX, y + OY, 0.5):
                L.px(x + k, y, "HAZE")
    return L


# ----------------------------------------------------------------------------------------
# ground

GROUND_RAMP = ["BROWN_BLACK", "BROWN_DARK", "BROWN", "BROWN_MID", "LEATHER", "RUST", "OCHRE", "AMBER", "DUST", "DUST_LIGHT"]


def ground_colour(x, y):
    z = F * EYE / (y - HY)
    X = (x - CX) * z / F
    d = (y - HY) / (SAFE_H + OY - HY)
    street = abs(X) < 6.0
    v = 0.74 - 0.86 * d - 0.30 * min(1.0, (abs(X) / 6.0) ** 2)
    # the sun lays a warm streak down the middle of the far street
    v += 0.12 * max(0.0, 1.0 - abs(X - 0.6) / 1.8) * max(0.0, 1.0 - d * 3.0)
    if not street:
        v -= 0.2
    if z < 34:  # wagon ruts, where they are wide enough to draw
        for rx in (-1.6, 1.5):
            dx = abs(X - rx)
            if dx < 0.12:
                v -= 0.24
            elif dx < 0.22 and X > rx:
                v += 0.07
    n = len(GROUND_RAMP)
    t = max(0.0, min(0.999, v)) * n
    i = int(t)
    f = t - i
    if f > 0.6 and i + 1 < n and dith(x + OX, y + OY, (f - 0.6) / 0.4 * 0.5):
        i += 1
    return GROUND_RAMP[i]


def draw_ground(L, rng):
    for y in range(HY + 1, SAFE_H + OY):
        for x in range(-OX, SAFE_W + OX):
            L.px(x, y, ground_colour(x, y))
    # pebbles, hoof prints and scuffs placed in metres so they shrink with distance
    cell = 0.4
    for iz in range(int(0.9 / cell), int(30 / cell)):
        for ix in range(int(-9 / cell), int(9 / cell)):
            h = hsh(ix, iz, 11)
            z = (iz + hsh(ix, iz, 2)) * cell
            X = (ix + hsh(ix, iz, 5)) * cell
            x, y = proj(X, 0, z)
            s = F / z
            if h < 0.045:     # pebble with a lit top
                r = max(0, round(0.06 * s))
                L.ellipse(x - r, y - max(0, r - 1), x + r, y, "BROWN_DARK")
                L.hline(x - r + 1, x + r - 1, y - max(0, r - 1) - (1 if r else 0), "TAN")
            elif h < 0.07 and abs(X) < 2.6:  # hoof print
                w = max(1, round(0.08 * s))
                L.hline(x - w, x + w, y, "BROWN_MID")
                L.px(x - w, y - 1, "BROWN")
                L.px(x + w, y - 1, "BROWN")
                L.hline(x - w + 1, x + w - 1, y + 1, "DUST")
            elif h < 0.095:   # boot scuff
                w = max(1, round(0.15 * s))
                L.hline(x, x + w, y, "LEATHER")
                L.hline(x + 1, x + w + 1, y + 1, "DUST")
    # foreground rocks and cracks, larger toward the camera
    for _ in range(130):
        y = rng.randint(362, SAFE_H + OY - 6)
        x = rng.randint(-OX, SAFE_W + OX)
        k = (y - 362) / 260
        if rng.random() < 0.55:
            r = 1 + int(k * 4 * rng.random())
            L.ellipse(x - r - 1, y - r, x + r + 1, y + r // 2, "BROWN")
            L.hline(x - r, x + r - 1, y - r, "TAN")
            L.hline(x - r + 1, x, y - r + 1, "OCHRE")
            L.hline(x - r, x + r + 1, y + r // 2 + 1, "BROWN_BLACK")
        else:
            ln = 3 + int(k * 12)
            pts = [(x, y)]
            for _i in range(3):
                pts.append((pts[-1][0] + rng.randint(1, ln), pts[-1][1] + rng.randint(-1, 1)))
            L.line(pts, "BROWN_DARK")
            L.line([(a + 1, b + 1) for a, b in pts], "LEATHER")


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
    """('lit' | 'dark' | 'frame' | 'bar' | 'sill' | 'glow', lit?) or None for a facade point."""
    u = z - z0
    rows = [(0.9, 2.7)]
    if kind in ("hotel", "bank"):
        rows.append((5.0, 7.2))
    elif kind == "saloon":
        rows.append((4.4, 6.0))
    for (y0, y1) in rows:
        k = int(u // 3.0)
        cu = k * 3.0 + 1.5
        lit = hsh(int(z0 * 10), k, int(y0)) < (0.9 if y0 < 3 else 0.55)
        du = abs(u - cu)
        if y0 - 0.15 <= Y <= y1 + 0.15 and du <= 0.95:
            if Y < y0 and Y >= y0 - 0.15:
                return ("sill", lit)
            if du > 0.8 or Y < y0 or Y > y1:
                return ("frame", lit)
            if du < 0.07 or abs(Y - (y0 + y1) / 2) < 0.07:
                return ("bar", lit)
            return ("lit" if lit else "dark", lit)
        # light spilling onto the wall around a lit window
        if lit and y0 - 0.7 <= Y <= y1 + 0.5 and du <= 1.5:
            return ("glow", True)
    return None


SIGN_TEXT = "SALOON"


def sign_pixel(z, Y):
    """The SALOON board on the saloon's false front."""
    z0, z1, y0, y1 = 8.0, 15.2, 6.6, 8.6
    if not (z0 <= z <= z1 and y0 <= Y <= y1):
        return None
    if z - z0 < 0.14 or z1 - z < 0.14 or Y - y0 < 0.14 or y1 - Y < 0.14:
        return "INK"
    if z - z0 < 0.3 or z1 - z < 0.3 or Y - y0 < 0.3 or y1 - Y < 0.3:
        return "LEATHER" if y1 - Y < 0.3 else "BROWN_MID"
    rows = gen_fonts.BODY_ROWS - 2
    glyphs = [gen_fonts.embolden(gen_fonts.pad(gen_fonts.BODY[c], gen_fonts.BODY_ROWS)) for c in SIGN_TEXT]
    total = sum(len(g[0]) + 1 for g in glyphs) - 1
    u = (z - z0 - 0.5) / (z1 - z0 - 1.0) * total
    v = (y1 - 0.45 - Y) / (y1 - y0 - 0.9) * rows
    if 0 <= u < total and 0 <= v < rows:
        x = int(u)
        for g in glyphs:
            w = len(g[0])
            if x < w:
                if g[int(v)][x] == "#":
                    return "SAND" if v < rows * 0.45 else "TAN"
                return "BROWN_DARK"
            x -= w + 1
    return "BROWN_DARK"


def facade_pixel(side, seg, z, Y, zc_prev, y_px_h, x, y):
    z0, z1, h, kind = seg
    far = z > 34
    wall = ("BROWN_MID" if side < 0 else "BROWN") if not far else ("BROWN_DARK" if side < 0 else "BROWN_DARK")
    siding = "BROWN" if side < 0 else "BROWN_DARK"
    if kind == "saloon":
        s = sign_pixel(z, Y)
        if s:
            return s
    if h - Y < 0.32:  # cap with a rim of sunset light
        return "RIM_HOT" if h - Y < y_px_h else ("RIM" if h - Y < 2 * y_px_h else "LEATHER")
    under_porch = Y < 3.7 and kind in ("saloon", "store", "bank", "hotel")
    w = window_at(kind, z, Y, z0)
    if w:
        what, lit = w
        if what == "lit":
            cy = Y - (0.9 if Y < 3 else 5.0)
            if hsh(int(z * 5), int(Y * 5)) < 0.12:
                return "AMBER"
            return "LAMP_HOT" if (cy < 0.5 and hsh(int(z * 3), 1) < 0.5) else "LAMP"
        if what == "dark":
            return "SHADOW" if hsh(int(z * 4), int(Y * 3)) < 0.2 else "CHARCOAL"
        if what == "bar":
            return "BROWN_DARK"
        if what == "frame":
            return "LEATHER" if not lit else "OCHRE"
        if what == "sill":
            return "TAN"
        if what == "glow" and dith(x + OX, y + OY, 0.28):
            return "RUST" if under_porch else "LEATHER"
    if kind == "saloon" and 12.2 <= z <= 13.6 and Y < 2.6:  # swinging doors, lit from inside
        if 0.5 < Y < 2.0:
            return "LEATHER" if int((z - 12.2) * 6) % 2 == 0 else "BROWN"
        return "LAMP"
    if kind == "barn" and Y < 4 and 46 < z < 52:
        return "BROWN_DARK"
    if y_px_h < 0.2 and int((Y + y_px_h) / 0.34) != int(Y / 0.34):
        return siding
    if y_px_h < 0.12 and int((Y + 2 * y_px_h) / 0.34) != int((Y + y_px_h) / 0.34):
        return "LEATHER" if side < 0 else "BROWN_MID"
    if zc_prev is not None and int(zc_prev / 2.4) != int(z / 2.4) and z < 22:
        return siding
    if under_porch:
        return "BROWN_DARK" if side < 0 else "BROWN_BLACK"
    # a few weathered boards
    if hsh(int(z * 2.5), int(Y / 0.34)) < 0.06 and not far:
        return "BROWN" if side < 0 else "SHADOW"
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
            L.px(x, y, facade_pixel(side, seg, z, Y, prev_z, y_px_h, x, y))
        prev_z = z


def porch(L, side, z0, z1, posts):
    """Porch roof, posts and boardwalk in front of a facade."""
    Xw, Xp = side * FACADE_X, side * 5.6
    L.poly([proj(Xw, 0.45, z0), proj(Xp, 0.45, z0), proj(Xp, 0.45, z1), proj(Xw, 0.45, z1)], "BROWN")
    L.poly([proj(Xp, 0.45, z0), proj(Xp, 0.0, z0), proj(Xp, 0.0, z1), proj(Xp, 0.45, z1)], "BROWN_DARK")
    L.line([proj(Xp, 0.45, z0), proj(Xp, 0.45, z1)], "OCHRE")
    for k in range(int(z0 * 3), int(z1 * 3)):  # plank seams
        z = k / 3.0
        if z < 11:
            L.line([proj(Xw, 0.45, z), proj(Xp, 0.45, z)], "BROWN_DARK")
    L.poly([proj(Xw, 3.6, z0), proj(Xp, 3.6, z0), proj(Xp, 3.6, z1), proj(Xw, 3.6, z1)], "CHARCOAL")
    for k in range(int(z0), int(z1)):  # rafters under the roof
        L.line([proj(Xw, 3.6, k + 0.5), proj(Xp, 3.6, k + 0.5)], "SHADOW")
    for z in posts:
        if not (z0 <= z <= z1):
            continue
        x0, y0 = proj(Xp, 0.45, z)
        x1, y1 = proj(Xp, 3.6, z)
        w = max(1, round(F * 0.22 / z))
        L.rect(x0 - w // 2, y1, x0 - w // 2 + w - 1, y0, "LEATHER")
        lit_edge = x0 - w // 2 + (w - 1 if side < 0 else 0)
        L.vline(lit_edge, y1, y0, "RIM" if z < 12 else "OCHRE")
        if w > 3:
            L.vline(lit_edge - side, y1, y0, "OCHRE")
        L.vline(x0 - w // 2 + (0 if side < 0 else w - 1), y1, y0, "BROWN_DARK")
    L.poly([proj(Xp, 3.6, z0), proj(Xp, 3.95, z0), proj(Xp, 3.95, z1), proj(Xp, 3.6, z1)], "LEATHER")
    L.poly([proj(Xp, 3.95, z0), proj(Xw, 4.45, z0), proj(Xw, 4.45, z1), proj(Xp, 3.95, z1)], "BROWN")
    for k in range(int(z0 * 2), int(z1 * 2)):  # roof shingles
        z = k / 2.0
        if z < 12:
            L.line([proj(Xp, 3.95, z), proj(Xw, 4.45, z)], "BROWN_DARK")
    L.line([proj(Xp, 3.95, z0), proj(Xp, 3.95, z1)], "RIM")


# ----------------------------------------------------------------------------------------
# far town, church, windmill, water tower

def far_town(L, rng):
    for X0, X1, z, h in ((-9, -3.2, 64, 5.0), (3.4, 8.0, 66, 6.0), (-16, -9.5, 70, 4.0), (8.5, 15, 72, 4.5),
                         (-22, -16.5, 76, 3.5), (15.5, 21, 78, 5.0)):
        x0, y0 = proj(X0, h, z)
        x1, y1 = proj(X1, 0, z)
        L.rect(x0, y0, x1, y1, "BROWN_DARK")
        L.hline(x0, x1, y0, "RIM")
        L.rect(x0, y1 - 2, x1, y1, "SHADOW")
        for k in range(int(x0) + 2, int(x1) - 1, 4):
            if hsh(k, z) < 0.55:
                L.px(k, (y0 + y1) // 2, "LAMP")
                L.px(k, (y0 + y1) // 2 + 1, "AMBER")
    z = 74  # church at the end of the street
    bx0, by0 = proj(-3.8, 5.5, z)
    bx1, by1 = proj(3.8, 0, z)
    L.rect(bx0, by0, bx1, by1, "BROWN_DARK")
    L.poly([(bx0 - 1, by0), (CX, by0 - 7), (bx1 + 1, by0)], "BROWN_DARK")
    L.line([(bx0 - 1, by0), (CX, by0 - 7)], "RIM")
    L.line([(CX, by0 - 7), (bx1 + 1, by0)], "RIM_HOT")
    tx0, ty0 = proj(-1.1, 14.5, z)
    tx1, ty1 = proj(1.1, 6.0, z)
    L.rect(tx0, ty0, tx1, ty1 + 4, "BROWN_DARK")
    L.poly([(tx0 - 1, ty0), (CX, ty0 - 7), (tx1 + 1, ty0)], "CHARCOAL")
    L.vline(CX, ty0 - 13, ty0 - 7, "CHARCOAL")
    L.hline(CX - 2, CX + 2, ty0 - 11, "CHARCOAL")
    L.vline(tx1, ty0, ty1 + 4, "RIM")
    L.rect(CX - 1, ty0 + 2, CX, ty0 + 4, "LAMP")
    L.rect(CX - 2, by1 - 5, CX + 1, by1 - 1, "LAMP")
    L.px(CX - 1, by1 - 5, "LAMP_HOT")
    for wx in (bx0 + 3, bx1 - 4):
        L.rect(wx, by0 + 3, wx + 1, by0 + 5, "AMBER")
    L.glow(CX, by1 - 3, 3, 9, "AMBER", 0.35, over=True)


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
    for k in range(int(x - w / 2), int(x + w / 2), 2):
        L.vline(k, yt + 1, ym - 1, "BROWN")
    L.poly([(x - w / 2 - 2, yt), (x, yt - 4), (x + w / 2 + 1, yt)], "CHARCOAL")
    L.vline(round(x + w / 2), yt, ym, "RIM")
    for hy in (yt + 2, ym - 2):
        L.hline(x - w / 2 - 1, x + w / 2, round(hy), "GREY_DARK")


def windmill(L):
    X, z = 11.5, 24.0
    xb, yb = proj(X, 0, z)
    _, yt = proj(X, 17.5, z)
    wb, wt = F * 3.0 / z, F * 0.8 / z
    lx0, lx1 = xb - wb / 2, xb + wb / 2
    tx0, tx1 = xb - wt / 2, xb + wt / 2
    L.line([(lx0, yb), (tx0, yt)], "CHARCOAL")
    L.line([(lx1, yb), (tx1, yt)], "CHARCOAL")
    L.line([(lx1 + 1, yb), (tx1 + 1, yt)], "RIM")
    n = 6
    for i in range(n):
        ya = yb + (yt - yb) * i / n
        yb2 = yb + (yt - yb) * (i + 1) / n
        fa, fb = i / n, (i + 1) / n
        xa0, xa1 = lx0 + (tx0 - lx0) * fa, lx1 + (tx1 - lx1) * fa
        xb0, xb1 = lx0 + (tx0 - lx0) * fb, lx1 + (tx1 - lx1) * fb
        L.line([(xa0, ya), (xb1, yb2)], "CHARCOAL")
        L.line([(xa1, ya), (xb0, yb2)], "CHARCOAL")
        L.line([(xb0, yb2), (xb1, yb2)], "CHARCOAL")
    cx, cy = xb, yt - 3
    L.rect(cx - 4, yt - 1, cx + 4, yt, "CHARCOAL")
    r = 13
    for k in range(18):  # blades: a spoke plus a widened outer vane
        a = k * math.pi * 2 / 18 + 0.1
        ex, ey = cx + r * math.cos(a), cy + r * math.sin(a)
        L.line([(cx, cy), (ex, ey)], "CHARCOAL")
        for f in (0.5, 0.7):
            mx, my = cx + r * f * math.cos(a + 0.13), cy + r * f * math.sin(a + 0.13)
            L.line([(mx, my), (ex, ey)], "CHARCOAL")
    for k in range(96):
        a = k * math.pi * 2 / 96
        L.px(cx + r * math.cos(a), cy + r * math.sin(a), "CHARCOAL")
        L.px(cx + 5 * math.cos(a), cy + 5 * math.sin(a), "CHARCOAL")
    L.ellipse(cx - 1, cy - 1, cx + 1, cy + 1, "INK")
    L.line([(cx, cy), (cx + 15, cy - 1)], "CHARCOAL")
    L.poly([(cx + 11, cy - 7), (cx + 19, cy - 6), (cx + 19, cy + 3), (cx + 12, cy + 2)], "CHARCOAL")
    L.hline(cx + 12, cx + 18, cy - 6, "RIM")
    for k in range(60):
        a = -1.3 + k * 0.045
        L.px(cx + r * math.cos(a), cy + r * math.sin(a), "RIM" if k % 3 else "RIM_HOT")


# ----------------------------------------------------------------------------------------
# sprites drawn as shapes

def horse(L, ox, oy, s=1.0, facing=-1, coat="LEATHER", shade="BROWN", dark="BROWN_DARK", blanket=None):
    """A standing horse, 40 x 36 design units scaled by s (drawn at scale, never resampled)."""
    S = Layer()
    wd = 40 * s

    def P_(x, y):
        return (ox + (x * s if facing < 0 else wd - x * s), oy + y * s)

    def poly(pts, c):
        S.poly([P_(x, y) for x, y in pts], c)

    def pline(pts, c, w=1):
        S.line([P_(x, y) for x, y in pts], c, w)

    for x0, x1 in ((13, 15.2), (31, 33.2)):                                # far legs
        poly([(x0, 20), (x1, 20), (x1, 32), (x1 - 0.3, 35), (x0, 35)], shade)
    poly([(9, 17), (14, 10), (27, 9), (34, 10), (38, 14), (37, 22), (31, 25), (14, 25), (9, 22)], coat)
    poly([(9, 18), (14, 11), (11, 4), (8, 2), (6, 5), (8, 13)], coat)      # neck
    poly([(8, 2), (4, 1), (0, 7), (0, 12), (3, 13), (5, 10), (7, 6)], coat)  # head
    poly([(6, 1.5), (7, -1.2), (8.2, 1.5)], coat)                           # ear
    for x0, x1 in ((10, 12.2), (16, 18.2), (28, 30.2), (34, 36.2)):
        poly([(x0, 22), (x1, 22), (x1, 32), (x1 - 0.3, 35), (x0, 35)], coat)
    S.outline("INK")
    cc = P.rgb(coat)
    arr = np.array(S.im)
    for X in range(W):
        ys = np.nonzero(arr[:, X, 3])[0]
        if not len(ys):
            continue
        ty = ys[0]
        for Y in ys:
            if tuple(arr[Y, X, :3]) != cc:
                continue
            rel = (Y - OY - (oy + 18 * s)) / (7 * s)
            if rel > 0 and dith(X, Y, rel):
                S.im.putpixel((X, Y), col(shade))
            if rel > 0.8 and dith(X, Y, rel - 0.8):
                S.im.putpixel((X, Y), col(dark))
            if Y == ty + 1 and (Y - OY) < oy + 12 * s:
                S.im.putpixel((X, Y), col("RIM"))
            elif Y == ty + 2 and (Y - OY) < oy + 12 * s and dith(X, Y, 0.5):
                S.im.putpixel((X, Y), col("OCHRE"))
    pline([(12.5, 10.5), (11, 6), (9, 2.5)], dark, max(1, round(s)))              # mane
    pline([(38, 13), (39, 20), (40, 29)], dark, max(1, round(s * 1.2)))           # tail
    pline([(38.7, 13), (39.8, 20), (40.8, 29)], "INK")
    dot = lambda x, y, c: S.px(P_(x, y)[0], P_(x, y)[1], c)
    dot(3, 5, "INK")
    dot(1, 11, dark)
    pline([(1, 8), (4, 9), (7, 6)], "BROWN_BLACK")                               # bridle
    for x0 in (10, 16, 28, 34):
        pline([(x0, 35), (x0 + 2.2, 35)], "INK")
    if blanket:
        poly([(18, 9.2), (27, 9.2), (27.5, 16), (17.5, 16)], blanket)
        pline([(18, 9.2), (27, 9.2)], "RED_LIGHT")
        pline([(17.5, 15.5), (27.5, 15.5)], "WINE")
        pline([(19, 12.5), (26, 12.5)], "GOLD")
        poly([(20, 7.5), (25, 7.5), (26, 9.5), (19, 9.5)], "BROWN_DARK")        # saddle
        pline([(20, 7.5), (25, 7.5)], "OCHRE")
    L.im.alpha_composite(S.im)


def wagon_wheel(L, cx, cy, r):
    for k in range(10):
        a = k * math.pi / 5
        L.line([(cx, cy), (cx + r * math.cos(a), cy + r * math.sin(a))], "LEATHER")
    for k in range(72):
        a = k * math.pi * 2 / 72
        L.px(cx + r * math.cos(a), cy + r * math.sin(a), "BROWN_DARK")
        L.px(cx + (r - 1) * math.cos(a), cy + (r - 1) * math.sin(a), "LEATHER" if math.sin(a) > -0.3 else "OCHRE")
    L.ellipse(cx - 1, cy - 1, cx + 1, cy + 1, "INK")


def barrel(L, x, y, w=20, h=27):
    L.rect(x + 1, y, x + w - 2, y + h - 1, "LEATHER")
    L.rect(x, y + 3, x + w - 1, y + h - 4, "LEATHER")
    for sx in range(x + 2, x + w - 1, 4):
        L.vline(sx, y + 1, y + h - 2, "BROWN_MID")
    for sx in range(x + 1, x + 4):
        L.vline(sx, y + 1, y + h - 2, "BROWN")
    L.vline(x + w - 3, y + 2, y + h - 3, "RIM")
    L.vline(x + w - 4, y + 2, y + h - 3, "OCHRE")
    L.vline(x + w - 5, y + 2, y + h - 3, "OCHRE")
    for hy in (y + 4, y + h - 6):
        L.hline(x, x + w - 1, hy, "GREY_DARK")
        L.hline(x, x + w - 1, hy + 1, "CHARCOAL")
        L.hline(x + w - 5, x + w - 2, hy, "SILVER")
    L.hline(x + 1, x + w - 2, y, "BROWN_DARK")
    L.hline(x + 2, x + w - 3, y + 1, "BROWN")
    L.hline(x + 3, x + w - 5, y + 2, "BROWN_MID")


def lantern(L, x, y):
    L.vline(x + 3, y - 9, y - 1, "CHARCOAL")
    L.glow(x + 3, y + 6, 4, 18, "AMBER", 0.45)
    L.glow(x + 3, y + 6, 4, 10, "LAMP", 0.35)
    L.rect(x, y, x + 6, y + 1, "CHARCOAL")
    L.rect(x + 1, y - 1, x + 5, y - 1, "GREY_DARK")
    L.rect(x, y + 2, x + 6, y + 10, "LAMP")
    L.rect(x + 2, y + 4, x + 4, y + 8, "LAMP_HOT")
    L.vline(x, y + 2, y + 10, "CHARCOAL")
    L.vline(x + 6, y + 2, y + 10, "CHARCOAL")
    L.vline(x + 3, y + 2, y + 3, "AMBER")
    L.rect(x, y + 11, x + 6, y + 11, "CHARCOAL")
    L.px(x + 3, y + 12, "CHARCOAL")


def bitmap(L, x, y, rows, colours):
    for ry, r in enumerate(rows):
        for rx, ch in enumerate(r):
            if ch in colours:
                L.px(x + rx, y + ry, colours[ch])


def cow_skull(L, x, y):
    bitmap(L, x, y, [
        "cc.................cc",
        "ccc...............ccc",
        ".cccc...........cccc.",
        "..cccbbbb...bbbbccc..",
        "....bbbbbbbbbbbbb....",
        "....bbooobbbooobb....",
        ".....boooobboooob....",
        ".....bbooobbbooobs...",
        "......bbbbbbbbbbs....",
        ".......bbbbbbbbs.....",
        ".......bbbbbbbss.....",
        "........bbbbbbs......",
        "........bbnbnbs......",
        "........bbbbbss......",
        ".........bbbbs.......",
        ".........tbtbt.......",
    ], {"c": "CREAM_SHADE", "b": "CREAM", "o": "INK", "n": "BROWN_BLACK", "s": "TAN", "t": "SAND"})
    for k in range(2):
        L.px(x + k, y, "PALE")
        L.px(x + 20 - k, y, "PALE")
    L.px(x + 9, y + 4, "PALE")
    L.px(x + 10, y + 4, "PALE")


def crow(L, x, y):
    bitmap(L, x, y, [
        ".....iii......",
        "....iiiii.....",
        "..gGiieii.....",
        "....iiiiii....",
        "....iiiiiii...",
        "....iiissiii..",
        ".....iissiiii.",
        ".....iiiiiiiii",
        "......iiiiiii.",
        ".......iiiii..",
        "........i.i...",
        "........i.i...",
        ".......ii.ii..",
    ], {"i": "INK", "g": "GREY", "G": "SILVER", "e": "LAMP", "s": "SLATE"})
    L.hline(x + 6, x + 9, y, "SLATE")
    L.px(x + 10, y + 7, "RIM")


def crate(L, x0, y0, x1, y1):
    L.rect(x0, y0, x1, y1, "BROWN_DARK")
    L.rect(x0, y0, x1, y0 + 7, "BROWN")
    L.hline(x0, x1, y0, "RIM")
    L.hline(x0, x1, y0 + 1, "OCHRE")
    L.hline(x0, x1, y0 + 7, "BROWN_BLACK")
    for x in range(x0 + 6, x1, 9):
        L.vline(x, y0 + 8, y1, "BROWN_BLACK")
        L.vline(x + 1, y0 + 8, y1, "BROWN")
    L.vline(x0, y0, y1, "LEATHER")
    L.vline(x0 + 1, y0, y1, "BROWN_MID")
    for y in range(y0 + 20, y1, 30):
        L.hline(x0, x1, y, "BROWN_BLACK")
        L.hline(x0, x1, y + 1, "BROWN")
    L.line([(x0 + 2, y0 + 10), (x1, y0 + 10 + (x1 - x0) * 2)], "BROWN", 3)
    L.line([(x0 + 3, y0 + 9), (x1 + 1, y0 + 9 + (x1 - x0) * 2)], "LEATHER")
    for k in range(4):
        L.px(x0 + 3, y0 + 12 + k * 36, "SILVER")


def sagebrush(L, rng, x0, x1, y0, y1, n):
    for _ in range(n):
        x = rng.randint(x0, x1)
        y = rng.randint(y0, y1)
        h = rng.randint(4, 10)
        for k in range(-3, 4):
            top = y - h + abs(k) * 2
            L.line([(x, y), (x + k * 2, top)], ("OLIVE_DARK", "OLIVE", "BROWN_DARK")[abs(k) % 3])
        for k in range(3):
            L.px(x + rng.randint(-5, 5), y - h + rng.randint(0, 3), "SAGE")
        L.hline(x - 3, x + 3, y + 1, "BROWN_BLACK")


# ----------------------------------------------------------------------------------------
# the player from behind, title framing (lower left, hat top near y 268)

def draw_player(rng):
    L = Layer()
    # trousers and boots of the back leg
    L.poly([(-42, 584), (-34, 482), (62, 482), (70, 584)], "CHARCOAL")
    L.poly([(10, 515), (19, 508), (25, 584), (8, 584)], "INK")
    L.recolour(-42, 482, 70, 584, lambda x, y, c: ("SHADOW" if c == "CHARCOAL" and (x > 40 and dith(x, y, (x - 40) / 40)) else
                                                   "NAVY" if c == "CHARCOAL" and hsh(x // 3, y // 7) < 0.08 else None))
    for y in range(486, 584, 4):
        L.px(56 - (y - 486) // 9, y, "GREY_DARK")
    # gun belt with brass cartridges
    L.poly([(-30, 462), (64, 456), (66, 472), (-30, 480)], "BROWN_DARK")
    L.line([(-30, 462), (64, 456)], "LEATHER")
    for x in range(-28, 64, 4):
        yy = 466 + (x + 30) * -6 // 94
        L.vline(x, yy - 1, yy + 3, "GOLD")
        L.vline(x + 1, yy - 1, yy + 3, "OCHRE")
        L.px(x, yy - 2, "LAMP")
    # holster on the right hip with the revolver seated in it, grip up and back
    L.poly([(56, 472), (73, 468), (80, 540), (65, 545)], "LEATHER")
    L.line([(73, 469), (80, 539)], "RIM")
    L.line([(72, 470), (79, 539)], "OCHRE")
    L.line([(60, 480), (67, 541)], "BROWN_MID")
    for y in range(480, 536, 5):  # stitching
        L.px(70 + (y - 480) // 9, y, "TAN")
    L.poly([(59, 486), (73, 484), (74, 500), (61, 503)], "BROWN")             # tooled panel
    L.line([(61, 490), (72, 488)], "OCHRE")
    L.poly([(58, 462), (75, 459), (76, 474), (60, 477)], "BROWN_DARK")         # holster mouth
    L.poly([(61, 444), (74, 441), (77, 464), (64, 467)], "SILVER")             # frame and cylinder
    L.poly([(63, 449), (74, 447), (75, 458), (64, 460)], "GREY")
    for yy in (450, 453, 456):
        L.hline(64, 74, yy, "GREY_DARK")
    L.vline(75, 442, 463, "STEEL_HI")
    L.poly([(52, 431), (62, 425), (68, 444), (59, 450)], "BROWN")              # wooden grip
    L.line([(55, 432), (61, 446)], "LEATHER")
    L.line([(53, 432), (60, 448)], "BROWN_DARK")
    L.px(58, 436, "GOLD")
    L.poly([(63, 437), (66, 434), (68, 441)], "SILVER")                        # hammer
    # right arm hanging past the poncho
    L.poly([(64, 390), (83, 398), (91, 456), (80, 470), (66, 457)], "BROWN_MID")
    L.line([(70, 402), (78, 450)], "BROWN")
    L.line([(74, 410), (80, 432)], "BROWN")
    L.poly([(72, 456), (88, 453), (94, 486), (78, 492)], "SKIN_DARK")          # forearm
    L.line([(88, 455), (93, 484)], "SKIN")
    L.poly([(75, 482), (94, 479), (97, 503), (80, 509)], "CHARCOAL")           # glove
    L.line([(94, 481), (96, 501)], "GREY_DARK")
    L.hline(78, 93, 485, "BROWN_DARK")
    L.vline(90, 400, 455, "RIM")
    L.vline(89, 405, 450, "OCHRE")
    # poncho: big teal blanket over the shoulders
    pon = [(-42, 338), (-8, 326), (25, 321), (55, 326), (78, 340), (91, 376), (97, 415), (88, 440), (-42, 468)]
    L.poly(pon, "TEAL")

    def hem(x):
        return 468 + (x + 42) * (440 - 468) / 138

    def shade(x, y, c):
        if c != "TEAL":
            return None
        fold = math.sin(x * 0.19 + (y - 320) * 0.045) + 0.35 * math.sin(x * 0.53 - y * 0.02)
        if x < 8 and dith(x, y, (8 - x) / 50 + 0.1):
            return "TEAL_DARK"
        if fold > 0.95 and y > 345:
            return "TEAL_DARK"
        if 0.6 < fold <= 0.95 and y > 345 and dith(x, y, 0.4):
            return "TEAL_DARK"
        if x > 58 and y < 400 and dith(x, y, (x - 58) / 34):
            return "TEAL_LIGHT"
        if fold < -0.9 and y > 350 and dith(x, y, 0.3):
            return "TEAL_LIGHT"
        return None
    L.recolour(-42, 318, 98, 470, shade)
    for x in range(-42, 97):
        h = round(hem(x))
        b = h - 19
        # mustard band with stepped teal diamonds and cream crosses
        for k in range(6):
            L.px(x, b + k, "GOLD")
        m = (x + 42) % 12
        dd = abs(m - 6)
        for k in range(6):
            if abs(k - 2.5) + dd < 3.2:
                L.px(x, b + k, "TEAL_DARK")
        if m == 6:
            L.px(x, b + 2, "CREAM")
            L.px(x, b + 3, "CREAM")
        if m in (5, 7):
            L.px(x, b + 2 if m == 5 else b + 3, "CREAM")
        L.px(x, b, "LAMP" if x > 55 else "GOLD")
        L.px(x, b - 3, "CREAM" if (x // 2) % 3 else "TEAL")
        L.px(x, b - 4, "TEAL_DARK")
        L.px(x, b + 7, "TEAL_DARK")
        L.px(x, h - 4, "GOLD")
        L.px(x, h - 3, "MAROON" if (x // 3) % 2 else "GOLD")
        L.px(x, h - 2, "TEAL_DARK")
        L.px(x, h - 1, "TEAL_DARK")
        if x % 2 == 0:  # fringe, strands of uneven length, knotted at the top
            ln = 6 + int(hsh(x, 5) * 7)
            L.vline(x, h, h + ln, "CREAM" if x % 4 else "CREAM_SHADE")
            L.px(x, h + ln, "TAN")
            L.px(x, h, "TAN")
    for x in range(-40, 62):  # shoulder band
        y = 342 + (x + 40) // 10
        L.px(x, y, "GOLD")
        L.px(x, y + 1, "GOLD" if (x // 3) % 2 == 0 else "TEAL_DARK")
        if x % 6 == 0:
            L.px(x, y - 2, "CREAM")
            L.px(x + 1, y - 2, "CREAM")
    L.line([(55, 326), (78, 340), (91, 376), (97, 413)], "RIM")
    L.line([(54, 328), (76, 342), (89, 377)], "TEAL_PALE")
    # neck, curly hair, hat
    L.poly([(14, 316), (42, 316), (45, 330), (11, 330)], "SKIN_DARK")
    L.line([(40, 318), (44, 329)], "SKIN")
    for (x, y) in [(10, 313), (16, 318), (22, 314), (28, 319), (34, 314), (40, 318), (45, 314), (47, 321),
                   (8, 320), (13, 324), (20, 323), (43, 325), (5, 316)]:
        L.ellipse(x - 3, y - 3, x + 3, y + 3, "BROWN_DARK")
        L.px(x, y - 2, "BROWN_MID")
        L.px(x + 1, y - 2, "BROWN")
        L.px(x - 1, y + 1, "BROWN_BLACK")
    L.ellipse(-17, 296, 80, 316, "CHARCOAL")                                   # brim
    L.hline(6, 76, 297, "RIM")
    L.hline(20, 70, 298, "OCHRE")
    L.ellipse(-14, 299, 77, 313, "INK")
    L.ellipse(-14, 297, 77, 310, "CHARCOAL")
    L.ellipse(-8, 298, 60, 306, "SHADOW")
    L.poly([(6, 302), (8, 277), (17, 268), (30, 273), (47, 268), (55, 277), (58, 302)], "CHARCOAL")  # crown
    L.poly([(18, 272), (30, 276), (44, 272), (40, 283), (22, 283)], "SHADOW")   # crease
    L.poly([(7, 290), (57, 290), (58, 300), (6, 300)], "LEATHER")               # band
    L.hline(7, 57, 291, "OCHRE")
    L.hline(6, 58, 299, "BROWN_DARK")
    for cx in (14, 26, 38, 50):                                                 # conchos
        L.px(cx, 294, "SILVER")
        L.px(cx + 1, 294, "STEEL_HI")
        L.px(cx, 295, "GREY")
    L.line([(30, 273), (47, 268), (55, 277), (58, 300)], "RIM")
    L.line([(46, 270), (53, 278)], "RIM_HOT")
    L.line([(17, 270), (28, 275)], "BROWN_DARK")
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
    lantern(town, round(lx) - 3, round(ly))
    wagon_wheel(town, 83, 313, 8)
    wagon_wheel(town, 72, 317, 10)
    town.rect(69, 303, 92, 309, "BROWN_DARK")
    town.hline(69, 92, 303, "RIM")
    town.hline(69, 92, 304, "OCHRE")
    horse(town, 188, 280, s=1.72, coat="BROWN", shade="BROWN_DARK", dark="BROWN_BLACK")
    horse(town, 163, 286, s=1.86, coat="LEATHER", shade="BROWN_MID", dark="BROWN", blanket="BLOOD")
    town.line([(177, 338), (272, 354)], "LEATHER", 3)
    town.line([(177, 337), (272, 353)], "RIM")
    for px_ in (180, 244):
        town.rect(px_, 337, px_ + 3, 362 + (px_ - 180) // 8, "BROWN")
        town.vline(px_ + 3, 337, 362 + (px_ - 180) // 8, "OCHRE")

    fg = Layer()
    # corner post of the near building with its roof beam, a skull nailed on, a crow on top
    fg.rect(245, 97, 255, 362, "BROWN")
    fg.vline(245, 97, 362, "RIM")
    fg.vline(246, 97, 362, "OCHRE")
    fg.vline(247, 97, 362, "LEATHER")
    fg.vline(255, 97, 362, "BROWN_DARK")
    for y in range(110, 360, 17):  # grain
        fg.vline(250 + (y // 17) % 3, y, y + 6, "BROWN_DARK")
    fg.rect(243, 124, 280, 132, "BROWN")
    fg.hline(243, 280, 124, "RIM")
    fg.hline(243, 280, 125, "OCHRE")
    fg.hline(243, 280, 132, "BROWN_DARK")
    cow_skull(fg, 240, 166)
    crow(fg, 243, 84)
    barrel(fg, 234, 326, 22, 28)
    crate(fg, 241, 414, 284, 596)
    sagebrush(fg, rng, 160, 270, 545, 580, 11)
    sagebrush(fg, rng, 100, 160, 562, 582, 4)
    sagebrush(fg, rng, 208, 236, 360, 372, 3)
    fg.outline("INK")

    player = draw_player(rng)

    for name, layer in (("sky", sky), ("mesas", mesas), ("town", town), ("fg", fg), ("player_back", player)):
        layer.save("%s/%s.png" % (out_dir, name))
    comp = Image.new("RGBA", (W, H))
    for layer in (sky, mesas, town, fg, player):
        comp.alpha_composite(layer.im)
    return comp
