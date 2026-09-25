"""The street and ground: perspective ramp, ruts, pebbles, hoof prints, rocks."""
from scene.common import *  # noqa: F401,F403


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
