class_name Outlaws
extends RefCounted
## The roster as data. Numbers are from DESIGN.md section 8 and the owner's clarifications.
## Quirk logic lives in main.gd; the look of each body is built in character.gd (milestone 3).

const QUIRK_NONE := ""
const QUIRK_DUCKER := "ducker"
const QUIRK_SIDESTEP := "sidestep"
const QUIRK_FLINCHER := "flincher"
const QUIRK_TWITCHY := "twitchy"
const QUIRK_ARMOUR := "armour"
const QUIRK_HEAVY := "heavy iron"
const QUIRK_CALLER := "caller"
const QUIRK_TWIN := "twin"

const DEFAULT_MISS := 0.12
const KIN_MISS := 0.05
const FOLLOWUP_MISS := 0.04

# grit 0 and return_k 1 for every named outlaw; the default miss chance is 0.12.
const NAMED := [
	{
		"id": "hawkins", "name": "Bill Hawkins", "short": "Hawkins", "sex": "m", "tall": 1.0,
		"bounty": 25, "draw": 650, "quirk": QUIRK_NONE, "feints": 0, "miss": 0.25,
		"crime": "Ranch hand turned outlaw. Quick on the draw, quicker to anger.",
		"known": "A clean draw. No tricks.",
	},
	{
		"id": "rosa", "name": "Rosa Valdez", "short": "Rosa", "sex": "f", "tall": 0.96,
		"bounty": 50, "draw": 560, "quirk": QUIRK_NONE, "feints": 1, "miss": DEFAULT_MISS,
		"crime": "Robbed the Tucson stage. Smiled at every passenger.",
		"known": "One feint. Watch the hand, not the smile.",
	},
	{
		"id": "elias", "name": "Father Elias", "short": "Elias", "sex": "m", "tall": 1.0,
		"bounty": 75, "draw": 500, "quirk": QUIRK_DUCKER, "feints": 0, "miss": DEFAULT_MISS,
		"crime": "Preached on Sunday. Buried his flock on Monday.",
		"known": "Ducks into the draw. Head shots go high.",
	},
	{
		"id": "lucy", "name": "Lucy Graves", "short": "Lucy", "sex": "f", "tall": 0.97,
		"bounty": 100, "draw": 450, "quirk": QUIRK_SIDESTEP, "feints": 0, "miss": DEFAULT_MISS,
		"crime": "Shot a marshal over a hand of cards. Kept the pot.",
		"known": "Steps off the line as she draws.",
	},
	{
		"id": "kid", "name": "Tombstone Kid", "short": "The Kid", "sex": "m", "tall": 0.95,
		"bounty": 150, "draw": 410, "quirk": QUIRK_FLINCHER, "feints": 0, "miss": 0.12,
		"crime": "Nineteen years old. Eleven notches on the grip.",
		"known": "Jumps at the first shot, hit or miss.",
	},
	{
		"id": "annie", "name": "Black Annie", "short": "Annie", "sex": "f", "tall": 0.98,
		"bounty": 200, "draw": 380, "quirk": QUIRK_TWITCHY, "feints": 2, "miss": DEFAULT_MISS,
		"crime": "Widowed four times. Every husband died of lead.",
		"known": "Twitchy. Two feints.",
	},
	{
		"id": "silas", "name": "Silas Crow", "short": "Silas", "sex": "m", "tall": 1.02,
		"bounty": 300, "draw": 350, "quirk": QUIRK_ARMOUR, "feints": 0, "miss": DEFAULT_MISS,
		"crime": "Robbed the Butterfield line twice. Nobody rode away.",
		"known": "Iron plate under the poncho. Chest shots ring off.",
	},
	{
		"id": "briggs", "name": "One-Eyed Briggs", "short": "Briggs", "sex": "m", "tall": 1.06,
		"bounty": 500, "draw": 320, "quirk": QUIRK_HEAVY, "feints": 1, "miss": DEFAULT_MISS,
		"boss": true,
		"crime": "Runs the Sundown gang. Owns the sheriff and the undertaker.",
		"known": "Heavy iron. His hits put you down. One feint.",
	},
	{
		"id": "crane", "name": "Hollis Crane", "short": "Crane", "sex": "m", "tall": 1.03,
		"bounty": 600, "draw": 330, "quirk": QUIRK_CALLER, "feints": 0, "miss": 0.06,
		"crime": "Bounty hunter. Wants the price on your head.",
		"known": "Counts you down. Draws on the last word.",
	},
	{
		"id": "mercer", "name": "The Mercer twins", "short": "Mercer", "sex": "m", "tall": 1.0,
		"bounty": 375, "draw": 340, "quirk": QUIRK_TWIN, "feints": 0, "miss": DEFAULT_MISS,
		"twin_names": ["Cass Mercer", "Joss Mercer"], "twin_draw_bonus": 40, "twin_feints": 1,
		"crime": "Two brothers, one grudge. $750 for the pair.",
		"known": "Drop one and the other walks in.",
	},
]


static func count() -> int:
	return NAMED.size()


## Named outlaw for duel n (1-based), or an empty dictionary for kin duels.
static func named(duel: int) -> Dictionary:
	if duel >= 1 and duel <= NAMED.size():
		return NAMED[duel - 1]
	return {}
