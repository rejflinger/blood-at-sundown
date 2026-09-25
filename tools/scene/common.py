"""Shared canvas, camera and raster helpers for the street scene (see art_scene.py)."""
import math

import numpy as np
from PIL import Image, ImageDraw

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
