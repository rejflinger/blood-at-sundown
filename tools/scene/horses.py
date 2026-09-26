"""The saddled bay at the hitching rail on the right side of the street (town layer).

One horse, drawn pixel by pixel at native size: it faces the street (left) in a 3/4 view with
the head slightly lowered, backlit by the sun to the upper left (rim light on every top edge
and on the face and chest) and lit from above right by the porch lantern (saddle, croup).
Coordinates are safe-area pixels. Order: ground shadow, far rail post, far legs, tail, body,
neck, head, near legs, tack, reins, then the hitching rail in front of it all. The foreground
barrel (x 248..271, y 376..416) stands in front of the hind legs. Nothing is drawn at
x < 195 in rows 322..360, where the PLAY button sits.

The coat is a dark red bay painted in solid form planes, dark to light: BROWN_BLACK in the
deepest shadow, WINE_DARK where the form turns away, BROWN_DARK, RUST where it turns up to the
sky or the lantern, then short ORANGE glints and a 1 px RIM on the sunward contour. A 50%
checker is used only as a 1 px seam where two planes meet, and no coat or leather pixel is
left alone (see _despeckle): every mark is a run or cluster of 2+ px, except the deliberate
glints (eye, bit, rings, buckle, stirrup).
"""
import numpy as np
from PIL import Image, ImageDraw

import palette as P
from scene.common import *  # noqa: F401,F403

# working window (safe px)
X0, Y0, X1, Y1 = 186, 294, 292, 420


class _Can:
    """A small grid of palette names (None = transparent) in safe coordinates."""

    def __init__(self):
        self.w, self.h = X1 - X0 + 1, Y1 - Y0 + 1
        self.c = np.full((self.h, self.w), None, dtype=object)

    def mask(self, pts):
        im = Image.new("L", (self.w, self.h), 0)
        ImageDraw.Draw(im).polygon([(x - X0, y - Y0) for x, y in pts], fill=1)
        return np.array(im).astype(bool)

    def poly(self, pts, name):
        m = self.mask(pts)
        self.c[m] = name
        return m

    def px(self, x, y, name):
        if X0 <= x <= X1 and Y0 <= y <= Y1:
            self.c[y - Y0, x - X0] = name

    def get(self, x, y):
        if X0 <= x <= X1 and Y0 <= y <= Y1:
            return self.c[y - Y0, x - X0]
        return None

    def hline(self, x0, x1, y, name):
        for x in range(x0, x1 + 1):
            self.px(x, y, name)

    def vline(self, x, y0, y1, name):
        for y in range(y0, y1 + 1):
            self.px(x, y, name)

    def line(self, pts, name, only=None):
        im = Image.new("L", (self.w, self.h), 0)
        ImageDraw.Draw(im).line([(x - X0, y - Y0) for x, y in pts], fill=1, width=1)
        m = np.array(im).astype(bool)
        if only is not None:
            m &= only
        self.c[m] = name
        return m

    def recolour(self, m, fn):
        ys, xs = np.nonzero(m)
        for yy, xx in zip(ys, xs):
            x, y = int(xx) + X0, int(yy) + Y0
            new = fn(x, y, self.c[yy, xx])
            if new:
                self.c[yy, xx] = new

    def alpha(self):
        return np.vectorize(lambda v: v is not None)(self.c)

    def is_(self, names):
        return np.vectorize(lambda v: v in names)(self.c)


def _dilate(m, n=1, diag=False):
    out = m.copy()
    for _ in range(n):
        o = out.copy()
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)) + (((1, 1), (1, -1), (-1, 1), (-1, -1)) if diag else ()):
            o |= _shift(out, dx, dy)
        out = o
    return out


def _shift(m, dx, dy):
    """out[y, x] = m[y + dy, x + dx], False outside."""
    h, w = m.shape
    out = np.zeros_like(m)
    ys0, ys1 = max(0, -dy), min(h, h - dy)
    xs0, xs1 = max(0, -dx), min(w, w - dx)
    if ys0 < ys1 and xs0 < xs1:
        out[ys0:ys1, xs0:xs1] = m[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx]
    return out


