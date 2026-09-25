class_name GameUI
extends Control
## All UI lives here and is laid out in native pixels (270 x 584) inside the UI SubViewport,
## which main.gd scales by the same integer factor as the world. Every string shown to the
## player goes through txt(), which rejects em-dashes and records the string for the tests.

signal action(name: String)
signal touch(kind: String, pos: Vector2)  # "press", "release", "drag" in native pixels

const NATIVE := Vector2i(270, 584)
const COL_LEFT := 16    # 0.06 of the width
const COL_RIGHT := 254  # 0.94 of the width

# Faces from tools/gen_fonts.py: [line height = font size at 1x, cap height]. The *_ol faces
# carry a baked ink outline and their own cream colour, for text laid straight over the scene.
const FACES := {
	"tiny": [8, 5], "body": [10, 7], "bold": [10, 7], "tall": [12, 9], "huge": [16, 13],
	"tiny_ol": [8, 5], "body_ol": [10, 7], "bold_ol": [10, 7],
}
const TINY_SIZE := 8

static var strings_seen := {}
static var _fonts := {}

var safe: Control           # the 270 x 584 play area, centred in the viewport
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
	var f: FontFile = load("res://assets/fonts/%s.fnt" % name)
	f.fixed_size_scale_mode = TextServer.FIXED_SIZE_SCALE_INTEGER_ONLY
	f.antialiasing = TextServer.FONT_ANTIALIASING_NONE
	f.subpixel_positioning = TextServer.SUBPIXEL_POSITIONING_DISABLED
	f.hinting = TextServer.HINTING_NONE
	_fonts[name] = f
	return f


static func font_size(name: String, scale := 1) -> int:
	return FACES[name][0] * scale


static func cap_height(name: String, scale := 1) -> int:
	return FACES[name][1] * scale


static func outlined(name: String) -> bool:
	return name.ends_with("_ol")


static func label(text: String, face := "body", color := PixelArt.CREAM, scale := 1,
		align := HORIZONTAL_ALIGNMENT_LEFT, width := 0, shadow := true) -> Label:
	var l := Label.new()
	l.text = txt(text)
	l.add_theme_font_override("font", font(face))
	l.add_theme_font_size_override("font_size", font_size(face, scale))
	# outlined faces carry their own colours, so they are drawn untinted
	l.add_theme_color_override("font_color", Color.WHITE if outlined(face) else PixelArt.c(color))
	l.add_theme_constant_override("line_spacing", 1 * scale)
	if shadow and not outlined(face):
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


## Title laid out after reference/bas_title.png: logo over the sky, the button column right
## of the player figure, the icon row along the bottom with captions over the street.
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
	logo.position = Vector2((NATIVE.x - logo.texture.get_width()) / 2, 8)
	root.add_child(logo)

	var tag := label("TEN OUTLAWS. ONE THUMB.", "bold_ol", PixelArt.CREAM, 1,
			HORIZONTAL_ALIGNMENT_CENTER, COL_RIGHT - COL_LEFT)
	tag.name = "Tagline"
	tag.position = Vector2(COL_LEFT, 8 + logo.texture.get_height() + 3)
	root.add_child(tag)

	var x := 93
	var w := 125
	var y := 318
	title_buttons.clear()
	for spec in [
		["play", "PLAY", PixelButton.STYLE_RED, 38, "huge"],
		["practice", "PRACTICE", PixelButton.STYLE_WOOD, 30, "tall"],
		["daily", "DAILY DUEL", PixelButton.STYLE_WOOD, 30, "tall"],
		["scores", "HIGH SCORES", PixelButton.STYLE_WOOD, 30, "tall"],
		["outlaws", "OUTLAWS", PixelButton.STYLE_WOOD, 30, "tall"],
	]:
		var b := PixelButton.new(spec[0], spec[1], spec[2], 1, spec[4])
		b.position = Vector2(x, y)
		b.size = Vector2(w, spec[3])
		b.pressed.connect(_emit.bind(spec[0]))
		root.add_child(b)
		title_buttons.append(b)
		y += spec[3] + 7
		if spec[0] == "daily":
			# centred under the button, as wide as the column allows on its right side
			var sw := 2 * (COL_RIGHT - (x + w / 2))
			var status := label("", "body_ol", PixelArt.CREAM, 1, HORIZONTAL_ALIGNMENT_CENTER, sw)
			status.name = "DailyStatus"
			status.position = Vector2(x + w / 2 - sw / 2, y - 5)
			status.set_meta("slot_y", y - 5)  # room for two lines; one line sits centred
			root.add_child(status)
			y += 18

	# Icon row as in the reference: stats bottom left, sound and how to play bottom right.
	for spec in [
		["stats", "STATS", PixelButton.ICON_STATS, COL_LEFT],
		["sound", "SOUND", PixelButton.ICON_SOUND_ON, 132],
		["howto", "HOW TO PLAY", PixelButton.ICON_HOWTO, COL_RIGHT - 32],
	]:
		var b := PixelButton.new(spec[0], "", PixelButton.STYLE_WOOD, 1)
		b.icon_rows = spec[2]
		b.position = Vector2(spec[3], 530)
		b.size = Vector2(32, 32)
		b.pressed.connect(_emit.bind(spec[0]))
		root.add_child(b)
		title_buttons.append(b)
		var cw := int(font("body_ol").get_string_size(spec[1], HORIZONTAL_ALIGNMENT_LEFT, -1, font_size("body_ol")).x) + 2
		var cap := label(spec[1], "body_ol", PixelArt.CREAM, 1, HORIZONTAL_ALIGNMENT_CENTER, cw)
		cap.name = "Cap_" + spec[0]
		cap.position = Vector2(clampi(spec[3] + 16 - cw / 2, COL_LEFT, COL_RIGHT - cw), 565)
		root.add_child(cap)


