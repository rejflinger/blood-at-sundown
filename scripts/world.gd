class_name WorldBuilder
extends RefCounted
## Builds the layered street scenery. Milestone 1 draws only the dusk backdrop (sky bands,
## sun, mesas, ground); milestone 2 adds the street, town, parallax, props and ambience.
## World coordinates: the 195 x 422 safe area spans (0, 0) to (195, 422). Scenery extends
## OVERSCAN pixels beyond it on every side so wider or taller screens show more world
## instead of black bars.

const NATIVE := Vector2i(195, 422)
const OVERSCAN := Vector2i(100, 60)
const HORIZON := 190


static func build(root: Node2D, seed: int) -> Node2D:
	var world := Node2D.new()
	world.name = "World"
	root.add_child(world)
	var backdrop := Sprite2D.new()
	backdrop.name = "Backdrop"
	backdrop.centered = false
	backdrop.texture = PixelArt.texture(backdrop_image(seed))
	backdrop.position = Vector2(-OVERSCAN)
	world.add_child(backdrop)
	return world


## Sky bands with dithered seams, a banded sun, a mesa line and a plain ground.
static func backdrop_image(seed: int) -> Image:
	var P := PixelArt
	var size := NATIVE + OVERSCAN * 2
	var ox := OVERSCAN.x
	var oy := OVERSCAN.y
	var img := P.new_image(size.x, size.y, P.c(P.SKY_TOP))
	var bands := [[P.SKY_TOP, 30], [P.SKY_HIGH, 92], [P.SKY_MID, 138], [P.SKY_LOW, 168], [P.HORIZON, HORIZON]]
	var y0 := 0
	for i in bands.size():
		var col: int = bands[i][0]
		var y1: int = bands[i][1] + oy
		P.rect(img, 0, y0, size.x, y1 - y0, P.c(col))
		if i > 0:  # dithered seam into the band above
			var above: int = bands[i - 1][0]
			for k in 4:
				for x in size.x:
					if P.dither_on(x, y0 + k, 1.0 - (k + 1) / 5.0):
						P.px(img, x, y0 + k, P.c(above))
		y0 = y1
	# sun with a flat horizontal band cut through it
	var sun_c := Vector2i(ox + 97, oy + HORIZON - 12)
	P.circle(img, sun_c.x, sun_c.y, 17, P.c(P.SUN))
	for band_y in [sun_c.y + 4, sun_c.y + 9]:
		P.hline(img, sun_c.x - 17, sun_c.x + 17, band_y, P.c(P.HORIZON))
	# mesas
	var rng := RandomNumberGenerator.new()
	rng.seed = seed
	var x := 0
	while x < size.x:
		var w := rng.randi_range(22, 48)
		var h := rng.randi_range(6, 26)
		var slope := rng.randi_range(3, 7)
		var top := oy + HORIZON - h
		var pts := PackedVector2Array([
			Vector2(x, oy + HORIZON + 1), Vector2(x + slope, top), Vector2(x + w - slope, top),
			Vector2(x + w, oy + HORIZON + 1)])
		P.polygon(img, pts, P.c(P.PLUM))
		P.hline(img, x + slope, x + w - slope - 1, top, P.c(P.PLUM_LIGHT))
		x += w + rng.randi_range(-8, 14)
	# ground: dusty street converging on the vanishing point, darker toward the camera
	var gy := oy + HORIZON
	P.rect(img, 0, gy, size.x, size.y - gy, P.c(P.OCHRE))
	for yy in range(gy, size.y):
		var depth := float(yy - gy) / float(size.y - gy)
		var half := int(4 + depth * 150)
		for xx in range(ox + 97 - half, ox + 98 + half):
			if xx >= 0 and xx < size.x:
				P.px(img, xx, yy, P.c(P.DUST if P.dither_on(xx, yy, 1.0 - depth * 0.7) else P.TAN))
		if depth > 0.55:
			for xx in size.x:
				if P.dither_on(xx, yy, (depth - 0.55) * 1.4) and (xx < ox + 97 - half or xx > ox + 97 + half):
					P.px(img, xx, yy, P.c(P.LEATHER))
	P.hline(img, 0, size.x - 1, gy, P.c(P.PLUM_LIGHT))
	return img
