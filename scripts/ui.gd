class_name GameUI
extends Control
## All UI lives here and is laid out in native pixels (195 x 422) inside the UI SubViewport,
## which main.gd scales by the same integer factor as the world. Every string shown to the
## player goes through txt(), which rejects em-dashes and records the string for the tests.

signal action(name: String)
signal touch(kind: String, pos: Vector2)  # "press", "release", "drag" in native pixels

const NATIVE := Vector2i(195, 422)
const COL_LEFT := 12    # 0.06 of the width
const COL_RIGHT := 183  # 0.94 of the width

const FONT_TINY := "res://assets/fonts/tiny.fnt"
const FONT_BODY := "res://assets/fonts/body.fnt"
const FONT_BOLD := "res://assets/fonts/bold.fnt"
const TINY_SIZE := 8
const BODY_SIZE := 10

static var strings_seen := {}
static var _fonts := {}

var safe: Control           # the 195 x 422 play area, centred in the viewport
var screens := {}           # name -> Control
var title_buttons: Array[PixelButton] = []
var sound_on := true


# --- strings and fonts -------------------------------------------------------------------

static func txt(s: String) -> String:
	if s.contains(char(0x2014)) or s.contains(char(0x2013)):
		push_error("UI text contains a dash that is not allowed: " + s)
		s = s.replace(char(0x2014), "-").replace(char(0x2013), "-")
	strings_seen[s] = true
	return s


static func font(name: String) -> FontFile:
	if _fonts.has(name):
		return _fonts[name]
	var path: String = {"tiny": FONT_TINY, "body": FONT_BODY, "bold": FONT_BOLD}[name]
	var f: FontFile = load(path)
	f.fixed_size_scale_mode = TextServer.FIXED_SIZE_SCALE_INTEGER_ONLY
	f.antialiasing = TextServer.FONT_ANTIALIASING_NONE
	f.subpixel_positioning = TextServer.SUBPIXEL_POSITIONING_DISABLED
	f.hinting = TextServer.HINTING_NONE
	_fonts[name] = f
	return f


static func font_size(name: String, scale := 1) -> int:
	return (TINY_SIZE if name == "tiny" else BODY_SIZE) * scale


static func cap_height(name: String, scale := 1) -> int:
	return (5 if name == "tiny" else 7) * scale


static func label(text: String, face := "body", color := PixelArt.CREAM, scale := 1,
		align := HORIZONTAL_ALIGNMENT_LEFT, width := 0, shadow := true) -> Label:
	var l := Label.new()
	l.text = txt(text)
	l.add_theme_font_override("font", font(face))
	l.add_theme_font_size_override("font_size", font_size(face, scale))
	l.add_theme_color_override("font_color", PixelArt.c(color))
	l.add_theme_constant_override("line_spacing", 1 * scale)
	if shadow:
		l.add_theme_color_override("font_shadow_color", PixelArt.c(PixelArt.INK))
		l.add_theme_constant_override("shadow_offset_x", 0)
		l.add_theme_constant_override("shadow_offset_y", scale)
		l.add_theme_constant_override("shadow_outline_size", 0)
	l.horizontal_alignment = align
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	if width > 0:
		l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		l.custom_minimum_size.x = width
		l.size.x = width
	return l


# --- building ----------------------------------------------------------------------------

func _init() -> void:
	name = "GameUI"
	mouse_filter = Control.MOUSE_FILTER_STOP
	safe = Control.new()
	safe.name = "Safe"
	safe.size = NATIVE
	safe.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(safe)


## Called by main.gd whenever the viewport size changes.
func layout(vp_size: Vector2i, safe_origin: Vector2i) -> void:
	position = Vector2.ZERO
	size = vp_size
	safe.position = safe_origin


func _gui_input(event: InputEvent) -> void:
	if not (event is InputEventMouseButton or event is InputEventMouseMotion):
		return
	var p: Vector2 = event.position.floor() - safe.position
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		touch.emit("press" if event.pressed else "release", p)
		accept_event()
	elif event is InputEventMouseMotion and (event.button_mask & MOUSE_BUTTON_MASK_LEFT):
		touch.emit("drag", p)
		accept_event()


func show_screen(which: String) -> void:
	for k in screens:
		screens[k].visible = (k == which)


func _emit(what: String) -> void:
	Sfx.play("click")
	action.emit(what)


