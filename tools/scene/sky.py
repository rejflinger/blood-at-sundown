"""Sky: dithered bands, streaky cloud strata, the setting sun and its stepped halo."""
import math

from scene.common import *  # noqa: F401,F403


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
