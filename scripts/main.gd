extends Node2D
## Game loop and states, the render pipeline, persistence and the headless test modes.
##
## Pipeline: the world is drawn into a SubViewport at native resolution (270 x 584 plus any
## overscan the screen shape needs) and shown through a SubViewportContainer that scales it
## by an integer factor with nearest-neighbour filtering. The UI has its own native-resolution
## SubViewport with a transparent background, scaled the same way and laid over the world, so
## HUD, cards and stamps share the world's pixel grid and even rotated stamps stay crisp.

enum State {
	TITLE, INTRO, READY, STANDOFF, DRAW, FALSESTART, FIRING, ENGAGE, WOUNDED, DRAW2,
	KILL, RESULT, PLAYERHIT, GAMEOVER, STATS, PAUSED,
}

const NATIVE := Vector2i(270, 584)
const TEST_MODES := ["autotest", "deathtest", "flowtest", "dailytest", "aimtest"]

var state: int = State.TITLE
var args := {}
var test_mode := ""

var pixel_scale := 2
var vp_size := NATIVE
var safe_origin := Vector2i.ZERO
var forced_window := Vector2i.ZERO   # tests pin the layout to a phone-sized window

var screen_layer: CanvasLayer
var world_box: SubViewportContainer
var world_vp: SubViewport
var stage: Node2D                    # world content; moved in whole pixels for shake
var world: Node2D
var ui_box: SubViewportContainer
var ui_vp: SubViewport
var ui: GameUI

var pb := {}
var pb_path := "user://pb.cfg"
var last_action := ""


# --- start-up ----------------------------------------------------------------------------

func _ready() -> void:
	args = parse_args(OS.get_cmdline_user_args())
	for m in TEST_MODES:
		if args.has(m):
			test_mode = m
	if test_mode != "":
		pb_path = "user://test_pb.cfg"
		DirAccess.remove_absolute(ProjectSettings.globalize_path(pb_path))
		forced_window = Vector2i(540, 1168)
		get_tree().root.size = forced_window  # headless windows start tiny; GUI picking needs room
	_load_pb()
	_build_pipeline()
	_build_world()
	_build_ui()
	get_tree().root.size_changed.connect(_apply_layout)
	_apply_layout()
	_enter_title()
	if test_mode != "":
		_run_tests.call_deferred(test_mode)
	elif args.has("shot"):
		_do_shot.call_deferred()


static func parse_args(list: PackedStringArray) -> Dictionary:
	var out := {}
	for a in list:
		var s := a.trim_prefix("--")
		var eq := s.find("=")
		if eq >= 0:
			out[s.substr(0, eq)] = s.substr(eq + 1)
		else:
			out[s] = true
	return out


## Integer scale and viewport size for a window. The viewport covers the whole window in
## native pixels; the 270 x 584 safe area sits centred inside it.
static func compute_layout(win: Vector2i) -> Dictionary:
	var k := maxi(1, mini(win.x / NATIVE.x, win.y / NATIVE.y))
	var vp := Vector2i(maxi(NATIVE.x, win.x / k), maxi(NATIVE.y, win.y / k))
	return {
		"scale": k,
		"viewport": vp,
		"safe_origin": (vp - NATIVE) / 2,
		"offset": (win - vp * k) / 2,
	}


func _build_pipeline() -> void:
	screen_layer = CanvasLayer.new()
	screen_layer.name = "Screen"
	add_child(screen_layer)

	world_box = SubViewportContainer.new()
	world_box.name = "WorldBox"
	world_box.stretch = true
	world_box.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	world_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	screen_layer.add_child(world_box)
	world_vp = SubViewport.new()
	world_vp.name = "WorldView"
	_pixel_viewport(world_vp, false)
	world_box.add_child(world_vp)
	stage = Node2D.new()
	stage.name = "Stage"
	world_vp.add_child(stage)

	ui_box = SubViewportContainer.new()
	ui_box.name = "UIBox"
	ui_box.stretch = true
	ui_box.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	ui_box.mouse_filter = Control.MOUSE_FILTER_STOP
	screen_layer.add_child(ui_box)
	ui_vp = SubViewport.new()
	ui_vp.name = "UIView"
	_pixel_viewport(ui_vp, true)
	ui_box.add_child(ui_vp)


