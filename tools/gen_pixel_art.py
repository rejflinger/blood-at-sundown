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
# masks: boolean numpy arrays [h, w], drawn with PIL in mode "1" (never antialiased)

def canvas(w, h):
    im = Image.new("1", (w, h), 0)
    return im, ImageDraw.Draw(im)


def to_mask(im):
    return np.array(im, dtype=bool)


def ellipse(d, box, fill):
    d.ellipse(box, fill=fill)


def slab(d, x0, y0, x1, y1):
    d.rectangle((x0, y0, x1, y1), fill=1)


def letter(ch, H, W, S, T):
    """Western slab letter as a mask. S = vertical stem width, T = horizontal thickness."""
    pad = 3  # room for serifs left and right
    im, d = canvas(W + pad * 2, H)
    o = pad
    R = o + W - 1
    B = H - 1
    mid = H // 2
    if ch == "B":
        top_h = mid - 1
        for (y0, y1, extra) in ((0, top_h + T // 2, 0), (top_h - T // 2 + 1, B, 1)):
            rw = o + int(W * 0.5)
            d.rectangle((o, y0, rw, y1), fill=1)
            d.ellipse((o + W // 5, y0, R - (1 - extra) * 2, y1), fill=1)
            d.rectangle((o + S, y0 + T, rw, y1 - T), fill=0)
            d.ellipse((o + W // 5 + S, y0 + T, R - (1 - extra) * 2 - S, y1 - T), fill=0)
        d.rectangle((o, 0, o + S - 1, B), fill=1)
        slab(d, o - 2, 0, o + S + 1, T - 1)
        slab(d, o - 2, B - T + 1, o + S + 1, B)
    elif ch == "D":
        d.rectangle((o, 0, o + W // 2, B), fill=1)
        d.ellipse((o + 1, 0, R, B), fill=1)
        d.rectangle((o + S, T, o + W // 2, B - T), fill=0)
        d.ellipse((o + 1 + S, T, R - S, B - T), fill=0)
        d.rectangle((o, 0, o + S - 1, B), fill=1)
        slab(d, o - 2, 0, o + S + 1, T - 1)
        slab(d, o - 2, B - T + 1, o + S + 1, B)
    elif ch == "O":
        d.ellipse((o, 0, R, B), fill=1)
        d.ellipse((o + S, T, R - S, B - T), fill=0)
    elif ch == "L":
        d.rectangle((o + 1, 0, o + S, B), fill=1)
        d.rectangle((o + 1, B - T + 1, R, B), fill=1)
        d.rectangle((R - 1, B - T - 2, R, B), fill=1)  # upturned toe
        slab(d, o - 1, 0, o + S + 3, T - 2)
        slab(d, o - 1, B - T + 1, o + 1, B)
    elif ch == "A":
        cx = o + W // 2
        d.polygon([(cx - 2, 0), (cx + 1, 0), (o + S + 1, B), (o + 1, B)], fill=1)
        d.polygon([(cx - 1, 0), (cx + 2, 0), (R - 1, B), (R - S - 1, B)], fill=1)
        cy = int(H * 0.62)
        d.rectangle((o + S - 1, cy, R - S + 1, cy + T - 1), fill=1)
        slab(d, o - 1, B - T + 2, o + S + 3, B)
        slab(d, R - S - 3, B - T + 2, R + 1, B)
    elif ch == "T":
        cx = o + W // 2
        d.rectangle((o, 0, R, T - 1), fill=1)
        d.rectangle((o, 0, o + 1, T + 1), fill=1)
        d.rectangle((R - 1, 0, R, T + 1), fill=1)
        d.rectangle((cx - S // 2, 0, cx - S // 2 + S - 1, B), fill=1)
        slab(d, cx - S // 2 - 2, B - T + 2, cx - S // 2 + S + 1, B)
    elif ch == "S":
        yt = mid + T // 2
        yb = mid - (T + 1) // 2
        top, dt = canvas(W + pad * 2, H)
        dt.ellipse((o, 0, R, yt), fill=1)
        dt.ellipse((o + S, T, R - S, yt - T), fill=0)
        tm = to_mask(top)
        tm[(yt // 2):, o + W // 2:] = False
        bot, db = canvas(W + pad * 2, H)
        db.ellipse((o, yb, R, B), fill=1)
        db.ellipse((o + S, yb + T, R - S, B - T), fill=0)
        bm = to_mask(bot)
        bm[: yb + (B - yb) // 2, : o + W // 2] = False
        m = tm | bm
        m[max(0, yt // 2 - 2): yt // 2 + 1, R - S + 1: R + 1] = True  # top terminal
        m[yb + (B - yb) // 2 - 1: yb + (B - yb) // 2 + 2, o: o + S] = True  # bottom terminal
        return m
    elif ch == "U":
        cy = B - W // 2
        d.ellipse((o, cy - W // 2, R, B), fill=1)
        d.ellipse((o + S, cy - W // 2 + T, R - S, B - T), fill=0)
        d.rectangle((o, 0, R, cy - 1), fill=0)
        d.rectangle((o, 0, o + S - 1, cy), fill=1)
        d.rectangle((R - S + 1, 0, R, cy), fill=1)
        slab(d, o - 2, 0, o + S + 1, T - 1)
        slab(d, R - S - 1, 0, R + 2, T - 1)
    elif ch == "N":
        s2 = max(2, S - 2)
        d.rectangle((o, 0, o + s2 - 1, B), fill=1)
        d.rectangle((R - s2 + 1, 0, R, B), fill=1)
        d.polygon([(o, 0), (o + S, 0), (R, B), (R - S, B)], fill=1)
        slab(d, o - 2, 0, o + S, T - 1)
        slab(d, o - 2, B - T + 1, o + s2 + 1, B)
        slab(d, R - s2 - 2, 0, R + 2, T - 1)
    elif ch == "W":
        q = W // 4
        stroke = S - 1
        d.polygon([(o, 0), (o + stroke, 0), (o + q + stroke, B), (o + q, B)], fill=1)
        d.polygon([(o + q, B), (o + q + stroke - 1, B), (o + 2 * q + 1, int(H * 0.25)), (o + 2 * q - stroke + 1, int(H * 0.25))], fill=1)
        d.polygon([(o + 2 * q - 1, int(H * 0.25)), (o + 2 * q + stroke - 1, int(H * 0.25)), (R - q + 1, B), (R - q - stroke + 2, B)], fill=1)
        d.polygon([(R - stroke, 0), (R, 0), (R - q + 1, B), (R - q - stroke + 1, B)], fill=1)
        slab(d, o - 2, 0, o + stroke + 1, T - 2)
        slab(d, R - stroke - 1, 0, R + 2, T - 2)
    else:
        raise ValueError(ch)
    return to_mask(im)


def trim(m):
    cols = np.where(m.any(axis=0))[0]
    return m[:, cols[0]: cols[-1] + 1]


def word(text, H, widths, S, T, gap):
    parts = [trim(letter(ch, H, widths[ch], S, T)) for ch in text]
    w = sum(p.shape[1] for p in parts) + gap * (len(parts) - 1)
    out = np.zeros((H, w), dtype=bool)
    x = 0
    for p in parts:
        out[:, x: x + p.shape[1]] |= p
        x += p.shape[1] + gap
    return out


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


def paint_word(img, m, x0, y0, light, mid, dark, grit, highlight, rng, drips=0):
    """Fill a word mask with a hard banded ramp, sparse grit, edge highlight and drips."""
    h, w = m.shape
    drip_mask = np.zeros((h + 14, w), dtype=bool)
    drip_mask[:h] = m
    if drips:
        bottoms = [x for x in range(1, w - 1) if m[h - 1, x] and m[h - 1, x - 1] and m[h - 1, x + 1]]
        rng.shuffle(bottoms)
        used = []
        for x in bottoms:
            if len(used) >= drips:
                break
            if any(abs(x - u) < 5 for u in used):
                continue
            used.append(x)
            length = rng.randint(3, 11)
            drip_mask[h: h + length, x] = True
            if length > 5:
                drip_mask[h: h + length - 3, x + 1] = True
            drip_mask[h + length - 1: h + length + 1, x - 1: x + 1] = True  # bulb
    full = drip_mask
    fh = full.shape[0]
    outline = dilate(full) & ~full
    shadow = np.zeros_like(full)
    shadow[2:, 1:] = (outline | full)[:-2, :-1]
    shadow &= ~(outline | full)
    for y in range(fh):
        for x in range(w):
            px, py = x0 + x, y0 + y
            if not (0 <= px < img.width and 0 <= py < img.height):
                continue
            if full[y, x]:
                t = y / max(1, h - 1)
                if y >= h:
                    col = mid
                elif t < 0.55:
                    col = light
                elif t < 0.8:
                    col = light if BAYER4[y % 4, x % 4] > (t - 0.55) / 0.25 else mid
                else:
                    col = mid if BAYER4[y % 4, x % 4] > (t - 0.8) / 0.35 else dark
                if y < h and y > 0 and not full[y - 1, x]:
                    col = highlight
                if y < h and rng.random() < grit and 1 < y < h - 2:
                    col = dark
                img.putpixel((px, py), col)
            elif outline[y, x]:
                img.putpixel((px, py), C("INK"))
            elif shadow[y, x]:
                img.putpixel((px, py), C("CHARCOAL"))
    return fh + 2


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


def gen_logo():
    """BLOOD in red over SUNDOWN in cream, both on a rough ink splatter with drips."""
    rng = random.Random(1873)
    W, Hh = 214, 140
    img = Image.new("RGBA", (W, Hh), (0, 0, 0, 0))
    blood = word("BLOOD", 50, {"B": 32, "L": 28, "O": 33, "D": 33}, 10, 7, 1)
    sundown = word("SUNDOWN", 38, {"S": 22, "U": 22, "N": 24, "D": 22, "O": 23, "W": 31}, 7, 5, 1)
    bx, by = (W - blood.shape[1]) // 2, 6
    sx, sy = (W - sundown.shape[1]) // 2, 81

    # the splatter: letters grown by a few pixels with a ragged edge and drips
    halo = np.zeros((Hh, W), dtype=bool)
    halo[by:by + blood.shape[0], bx:bx + blood.shape[1]] |= blood
    halo[sy:sy + sundown.shape[0], sx:sx + sundown.shape[1]] |= sundown
    halo[63:73, 30:W - 30] = True
    for i in range(4):
        halo = dilate(halo)
    for _ in range(2):
        grown = dilate(halo)
        noise = np.array([[rng.random() < 0.45 for _ in range(W)] for _ in range(Hh)])
        halo = halo | (grown & noise)
    bottom = [x for x in range(W) if halo[:, x].any()]
    for x in rng.sample(bottom, 22):
        ys = np.nonzero(halo[:, x])[0]
        y0 = ys[-1]
        if y0 < 40 and rng.random() < 0.5:
            continue
        ln = rng.randint(4, 16)
        halo[y0:min(Hh, y0 + ln), x] = True
        if ln > 6:
            halo[y0:min(Hh, y0 + ln - 3), min(W - 1, x + 1)] = True
    for y, x in zip(*np.nonzero(halo)):
        img.putpixel((int(x), int(y)), C("INK"))
    # dark red flecks around the edge of the splatter
    edge = halo & ~np.roll(halo, 1, 0) | halo & ~np.roll(halo, -1, 1)
    for y, x in zip(*np.nonzero(edge)):
        if rng.random() < 0.25:
            img.putpixel((int(x), int(y)), C("WINE"))
    for _ in range(40):
        x, y = rng.randint(0, W - 1), rng.randint(0, Hh - 1)
        if not halo[y, x] and dilate(halo)[y, x]:
            img.putpixel((x, y), C("WINE"))

    paint_word(img, blood, bx, by, C("RED"), C("BLOOD"), C("MAROON"), 0.05, C("RED_LIGHT"), rng, drips=8)
    # grunge: a few darker blotches inside BLOOD
    for _ in range(80):
        x, y = rng.randint(0, blood.shape[1] - 2), rng.randint(3, blood.shape[0] - 3)
        if blood[y, x] and blood[y, x + 1]:
            img.putpixel((bx + x, by + y), C("BLOOD"))
            img.putpixel((bx + x + 1, by + y), C("BLOOD"))

    # "AT" between ruled lines with diamond ends
    tw = text_width("AT")
    ax = (W - tw) // 2
    at_y = 62
    draw_font_text(img, "AT", ax, at_y, C("CREAM"))
    for side in (-1, 1):
        x0 = ax - 4 if side < 0 else ax + tw + 3
        for i in range(44):
            img.putpixel((x0 + side * i, at_y + 4), C("TAN"))
        dx = x0 + side * 44
        for ddx, ddy in ((0, -1), (0, 1), (side, 0), (0, 0)):
            img.putpixel((dx + ddx, at_y + 4 + ddy), C("CREAM"))

    paint_word(img, sundown, sx, sy, C("CREAM"), C("CREAM_SHADE"), C("TAN"), 0.03, C("PALE"), rng, drips=0)
    for _ in range(46):  # blood spatter on the cream letters
        x = rng.randint(1, sundown.shape[1] - 3)
        y = rng.randint(1, sundown.shape[0] - 2)
        if sundown[y, x]:
            img.putpixel((sx + x, sy + y), C("RED") if rng.random() < 0.6 else C("BLOOD"))
            if rng.random() < 0.4 and sundown[y, x + 1]:
                img.putpixel((sx + x + 1, sy + y), C("BLOOD"))
    img = img.crop(img.getbbox())
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