def _depth(S, dirs, kmax):
    """For each pixel of S, the fewest steps toward any of `dirs` that leave S (0 = never)."""
    D = np.zeros(S.shape, int)
    for k in range(kmax, 0, -1):
        hit = np.zeros_like(S)
        for dx, dy in dirs:
            hit |= ~_shift(S, int(round(k * dx)), int(round(k * dy)))
        D[S & hit] = k
    return D


def _plane(C, where, pts, name, over, seam=1):
    """A solid form plane over the `over` colours inside `where`, with a 1 px 50% checker seam
    around it (every seam pixel touches another of its colour on a diagonal)."""
    core = C.mask(pts) & where
    C.recolour(core, lambda x, y, c: name if c in over else None)
    acc = core.copy()
    for _ in range(seam):
        ring = _dilate(acc) & where & ~acc
        C.recolour(ring, lambda x, y, c: name if c in over and (x + y) % 2 == 0 else None)
        acc |= ring


# ---------------------------------------------------------------- silhouette

# the crest arches up from the withers and peaks just behind the poll
NECK = [(208, 306), (212, 305), (216, 306), (220, 307), (224, 309), (228, 312), (231, 315),
        (234, 319), (237, 323), (237, 334), (231, 348), (217, 352), (213, 346), (212, 338),
        (211, 331), (211, 318), (210, 311)]
BODY = [(230, 318), (234, 319), (240, 321), (248, 322), (255, 322), (259, 321), (262, 321),
        (265, 323), (267, 327), (268, 333), (268, 341), (267, 348), (265, 353), (262, 357),
        (257, 360), (250, 362), (240, 363), (230, 363), (222, 362), (217, 359), (214, 355),
        (213, 348), (216, 340), (222, 330)]
# near fore: forearm, knee bulge (380..384), slim cannon, fetlock bulge (399..402), pastern
FORE_NEAR = [(214, 350), (222, 352), (222, 358), (221, 366), (221, 374), (222, 380), (222, 384),
             (221, 386), (221, 398), (222, 399), (222, 402), (221, 403), (221, 405), (215, 405),
             (215, 403), (216, 402), (216, 399), (217, 398), (217, 386), (215, 384), (215, 380),
             (216, 373), (214, 366)]
FORE_FAR = [(223, 354), (229, 354), (228, 366), (228, 374), (229, 380), (229, 384), (228, 386),
            (228, 396), (229, 397), (229, 400), (228, 402), (223, 402), (222, 400), (223, 397),
            (224, 396), (224, 386), (223, 384), (223, 380), (224, 374), (224, 366)]
HIND_NEAR = [(254, 340), (262, 336), (267, 341), (267, 350), (265, 357), (263, 364), (262, 372),
             (263, 381), (263, 386), (261, 390), (261, 401), (262, 403), (262, 405), (256, 405),
             (256, 403), (257, 401), (257, 391), (255, 386), (254, 379), (253, 368), (251, 360),
             (251, 350)]
HIND_FAR = [(245, 352), (252, 352), (252, 364), (251, 372), (251, 382), (250, 386), (250, 398),
            (251, 400), (250, 402), (246, 402), (245, 400), (246, 398), (246, 386), (245, 382),
            (245, 372), (244, 362)]
TAIL = [(263, 322), (266, 322), (268, 325), (269, 332), (269, 345), (268, 358), (267, 368),
        (265, 375), (263, 371), (263, 360), (262, 348), (262, 336), (262, 327)]
# hooves (x0, x1, top, bottom): broad, the toe forward
HOOVES = ((213, 221, 406, 412), (222, 229, 403, 409), (255, 262, 406, 412), (244, 251, 403, 409))