func _pixel_viewport(vp: SubViewport, transparent: bool) -> void:
	vp.transparent_bg = transparent
	vp.disable_3d = true
	vp.msaa_2d = Viewport.MSAA_DISABLED
	vp.screen_space_aa = Viewport.SCREEN_SPACE_AA_DISABLED
	vp.snap_2d_transforms_to_pixel = true
	vp.snap_2d_vertices_to_pixel = true
	vp.canvas_item_default_texture_filter = Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_NEAREST
	vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	vp.handle_input_locally = true


func _apply_layout() -> void:
	var win := forced_window if forced_window != Vector2i.ZERO else get_tree().root.size
	var l := compute_layout(win)
	pixel_scale = l.scale
	vp_size = l.viewport
	safe_origin = l.safe_origin
	for box in [world_box, ui_box]:
		box.stretch_shrink = pixel_scale
		box.position = l.offset
		box.size = vp_size * pixel_scale
	stage.position = safe_origin
	if ui:
		ui.layout(vp_size, safe_origin)


func _build_world() -> void:
	PixelArt.set_sun(0.0)
	world = WorldBuilder.build(stage, 1873)


func _build_ui() -> void:
	ui = GameUI.new()
	ui_vp.add_child(ui)
	ui.build_title()
	ui.build_card("howto", "HOW TO PLAY", [
		["1. HOLD", "Keep your thumb on the screen to steady your hand."],
		["2. AIM", "Slide up or down to aim from gut to chest to head."],
		["3. DRAW", "Release when DRAW appears to shoot."],
	], "GOT IT", "back")
	# Placeholders until their milestones build the real screens.
	ui.build_card("play", "PLAY", ["The first duel rides in with milestone 4."], "BACK", "back")
	ui.build_card("practice", "PRACTICE", ["The straw man arrives with milestone 4."], "BACK", "back")
	ui.build_card("daily", "DAILY DUEL", ["The daily duel opens with milestone 6."], "BACK", "back")
	ui.build_card("scores", "HIGH SCORES", ["No names on the ladder yet."], "BACK", "back")
	ui.build_card("outlaws", "OUTLAWS", ["Ten names on the wall. Meet them in a run."], "BACK", "back")
	ui.build_card("stats", "STATS", ["No duels fought yet."], "BACK", "back")
	ui.action.connect(_on_action)
	ui.set_sound(pb.get("sound", true))
	Sfx.set_muted(not pb.get("sound", true))


# --- states and menus --------------------------------------------------------------------

func _enter_title() -> void:
	state = State.TITLE
	ui.set_daily_status(daily_status_text())
	ui.show_screen("title")


func _on_action(what: String) -> void:
	last_action = what
	match what:
		"back":
			_enter_title()
		"sound":
			pb["sound"] = not pb.get("sound", true)
			ui.set_sound(pb["sound"])
			Sfx.set_muted(not pb["sound"])
			_save_pb()
		"stats":
			state = State.STATS
			ui.show_screen("stats")
		"play", "practice", "daily", "scores", "outlaws", "howto":
			ui.show_screen(what)


## yyyymmdd for a date dictionary from Time.get_date_dict_from_system().
static func daily_seed(date: Dictionary) -> int:
	return int(date.year) * 10000 + int(date.month) * 100 + int(date.day)


func daily_status_text() -> String:
	var today := daily_seed(Time.get_date_dict_from_system())
	var d: Dictionary = pb.get("daily", {})
	if int(d.get("date", 0)) == today:
		return "TODAY: %d DUELS · $%d · BACK TOMORROW" % [int(d.get("wins", 0)), int(d.get("bounty", 0))]
	return "ONE TRY TODAY"


# --- persistence -------------------------------------------------------------------------

