"""Renders the street scene into a private folder and puts it beside the references.

    python3 tools/preview_scene.py --out /some/dir [--ref a.png --ref b.png]

Writes <out>/layers/*.png, <out>/native.png (270 x 584 view with the logo and the title
button rectangles roughly where Godot puts them), <out>/preview_2x.png and <out>/compare.png
(ours at 2x beside each reference scaled to the same height). Nothing in assets/ is touched,
so several people can preview at once. The real frame is still the Godot --shot render.
"""
import argparse
import os
import sys

if os.environ.get("PYTHONHASHSEED") != "0":
    os.environ["PYTHONHASHSEED"] = "0"
    os.execv(sys.executable, [sys.executable] + sys.argv)

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import art_scene  # noqa: E402
import palette as P  # noqa: E402
from scene.common import OX, OY, SAFE_W, SAFE_H  # noqa: E402

# Title layout from scripts/ui.gd (native pixels): (x, y, w, h, red?)
BUTTONS = [(78, 318, 116, 38, True), (78, 362, 116, 30, False), (78, 398, 116, 30, False),
           (78, 446, 116, 30, False), (78, 482, 116, 30, False),
           (32, 528, 32, 32, False), (119, 528, 32, 32, False), (206, 528, 32, 32, False)]


def c(name):
    return P.rgb(name, 0.0) + (255,)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--ref", action="append", default=[])
    ap.add_argument("--no-ui", action="store_true", help="scene only, no logo or buttons")
    a = ap.parse_args()
    layers_dir = os.path.join(a.out, "layers")
    os.makedirs(layers_dir, exist_ok=True)
    comp = art_scene.build(layers_dir)
    allowed = {c_ + (255,) for c_ in P.all_colours()}
    bad = []
    for name in art_scene.LAYER_NAMES:
        im = Image.open(os.path.join(layers_dir, name + ".png")).convert("RGBA")
        if im.size != (SAFE_W + 2 * OX, SAFE_H + 2 * OY):
            bad.append("%s: size %s" % (name, im.size))
        cols = {px for _n, px in im.getcolors(1 << 20) if px[3] != 0}
        stray = [px for px in cols if px not in allowed]
        if stray:
            bad.append("%s: %d colours outside the palette or not fully opaque, e.g. %s" % (name, len(stray), stray[:3]))
    print("PIXEL RULES:", "PASS" if not bad else "FAIL\n  " + "\n  ".join(bad))
    view = comp.crop((OX, OY, OX + SAFE_W, OY + SAFE_H))
    if not a.no_ui:
        logo = Image.open(os.path.join(ROOT, "assets", "ui", "logo.png"))
        view.alpha_composite(logo, ((SAFE_W - logo.width) // 2, 16))
        d = ImageDraw.Draw(view)
        for x, y, w, h, red in BUTTONS:
            d.rectangle((x, y, x + w - 1, y + h - 1), fill=c("INK"))
            d.rectangle((x + 1, y + 1, x + w - 2, y + h - 2), fill=c("ORANGE" if red else "OCHRE"))
            d.rectangle((x + 3, y + 3, x + w - 4, y + h - 4), fill=c("BLOOD" if red else "BROWN_DARK"))
    view.save(os.path.join(a.out, "native.png"))
    big = view.resize((SAFE_W * 2, SAFE_H * 2), Image.NEAREST)
    big.save(os.path.join(a.out, "preview_2x.png"))
    refs = [Image.open(r).convert("RGBA") for r in a.ref if os.path.exists(r)]
    refs = [r.resize((round(r.width * big.height / r.height), big.height)) for r in refs]
    cw = big.width + sum(r.width + 16 for r in refs)
    cmp_ = Image.new("RGBA", (cw, big.height), (0, 0, 0, 255))
    cmp_.paste(big, (0, 0))
    x = big.width + 16
    for r in refs:
        cmp_.paste(r, (x, 0))
        x += r.width + 16
    cmp_.save(os.path.join(a.out, "compare.png"))
    print("wrote", os.path.join(a.out, "compare.png"))


if __name__ == "__main__":
    main()