# The head, pixel by pixel (x 195..214 from y 300), in a 3/4 profile facing the street: two
# ears close together at the poll, tipped forward, the far one half hidden; the face line
# slopes from the forehead (x 199 at y 312) to a blunt, rounded muzzle (x 195, rows 331..339);
# a round jowl behind the cheek strap, lit on its upper front. Backlit: 1 px RIM down the
# face, short ORANGE glints on the forehead and the nose bridge, RUST beside the rim, the face
# BROWN_DARK above the facial crest and WINE_DARK below it, a dark muzzle. Bridle: GOLD brow
# band and noseband sloping down toward the back like the head, OCHRE cheek strap and
# throatlatch, a LAMP ring, a SILVER bit, AMBER catchlight in the eye.
HEAD_X, HEAD_Y = 195, 300
HEAD_ART = [
    ".........H..........",   # 300
    ".....H...Hr.........",   # 301
    ".....Rr..Rdr........",   # 302
    ".....Rdr.Rddr.......",   # 303
    ".....RdbdRddr.......",   # 304
    ".....RdbdRddbr......",   # 305
    ".....RddddObbbR.....",   # 306
    ".....RodddObmmb.....",   # 307
    "....RoddOdbmmmb.....",   # 308
    "....RoodObmmmbb.....",   # 309
    "....gggddmmmmbbb....",   # 310
    "....Roordmggmmbb....",   # 311
    "....RoormmmmgOmb....",   # 312
    "...RoormmmmmOmOb....",   # 313
    "...RoormmbbmOmOb....",   # 314
    "...RorrmbddmOmmOb...",   # 315
    "...RrrrbbbbmOmmOb...",   # 316
    "...RrrrbaKKbOmmbb...",   # 317
    "...RrrrmKKmbOmrmd...",   # 318
    "..RrrrmmmmbmOrrrd...",   # 319
    "..RorrmmmmmbOrrmd...",   # 320
    "..RoormmmmbOmrrmd...",   # 321
    "..RoormmmbbOmmrmd...",   # 322
    "..RorrmmbbbOmmmmd...",   # 323
    "..RorrmmmbbOmmmmd...",   # 324
    ".RorrmmmbbbOmmmbd...",   # 325
    ".RorrmmbbbbOmmbbd...",   # 326
    ".RrrmmbbbbbObbbdd...",   # 327
    ".RrrmmmbbbbObbbdd...",   # 328
    ".ggmmmbbbbbObbddd...",   # 329
    ".RrgggbbbbbObdddd...",   # 330
    "RrmmbbOOObbOdddd....",   # 331
    "RrmbbbbbbOOldddd....",   # 332
    "Rrmmbbbbbbddddd.....",   # 333
    "RrKbbbbbbddddd......",   # 334
    "RrKbbbbbddddd.......",   # 335
    "Rrbbbbbddddd........",   # 336
    "Rrsbbbddddd.........",   # 337
    "Rbbbbdddddd.........",   # 338
    "Rbbbdddddd..........",   # 339
    ".KKKKddddd..........",   # 340
    ".dddddddd...........",   # 341
    "..dddddd............",   # 342
    "...dddd.............",   # 343
]
HEAD_KEY = {"K": "INK", "d": "BROWN_BLACK", "b": "WINE_DARK", "m": "BROWN_DARK",
            "r": "RUST", "o": "ORANGE", "R": "RIM", "H": "RIM_HOT", "O": "OCHRE", "g": "GOLD",
            "l": "LAMP", "a": "AMBER", "s": "SILVER"}


def _head_mask(C):
    m = np.zeros((C.h, C.w), bool)
    for j, row in enumerate(HEAD_ART):
        for i, ch in enumerate(row):
            if ch != ".":
                m[HEAD_Y + j - Y0, HEAD_X + i - X0] = True
    return m


def _paint_head(C, rimmed):
    for j, row in enumerate(HEAD_ART):
        for i, ch in enumerate(row):
            if ch == ".":
                continue
            x, y = HEAD_X + i, HEAD_Y + j
            C.px(x, y, HEAD_KEY[ch])
            rimmed[y - Y0, x - X0] = ch in "RH"


# coat ramp, dark to light: a dark red bay. The coat is BROWN_DARK, WINE_DARK where the form
# turns away, BROWN_BLACK in the deepest shadow, RUST planes where it turns up to the light,
# ORANGE glints.
DEEP, SHAD, BASE, LIT, HOT = "BROWN_BLACK", "WINE_DARK", "BROWN_DARK", "RUST", "ORANGE"


