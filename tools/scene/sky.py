"""Sky: dithered bands with wavy seams, clumpy crimson cloud masses that radiate from the
sunset, the flat golden sun with a stepped halo and the red cloud masses across its lower part.

Everything is drawn into a grid of palette indices over the whole layer (safe coordinates, the
overscan added on write), then written to the Layer in one go. The grid keeps a cloud mask so
the sun halo only lights bare sky, never the clouds.

A cloud is one or more lenses (long axis along the local slope, tapering to points) whose
edge is roughened by stretched value noise, so each mass has a lumpy top, a flatter belly,
bitten ends and the odd hole. Inside, a second noise field mottles it between the zone's dark,
body and lit colours; the lit colour takes the lower edge, the dark colour the upper edge.
"""
import math

import numpy as np
from PIL import Image, ImageDraw

import palette as P
from scene.common import *  # noqa: F401,F403


# band colour and the safe y where it starts; each seam is an 8-row Bayer step (upper colour
# reaching down) that wanders up and down by a few pixels across the width
SKY_BANDS = [("SKY_TOP", -OY), ("SKY_UPPER", 12), ("SKY_HIGH", 46), ("SKY_MID", 90),
             ("SKY_WARM", 136), ("SKY_LOW", 201), ("HORIZON", 252), ("HORIZON_HOT", 268)]
SEAM_ROWS = 8
SKY_ROWS = 262                        # nothing below this row is ever seen (mesas, town)

# cloud zones by cluster centre: y from, y to, clusters, (dark, body, lit, highlight),
# share of clusters with a lit belly, share with a dark top edge, length range, thickness range.
# The window under the logo (y 138..222) is meant to read crimson: dense RED bodies, the warm
# band showing through only as lighter streaks between them.
CLOUD_ZONES = [
    (-12, 46, 44, ("PLUM", "MAROON", "BLOOD", "RED"), 0.75, 0.45, (18, 42), (8, 13)),
    (46, 90, 34, ("MAROON", "BLOOD", "RED", "RED"), 0.7, 0.4, (20, 44), (8, 13)),
    (90, 138, 16, ("MAROON", "BLOOD", "RED", "RED"), 0.7, 0.35, (26, 60), (6, 10)),
    (138, 192, 42, ("SKY_MID", "RED", "SKY_LOW", "RED_LIGHT"), 0.35, 0.25, (30, 70), (7, 12)),
    (192, 222, 30, ("SKY_MID", "RED", "SKY_LOW", "RED_LIGHT"), 0.6, 0.3, (20, 48), (4, 7)),
]
CLEAR = (128, 190, 186, 222)          # x0, y0, x1, y1 above and beside the disc down to its
                                      # centre row: no mass here, so the glow rings a clean
                                      # upper disc (rows 195..227, its upper 60 percent)
HALO = 19                             # outer radius of the glow past the disc edge
NEAR_SUN = 14                         # clouds this close to the disc edge are lit HORIZON
RUN_CAP = (28, 36)                    # longest solid run in a cloud row before a gap
LENS_TILT = 0.6                       # puff slope as a share of the band slope


class _Grid:
    """Palette-index canvas over the full layer plus a mask of cloud pixels."""

    def __init__(self):
        self.g = np.zeros((H, W), dtype=np.int16)
        self.cloud = np.zeros((H, W), dtype=bool)

    def set(self, x, y, name, cloud=False):
        X, Y = int(x) + OX, int(y) + OY
        if 0 <= X < W and 0 <= Y < H:
            self.g[Y, X] = P.IDX[name]
            self.cloud[Y, X] = cloud

    def name(self, x, y):
        X, Y = int(x) + OX, int(y) + OY
        if 0 <= X < W and 0 <= Y < H:
            return P.NAMES[self.g[Y, X]]
        return None

    def to_layer(self):
        L = Layer()
        lut = np.array([P.rgb(n, 0.0) + (255,) for n in P.NAMES], dtype=np.uint8)
        L.im = Image.fromarray(lut[self.g], "RGBA")
        L.d = ImageDraw.Draw(L.im)
        return L


