class_name PixelArt
extends RefCounted
## Palette, raster tools and (later) sprite generation. Everything here works on Image at
## native resolution with hard edges: no blending, no antialiasing, palette colours only.

# Palette indices. Order matches tools/palette.py, which writes assets/palette.png and
# assets/palette_names.txt (the autotest checks the two agree).
enum {
	INK, CHARCOAL, SHADOW, PLUM, PLUM_LIGHT, MAUVE, WINE_DARK, WINE, MAROON, BLOOD, RED,
	RED_LIGHT, RUST, ORANGE, AMBER, GOLD, LAMP, LAMP_HOT, CREAM, CREAM_SHADE, PALE,
	BROWN_BLACK, BROWN_DARK, BROWN, BROWN_MID, LEATHER, OCHRE, TAN, SAND, SKIN_DEEP,
	SKIN_DARK, SKIN, SKIN_LIGHT, TEAL_DARK, TEAL, TEAL_LIGHT, TEAL_PALE, NAVY, SLATE, BLUE,
	BLUE_LIGHT, GREY_DARK, GREY, SILVER, STEEL_HI, OLIVE_DARK, OLIVE, SAGE, SKY_TOP,
	SKY_UPPER, SKY_HIGH, SKY_MID, SKY_WARM, SKY_LOW, HORIZON, HORIZON_HOT, SUN, SUN_CORE, RIM,
	RIM_HOT, DUST, DUST_LIGHT, HAZE, MESA_LIT,
}
const PALETTE_SIZE := 64
const FIRST_SWAP := SKY_TOP
const PALETTE_PATH := "res://assets/palette.png"

const BAYER4 := [
	[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5],
]

static var _gold: PackedColorArray
static var _red: PackedColorArray
static var _current: PackedColorArray
static var _sun_t := -1.0


static func _load() -> void:
	if not _gold.is_empty():
		return
	var tex: Texture2D = load(PALETTE_PATH)
	var img := tex.get_image()
	img.decompress()
	for x in PALETTE_SIZE:
		_gold.append(img.get_pixel(x, 0))
		_red.append(img.get_pixel(x, 1))
	set_sun(0.0)


## Palette ramp position for a duel: gold at duel 1, deep red from duel 8 on.
static func sun_t_for_duel(duel: int) -> float:
	return clampf(float(duel - 1) / 7.0, 0.0, 1.0)


## Swap the sky, rim and dust entries to sun_t. The other 24 entries never change, so every
## frame uses exactly PALETTE_SIZE colours.
static func set_sun(t: float) -> void:
	_load()
	_sun_t = t
	_current = palette_at(t)


static func palette_at(t: float) -> PackedColorArray:
	_load()
	var out := _gold.duplicate()
	for i in range(FIRST_SWAP, PALETTE_SIZE):
		var a: Color = _gold[i]
		var b: Color = _red[i]
		out[i] = Color8(
			roundi(lerpf(a.r8, b.r8, t)), roundi(lerpf(a.g8, b.g8, t)), roundi(lerpf(a.b8, b.b8, t)))
	return out


static func sun_t() -> float:
	_load()
	return _sun_t


## Palette colour by index at the current sun position.
static func c(i: int) -> Color:
	_load()
	return _current[i]


static func palette() -> PackedColorArray:
	_load()
	return _current


# --- images ------------------------------------------------------------------------------

static func new_image(w: int, h: int, fill := Color(0, 0, 0, 0)) -> Image:
	var img := Image.create(w, h, false, Image.FORMAT_RGBA8)
	img.fill(fill)
	return img


static func px(img: Image, x: int, y: int, col: Color) -> void:
	if x >= 0 and y >= 0 and x < img.get_width() and y < img.get_height():
		img.set_pixel(x, y, col)


static func rect(img: Image, x: int, y: int, w: int, h: int, col: Color) -> void:
	var r := Rect2i(x, y, w, h).intersection(Rect2i(0, 0, img.get_width(), img.get_height()))
	if r.size.x > 0 and r.size.y > 0:
		img.fill_rect(r, col)


