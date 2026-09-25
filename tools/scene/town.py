"""Facades, porches, sign, far town and church, water tower and windmill, all projected
through the one street camera."""
import math

import gen_fonts
from scene.common import *  # noqa: F401,F403


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


def wagon_wheel(L, cx, cy, r):
    for k in range(10):
        a = k * math.pi / 5
        L.line([(cx, cy), (cx + r * math.cos(a), cy + r * math.sin(a))], "LEATHER")
    for k in range(72):
        a = k * math.pi * 2 / 72
        L.px(cx + r * math.cos(a), cy + r * math.sin(a), "BROWN_DARK")
        L.px(cx + (r - 1) * math.cos(a), cy + (r - 1) * math.sin(a), "LEATHER" if math.sin(a) > -0.3 else "OCHRE")
    L.ellipse(cx - 1, cy - 1, cx + 1, cy + 1, "INK")


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


def draw_town_back(L, rng):
    """Everything on the horizon that the ground and facades are drawn over."""
    far_town(L, rng)
    water_tower(L)


def draw_town_front(L, rng):
    """Windmill, facades, porches, lantern and the wagon by the saloon."""
    windmill(L)
    draw_facades(L, -1, LEFT)
    draw_facades(L, 1, RIGHT)
    porch(L, -1, 2.6, 23.0, [3.4, 6.4, 9.4, 12.4, 15.4, 18.4, 21.4])
    porch(L, 1, 3.0, 17.0, [3.8, 6.8, 9.8, 12.8, 15.8])
    lx, ly = proj(5.4, 3.5, 7.0)
    lantern(L, round(lx) - 3, round(ly))
    wagon_wheel(L, 83, 313, 8)
    wagon_wheel(L, 72, 317, 10)
    L.rect(69, 303, 92, 309, "BROWN_DARK")
    L.hline(69, 92, 303, "RIM")
    L.hline(69, 92, 304, "OCHRE")
