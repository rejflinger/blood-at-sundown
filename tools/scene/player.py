"""The player seen from behind in the lower left (title framing)."""
import math

import numpy as np

import palette as P
from scene.common import *  # noqa: F401,F403


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
