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
const LOGO_Y := 16      # BLOOD's cap line lands where the reference has it

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
	logo.position = Vector2((NATIVE.x - logo.texture.get_width()) / 2, LOGO_Y)
	root.add_child(logo)

	var tag := label("TEN OUTLAWS. ONE THUMB.", "bold_ol", PixelArt.CREAM, 1,
			HORIZONTAL_ALIGNMENT_CENTER, COL_RIGHT - COL_LEFT)
	tag.name = "Tagline"
	tag.position = Vector2(COL_LEFT, LOGO_Y + logo.texture.get_height() + 3)
	root.add_child(tag)

	# Centred column as in the reference; it may overlap the player figure on the left.
	var w := 116
	var x := (NATIVE.x - w) / 2 + 1
	var y := 322
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
		y += spec[3] + 6
		if spec[0] == "daily":
			# centred under the button, as wide as the column allows on its right side
			var sw := 2 * (COL_RIGHT - (x + w / 2))
			var status := label("", "body_ol", PixelArt.CREAM, 1, HORIZONTAL_ALIGNMENT_CENTER, sw)
			status.name = "DailyStatus"
			status.position = Vector2(x + w / 2 - sw / 2, y - 5)
			status.set_meta("slot_y", y - 5)  # room for two lines; one line sits centred
			root.add_child(status)
			y += 16

	# Icon row as in the reference: stats bottom left, sound and how to play bottom right.
	for spec in [
		["stats", "STATS", PixelButton.ICON_STATS, COL_LEFT],
		["sound", "SOUND", PixelButton.ICON_SOUND_ON, 132],
		["howto", "HOW TO PLAY", PixelButton.ICON_HOWTO, COL_RIGHT - 32],
	]:
		var b := PixelButton.new(spec[0], "", PixelButton.STYLE_WOOD, 1)
		b.icon_rows = spec[2]
		b.position = Vector2(spec[3], 526)
		b.size = Vector2(32, 32)
		b.pressed.connect(_emit.bind(spec[0]))
		root.add_child(b)
		title_buttons.append(b)
		var cw := int(font("body_ol").get_string_size(spec[1], HORIZONTAL_ALIGNMENT_LEFT, -1, font_size("body_ol")).x) + 2
		var cap := label(spec[1], "body_ol", PixelArt.CREAM, 1, HORIZONTAL_ALIGNMENT_CENTER, cw)
		cap.name = "Cap_" + spec[0]
		cap.position = Vector2(clampi(spec[3] + 16 - cw / 2, COL_LEFT, COL_RIGHT - cw), 561)
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
		if size.x < 1 or size.y < 1:
			return
		var key := "%s %d %d %s" % [style, size.x, size.y, pressed_look]
		if key != _tex_key:
			_tex_key = key
			_tex = PixelArt.texture(GameUI.panel_image(int(size.x), int(size.y), style, pressed_look))
		draw_texture(_tex, Vector2.ZERO)


