# DESIGN.md: Blood at Sundown

This file is the complete specification. Build a complete mobile game called **Blood at Sundown** in **Godot 4.3+ (GDScript, Compatibility renderer)**. Everything is original and generated in code or by Python scripts in `tools/`: pixel sprites, tiles, animation frames, effects, audio and music. Do not use imported character art, 3D models, smooth vector silhouettes or AI image files. Render the game as 2D pixel art with nearest-neighbour scaling. Work in this order: project skeleton, pixel-art pipeline and palette, world, characters, duel loop, deaths and gore, UI and menus, modes and persistence, audio, visual review, headless tests, packaging. After every major step run the headless self-tests described at the end and only continue when they pass. The project must open in the Godot editor and export to Android. See section 0 for the reference images that define the look.

Write the game in English. No em-dashes anywhere in UI text. Keep in-duel prompts to two or three words.

---

## 0. Reference images

`reference/` holds four concept images. They define the **look**: palette, composition, pixel vocabulary, UI framing, character silhouettes. They do **not** define content: where an image and this text disagree on names, menu items, mechanics, HUD values or screens, **this text wins**. The images were generated as concept art at a much higher resolution than the game; do not copy pixels from them, reproduce the style at the native 270 x 584 resolution (section 15).

- `bas_screens.png`: 18 concept screens. Use for: card and panel framing (dark wood panels, cream pixel type, red primary button, arrow ornaments), HUD placement (bounty top left, duel number and cylinder top right, aim ladder HEAD/CHEST/GUT bottom right, prompt word centred), the practice dummy on a post, the HOW TO PLAY card (4), the hit and fall frames (7 and 8), the round-clear and game-over cards (9, 10), the high-score list (11, without the Global/Friends tabs), the stats card (14), the outlaw detail card (15), the pause panel (18). **Not in this version, do not build:** Splash "tap to start" (1, no tap-anywhere), Achievements (12), the Settings page (13), Quit confirm (16), Loading (17), Global/Friends score tabs. They may come later, so keep the menu code open for more buttons. The HUD shows the bounty earned this run in dollars, not a score.
- `bas_title.png`: the title composition. Player from behind lower left in the striped teal poncho with cream fringe, town flanking the street, sun between the mesas, windmill and water tower, lit windows, horses, logo at the top, buttons stacked in the lower half. Button order from section 9 (PLAY, PRACTICE, DAILY DUEL, HIGH SCORES, OUTLAWS, then the icon row).
- `bas_duel.png`: the duel view and its scale. The outlaw stands centred on the street, roughly 125 to 155 native pixels tall, face and hands readable, gun hand at the hip. Player hat and poncho in the lower left, a crate lower right, DRAW word centred under the outlaw, aim ladder lower right, cylinder and duel number top right. Match the dusk banding of the sky and the warm rim light.
- `bas_characters.png`: **the cast.** The player figure and the eight named outlaws are built to match these models and names: silhouette, clothing, colours, hair, face, pose. Section 8 assigns their numbers, quirks and bounties. Full-body sprites, adult proportions, strong silhouettes, faces with visible eyes and mouth, revolvers as readable silhouettes. One change: Silas Crow carries a revolver, not a rifle; nobody in the game carries a rifle.

---

## 1. Concept

A one-thumb quick-draw duel game in the spirit of Gunblood, played in portrait on a phone. The player is seen from behind at the near end of a Western main street at dusk; an outlaw walks in and faces them. The player **holds** the screen to steady their hand, **waits** for the word DRAW, **releases** to fire, and can **slide** the thumb up before releasing to raise the aim from gut to chest to head. Reflexes decide who fires first, aim decides whether the shot kills. Very gory: blood, exit wounds, dismemberment, exploding heads on the fastest draws, physics ragdolls that fall differently depending on how they were hit. Endless: duel until you die.

Desktop controls for testing: hold and release Space, aim with Up/Down or W/S.

---

## 2. Project setup