# ---------------------------------------------------------------- noise and small helpers

def _vnoise(rng, cell_x, cell_y):
    """Smooth value noise in 0..1 over the whole layer, lattice cells cell_x by cell_y."""
    gw, gh = W // cell_x + 3, H // cell_y + 3
    lat = np.array([rng.random() for _ in range(gw * gh)]).reshape(gh, gw)
    xs, ys = np.arange(W) / cell_x, np.arange(H) / cell_y
    x0, y0 = xs.astype(int), ys.astype(int)
    fx, fy = xs - x0, ys - y0
    sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = lat[y0][:, x0], lat[y0][:, x0 + 1]
    c, d = lat[y0 + 1][:, x0], lat[y0 + 1][:, x0 + 1]
    top = a + (b - a) * sx[None, :]
    bot = c + (d - c) * sx[None, :]
    return top + (bot - top) * sy[:, None]


def _wave(rng, amp=3.5):
    """Per-column whole-pixel offset: two slow sines, about +-amp over 40..70 px."""
    p1, p2 = rng.uniform(46, 70), rng.uniform(22, 32)
    f1, f2 = rng.uniform(0, 6.283), rng.uniform(0, 6.283)
    xs = np.arange(W)
    w = 0.68 * amp * np.sin(xs * 6.283 / p1 + f1) + 0.32 * amp * np.sin(xs * 6.283 / p2 + f2)
    return np.floor(w + 0.5).astype(int)


def _nbr(m, dy, dx, fill=False):
    """m shifted so out[y, x] = m[y + dy, x + dx]; edges read as fill."""
    out = np.full(m.shape, fill, dtype=m.dtype)
    h, w = m.shape
    ys, yd = (slice(max(0, dy), h + min(0, dy)), slice(max(0, -dy), h + min(0, -dy)))
    xs, xd = (slice(max(0, dx), w + min(0, dx)), slice(max(0, -dx), w + min(0, -dx)))
    out[yd, xd] = m[ys, xs]
    return out


# ---------------------------------------------------------------- bands

def _bands(G, rng):
    """Full-width bands; each seam wanders by a few pixels and steps down over 8 Bayer rows.
    Keeps a copy of the bare bands for the gaps cut into long cloud runs."""
    top = np.full(W, -OY)
    rows = np.arange(H)[:, None] - OY
    band = np.zeros((H, W), dtype=np.int16)
    seams = []
    for i, (name, y0) in enumerate(SKY_BANDS):
        if i:
            off = _wave(rng, 3.5 if y0 < 250 else 2.0)
            top = y0 + off
            seams.append((i, top))
        band[rows >= top[None, :]] = i
    idx = np.array([P.IDX[n] for n, _ in SKY_BANDS], dtype=np.int16)
    G.g[:, :] = idx[band]
    thr = (BAYER4[np.arange(H)[:, None] % 4, np.arange(W)[None, :] % 4] + 0.5) / 16.0
    for i, top in seams:
        above = P.IDX[SKY_BANDS[i - 1][0]]
        for k in range(SEAM_ROWS):
            lvl = 0.88 - k * (0.76 / (SEAM_ROWS - 1))
            Y = top + k + OY
            ok = (Y >= 0) & (Y < H)
            X = np.nonzero(ok)[0]
            Y = Y[ok]
            hit = thr[Y, X] < lvl
            G.g[Y[hit], X[hit]] = above
    G.band = G.g.copy()


# ---------------------------------------------------------------- cloud masses

def _slope(xc, yc):
    """Streak slope (dy per dx): the clouds radiate from the sunset. Top-left streaks descend to
    the right, top-right ones to the left, about 25..30 degrees in the top corners, easing to
    flat by about y 170."""
    f = min(1.0, max(0.0, (170.0 - yc) / 110.0)) ** 0.7
    return 0.6 * (140 - xc) / 140.0 * f


