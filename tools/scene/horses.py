"""Horses at the hitching rail on the right side of the street (town layer)."""
import math

import numpy as np

import palette as P
from scene.common import *  # noqa: F401,F403


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


def draw_street_props(L, rng):
    """Horses at the hitching rail on the right side of the street (town layer)."""
    horse(L, 188, 280, s=1.72, coat="BROWN", shade="BROWN_DARK", dark="BROWN_BLACK")
    horse(L, 163, 286, s=1.86, coat="LEATHER", shade="BROWN_MID", dark="BROWN", blanket="BLOOD")
    L.line([(177, 338), (272, 354)], "LEATHER", 3)
    L.line([(177, 337), (272, 353)], "RIM")
    for px_ in (180, 244):
        L.rect(px_, 337, px_ + 3, 362 + (px_ - 180) // 8, "BROWN")
        L.vline(px_ + 3, 337, 362 + (px_ - 180) // 8, "OCHRE")