## A signboard button: the panel, its label or icon and the pressed look are baked into one
## palette image per state, so the label gets a hard two-tone fill and a full ink outline.
## Both states are baked on the first draw, so a tap never waits for a bake.
class PixelButton extends BaseButton:
	const STYLE_WOOD := "wood"
	const STYLE_RED := "red"

	# '#' cream, 'r' red. Every glyph gets a full ink outline, one extra ink row below it,
	# and cream pixels with nothing under them turn cream shade.
	const ICON_STATS := [
		".......rrr##.......",
		".......rrrr#.......",
		".......#rr##.......",
		".......##r##.......",
		".......#####..#####",
		".......#####..#####",
		".......#####..#####",
		"#####..#####..#####",
		"#####..#####..#####",
		"#####..#####..#####",
		"#####..#####..#####",
		"#####..#####..#####",
		"#####..#####..#####",
		"#####..#####..#####",
		"#####..#####..#####",
		"#####..#####..#####",
		"#####..#####..#####",
	]
	const ICON_HOWTO := [
		"...######...",
		".##########.",
		"####....####",
		"###......###",
		"###......###",
		".........###",
		"........####",
		".......####.",
		"......####..",
		".....####...",
		"....####....",
		"....####....",
		"....####....",
		"............",
		".....##.....",
		"....####....",
		"....####....",
		".....##.....",
	]
	const ICON_SOUND_ON := [
		"....................",
		"........#......##...",
		".......##.......##..",
		"......###........##.",
		".....####..##....##.",
		"#########...##....##",
		"#########....##...##",
		"#########....##...##",
		"#########....##...##",
		"#########....##...##",
		"#########...##....##",
		".....####..##....##.",
		"......###........##.",
		".......##.......##..",
		"........#......##...",
		"....................",
	]
	const ICON_SOUND_OFF := [
		"....................",
		"........#...........",
		".......##...........",
		"......###...........",
		".....####...rr...rr.",
		"#########...rrr.rrr.",
		"#########....rrrrr..",
		"#########.....rrr...",
		"#########....rrrrr..",
		"#########...rrr.rrr.",
		"#########...rr...rr.",
		".....####...........",
		"......###...........",
		".......##...........",
		"........#...........",
		"....................",
	]

	var id := ""
	var text := ""
	var style := STYLE_WOOD
	var text_scale := 1
	var face := "bold"
	var icon_rows: Array = []
	var _panel := {}  # state key -> [ImageTexture, label baked into it]
	var _prebake_due := false

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

	func _key(down: bool) -> String:
		return "%d %d %s %s %d" % [size.x, size.y, down, text, icon_rows.hash()]

	func _face(down: bool) -> Array:
		var key := _key(down)
		if not _panel.has(key):
			var w := int(size.x)
			var h := int(size.y)
			# the label's columns, so the bullet holes sit between the crosshairs and the text
			var span := GameUI.label_span(w, text, face, text_scale) if text != "" else Vector2i(-1, -1)
			var img := GameUI.panel_image(w, h, style, down, id, span)
			var shift := 1 if down else 0
			if not icon_rows.is_empty():
				GameUI.stamp_icon(img, icon_rows, (w - icon_rows[0].length()) / 2,
						(h - icon_rows.size()) / 2 + shift)
			var baked := true
			if text != "":
				baked = GameUI.stamp_label(img, text, face, text_scale, shift)
			_panel[key] = [PixelArt.texture(img), baked]
		return _panel[key]

	func _face_tex(down: bool) -> ImageTexture:
		return _face(down)[0]

	func _draw() -> void:
		if size.x < 1 or size.y < 1:
			return
		var down := is_pressed() or button_pressed
		var f := _face(down)
		draw_texture(f[0], Vector2.ZERO)
		if text != "" and not f[1]:  # a face without a readable atlas: plain shadowed text
			var fnt := GameUI.font(face)
			var fs := GameUI.font_size(face, text_scale)
			var tw := int(fnt.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x)
			var cap := GameUI.cap_height(face, text_scale)
			var base := (int(size.y) - cap + 1) / 2 + cap + (1 if down else 0)
			draw_string(fnt, Vector2((int(size.x) - tw) / 2, base + text_scale), text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, PixelArt.c(PixelArt.INK))
			draw_string(fnt, Vector2((int(size.x) - tw) / 2, base), text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, PixelArt.c(PixelArt.CREAM))
		# bake the other state a few frames later, one button at a time, not on the tap
		if not _prebake_due and not _panel.has(_key(not down)) and is_inside_tree():
			_prebake_due = true
			get_tree().create_timer(0.05 * (get_index() + 1)).timeout.connect(_prebake)

	func _prebake() -> void:
		_prebake_due = false
		if size.x >= 1 and size.y >= 1:
			_face(false)
			_face(true)


# --- label and icon rasters ----------------------------------------------------------------

static var _glyph_cache := {}

