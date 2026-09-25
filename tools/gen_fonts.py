"""Bitmap fonts for Blood at Sundown, written as BMFont (.fnt text + .png page).

Three faces, all hand-authored here as '#' bitmaps:
  tiny  5 px caps, mixed case, 8 px line  (HUD rows, sub lines, captions)
  body  7 px caps, mixed case, 10 px line (card text, prompts)
  bold  body thickened one pixel sideways (buttons, DRAW at 2x and up)
  tall  bold stretched to 10 px caps (PLAY, card titles)
  tiny_ol, bold_ol  cream glyphs with a baked ink ring, for text straight over the scene

Glyph pixels are white; the game tints them with palette colours. Godot imports .fnt
natively; ui.gd sets integer-only scaling so a font drawn at 2x its size stays crisp.

Run: python3 tools/gen_fonts.py
"""
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "fonts")


def g(s):
    return s.split()


# --- tiny: cap height 5, rows 0-4 above the baseline, 5-6 descender ----------------------
TINY_ROWS, TINY_BASE = 7, 5
TINY = {
    "A": g(".#. #.# ### #.# #.#"), "B": g("##. #.# ##. #.# ##."),
    "C": g(".## #.. #.. #.. .##"), "D": g("##. #.# #.# #.# ##."),
    "E": g("### #.. ##. #.. ###"), "F": g("### #.. ##. #.. #.."),
    "G": g(".## #.. #.# #.# .##"), "H": g("#.# #.# ### #.# #.#"),
    "I": g("### .#. .#. .#. ###"), "J": g("..# ..# ..# #.# .#."),
    "K": g("#.# #.# ##. #.# #.#"), "L": g("#.. #.. #.. #.. ###"),
    "M": g("#...# ##.## #.#.# #...# #...#"), "N": g("#..# ##.# #.## #..# #..#"),
    "O": g(".#. #.# #.# #.# .#."), "P": g("##. #.# ##. #.. #.."),
    "Q": g(".#. #.# #.# ##. .##"), "R": g("##. #.# ##. #.# #.#"),
    "S": g(".## #.. .#. ..# ##."), "T": g("### .#. .#. .#. .#."),
    "U": g("#.# #.# #.# #.# ###"), "V": g("#.# #.# #.# #.# .#."),
    "W": g("#...# #...# #.#.# ##.## #...#"), "X": g("#.# #.# .#. #.# #.#"),
    "Y": g("#.# #.# .#. .#. .#."), "Z": g("### ..# .#. #.. ###"),
    "0": g("### #.# #.# #.# ###"), "1": g(".#. ##. .#. .#. ###"),
    "2": g("##. ..# .#. #.. ###"), "3": g("##. ..# .#. ..# ##."),
    "4": g("#.# #.# ### ..# ..#"), "5": g("### #.. ##. ..# ##."),
    "6": g(".## #.. ### #.# ###"), "7": g("### ..# .#. .#. .#."),
    "8": g("### #.# ### #.# ###"), "9": g("### #.# ### ..# ##."),
    "a": g("... .## #.# #.# .##"), "b": g("#.. ##. #.# #.# ##."),
    "c": g("... .## #.. #.. .##"), "d": g("..# .## #.# #.# .##"),
    "e": g("... .#. ### #.. .##"), "f": g(".# #. ## #. #."),
    "g": g("... .## #.# #.# .## ..# ##."), "h": g("#.. ##. #.# #.# #.#"),
    "i": g("# . # # #"), "j": g(".# .. .# .# .# .# #."),
    "k": g("#.. #.# ##. #.# #.#"), "l": g("#. #. #. #. .#"),
    "m": g("..... ##.#. #.#.# #.#.# #.#.#"), "n": g("... ##. #.# #.# #.#"),
    "o": g("... .#. #.# #.# .#."), "p": g("... ##. #.# #.# ##. #.. #.."),
    "q": g("... .## #.# #.# .## ..# ..#"), "r": g("... #.# ##. #.. #.."),
    "s": g("... .## #.. ..# ##."), "t": g(".#. ### .#. .#. ..#"),
    "u": g("... #.# #.# #.# .##"), "v": g("... #.# #.# #.# .#."),
    "w": g("..... #...# #.#.# #.#.# .#.#."), "x": g("... #.# .#. .#. #.#"),
    "y": g("... #.# #.# #.# .## ..# ##."), "z": g("... ### .#. #.. ###"),
    ".": g(". . . . #"), ",": g(". . . . # #"), ":": g(". # . # ."),
    ";": g(". # . . # #"), "!": g("# # # . #"), "?": g("##. ..# .#. ... .#."),
    "'": g("# # . . ."), "\"": g("#.# #.# ... ... ..."), "-": g("... ... ### ... ..."),
    "+": g("... .#. ### .#. ..."), "/": g("..# ..# .#. #.. #.."),
    "(": g(".# #. #. #. .#"), ")": g("#. .# .# .# #."),
    "$": g(".## ##. .#. .## ##."), "%": g("#.# ..# .#. #.. #.#"),
    "·": g(". . # . ."), "#": g("#.# ### #.# ### #.#"),
    "<": g("..# .#. #.. .#. ..#"), ">": g("#.. .#. ..# .#. #.."),
    "=": g("... ### ... ### ..."), "_": g("... ... ... ... ###"),
    "*": g("#.# .#. #.# ... ..."), "&": g(".#. #.# .#. #.# .##"),
    "[": g("## #. #. #. ##"), "]": g("## .# .# .# ##"),
}
TINY_SPACE = 3