class _Mass:
    """One cloud: lenses (xc, yc, length, thickness up, thickness down, slope) plus the colours
    it is painted with."""

    def __init__(self, lenses, ramp, lit, dark, rough=0.85, thresh=0.12, hole=True, dark_cut=-0.40):
        self.lenses, self.ramp, self.lit, self.dark = lenses, ramp, lit, dark
        self.dark_cut = dark_cut          # below this shade the inside mottles dark
        self.rough, self.thresh, self.hole = rough, thresh, hole

    def bbox(self, pad=3):
        x0 = min(l[0] - l[2] / 2 for l in self.lenses) - pad
        x1 = max(l[0] + l[2] / 2 for l in self.lenses) + pad
        y0 = min(l[1] - l[3] - abs(l[5]) * l[2] / 2 for l in self.lenses) - pad
        y1 = max(l[1] + l[4] + abs(l[5]) * l[2] / 2 for l in self.lenses) + pad
        return int(math.floor(x0)), int(math.floor(y0)), int(math.ceil(x1)), int(math.ceil(y1))


def _lens_field(X, Y, lenses):
    """Largest lens value at each pixel: 1 on the axis centre, 0 on the outline. The long
    ends taper to points (power 1.5), the top is fuller than the belly."""
    F = np.full(X.shape, -2.0)
    V = np.zeros(X.shape)
    for xc, yc, ln, tu, td, s in lenses:
        u = np.abs(X - xc) / (ln / 2.0)
        dv = Y - (yc + s * (X - xc))
        v = np.where(dv < 0, dv / tu, dv / td)
        b = 1.0 - u ** 1.5 - v * v
        better = b > F
        F = np.where(better, b, F)
        V = np.where(better, v, V)
    return F, V


def _paint_mass(G, M, NZ, MOT):
    """Rasterise one mass: lens field plus edge noise, cleaned of lone pixels, then toned."""
    x0, y0, x1, y1 = M.bbox()
    xs, ys = np.arange(x0, x1 + 1), np.arange(y0, y1 + 1)
    X, Y = np.meshgrid(xs, ys)
    Xg, Yg = np.clip(X + OX, 0, W - 1), np.clip(Y + OY, 0, H - 1)
    F, V = _lens_field(X, Y, M.lenses)
    # the noise runs along the streak, so bites and dabs follow the slope
    xa, s = M.lenses[0][0], M.lenses[0][5]
    Yn = np.clip(Yg - np.floor(s * (X - xa) + 0.5).astype(int), 0, H - 1)
    m = F + M.rough * (NZ[Yn, Xg] - 0.5) > M.thresh
    if not M.hole:                                  # thin wisps: no bites out of the middle
        m |= F > 0.55
    # no lone pixels, no one-pixel holes
    for _ in range(2):
        n4 = (_nbr(m, 0, 1).astype(int) + _nbr(m, 0, -1) + _nbr(m, 1, 0) + _nbr(m, -1, 0))
        m &= ~(m & (n4 == 0))
        m |= (~m) & (n4 == 4)
        # a pixel with no horizontal partner and at most one vertical one goes
        h2 = _nbr(m, 0, 1) | _nbr(m, 0, -1)
        m &= h2 | (_nbr(m, 1, 0) & _nbr(m, -1, 0))
    dark, body, lit, hi = M.ramp
    below_open = ~_nbr(m, 1, 0)
    above_open = ~_nbr(m, -1, 0)
    mot = MOT[Yn, Xg]
    # tone: lighter toward the belly, mottled; the lit colour takes the lower edge
    sh = 0.55 * V + 0.9 * (mot - 0.5)
    out = np.full(m.shape, P.IDX[body], dtype=np.int16)
    out[sh > 0.34] = P.IDX[lit if M.lit else body]
    out[sh > 0.62] = P.IDX[hi if M.lit else body]
    out[sh < M.dark_cut] = P.IDX[dark]
    if M.lit:
        out[below_open & (mot > 0.24)] = P.IDX[lit]      # broken here and there
        # thick masses get a two-row belly in places
        b2 = _nbr(below_open, 1, 0) & (mot > 0.5)
        out[b2 & ~above_open] = P.IDX[lit]
    if M.dark:
        out[above_open & (mot < 0.72)] = P.IDX[dark]
    Gy, Gx = Yg[m], Xg[m]
    inside = (X[m] + OX == Gx) & (Y[m] + OY == Gy)
    G.g[Gy[inside], Gx[inside]] = out[m][inside]
    G.cloud[Gy[inside], Gx[inside]] = True


