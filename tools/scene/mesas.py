"""Mesas, buttes and the far hazy hills along the horizon."""
import math

import numpy as np

from scene.common import *  # noqa: F401,F403


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
