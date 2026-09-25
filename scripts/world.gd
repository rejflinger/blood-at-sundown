class_name WorldBuilder
extends RefCounted
## Builds the layered street scenery from the layers tools/art_scene.py draws: sky, mesas,
## town (street, facades, porches, windmill, horses), foreground props and the player seen
## from behind. Milestone 2 adds parallax, palette swaps per duel and ambience.
## World coordinates: the 195 x 422 safe area spans (0, 0) to (195, 422). Every layer is
## drawn OVERSCAN pixels beyond it on each side, so wider or taller screens show more world
## instead of black bars.

const NATIVE := Vector2i(195, 422)
const OVERSCAN := Vector2i(100, 60)
const HORIZON := 214
const LAYERS := ["sky", "mesas", "town", "fg", "player_back"]


static func build(root: Node2D, _seed: int) -> Node2D:
	var world := Node2D.new()
	world.name = "World"
	root.add_child(world)
	for layer in LAYERS:
		var s := Sprite2D.new()
		s.name = layer.to_pascal_case()
		s.centered = false
		s.texture = load("res://assets/world/%s.png" % layer)
		s.position = Vector2(-OVERSCAN)
		world.add_child(s)
	return world