# --- body: cap height 7, rows 0-6 above the baseline, 7-8 descender ----------------------
BODY_ROWS, BODY_BASE = 9, 7
BODY = {
    "A": g(".###. #...# #...# ##### #...# #...# #...#"),
    "B": g("####. #...# #...# ####. #...# #...# ####."),
    "C": g(".###. #...# #.... #.... #.... #...# .###."),
    "D": g("####. #...# #...# #...# #...# #...# ####."),
    "E": g("##### #.... #.... ####. #.... #.... #####"),
    "F": g("##### #.... #.... ####. #.... #.... #...."),
    "G": g(".###. #...# #.... #.### #...# #...# .####"),
    "H": g("#...# #...# #...# ##### #...# #...# #...#"),
    "I": g("### .#. .#. .#. .#. .#. ###"),
    "J": g("..### ...#. ...#. ...#. #..#. #..#. .##.."),
    "K": g("#...# #..#. #.#.. ##... #.#.. #..#. #...#"),
    "L": g("#.... #.... #.... #.... #.... #.... #####"),
    "M": g("#...# ##.## #.#.# #.#.# #...# #...# #...#"),
    "N": g("#...# ##..# ##..# #.#.# #..## #..## #...#"),
    "O": g(".###. #...# #...# #...# #...# #...# .###."),
    "P": g("####. #...# #...# ####. #.... #.... #...."),
    "Q": g(".###. #...# #...# #...# #.#.# #..#. .##.#"),
    "R": g("####. #...# #...# ####. #.#.. #..#. #...#"),
    "S": g(".###. #...# #.... .###. ....# #...# .###."),
    "T": g("##### ..#.. ..#.. ..#.. ..#.. ..#.. ..#.."),
    "U": g("#...# #...# #...# #...# #...# #...# .###."),
    "V": g("#...# #...# #...# #...# #...# .#.#. ..#.."),
    "W": g("#...# #...# #...# #.#.# #.#.# ##.## #...#"),
    "X": g("#...# #...# .#.#. ..#.. .#.#. #...# #...#"),
    "Y": g("#...# #...# .#.#. ..#.. ..#.. ..#.. ..#.."),
    "Z": g("##### ....# ...#. ..#.. .#... #.... #####"),
    "0": g(".###. #...# #..## #.#.# ##..# #...# .###."),
    "1": g("..#.. .##.. ..#.. ..#.. ..#.. ..#.. .###."),
    "2": g(".###. #...# ....# ...#. ..#.. .#... #####"),
    "3": g(".###. #...# ....# ..##. ....# #...# .###."),
    "4": g("...#. ..##. .#.#. #..#. ##### ...#. ...#."),
    "5": g("##### #.... ####. ....# ....# #...# .###."),
    "6": g(".###. #.... #.... ####. #...# #...# .###."),
    "7": g("##### ....# ...#. ..#.. ..#.. ..#.. ..#.."),
    "8": g(".###. #...# #...# .###. #...# #...# .###."),
    "9": g(".###. #...# #...# .#### ....# ....# .###."),
    "a": g("..... ..... .###. ....# .#### #...# .####"),
    "b": g("#.... #.... ####. #...# #...# #...# ####."),
    "c": g("..... ..... .###. #.... #.... #.... .###."),
    "d": g("....# ....# .#### #...# #...# #...# .####"),
    "e": g("..... ..... .###. #...# ##### #.... .###."),
    "f": g("..## .#.. ###. .#.. .#.. .#.. .#.."),
    "g": g("..... ..... .#### #...# #...# .#### ....# ....# .###."),
    "h": g("#.... #.... ####. #...# #...# #...# #...#"),
    "i": g(".#. ... ##. .#. .#. .#. ###"),
    "j": g("..# ... .## ..# ..# ..# ..# #.# .#."),
    "k": g("#... #... #..# #.#. ##.. #.#. #..#"),
    "l": g("##. .#. .#. .#. .#. .#. ###"),
    "m": g("..... ..... ##.#. #.#.# #.#.# #.#.# #.#.#"),
    "n": g("..... ..... ####. #...# #...# #...# #...#"),
    "o": g("..... ..... .###. #...# #...# #...# .###."),
    "p": g("..... ..... ####. #...# #...# #...# ####. #.... #...."),
    "q": g("..... ..... .#### #...# #...# #...# .#### ....# ....#"),
    "r": g(".... .... #.## ##.. #... #... #..."),
    "s": g("..... ..... .#### #.... .###. ....# ####."),
    "t": g(".#.. .#.. ###. .#.. .#.. .#.. ..##"),
    "u": g("..... ..... #...# #...# #...# #...# .####"),
    "v": g("..... ..... #...# #...# #...# .#.#. ..#.."),
    "w": g("..... ..... #...# #...# #.#.# #.#.# .#.#."),
    "x": g("..... ..... #...# .#.#. ..#.. .#.#. #...#"),
    "y": g("..... ..... #...# #...# #...# .#### ....# ....# .###."),
    "z": g("..... ..... ##### ...#. ..#.. .#... #####"),
    ".": g(". . . . . . #"), ",": g(". . . . . . # #"),
    ":": g(". . # . . . #"), ";": g(". . # . . . # #"),
    "!": g("# # # # # . #"), "?": g(".###. #...# ....# ...#. ..#.. ..... ..#.."),
    "'": g("# # . . . . ."), "\"": g("#.# #.# ... ... ... ... ..."),
    "-": g(".... .... .... #### .... .... ...."),
    "+": g("..... ..#.. ..#.. ##### ..#.. ..#.. ....."),
    "/": g("....# ...#. ...#. ..#.. .#... .#... #...."),
    "(": g("..# .#. #.. #.. #.. .#. ..#"), ")": g("#.. .#. ..# ..# ..# .#. #.."),
    "$": g("..#.. .#### #.#.. .###. ..#.# ####. ..#.."),
    "%": g("##..# ##.#. ...#. ..#.. .#... .#.## #..##"),
    "·": g(". . . # . . ."),
    "#": g(".#.#. ##### .#.#. .#.#. ##### .#.#. ....."),
    "<": g("...#. ..#.. .#... #.... .#... ..#.. ...#."),
    ">": g(".#... ..#.. ...#. ....# ...#. ..#.. .#..."),
    "=": g("..... ..... ##### ..... ##### ..... ....."),
    "_": g("..... ..... ..... ..... ..... ..... #####"),
    "*": g("..... #.#.# .###. #.#.# ..... ..... ....."),
    "&": g(".##.. #..#. .##.. .#... #.#.# #..#. .##.#"),
    "[": g("### #.. #.. #.. #.. #.. ###"), "]": g("### ..# ..# ..# ..# ..# ###"),
}
BODY_SPACE = 4


