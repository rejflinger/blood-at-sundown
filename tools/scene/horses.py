"""The saddled bay at the hitching rail on the right side of the street (town layer).

One horse, drawn pixel by pixel at native size: it faces the street (left) in a 3/4 view with
the head lowered, backlit by the sun to the upper left (rim light on every top edge and on the
face and chest) and lit from above right by the porch lantern (saddle, croup). Coordinates are
safe-area pixels. Order: ground shadow, the rail's low board, far legs, tail, body, neck, head,
near legs, tack, reins, then the rail post and top rail in front of it all. The foreground
barrel (x 245..268, y 375..418) stands in front of the hind legs. The PLAY button (x 78..193,
y 318..355) covers the muzzle and the chin: the face line crosses the button's top edge just
left of its corner (x 191 at y 318), so the lit face runs under the corner instead of along
the button's right edge. The ears stand at x 201 and 206, right of the porch lantern's column.

The coat is a dark bay painted in solid form planes that meet at hard stepped edges, dark to
light: BROWN_BLACK in the deepest shadow and on the points, BROWN_DARK for the coat, BROWN
planes where the form turns up to the sky or the lantern, each with a 1 px RUST sheen along its
top, a few short ORANGE glints and a 1 px RIM on the sunward contour. Head and neck share this
ramp. No dither and no checker anywhere, and no coat or leather pixel is left alone (see
_despeckle and _tidy): every mark is a run or cluster of 2+ px, except the deliberate glints
(eye, bit and rings, keeper, stirrup). Lines drawn across a flat fill are 4-connected. Ties are
always broken in name order, so the output never depends on set order or the hash seed.
"""
import numpy as np
from PIL import Image, ImageDraw

import palette as P
from scene.common import OX, OY, Layer, hsh

# working window (safe px)
X0, Y0, X1, Y1 = 180, 294, 292, 420


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

    def line(self, pts, name, only=None, solid=False):
        """A 1 px line; `solid` fills the upper corner of every diagonal step, so the line is
        4-connected and never leaves a 2 x 2 checker cell where it crosses a flat fill."""
        im = Image.new("L", (self.w, self.h), 0)
        ImageDraw.Draw(im).line([(x - X0, y - Y0) for x, y in pts], fill=1, width=1)
        m = np.array(im).astype(bool)
        if solid:
            dr = m & _shift(m, 1, 1) & ~_shift(m, 1, 0) & ~_shift(m, 0, 1)
            dl = m & _shift(m, -1, 1) & ~_shift(m, -1, 0) & ~_shift(m, 0, 1)
            m = m | _shift(dr, -1, 0) | _shift(dl, 1, 0)
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


def _isolated(m):
    """Pixels of m with no other pixel of m among their 8 neighbours."""
    nb = np.zeros_like(m)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx or dy:
                nb |= _shift(m, dx, dy)
    return m & ~nb


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


def _plane(C, where, pts, name, over):
    """A solid form plane over the `over` colours inside `where`, meeting its neighbours at a
    hard stepped edge (no dithered seam)."""
    core = C.mask(pts) & where
    C.recolour(core, lambda x, y, c: name if c in over else None)


# ---------------------------------------------------------------- silhouette

# the crest arches up from the withers and peaks just behind the poll
NECK = [(204, 308), (208, 306), (212, 306), (216, 307), (220, 308), (224, 310), (228, 312),
        (231, 315), (234, 319), (237, 323), (237, 334), (231, 348), (217, 352), (212, 347),
        (209, 341), (207, 334), (207, 318), (205, 312)]
BODY = [(230, 318), (234, 319), (240, 321), (248, 322), (255, 322), (259, 321), (262, 321),
        (265, 323), (267, 327), (268, 333), (268, 341), (267, 348), (265, 353), (262, 357),
        (257, 360), (250, 362), (240, 363), (230, 363), (222, 362), (217, 359), (214, 355),
        (213, 348), (216, 340), (222, 330)]
# near fore: forearm, knee bulge (380..384), slim cannon, fetlock bulge (399..402), pastern
FORE_NEAR = [(214, 350), (221, 352), (221, 358), (220, 366), (220, 374), (221, 380), (221, 384),
             (220, 386), (220, 398), (221, 399), (221, 402), (220, 403), (220, 405), (215, 405),
             (215, 403), (216, 402), (216, 399), (217, 398), (217, 386), (215, 384), (215, 380),
             (216, 373), (214, 366)]
