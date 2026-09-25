"""The Sundown street at dusk: sky, mesas, town, props and the player seen from behind.

Drawn at native resolution (270 x 584, DESIGN.md section 15) into layers the size of the world
canvas: the safe area plus OVERSCAN on every side. Everything is palette colours, hard edges and
whole pixels; glows and haze are dithered palette pixels, never blended.

The street is a small perspective scene: facades, porches, boardwalks, ground detail and the
windmill are placed in metres and projected with one camera, so every line runs to the same
vanishing point. Coordinates in this file are safe-area pixels unless noted.
"""
import random

from PIL import Image

from scene.common import W, H, Layer
from scene.sky import draw_sky
from scene.mesas import draw_mesas
from scene.ground import draw_ground
from scene.town import draw_town_back, draw_town_front
from scene.horses import draw_street_props
from scene.foreground import draw_foreground
from scene.player import draw_player

LAYER_NAMES = ["sky", "mesas", "town", "fg", "player_back"]


def build(out_dir):
    """Draws every layer, saves them as out_dir/<name>.png and returns the composite.
    Each area lives in its own module under scene/; this function only orders them."""
    rng = random.Random(1873)
    sky = draw_sky(random.Random(11))
    mesas = draw_mesas(random.Random(12))
    town = Layer()
    draw_town_back(town, random.Random(13))
    draw_ground(town, random.Random(14))
    draw_town_front(town, random.Random(15))
    draw_street_props(town, random.Random(16))
    fg = draw_foreground(random.Random(17))
    player = draw_player(random.Random(18))
    layers = (sky, mesas, town, fg, player)
    for name, layer in zip(LAYER_NAMES, layers):
        layer.save("%s/%s.png" % (out_dir, name))
    comp = Image.new("RGBA", (W, H))
    for layer in layers:
        comp.alpha_composite(layer.im)
    return comp