- Native resolution 270 x 584 for world, UI and touch layout (section 15). Draw the world into a `SubViewport` of that size (plus overscan) with transparent background disabled and nearest-neighbour texture filtering, and scale it by a whole number to the screen: 4x on 1080-wide phones, 5x on 1440-wide, 2x on 720-wide. Where the screen shape differs, extend the background (overscan) without filtering. No interpolation, mipmaps, antialiasing, blur, glow or subpixel camera positions. Snap sprite positions and camera offsets to integer source pixels.
- Godot 4.3+ (GDScript, Compatibility renderer). One scene `scenes/Main.tscn` with a root Node2D running `scripts/main.gd`. World, actors and effects are Node2D scenes/nodes; HUD is a CanvasLayer outside the world SubViewport. Use 2D collision and joint nodes for physical bodies.
- Scripts: `main.gd` (game loop and states), `world.gd` (`WorldBuilder`), `character.gd` (`Outlaw` pixel sprite rig and 2D ragdoll), `player_figure.gd` (player silhouette from behind), `gore.gd` (blood, splats, gibs, dust), `ui.gd` (`GameUI`), `sfx.gd`, `outlaws.gd`, `camera_rig.gd`, `ambience.gd`, `pixel_art.gd` (palette, raster tools, sprite generation and animation).
- Shaders only where useful for hard-edged palette ramps and palette cycling. No 3D shaders or screen post-processing. A shader must preserve exact pixel blocks and palette colours.
- Bundle pixel-friendly display and body fonts with suitable licences, or generate bitmap glyph atlases in `tools/`. Render HUD type crisp at integer sizes; wanted cards can use a larger readable pixel font.
- Python generators in `tools/`: `gen_audio.py`, `gen_lofi.py`, `gen_pixel_art.py` (sprite atlases and tiles). Use PIL and numpy. Include the generators and generated assets in the zip.

---

## 3. Art style

**Hand-drawn-inspired pixel art Western.** The whole game should share the same illustrated pixel vocabulary as the reference images in `reference/` (section 0), above all `bas_characters.png` and `bas_duel.png`: readable silhouettes, confident clusters of pixels, a limited warm dusk palette, selective outlines, chunky shadows and highlights. The scene must look intentionally drawn at its native resolution, not like filtered 3D or a downscaled render.

- **Pixel discipline:** 270 x 584 native world resolution, nearest-neighbour display, source-aligned positions and hard edges. No smooth contours, gradients, anti-aliasing, film grain, chromatic aberration, bloom, realistic material maps or tiny decorative noise. Every silhouette and shadow should consist of deliberate pixel clusters. Keep one consistent apparent pixel size across characters, scenery and effects.
- **Palette:** a master palette of about 56 to 64 colours, about 40 to 48 in any one scene. Deep plum and charcoal for outlines/shadows, dusty tan and ochre for ground and skin lights, burnt orange and muted rose at the horizon, desaturated teal for cool shadows, dark wine and bright red for blood. Each character gets one small accent colour. Player poncho: deep teal with mustard and cream stripe clusters. Use three to five shades per material; keep faces and hands legible against the sky.
- **Lighting:** draw a low sunset behind the outlaw as distinct colour bands and hard-edged highlight clusters. Add warm rim pixels on hat, shoulders and boots and a cool front fill for readable facial features. Shade per sprite, with no smooth lighting or normal maps. Across the eight named duels, palette-swap sky, ground and rim-light ramps from gold to deep red (`sun_t = duel / 7`).
- **Characters:** full-body, compact but anatomically continuous pixel sprites with recognizable hats, clothing and faces. Adult proportions with modest stylization, no oversized toy heads. Each named outlaw must be identifiable in silhouette and colour at gameplay scale. Use strong poses, visible eyes, nose and mouth clusters, asymmetric details and expressive hands. Draw the weapon as a readable revolver silhouette; Father Elias's cross and Briggs's eyepatch must read clearly. Do not make all characters recolours of one base sprite.
- **Animation:** hand-authored or procedurally assembled pixel frames and rigid sprite parts, with limited but expressive key poses. Idle breathing, hat/coat sway, steps, hand twitch, draw, recoil, wound, stumble and unique death poses must read without smooth deformation. Quantize motion to source pixels. Keep frame pacing intentional (typically 8 to 12 distinct poses per second) while game timing and input sampling stay precise.
- **Depth:** a layered 2D stage with foreground player silhouette, middle-ground duel line and parallax town, mesas and sky. Use size, overlap and shadow pixels to suggest depth. Dust and haze are sparse, pixel-aligned, dithered clusters rather than translucent fog.
- **Visual review:** capture the title, walk-in, active duel, each outlaw, each death tier and result card at native resolution and nearest-neighbour enlarged size. Check readability on a phone and consistent pixel scale before packaging.

---

## 4. World

`WorldBuilder.build(root, seed)` creates layered Node2D scenery and a ground collision strip. Keep world coordinates in 2D screen pixels; map aim heights to sprite-space anatomy rather than 3D metres.