func build_title() -> void:
	var root := Control.new()
	root.name = "Title"
	root.size = NATIVE
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	safe.add_child(root)
	screens["title"] = root

	var logo := TextureRect.new()
	logo.name = "Logo"
	logo.texture = load("res://assets/ui/logo.png")
	logo.mouse_filter = Control.MOUSE_FILTER_IGNORE
	logo.position = Vector2((NATIVE.x - logo.texture.get_width()) / 2, 14)
	root.add_child(logo)

	var tag := label("TEN OUTLAWS. ONE THUMB.", "bold", PixelArt.CREAM, 1,
			HORIZONTAL_ALIGNMENT_CENTER, COL_RIGHT - COL_LEFT)
	tag.name = "Tagline"
	tag.position = Vector2(COL_LEFT, 14 + logo.texture.get_height() + 6)
	root.add_child(tag)

	# Button column right of centre, clear of the player figure in the lower left.
	var x := 66
	var w := 112
	var y := 196
	title_buttons.clear()
	for spec in [
		["play", "PLAY", PixelButton.STYLE_RED, 28, 2],
		["practice", "PRACTICE", PixelButton.STYLE_WOOD, 21, 1],
		["daily", "DAILY DUEL", PixelButton.STYLE_WOOD, 21, 1],
		["scores", "HIGH SCORES", PixelButton.STYLE_WOOD, 21, 1],
		["outlaws", "OUTLAWS", PixelButton.STYLE_WOOD, 21, 1],
	]:
		var b := PixelButton.new(spec[0], spec[1], spec[2], spec[4])
		b.position = Vector2(x, y)
		b.size = Vector2(w, spec[3])
		b.pressed.connect(_emit.bind(spec[0]))
		root.add_child(b)
		title_buttons.append(b)
		y += spec[3] + 5
		if spec[0] == "daily":
			var plate := plate_label("DailyStatus", "", x + 4, y - 4, w - 8)
			plate.set_meta("slot_y", y - 4)  # room for two lines; one line sits centred
			root.add_child(plate)
			y += 16

	# Icon row: stats and how to play on the left and middle, sound toggle bottom right.
	var icons := [
		["stats", "STATS", PixelButton.ICON_STATS, 18],
		["howto", "HOW TO PLAY", PixelButton.ICON_HOWTO, 86],
		["sound", "SOUND", PixelButton.ICON_SOUND_ON, 155],
	]
	for spec in icons:
		var b := PixelButton.new(spec[0], "", PixelButton.STYLE_WOOD, 1)
		b.icon_rows = spec[2]
		b.position = Vector2(spec[3], 380)
		b.size = Vector2(24, 24)
		b.pressed.connect(_emit.bind(spec[0]))
		root.add_child(b)
		title_buttons.append(b)
		var cw := int(font("tiny").get_string_size(spec[1], HORIZONTAL_ALIGNMENT_LEFT, -1, TINY_SIZE).x) + 7
		var cap := plate_label("Cap_" + spec[0], spec[1], clampi(spec[3] + 12 - cw / 2, COL_LEFT, COL_RIGHT - cw), 405, cw)
		root.add_child(cap)


## Small text on a dark inset plate: the 5 px face needs a dark ground to stay legible.
func plate_label(id: String, text: String, x: int, y: int, w: int) -> PixelPanel:
	var plate := PixelPanel.new(PixelPanel.STYLE_INSET)
	plate.name = id
	plate.position = Vector2(x, y)
	plate.size = Vector2(w, 11)
	var l := label(text, "tiny", PixelArt.CREAM, 1, HORIZONTAL_ALIGNMENT_CENTER, w - 4, false)
	l.name = "Text"
	l.position = Vector2(2, 2)
	plate.add_child(l)
	return plate


## Sets a plate's text and grows it to fit the wrapped lines.
func set_plate_text(plate: PixelPanel, text: String) -> void:
	var l: Label = plate.get_node("Text")
	l.text = txt(text)
	var lines := maxi(1, l.get_line_count())
	plate.size.y = 3 + lines * 8
	plate.queue_redraw()


func set_daily_status(text: String) -> void:
	var plate: PixelPanel = screens["title"].get_node("DailyStatus")
	set_plate_text(plate, text)
	plate.position.y = plate.get_meta("slot_y") + (4 if plate.size.y <= 11 else 0)


func set_sound(on: bool) -> void:
	sound_on = on
	for b in title_buttons:
		if b.id == "sound":
			b.icon_rows = PixelButton.ICON_SOUND_ON if on else PixelButton.ICON_SOUND_OFF
			b.queue_redraw()