def pad(rows, total):
    w = max(len(r) for r in rows)
    rows = [r.ljust(w, ".") for r in rows]
    return rows + ["." * w] * (total - len(rows))


def embolden(rows):
    """Thicken every stroke one pixel to the right."""
    w = len(rows[0]) + 1
    out = []
    for r in rows:
        r = r + "."
        out.append("".join("#" if (r[x] == "#" or (x > 0 and r[x - 1] == "#")) else "." for x in range(w)))
    return out


def stretch_tall(rows, base):
    """7 px caps to 10 px: repeat cap rows 1, 3 and 5; keep descenders."""
    order = [0, 1, 1, 2, 3, 3, 4, 5, 5, 6] + list(range(base, len(rows)))
    return [rows[i] for i in order]


def outlined(rows):
    """Pad one pixel all round and mark the 8-neighbour ring with 'o'."""
    w = len(rows[0]) + 2
    grid = ["." * w] + ["." + r + "." for r in rows] + ["." * w]
    out = []
    for y in range(len(grid)):
        line = ""
        for x in range(w):
            if grid[y][x] == "#":
                line += "#"
            elif any(0 <= y + dy < len(grid) and 0 <= x + dx < w and grid[y + dy][x + dx] == "#"
                     for dy in (-1, 0, 1) for dx in (-1, 0, 1)):
                line += "o"
            else:
                line += "."
        out.append(line)
    return out