- Main street: hand-built/generated pixel tiles with two wagon ruts, hoof prints, boot scuffs and clusters of pebbles. Sparse repeated patterns with intentional tile variation. Foreground hitching rail on the left and trough on the right provide 2D collision for bodies. Keep the middle aim line unobstructed.
- Horizon layers: nine mesa silhouettes on fixed bearings with simple palette ramps; cacti, water tower, telegraph poles and a dead tree. Town facades flank the street: saloon, stores, hotel, barn, sheriff, bank, church and shacks. Silhouette-first architecture with chunky plank, door and window details; lit windows are warm solid pixel clusters, never blurred halos. Wagon, crates, barrels, sacks, troughs and rails use the same palette and scale.
- Animate saloon doors, hotel curtain and hanging sign with snapped pixel poses. Sparse dust puffs, drifting dust clusters, a rolling tumbleweed and distant birds provide movement without cluttering the duel.
- Camera: fixed portrait composition with the outlaw centred and large enough to read their face and wound zone. Player seen from behind in the lower left, with hat, striped teal poncho, scarf, right arm and revolver. Use limited camera shake in integer pixels on shots and impacts, a small tilt/drop when the player is hit, and a short low-angle-looking walk-in composition built from alternate 2D framing. **No zoom on shots.**
- The outlaw's gut, chest and head centres, collision silhouettes and reticle anchors are defined in sprite-space coordinates and transformed by actor position, pose and scale. Keep these points aligned through crouches, sidesteps and death animations.

---

## 5. Characters (pixel sprite rigs)

`Outlaw` extends Node2D and is built from a style dictionary and distinct generated sprite layers/frames. Use a stable visual scale: a standing outlaw should occupy roughly 125 to 155 native pixels from boots to hat, with readable head, chest and gut zones. The actor faces the player. Mirror left/right poses only when appropriate; keep the revolver on the character's right hip.

- Rig parts: pelvis/hips, torso, head, upper/lower arms, hands, thighs/shins, boots, hat and optional coat tails/hair. Parts overlap through deliberate silhouette pixels to avoid visible gaps; pivots rotate only to snapped poses. Pixel assets must preserve consistent outlines, shade ramps and apparent pixel size.
- Face library: head and jaw shapes, brow, eyes, nose, mouth, scars, eyepatch, freckles, stubble, moustache, beard, glasses, gold tooth, earrings, hair flower. Eyes and expressions must be legible in the duel view. Hair: short, long, braids, bun, tonsure, bald. Hats: bowler, stetson, boss wide-brim, top hat, veil, hood, none. A flying hat becomes an independently animated sprite.
- Clothes: vest and shirt, coat/duster, blouse and neckerchief, corset and skirt, cassock, blanket poncho, fur-collared coat, bandolier, belt and buckle. Distinct silhouettes and a few purposeful highlight clusters distinguish fabrics; avoid dense patterns. Extra props include a cross, a rope belt and a bandolier.
- Idle: two to four breathing/weight-shift poses, head turn and blink frames, gun-hand twitch near the holster. Walk-in: timed stepping frames, snapped boot plants, prints and dust puffs. Draw: a clear hand-to-holster-to-raised-revolver sequence that reaches the fire pose exactly at the outlaw's draw time.
- Death physics: keep a pose-driven pixel character rig for reactions, then transition to 2D RigidBody2D body parts with PinJoint2D or DampedSpringJoint2D constraints and tuned angular limits/forces. Preserve connected silhouettes with sprite overlap. Use deterministic impulses by hit zone and death variant; record impacts for dust and camera kick. After settling, one to three short twitch frames. If the chosen 2D joints prove unstable, use a deterministic pose-and-collision fall controller that visibly lands on the ground or nearby prop. Death results must never look like limbs drifting apart.
- Training dummy: burlap sack body on a wooden post, button eyes, stitched mouth, straw tuft and painted chest target. It never fires or bleeds; hits produce straw clusters.

---

## 6. Duel loop and states

States: title, intro, ready, standoff, draw, falsestart, firing, engage, wounded, draw2, kill, result, playerhit, gameover, stats, paused.