## A simple wood card with a title, body lines and one button. Used for placeholder
## screens until their real content arrives, and for HOW TO PLAY.
func build_card(id: String, title: String, lines: Array, button_text: String, button_action: String) -> Control:
	var root := Control.new()
	root.name = "Card_" + id
	root.size = NATIVE
	root.mouse_filter = Control.MOUSE_FILTER_STOP
	root.visible = false
	safe.add_child(root)
	screens[id] = root

	var panel := PixelPanel.new(PixelPanel.STYLE_DARK)
	panel.position = Vector2(COL_LEFT, 40)
	panel.size = Vector2(COL_RIGHT - COL_LEFT, 330)
	root.add_child(panel)

	var t := label(title, "bold", PixelArt.CREAM, 2, HORIZONTAL_ALIGNMENT_CENTER, COL_RIGHT - COL_LEFT - 16)
	t.position = Vector2(COL_LEFT + 8, 52)
	root.add_child(t)

	var y := 84
	for entry in lines:
		if entry is Array:  # [heading, body]
			var box := PixelPanel.new(PixelPanel.STYLE_INSET)
			box.position = Vector2(COL_LEFT + 8, y)
			box.size = Vector2(COL_RIGHT - COL_LEFT - 16, 62)
			root.add_child(box)
			var h := label(entry[0], "bold", PixelArt.GOLD, 1, HORIZONTAL_ALIGNMENT_LEFT, 110)
			h.position = Vector2(COL_LEFT + 16, y + 7)
			root.add_child(h)
			var b := label(entry[1], "tiny", PixelArt.CREAM, 1, HORIZONTAL_ALIGNMENT_LEFT, COL_RIGHT - COL_LEFT - 32)
			b.position = Vector2(COL_LEFT + 16, y + 22)
			root.add_child(b)
			y += 68
		else:
			var l := label(entry, "body", PixelArt.CREAM, 1, HORIZONTAL_ALIGNMENT_CENTER, COL_RIGHT - COL_LEFT - 24)
			l.position = Vector2(COL_LEFT + 12, y)
			root.add_child(l)
			y += 12 * maxi(1, ceili(entry.length() / 26.0)) + 4

	var btn := PixelButton.new(button_action, button_text, PixelButton.STYLE_RED, 1)
	btn.position = Vector2(56, 336)
	btn.size = Vector2(83, 21)
	btn.pressed.connect(_emit.bind(button_action))
	root.add_child(btn)
	return root


# --- pixel widgets -----------------------------------------------------------------------

## A generated panel texture drawn at the control's exact size (no stretching).
class PixelPanel extends Control:
	const STYLE_WOOD := "wood"
	const STYLE_RED := "red"
	const STYLE_DARK := "dark"
	const STYLE_INSET := "inset"

	var style := STYLE_WOOD
	var pressed_look := false
	var _tex: ImageTexture
	var _tex_key := ""

	func _init(p_style := STYLE_WOOD) -> void:
		style = p_style
		mouse_filter = Control.MOUSE_FILTER_IGNORE

	func _draw() -> void:
		var key := "%s %d %d %s" % [style, size.x, size.y, pressed_look]
		if key != _tex_key:
			_tex_key = key
			_tex = PixelArt.texture(GameUI.panel_image(int(size.x), int(size.y), style, pressed_look))
		draw_texture(_tex, Vector2.ZERO)


class PixelButton extends BaseButton:
	const STYLE_WOOD := "wood"
	const STYLE_RED := "red"

	const ICON_STATS := [
		"........##.",
		"........##.",
		"....##..##.",
		"....##..##.",
		".##.##..##.",
		".##.##..##.",
		".##.##..##.",
		"###########",
	]
	const ICON_HOWTO := [
		"..####..",
		".##..##.",
		".....##.",
		"....##..",
		"...##...",
		"...##...",
		"........",
		"...##...",
	]
	const ICON_SOUND_ON := [
		"....#.......",
		"...##...#...",
		".####....#..",
		"#####..#..#.",
		"#####...#.#.",
		"#####..#..#.",
		".####....#..",
		"...##...#...",
		"....#.......",
	]
	const ICON_SOUND_OFF := [
		"....#.......",
		"...##.......",
		".####..#...#",
		"#####...#.#.",
		"#####....#..",
		"#####...#.#.",
		".####..#...#",
		"...##.......",
		"....#.......",
	]

	var id := ""
	var text := ""
	var style := STYLE_WOOD
	var text_scale := 1
	var icon_rows: Array = []
	var _panel := {}

	func _init(p_id := "", p_text := "", p_style := STYLE_WOOD, p_scale := 1) -> void:
		id = p_id
		name = "Btn_" + p_id
		text = GameUI.txt(p_text) if p_text != "" else ""
		style = p_style
		text_scale = p_scale
		focus_mode = Control.FOCUS_NONE
		mouse_filter = Control.MOUSE_FILTER_STOP
		button_down.connect(queue_redraw)
		button_up.connect(queue_redraw)

	func _panel_tex(down: bool) -> ImageTexture:
		var key := "%d %d %s" % [size.x, size.y, down]
		if not _panel.has(key):
			_panel[key] = PixelArt.texture(GameUI.panel_image(int(size.x), int(size.y), style, down))
		return _panel[key]

	func _draw() -> void:
		var down := is_pressed() or button_pressed
		draw_texture(_panel_tex(down), Vector2.ZERO)
		var shift := 1 if down else 0
		if not icon_rows.is_empty():
			var iw: int = icon_rows[0].length()
			var ih: int = icon_rows.size()
			var ox := (int(size.x) - iw) / 2
			var oy := (int(size.y) - ih) / 2 + shift
			for ry in ih:
				var r: String = icon_rows[ry]
				for rx in iw:
					if r[rx] == "#":
						draw_rect(Rect2(ox + rx, oy + ry + 1, 1, 1), PixelArt.c(PixelArt.INK))
						draw_rect(Rect2(ox + rx, oy + ry, 1, 1), PixelArt.c(PixelArt.CREAM))
		if text != "":
			var f := GameUI.font("bold")
			var fs := GameUI.font_size("bold", text_scale)
			var tw := int(f.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x)
			var cap := GameUI.cap_height("bold", text_scale)
			var tx := (int(size.x) - tw) / 2
			var base := (int(size.y) - cap) / 2 + cap + shift
			draw_string(f, Vector2(tx, base + text_scale), text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, PixelArt.c(PixelArt.INK))
			draw_string(f, Vector2(tx, base), text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, PixelArt.c(PixelArt.CREAM))