func _load_pb() -> void:
	pb = {}
	if FileAccess.file_exists(pb_path):
		var f := FileAccess.open(pb_path, FileAccess.READ)
		var parsed = JSON.parse_string(f.get_as_text())
		if parsed is Dictionary:
			pb = parsed


func _save_pb() -> void:
	var f := FileAccess.open(pb_path, FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify(pb, "  "))


# --- frame capture -----------------------------------------------------------------------

func _do_shot() -> void:
	var when: String = str(args.get("when", "title"))
	var out: String = str(args.get("out", "/tmp/shot.png"))
	if when != "title":
		print("[autotest] shot: --when=%s arrives in a later milestone" % when)
		get_tree().quit(1)
		return
	if args.has("screen"):  # e.g. --screen=howto to look at a menu card
		ui.show_screen(str(args.screen))
	for i in 10:
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var native := capture_native()
	var big := get_viewport().get_texture().get_image()
	var r := Rect2i(Vector2i(ui_box.position) + safe_origin * pixel_scale, NATIVE * pixel_scale)
	big = big.get_region(r.intersection(Rect2i(Vector2i.ZERO, big.get_size())))
	big.save_png(out)
	native.save_png(out.get_basename() + "_native.png")
	print("[autotest] shot saved %s (%dx%d) and native %dx%d" % [out, big.get_width(), big.get_height(), native.get_width(), native.get_height()])
	get_tree().quit(0)


## World and UI composited at native resolution, cropped to the 270 x 584 safe area.
func capture_native() -> Image:
	var w := world_vp.get_texture().get_image()
	var u := ui_vp.get_texture().get_image()
	w.convert(Image.FORMAT_RGBA8)
	u.convert(Image.FORMAT_RGBA8)
	w.blend_rect(u, Rect2i(Vector2i.ZERO, u.get_size()), Vector2i.ZERO)
	return w.get_region(Rect2i(safe_origin, NATIVE))


# --- tests -------------------------------------------------------------------------------
# Every mode prints [autotest] lines and exits 0 when everything passed, 1 otherwise.
# Parts that belong to later milestones print SKIP lines naming the milestone.

var _t_pass := 0
var _t_fail := 0


func check(what: String, ok: bool, detail := "") -> void:
	if ok:
		_t_pass += 1
		print("[autotest] PASS %s" % what)
	else:
		_t_fail += 1
		print("[autotest] FAIL %s  %s" % [what, detail])


func skip(what: String, milestone: int) -> void:
	print("[autotest] SKIP %s (milestone %d)" % [what, milestone])


func _run_tests(mode: String) -> void:
	await get_tree().process_frame
	await get_tree().process_frame
	print("[autotest] mode %s" % mode)
	match mode:
		"autotest":
			await _autotest()
		"deathtest":
			await _deathtest()
		"flowtest":
			await _flowtest()
		"dailytest":
			await _dailytest()
		"aimtest":
			await _aimtest()
	print("[autotest] %s done: %d passed, %d failed" % [mode, _t_pass, _t_fail])
	DirAccess.remove_absolute(ProjectSettings.globalize_path(pb_path))
	get_tree().quit(0 if _t_fail == 0 else 1)


func _autotest() -> void:
	_test_palette()
	_test_raster()
	_test_layout()
	_test_title()
	_test_roster()
	check("starts on the title", state == State.TITLE)
	skip("head Execution with corpse shots and bonus forfeit", 4)
	skip("wounded exchange on both sides", 4)
	skip("false-start death, death card and ladder", 4)
	skip("deep kin duel", 4)
	skip("miss, graze, settled headshot", 4)
	skip("fallen bodies connected, near the duel area, grounded", 5)