func set_daily_status(text: String) -> void:
	var l: Label = screens["title"].get_node("DailyStatus")
	l.text = txt(text)
	var lines := maxi(1, l.get_line_count())
	l.position.y = l.get_meta("slot_y") + (5 if lines == 1 else 0)


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
	panel.position = Vector2(COL_LEFT, 56)
	panel.size = Vector2(COL_RIGHT - COL_LEFT, 460)
	root.add_child(panel)

	var t := label(title, "huge", PixelArt.CREAM, 1, HORIZONTAL_ALIGNMENT_CENTER, COL_RIGHT - COL_LEFT - 20)
	t.position = Vector2(COL_LEFT + 10, 74)
	root.add_child(t)

	var y := 112
	for entry in lines:
		if entry is Array:  # [heading, body]
			var box := PixelPanel.new(PixelPanel.STYLE_INSET)
			box.position = Vector2(COL_LEFT + 10, y)
			box.size = Vector2(COL_RIGHT - COL_LEFT - 20, 86)
			root.add_child(box)
			var h := label(entry[0], "tall", PixelArt.GOLD, 1, HORIZONTAL_ALIGNMENT_LEFT, 160)
			h.position = Vector2(COL_LEFT + 22, y + 11)
			root.add_child(h)
			var b := label(entry[1], "body", PixelArt.CREAM, 1, HORIZONTAL_ALIGNMENT_LEFT, COL_RIGHT - COL_LEFT - 44)
			b.position = Vector2(COL_LEFT + 22, y + 32)
			root.add_child(b)
			y += 94
		else:
			var l := label(entry, "body", PixelArt.CREAM, 1, HORIZONTAL_ALIGNMENT_CENTER, COL_RIGHT - COL_LEFT - 32)
			l.position = Vector2(COL_LEFT + 16, y)
			root.add_child(l)
			y += 12 * maxi(1, ceili(entry.length() / 34.0)) + 6

	var btn := PixelButton.new(button_action, button_text, PixelButton.STYLE_RED, 1, "tall")
	btn.position = Vector2((NATIVE.x - 116) / 2, 464)
	btn.size = Vector2(116, 32)
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

	# '#' cream with an ink drop shadow, 'r' red.
	const ICON_STATS := [
		"...............####",
		"...............####",
		"..........rr...####",
		".........rrrr..####",
		"..........rr...####",
		"..........####.####",
		"..........####.####",
		".....####.####.####",
		".....####.####.####",
		".....####.####.####",
		".....####.####.####",
		".....####.####.####",
		".....####.####.####",
		"...................",
		"###################",
		"###################",
	]
	const ICON_HOWTO := [
		"...######...",
		"..########..",
		".###....###.",
		".##......##.",
		".........##.",
		"........###.",
		".......###..",
		"......###...",
		".....###....",
		".....##.....",
		".....##.....",
		"............",
		".....##.....",
		".....##.....",
	]
	const ICON_SOUND_ON := [
		"........#.........",
		".......##.....#...",
		"......###..#...#..",
		".....####...#...#.",
		"#########...#...#.",
		"#########.#..#..#.",
		"#########.#..#..#.",
		"#########.#..#..#.",
		"#########...#...#.",
		".....####...#...#.",
		"......###..#...#..",
		".......##.....#...",
		"........#.........",
	]
	const ICON_SOUND_OFF := [
		"........#.........",
		".......##.........",
		"......###.........",
		".....####.##...##.",
		"#########..##.##..",
		"#########...###...",
		"#########...###...",
		"#########..##.##..",
		"#########.##...##.",
		".....####.........",
		"......###.........",
		".......##.........",
		"........#.........",
	]

	var id := ""
	var text := ""
	var style := STYLE_WOOD
	var text_scale := 1
	var face := "bold"
	var icon_rows: Array = []
	var _panel := {}

	func _init(p_id := "", p_text := "", p_style := STYLE_WOOD, p_scale := 1, p_face := "bold") -> void:
		id = p_id
		name = "Btn_" + p_id
		text = GameUI.txt(p_text) if p_text != "" else ""
		style = p_style
		text_scale = p_scale
		face = p_face
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
					if r[rx] != ".":
						draw_rect(Rect2(ox + rx, oy + ry + 1, 1, 1), PixelArt.c(PixelArt.INK))
			for ry in ih:
				var r: String = icon_rows[ry]
				for rx in iw:
					if r[rx] == "#":
						draw_rect(Rect2(ox + rx, oy + ry, 1, 1), PixelArt.c(PixelArt.CREAM))
					elif r[rx] == "r":
						draw_rect(Rect2(ox + rx, oy + ry, 1, 1), PixelArt.c(PixelArt.RED))
		if text != "":
			var f := GameUI.font(face)
			var fs := GameUI.font_size(face, text_scale)
			var tw := int(f.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x)
			var cap := GameUI.cap_height(face, text_scale)
			var tx := (int(size.x) - tw) / 2
			var base := (int(size.y) - cap + 1) / 2 + cap + shift
			draw_string(f, Vector2(tx, base + text_scale), text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, PixelArt.c(PixelArt.INK))
			draw_string(f, Vector2(tx, base), text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, PixelArt.c(PixelArt.CREAM))