FILL = (243, 226, 189, 255)   # palette CREAM
RING = (27, 16, 34, 255)      # palette INK


def build(name, glyphs, rows, base, space, spacing, bold=False, tall=False, outline=False):
    cells = {}
    for ch, bm in glyphs.items():
        bm = pad(bm, rows)
        if bold:
            bm = embolden(bm)
        if tall:
            bm = stretch_tall(bm, base)
        if outline:
            bm = outlined(bm)
        cells[ch] = bm
    if tall:
        base += 3
        rows += 3
    line_h = rows + 1
    ch_h = rows + (2 if outline else 0)
    page_w = 256
    x, y = 1, 1
    placed = {}
    for ch in sorted(cells):
        w = len(cells[ch][0])
        if x + w + 1 > page_w:
            x, y = 1, y + ch_h + 1
        placed[ch] = (x, y, w)
        x += w + 1
    page_h = 1
    while page_h < y + ch_h + 1:
        page_h *= 2
    img = Image.new("RGBA", (page_w, page_h), (0, 0, 0, 0))
    for ch, (px, py, w) in placed.items():
        for ry, r in enumerate(cells[ch]):
            for rx, c in enumerate(r):
                if c == "#":
                    img.putpixel((px + rx, py + ry), FILL if outline else (255, 255, 255, 255))
                elif c == "o":
                    img.putpixel((px + rx, py + ry), RING)
    img.save(os.path.join(OUT, name + ".png"))
    chnl = "alphaChnl=0 redChnl=0 greenChnl=0 blueChnl=0" if outline else "alphaChnl=0 redChnl=4 greenChnl=4 blueChnl=4"
    lines = [
        'info face="%s" size=%d bold=%d italic=0 charset="" unicode=1 stretchH=100 smooth=0 aa=1 padding=0,0,0,0 spacing=1,1 outline=%d'
        % (name, line_h, 1 if bold else 0, 1 if outline else 0),
        "common lineHeight=%d base=%d scaleW=%d scaleH=%d pages=1 packed=0 %s"
        % (line_h, base, page_w, page_h, chnl),
        'page id=0 file="%s.png"' % name,
        "chars count=%d" % (len(placed) + 1),
        "char id=32 x=0 y=0 width=0 height=0 xoffset=0 yoffset=0 xadvance=%d page=0 chnl=15" % space,
    ]
    off = -1 if outline else 0
    for ch in sorted(placed, key=ord):
        px, py, w = placed[ch]
        adv = (w - 2 if outline else w) + spacing
        lines.append(
            "char id=%d x=%d y=%d width=%d height=%d xoffset=%d yoffset=%d xadvance=%d page=0 chnl=15"
            % (ord(ch), px, py, w, ch_h, off, off, adv)
        )
    with open(os.path.join(OUT, name + ".fnt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("font %-12s %3d glyphs, line %d px, page %dx%d" % (name, len(placed), line_h, page_w, page_h))


def main():
    os.makedirs(OUT, exist_ok=True)
    build("tiny", TINY, TINY_ROWS, TINY_BASE, TINY_SPACE, 1)
    build("body", BODY, BODY_ROWS, BODY_BASE, BODY_SPACE, 1)
    build("bold", BODY, BODY_ROWS, BODY_BASE, BODY_SPACE + 1, 1, bold=True)
    build("tall", BODY, BODY_ROWS, BODY_BASE, BODY_SPACE + 1, 1, bold=True, tall=True)
    # cream glyphs with a baked ink ring, for text laid straight over the scene
    build("tiny_ol", TINY, TINY_ROWS, TINY_BASE, TINY_SPACE + 1, 1, outline=True)
    build("bold_ol", BODY, BODY_ROWS, BODY_BASE, BODY_SPACE + 1, 1, bold=True, outline=True)


if __name__ == "__main__":
    main()