func _test_palette() -> void:
	var pal := PixelArt.palette()
	var uniq := {}
	for col in pal:
		uniq[col.to_rgba32()] = true
	check("palette has 64 distinct colours", pal.size() == 64 and uniq.size() == 64, "%d/%d" % [pal.size(), uniq.size()])
	var names := FileAccess.get_file_as_string("res://assets/palette_names.txt").strip_edges().split("\n")
	var consts := (load("res://scripts/pixel_art.gd") as Script).get_script_constant_map()
	var named_ok := names.size() == PixelArt.PALETTE_SIZE
	for i in names.size():
		if not consts.has(names[i]) or consts[names[i]] != i:
			named_ok = false
	check("palette names in pixel_art.gd match tools/palette.py", named_ok)
	check("INK is the darkest outline colour", PixelArt.c(PixelArt.INK).to_html(false) == "1f0e16")
	check("sun_t gold at duel 1", is_equal_approx(PixelArt.sun_t_for_duel(1), 0.0))
	check("sun_t 3/7 at duel 4", is_equal_approx(PixelArt.sun_t_for_duel(4), 3.0 / 7.0))
	check("sun_t deep red from duel 8", PixelArt.sun_t_for_duel(8) == 1.0 and PixelArt.sun_t_for_duel(40) == 1.0)
	var a := PixelArt.palette_at(0.0)
	var b := PixelArt.palette_at(1.0)
	var fixed_same := true
	var swap_diff := true
	for i in PixelArt.PALETTE_SIZE:
		if i < PixelArt.FIRST_SWAP and a[i] != b[i]:
			fixed_same = false
		if i >= PixelArt.FIRST_SWAP and a[i] == b[i]:
			swap_diff = false
	check("sun ramp swaps only the 16 sky, sun, rim, dust and haze entries", fixed_same and swap_diff)
	PixelArt.set_sun(0.5)
	check("mid-run palette still 64 colours", PixelArt.palette().size() == 64)
	PixelArt.set_sun(0.0)


func _test_raster() -> void:
	var P := PixelArt
	var ink := P.c(P.INK)
	var red := P.c(P.RED)
	var img := P.new_image(16, 16)
	P.line(img, 0, 0, 5, 3, ink)
	check("line covers both endpoints", img.get_pixel(0, 0) == ink and img.get_pixel(5, 3) == ink)
	check("line has one pixel per major step", P.count_colors(img) == 1 and _opaque(img) == 6, str(_opaque(img)))
	img = P.new_image(16, 16)
	P.rect(img, 2, 3, 4, 5, red)
	check("rect fills w*h pixels", _opaque(img) == 20)
	P.rect(img, -5, -5, 8, 8, red)
	check("rect clips at the edges", img.get_pixel(0, 0) == red)
	img = P.new_image(21, 21)
	P.ellipse(img, 10, 10, 7, 4, red)
	var sym := true
	for y in 21:
		for x in 21:
			if img.get_pixel(x, y) != img.get_pixel(20 - x, y) or img.get_pixel(x, y) != img.get_pixel(x, 20 - y):
				sym = false
	check("ellipse is symmetric", sym)
	img = P.new_image(12, 12)
	P.polygon(img, PackedVector2Array([Vector2(0, 0), Vector2(10, 0), Vector2(0, 10)]), red)
	var n := _opaque(img)
	check("polygon fill is close to the triangle area", n >= 45 and n <= 60, str(n))
	img = P.new_image(8, 8)
	P.dither_rect(img, 0, 0, 4, 4, red, ink, 0.5)
	var dark := 0
	for y in 4:
		for x in 4:
			if img.get_pixel(x, y) == ink:
				dark += 1
	check("dither at 0.5 is half and half", dark == 8, str(dark))
	img = P.new_image(9, 9)
	P.px(img, 4, 4, red)
	P.outline(img, ink)
	check("outline adds 4 neighbours", _opaque(img) == 5 and img.get_pixel(3, 4) == ink and img.get_pixel(3, 3).a == 0)
	P.outline(img, ink, true)
	check("diagonal outline fills the ring", _opaque(img) == 13 + 8 or _opaque(img) == 21, str(_opaque(img)))
	var dst := P.new_image(4, 4, ink)
	var src := P.new_image(4, 4)
	src.set_pixel(1, 1, Color(red, 0.8))
	P.blit(dst, src, 0, 0)
	check("blit never blends", dst.get_pixel(1, 1) == red and dst.get_pixel(0, 0) == ink)
	var messy := P.new_image(4, 4, Color(0.9, 0.2, 0.18, 0.7))
	P.quantize(messy)
	check("quantize snaps to palette and full alpha", P.is_palette_clean(messy))
	var logo: Texture2D = load("res://assets/ui/logo.png")
	check("logo uses palette colours only", P.is_palette_clean(logo.get_image()))
	var panel := GameUI.panel_image(112, 21, "wood")
	check("wood panel uses palette colours only", P.is_palette_clean(panel))
	check("red panel uses palette colours only", P.is_palette_clean(GameUI.panel_image(112, 28, "red")))