def _in_clear(M, pad=4):
    x0, y0, x1, y1 = M.bbox(pad)
    cx0, cy0, cx1, cy1 = CLEAR
    return x1 >= cx0 and x0 <= cx1 and y1 >= cy0 and y0 <= cy1


def _plan(rng, xc, yc, zone):
    """A cluster: a main lens and one to three smaller puffs stepped along the band slope."""
    z0, z1, _n, ramp, p_lit, p_dark, lens, thick = zone
    s = _slope(xc, yc)
    sl = s * LENS_TILT                    # each puff is flatter than the band it sits in
    ln = rng.randint(*lens)
    t = rng.uniform(*thick)
    lenses = [(xc, yc, ln, t * 0.62, t * 0.38, sl)]
    dirn = (1 if s > 0 else -1) if abs(s) > 0.08 else rng.choice((-1, 1))
    for _ in range(rng.choice((1, 1, 2, 2, 3))):
        l2 = ln * rng.uniform(0.45, 0.8)
        t2 = t * rng.uniform(0.5, 0.9)
        dx = dirn * rng.uniform(0.35, 0.7) * ln + rng.uniform(-4, 4)
        dy = s * dx + rng.choice((-1, 1)) * rng.uniform(1.5, t * 0.6 + 1)
        lenses.append((xc + dx, yc + dy, l2, t2 * 0.62, t2 * 0.38, sl))
    return _Mass(lenses, ramp, rng.random() < p_lit, rng.random() < p_dark,
                 dark_cut=-0.40 if z0 < 138 else -0.58)


def _clouds(rng):
    """Seeded chains of clusters. Chain heads are spread by jittered slots in x and in y (a
    Latin square) so no stretch of sky is left bare; each chain runs on along the local slope,
    so the corners fill with long diagonal bands. None may enter the clear patch over the sun."""
    masses = []
    for zone in CLOUD_ZONES:
        z0, z1, count = zone[0], zone[1], zone[2]
        # the two low zones are only seen between the facades: keep them near the view
        xl, xr = (-50, SAFE_W + 50) if z0 >= 138 else (-OX, SAFE_W + OX)
        span = xr - xl
        heads = (count + 1) // 2
        ys = [z0 + (j + rng.random()) * (z1 - z0) / heads for j in range(heads)]
        rng.shuffle(ys)
        made = 0
        for i in range(heads):
            xc = xl + (i + rng.random()) * span / heads
            yc = ys[i]
            links = min(count - made, rng.choice((1, 2, 2, 3)))
            dirn = rng.choice((-1, 1))
            for _ in range(links):
                M = _plan(rng, xc, yc, zone)
                if not _in_clear(M):
                    masses.append(M)
                made += 1
                ln = M.lenses[0][2]
                dx = dirn * ln * rng.uniform(0.75, 1.05)
                xc += dx
                yc += _slope(xc, yc) * dx + rng.uniform(-2.5, 2.5)
        while made < count:                       # top up with loose clusters
            for _try in range(40):
                M = _plan(rng, rng.uniform(xl, xr), rng.uniform(z0, z1 - 1), zone)
                if not _in_clear(M):
                    masses.append(M)
                    break
            made += 1
    return masses