static func rect_outline(img: Image, x: int, y: int, w: int, h: int, col: Color) -> void:
	hline(img, x, x + w - 1, y, col)
	hline(img, x, x + w - 1, y + h - 1, col)
	vline(img, x, y, y + h - 1, col)
	vline(img, x + w - 1, y, y + h - 1, col)


static func hline(img: Image, x0: int, x1: int, y: int, col: Color) -> void:
	for x in range(mini(x0, x1), maxi(x0, x1) + 1):
		px(img, x, y, col)


static func vline(img: Image, x: int, y0: int, y1: int, col: Color) -> void:
	for y in range(mini(y0, y1), maxi(y0, y1) + 1):
		px(img, x, y, col)


## Bresenham line, both endpoints included.
static func line(img: Image, x0: int, y0: int, x1: int, y1: int, col: Color) -> void:
	var dx := absi(x1 - x0)
	var dy := -absi(y1 - y0)
	var sx := 1 if x0 < x1 else -1
	var sy := 1 if y0 < y1 else -1
	var err := dx + dy
	while true:
		px(img, x0, y0, col)
		if x0 == x1 and y0 == y1:
			break
		var e2 := 2 * err
		if e2 >= dy:
			err += dy
			x0 += sx
		if e2 <= dx:
			err += dx
			y0 += sy


## Filled ellipse centred on (cx, cy) with integer radii; symmetric, hard edged.
static func ellipse(img: Image, cx: int, cy: int, rx: int, ry: int, col: Color) -> void:
	if rx <= 0 or ry <= 0:
		px(img, cx, cy, col)
		return
	var rx2 := (rx + 0.5) * (rx + 0.5)
	var ry2 := (ry + 0.5) * (ry + 0.5)
	for y in range(-ry, ry + 1):
		var half := int(floor(sqrt(maxf(0.0, rx2 * (1.0 - y * y / ry2)))))
		hline(img, cx - half, cx + half, cy + y, col)


static func circle(img: Image, cx: int, cy: int, r: int, col: Color) -> void:
	ellipse(img, cx, cy, r, r, col)


## Scanline polygon fill (even-odd), sampled at pixel centres.
static func polygon(img: Image, pts: PackedVector2Array, col: Color) -> void:
	if pts.size() < 3:
		return
	var y_min := INF
	var y_max := -INF
	for p in pts:
		y_min = minf(y_min, p.y)
		y_max = maxf(y_max, p.y)
	for y in range(int(floor(y_min)), int(ceil(y_max)) + 1):
		var sy := y + 0.5
		var xs: Array[float] = []
		for i in pts.size():
			var a := pts[i]
			var b := pts[(i + 1) % pts.size()]
			if (a.y <= sy and b.y > sy) or (b.y <= sy and a.y > sy):
				xs.append(a.x + (sy - a.y) / (b.y - a.y) * (b.x - a.x))
		xs.sort()
		for k in range(0, xs.size() - 1, 2):
			var x0 := int(ceil(xs[k] - 0.5))
			var x1 := int(floor(xs[k + 1] - 0.5))
			if x1 >= x0:
				hline(img, x0, x1, y, col)


## Ordered 4x4 dither between two colours; level 0 is all a, 1 is all b.
static func dither_rect(img: Image, x: int, y: int, w: int, h: int, a: Color, b: Color, level: float) -> void:
	for yy in range(y, y + h):
		for xx in range(x, x + w):
			px(img, xx, yy, b if dither_on(xx, yy, level) else a)


static func dither_on(x: int, y: int, level: float) -> bool:
	return (BAYER4[posmod(y, 4)][posmod(x, 4)] + 0.5) / 16.0 < level