func _opaque(img: Image) -> int:
	var n := 0
	for y in img.get_height():
		for x in img.get_width():
			if img.get_pixel(x, y).a > 0.5:
				n += 1
	return n


func _test_layout() -> void:
	var l := compute_layout(Vector2i(540, 1168))
	check("540x1168 is exactly 2x native", l.scale == 2 and l.viewport == NATIVE and l.safe_origin == Vector2i.ZERO)
	l = compute_layout(Vector2i(1080, 2400))
	check("1080x2400 scales 4x and extends the world", l.scale == 4 and l.viewport == Vector2i(270, 600) and l.safe_origin == Vector2i(0, 8), str(l))
	l = compute_layout(Vector2i(1440, 3200))
	check("1440x3200 scales 5x", l.scale == 5 and l.safe_origin.x <= WorldBuilder.OVERSCAN.x and l.safe_origin.y <= WorldBuilder.OVERSCAN.y, str(l))
	l = compute_layout(Vector2i(720, 1600))
	check("720x1600 scales 2x inside the overscan", l.scale == 2 and l.safe_origin.x <= WorldBuilder.OVERSCAN.x and l.safe_origin.y <= WorldBuilder.OVERSCAN.y, str(l))
	l = compute_layout(Vector2i(1536, 2048))
	check("tablet scales 3x and stays inside the overscan", l.scale == 3 and l.safe_origin.x <= WorldBuilder.OVERSCAN.x and l.safe_origin.y <= WorldBuilder.OVERSCAN.y, str(l))
	l = compute_layout(Vector2i(100, 100))
	check("tiny window falls back to 1x native", l.scale == 1 and l.viewport == NATIVE)
	check("world viewport is opaque", not world_vp.transparent_bg)
	check("ui viewport is transparent", ui_vp.transparent_bg)
	check("viewports snap to pixels", world_vp.snap_2d_transforms_to_pixel and world_vp.snap_2d_vertices_to_pixel and ui_vp.snap_2d_transforms_to_pixel)
	check("nearest filtering everywhere", world_vp.canvas_item_default_texture_filter == Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_NEAREST
		and world_box.texture_filter == CanvasItem.TEXTURE_FILTER_NEAREST and ui_box.texture_filter == CanvasItem.TEXTURE_FILTER_NEAREST
		and int(ProjectSettings.get_setting("rendering/textures/canvas_textures/default_texture_filter")) == 0)
	check("containers scale by the integer factor", world_box.stretch_shrink == pixel_scale and ui_box.stretch_shrink == pixel_scale and world_vp.size == vp_size)
	check("stage sits on whole pixels", stage.position == Vector2(safe_origin))
	var covers := true
	var clean := true
	for layer in WorldBuilder.LAYERS:
		var sp: Sprite2D = world.get_node(layer.to_pascal_case())
		var img := sp.texture.get_image()
		if img.get_width() != NATIVE.x + WorldBuilder.OVERSCAN.x * 2 or img.get_height() != NATIVE.y + WorldBuilder.OVERSCAN.y * 2:
			covers = false
		if not PixelArt.is_palette_clean(img):
			clean = false
	check("scene layers cover the overscan", covers)
	check("scene layers use palette colours only", clean)
	var sky: Image = world.get_node("Sky").texture.get_image()
	var opaque := true
	for y in range(0, sky.get_height(), 7):
		for x in range(0, sky.get_width(), 7):
			if sky.get_pixel(x, y).a8 != 255:
				opaque = false
	check("sky layer is fully opaque", opaque)