def _seam_clouds(rng):
    """Extra clusters laid along the band seams where they are seen past the logo (the two top
    corners for the upper seams, the centre window for the lower two), so no seam reads as a
    ruler line."""
    out = []
    corners = ((-24, 40), (230, 294))
    for y_seam, zi, spans in ((12, 0, corners), (46, 1, corners), (90, 2, corners),
                              (136, 3, ((40, 110), (110, 180), (180, 250))),
                              (201, 4, ((40, 118), (186, 240)))):
        zone = CLOUD_ZONES[zi]
        for x_lo, x_hi in spans:
            for _ in range(1 if (x_lo < 0 and zi) or zi >= 3 else 2):
                for _try in range(10):
                    M = _plan(rng, rng.uniform(x_lo, x_hi), y_seam + rng.uniform(-1, 5), zone)
                    if not _in_clear(M):
                        out.append(M)
                        break
    return out


def _heroes(rng):
    """Long thick banks in the visible centre window, left and right of the sun."""
    ramp = ("SKY_MID", "RED", "SKY_LOW", "RED_LIGHT")
    out = []
    for x_lo, x_hi, y_lo, y_hi, s in ((-30, 108, 152, 180, 0.04), (162, 300, 160, 188, -0.04)):
        n = 6
        step = (y_hi - y_lo) / (n - 1)
        for i in range(n):
            ln = rng.randint(40, 90)
            xc = rng.uniform(x_lo + ln / 2, x_hi - ln / 2)
            yc = y_lo + i * step + rng.uniform(-1.5, 1.5)
            t = rng.uniform(3.5, 6.5)
            lenses = [(xc, yc, ln, t * 0.6, t * 0.4, s)]
            if rng.random() < 0.6:
                d = rng.choice((-1, 1)) * ln * rng.uniform(0.3, 0.5)
                lenses.append((xc + d, yc - rng.uniform(1.5, 3), ln * 0.5, t * 0.5, t * 0.3, s))
            M = _Mass(lenses, ramp, rng.random() < 0.55, rng.random() < 0.5)
            if not _in_clear(M, 2):
                out.append(M)
    # a thinner bridge over the sun between the two banks, stopping short of the clear patch
    for i in range(4):
        ln = rng.randint(30, 56)
        xc = rng.uniform(96 + ln / 2, 214 - ln / 2)
        yc = 168 + i * 5.5 + rng.uniform(-1, 1)
        t = rng.uniform(3.0, 4.5)
        M = _Mass([(xc, yc, ln, t * 0.6, t * 0.4, 0.0)], ramp, True, rng.random() < 0.3)
        if not _in_clear(M, 2):
            out.append(M)
    # the two short warm streaks under the right bank
    for xc, yc, ln in ((177, 185, 18), (190, 189, 20)):
        out.append(_Mass([(xc, yc, ln, 1.6, 1.0, 0.0)], ("SKY_MID", "SKY_LOW", "HORIZON", "HORIZON"),
                         True, False, rough=0.5, thresh=0.15, hole=False))
    # at most two thin warm wisps over the clear patch
    for xc, yc, ln in ((130, 194, 26), (176, 198, 22)):
        out.append(_Mass([(xc, yc, ln, 1.3, 0.9, 0.0)], ("SKY_WARM", "SKY_WARM", "SKY_WARM", "SKY_WARM"),
                         False, False, rough=0.45, thresh=0.12, hole=False))
    return out


def _sunlit(M):
    """Clouds near the disc take HORIZON on their lit side."""
    sx, sy, r = SUN
    x0, y0, x1, y1 = M.bbox(0)
    nx, ny = min(max(sx, x0), x1), min(max(sy, y0), y1)
    if math.hypot(nx - sx, ny - sy) <= r + NEAR_SUN and M.ramp[2] in ("RED_LIGHT", "RED", "SKY_LOW"):
        M.ramp = (M.ramp[0], M.ramp[1], "HORIZON", "HORIZON")
        M.lit = True