# the far fore stands a step behind and to the right, with 3 px of ground showing between the
# two from the chest down to the hooves
FORE_FAR = [(227, 354), (233, 354), (233, 366), (232, 374), (233, 380), (233, 384), (232, 386),
            (232, 396), (233, 397), (233, 400), (232, 402), (227, 402), (227, 400), (228, 397),
            (228, 396), (228, 386), (227, 384), (227, 380), (228, 374), (228, 366)]
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
HOOVES = ((213, 221, 406, 412), (227, 234, 403, 409), (255, 262, 406, 412), (244, 251, 403, 409))

# The head, pixel by pixel (x 183..208 from y 300), in a 3/4 profile facing the street and
# lowered: two pricked ears at the poll (tips at x 201 and 206), a dark forelock between them;
# the face line slopes from the forehead (x 199 at y 306) through the button's top edge (x 191
# at y 318) to a blunt muzzle (x 186, rows 326..334) hidden behind the PLAY button with the
# nostril and the chin; a round jowl behind the cheek strap. Backlit: 1 px RIM down the face and
# up the ears, a 2 px RUST band beside it with ORANGE glints on the forehead and the nose
# bridge, the front of the face BROWN, the side below the facial crest BROWN_DARK, a
# BROWN_BLACK jaw and muzzle. Bridle, every strap 4-connected: a GOLD brow band and noseband
# sloping down toward the back, an OCHRE cheek strap, a LAMP ring and a SILVER bit at the corner
# of the mouth (right of the button), an AMBER catchlight in the eye.
HEAD_X, HEAD_Y = 183, 300
HEAD_ART = [
    ".......................H..",   # 300
    "..................H....Hb.",   # 301
    "..................Hr..Rdb.",   # 302
    "..................RdrdRddb",   # 303
    "..................Rdrdddbb",   # 304
    ".................Rodddbbb.",   # 305
    "................Rormddbbb.",   # 306
    "...............Rormmddbbb.",   # 307
    "...............Rgggmmdbbb.",   # 308
    "..............Rrrmgggmbbb.",   # 309
    ".............Rrrmmmmgggbb.",   # 310
    ".............RrrmmmmmmOOb.",   # 311
    "............RrrmaKbmmmObb.",   # 312
    "...........RrrmmKKbbbbObb.",   # 313
    "...........RrrmmmbbbbOObb.",   # 314
    "..........RrrmmmbbbbbObbb.",   # 315
    ".........RormmmmbbbbbOmmb.",   # 316
    ".........RormmmbbbbbOOmmb.",   # 317
    "........RrrmmmbbbbbbOmmbd.",   # 318
    ".......RrmmmmmbbbbbbOmbbd.",   # 319
    ".......RrmmmmbbbbbbOOmbbd.",   # 320
    "......RrmmmmbbbbbbbOmbbbd.",   # 321
    ".....ggmmmmmbbbbbbbOmbbbd.",   # 322
    ".....RggggmbbbbbbbOObbbbd.",   # 323
    "....RrmmmggggbbbbbObbbbbd.",   # 324
    "....RrmmmmbbggggbbObbbbbd.",   # 325
    "...RrmmmmbbbbbbggOObbbbbd.",   # 326
    "...RrdddbbbbbbbbbObbbbbbd.",   # 327
    "...RrddddbbbbbbbbObbbbbbd.",   # 328
    "...RrKddddbbbbbbOObbbbbbd.",   # 329
    "...RrKKddddbbbbbObbbbbbbd.",   # 330
    "...RrddddddddddOObbbbbddd.",   # 331
    "...RrdddddddddOOdbbdddddd.",   # 332
    "...RrdddddddddOdddddddddd.",   # 333
    "...Rrdddddddddldddddddddd.",   # 334
    "....Rrdddddddsddddddddddd.",   # 335
    "....KKKKKKKKKKddddddddddd.",   # 336
    ".....dddddddddddddddddddd.",   # 337
    "......ddddddddddddddd.....",   # 338
    ".......dddddddddd.........",   # 339
    ".........ddd..............",   # 340
]
MANE_X = 208          # the mane starts behind the far ear
HEAD_KEY = {"K": "INK", "d": "BROWN_BLACK", "b": "BROWN_DARK", "m": "BROWN",
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


# coat ramp, dark to light: a dark bay, no crimson. The coat is BROWN_DARK; BROWN_BLACK in the
# deepest shadow and on the points (mane, tail, lower legs); solid BROWN planes where the form
# turns up to the sky or the lantern, each with a 1 px RUST sheen along its upper edge; a few
# short ORANGE glints; RIM on the sunward contour.
DEEP, SHAD, BASE, LIT, HOT = "BROWN_BLACK", "BROWN_DARK", "BROWN", "RUST", "ORANGE"

# lit form planes (BROWN over the BROWN_DARK coat)
PLANES = (
    # neck: the middle of the neck below the mane, turning up toward the sky
    [(211, 317), (219, 318), (226, 321), (229, 325), (224, 328), (214, 327)],
    # the throat and the front of the chest, facing the sun
    [(208, 330), (212, 331), (214, 339), (215, 347), (212, 347), (209, 341)],
    # the shoulder, behind the breast collar
    [(218, 339), (224, 334), (229, 335), (230, 341), (226, 348), (220, 350), (216, 346)],
    # the forearm front
    [(214, 351), (218, 352), (217, 368), (214, 366)],
    # croup and hip, lit by the lantern
    [(254, 322), (264, 323), (267, 330), (263, 336), (256, 332)],
    # the stifle
    [(251, 347), (256, 346), (256, 354), (252, 356)],
)
# short ORANGE glints (x0, x1, y) on the sheen where the light is strongest: the neck, the
# point of the shoulder, the croup
GLINTS = ((214, 215, 318), (222, 223, 320), (224, 225, 341), (259, 261, 323))


def _horse():
    C = _Can()
    parts = {}
    parts["fore_far"] = C.poly(FORE_FAR, SHAD)
    parts["hind_far"] = C.poly(HIND_FAR, SHAD)
    parts["body"] = C.poly(BODY, SHAD)
    parts["hind_near"] = C.poly(HIND_NEAR, SHAD)
    parts["neck"] = C.poly(NECK, SHAD)
    parts["head"] = _head_mask(C)
    C.c[parts["head"]] = SHAD
    parts["fore_near"] = C.poly(FORE_NEAR, SHAD)
    near = parts["body"] | parts["hind_near"] | parts["neck"] | parts["head"] | parts["fore_near"]
    fore = parts["fore_near"] & ~parts["body"]
    coat = near & ~parts["head"]
    hind = parts["hind_near"]

    # ---- lit planes: solid BROWN, a 1 px RUST sheen along each one's upper edge
    under = _depth(near, [(0, 1)], 8)
    back = _depth(near, [(1, 0)], 4)
    for pts in PLANES:
        m = C.mask(pts) & coat
        C.c[m] = BASE
        C.c[m & ~_shift(m, 0, -1)] = LIT
    # ---- form shadow: BROWN_BLACK where the belly and the quarters turn away
    def shade(x, y, c):
        yy, xx = y - Y0, x - X0
        ku, kb = under[yy, xx], back[yy, xx]
        if y > 352 and ku == 1 and x < 250:
            return LIT                    # warm light bounced up from the street
        if y > 350 and ku and ku <= 3:
            return DEEP
        if kb and kb <= 2 and y > 324:
            return DEEP
        return None
    C.recolour(coat & ~fore, shade)
    # the girth behind the elbow turns away from both lights
    _plane(C, coat, [(229, 346), (233, 345), (233, 366), (229, 366)], DEEP, (SHAD,))
    for x0, x1, y in GLINTS:
        for x in range(x0, x1 + 1):
            if coat[y - Y0, x - X0]:
                C.px(x, y, HOT)
    C.line([(223, 356), (225, 359), (228, 362)], DEEP, only=coat, solid=True)          # elbow
    C.line([(253, 349), (254, 355), (255, 361)], DEEP, only=hind, solid=True)          # stifle crease

    # ---- the near fore: bay points below the knee, dark back edge
    C.recolour(fore, lambda x, y, c: DEEP if back[y - Y0, x - X0] == 1 else None)
    C.recolour(fore, lambda x, y, c: SHAD if back[y - Y0, x - X0] == 2 and y > 356 else None)
    C.recolour(fore, lambda x, y, c: (DEEP if back[y - Y0, x - X0] in (1, 2) else SHAD) if y >= 386 else None)
    C.hline(216, 220, 381, DEEP)                                           # knee crease
    C.hline(217, 220, 399, DEEP)                                           # fetlock
    C.vline(217, 383, 384, BASE)                                           # knee cap
    C.vline(217, 400, 401, BASE)                                           # fetlock knob
    # far legs: dark, a line of light down the forearm
    for key, knee in (("fore_far", 380), ("hind_far", 382)):
        m = parts[key] & ~near
        C.recolour(m, lambda x, y, c, k=knee: SHAD if y < k else DEEP)
    C.vline(229, 358, 377, BASE)
    C.vline(229, 387, 395, SHAD)
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
    # a RUST sheen 2 px deep inside the rim down the throat and the chest, ORANGE where the
    # light is strongest
    for y in range(331, 356):
        xs = [int(xx) + X0 for xx in np.nonzero(rimmed[y - Y0] & coat[y - Y0])[0] if int(xx) + X0 < 222]
        if xs:
            x = min(xs)
            C.px(x + 1, y, HOT if 342 <= y <= 348 else LIT)
            C.px(x + 2, y, LIT)

    # ---- mane along the crest: a thick dark mass falling on the near side, its lower edge cut
    # into pointed locks, BASE strands, lit lock ends under the crest rim
    alpha = near.copy()
    for x in range(MANE_X, 235):
        idx = np.nonzero(alpha[:, x - X0])[0]
        if not len(idx):
            continue
        ty = int(idx[0]) + Y0
        t = (x - MANE_X) / float(235 - MANE_X)
        body = 4 + int(round(4.5 * np.sin(np.pi * min(1.0, t * 1.25))))   # thickest mid-neck
        lock = (x - MANE_X) // 3
        tip = (0, 2, 1)[(x - MANE_X) % 3] + int(hsh(lock, 5) * 2.4)
        fall = max(2, body + tip - (3 if x > 231 else 0))
        for k in range(1, 1 + fall):
            C.px(x, ty + k, DEEP)
        if (x - MANE_X) % 4 == 2 and fall >= 5:           # strands
            for k in range(2, min(fall, 6)):
                C.px(x, ty + k, BASE)
        # lit lock ends: runs of 2-3 px just under the crest rim, broken irregularly
        if hsh(lock, 11) < 0.55 and 1 <= lock <= 6:     # whole locks, clear of the head and pommel
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
        C.hline(x0 + 1, x1, yt, "BROWN_DARK" if far else "BROWN")
        C.px(x0 + 1, yt, "BROWN_DARK" if far else "RUST")
        C.vline(x1, yt, yb, "INK")
        C.hline(x0, x1, yb, "INK")
        if not far:
            C.px(x0, yb - 1, "ORANGE")
            C.px(x0, yb - 2, "ORANGE")
    return C, parts, rimmed


def _tack(C):
    """Dark leather tack, close to the coat in value. The saddle sits on a SHADOW blanket that
    shows as a narrow band under its skirt; the skirt is BROWN_DARK with BROWN tooling, BROWN
    where the lantern catches its rear, and OCHRE edges; the tree is BROWN, BROWN_MID on the
    cantle's lantern-lit face, BROWN_DARK below, RIM only where the sun hits the horn, pommel and
    cantle tops."""
    # saddle blanket: a band 2 px deep under the skirt, ending before its rear edge
    pad = [(233, 338), (256, 338), (257, 342), (252, 347), (240, 347), (234, 345)]
    C.poly(pad, "SHADOW")
    # skirt: one leaf shape, rounded at the rear and the bottom, a tooled border
    sk = [(231, 325), (247, 326), (255, 325), (259, 328), (260, 333), (259, 338), (256, 342),
          (250, 345), (242, 345), (236, 344), (232, 341), (230, 336), (230, 329)]
    m = C.mask(sk)
    C.c[m] = "BROWN_DARK"
    C.recolour(m, lambda x, y, c: "BROWN" if x - 2 * (y - 327) >= 246 else None)   # lantern-lit rear
    C.line([(232, 341), (236, 344), (242, 345), (250, 345), (256, 342), (259, 338), (260, 333)], "BROWN_BLACK", solid=True)
    # tooled border, 2 px in from the edge, in stitched runs
    for pts in (((232, 331), (232, 336)), ((234, 340), (236, 342)), ((239, 343), (243, 343)),
                ((246, 343), (250, 343)), ((253, 341), (255, 339)), ((257, 336), (258, 331))):
        C.line(list(pts), "BROWN", solid=True)
    C.line([(230, 330), (230, 336)], "OCHRE")                       # front edge, sky-lit
    C.line([(259, 328), (260, 332)], "OCHRE")                       # rear edge, lantern-lit
    # tree: one continuous shape, the rounded pommel with a knob horn, the deep seat and the
    # curved cantle; sky light on the pommel's front, lantern light along the seat and cantle
    tree = [(229, 317), (230, 315), (232, 313), (236, 313), (237, 315), (238, 320), (240, 322),
            (241, 323), (244, 323), (246, 321), (248, 318), (250, 316), (255, 316), (257, 318),
            (257, 326), (229, 326)]
    m = C.mask(tree)
    C.c[m] = "BROWN"
    C.recolour(m, lambda x, y, c: "BROWN_MID" if 247 <= x <= 255 and y <= 321 else None)   # cantle face
    C.recolour(m, lambda x, y, c: "BROWN_DARK" if x >= 256 or y >= 324 or (x >= 254 and y >= 322) else None)
    C.recolour(m, lambda x, y, c: "BROWN_DARK" if 235 <= x <= 237 and 315 <= y <= 323 else None)   # pommel's back
    C.hline(230, 256, 326, "BROWN_BLACK")
    # pommel: RIM over the top and down the front, OCHRE inside it
    C.line([(229, 318), (229, 317), (230, 316), (230, 315), (231, 314), (232, 313), (235, 313)], "RIM")
    C.vline(229, 319, 323, "OCHRE")
    C.line([(230, 317), (231, 316), (231, 315), (232, 314), (234, 314)], "OCHRE")
    # knob horn
    C.hline(233, 235, 311, "RIM")
    C.hline(233, 235, 312, "OCHRE")
    # the seat surface and the cantle's rim
    C.line([(238, 320), (240, 322), (241, 323), (244, 323), (246, 321), (248, 318), (249, 317)], "OCHRE")
    C.hline(250, 255, 316, "RIM")
    C.px(249, 317, "RIM")
    C.px(256, 317, "RIM")
    C.hline(250, 255, 317, "OCHRE")
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
    # breast collar across the shoulder, a ring at the point of the chest
    strap = [(230, 328), (227, 333), (223, 338), (219, 342), (216, 345)]
    C.line([(x, y + 2) for x, y in strap], "BROWN_BLACK", solid=True)
    C.line([(x, y + 1) for x, y in strap], "BROWN_DARK", solid=True)
    C.line(strap, "OCHRE", solid=True)
    C.px(215, 346, "LAMP")
    C.px(215, 347, "GOLD")
    C.px(216, 347, "GOLD")
    # saddle strings off the rear skirt
    C.vline(256, 327, 334, "OCHRE")
    C.vline(257, 328, 332, "BROWN_BLACK")


# coat and leather colours: no lone pixel of these is left on the horse (see _despeckle, _tidy)
COAT_NAMES = ("BROWN_BLACK", "BROWN_DARK", "BROWN", "BROWN_MID", "LEATHER", "RUST", "ORANGE", "SHADOW")


def _despeckle(C, keep):
    """Every coat and leather mark is a run or cluster of 2+ px: a lone pixel of one of these
    colours (no neighbour of its own colour, diagonals included) takes the colour most of its
    neighbours share. Pixels in `keep` (the hand-drawn head) are left alone."""
    names = set(COAT_NAMES)
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
                C.c[yy, xx] = max(sorted(set(opts)), key=opts.count)


def _reins(L):
    """Reins from the bit ring (197, 334), sagging to a low point by the forearm, then up to the
    rail post."""
    pts = []
    for i in range(0, 81):
        t = i / 80.0
        if t < 0.45:
            u = t / 0.45
            x = 197 + (216 - 197) * u
            y = 335 + (356 - 335) * (1 - (1 - u) ** 2)
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
    # the rope must not leave a lone coat or street pixel beside it
    coat = {P.rgb(n) for n in ("BROWN_DARK", "BROWN_BLACK", "BROWN", "RUST")}
    for x, y in seen:
        for dx, dy in ((0, -1), (0, 2), (-1, 0), (1, 0)):
            q = L.get(x + dx, y + dy)
            if q[3] == 0 or q[:3] not in coat:
                continue
            nb = [L.get(x + dx + i, y + dy + j)[:3] for i in (-1, 0, 1) for j in (-1, 0, 1) if i or j]
            if q[:3] not in nb:
                opts = [c for c in nb if c in coat]
                if opts:
                    L.px(x + dx, y + dy, max(sorted(set(opts)), key=opts.count) + (255,))


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
    ink = np.zeros_like(pad)
    ys, xs = np.nonzero(ring)
    for yy, xx in zip(ys, xs):
        x, y = int(xx) - 1 + X0, int(yy) - 1 + Y0
        if not near_body[yy, xx]:
            bg = L.get(x, y)
            if bg[3] == 0 or rev.get(tuple(bg[:3])) not in bright:
                continue
        ink[yy, xx] = True
    # an outline dot with no other outline pixel around it (where a rimmed edge meets a plain
    # one) is left off: it would read as a stray speck
    ink &= ~_isolated(ink)
    ys, xs = np.nonzero(ink)
    for yy, xx in zip(ys, xs):
        L.px(int(xx) - 1 + X0, int(yy) - 1 + Y0, "INK")
    for yy in range(h):
        for xx in range(w):
            v = C.c[yy, xx]
            if v is not None:
                L.px(xx + X0, yy + Y0, v)


def _shadow(L):
    """Cast shadow on the street, toward the camera (the sun is behind the horse): a solid
    BROWN_DARK core, BROWN_BLACK where the hooves meet the ground, and a ragged BROWN fringe
    (the next step up), 1-2 px deep, its edge wandering in 2 px steps. No dither, no checker;
    street pixels already darker than the fringe keep their colour."""
    rev = {P.rgb(n): n for n in P.NAMES}
    cx, cy, rx, ry = 236, 412, 37.0, 5.5
    contact = [(x0 - 1, x1 + 1, yb - 1, yb + 2) for x0, x1, yt, yb in HOOVES]
    for x in range(int(cx - rx) + 1, int(cx + rx)):
        u = (x - cx) / rx
        hh = ry * np.sqrt(1.0 - u * u)
        k = x // 2
        top = int(round(cy - hh + (hsh(k, 61) - 0.5) * 1.4))
        bot = int(round(cy + hh + (hsh(k, 62) - 0.5) * 1.4))
        uc = (x - cx) / (rx - 6)
        if abs(uc) < 1:
            hc = (ry - 1.2) * np.sqrt(1.0 - uc * uc)
            ctop = max(top + 1, int(round(cy - hc + (hsh(k, 63) - 0.5))))
            cbot = min(bot - 1, int(round(cy + hc + (hsh(k, 64) - 0.5))))
        else:
            ctop, cbot = 1, 0
        for y in range(top, bot + 1):
            g = L.get(x, y)
            if g[3] == 0:
                continue
            if ctop <= y <= cbot:
                hoof = any(xa <= x <= xb and ya <= y <= yb for xa, xb, ya, yb in contact)
                L.px(x, y, "BROWN_BLACK" if hoof else "BROWN_DARK")
            elif rev.get(tuple(g[:3])) not in ("BROWN_DARK", "BROWN_BLACK", "INK"):
                L.px(x, y, "BROWN")


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
    """The hitching rail in front of the horse; returns its own layer (what it covers)."""
    R = Layer()
    # the top rail runs right from the post (behind the barrel)
    for xa, xb, y0, y1 in ((249, 300, 354, 360),):
        R.rect(xa, y0, xb, y1, "BROWN")
        R.hline(xa, xb, y0, "OCHRE")
        R.hline(xa, xb, y0 + 1, "LEATHER")
        R.hline(xa, xb, y1, "BROWN_BLACK")
        R.hline(xa, xb, y1 - 1, "BROWN_DARK")
        for x in range(xa + 3, xb, 8):
            R.hline(x, x + 3, y0 + 3, "BROWN_DARK")
    _post(R, 244, 250, 350, 411)
    R.hline(245, 249, 361, "BROWN_BLACK")        # rail shadow on the post
    R.hline(245, 249, 403, "BROWN_BLACK")
    R.outline("INK", diag=False)
    L.im.alpha_composite(R.im)
    return R


def _tidy(L, C, keep, cover):
    """Last pass, once the reins and the rail lie over the horse: a coat or leather pixel they
    left alone takes the colour most of its neighbours share (ties in name order)."""
    names = set(COAT_NAMES)
    rev = {P.rgb(n): n for n in P.NAMES}

    def name(x, y):
        p = L.get(x, y)
        return rev.get(tuple(p[:3])) if p[3] else None
    ys, xs = np.nonzero(C.alpha() & ~keep)
    for yy, xx in zip(ys, xs):
        x, y = int(xx) + X0, int(yy) + Y0
        v = name(x, y)
        if v not in names or cover.get(x, y)[3]:
            continue
        nb = [name(x + i, y + j) for j in (-1, 0, 1) for i in (-1, 0, 1) if i or j]
        if v in nb:
            continue
        opts = [n for n in nb if n in names]
        if opts:
            L.px(x, y, max(sorted(set(opts)), key=opts.count))


def _low_board(L):
    """The rail's low board, behind the legs: it starts behind the far fore and runs past the
    post behind the barrel (drawn before the horse, so the legs stand in front of it)."""
    xa, xb, y0, y1 = 229, 300, 398, 402
    L.rect(xa, y0, xb, y1, "BROWN")
    L.hline(xa, xb, y0, "OCHRE")
    L.hline(xa, xb, y0 + 1, "LEATHER")
    L.hline(xa, xb, y1, "BROWN_BLACK")
    L.hline(xa, xb, y1 - 1, "BROWN_DARK")
    for x in range(xa + 3, xb, 8):
        L.hline(x, x + 3, y0 + 3, "BROWN_DARK")
    L.hline(xa, xb, y0 - 1, "INK")
    L.hline(xa, xb, y1 + 1, "INK")


def _tidy_seams(L, before):
    """The horse, its shadow and the rail must not strand a background pixel: one that had a
    same-coloured neighbour before they were drawn and has none after takes the colour most of
    its neighbours share (ties in name order). Pixels that were alone already (a lamp glint on
    the wall, a pebble on the street) are left as they are."""
    rev = {P.rgb(n): n for n in P.NAMES}
    b = np.array(before).astype(np.int64)
    a = np.array(L.im).astype(np.int64)
    kb = (b[..., 0] << 16) | (b[..., 1] << 8) | b[..., 2]
    ka = (a[..., 0] << 16) | (a[..., 1] << 8) | a[..., 2]
    changed = (b != a).any(2)
    ring = [(i, j) for j in (-1, 0, 1) for i in (-1, 0, 1) if i or j]
    fixes = []
    for y in range(Y0 + OY - 1, Y1 + OY + 2):
        for x in range(X0 + OX - 1, X1 + OX + 2):
            if changed[y, x] or a[y, x, 3] == 0 or not changed[y - 1:y + 2, x - 1:x + 2].any():
                continue
            if any(ka[y + j, x + i] == ka[y, x] for i, j in ring):
                continue
            if not any(kb[y + j, x + i] == kb[y, x] for i, j in ring):
                continue
            opts = [rev[tuple(int(v) for v in a[y + j, x + i, :3])] for i, j in ring if a[y + j, x + i, 3]]
            if opts:
                fixes.append((x - OX, y - OY, max(sorted(set(opts)), key=opts.count)))
    for x, y, c in fixes:
        L.px(x, y, c)


def draw_street_props(L, rng):
    """The saddled bay at the hitching rail on the right side of the street (town layer).
    `rng` is unused: every irregularity here comes from hsh(), so the horse never shifts when
    another layer's random draws change."""
    before = L.im.copy()
    _shadow(L)
    _low_board(L)
    C, parts, rimmed = _horse()
    _tack(C)
    _despeckle(C, parts["head"])
    rimmed |= C.is_(("RIM", "RIM_HOT"))
    _composite(L, C, rimmed)
    _reins(L)
    R = _rail(L)
    _tidy(L, C, parts["head"], R)
    _tidy_seams(L, before)