func _test_title() -> void:
	var ids := []
	for b in ui.title_buttons:
		ids.append(b.id)
	check("title buttons in order", ids == ["play", "practice", "daily", "scores", "outlaws", "stats", "sound", "howto"], str(ids))
	var texts := []
	for b in ui.title_buttons.slice(0, 5):
		texts.append(b.text)
	check("title button labels", texts == ["PLAY", "PRACTICE", "DAILY DUEL", "HIGH SCORES", "OUTLAWS"], str(texts))
	var inside := true
	var big_enough := true
	var overlap := false
	for i in ui.title_buttons.size():
		var r := Rect2(ui.title_buttons[i].position, ui.title_buttons[i].size)
		if r.position.x < GameUI.COL_LEFT or r.end.x > GameUI.COL_RIGHT or r.end.y > NATIVE.y:
			inside = false
		if r.size.y < 26 or r.size.x < 26:
			big_enough = false
		for j in range(i + 1, ui.title_buttons.size()):
			if r.intersects(Rect2(ui.title_buttons[j].position, ui.title_buttons[j].size)):
				overlap = true
	check("title buttons inside the 0.06 to 0.94 column", inside)
	check("touch targets at least 26 native px (7 mm at 4x on a 1080 phone)", big_enough)
	check("title buttons do not overlap", not overlap)
	check("PLAY is the large red button", ui.title_buttons[0].style == "red" and ui.title_buttons[0].size.y > ui.title_buttons[1].size.y)
	var tag: Label = ui.screens["title"].get_node("Tagline")
	check("tagline", tag.text == "TEN OUTLAWS. ONE THUMB.")
	var status: Control = ui.screens["title"].get_node("DailyStatus")
	check("daily status line under DAILY DUEL", status.text != "" and status.position.y > ui.title_buttons[2].position.y
		and status.position.y + status.get_line_count() * status.get_theme_font_size("font_size") <= ui.title_buttons[3].position.y + 1)
	var labels_inside := true
	for n in ui.screens["title"].get_children():
		if n is Label and (n.position.x < GameUI.COL_LEFT - 1 or n.position.x + n.size.x > GameUI.COL_RIGHT + 1):
			labels_inside = false
	check("title text wraps inside the column", labels_inside)
	_test_strings()


func _test_strings() -> void:
	var dash := []
	var missing := {}
	for s in GameUI.strings_seen:
		if s.contains(char(0x2014)) or s.contains(char(0x2013)):
			dash.append(s)
		for ch in s:
			for face in ["tiny", "body", "bold"]:
				if ch != " " and ch != "\n" and not GameUI.font(face).has_char(ch.unicode_at(0)):
					missing[face + " '" + ch + "'"] = true
	check("no em-dashes in UI text", dash.is_empty(), str(dash))
	check("every UI character has a glyph in every font", missing.is_empty(), str(missing.keys()))


func _test_roster() -> void:
	check("ten named outlaws", Outlaws.count() == 10)
	var bounties := []
	var draws := []
	for o in Outlaws.NAMED:
		bounties.append(o.bounty)
		draws.append(o.draw)
	check("named bounties", bounties == [25, 50, 75, 100, 150, 200, 300, 500, 600, 375], str(bounties))
	check("named draw times", draws == [650, 560, 500, 450, 410, 380, 350, 320, 330, 340], str(draws))
	check("Bill misses a quarter of the time", Outlaws.named(1).miss == 0.25)
	check("the twins pay $750 for the pair", Outlaws.named(10).bounty * 2 == 750)
	check("duel 11 is kin", Outlaws.named(11).is_empty())


func _deathtest() -> void:
	skip("every tier and variant reaches a grounded pose within 4 s", 5)
	skip("no detached parts except scripted dismemberment", 5)
	check("deathtest scaffold runs", true)