def _horse():
    C = _Can()
    parts = {}
    parts["fore_far"] = C.poly(FORE_FAR, SHAD)
    parts["hind_far"] = C.poly(HIND_FAR, SHAD)
    parts["body"] = C.poly(BODY, BASE)
    parts["hind_near"] = C.poly(HIND_NEAR, BASE)
    parts["neck"] = C.poly(NECK, BASE)
    parts["head"] = _head_mask(C)
    C.c[parts["head"]] = BASE
    parts["fore_near"] = C.poly(FORE_NEAR, BASE)
    near = parts["body"] | parts["hind_near"] | parts["neck"] | parts["head"] | parts["fore_near"]
    fore = parts["fore_near"] & ~parts["body"]
    neck = parts["neck"] & ~parts["head"]
    coat = near & ~parts["head"]
    hind = parts["hind_near"]

    # ---- form shadow first: WINE_DARK where the barrel, the neck and the quarters turn away
    under = _depth(near, [(0, 1)], 8)
    back = _depth(near, [(1, 0)], 4)

    def shade(x, y, c):
        yy, xx = y - Y0, x - X0
        ku, kb = under[yy, xx], back[yy, xx]
        if y > 352 and ku == 1:
            return DEEP
        if y > 346 and ku and (ku <= 7 or (ku == 8 and (x + y) % 2 == 0)):
            return SHAD
        if kb == 1 and y > 324:
            return DEEP
        if kb and y > 326 and (kb <= 3 or (kb == 4 and (x + y) % 2 == 0)):
            return SHAD
        return None
    C.recolour(coat & ~fore, shade)
    # lower neck and throat, the girth behind the elbow
    _plane(C, neck, [(211, 330), (218, 331), (225, 334), (230, 338), (222, 352), (213, 350)], SHAD, (BASE,))
    _plane(C, coat, [(228, 340), (238, 339), (239, 366), (227, 366)], SHAD, (BASE,))
    # ---- form lights: small solid RUST planes, then ORANGE glints, where the neck, the
    # shoulder and the croup turn up toward the sky and the lantern
    planes = (
        # neck: a sheen along the middle of the neck, below the mane's shadow
        ([(214, 318), (220, 318), (226, 321), (231, 325), (229, 329), (222, 328), (215, 325)],
         LIT, (BASE, SHAD)),
        # the point of the shoulder, behind the neck groove
        ([(218, 338), (223, 334), (228, 335), (227, 343), (221, 348), (216, 346)],
         LIT, (BASE, SHAD)),
        # the forearm front
        ([(214, 351), (217, 352), (216, 368), (214, 366)], LIT, (BASE, SHAD)),
        # croup and hip, lit by the lantern
        ([(256, 322), (264, 323), (267, 329), (263, 334), (258, 331)], LIT, (BASE, SHAD)),
        # the stifle
        ([(252, 348), (256, 347), (256, 354), (253, 356)], LIT, (BASE, SHAD)),
    )
    for pts, name, over in planes:
        _plane(C, coat, pts, name, over)
    # glints: short ORANGE runs where the light is strongest
    for x0, x1, y in ((215, 217, 313), (216, 218, 314), (220, 222, 315), (221, 222, 316),
                      (216, 217, 339), (216, 217, 340), (217, 218, 341),
                      (259, 261, 323), (260, 262, 324)):
        for x in range(x0, x1 + 1):
            if coat[y - Y0, x - X0]:
                C.px(x, y, HOT)
    C.line([(223, 356), (225, 359), (228, 362)], DEEP, only=coat)          # elbow
    C.line([(231, 327), (225, 332), (220, 337), (217, 341)], BASE, only=coat)   # neck groove
    C.line([(253, 349), (254, 355), (255, 361)], DEEP, only=hind)          # stifle crease

    # ---- the near fore: bay points below the knee, dark back edge
    C.recolour(fore, lambda x, y, c: DEEP if back[y - Y0, x - X0] == 1 else None)
    C.recolour(fore, lambda x, y, c: SHAD if back[y - Y0, x - X0] == 2 and y > 356 else None)
    C.recolour(fore, lambda x, y, c: (DEEP if back[y - Y0, x - X0] in (1, 2) else SHAD) if y >= 386 else None)
    C.hline(216, 221, 381, DEEP)                                           # knee crease
    C.hline(217, 221, 399, DEEP)                                           # fetlock
    C.vline(217, 383, 384, BASE)                                           # knee cap
    C.vline(217, 400, 401, BASE)                                           # fetlock knob
    # far legs: dark, a line of light down the forearm
    for key, knee in (("fore_far", 380), ("hind_far", 382)):
        m = parts[key] & ~near
        C.recolour(m, lambda x, y, c, k=knee: SHAD if y < k else DEEP)
    C.vline(224, 358, 375, BASE)
    C.vline(224, 387, 395, SHAD)
    C.vline(246, 383, 397, SHAD)
    # hind near below the stifle: darker, hidden by the barrel below y 376
    C.recolour(hind & ~parts["body"], lambda x, y, c: DEEP if y >= 383 else None)

    # ---- rim: 1 px RIM on the sunward contour (top and front), the legs keep a thin lit front
    lit = _depth(near, [(0, -1), (-1, 0)], 2)
    rimmed = np.zeros_like(near)
    ys_, xs_ = np.nonzero((lit == 1) & coat)
    for yy, xx in zip(ys_, xs_):
        x, y = int(xx) + X0, int(yy) + Y0
        if y > 405:
            continue
        if y < 358:
            C.c[yy, xx] = "RIM"
            rimmed[yy, xx] = True
        elif (fore | hind)[yy, xx] and not near[yy, xx - 1]:   # the legs: only their front edges
            C.c[yy, xx] = HOT if y < 383 else LIT
    # the second column in on the chest catches light too
    for y in range(342, 356):
        idx = np.nonzero(near[y - Y0])[0]
        if len(idx):
            x = int(idx[0]) + X0 + 1
            C.px(x, y, HOT if y < 350 else LIT)

    # ---- mane along the crest: a thick dark mass falling on the near side, its lower edge cut
    # into pointed locks, BROWN_DARK strands, lit lock ends under the crest rim
    alpha = near.copy()
    for x in range(209, 235):
        idx = np.nonzero(alpha[:, x - X0])[0]
        if not len(idx):
            continue
        ty = int(idx[0]) + Y0
        t = (x - 209) / 25.0
        body = 4 + int(round(4.5 * np.sin(np.pi * min(1.0, t * 1.25))))   # thickest mid-neck
        lock = (x - 209) // 3
        tip = (0, 2, 1)[(x - 209) % 3] + int(hsh(lock, 5) * 2.4)
        fall = max(2, body + tip - (3 if x > 231 else 0))
        for k in range(1, 1 + fall):
            C.px(x, ty + k, DEEP)
        if (x - 209) % 4 == 2 and fall >= 5:           # strands
            for k in range(2, min(fall, 6)):
                C.px(x, ty + k, BASE)
        # lit lock ends: runs of 2-3 px just under the crest rim, broken irregularly
        if hsh(lock, 11) < 0.55 and x < 232:
            C.px(x, ty + 1, "OCHRE")
    # forelock and poll tuft between the ears (painted with the head)
    _paint_head(C, rimmed)
    # tail: over the rump's rear edge, dark with strands, a lit dock
    tail = C.poly(TAIL, DEEP)
    C.line([(264, 325), (265, 340), (265, 366)], SHAD)
    C.line([(266, 326), (267, 338), (267, 356)], BASE)
    C.line([(263, 330), (263, 346)], BASE)
    C.line([(268, 334), (268, 350)], "INK")
    C.vline(267, 327, 331, LIT)
    C.hline(263, 266, 322, "RIM")
    C.px(267, 323, "RIM")
    C.hline(263, 265, 323, "OCHRE")
    rimmed[tail] = False
    rimmed[322 - Y0, 263 - X0:268 - X0] = True
    # hooves: dark horn, broad at the ground, a lit coronet and front edge, a bright toe
    for k, (x0, x1, yt, yb) in enumerate(HOOVES):
        far = k % 2 == 1
        for y in range(yt, yb + 1):
            xs = x0 + (1 if y < yt + 2 else 0)
            C.hline(xs, x1, y, "BROWN_BLACK")
            C.px(xs, y, "BROWN_DARK" if far else "RUST")
        C.hline(x0 + 1, x1, yt, "WINE_DARK" if far else "BROWN_DARK")
        C.px(x0 + 1, yt, "BROWN_DARK" if far else "RUST")
        C.vline(x1, yt, yb, "INK")
        C.hline(x0, x1, yb, "INK")
        if not far:
            C.px(x0, yb - 1, "ORANGE")
            C.px(x0, yb - 2, "ORANGE")
    return C, parts, rimmed