## Wood, red, dark and inset panels, drawn pixel by pixel at an exact size. The grain is
## seeded from the size so every panel of the same size looks the same.
static func panel_image(w: int, h: int, style: String, down := false) -> Image:
	var P := PixelArt
	var img := P.new_image(w, h)
	var fill := P.BROWN
	var hi := P.LEATHER
	var lo := P.BROWN_DARK
	var grain := P.BROWN_DARK
	var orn := P.TAN
	match style:
		"red":
			fill = P.BLOOD; hi = P.RED; lo = P.WINE; grain = P.WINE; orn = P.GOLD
		"dark":
			fill = P.CHARCOAL; hi = P.BROWN; lo = P.INK; grain = P.INK; orn = P.OCHRE
		"inset":
			fill = P.INK; hi = P.CHARCOAL; lo = P.BROWN; grain = P.CHARCOAL; orn = -1
	if down:
		var t := hi
		hi = lo
		lo = t
	var ink := P.c(P.INK)
	# outline with clipped corners
	P.rect(img, 1, 0, w - 2, h, ink)
	P.rect(img, 0, 1, w, h - 2, ink)
	# bevel ring
	P.rect(img, 1, 1, w - 2, h - 2, P.c(lo))
	P.rect(img, 1, 1, w - 3, h - 3, P.c(hi))
	P.rect(img, 2, 2, w - 4, h - 4, P.c(lo))
	P.rect(img, 3, 3, w - 6, h - 6, P.c(fill))
	# grain: sparse broken horizontal streaks
	var rng := RandomNumberGenerator.new()
	rng.seed = hash("%s%d%d" % [style, w, h])
	var gy := 5 + (1 if down else 0)
	while gy < h - 4:
		var gx := 4 + rng.randi_range(0, 6)
		while gx < w - 5:
			var run := rng.randi_range(3, 10)
			P.hline(img, gx, mini(gx + run, w - 5), gy, P.c(grain))
			gx += run + rng.randi_range(4, 14)
		gy += rng.randi_range(3, 5) if style == "wood" or style == "red" else rng.randi_range(7, 11)
	# corner ornaments: tiny diamonds
	if orn >= 0 and w >= 16 and h >= 14:
		for cxy in [Vector2i(5, 5), Vector2i(w - 6, 5), Vector2i(5, h - 6), Vector2i(w - 6, h - 6)]:
			P.px(img, cxy.x, cxy.y, P.c(orn))
			if h >= 20:
				P.px(img, cxy.x - 1, cxy.y, P.c(lo))
				P.px(img, cxy.x + 1, cxy.y, P.c(lo))
	# bullet holes on the red button
	if style == "red" and w >= 60 and h >= 20:
		for hx in [w / 5, w - w / 6]:
			var hy := h / 2 + (2 if hx > w / 2 else -2)
			P.px(img, hx, hy, ink)
			P.px(img, hx + 1, hy, ink)
			P.px(img, hx, hy + 1, ink)
			P.px(img, hx + 1, hy + 1, P.c(P.WINE))
			P.px(img, hx - 1, hy - 1, P.c(P.WINE))
	return img