## Adds a one-pixel outline around every opaque pixel. diagonal=true includes corners.
static func outline(img: Image, col: Color, diagonal := false) -> void:
	var w := img.get_width()
	var h := img.get_height()
	var src := img.duplicate() as Image
	var dirs := [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]
	if diagonal:
		dirs += [Vector2i(1, 1), Vector2i(-1, 1), Vector2i(1, -1), Vector2i(-1, -1)]
	for y in h:
		for x in w:
			if src.get_pixel(x, y).a > 0.5:
				continue
			for d in dirs:
				var nx: int = x + d.x
				var ny: int = y + d.y
				if nx >= 0 and ny >= 0 and nx < w and ny < h and src.get_pixel(nx, ny).a > 0.5:
					img.set_pixel(x, y, col)
					break


## Copies opaque pixels of src onto dst (alpha test, never blending).
static func blit(dst: Image, src: Image, x: int, y: int, flip_h := false) -> void:
	var w := src.get_width()
	for sy in src.get_height():
		for sx in w:
			var col := src.get_pixel(w - 1 - sx if flip_h else sx, sy)
			if col.a > 0.5:
				px(dst, x + sx, y + sy, Color(col, 1.0))


static func replace_color(img: Image, from: Color, to: Color) -> void:
	for y in img.get_height():
		for x in img.get_width():
			if img.get_pixel(x, y).is_equal_approx(from):
				img.set_pixel(x, y, to)


## Maps each opaque pixel's palette index through `mapping` (index -> index).
static func palette_swap(img: Image, mapping: Dictionary) -> void:
	var pal := palette()
	for y in img.get_height():
		for x in img.get_width():
			var col := img.get_pixel(x, y)
			if col.a < 0.5:
				continue
			var i := nearest_index(col)
			if mapping.has(i):
				img.set_pixel(x, y, pal[mapping[i]])


static func nearest_index(col: Color, pal: PackedColorArray = PackedColorArray()) -> int:
	if pal.is_empty():
		pal = palette()
	var best := 0
	var best_d := INF
	for i in pal.size():
		var p := pal[i]
		var d := (p.r - col.r) * (p.r - col.r) + (p.g - col.g) * (p.g - col.g) + (p.b - col.b) * (p.b - col.b)
		if d < best_d:
			best_d = d
			best = i
	return best


## Snaps every opaque pixel to the nearest palette colour and every alpha to 0 or 1.
static func quantize(img: Image) -> void:
	var pal := palette()
	for y in img.get_height():
		for x in img.get_width():
			var col := img.get_pixel(x, y)
			img.set_pixel(x, y, Color(pal[nearest_index(col, pal)], 1.0) if col.a >= 0.5 else Color(0, 0, 0, 0))


## Distinct opaque colours in an image.
static func count_colors(img: Image) -> int:
	var seen := {}
	for y in img.get_height():
		for x in img.get_width():
			var col := img.get_pixel(x, y)
			if col.a > 0.5:
				seen[col.to_rgba32()] = true
	return seen.size()


## True when every opaque pixel is a palette colour (at any sun_t) and alpha is 0 or 1.
static func is_palette_clean(img: Image) -> bool:
	_load()
	var ok := {}
	for col in _gold:
		ok[col.to_rgba32()] = true
	for col in _red:
		ok[col.to_rgba32()] = true
	for y in img.get_height():
		for x in img.get_width():
			var col := img.get_pixel(x, y)
			if col.a8 == 0:
				continue
			if col.a8 != 255 or not ok.has(col.to_rgba32()):
				return false
	return true


static func texture(img: Image) -> ImageTexture:
	return ImageTexture.create_from_image(img)


static func mask_from_strings(rows: PackedStringArray) -> Array:
	var out := []
	for r in rows:
		var line_bits := []
		for ch in r:
			line_bits.append(ch == "#")
		out.append(line_bits)
	return out


## Draws a '#' bitmap (list of strings) at x, y in one colour.
static func stamp(img: Image, rows: PackedStringArray, x: int, y: int, col: Color) -> void:
	for ry in rows.size():
		var r: String = rows[ry]
		for rx in r.length():
			if r[rx] == "#":
				px(img, x + rx, y + ry, col)