1. **intro**: the walk-in cinematic (1.35 s), then the camera cuts back and the **wanted card** shows: DEAD OR ALIVE stamp, name, crime line, quirk warning, quote (kin), reward, rows "Draws in", "Survives (gut 50, chest 25, head 0 percent, plus grit)", "Known for". Auto-continues after 3.8 s or on tap.
2. **ready**: HOLD ring at the bottom. Press starts the standoff.
3. **standoff**: "STEADY, release on draw". A heartbeat that accelerates (interval 0.95 s shrinking by 10 percent per beat, floor 0.42). Wait `randf_range(1.0, 3.4 + min(1.6, duel * 0.12))` seconds. Releasing before 0.3 s returns to ready; releasing later is a **false start**: the outlaw draws in 0.42 s and fires. Feints (see quirks) may happen here, never in the last 0.5 s. The reticle hovers at the gut with a small twitch. Music drops, wind fades, a low drone rises.
4. **draw**: DRAW! flashes, drum hit, haptic. Reaction timer starts on the frame DRAW is presented. The outlaw's arm rises over his `draw` milliseconds and he fires at 1.0 unless dead. Player: release fires (state firing, a 55 ms arm animation, then the shot resolves).
5. **Aiming**: `aim_h` is a world height on the outlaw's axis, starting at the gut. Sliding the thumb up moves it: sensitivity `(head_y - gut_y) / (2.1 * thr)` where `thr = max(30 px, 4.5 percent of screen height)`. Aim persists between shots. Spread shrinks as the hand settles: `lerp(0.12, 0.012, smoothstep(settle / 0.18))` in normalized actor-height units, reset to 0 on every move. Recoil adds 0.18 actor-height units upward per shot and decays `exp(-9 t)`. The reticle follows a sidestepping outlaw's x with a lag (rate 5.5/s).
6. **Hit resolution** (`_resolve_aim`): sample a point at height `aim_h + recoil + triangular(spread)` and sideways `triangular(spread * 0.35)` in normalized actor coordinates; compare to pose-transformed gut, chest and head centres on the sprite; nearest zone wins; tune hit and graze radii in source pixels against the visible silhouette; else miss. Show MISS, GRAZE, CLANG as floating words. A reticle on screen shows the current zone colour, a settle ring for spread, and the projected point.
7. **Survival**: gut 50 percent, chest 25 percent, head 0, plus the outlaw's `grit` (kin up to +20) and +40 on the chest for armour. A survivor is **wounded** (hunched pose, hands to the wound, wound counted, second wound never survives), and returns fire after `(0.75 + rand 0.45) * return_k` seconds; heavy-iron outlaws take 1.5x. While he is standing the player keeps firing (state wounded, follow-up shots gated at 220 ms). Player survival on his hits: same table, halved against heavy iron. A wounded player gets "AGAIN!" and must fire again before his second shot (`draw * 1.6` ms). A second hit kills the player. Zone of his shot: 45 percent gut, 40 chest, 15 head.
8. **Enemy misses**: each outlaw has a `miss` chance (Bill Hawkins 0.25, most named 0.12, kin 0.05, follow-ups 0.04). A miss whips past the ear: tracer past the camera, whip crack, camera flinch, dirt behind the player, "MISSED YOU", and he cocks again after about 0.9 s.
9. **Six rounds** per duel, shown as a revolver cylinder in the corner. After a kill the player may tap to fire into the corpse (impulses, extra blood, 12 percent chance a head shot bursts the skull) until empty. Firing into the corpse **forfeits the one-shot bonus**. Empty: "Click".
10. **Bounty**: all money is US dollars in 1870s amounts, whole dollars, no cents, formatted "$250". `earned = round5(bounty * zone_mult * (1 + clamp((draw - reaction) / draw, 0, 1)))` with tier multipliers EXECUTION 2.5, DEADEYE 2.0, GUNSLINGER 1.4, BUTCHER 1.2, GUTSHOT 1.0. A whole run should read like a real bounty ledger: a first kill pays tens of dollars, a boss a few hundred, a long run adds up to a few thousand. One shot, one kill bonus: +50 percent, settled on the result card only if exactly one round was fired in the duel.
11. **kill**: slow motion (time scale 0.12) held 0.9 s then eased over 0.8 s on kills, 0.3 s on wounds; a second short hold as the body lands on Deadeye and Execution kills. Camera shake only, no zoom. Result card waits for the body to land (rest, or death_t > 2.4 s, or 4.6 s cap): tier **stamp** slams onto the card (rotated, scale 2.6 to 1, stamp sound, haptic), reaction ms, description line, rows (he drew in, aim zone and multiplier, rounds fired and misses, bounty, one-shot bonus), new personal best badge, tap to continue.
12. **playerhit**: red flash, lens blood, camera roll and drop, 2 s, then the **death card** (Buried at sundown, why you died, duels won, bounty, average draw, ladder rank badge) and back to the title.
13. A dying outlaw's gun may go off (55 percent when he still holds it and the kill was slower than 45 percent of his draw): tracer, flash, dust where it hits the ground, and if it points at the player it **grazes** (flash, small lens splatter, kick), never wounds, never kills. A dead outlaw can never fire a lethal round through any path.