def _cap_runs(G, rng):
    """Where masses overlap, their bodies can join into one long bar. Every same-coloured
    cloud run in a row longer than about 35 px is broken by a 1..3 px gap of bare sky."""
    g, cl = G.g, G.cloud
    for Y in range(0, OY + SKY_ROWS):
        row, crow = g[Y], cl[Y]
        X = 0
        while X < W:
            if not crow[X]:
                X += 1
                continue
            e = X + 1
            while e < W and crow[e] and row[e] == row[X]:
                e += 1
            start = X
            cap = rng.randint(*RUN_CAP)
            while e - start > cap:
                gpos = start + rng.randint(cap * 2 // 3, cap)
                gl = rng.randint(1, 3)
                if gpos + gl + 3 >= e:
                    break
                row[gpos:gpos + gl] = G.band[Y, gpos:gpos + gl]
                crow[gpos:gpos + gl] = False
                start = gpos + gl
                cap = rng.randint(*RUN_CAP)
            X = e


def _tidy(G):
    """Cloud pixels left without a same-coloured 4-neighbour (where masses overlap or tones
    meet) take the most common colour around them, so every mark stays a run or cluster."""
    g = G.g
    for _ in range(3):
        same = np.zeros(g.shape, dtype=np.int16)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            same += np.roll(np.roll(g, dy, 0), dx, 1) == g
        ys, xs = np.nonzero(G.cloud & (same == 0))
        if not len(ys):
            break
        for Y, X in zip(ys, xs):
            if 0 < X < W - 1 and 0 < Y < H - 1:
                ns = [g[Y, X - 1], g[Y, X + 1], g[Y - 1, X], g[Y + 1, X]]
                best = max(sorted(set(ns)), key=ns.count)
                g[Y, X] = best


# ---------------------------------------------------------------- the sun

def _in_disc(x, y, sx, sy, r):
    return (x - sx) ** 2 + (y - sy) ** 2 <= (r + 0.5) ** 2


def _sun(G):
    sx, sy, r = SUN
    # stepped halo on bare sky only: HORIZON over SKY_LOW close in, then SKY_LOW thinning out
    # over the warm band; clouds keep their colours and stand in front of the glow. Below
    # y 250 (behind the mesas) the bands stay plain.
    for y in range(sy - r - HALO, sy + r + HALO + 1):
        for x in range(sx - r - HALO, sx + r + HALO + 1):
            d = math.hypot(x - sx, y - sy)
            X, Y = x + OX, y + OY
            if d <= r + 0.5 or d > r + HALO - 0.5 or y >= 250 or G.cloud[Y, X]:
                continue
            cur = G.name(x, y)
            if cur not in ("SKY_WARM", "SKY_LOW", "HORIZON", "SKY_MID"):
                continue
            k = d - r
            low = y > sy + 6                 # the lower rim stays crisp against the sky
            if k <= 1.5:
                c = "HORIZON" if not low or dith(X, Y, 0.5) else "SKY_LOW"
            elif k <= 4.5:
                c = "HORIZON" if dith(X, Y, 0.25 if low else 0.5) else "SKY_LOW"
            elif k <= 9.5:
                c = "SKY_LOW"
            elif cur in ("SKY_WARM", "SKY_MID"):
                c = "SKY_LOW" if dith(X, Y, 0.56 - 0.5 * (k - 9.5) / (HALO - 10.0)) else None
            else:
                c = "HORIZON" if dith(X, Y, 0.25 - 0.2 * (k - 9.5) / (HALO - 10.0)) else None
            if c and not (cur == "HORIZON" and c == "SKY_LOW"):
                G.set(x, y, c)
    # the disc: flat HORIZON_HOT
    for y in range(sy - r, sy + r + 1):
        for x in range(sx - r, sx + r + 1):
            if _in_disc(x, y, sx, sy, r):
                G.set(x, y, "HORIZON_HOT")


def _noise1(rng, n, period, amp):
    """1D smooth value noise, n samples, +-amp."""
    k = n // period + 3
    lat = [rng.uniform(-amp, amp) for _ in range(k)]
    out = []
    for i in range(n):
        f = i / period
        j = int(f)
        t = f - j
        t = t * t * (3 - 2 * t)
        out.append(lat[j] + (lat[j + 1] - lat[j]) * t)
    return out


def _strip(G, rng, x0, x1, y0, y1, thick, peak=0.3, belly=True, tips=(True, True), cut_x=None):
    """One lumpy crimson mass across the lower disc. The RED body is thickest (thick rows) at
    `peak` along its length and thins to a single row toward both ends, where it breaks into
    drifting dashes; its centre line steps from y0 to y1, so it slants instead of lying flat.
    The top carries a few low rounded puffs where it is thick, a thin part may be cut once or
    twice (only between cut_x, when given) so the disc shows through, the belly is broken BLOOD
    under the thick part, the puff tops are RED_LIGHT in runs of 3+ and the top edge is lit
    (over the disc the disc row just above turns HORIZON; on the glow the top row itself does)."""
    sx, sy, r = SUN
    n = x1 - x0 + 1
    pk = peak * (n - 1)
    puffs = []
    px = x0 + rng.randint(2, 6)
    while px < x1 - 4:
        w, h = rng.uniform(5, 11), rng.uniform(1.0, 2.6)
        puffs.append((px, w, h))
        px += int(w * rng.uniform(0.8, 1.3))
    belly_n = _noise1(rng, n + 2, rng.randint(9, 14), 0.55)
    under_n = _noise1(rng, n + 2, 5, 1.0)
    lit_n = _noise1(rng, n + 2, 5, 1.0)
    rows = []
    for i in range(n):
        x = x0 + i
        f = i / pk if i <= pk else (n - 1 - i) / (n - 1 - pk)     # 0 at the tips, 1 at the peak
        t = max(1.0, thick * f ** 0.6)
        yc = y0 + (y1 - y0) * i / (n - 1)
        puff = max([h * max(0.0, 1.0 - ((x - p0) / (w / 2.0)) ** 2) ** 0.5 for p0, w, h in puffs] + [0.0])
        top = int(math.floor(yc - t * 0.5 - puff * min(1.0, max(0.0, f * 2.5 - 1.5)) + 0.5))
        bot = int(math.floor(yc + t * 0.5 + belly_n[i] * min(1.0, f) + 0.5)) - 1
        rows.append([x, top, max(top, bot)])
    # cut the thin stretch once or twice (2..3 px) so the disc shows through the mass; cut_x
    # keeps the cuts to a span of the disc that is seen between the mesas
    lo, hi = cut_x or (-OX, SAFE_W + OX)
    thin = [i for i in range(4, n - 4) if rows[i][2] - rows[i][1] <= 1 and lo <= rows[i][0] <= hi
            and _in_disc(rows[i][0], rows[i][1], sx, sy, r)]
    cuts = set()
    if thin:
        for _ in range(rng.choice((1, 2, 2))):
            c = rng.choice(thin)
            if all(abs(c - k) > 7 for k in cuts):
                cuts.update(range(c, c + rng.randint(2, 3)))
    # the puff tops catch the sun (RED_LIGHT), but only in runs of 3+ along one row, so no
    # lit pixel is left on its own where the mass steps or another layer crosses it. Where the
    # top edge is lit HORIZON on the glow instead (below), that top pixel is not RED_LIGHT.
    uncovered = [not G.cloud[top - 1 + OY, x + OX] for x, top, bot in rows]
    glow_top = [uncovered[i] and lit_n[i] > 0.2 and not _in_disc(x, top - 1, sx, sy, r) and
                math.hypot(x - sx, top - sy) < r + 10 and bot - top >= 2
                for i, (x, top, bot) in enumerate(rows)]
    lit = [i not in cuts and rows[i][2] - rows[i][1] >= 2 and lit_n[i] > -0.1 and not glow_top[i]
           for i in range(n)]
    i = 0
    while i < n:
        j = i
        while j + 1 < n and lit[i] and lit[j + 1] and rows[j + 1][1] == rows[i][1]:
            j += 1
        if lit[i] and j - i < 2:
            for k in range(i, j + 1):
                lit[k] = False
        i = j + 1
    for i, (x, top, bot) in enumerate(rows):
        if i in cuts:
            continue
        for y in range(top, bot + 1):
            c = "RED"
            if belly and y == bot and bot - top >= 2 and under_n[i] > 0.45:
                c = "BLOOD"
            elif y == top and lit[i]:
                c = "RED_LIGHT"
            G.set(x, y, c, True)
        if uncovered[i] and lit_n[i] > 0.2 and _in_disc(x, top - 1, sx, sy, r):
            G.set(x, top - 1, "HORIZON", True)
        elif glow_top[i]:
            G.set(x, top, "HORIZON", True)
    # ragged ends: dashes that drift off the tips
    for side, (last, y), on in ((-1, (x0, rows[0][1]), tips[0]), (1, (x1, rows[-1][1]), tips[1])):
        for _ in range(rng.randint(1, 3) if on else 0):
            gap = rng.randint(2, 4)
            dl = rng.randint(2, 5)
            x = last + side * gap
            y += rng.choice((0, 0, 1, -1))
            for k in range(dl):
                G.set(x + side * k, y, "RED", True)
            last = x + side * (dl - 1)


def _strips(G, rng):
    """Two crimson masses across the lower part of the disc, from row sy + 6 down, so disc rows
    195..227 (its upper 60 percent) stay a clean flat disc. The main one is a lumpy end of up
    to five rows at the left rim (228..232), two to four rows over the middle, cut right of the
    centre so the disc shows through, and runs on as a thin arm behind the right mesa and the
    windmill. The lower one comes in from the left, two to four rows, is cut near the centre and
    ends in dashes behind the right mesa. Neither is a full-width bar. The cuts are kept to the
    middle of the disc, where they are seen between the mesas."""
    sx, sy, r = SUN
    _strip(G, rng, 108, 198, 230.5, 233.5, 3.8, peak=0.3, cut_x=(sx - 6, sx + 12))
    _strip(G, rng, 104, 166, 239.5, 241.0, 3.0, peak=0.58, cut_x=(sx - 10, sx + 2))
    # a short streak in the glow right of the disc, clear of it, drifting off to the right
    _strip(G, rng, 187, 214, 218.5, 219.5, 2.4, peak=0.35, belly=False, tips=(False, True))
    # and its partner on the left: a thin streak out of the left mesas toward the rim at about
    # sy - 12 (clear of the butte top at y 214), its tip stopping 3 px short of the disc so the
    # disc itself stays clean
    _strip(G, rng, 100, 127, 209.5, 210.4, 2.2, peak=0.3, belly=False, tips=(True, False))


def draw_sky(rng):
    G = _Grid()
    _bands(G, rng)
    NZ = 0.62 * _vnoise(rng, 12, 3) + 0.38 * _vnoise(rng, 5, 2)
    MOT = 0.6 * _vnoise(rng, 7, 3) + 0.4 * _vnoise(rng, 4, 3)
    masses = _clouds(rng) + _seam_clouds(rng) + _heroes(rng)
    for M in masses:
        _sunlit(M)
        _paint_mass(G, M, NZ, MOT)
    _tidy(G)
    _cap_runs(G, rng)
    _tidy(G)
    _sun(G)
    _strips(G, rng)
    _tidy(G)
    return G.to_layer()
