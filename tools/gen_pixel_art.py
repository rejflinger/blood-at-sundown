"""Pixel art generator for Blood at Sundown (PIL, numpy).

Milestone 1 output:
  assets/palette.png   64 x 2 palette (row 0 gold dusk, row 1 deep red dusk)
  assets/ui/logo.png   title logo: red BLOOD, cream SUNDOWN, ink outline, drips
  icon.png             192 x 192 app icon (48 x 48 art scaled 4x nearest)
  assets/world/*.png   street scene layers (art_scene.py): sky, mesas, town, fg, player_back

Everything is drawn with aliased primitives at native resolution and uses only palette
colours. Run: python3 tools/gen_pixel_art.py
"""
import os
import sys

# Set iteration order must not change the art: re-run with a fixed hash seed.
if os.environ.get("PYTHONHASHSEED") != "0":
    os.environ["PYTHONHASHSEED"] = "0"
    os.execv(sys.executable, [sys.executable] + sys.argv)
import random

import numpy as np
from PIL import Image, ImageDraw

import art_scene
import gen_fonts
import palette as P

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0


def C(name, t=0.0):
    return P.rgb(name, t) + (255,)


# ----------------------------------------------------------------------------------------
# logo lettering: Tuscan western capitals built on a padded boolean grid

class Glyph:
    """One letter on a boolean grid. Letter coordinates run 0..w-1, 0..h-1; a margin of PAD
    pixels on every side leaves room for serifs and spurs, and is trimmed afterwards."""
    PAD = 5

    def __init__(self, w, h):
        self.w, self.h = w, h
        p = self.PAD
        self.m = np.zeros((h + 2 * p, w + 2 * p), dtype=bool)

    def px(self, x, y, v=True):
        p = self.PAD
        if 0 <= y + p < self.m.shape[0] and 0 <= x + p < self.m.shape[1]:
            self.m[y + p, x + p] = v

    def rect(self, x0, y0, x1, y1, v=True):
        if x1 < x0 or y1 < y0:
            return
        p = self.PAD
        self.m[max(0, y0 + p): y1 + p + 1, max(0, x0 + p): x1 + p + 1] = v

    def rr(self, x0, y0, x1, y1, r=(0, 0, 0, 0), v=True, n=2.0):
        """Rectangle with rounded corners r = (tl, tr, br, bl); each corner is a radius or
        an (rx, ry) pair. Tested at pixel centres, so the edge is hard and aliased."""
        rs = []
        for c in r:
            rs.append((c, c) if isinstance(c, (int, float)) else c)
        (tlx, tly), (trx, try_), (brx, bry), (blx, bly) = rs
        corners = (
            (tlx, tly, x0 + tlx, y0 + tly, -1, -1),
            (trx, try_, x1 + 1 - trx, y0 + try_, 1, -1),
            (brx, bry, x1 + 1 - brx, y1 + 1 - bry, 1, 1),
            (blx, bly, x0 + blx, y1 + 1 - bly, -1, 1),
        )
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                cx, cy = x + 0.5, y + 0.5
                inside = True
                for rx, ry, ox, oy, sx, sy in corners:
                    if rx <= 0 or ry <= 0:
                        continue
                    if (cx - ox) * sx > 0 and (cy - oy) * sy > 0:
                        if (abs(cx - ox) / rx) ** n + (abs(cy - oy) / ry) ** n > 1.0:
                            inside = False
                            break
                if inside:
                    self.px(x, y, v)

    def poly(self, pts, v=True):
        p = self.PAD
        im = Image.new("1", (self.m.shape[1], self.m.shape[0]), 0)
        ImageDraw.Draw(im).polygon([(x + p, y + p) for x, y in pts], fill=1)
        sel = np.array(im, dtype=bool)
        self.m[sel] = v

    def serif(self, x0, x1, y0, rows, notch_l=True, notch_r=True):
        """Slab serif; each notched end is split by a 1 px notch into two points."""
        self.rect(x0, y0, x1, y0 + rows - 1)
        mids = range(y0 + 1, y0 + rows - 1)
        for y in mids:
            if notch_l:
                self.px(x0, y, False)
            if notch_r:
                self.px(x1, y, False)

    def bracket(self, x_edge, y0, side, down, prof):
        """Concave fillet where a serif meets its stem: prof[i] pixels out, row by row."""
        for i, d in enumerate(prof):
            for j in range(1, d + 1):
                self.px(x_edge + side * j, y0 + down * i)

    def spur(self, x_edge, y_mid, side, prof=(1, 2, 1)):
        """A point bulging out of a stem: prof[i] pixels beyond column x_edge."""
        k = len(prof) // 2
        for i, d in enumerate(prof):
            for j in range(1, d + 1):
                self.px(x_edge + side * j, y_mid - k + i)

    def nib(self, pts, nw, nh):
        """Drag a flat nw x nh pen along points: verticals come out nw thick, horizontals nh."""
        for (x, y) in pts:
            x0 = int(np.floor(x - nw / 2.0 + 0.5))
            y0 = int(np.floor(y - nh / 2.0 + 0.5))
            self.rect(x0, y0, x0 + nw - 1, y0 + nh - 1)

    def get(self, x, y):
        p = self.PAD
        if 0 <= y + p < self.m.shape[0] and 0 <= x + p < self.m.shape[1]:
            return bool(self.m[y + p, x + p])
        return False