---

## 7. Deaths and gore

Death tiers by zone and reaction: head under 165 ms has a 20 percent chance of **EXECUTION** (head bursts into pixel skull, brain and eye fragments, hat flies, neck stump gushes); other head shots are **DEADEYE** (head snaps back, exit spray and wound clusters); chest is **GUNSLINGER**; gut on an already wounded outlaw has 15 percent **BUTCHER** (gun arm detaches as connected sprite parts, stump gush, shout), else **GUTSHOT**. Head explosions are reserved for this fastest-draw condition.

Start with recognizable hit poses over 0 to 0.3 s, then pose-driven stumble and 2D collision-aware fall. Chest hits arch back, gut hits fold over the wound, head hits snap the neck. Variants: GUNSLINGER stumbles back then pitches forward, crosses sideways then topples, or drops to knees then face first; GUTSHOT shuffles then drops sideways, sinks to knees then face plants, or falls backward; DEADEYE topples back or drops straight down with occasional spin. Change momentum and timing by reaction speed. Feet and props must ground the motion; avoid floaty or identical falls. Add postmortem twitches, hat and gun drops, a spreading dark pool and an occasional gurgle.

All effects use palette-limited pixel sprites or direct raster drawing at the native world resolution. Blood sprays are branching arcs of discrete red clusters; droplets follow 2D gravity and become irregular 2 to 6 pixel splats when they hit scenery. Use a handful of distinctive fragment shapes for bone, brain, tooth, eye and skull. Use hard-edged dust and smoke clusters with sparse dither transitions. Cap particle counts for Android and keep foreground action readable. No soft particles, alpha-blended mist, smooth gradient pools or full-screen blur.

**Blood on bodies:** overlay authored/generated wound decals and dark-red cluster masks tied to torso, head, arms and legs. Entry marks appear at the exact hit point; nearby pixels spread into a stain over about 5 s and a few stepped drips follow gravity as the body changes pose. Spray can land on other body parts and the player's poncho. Shift older blood to darker palette entries over about 30 s. Player poncho stains persist for the run and clear on a new run. Keep wounds legible at the native pixel scale.

---

## 8. Roster

Ten named outlaws, then endless generated kin. Fields: name, short, crime, bounty, draw (ms), quirk, feints, miss, style. Numbers 1 to 8 are the cast in `reference/bas_characters.png`; build them to match those models. 9 and 10 are not in the image and are designed from the text.

1. Bill Hawkins, $25, 650 ms, miss 0.25. Brown duster over a white shirt, red neckerchief, stetson, short dark beard. Crime line: "Ranch hand turned outlaw. Quick on the draw, quicker to anger." Tutorial-clean, no quirk.
2. Rosa Valdez, $50, 560 ms. Long black hair with a red flower, gold earrings, white blouse, brown corset, red skirt with a slit, boots. 1 feint.
3. Father Elias, $75, 500 ms. Bald, grey beard, black cassock, rope belt, wooden cross on a chain. Quirk **ducker**: crouches into the draw so head shots go over him.
4. Lucy Graves, $100, 450 ms. Wide flat-brimmed hat, long red hair, white blouse, dark corset, jeans, freckles. Quirk **sidestep**: steps off the line as the hand drops; the reticle lags behind her.
5. Tombstone Kid, $150, 410 ms, miss 0.12. Young, clean-shaven, grin, small black hat, dark vest over a white shirt, red string tie, sleeves rolled. Quirk **flincher**: the player's first shot of the duel, hit or miss, makes him jump and stalls his draw by 380 ms.
6. Black Annie, $200, 380 ms. Wide black hat, long dark curls, black coat over a cream blouse, bandolier, dark trousers. Quirk **twitchy**: two feints.
7. Silas Crow, $300, 350 ms. Long black hair, blue blanket poncho with fringe, bandolier, buckskin trousers, gaunt face. Quirk **armour**: chest shots ring off an iron plate under the poncho (+40 survival, CLANG, sparks, no blood). Revolver, not the rifle shown in the image.
8. One-Eyed Briggs, $500, 320 ms, gang boss, tall 1.06. Eyepatch, huge black beard, red coat with a fur collar, bandolier, bald. Quirk **heavy iron**: his hits put you down twice as often; slow to bring the gun back up when wounded. 1 feint.
9. Hollis Crane, bounty hunter, $600, 330 ms, miss 0.06. Long grey coat, flat hat, moustache. Quirk **caller**: no random standoff; he counts THREE, TWO, ONE (0.55, 1.25, 1.95 s) and DRAW comes at 2.75 s, no feints.
10. The Mercer twins, $750 for the pair, 340 ms. Identical young men, grey vests, bowler hats. Quirk **twin**: after Cass goes down, Joss walks in on the same cylinder (bullets carry over, draw 40 ms faster, one feint), same duel number.

