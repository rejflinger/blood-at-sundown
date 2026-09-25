"""Foreground layer: the near right building corner with the cow skull and crow, barrel,
crate and sagebrush."""
import math

import numpy as np

import palette as P
from scene.common import *  # noqa: F401,F403


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


def draw_foreground(rng):
    """Foreground layer: corner post with skull and crow, barrel, crate, sagebrush."""
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
    return fg