def _tack(C):
    # saddle blanket: only a dark 1-2 px edge under the skirt's rear
    C.line([(238, 346), (247, 346), (254, 345), (258, 342), (260, 338)], "WINE_DARK")
    C.line([(248, 345), (254, 344), (257, 342)], "WINE")
    # skirt: one leaf shape, rounded at the rear and the bottom, a tooled border
    sk = [(231, 325), (247, 326), (255, 325), (259, 328), (260, 333), (259, 338), (256, 342),
          (250, 345), (242, 345), (236, 344), (232, 341), (230, 336), (230, 329)]
    m = C.mask(sk)

    def skirt(x, y, c):
        # lighter toward the top and the rear (lantern above right), darker at the bottom front
        u = (x - 230) * 0.45 - (y - 327) * 0.9
        k = 1 if (x + y) % 2 == 0 else 0
        if u > 3.5 + k:
            return "RUST"
        if u > -2.5 + k:
            return "BROWN"
        return "BROWN_DARK"
    C.recolour(m, skirt)
    C.line([(232, 341), (236, 344), (242, 345), (250, 345), (256, 342), (259, 338), (260, 333)], "BROWN_BLACK")
    C.line([(259, 328), (260, 332)], "BROWN")
    # tooled border, 2 px in from the edge, in stitched runs
    for pts in (((232, 331), (232, 336)), ((234, 340), (236, 342)), ((239, 343), (243, 343)),
                ((246, 343), (250, 343)), ((253, 341), (255, 339)), ((257, 336), (258, 331))):
        C.line(list(pts), "RUST")
    C.line([(230, 330), (230, 336)], "ORANGE")                      # front edge, sky-lit
    # tree: one continuous shape, the rounded pommel with a knob horn, the deep seat and the
    # curved cantle; sky light on the pommel's front, lantern light along the seat and cantle
    tree = [(229, 317), (230, 315), (232, 313), (236, 313), (237, 315), (238, 320), (240, 322),
            (241, 323), (244, 323), (246, 321), (248, 318), (250, 316), (255, 316), (257, 318),
            (257, 326), (229, 326)]
    m = C.mask(tree)
    C.c[m] = "RUST"
    C.recolour(m, lambda x, y, c: "BROWN" if y >= 324 or (x >= 236 and y >= 322 and x <= 246) else None)
    C.recolour(m, lambda x, y, c: "BROWN_DARK" if x >= 256 or y >= 326 or (x >= 254 and y >= 322) else None)
    C.recolour(m, lambda x, y, c: "BROWN" if 235 <= x <= 238 and 315 <= y <= 323 else None)   # pommel's back
    C.hline(230, 256, 326, "BROWN_BLACK")
    # pommel: RIM over the top and down the front, ORANGE inside it
    C.line([(229, 318), (229, 317), (230, 316), (230, 315), (231, 314), (232, 313), (235, 313)], "RIM")
    C.vline(229, 319, 325, "ORANGE")
    C.line([(230, 317), (231, 316), (231, 315), (232, 314), (234, 314)], "ORANGE")
    C.vline(230, 318, 321, "ORANGE")
    # knob horn
    C.hline(233, 235, 311, "RIM")
    C.hline(233, 235, 312, "RUST")
    # the seat surface and the cantle's rim
    C.line([(238, 320), (240, 322), (241, 323), (244, 323), (246, 321), (248, 318), (249, 317)], "OCHRE")
    C.hline(250, 255, 316, "RIM")
    C.px(249, 317, "RIM")
    C.px(256, 317, "RIM")
    C.hline(250, 255, 317, "OCHRE")
    C.line([(248, 320), (250, 318)], "ORANGE")
    C.line([(257, 327), (259, 329)], "ORANGE")                      # skirt's rear corner, lantern-lit
    # fender and stirrup leather: narrow, in the skirt's shadow, a keeper with a buckle
    C.poly([(235, 328), (239, 328), (240, 350), (236, 350)], "BROWN_DARK")
    C.line([(235, 328), (236, 350)], "BROWN")
    C.line([(239, 328), (240, 350)], "BROWN_BLACK")
    C.hline(236, 240, 350, "BROWN_BLACK")
    C.hline(236, 239, 339, "BROWN_BLACK")
    C.px(237, 338, "OCHRE")
    C.vline(237, 351, 353, "BROWN")
    C.vline(238, 351, 353, "BROWN_BLACK")
    # stirrup iron
    for y in range(355, 362):
        C.px(233 + (1 if y < 357 else 0), y, "GREY_DARK")
        C.px(240 - (1 if y < 357 else 0), y, "GREY_DARK")
    C.hline(235, 238, 354, "GREY_DARK")
    C.hline(233, 240, 362, "GREY_DARK")
    C.hline(234, 239, 361, "INK")
    C.px(234, 357, "SILVER")
    # cinch, from the skirt to the belly
    for y in range(344, 366):
        C.hline(242, 244, y, "BROWN_BLACK")
    C.vline(242, 344, 365, "BROWN_DARK")
    C.hline(242, 244, 350, "GREY_DARK")
    C.px(243, 351, "SILVER")
    # breast collar across the shoulder, a ring at the point of the chest
    strap = [(230, 328), (227, 333), (223, 338), (219, 342), (216, 345)]
    C.line([(x, y + 2) for x, y in strap], "BROWN_BLACK")
    C.line([(x, y + 1) for x, y in strap], "RUST")
    C.line(strap, "ORANGE")
    C.px(215, 346, "LAMP")
    C.px(215, 347, "GOLD")
    C.px(216, 347, "GOLD")
    # saddle strings off the rear skirt
    C.vline(256, 327, 334, "OCHRE")
    C.vline(257, 328, 332, "BROWN_BLACK")