Feints: a jerk of the gun hand and dropped shoulder with a click, scheduled at random times in the standoff but never in the last 0.5 s. Releasing on a feint is a false start.

Kin (duel 11 onward): base body of one of the eight cast outlaws with a generated name (first name by sex, surname, epithet 60 percent), random crime line and a quote on the poster, random skin, hair, eyes, hair style, hat, facial hair or none, random extras (eyepatch, scar, glasses, gold tooth, freckles at 18 percent each), height 0.92 to 1.1, a random quirk 75 percent of the time (any except twin), 0 to 2 feints, miss 0.05. Difficulty by tier t = duel - 10: draw `max(200, 320 - 12 t)`, bounty `400 + 50 t`, grit `min(0.2, 0.05 t)`, return fire factor `max(0.55, 1 - 0.05 t)`. Everything seeded from the duel number so the same duel always produces the same kin.

---

## 9. UI and menus

Use a consistent pixel-art UI: crisp bitmap fonts, pixel-bordered wanted posters, chunky stamps and solid-colour flashes at integer coordinates. Preserve generous touch targets and readable text on a phone. CanvasLayer with: red and white flash rects, HUD (bounty earned this run top left, duel number and name top right, pause button under it), the revolver cylinder with rotating chambers bottom left, HOLD ring (text HOLD / STEADY, sub line), DRAW label (scales in), prompt box (big word plus small line, warn colour), reticle (zone-coloured crosshair with spread ring and MISS/GRAZE/CLANG floating words), pixel-cluster lens blood splats (stepped drips), cards (paper panel with stamp, eyebrow, title, big number, sub, rows with rules, badge, blinking tap line, and the big rotated tier stamp with slam animation), title screen, pause panel, sound toggle bottom right.