## Wood, red, dark and inset panels after the reference buttons: ink outline with clipped
## corners, a two-pixel bevelled frame, an ink groove, a dark planked fill with sparse grain,
## diamond nails in the corners and small arrow marks at the ends. Drawn pixel by pixel at
## an exact size; grain is seeded from the size so equal panels look equal.
static func panel_image(w: int, h: int, style: String, down := false) -> Image:
	var P := PixelArt
	var img := P.new_image(w, h)
	var fill := P.BROWN_DARK
	var lit := P.OCHRE       # outer frame, top and left
	var frame := P.LEATHER   # inner frame
	var shade := P.BROWN     # outer frame, bottom and right
	var grain := P.BROWN
	var grain2 := P.LEATHER
	var orn := P.TAN
	match style:
		"red":
			fill = P.BLOOD; lit = P.ORANGE; frame = P.RED; shade = P.WINE
			grain = P.WINE; grain2 = P.RED; orn = P.GOLD
		"dark":
			fill = P.CHARCOAL; lit = P.LEATHER; frame = P.BROWN; shade = P.BROWN_DARK
			grain = P.INK; grain2 = P.PLUM; orn = P.OCHRE
		"inset":
			fill = P.INK; lit = P.BROWN; frame = P.CHARCOAL; shade = P.BROWN_DARK
			grain = P.CHARCOAL; grain2 = P.CHARCOAL; orn = -1
	if down:
		var t := lit
		lit = shade
		shade = t
	var ink := P.c(P.INK)
	P.rect(img, 1, 0, w - 2, h, ink)
	P.rect(img, 0, 1, w, h - 2, ink)
	P.rect(img, 1, 1, w - 2, h - 2, P.c(shade))
	P.rect(img, 1, 1, w - 3, h - 3, P.c(lit))
	P.rect(img, 2, 2, w - 4, h - 4, P.c(frame))
	P.rect(img, 3, 3, w - 6, h - 6, ink)
	P.rect(img, 4, 4, w - 8, h - 8, P.c(fill))
	var rng := RandomNumberGenerator.new()
	rng.seed = hash("%s%d%d" % [style, w, h])
	var gy := 5 + (1 if down else 0)
	var sparse := style == "dark" or style == "inset"
	while gy < h - 5:
		var gx := 5 + rng.randi_range(0, 8)
		while gx < w - 6:
			var run := rng.randi_range(3, 12)
			var c := grain2 if rng.randf() < 0.25 else grain
			P.hline(img, gx, mini(gx + run, w - 6), gy, P.c(c))
			gx += run + rng.randi_range(5, 16)
		gy += rng.randi_range(7, 11) if sparse else rng.randi_range(3, 5)
	if orn >= 0 and w >= 16 and h >= 14:
		for cxy in [Vector2i(3, 3), Vector2i(w - 4, 3), Vector2i(3, h - 4), Vector2i(w - 4, h - 4)]:
			for d in [Vector2i(0, -1), Vector2i(-1, 0), Vector2i(1, 0), Vector2i(0, 1)]:
				P.px(img, cxy.x + d.x, cxy.y + d.y, P.c(orn))
			P.px(img, cxy.x, cxy.y, ink)
		if w >= 40 and h >= 18:  # arrow marks at the ends
			var my := h / 2 + (1 if down else 0)
			for side in [-1, 1]:
				var x0 := 6 if side < 0 else w - 7
				P.px(img, x0, my, P.c(orn))
				P.px(img, x0 - side, my, P.c(orn))
				P.px(img, x0 - side * 2, my, P.c(frame))
				P.px(img, x0 - side, my - 1, P.c(frame))
				P.px(img, x0 - side, my + 1, P.c(frame))
	if style == "red" and w >= 60 and h >= 20:
		for hx in [w / 6, w - w / 7]:
			var hy := h / 2 + (2 if hx > w / 2 else -2)
			for d in [Vector2i(-1, -1), Vector2i(2, 2), Vector2i(-2, 1), Vector2i(3, -1), Vector2i(1, -2)]:
				P.px(img, hx + d.x, hy + d.y, P.c(P.WINE))
			P.px(img, hx - 1, hy, P.c(P.RED))
			P.px(img, hx, hy - 1, P.c(P.RED))
			P.rect(img, hx, hy, 2, 2, ink)
	return img