def _despeckle(C, keep):
    """Every coat and leather mark is a run or cluster of 2+ px: a lone pixel of one of these
    colours (no neighbour of its own colour, diagonals included) takes the colour most of its
    neighbours share. Pixels in `keep` (the hand-drawn head) are left alone."""
    names = {"WINE_DARK", "BROWN_DARK", "BROWN_BLACK", "BROWN", "BROWN_MID", "RUST", "ORANGE", "LEATHER"}
    src = C.c.copy()
    h, w = src.shape
    for yy in range(1, h - 1):
        for xx in range(1, w - 1):
            v = src[yy, xx]
            if v not in names or keep[yy, xx]:
                continue
            nb = [src[yy + dy, xx + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]
            if v in nb:
                continue
            opts = [n for n in nb if n in names]
            if opts:
                C.c[yy, xx] = max(set(opts), key=opts.count)


def _reins(L):
    """Reins from the bit, sagging to a low point by the forearm, then up to the rail post."""
    pts = []
    for i in range(0, 81):
        t = i / 80.0
        if t < 0.45:
            u = t / 0.45
            x = 198 + (216 - 198) * u
            y = 337 + (356 - 337) * (1 - (1 - u) ** 2)
        else:
            u = (t - 0.45) / 0.55
            x = 216 + (243 - 216) * u
            y = 356 - (356 - 354) * u * u
        pts.append((round(x), round(y)))
    seen = []
    for p in pts:
        if p not in seen:
            seen.append(p)
    for x, y in seen:                          # a shaded underside so the rope reads on the street
        if (x, y + 1) not in seen:
            L.px(x, y + 1, "BROWN_BLACK")
    for x, y in seen:
        L.px(x, y, "OCHRE" if y > 345 or x > 205 else "GOLD")
    # the rope must not leave a lone coat pixel beside it
    coat = {P.rgb(n) for n in ("WINE_DARK", "BROWN_DARK", "BROWN_BLACK", "BROWN", "RUST")}
    for x, y in seen:
        for dx, dy in ((0, -1), (0, 2), (-1, 0), (1, 0)):
            q = L.get(x + dx, y + dy)
            if q[3] == 0 or q[:3] not in coat:
                continue
            nb = [L.get(x + dx + i, y + dy + j)[:3] for i in (-1, 0, 1) for j in (-1, 0, 1) if i or j]
            if q[:3] not in nb:
                opts = [c for c in nb if c in coat]
                if opts:
                    L.px(x + dx, y + dy, max(set(opts), key=opts.count) + (255,))


def _composite(L, C, rimmed):
    """Writes the canvas into the layer. INK outline all round; where the rim is the edge the
    outline is left off, unless the background behind is bright."""
    a = C.alpha()
    h, w = a.shape
    pad = np.zeros((h + 2, w + 2), bool)
    pad[1:-1, 1:-1] = a
    rpad = np.zeros((h + 2, w + 2), bool)
    rpad[1:-1, 1:-1] = rimmed
    ring = np.zeros_like(pad)
    near_body = np.zeros_like(pad)
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        ring |= _shift(pad, dx, dy)
        near_body |= _shift(pad & ~rpad, dx, dy)
    ring &= ~pad
    bright = {"LAMP", "LAMP_HOT", "AMBER", "GOLD", "SKY_LOW", "HORIZON", "HORIZON_HOT", "SUN",
              "RIM", "RIM_HOT", "ORANGE", "TAN", "SAND", "DUST", "CREAM", "CREAM_SHADE",
              "SKY_WARM", "RED_LIGHT", "OCHRE", "DUST_LIGHT"}
    rev = {P.rgb(n): n for n in P.NAMES}
    ys, xs = np.nonzero(ring)
    for yy, xx in zip(ys, xs):
        x, y = int(xx) - 1 + X0, int(yy) - 1 + Y0
        if not near_body[yy, xx]:
            bg = L.get(x, y)
            if bg[3] == 0 or rev.get(tuple(bg[:3])) not in bright:
                continue
        if x < 195 and 322 <= y <= 360:
            continue
        L.px(x, y, "INK")
    for yy in range(h):
        for xx in range(w):
            v = C.c[yy, xx]
            if v is not None:
                L.px(xx + X0, yy + Y0, v)


def _shadow(L):
    """Cast shadow on the street, toward the camera: 60% Bayer, solid under the hooves."""
    for y in range(406, 418):
        for x in range(198, 273):
            d = np.hypot((x - 236) / 37.0, (y - 412) / 5.5)
            if d > 1.0:
                continue
            solid = (211 <= x <= 230 and 407 <= y <= 413) or (243 <= x <= 264 and 407 <= y <= 414)
            if solid or (dith(x + OX, y + OY, 0.6) if d < 0.75 else (x + y) % 2 == 0):
                L.px(x, y, "BROWN_BLACK")


def _post(R, x0, x1, y0, y1):
    R.rect(x0, y0, x1, y1, "BROWN")
    R.vline(x0, y0, y1, "RIM")
    R.vline(x0 + 1, y0 + 1, y1, "OCHRE")
    R.vline(x1, y0, y1, "BROWN_BLACK")
    R.vline(x1 - 1, y0 + 1, y1, "BROWN_DARK")
    R.hline(x0, x1, y0, "OCHRE")
    R.hline(x0, x0 + 2, y0, "RIM")
    for y in range(y0 + 5, y1 - 2, 9):          # grain
        R.vline(x0 + 3, y, y + 3, "BROWN_DARK")


def _rail(L):
    R = Layer()
    # the top rail runs right from the post (behind the barrel), a low board runs left of it
    for xa, xb, y0, y1 in ((249, 300, 354, 360), (230, 300, 398, 402)):
        R.rect(xa, y0, xb, y1, "BROWN")
        R.hline(xa, xb, y0, "OCHRE")
        R.hline(xa, xb, y0 + 1, "LEATHER")
        R.hline(xa, xb, y1, "BROWN_BLACK")
        R.hline(xa, xb, y1 - 1, "BROWN_DARK")
        for x in range(xa + 3, xb, 8):
            R.hline(x, x + 3, y0 + 3, "BROWN_DARK")
    R.vline(230, 398, 402, "BROWN_DARK")
    _post(R, 244, 250, 350, 411)
    R.hline(245, 249, 361, "BROWN_BLACK")        # rail shadow on the post
    R.hline(245, 249, 403, "BROWN_BLACK")
    R.outline("INK", diag=False)
    L.im.alpha_composite(R.im)


def _far_post(L):
    """The far post of the rail, in shadow behind the horse."""
    L.rect(232, 362, 235, 402, "BROWN_BLACK")
    L.vline(232, 362, 402, "BROWN_DARK")
    L.hline(232, 235, 362, "BROWN")


def draw_street_props(L, rng):
    """The saddled bay at the hitching rail on the right side of the street (town layer)."""
    _shadow(L)
    _far_post(L)
    C, parts, rimmed = _horse()
    _tack(C)
    _despeckle(C, parts["head"])
    rimmed |= C.is_(("RIM", "RIM_HOT"))
    _composite(L, C, rimmed)
    _reins(L)
    _rail(L)