Title: game name as a hand-drawn pixel logo (red BLOOD, cream SUNDOWN, dark outline, blood drips, see `reference/bas_title.png`; a bitmap font is acceptable, no smooth vector font), tagline "TEN OUTLAWS. ONE THUMB.", then buttons in this order: **PLAY** (large, red, primary), **PRACTICE**, **DAILY DUEL** (with a line under it showing today's status), **HIGH SCORES**, **OUTLAWS**, and an icon row at the bottom with **STATS** and **HOW TO PLAY** plus the sound toggle. Same wood-panel buttons as `reference/bas_title.png`. Everything word-wrapped so the column never grows past its anchors (0.06 to 0.94 of the width). No splash screen, no tap-anywhere: the title is the first screen.

Pause: button "II" during a run and the Android back button. Allowed only in intro, ready, standoff, kill, result, playerhit (never between DRAW and the shots). `get_tree().paused`, UI and audio on process mode Always, on resume shift every millisecond timestamp by the paused duration. Panel: PAUSED, CONTINUE, RESTART RUN (hidden in the daily), EXIT TO MENU (in the daily, exiting counts as the day's attempt).

Cards content as in section 6. **High scores**: the local ladder, top ten, rank, name (the player enters a three-letter tag on their first ladder entry), duels won and bounty, the current run highlighted, like screen 11 without the Global/Friends tabs. **Outlaws**: a list of the ten named outlaws, each opening a detail card like screen 15 (portrait sprite, name, crime line, "Duel N", bounty, "best N ms" if killed, "still breathing" if met, "? ? ?" and a silhouette if never met), plus a kin line. **Stats**: duels fought, won/lost, headshot rate, fastest draw, total bounty, a reaction-time histogram (under 150, 150 to 199, 200 to 249, 250 to 299, 300 to 399, 400 and up) drawn with block characters. **How to play**: the three-step card from screen 4 (HOLD, AIM, DRAW) with a GOT IT button.

---

## 10. Modes and persistence

- **Run** (PLAY): endless, one life, the named ten then kin. Ladder entry on death: duels won, then bounty; top ten in `user://ladder.cfg` (JSON).
- **Daily duel**: seed from the date (yyyymmdd). The cast's order (first eight) is shuffled by the seed and draw times ramp by slot (650 - 47 n); the two after them are fixed; kin are reseeded. One attempt per day, stored with wins and bounty; the button locks with "TODAY: N DUELS · $X · BACK TOMORROW"; a 30-entry history.
- **Practice** (PRACTICE): the straw man. Hints above the hold ring for each step (hold, steady, release, slide to aim, fire again). Two knockdowns end it with a "You'll do" card. Running dry reloads the round. Does not touch stats.
- Persistence in `user://pb.cfg`: fastest draw, best bounty, stats (duels, kills, headshots, deaths, histogram, best ms per outlaw, outlaws met), daily state and log.

---

## 11. Audio and haptics

All WAVs generated by `tools/gen_audio.py` (numpy): shot (noise burst, sub thump, crack, tail), splat, pop (head), thud, heartbeat, sting, click (hammer), wind loop, drone loop (D2 plus A2 strings), drum (DRAW hit), stamp, three tier stings (high tremolo and bell for head kills, brass stab for chest and arm, low ominous for gut), whip crack, thunder, voices via glottal pulse and formant filters (male and female grunt, male and female shout, cough, gurgle).

Music `tools/gen_lofi.py`: a 16-bar lofi western beat, 78 bpm, D minor (Dm7, Gm7, Bbmaj7, A7), swung boom-bap drums, electric piano, round bass, plucked guitar melody with slide-in grace notes, sidechain on the kick, tape wow, lowpass 5.2 kHz, vinyl hiss and crackle, seamless loop. It never stops: -9 dB in the menu, -14 under the duel, -26 during Steady, back to -14 on DRAW.

Reactive layer: Steady fades the wind out and the drone in; DRAW cuts the drone and plays the drum; each kill plays its tier sting 0.4 s after the shot; the stamp thumps when it lands. Voices: grunt on any hit, cough 0.4 s after gut shots, shout when the arm comes off, gurgle from a body that has just gone still; pitch by sex and height. Haptics (Android `Input.vibrate_handheld`): DRAW 45 ms, your shot 70, being wounded 110, being killed 160, thuds 20 to 70 by impact, stamp 40, false start 60.

---

## 12. Testing and tooling

Command-line modes on `main.gd` (all headless-safe, print `[autotest]` lines, exit 0 or 1):
- `--autotest`: five duels covering head Execution with corpse shots and bonus forfeit, a wounded exchange on both sides, a false-start death and the death card and ladder, a deep kin duel, and a miss then graze then settled headshot. Samples fallen 2D body positions and checks that parts stay connected, remain near the duel area and settle on ground or props.
- `--deathtest`: every tier and variant; all bodies must reach a grounded fallen pose within 4 s, with no detached parts except scripted dismemberment.
- `--aimtest`: hit, graze and miss percentages per zone at normalized spreads 0.012, 0.06, 0.12 and through crouch/sidestep poses.
- `--dailytest`: daily start, kill, death, lock, stats rows.
- `--flowtest`: practice, pause and resume and exit, twins, forced near miss, the caller's countdown.
- `--shot --when=title|ready|intro|kill|corpse|corpsehead|result --round=N [--close] [--practice] --out=path.png`: renders a frame headlessly where supported, otherwise under Xvfb with the Compatibility renderer. Save both native 270 x 584 and exact 2x nearest-neighbour frames for visual review.
- Debug flags for the muscles: `--joint-stiffness=`, `--joint-damping=`, `--gravity=`, `--no-joints`, `--no-impulse`. Test forcing: `force_spread`, `force_tier_roll`, `force_survive`, `force_zone`.
Always run `--import` headless after deleting `.godot` before tests, because class names are cached there.

Packaging: delete `.godot` and all `*.import` files, zip the project folder. Export preset for Android (portrait, immersive).

---

## 13. Tone and copy

Western pulp, dry, short. Crime lines like "Horse thief. Drunk before noon, dead by dusk." Result lines like "Headshot. Clean through the skull." Death card: "Buried at sundown". No jokes at the player's expense beyond "You twitched". Tier names in caps: EXECUTION, DEADEYE, BUTCHER, GUNSLINGER, GUTSHOT. In-duel prompts: "Missed · 4 left", "Grazed · 3 left", "Still up · 2 left", "Chest shot · still up · fire again · 1 left", "5 left · tap to keep firing · stop here for the bonus", "Click · empty".

Build it in that order, test after each step, and commit after each section with a one-line summary of the player-facing change. The owner tests every milestone on a phone in the Godot 4.7 editor and reports back.

---

## 14. Owner clarifications (2026-09-25)

Answers to open questions, numbered as asked. They are part of the spec and win over
anything above that they contradict.

1. The revolver cylinder sits top right next to the duel number.
2. The HEAD/CHEST/GUT aim ladder sits bottom right. The sound toggle appears only on the title and the pause panel.
3. EXECUTION (head under 165 ms, 20 percent) is the live kill condition. The 12 percent skull burst applies only to shots into a corpse's head and is separate.
4. Fonts are bitmap fonts generated in `tools/gen_fonts.py`.
5. The big prompt word is two or three words; the small line under it may be a short sentence. The section 13 examples are allowed as written.
6. `sun_t = clamp((duel - 1) / 7, 0, 1)`: gold at duel 1, deep red from duel 8 on.
7. The death card has RETRY and MAIN MENU buttons like screen 10. If the run makes the top ten, a three-letter tag picker (tap letters, no keyboard) appears on the death card before the buttons become active.
8. A rail and a trough stand at mid street near the outlaw's line to catch bodies; the crate stays in the foreground lower right.
9. `draw2` is the player's AGAIN window, `engage` is the exchange after a wound, `stats` is a menu screen.
10. The scripted pose-and-collision fall is the main death path. Rigid bodies only for the arm, hat, gun and gibs. Depth by size: a body falling backward shrinks slightly and slides up the street, one falling forward grows toward the camera. Most variants end lying across the street as a sideways silhouette.
11. False start: the player cannot fire in the 0.42 s window. His shot uses his normal miss chance; if he misses, DRAW comes at once and the duel continues normally. Releasing during the caller's THREE, TWO, ONE is a false start.
12. CLANG is not a wound. Silas's chest survival is 65 percent; when the plate fails it is a normal bloody GUNSLINGER kill. Head and gut are unaffected.
13. Heavy iron halves the player's survival.
14. The 0.04 follow-up miss chance applies to his return fire when wounded and to his re-cock after a miss.
15. The player's `draw * 1.6` ms window starts when AGAIN appears, which is the moment his hit lands.
16. Named outlaws have grit 0 and return_k 1; an unlisted miss chance is 0.12. Heavy iron keeps the 1.5x return fire delay.
17. Mercer twins: $375 each, paid separately. One-shot bonus for Cass if exactly one round was fired before he fell, for Joss if exactly one round after. Joss gets a short wanted card ("The other Mercer"), his own HOLD phase and his own result card. The duel counter does not advance between them.
18. Daily: outlaws keep their own bounties. The daily has its own log and does not go on the main ladder. Kills, headshots and reaction times count in stats.
19. Tapping II or the back button during the standoff is never a false start; on resume the standoff restarts from ready.
20. Kin may roll the caller quirk.
21. Superseded by section 15: master palette of about 56 to 64 colours, about 40 to 48 per scene. Sky and rim ramps swap entries within it; accent colours come from the palette.
22. No skull progress bar in the HUD.
23. `project.godot` is marked 4.3 compatible; test with the newest stable. The owner plays in Godot 4.7.2 on Android.

---

## 15. Revised visual target (2026-09-25)

Set by the owner after the first title pass; wins over any older number above.

| | |
|---|---|
| Native world | 270 x 584 |
| Display | integer nearest-neighbour scaling (4x on 1080-wide phones) |
| Target outlaw height | 125 to 155 px |
| Master palette | about 56 to 64 colours (the game uses 64: 48 fixed, 16 swapped per duel) |
| Typical scene | about 40 to 48 colours |
| Material shading | 3 to 5 shades |
| Animation | 60 Hz gameplay, 8 to 12 authored poses per second |
| Lighting | hard pixel clusters, palette ramps, dithered transitions allowed |
| Atmosphere | sparse pixel-aligned haze allowed |
| Lamp and sun glow | dithered or stepped pixels only |
| Filtering | nearest neighbour |
| Anti-aliasing, bloom, blur, smooth gradients, subpixel movement | off |