## Condensed signboard capitals, 11 px caps with 2 px stems (the wood button labels).
const SIGN_TALL := {
	"A": ["..###..", "..###..", ".##.##.", ".##.##.", ".##.##.", "##...##", "##...##", "#######", "##...##", "##...##", "##...##"],
	"B": ["#####.", "##..##", "##..##", "##..##", "#####.", "##..##", "##..##", "##..##", "##..##", "##..##", "#####."],
	"C": [".####.", "##..##", "##..##", "##....", "##....", "##....", "##....", "##....", "##..##", "##..##", ".####."],
	"D": ["#####.", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "#####."],
	"E": ["#####", "##...", "##...", "##...", "##...", "####.", "##...", "##...", "##...", "##...", "#####"],
	"F": ["#####", "##...", "##...", "##...", "##...", "####.", "##...", "##...", "##...", "##...", "##..."],
	"G": [".####.", "##..##", "##..##", "##....", "##....", "##.###", "##..##", "##..##", "##..##", "##..##", ".#####"],
	"H": ["##..##", "##..##", "##..##", "##..##", "##..##", "######", "##..##", "##..##", "##..##", "##..##", "##..##"],
	"I": ["##", "##", "##", "##", "##", "##", "##", "##", "##", "##", "##"],
	"J": ["...##", "...##", "...##", "...##", "...##", "...##", "...##", "...##", "##.##", "##.##", ".###."],
	"K": ["##..##", "##..##", "##.##.", "##.##.", "####..", "###...", "####..", "##.##.", "##.##.", "##..##", "##..##"],
	"L": ["##...", "##...", "##...", "##...", "##...", "##...", "##...", "##...", "##...", "##...", "#####"],
	"M": ["##....##", "###..###", "########", "##.##.##", "##.##.##", "##....##", "##....##", "##....##", "##....##", "##....##", "##....##"],
	"N": ["##..##", "###.##", "###.##", "######", "######", "##.###", "##.###", "##..##", "##..##", "##..##", "##..##"],
	"O": [".####.", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", ".####."],
	"P": ["#####.", "##..##", "##..##", "##..##", "##..##", "#####.", "##....", "##....", "##....", "##....", "##...."],
	"Q": [".####.", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##.###", "##..##", ".#####"],
	"R": ["#####.", "##..##", "##..##", "##..##", "##..##", "#####.", "##.##.", "##..##", "##..##", "##..##", "##..##"],
	"S": [".####.", "##..##", "##..##", "##....", "##....", ".####.", "....##", "....##", "##..##", "##..##", ".####."],
	"T": ["######", "..##..", "..##..", "..##..", "..##..", "..##..", "..##..", "..##..", "..##..", "..##..", "..##.."],
	"U": ["##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", ".####."],
	"V": ["##...##", "##...##", "##...##", "##...##", "##...##", ".##.##.", ".##.##.", ".##.##.", "..###..", "..###..", "..###.."],
	"W": ["##....##", "##....##", "##....##", "##.##.##", "##.##.##", "##.##.##", "##.##.##", "##.##.##", ".######.", ".##..##.", ".##..##."],
	"X": ["##..##", "##..##", "##..##", ".####.", "..##..", "..##..", ".####.", "##..##", "##..##", "##..##", "##..##"],
	"Y": ["##..##", "##..##", "##..##", "##..##", ".####.", "..##..", "..##..", "..##..", "..##..", "..##..", "..##.."],
	"Z": ["######", "....##", "....##", "...##.", "...##.", "..##..", ".##...", ".##...", "##....", "##....", "######"],
	"0": [".####.", "##..##", "##..##", "##..##", "##.###", "##.###", "###.##", "##..##", "##..##", "##..##", ".####."],
	"1": ["..##", ".###", "####", "..##", "..##", "..##", "..##", "..##", "..##", "..##", "..##"],
	"2": [".####.", "##..##", "....##", "....##", "...##.", "..##..", ".##...", "##....", "##....", "##....", "######"],
	"3": [".####.", "##..##", "....##", "....##", "..###.", "....##", "....##", "....##", "....##", "##..##", ".####."],
	"4": ["...###", "..####", ".##.##", "##..##", "##..##", "######", "....##", "....##", "....##", "....##", "....##"],
	"5": ["######", "##....", "##....", "##....", "#####.", "....##", "....##", "....##", "....##", "##..##", ".####."],
	"6": [".####.", "##..##", "##....", "##....", "#####.", "##..##", "##..##", "##..##", "##..##", "##..##", ".####."],
	"7": ["######", "....##", "....##", "...##.", "...##.", "..##..", "..##..", "..##..", "..##..", "..##..", "..##.."],
	"8": [".####.", "##..##", "##..##", "##..##", ".####.", "##..##", "##..##", "##..##", "##..##", "##..##", ".####."],
	"9": [".####.", "##..##", "##..##", "##..##", "##..##", ".#####", "....##", "....##", "....##", "##..##", ".####."],
	" ": ["...", "...", "...", "...", "...", "...", "...", "...", "...", "...", "..."],
	".": ["..", "..", "..", "..", "..", "..", "..", "..", "..", "##", "##"],
	",": ["..", "..", "..", "..", "..", "..", "..", "..", "..", "##", "##", ".#"],
	"!": ["##", "##", "##", "##", "##", "##", "##", "..", "..", "##", "##"],
	"?": [".####.", "##..##", "....##", "....##", "...##.", "..##..", "..##..", "..##..", "......", "..##..", "..##.."],
	"'": ["##", "##", ".#", "..", "..", "..", "..", "..", "..", "..", ".."],
	"-": ["....", "....", "....", "....", "....", "####", "....", "....", "....", "....", "...."],
	":": ["..", "..", "##", "##", "..", "..", "..", "..", "##", "##", ".."],
	"/": ["....##", "....##", "...##.", "...##.", "...##.", "..##..", ".##...", ".##...", ".##...", "##....", "##...."],
}

## Slab-serif western capitals, 18 px caps, with spurs low on the stems (the PLAY button).
const SIGN_HUGE := {
	"P": ["##########..", "###########.", ".####...####", ".####...####", ".####...####", ".####...####", ".####...####", ".####..#####", ".##########.", ".#########..", ".####.......", ".####.......", "######......", ".####.......", ".####.......", ".####.......", "#######.....", "#######....."],
	"L": ["#######....", "#######....", ".####......", ".####......", ".####......", ".####......", ".####......", ".####......", ".####......", ".####......", ".####......", ".####......", "######.....", ".####....##", ".####....##", ".####....##", "###########", "###########"],
	"A": [".....###.....", ".....####....", "....#####....", "....######...", "....######...", "...###.####..", "...###.####..", "...###.####..", "..###...####.", "..###...####.", "..##########.", "..##########.", ".###.....####", ".###.....####", ".###.....####", ".###.....####", "#####...#####", "#####...#####"],
	"Y": ["#####..#####", "#####..#####", ".###....###.", ".###....###.", "..###..###..", "..###..###..", "...######...", "...######...", "....####....", "....####....", "....####....", "....####....", "...######...", "....####....", "....####....", "....####....", "..########..", "..########.."],
}


## Pixels of `s` as signboard lettering at scale 1: [Array of Vector2i relative to the pen
## start on the baseline, ink width, cap height]. "huge" labels drawn only from SIGN_HUGE
## letters and "tall" labels drawn only from SIGN_TALL characters use those hand-drawn
## bitmaps; anything else is read from the font's own atlas. Returns an empty array when
## the atlas cannot be read.
static func text_pixels(s: String, face: String) -> Array:
	var key := face + "|" + s
	if _glyph_cache.has(key):
		return _glyph_cache[key]
	var out := []
	var hand := {}
	if face == "huge" and _covers(SIGN_HUGE, s):
		hand = SIGN_HUGE
	elif (face == "tall" or face == "huge") and _covers(SIGN_TALL, s):
		hand = SIGN_TALL
	if not hand.is_empty():
		out = _hand_pixels(s, hand)
	else:
		out = _atlas_pixels(s, face)
	if not out.is_empty():
		_glyph_cache[key] = out
	return out


static func _covers(glyphs: Dictionary, s: String) -> bool:
	if s.is_empty():
		return false
	for i in s.length():
		if not glyphs.has(s[i]):
			return false
	return true


## Hand-drawn glyphs: every row list starts at the cap line; rows past the cap height hang
## below the baseline. One pixel between letters, which the ink outlines close up.
static func _hand_pixels(s: String, glyphs: Dictionary) -> Array:
	var cap: int = glyphs["A" if glyphs.has("A") else glyphs.keys()[0]].size()
	var pts: Array[Vector2i] = []
	var pen := 0
	var right := 0
	for i in s.length():
		var rows: Array = glyphs[s[i]]
		var gw := 0
		for yy in rows.size():
			var r: String = rows[yy]
			gw = maxi(gw, r.length())
			for xx in r.length():
				if r[xx] != ".":
					pts.append(Vector2i(pen + xx, yy - cap))
					right = maxi(right, pen + xx + 1)
		pen += gw + 1
	return [pts, right, cap]


## Glyphs read from the face's atlas through the FontFile glyph API, as the font draws them.
static func _atlas_pixels(s: String, face: String) -> Array:
	var f := font(face)
	var sz := Vector2i(FACES[face][0], 0)
	if f.get_cache_count() < 1 or f.get_texture_count(0, sz) < 1:
		return []
	var atlases := {}
	var pts: Array[Vector2i] = []
	var pen := 0
	for i in s.length():
		var g: int = s.unicode_at(i)
		var adv := int(f.get_glyph_advance(0, sz.x, g).x)
		var uv := Rect2i(f.get_glyph_uv_rect(0, sz, g))
		var off := Vector2i(f.get_glyph_offset(0, sz, g))
		var ti := f.get_glyph_texture_idx(0, sz, g)
		if not atlases.has(ti):
			atlases[ti] = f.get_texture_image(0, sz, ti)
		var atlas: Image = atlases[ti]
		if atlas == null:
			return []
		for yy in uv.size.y:
			for xx in uv.size.x:
				if atlas.get_pixel(uv.position.x + xx, uv.position.y + yy).a > 0.5:
					pts.append(Vector2i(pen + off.x + xx, off.y + yy))
		pen += adv
	return [pts, pen, FACES[face][1]]


## Where stamp_label puts the label in a button `w` wide: the first and last columns of its
## ink outline, or (-1, -1) when it cannot be baked.
static func label_span(w: int, s: String, face: String, scale := 1) -> Vector2i:
	if s == "" or outlined(face):
		return Vector2i(-1, -1)
	var tp := text_pixels(s, face)
	if tp.is_empty():
		return Vector2i(-1, -1)
	var lo := 1 << 20
	var hi := -(1 << 20)
	for p in tp[0]:
		lo = mini(lo, p.x)
		hi = maxi(hi, p.x)
	var tx := (w - int(tp[1]) * scale) / 2
	return Vector2i(tx + lo * scale - scale, tx + hi * scale + 2 * scale - 1)


## Bakes a button label into img, centred in it: cream glyphs with a hard cream-shade band on
## the lower third, a full ink outline and one more ink row below.
static func stamp_label(img: Image, s: String, face: String, scale: int, shift: int) -> bool:
	if outlined(face):
		return false
	var tp := text_pixels(s, face)
	if tp.is_empty():
		return false
	var pts: Array = tp[0]
	var cap: int = tp[2]
	var tw: int = tp[1] * scale
	var tx := (img.get_width() - tw) / 2
	var base := (img.get_height() - cap * scale + 1) / 2 + cap * scale + shift
	var band := -maxi(2, cap / 3)
	var P := PixelArt
	# a mask over the label's box: 2 glyph, 1 outline (8 neighbours plus one more row below)
	var lo := Vector2i(1 << 20, 1 << 20)
	var hi := -lo
	for p in pts:
		lo = lo.min(p)
		hi = hi.max(p)
	var mw := hi.x - lo.x + 3
	var mh := hi.y - lo.y + 4
	var mask := PackedByteArray()
	mask.resize(mw * mh)
	for p in pts:
		mask[(p.y - lo.y + 1) * mw + p.x - lo.x + 1] = 2
	for p in pts:
		var i: int = (p.y - lo.y) * mw + p.x - lo.x
		for dy in 4:
			for dx in 3:
				var j := i + dy * mw + dx
				if mask[j] == 0:
					mask[j] = 1
	var cols := [P.c(P.INK), P.c(P.CREAM), P.c(P.CREAM_SHADE)]
	for my in mh:
		var gy := lo.y - 1 + my
		for mx in mw:
			var m := mask[my * mw + mx]
			if m == 0:
				continue
			var col: Color = cols[0] if m == 1 else (cols[2] if gy >= band else cols[1])
			var x := tx + (lo.x - 1 + mx) * scale
			var y := base + gy * scale
			if scale == 1:
				P.px(img, x, y, col)
			else:
				P.rect(img, x, y, scale, scale, col)
	return true


## Bakes an icon bitmap into img at (ox, oy) with the same outline treatment as the labels.
static func stamp_icon(img: Image, rows: Array, ox: int, oy: int) -> void:
	var P := PixelArt
	var ink := P.c(P.INK)
	var ih := rows.size()
	for ry in ih:
		var r: String = rows[ry]
		for rx in r.length():
			if r[rx] == ".":
				continue
			for dy in [-1, 0, 1, 2]:
				for dx in [-1, 0, 1]:
					P.px(img, ox + rx + dx, oy + ry + dy, ink)
	for ry in ih:
		var r: String = rows[ry]
		for rx in r.length():
			var ch := r[rx]
			if ch == ".":
				continue
			var col := P.CREAM
			if ch == "r":
				col = P.RED
			elif ch == "s":
				col = P.CREAM_SHADE
			elif ry == ih - 1 or rx >= String(rows[ry + 1]).length() or String(rows[ry + 1])[rx] == ".":
				col = P.CREAM_SHADE
			P.px(img, ox + rx, oy + ry, P.c(col))


# --- panels ----------------------------------------------------------------------------------

const OUTLINE := 2  # ink outline width of the wood and red signboards and icon squares


## Wood, red, dark and inset signboards after the reference buttons. Wood and red buttons: a
## two-pixel ink silhouette with a square notch at each corner, two lit frame rings (brightest
## on the top and left) and a dark groove that all step round the notches, a diamond knob on
## each notched corner, a planked fill with long grain strokes and a seam through the middle
## (red paint darkens into the groove and toward the bottom), a crosshair at each end and a
## bullet hole with short cracks between each crosshair and the label. `clear` is the label's
## column span (label_span); the holes stay out of it. Icon squares get the same frame with
## stepped diagonal corners and a plain fill. Dark and inset cards keep a one-pixel outline,
## a diagonal chamfer and small nails. Drawn pixel by pixel at the exact size and seeded from
## style, size and `variant`, so equal panels match; the pressed state only swaps the frame
## light and moves the content down one pixel.
static func panel_image(w: int, h: int, style: String, down := false, variant := "",
		clear := Vector2i(-1, -1)) -> Image:
	var P := PixelArt
	var img := P.new_image(w, h)
	var button := style == "wood" or style == "red"
	var square := w <= 40 and h <= 40
	var notch := 2 if button and not square else 0
	var cham := 3 if square else 2
	var ol := OUTLINE if button else 1  # ink outline width
	# ring 1 and ring 2 as [top and left, bottom and right]
	var r1 := [P.SAND, P.TAN]
	var r2 := [P.OCHRE, P.LEATHER]
	var groove := P.BROWN_BLACK
	var fill := P.BROWN_DARK
	var edge := P.BROWN_DARK  # the first two fill rows inside the groove
	var grain := P.BROWN_BLACK
	var grain2 := P.BROWN
	var seam := P.BROWN_BLACK
	var knob := P.SAND
	var sight := [P.SAND, P.TAN]
	var nail := -1
	var sparse := false
	match style:
		"red":
			r1 = [P.LAMP, P.AMBER]; r2 = [P.ORANGE, P.RUST]; groove = P.WINE_DARK
			fill = P.BLOOD; edge = P.MAROON; grain = P.MAROON; grain2 = P.RED; seam = P.MAROON
			knob = P.LAMP; sight = [P.LAMP, P.GOLD]
		"dark":
			r1 = [P.LEATHER, P.BROWN_DARK]; r2 = [P.BROWN, P.BROWN]; groove = P.INK
			fill = P.CHARCOAL; edge = P.CHARCOAL; grain = P.INK; grain2 = P.PLUM; nail = P.OCHRE
			sparse = true
		"inset":
			r1 = [P.BROWN, P.BROWN_DARK]; r2 = [P.CHARCOAL, P.CHARCOAL]; groove = P.INK
			fill = P.INK; edge = P.INK; grain = P.CHARCOAL; grain2 = P.CHARCOAL; sparse = true
	if down:
		r1 = [r1[1], r1[0]]
		r2 = [r2[1], r2[0]]
	var shift := 1 if down else 0
	var cols := [P.c(P.INK), [P.c(r1[0]), P.c(r1[1])], [P.c(r2[0]), P.c(r2[1])], P.c(groove)]
	var c_fill := P.c(fill)
	var c_edge := P.c(edge)
	# silhouette and rings from the depth to the notched or chamfered edge; only the border
	# band is walked pixel by pixel, the plain middle of the fill is one rectangle
	var band := 5 + ol + notch
	var depth := PackedInt32Array()
	depth.resize(w * h)
	depth.fill(6)
	if w > 2 * band and h > 2 * band:
		img.fill_rect(Rect2i(band, band, w - 2 * band, h - 2 * band), c_fill)
	var bayer: Array = P.BAYER4
	for y in h:
		var b := h - 1 - y
		var inner := y >= band and b >= band and w > 2 * band
		var x := 0
		while x < w:
			if inner and x == band:
				x = w - band
			var r := w - 1 - x
			var d: int
			if notch > 0:
				d = maxi(mini(mini(x - notch, r - notch), mini(y, b)), mini(mini(x, r), mini(y - notch, b - notch)))
			else:
				d = mini(mini(mini(x, y), mini(r, b)), mini(mini(x + y, r + y), mini(x + b, r + b)) - cham)
			if d >= 0 and d < ol - 1:
				d = 0  # the outer rows of a wide outline
			elif d >= 0:
				d -= ol - 1
			depth[y * w + x] = d
			if d >= 0:
				var col: Color
				if d >= 6:
					col = c_fill
				elif d >= 4:
					# the paint darkens into the groove: a solid row, then an ordered-dither row
					col = c_edge if d == 4 or bayer[y & 3][x & 3] < 8 else c_fill
				elif d == 0 or d == 3:
					col = cols[d]
				else:
					col = cols[d][0 if mini(x, y) <= mini(r, b) else 1]
				img.set_pixel(x, y, col)
			x += 1
	# grain: long horizontal strokes on close rows, the light ones shorter. Rows are chosen
	# unshifted so both states consume the same random numbers.
	var rng := RandomNumberGenerator.new()
	rng.seed = hash("%s%d%d%s" % [style, w, h, variant])
	var gap := Vector2i(3, 12)
	if sparse:
		gap = Vector2i(5, 16)
	var gy := 4 + ol
	while gy < h - 4 - ol:
		var gx := 5 + rng.randi_range(0, 10)
		while gx < w - 6:
			var run := rng.randi_range(6, 30)
			var c := grain
			var dark := rng.randf()
			if style == "red" and gy > h / 2 and dark < float(gy) / h:
				c = P.WINE  # the paint darkens toward the bottom
			var light := rng.randf() < (0.15 if style == "red" else 0.3)
			if light and not square and (style != "red" or (gy >= 7 and gy < h / 2 - 2)):
				c = grain2
				run = mini(run, rng.randi_range(3, 8) if style == "red" else rng.randi_range(6, 14))
			_hline_on(img, depth, gx, mini(gx + run - 1, w - 6), gy + shift, P.c(c), 4)
			gx += run + rng.randi_range(gap.x, gap.y)
		gy += rng.randi_range(7, 11) if sparse else rng.randi_range(2, 4)
	# damage has its own generator, so the pressed state keeps every crack in place
	var dmg := RandomNumberGenerator.new()
	dmg.seed = hash("%s%d%d%s holes" % [style, w, h, variant])
	if button and not square:
		_hline_on(img, depth, 4, w - 5, h / 2 + shift, P.c(seam), 4)
	if style == "red":  # dark flecks in the paint
		for i in dmg.randi_range(6, 10):
			var fx := dmg.randi_range(6, w - 8)
			var fy := dmg.randi_range(6, h - 7) + shift
			_hline_on(img, depth, fx, fx + dmg.randi_range(0, 1), fy, P.c(P.WINE), 5)
	if button and not square and w >= 60:
		var m := roundi(w * 0.15)
		var left := Vector2i(13, clear.x - 2 if clear.x >= 0 else 2 * m - 13)
		var right := Vector2i(clear.y + 2 if clear.y >= 0 else w - 1 - (2 * m - 13), w - 14)
		_bullet_hole(img, depth, left, h / 2 - 1 + shift, dmg, style)
		_bullet_hole(img, depth, right, h / 2 + 1 + shift, dmg, style)
	if button and not square and w >= 40 and h >= 18:
		for cx in [8, w - 9]:
			_crosshair(img, cx, h / 2 + shift, sight)
	if notch > 0:
		var k := 3 + ol
		for c in [Vector2i(k, k), Vector2i(w - 1 - k, k), Vector2i(k, h - 1 - k), Vector2i(w - 1 - k, h - 1 - k)]:
			_knob(img, c, knob)
	if nail >= 0 and w >= 16 and h >= 14:
		for c in [Vector2i(5, 5), Vector2i(w - 6, 5), Vector2i(5, h - 6), Vector2i(w - 6, h - 6)]:
			for o in [Vector2i(0, -1), Vector2i(-1, 0), Vector2i(1, 0), Vector2i(0, 1)]:
				P.px(img, c.x + o.x, c.y + o.y, P.c(nail))
			P.px(img, c.x, c.y, P.c(P.CREAM))
	return img


## A horizontal run painted only where the panel is at least `min_depth` deep.
static func _hline_on(img: Image, depth: PackedInt32Array, x0: int, x1: int, y: int, col: Color,
		min_depth: int) -> void:
	var w := img.get_width()
	if y < 0 or y >= img.get_height():
		return
	for x in range(maxi(x0, 0), mini(x1, w - 1) + 1):
		if depth[y * w + x] >= min_depth:
			img.set_pixel(x, y, col)


## A hollow diamond knob in the inner corner of a notch, with an ink heart.
static func _knob(img: Image, c: Vector2i, col: int) -> void:
	var P := PixelArt
	for o in [Vector2i(2, 0), Vector2i(-2, 0), Vector2i(0, 2), Vector2i(0, -2),
			Vector2i(1, 1), Vector2i(-1, 1), Vector2i(1, -1), Vector2i(-1, -1)]:
		P.px(img, c.x + o.x, c.y + o.y, P.c(col))
	for o in [Vector2i(0, 0), Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
		P.px(img, c.x + o.x, c.y + o.y, P.c(P.INK))


## A gun sight: a small ring round an ink heart, its corners a shade darker so it reads
## round, and four two-pixel spokes with cream tips. col is [bright, dim].
static func _crosshair(img: Image, cx: int, cy: int, col: Array) -> void:
	var P := PixelArt
	for o in [Vector2i(1, 1), Vector2i(-1, 1), Vector2i(1, -1), Vector2i(-1, -1)]:
		P.px(img, cx + o.x, cy + o.y, P.c(col[1]))
	P.px(img, cx, cy, P.c(P.INK))
	for o in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
		P.px(img, cx + o.x, cy + o.y, P.c(col[0]))
		P.px(img, cx + o.x * 2, cy + o.y * 2, P.c(col[0]))
		P.px(img, cx + o.x * 3, cy + o.y * 3, P.c(P.CREAM))


## A bullet hole centred in the free columns span.x..span.y: a round ink hole (five pixels
## across when there is room, else four) with a scorched rim on its upper left and a lit lip on
## its lower right, and two or three short cracks, each with an ink root and one lit pixel
## beside it. Cracks stay inside the span and the fill and are left out when the span is
## narrow; with no room for the hole there is no hole.
static func _bullet_hole(img: Image, depth: PackedInt32Array, span: Vector2i, cy: int,
		rng: RandomNumberGenerator, style: String) -> void:
	var P := PixelArt
	var wood := style == "wood"
	var scorch := P.c(P.BROWN_BLACK if wood else P.WINE_DARK)
	var lip := P.c(P.ORANGE)
	var crack := P.c(P.BROWN_BLACK if wood else P.WINE_DARK)
	var crack_lit := P.c(P.OCHRE if wood else P.ORANGE)
	var ink := P.c(P.INK)
	var room := span.y - span.x + 1
	# every random number is drawn up front, so the shape never depends on the room
	var n := 3 if span.y - span.x >= 11 else 2
	var a0 := rng.randf() * TAU
	var nub := rng.randi_range(0, 3)
	var jit := []
	for i in 3:
		jit.append([rng.randf_range(-0.35, 0.35), rng.randi_range(3, 5), rng.randf_range(-0.7, 0.7)])
	if room < 4:
		return
	var w := img.get_width()
	var h := img.get_height()
	var s := 4
	if room >= 13 and h >= 34:
		s = 6
	elif room >= 9:
		s = 5
	var cx := (span.x + span.y + 1) / 2
	var o := Vector2i(cx - s / 2, cy - s / 2)
	var clip := Rect2i(span.x, 5, room, h - 10)
	var core := {}
	for j in s:
		for i in s:
			if (i == 0 or i == s - 1) and (j == 0 or j == s - 1):
				continue
			core[o + Vector2i(i, j)] = true
	# one ragged edge pixel so the holes are not all the same coin
	var nubs := [Vector2i(s - 1, 0), Vector2i(0, s - 1), Vector2i(s, 1), Vector2i(1, s)]
	if s == 6:  # a big hole gets ragged on both sides
		core[o + nubs[(nub + 2) % 4]] = true
	core[o + nubs[nub]] = true
	if room >= 7:
		var centre := Vector2(o.x + (s - 1) / 2.0, o.y + (s - 1) / 2.0)
		for i in n:
			var a: float = a0 + TAU * i / n + jit[i][0]
			var dir := Vector2(cos(a), sin(a))
			var bend: float = a + jit[i][2]
			var pts: Array[Vector2i] = []
			var p := centre + dir * (s / 2.0 + 0.6)
			for k in jit[i][1]:
				var q := Vector2i(roundi(p.x), roundi(p.y))
				if pts.is_empty() or pts[-1] != q:
					pts.append(q)
				p += (dir if k < 2 else Vector2(cos(bend), sin(bend)))
			for k in pts.size():
				var q := pts[k]
				if core.has(q) or not clip.has_point(q) or depth[q.y * w + q.x] < 5:
					break
				P.px(img, q.x, q.y, ink if k == 0 else crack)
				if k == 0 or (wood and k < pts.size() - 1):
					# the lit edge is on the side facing down and right; cracks in the wood
					# catch the light along their length, cracks in the paint at the root
					var side := Vector2i(roundi(-dir.y), roundi(dir.x))
					if side.x + side.y < 0:
						side = -side
					if side == Vector2i.ZERO:
						side = Vector2i(0, 1)
					var t := q + side
					if not core.has(t) and not pts.has(t) and clip.has_point(t) and depth[t.y * w + t.x] >= 5:
						P.px(img, t.x, t.y, crack_lit)
	for q in [o, o + Vector2i(1, -1), o + Vector2i(2, -1), o + Vector2i(-1, 1), o + Vector2i(-1, 2)]:
		if not core.has(q) and clip.has_point(q) and depth[q.y * w + q.x] >= 4:
			P.px(img, q.x, q.y, scorch)
	for q in core:
		P.px(img, q.x, q.y, ink)
	var e := s - 1
	for q in [o + Vector2i(e, e), o + Vector2i(e + 1, e - 1), o + Vector2i(e - 1, e + 1)]:
		if not core.has(q) and clip.has_point(q) and depth[q.y * w + q.x] >= 4:
			P.px(img, q.x, q.y, lip)