## Taps a point given in native safe-area pixels through the real input path.
func tap(native: Vector2) -> void:
	var p := Vector2(ui_box.position) + (native + Vector2(safe_origin) + Vector2(0.5, 0.5)) * pixel_scale
	for pressed in [true, false]:
		var e := InputEventMouseButton.new()
		e.button_index = MOUSE_BUTTON_LEFT
		e.pressed = pressed
		e.position = p
		e.global_position = p
		get_viewport().push_input(e)
		await get_tree().process_frame


func _centre(b: Control) -> Vector2:
	return (b.position + b.size / 2).floor()


func _flowtest() -> void:
	var screens := {"play": "play", "practice": "practice", "daily": "daily", "scores": "scores",
		"outlaws": "outlaws", "stats": "stats", "howto": "howto"}
	for b in ui.title_buttons:
		if not screens.has(b.id):
			continue
		last_action = ""
		await tap(_centre(b))
		check("tap %s opens its screen" % b.id, last_action == b.id and ui.screens[screens[b.id]].visible, "got '%s'" % last_action)
		var card: Control = ui.screens[screens[b.id]]
		var back: GameUI.PixelButton = null
		for n in card.get_children():
			if n is GameUI.PixelButton:
				back = n
		await tap(_centre(back))
		check("%s returns to the title" % b.id, ui.screens["title"].visible and state == State.TITLE)
	var sound: GameUI.PixelButton = ui.title_buttons.filter(func(b): return b.id == "sound")[0]
	await tap(_centre(sound))
	check("sound toggle turns sound off", pb.get("sound", true) == false and Sfx.muted and sound.icon_rows == GameUI.PixelButton.ICON_SOUND_OFF)
	_load_pb()
	check("sound setting persists", pb.get("sound", true) == false)
	await tap(_centre(sound))
	check("sound toggle turns sound back on", pb.get("sound", false) == true and not Sfx.muted)
	skip("practice run and the straw man", 6)
	skip("pause, resume and exit", 6)
	skip("twins on one cylinder", 4)
	skip("forced near miss", 4)
	skip("the caller's countdown", 4)


func _dailytest() -> void:
	check("daily seed is yyyymmdd", daily_seed({"year": 2026, "month": 9, "day": 25}) == 20260925)
	check("open daily reads one try", daily_status_text() == "ONE TRY TODAY")
	pb["daily"] = {"date": daily_seed(Time.get_date_dict_from_system()), "wins": 3, "bounty": 450}
	check("locked daily line", daily_status_text() == "TODAY: 3 DUELS · $450 · BACK TOMORROW", daily_status_text())
	ui.set_daily_status(daily_status_text())
	await get_tree().process_frame
	var line: Label = ui.screens["title"].get_node("DailyStatus")
	var bottom := line.position.y + line.get_line_count() * line.get_theme_font_size("font_size")
	check("locked line stays on one line", line.get_line_count() == 1, str(line.get_line_count()))
	pb["daily"] = {"date": daily_seed(Time.get_date_dict_from_system()), "wins": 12, "bounty": 12345}
	ui.set_daily_status(daily_status_text())
	await get_tree().process_frame
	check("long locked line still fits on one line", line.get_line_count() == 1, daily_status_text())
	pb["daily"] = {"date": daily_seed(Time.get_date_dict_from_system()), "wins": 3, "bounty": 450}
	check("locked line fits between DAILY DUEL and HIGH SCORES",
		line.position.y >= ui.title_buttons[2].position.y + ui.title_buttons[2].size.y - 4
		and bottom <= ui.title_buttons[3].position.y + 1, "%s %s" % [line.position.y, bottom])
	pb.erase("daily")
	ui.set_daily_status(daily_status_text())
	skip("daily start, kill, death, lock and stats rows", 6)


func _aimtest() -> void:
	skip("hit, graze and miss rates per zone at spreads 0.012, 0.06, 0.12", 4)
	skip("aim through crouch and sidestep poses", 4)
	check("aimtest scaffold runs", true)