def letter(ch, H, W, S, T, ser=3, sr=4, prof=(1, 2, 1), cw=None, raw=False):
    """Tuscan western capital as a mask of H rows (columns trimmed).
    S = stem width, T = horizontal stroke, ser = serif overhang, sr = serif rows,
    prof = mid-stem spur profile, cw = counter width."""
    g = Glyph(W, H)
    B = H - 1
    iprof = tuple(max(0, d - 1) for d in prof)  # smaller spur into a counter
    bp = (2, 1, 1) if S >= 9 else (1, 1)          # serif bracket
    if cw is None:
        cw = max(4, S * 4 // 5)
    if ch == "B":
        xs, xe = ser, ser + S - 1
        ym = int(H * 0.46)
        bar0 = ym - T // 2
        bar1 = bar0 + T - 1
        up_r = W - 1 - max(2, W // 9)
        g.rect(xs, 0, xe, B)
        ru = (max(4, (up_r - xe) * 4 // 5), max(4, (bar1 + 1) * 9 // 20))
        rl = (max(4, (W - 1 - xe) * 4 // 5), max(4, (B - bar0) * 9 // 20))
        g.rr(xs, 0, up_r, bar1, (0, ru, ru, 0), n=2.1)
        g.rr(xs, bar0, W - 1, B, (0, rl, rl, 0), n=2.1)
        cu, cl = cw - 2, cw - 1
        g.rr(xe + 1, T, xe + cu, bar0 - 1, (0, (2, 3), (2, 3), 0), v=False)
        g.rr(xe + 1, bar1 + 1, xe + cl, B - T, (0, (2, 3), (2, 3), 0), v=False)
        g.serif(0, xe + 2, 0, sr, True, False)
        g.serif(0, xe + 2, H - sr, sr, True, False)
        g.bracket(xs, sr, -1, 1, bp)
        g.bracket(xs, H - sr - 1, -1, -1, bp)
        # waist: a V notch between the bowls with a small point in its throat
        wm = (bar0 + bar1) // 2
        dn = max(4, W // 6)
        g.poly([(W + 1, wm - dn), (W - dn, wm), (W - dn, wm + 1), (W + 1, wm + dn + 1)], v=False)
        g.spur(xs, ym, -1, prof)
        g.spur(xe, (T + bar0) // 2, 1, iprof)
        g.spur(xe, (bar1 + B - T) // 2 + 1, 1, iprof)
    elif ch == "D":
        xs, xe = ser, ser + S - 1
        g.rect(xs, 0, xe, B)
        R = (max(5, (W - 1 - xe) * 4 // 5), max(6, H * 3 // 10))
        g.rr(xs, 0, W - 1, B, (0, R, R, 0), n=2.4)
        g.rr(xe + 1, T, xe + cw - 1, B - T, (0, (3, 5), (3, 5), 0), v=False)
        g.serif(0, xe + 2, 0, sr, True, False)
        g.serif(0, xe + 2, H - sr, sr, True, False)
        g.bracket(xs, sr, -1, 1, bp)
        g.bracket(xs, H - sr - 1, -1, -1, bp)
        g.spur(xs, H // 2, -1, prof)
        g.spur(W - 1, H // 2, 1, prof)
        g.spur(xe, H // 2, 1, iprof)
    elif ch == "O":
        R = (W // 2, max(6, H * 3 // 10))
        g.rr(0, 0, W - 1, B, (R, R, R, R), n=2.3)
        cx0 = (W - cw) // 2
        rc = (cw // 2, max(3, cw))
        g.rr(cx0, T + 1, cx0 + cw - 1, B - T - 1, (rc, rc, rc, rc), v=False, n=2.0)
        g.spur(0, H // 2, -1, prof)
        g.spur(W - 1, H // 2, 1, prof)
        g.spur(cx0 - 1, H // 2, 1, iprof)
        g.spur(cx0 + cw, H // 2, -1, iprof)
    elif ch == "L":
        xs, xe = ser, ser + S - 1
        g.rect(xs, 0, xe, B)
        g.serif(0, xe + ser, 0, sr, True, True)
        g.rect(1, H - T, W - 1, B)
        g.serif(0, xe + 2, H - sr, sr, True, False)
        g.bracket(xs, sr, -1, 1, bp)
        g.bracket(xe, sr, 1, 1, bp)
        g.bracket(xs, H - sr - 1, -1, -1, bp)
        toe = max(8, H // 4)
        tw = max(6, W // 3)
        for i in range(tw + 1):  # upturned toe: a concave wedge rising to a point
            c = W - 1 - tw + i
            rise = int(round(toe * (i / float(tw)) ** 2))
            g.rect(c, H - T - rise, c, H - T)
        g.rect(W - 2, H - T - toe + 1, W - 1, H - T)
        for (x, y) in ((xe + 1, H - T - 1), (xe + 2, H - T - 1), (xe + 1, H - T - 2)):
            g.px(x, y)  # bracket between stem and foot
        ym = (sr + H - T) // 2
        g.spur(xs, ym, -1, prof)
        g.spur(xe, ym, 1, prof)
    elif ch == "U":
        xl, xr = ser, W - 1 - ser
        R = ((xr - xl + 1) // 2, max(6, H * 3 // 10))
        g.rr(xl, 0, xr, B, (0, 0, R, R), n=2.4)
        c0, c1 = xl + S, xr - S
        rc = ((c1 - c0 + 1) // 2, max(3, c1 - c0 + 1))
        g.rr(c0, -1, c1, B - T, (0, 0, rc, rc), v=False)
        g.serif(xl - ser, xl + S, 0, sr, True, False)
        g.serif(xr - S, xr + ser, 0, sr, False, True)
        g.bracket(xl, sr, -1, 1, bp)
        g.bracket(xr, sr, 1, 1, bp)
        ym = int(H * 0.44)
        g.spur(xl, ym, -1, prof)
        g.spur(xr, ym, 1, prof)
        g.spur(c0 - 1, ym, 1, iprof)
        g.spur(c1 + 1, ym, -1, iprof)
    elif ch == "N":
        s2 = max(3, (S + 1) // 2)
        xl, xr = ser, W - 1 - ser
        g.rect(xl, 0, xl + s2 - 1, B)
        g.rect(xr - s2 + 1, 0, xr, B)
        g.poly([(xl, 0), (xl + S + 1, 0), (xr + 1, B), (xr - S, B)])
        g.serif(0, xl + s2 + 1, 0, sr, True, False)
        g.serif(0, xl + s2 - 1 + ser, H - sr, sr, True, True)
        g.serif(xr - s2 + 1 - ser, xr + ser, 0, sr, True, True)
        g.bracket(xl, sr, -1, 1, bp)
        g.bracket(xl, H - sr - 1, -1, -1, bp)
        g.bracket(xl + s2 - 1, H - sr - 1, 1, -1, bp)
        g.bracket(xr, sr, 1, 1, bp)
        g.bracket(xr - s2 + 1, sr, -1, 1, bp)
        ym = H // 2
        g.spur(xl, ym, -1, prof)
        g.spur(xr, ym, 1, prof)
    elif ch == "W":
        thin = max(3, (S + 1) // 2)
        xL = ser + S // 2
        xR = W - 1 - ser - thin // 2
        v1, v2 = int(W * 0.31), int(W * 0.69)
        apex = W // 2

        def stroke(xt, xb, w):
            h0, h1 = w / 2.0, w / 2.0
            g.poly([(xt - h0 + 0.5, 0), (xt + h1 - 0.5, 0), (xb + h1 - 0.5, B), (xb - h0 + 0.5, B)])

        stroke(xL, v1, S)
        stroke(apex - 1, v1, thin)
        stroke(apex, v2, S)
        stroke(xR, v2, thin)
        g.serif(0, xL + S // 2 + 2, 0, sr, True, True)
        g.serif(xR - thin // 2 - 2, W - 1, 0, sr, True, True)
        g.serif(apex - thin // 2 - 3, apex + S // 2 + 2, 0, max(2, sr - 1), True, True)
    elif ch == "S":
        # two elliptical bowls drawn with a flat pen, joined by a heavy diagonal spine
        hx, hy = S / 2.0, T / 2.0
        ym = H * 0.48
        cx = (W - 1) / 2.0
        rx = cx - hx + 0.5
        cy1, ry1 = (hy + ym) / 2.0, (ym - hy) / 2.0
        cy2, ry2 = (ym + H - 1 - hy + 0.5) / 2.0, (H - 1 - hy + 0.5 - ym) / 2.0
        ang = np.radians
        up = [(cx + rx * np.cos(ang(a)), cy1 - ry1 * np.sin(ang(a))) for a in np.arange(25, 236, 1.0)]
        lo = [(cx + rx * np.cos(ang(a)), cy2 - ry2 * np.sin(ang(a))) for a in np.arange(56, -156, -1.0)]
        g.nib(up, S, T)
        g.nib(lo, S, T)
        (xa, ya), (xb, yb) = up[-1], lo[0]
        spine = [(xa + (xb - xa) * t, ya + (yb - ya) * t) for t in np.linspace(0, 1, 40)]
        g.nib(spine, S, T + 2)
        # barbed terminals: a vertical serif top right and bottom left
        k = T + max(4, H // 7)
        g.rect(W - S + 1, 0, W - 1, k)
        g.px(W - 1, 1, False)
        g.px(W - 1, k - 1, False)
        g.rect(0, B - k, S - 2, B)
        g.px(0, B - 1, False)
        g.px(0, B - k + 1, False)
        g.spur(0, int(round(cy1)), -1, prof)
        g.spur(W - 1, int(round(cy2)), 1, prof)
    elif ch == "A":
        cx = W // 2
        g.poly([(cx - 2, 0), (cx + 1, 0), (ser + S, B), (ser, B)])
        g.poly([(cx - 1, 0), (cx + 2, 0), (W - 1 - ser, B), (W - 1 - ser - S, B)])
        cy = int(H * 0.62)
        g.rect(ser + S - 1, cy, W - 1 - ser - S + 1, cy + T - 1)
        g.serif(0, ser + S + 2, H - sr, sr, True, True)
        g.serif(W - 1 - ser - S - 2, W - 1, H - sr, sr, True, True)
    elif ch == "T":
        cx = W // 2
        g.rect(0, 0, W - 1, T - 1)
        g.rect(0, 0, 1, T + 1)
        g.rect(W - 2, 0, W - 1, T + 1)
        g.rect(cx - S // 2, 0, cx - S // 2 + S - 1, B)
        g.serif(cx - S // 2 - ser, cx - S // 2 + S - 1 + ser, H - sr, sr, True, True)
    else:
        raise ValueError(ch)
    p = Glyph.PAD
    if raw:
        return g.m[p: p + H, :].copy()
    return trim(g.m[p: p + H, :])


def trim(m):
    cols = np.where(m.any(axis=0))[0]
    return m[:, cols[0]: cols[-1] + 1]


def kern_word(text, specs, S, T, gmin, kprof=None, **kw):
    """Letters kerned so their closest approach leaves gmin clear pixels (8-neighbour), so
    serifs interlock the way hand-set wood type does. With kprof, spacing is measured on the
    letters drawn with that (smaller) spur profile, so neighbouring spurs reach towards each
    other; where two spurs would meet, the later one is trimmed to keep one clear pixel.
    specs[i] = (H, W, top, extra letter() kwargs); top is the letter's top row in word
    coordinates. Returns (mask, labels, spans, y0): labels holds each pixel's letter index
    (-1 empty) and mask row 0 is word row y0."""
    parts = []
    for ch, (H, W, top, ex) in zip(text, specs):
        a = dict(kw)
        a.update(ex)
        s_, t_ = a.pop("S", S), a.pop("T", T)
        m = letter(ch, H, W, s_, t_, raw=True, **a)
        if kprof is not None:
            a["prof"] = kprof
        km = letter(ch, H, W, s_, t_, raw=True, **a)
        used = np.nonzero((m | km).any(axis=0))[0]
        c0, c1 = used[0], used[-1] + 1
        parts.append((m[:, c0:c1], km[:, c0:c1], top))
    y0 = min(t for _, _, t in parts)
    Hw = max(t + m.shape[0] for m, _, t in parts) - y0
    Ww = sum(m.shape[1] for m, _, _ in parts) + gmin * len(parts) + 4
    mask = np.zeros((Hw, Ww), dtype=bool)
    kmask = np.zeros((Hw, Ww), dtype=bool)
    labels = np.full((Hw, Ww), -1, dtype=int)
    spans = []
    for i, (m, km, t) in enumerate(parts):
        h, w = m.shape
        y = t - y0
        x = 0
        if spans:
            grown = kmask
            for _ in range(gmin):
                grown = dilate(grown)
            x = spans[-1][0]
            while (grown[y:y + h, x:x + w] & km).any():
                x += 1
            near = dilate(mask)                 # keep one clear pixel between letters
            m = m & ~near[y:y + h, x:x + w]
        mask[y:y + h, x:x + w] |= m
        kmask[y:y + h, x:x + w] |= km
        labels[y:y + h, x:x + w][m] = i
        spans.append((x, x + w - 1))
    right = spans[-1][1] + 1
    return mask[:, :right], labels[:, :right], spans, y0


def dilate(m, diag=True):
    o = m.copy()
    o[1:, :] |= m[:-1, :]
    o[:-1, :] |= m[1:, :]
    o[:, 1:] |= m[:, :-1]
    o[:, :-1] |= m[:, 1:]
    if diag:
        o[1:, 1:] |= m[:-1, :-1]
        o[1:, :-1] |= m[:-1, 1:]
        o[:-1, 1:] |= m[1:, :-1]
        o[:-1, :-1] |= m[1:, 1:]
    return o


def erode(m, diag=True):
    return ~dilate(~m, diag)


def blob(rng, x, y, size):
    """An irregular 4-connected cluster of `size` pixels grown from (x, y)."""
    pts = [(x, y)]
    seen = {(x, y)}
    while len(pts) < size:
        bx, by = rng.choice(pts)
        dx, dy = rng.choice(((1, 0), (-1, 0), (0, 1), (0, -1), (1, 0), (0, 1)))
        q = (bx + dx, by + dy)
        if q not in seen:
            seen.add(q)
            pts.append(q)
    return pts


def value_noise(rng, w, h, cell):
    """Blocky low-frequency noise in 0..1 (bilinear between seeded lattice values)."""
    gw, gh = w // cell + 2, h // cell + 2
    lat = np.array([[rng.random() for _ in range(gw)] for _ in range(gh)])
    ys, xs = np.mgrid[0:h, 0:w]
    fx, fy = xs / cell, ys / cell
    x0, y0 = fx.astype(int), fy.astype(int)
    tx, ty = fx - x0, fy - y0
    a = lat[y0, x0] * (1 - tx) + lat[y0, x0 + 1] * tx
    b = lat[y0 + 1, x0] * (1 - tx) + lat[y0 + 1, x0 + 1] * tx
    return a * (1 - ty) + b * ty


def soak_line(rng, w, base, amp, spikes, smin=3, smax=9):
    """Per-column top of a ragged 'soaked from below' zone: a wandering line with spikes."""
    line = []
    v = 0.0
    for x in range(w):
        v += rng.uniform(-1.2, 1.2)
        v = max(-amp, min(amp, v * 0.85))
        line.append(base + v)
    line = np.array(line)
    for _ in range(spikes):  # flame-like tongues: tapering triangles
        x = rng.randint(0, w - 1)
        ln = rng.randint(smin, smax)
        wd = rng.choice((1, 2, 3, 3, 4, 5))
        for i in range(-wd, wd + 1):
            if 0 <= x + i < w:
                line[x + i] = min(line[x + i], base + 1 - ln * (1 - abs(i) / (wd + 1.0)))
    return np.round(line).astype(int)


def fill_holes(m):
    """Fill every region of ~m that the border cannot reach (4-connected)."""
    outside = np.zeros_like(m)
    outside[0, :] = ~m[0, :]
    outside[-1, :] = ~m[-1, :]
    outside[:, 0] = ~m[:, 0]
    outside[:, -1] = ~m[:, -1]
    while True:
        grown = dilate(outside, diag=False) & ~m
        if (grown == outside).all():
            break
        outside = grown
    return ~outside


def despeckle8(cols, region, passes=2):
    """Inside `region`, a pixel with no 8-neighbour of its own colour takes the colour most of
    its neighbours have, so every texture mark is a cluster of two or more pixels."""
    h, w = cols.shape
    for _ in range(passes):
        changed = 0
        for y, x in zip(*np.nonzero(region)):
            n = cols[y, x]
            nb = []
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if (dy or dx) and 0 <= y + dy < h and 0 <= x + dx < w and cols[y + dy, x + dx] != "":
                        nb.append(cols[y + dy, x + dx])
            if nb and n not in nb:
                cols[y, x] = max(sorted(set(nb)), key=nb.count)
                changed += 1
        if not changed:
            break


def despeckle(cols, mask, name, base):
    """Revert isolated single pixels of `name` (no 4-neighbour of the same colour) to base."""
    h, w = cols.shape
    for y in range(h):
        for x in range(w):
            if mask[y, x] and cols[y, x] == name:
                n = 0
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < w and 0 <= yy < h and cols[yy, xx] == name:
                        n += 1
                if n == 0:
                    cols[y, x] = base


def draw_font_text(img, text, x, y, col, rows=gen_fonts.BODY_ROWS, bold=True):
    for ch in text:
        if ch == " ":
            x += gen_fonts.BODY_SPACE
            continue
        bm = gen_fonts.pad(gen_fonts.BODY[ch], rows)
        if bold:
            bm = gen_fonts.embolden(bm)
        for ry, r in enumerate(bm):
            for rx, c in enumerate(r):
                if c == "#":
                    img.putpixel((x + rx, y + ry), col)
        x += len(bm[0]) + 1
    return x


def text_width(text):
    w = 0
    for ch in text:
        w += gen_fonts.BODY_SPACE if ch == " " else len(gen_fonts.BODY[ch][0]) + 2
    return w - 1


def outline_rgba(img):
    a = np.array(img)[:, :, 3] > 0
    o = dilate(a) & ~a
    ys, xs = np.nonzero(o)
    for y, x in zip(ys, xs):
        img.putpixel((int(x), int(y)), C("INK"))


# ----------------------------------------------------------------------------------------

def gen_palette():
    im = Image.new("RGBA", (len(P.NAMES), 2))
    for t in (0, 1):
        for i, c in enumerate(P.row(float(t))):
            im.putpixel((i, t), c + (255,))
    im.save(os.path.join(ROOT, "assets", "palette.png"))
    with open(os.path.join(ROOT, "assets", "palette_names.txt"), "w") as f:
        f.write("\n".join(P.NAMES) + "\n")


# AT, cut by hand at 12 rows: a flat-topped A on slab feet, a T whose bar ends flare down
# (fishtails) with a small spur on its stem
AT_A = ("....#####....",
        "....#####....",
        "...###.###...",
        "...###.###...",
        "..###...###..",
        "..###...###..",
        "..#########..",
        ".##########..",
        ".###.....###.",
        ".###.....###.",
        "#####...#####",
        "#####...#####")
AT_T = ("############",
        "############",
        "##..####..##",
        "#...####...#",
        "....####....",
        "...######...",
        "....####....",
        "....####....",
        "....####....",
        "....####....",
        "..########..",
        "..########..")
STAR = ("..#..",
        "..#..",
        ".###.",
        "##.##",
        ".###.",
        "..#..",
        "..#..")


def close_mask(m, r):
    """Morphological closing: fills cracks and bays narrower than about 2r."""
    o = m
    for i in range(r):
        o = dilate(o, diag=(i % 2 == 0))
    for i in range(r):
        o = erode(o, diag=(i % 2 == 0))
    return o | m


def dist_field(m, n):
    """Steps from m (alternating 4- and 8-neighbour growth, a near-octagonal metric)."""
    d = np.full(m.shape, 99, dtype=int)
    d[m] = 0
    cur = m.copy()
    for k in range(1, n + 1):
        cur = dilate(cur, diag=(k % 2 == 0))
        d[cur & (d == 99)] = k
    return d


def put(cols, x, y, name):
    h, w = cols.shape
    if 0 <= y < h and 0 <= x < w:
        cols[y, x] = name


def gen_logo():
    """Distressed red BLOOD over blood-spattered cream SUNDOWN, AT between tapered rules, all
    on a ragged ink splatter that hugs the lettering, with blood soaking out of its lower
    edge and dripping off it. Laid out after concept B: B and D stand taller than L O O, the
    first S and last N of SUNDOWN rise to the AT rules, and the letters interlock."""
    rng = random.Random(1873)
    Wc, Hc = 250, 200
    CX = Wc // 2
    cols = np.full((Hc, Wc), "", dtype=object)
    yy_, xx_ = np.mgrid[0:Hc, 0:Wc]

    # --- words -----------------------------------------------------------------------------
    oy = 24          # cap top of BLOOD's short letters; B and D rise 5 px above and drop 4
    sy = 96          # cap top of SUNDOWN's short letters; the S and last N rise 10 and 11 px
    bspec = [(60, 35, -5, dict(cw=8)), (50, 28, 1 + rng.randint(0, 1), {}),
             (51, 30, rng.randint(0, 1), dict(cw=5)), (51, 30, rng.randint(0, 1), dict(cw=5)),
             (60, 34, -5, dict(cw=8))]
    # spaced on the spur-less bodies, so the mid-stem spurs of neighbours nearly meet
    blood, _blab, bsp, by0 = kern_word("BLOOD", bspec, 12, 7, 3, kprof=(0,), ser=3, sr=5,
                                       prof=(1, 1, 2, 2, 3, 2, 2, 1, 1))
    sspec = ([(50, 26, -10, {})] + [(39, w, rng.randint(0, 1), {}) for w in (24, 24, 23, 20, 27)]
             + [(50, 26, -11, {})])
    sundown, _slab, ssp, sy0 = kern_word("SUNDOWN", sspec, 8, 5, 1, ser=2, sr=4,
                                         prof=(1, 1, 2, 1, 1), cw=5)
    bx, sx = CX - blood.shape[1] // 2, CX - sundown.shape[1] // 2
    lb = np.zeros((Hc, Wc), dtype=bool)
    lb[oy + by0: oy + by0 + blood.shape[0], bx: bx + blood.shape[1]] = blood
    ls = np.zeros((Hc, Wc), dtype=bool)
    ls[sy + sy0: sy + sy0 + sundown.shape[0], sx: sx + sundown.shape[1]] = sundown
    letters = lb | ls
    bspan = [(bx + a, bx + b) for a, b in bsp]
    sspan = [(sx + a, sx + b) for a, b in ssp]

    # --- AT between tapered rules with four-point stars ----------------------------------
    at_y, AH = 81, 12
    am = np.array([[c == "#" for c in r] for r in AT_A])
    tm = np.array([[c == "#" for c in r] for r in AT_T])
    at_m = np.zeros((AH, am.shape[1] + tm.shape[1]), dtype=bool)
    at_m[:, :am.shape[1]] = am
    at_m[:, am.shape[1]:] |= tm           # the T tucks against the A's right foot
    ax = CX - at_m.shape[1] // 2
    at = np.zeros((Hc, Wc), dtype=bool)
    at[at_y: at_y + AH, ax: ax + at_m.shape[1]] = at_m
    at_x0, at_x1 = ax, ax + at_m.shape[1] - 1
    ry = at_y + AH // 2 - 1
    orn = []                                   # (x, y, colour) drawn last
    rule_len = 31
    for side in (-1, 1):
        edge = at_x0 if side < 0 else at_x1
        scx = edge + side * 6                  # star centre: 3 px gap, then the 5 px star
        for j, row in enumerate(STAR):
            for i, c in enumerate(row):
                if c == "#":
                    orn.append((scx - 2 + i, ry - 3 + j, "CREAM"))
        orn.append((scx, ry, "INK"))
        r0 = scx + side * 5
        for i in range(rule_len):
            x = r0 + side * i
            if i < 12:                          # 2 px next to the star
                orn.append((x, ry, "CREAM"))
                orn.append((x, ry + 1, "SAND"))
            elif i < 22:                        # thinning to 1 px, then TAN to the point
                orn.append((x, ry, "CREAM" if i < 17 else "SAND"))
            else:
                orn.append((x, ry, "TAN"))
    rx0 = min(p[0] for p in orn)
    rx1 = max(p[0] for p in orn)
    band = np.zeros((Hc, Wc), dtype=bool)
    band[at_y - 1: at_y + AH + 1, rx0 - 1: rx1 + 2] = True
    # one mass between the words
    band[oy + 44: sy + 4, bspan[0][0] + 6: bspan[-1][1] - 5] = True

    # --- ink splatter backing that hugs the letters ------------------------------------
    core = close_mask(letters | at | band, 6)
    dist = dist_field(core, 14)
    nz = value_noise(rng, Wc, Hc, 5)
    nz2 = value_noise(rng, Wc, Hc, 2)
    base = np.where(yy_ < oy + 8, 3, 4)          # a thin hug over the tops of BLOOD
    reach = base + np.round(nz * 2.4 + nz2 * 1.2 - 1.3).astype(int)
    backing = (dist <= np.maximum(reach, 3)) | core
    edge_pts = sorted(zip(*np.nonzero(backing & ~erode(backing, diag=False))))

    def nearest_edge(tx, ty):
        return min(edge_pts, key=lambda p: (p[1] - tx) ** 2 + (p[0] - ty) ** 2)

    B0, B1 = bspan[0][0], bspan[-1][1]
    S0, S1 = sspan[0][0], sspan[-1][1]

    def free(q, r):
        """Inside the logo's box: 100 px either side of the axis, at most 8 rows above B and
        D, and clear of the crow's beak (native x 232) beside the top of the last N."""
        if not (0 <= q < Wc and oy - 13 <= r < Hc) or abs(q - CX) > 100:
            return False
        return not (sy - 10 <= r <= sy + 14 and q > CX + 94)

    # corner lobes: left of B, right of D, left of S, right of the last N (below the crow)
    lobes = [(B0 - 3, oy + 14, 34, -1), (B0 - 2, oy + 40, 24, -1), (B1 + 3, oy + 8, 36, 1),
             (B1 + 2, oy + 34, 30, 1), (S0 - 3, sy + 6, 38, -1), (S0 - 2, sy + 30, 24, -1),
             (S1 + 1, sy + 33, 26, 1)]
    for tx, ty, size, side in lobes:
        ey, ex = nearest_edge(tx, ty)
        splat = blob(rng, ex + side * 3, ey, size)
        splat += blob(rng, ex + side * 5, ey + rng.randint(-3, 3), size // 3)
        cx_, cy_ = ex + side * 4, ey
        for _ in range(rng.randint(2, 3)):     # prongs thrown out of the splat
            ang = np.radians(rng.uniform(-55, 55))
            ux, uy = side * np.cos(ang), np.sin(ang)
            ln = rng.randint(4, 7)
            for i in range(ln):
                q, r = int(round(cx_ + ux * (3 + i))), int(round(cy_ + uy * (3 + i)))
                splat.append((q, r))
                if i < ln // 2:
                    splat.append((q, r + 1) if abs(ux) > abs(uy) else (q + 1, r))
            q, r = int(round(cx_ + ux * (ln + 4))), int(round(cy_ + uy * (ln + 4)))
            splat += [(q, r), (q + 1, r), (q, r + 1), (q + 1, r + 1)]
        for (q, r) in splat:
            if free(q, r):
                backing[r, q] = True
    backing = fill_holes(backing)

    # --- wet blood soaking out of the lower edge under SUNDOWN -------------------------
    ol = dilate(dilate(ls))
    wet = np.zeros((Hc, Wc), dtype=bool)
    wet_top, wet_bot = {}, {}
    xr = range(S0 - 4, S1 + 5)
    bump = np.zeros(Wc)
    for _ in range(9):                          # lumps where the blood gathers
        c, hw, hh = rng.randint(S0, S1), rng.randint(2, 4), rng.choice((1, 1, 2))
        for x in range(c - hw, c + hw + 1):
            bump[x] = max(bump[x], hh * (1 - ((x - c) / (hw + 1.0)) ** 2))
    v = 0.0
    for x in xr:
        rows = [np.nonzero(ol[:, c])[0] for c in range(x - 2, x + 3) if ol[:, c].any()]
        if not rows:
            continue
        ob = max(r[-1] for r in rows)
        v += rng.uniform(-0.9, 0.9)
        v = max(-1.2, min(1.2, v * 0.8))
        edge_fade = min(x - (S0 - 4), S1 + 4 - x)
        dep = min(7, max(4, int(round(4.8 + v + bump[x])))) - max(0, 4 - edge_fade)
        if dep < 2:
            continue
        wet[ob + 1: ob + 1 + dep, x] = True
        wet_top[x], wet_bot[x] = ob + 1, ob + dep
    backing |= wet

    cols[backing] = "INK"
    ring = backing & ~erode(backing, diag=False)
    for y, x in zip(*np.nonzero(ring & ~wet)):
        if nz2[y, x] > 0.5:
            cols[y, x] = "WINE_DARK"
    # the soak: WINE_DARK against the ink, WINE through the middle with MAROON patches,
    # MAROON along the wet lower edge with BLOOD shine; colours come in runs, never lone
    run_name, run_left = "WINE", 0
    for x in sorted(wet_bot):
        t, bt = wet_top[x], wet_bot[x]
        for y in range(t, bt + 1):
            cols[y, x] = "WINE"
        if bt - t >= 3:
            cols[t, x] = "WINE_DARK"
        if run_left <= 0:
            run_name = rng.choice(("MAROON", "MAROON", "MAROON", "BLOOD", "WINE"))
            run_left = rng.randint(2, 5)
        run_left -= 1
        cols[bt, x] = run_name
    for _ in range(14):
        x = rng.choice(sorted(wet_bot))
        y = rng.randint(wet_top[x] + 1, max(wet_top[x] + 1, wet_bot[x] - 1))
        for (q, r) in blob(rng, x, y, rng.randint(2, 5)):
            if wet[r, q] and r < wet_bot[q]:
                cols[r, q] = "MAROON"

    # --- drips hanging off the wet edge, in clusters ------------------------------------
    drips = np.zeros((Hc, Wc), dtype=bool)
    sp = sspan
    drip_spec = [  # (x, top width, length)
        (sp[0][0] + 4, 2, 9), (sp[0][0] + 9, 3, 16),
        (sp[1][1] - 3, 1, 4),
        (sp[2][0] + 6, 2, 6),
        (sp[3][0] + 5, 3, 12), (sp[3][1] - 3, 2, 5), (sp[4][0] + 6, 2, 10),
        (sp[5][0] + 8, 1, 3), (sp[5][1] - 8, 2, 8),
        (sp[6][0] + 6, 4, 17), (sp[6][0] + 11, 2, 7), (sp[6][1] - 4, 1, 4)]
    shine = []
    body = {4: ("WINE", "MAROON", "WINE", "WINE_DARK"), 3: ("WINE", "MAROON", "WINE_DARK"),
            2: ("WINE", "WINE_DARK"), 1: ("WINE",)}
    for x, w0, ln in drip_spec:
        x += rng.randint(-1, 1)
        if x not in wet_bot:
            continue
        top_y = wet_bot[x] + 1
        taper = max(1, int(ln * 0.5))
        for j in range(ln):
            w = max(1, w0 - (j * w0) // taper) if j < taper else 1
            c0 = x - (w - 1) // 2
            for i, c in enumerate(range(c0, c0 + w)):
                name = body[w][i]
                if j < 3 and i == (w - 1) // 2 and w <= 2:
                    name = "MAROON"             # the core highlight near the neck
                put(cols, c, top_y + j, name)
                drips[top_y + j, c] = True
        if w0 >= 2:                             # the rim swells where a drip leaves it
            for c in (x - (w0 - 1) // 2 - 1, x + w0 // 2 + 1):
                if c in wet_bot and wet_bot[c] < top_y:
                    put(cols, c, top_y, cols[wet_bot[c], c])
                    drips[top_y, c] = True
        yb = top_y + ln
        if ln >= 6:                             # bulb
            bw = 3 if w0 >= 3 else 2
            c0 = x - (bw - 1) // 2
            for c in range(c0, c0 + bw):
                for y in (yb, yb + 1):
                    put(cols, c, y, "WINE_DARK")
                    drips[y, c] = True
            shine.append((c0, yb))

    # --- streaks and spatter around the splatter ---------------------------------------
    solid = backing | drips
    out_d = dist_field(solid, 9)
    cy_mid = (oy + sy) // 2
    rim = sorted(zip(*np.nonzero(solid & ~erode(solid, diag=False) & ~wet)))
    placed = tries = 0
    while placed < 10 and tries < 600:          # radial 1 px streaks ending in 2x2 dots
        tries += 1
        y, x = rim[rng.randrange(len(rim))]
        dx, dy = x - CX, (y - cy_mid) * 1.6
        n = max(1e-6, (dx * dx + dy * dy) ** 0.5)
        ux, uy = dx / n, dy / n
        if y > sy + 30 or abs(ux) < 0.35 and uy > 0:
            continue
        ln = rng.randint(3, 7)
        pts = [(int(round(x + ux * i)), int(round(y + uy * i))) for i in range(1, ln + 1)]
        ex_, ey_ = pts[-1]
        dot = [(ex_ + a, ey_ + b) for a in (0, 1) for b in (0, 1)]
        if any(not free(q, r) or out_d[r, q] < 1 for q, r in pts + dot):
            continue
        if out_d[ey_, ex_] > 8:
            continue
        for q, r in pts + dot:
            cols[r, q] = "INK"
        placed += 1
    out_d = dist_field(cols != "", 9)
    cand = sorted(zip(*np.nonzero((out_d >= 2) & (out_d <= 4))))
    placed = tries = 0
    while placed < 40 and tries < 6000:         # flecks thrown off the splatter
        tries += 1
        y, x = cand[rng.randrange(len(cand))]
        if y > sy + 36 or y < 4:
            continue
        shape = rng.choice(((1, 0), (0, 1), (1, 0), (1, 1)))
        if shape == (1, 1):
            pts = [(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)]
        else:
            pts = [(x, y), (x + shape[0], y + shape[1])]
        if any(not free(q, r) or out_d[r, q] < 2 for q, r in pts):
            continue
        name = "INK" if rng.random() < 0.85 else "WINE_DARK"
        for q, r in pts:
            cols[r, q] = name
        placed += 1
    # bright red droplets flicked off the top left of B and the right of D: round drops
    # with a light top left pixel and an ink shadow on their lower right
    drop_shapes = {4: ("##", "##"), 7: (".##", "###", "##."), 12: (".##.", "####", "####", ".##.")}
    for tx, ty, size in ((B0 - 7, oy + 2, 7), (B0 - 8, oy + 24, 4), (B1 + 8, oy + 12, 12),
                         (B1 + 12, oy + 5, 4), (B1 + 7, oy + 32, 7)):
        shape = drop_shapes[size]
        for _t in range(120):
            x = tx + rng.randint(-3, 3)
            y = ty + rng.randint(-4, 4)
            drop = [(x + i, y + j) for j, row in enumerate(shape) for i, c in enumerate(row) if c == "#"]
            ds = set(drop)
            shadow = {(q + a, r + b) for q, r in drop for a, b in ((1, 0), (0, 1), (1, 1))} - ds
            if all(free(q, r) and out_d[r, q] >= 2 for q, r in ds | shadow):
                break
        else:
            continue
        for q, r in shadow:
            if cols[r, q] == "":
                cols[r, q] = "INK"
        for q, r in drop:
            cols[r, q] = "RED"
        q, r = min(drop, key=lambda p: (p[1], p[0]))
        cols[r, q] = "RED_LIGHT"
        if size >= 7:
            q, r = max(drop, key=lambda p: (p[1], p[0]))
            cols[r, q] = "BLOOD"
        out_d[max(0, y - 5): y + 6, max(0, x - 5): x + 6] = 0   # keep droplets apart

    # --- BLOOD: bright red, distressed, soaked dark from below ------------------------
    ys_, xs_ = np.nonzero(lb)
    cols[lb] = "RED"
    soak = soak_line(rng, Wc, oy + 32, 2.5, 46, 4, 14)
    for (x0, x1) in bspan:                      # each letter soaked to its own depth
        soak[x0: x1 + 1] += rng.randint(-2, 2)
    for y, x in zip(ys_, xs_):
        if y >= soak[x]:
            cols[y, x] = "BLOOD"
    area = int(lb.sum())
    upper = [(x, y) for y, x in zip(ys_, xs_) if y < soak[x] - 1]
    lower = [(x, y) for y, x in zip(ys_, xs_) if y >= soak[x] + 2]

    def splash(pool, count, name, smin, smax, where, over=None):
        for _ in range(count):
            x, y = pool[rng.randrange(len(pool))]
            for (px_, py_) in blob(rng, x, y, rng.randint(smin, smax)):
                if 0 <= py_ < Hc and 0 <= px_ < Wc and where[py_, px_]:
                    if over is None or cols[py_, px_] in over:
                        cols[py_, px_] = name

    near_up = [(x, y) for (x, y) in upper if y >= soak[x] - 8]
    near_lo = [(x, y) for (x, y) in lower if y < soak[x] + 7]
    splash(upper, area * 1 // 100 // 5, "BLOOD", 2, 5, lb, ("RED",))
    splash(near_up, area * 2 // 100 // 4, "BLOOD", 2, 6, lb, ("RED",))
    splash(lower, area * 2 // 100 // 3, "MAROON", 2, 5, lb, ("BLOOD",))
    splash(near_lo, area * 2 // 100 // 3, "RED", 2, 4, lb, ("BLOOD",))
    up_half = [(x, y) for (x, y) in upper if y < oy + 26]
    for _ in range(area * 3 // 200 // 3):       # small light flecks, upper half only
        x, y = up_half[rng.randrange(len(up_half))]
        pts = blob(rng, x, y, rng.randint(2, 3))
        if all(lb[py_, px_] and cols[py_, px_] == "RED" for (px_, py_) in pts):
            for (px_, py_) in pts:
                cols[py_, px_] = "RED_LIGHT"
    # broken 1 px highlight along the tops and down the left edges, above the soak
    tops = lb & ~np.roll(lb, 1, axis=0)
    lefts = lb & ~np.roll(lb, 1, axis=1)

    def broken(pts):
        run = gap = 0
        lim = rng.randint(3, 6)
        prev = None
        for (x, y) in pts:
            if prev is not None and abs(x - prev[0]) + abs(y - prev[1]) > 1:
                run = 0
            prev = (x, y)
            if gap > 0:
                gap -= 1
                continue
            cols[y, x] = "RED_LIGHT"
            run += 1
            if run >= lim:
                run, gap, lim = 0, rng.randint(1, 3), rng.randint(3, 6)

    broken([(x, y) for y, x in zip(*np.nonzero(tops)) if y < soak[x] - 2])
    broken(sorted(((x, y) for y, x in zip(*np.nonzero(lefts & ~tops)) if y < soak[x] - 3),
                  key=lambda p: (p[0], p[1])))
    for _ in range(area * 1 // 200 // 2):       # ink scratches
        i = rng.randrange(len(xs_))
        x, y = int(xs_[i]), int(ys_[i])
        pts = blob(rng, x, y, rng.choice((2, 2, 3)))
        if all(lb[py_ + a, px_ + b] for (px_, py_) in pts
               for a, b in ((0, 0), (0, 1), (0, -1), (1, 0), (-1, 0))):
            for (px_, py_) in pts:
                cols[py_, px_] = "INK"
    despeckle(cols, lb, "BLOOD", "RED")
    despeckle(cols, lb, "MAROON", "BLOOD")

    # short drips from the bottom of BLOOD into the AT gap, clear of AT and its rules
    cand = []
    for x in range(Wc):
        if not lb[:, x].any():
            continue
        yb = np.nonzero(lb[:, x])[0][-1]
        if lb[yb, x - 1] and lb[yb, x + 1] and not (at_x0 - 10 <= x <= at_x1 + 10):
            cand.append((x, yb))
    rng.shuffle(cand)
    used = []
    for x, yb in cand:
        if len(used) >= 5:
            break
        if any(abs(x - u) < 12 for u in used):
            continue
        ln = min(rng.randint(3, 7), ry - 3 - yb)
        if ln < 3:
            continue
        used.append(x)
        name = "BLOOD" if rng.random() < 0.6 else "RED"
        for y in range(yb + 1, yb + ln + 1):
            cols[y, x] = name
        for y in range(yb + 1, yb + max(2, ln - 1)):
            cols[y, x + 1] = name

    # --- SUNDOWN: sandy cream, soaked tan from below, spattered with blood -------------
    ys_, xs_ = np.nonzero(ls)
    cols[ls] = "CREAM"
    soak1 = soak_line(rng, Wc, sy + 12, 3.0, 50, 2, 8)
    soak2 = soak_line(rng, Wc, sy + 22, 2.5, 44, 2, 8)
    for y, x in zip(ys_, xs_):
        if y >= soak2[x]:
            cols[y, x] = "TAN"
        elif y >= soak1[x]:
            cols[y, x] = "SAND"
    area = int(ls.sum())
    upper = [(x, y) for y, x in zip(ys_, xs_) if y < soak1[x] - 1]
    mid = [(x, y) for y, x in zip(ys_, xs_) if soak1[x] + 1 <= y < soak2[x] - 1]
    lower = [(x, y) for y, x in zip(ys_, xs_) if y >= soak2[x] + 1]
    splash(upper, area * 18 // 100 // 6, "SAND", 4, 9, ls, ("CREAM",))
    splash(mid, area * 4 // 100 // 5, "CREAM", 3, 7, ls, ("SAND",))
    splash(mid, area * 4 // 100 // 5, "TAN", 3, 7, ls, ("SAND",))
    splash(lower, area * 3 // 100 // 4, "SAND", 3, 5, ls, ("TAN",))
    despeckle(cols, ls, "SAND", "CREAM")
    despeckle(cols, ls, "TAN", "SAND")
    despeckle(cols, ls, "CREAM", "SAND")
    rgt = ls & ~np.roll(ls, -1, axis=1)
    bot = ls & ~np.roll(ls, -1, axis=0)
    for y, x in zip(*np.nonzero(rgt | bot)):
        cols[y, x] = "TAN" if cols[y, x] in ("SAND", "TAN") else "CREAM_SHADE"
    pool = [(x, y) for y, x in zip(ys_, xs_)]
    # splash centres: always one high on the first S and one on the last N
    centres = [(sspan[0][0] + 7, sy - 4), (sspan[-1][1] - 6, sy - 5)]
    tries = 0
    while len(centres) < 7 and tries < 3000:
        tries += 1
        x, y = pool[rng.randrange(len(pool))]
        if all(abs(x - cx) > 18 for cx, _ in centres):
            centres.append((x, y))
    for k_, (cx, cy) in enumerate(centres):   # the S and N get the heaviest splats
        big = k_ < 2
        for (px_, py_) in blob(rng, cx, cy, rng.randint(18, 24) if big else rng.randint(8, 14)):
            if ls[py_, px_]:
                cols[py_, px_] = "BLOOD"
        for (px_, py_) in blob(rng, cx, cy, 6 if big else 3):
            if ls[py_, px_]:
                cols[py_, px_] = "MAROON"
    for i in range(44):
        cx, cy = centres[i % len(centres)]
        for _ in range(30):
            x = int(round(cx + rng.gauss(0, 6)))
            y = int(round(cy + rng.gauss(0, 7)))
            if 0 <= y < Hc and 0 <= x < Wc and ls[y, x]:
                break
        name = "RED" if rng.random() < 0.6 else "BLOOD"
        for (px_, py_) in blob(rng, x, y, rng.randint(2, 3)):
            if ls[py_, px_]:
                cols[py_, px_] = name
    feet = ls & ~np.roll(ls, -1, axis=0)
    fy, fx = np.nonzero(feet)
    order = sorted(zip(fx, fy))
    i = 0
    while i < len(order):
        if rng.random() < 0.3:
            ln = rng.randint(2, 5)
            for j in range(i, min(len(order), i + ln)):
                x_, y_ = order[j]
                cols[y_, x_] = "BLOOD" if rng.random() < 0.7 else "MAROON"
            i += ln
        i += rng.randint(2, 6)
    for i in range(5):
        for _ in range(50):
            x, y = pool[rng.randrange(len(pool))]
            ln = rng.randint(3, 6)
            if all(ls[y + k, x] for k in range(ln + 1)):
                break
        for k in range(ln):
            cols[y + k, x] = "BLOOD"
        side = rng.choice((-1, 1))
        if ls[y, x + side]:
            cols[y, x + side] = "BLOOD"
        if ls[y + ln, x]:
            cols[y + ln, x] = "MAROON"

    # no lone pixels in the letter fills or on the splatter
    despeckle8(cols, lb | ls)
    despeckle8(cols, backing & ~(lb | ls) & ~dilate(lb | ls) & ~wet)
    despeckle8(cols, wet | drips)
    for (x, y) in shine:                        # one wet highlight on each drip's bulb
        cols[y, x] = "BLOOD"

    # --- AT and its ornaments on top ------------------------------------------------------
    for y, x in zip(*np.nonzero(at)):
        cols[y, x] = "SAND" if y >= at_y + AH - 2 else "CREAM"
    for (x, y, name) in orn:
        cols[y, x] = name

    # --- to RGBA, cropped symmetric about the letters' axis ------------------------------
    img = Image.new("RGBA", (Wc, Hc), (0, 0, 0, 0))
    ys_, xs_ = np.nonzero(cols != "")
    for y, x in zip(ys_, xs_):
        img.putpixel((int(x), int(y)), C(cols[y, x]))
    x0, y0, x1, y1 = img.getbbox()
    half = max(CX - x0, x1 - CX)
    img = img.crop((CX - half, y0, CX + half, y1))
    if img.width > 206 or img.height > 152:
        print("warning: logo larger than 206 x 152:", img.size)
    img.save(os.path.join(ROOT, "assets", "ui", "logo.png"))
    print("logo", img.size)


def gen_icon():
    s = 48
    img = Image.new("RGBA", (s, s), C("SKY_TOP"))
    d = ImageDraw.Draw(img)
    bands = [("SKY_TOP", 0), ("SKY_HIGH", 9), ("SKY_MID", 17), ("SKY_LOW", 23), ("HORIZON", 28)]
    for name, y in bands:
        d.rectangle((0, y, s, s), fill=C(name))
    d.ellipse((17, 18, 33, 34), fill=C("SUN"))
    d.rectangle((0, 31, s, s), fill=C("PLUM"))
    d.polygon([(0, 31), (6, 26), (12, 27), (14, 31)], fill=C("PLUM"))
    d.polygon([(34, 31), (37, 25), (44, 25), (47, 31)], fill=C("PLUM"))
    d.rectangle((0, 35, s, s), fill=C("OCHRE"))
    # player from behind: hat and poncho shoulders
    d.polygon([(4, 48), (10, 36), (24, 33), (38, 36), (44, 48)], fill=C("TEAL"))
    d.rectangle((6, 42, 42, 43), fill=C("GOLD"))
    for x in range(8, 41, 3):
        d.point((x, 44), fill=C("CREAM"))
    d.rectangle((18, 30, 30, 34), fill=C("SKIN_DARK"))
    d.ellipse((8, 26, 40, 31), fill=C("CHARCOAL"))
    d.rectangle((15, 19, 33, 28), fill=C("CHARCOAL"))
    d.rectangle((15, 25, 33, 26), fill=C("LEATHER"))
    d.rectangle((15, 19, 33, 19), fill=C("RIM"))
    img = img.resize((192, 192), Image.NEAREST)
    img.save(os.path.join(ROOT, "icon.png"))


def gen_scene():
    out = os.path.join(ROOT, "assets", "world")
    os.makedirs(out, exist_ok=True)
    comp = art_scene.build(out)
    preview = os.environ.get("SCENE_PREVIEW")
    if preview:
        comp.save(preview)


def main():
    gen_palette()
    gen_scene()
    gen_logo()
    gen_icon()


if __name__ == "__main__":
    main()
