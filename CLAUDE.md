# Blood at Sundown, working rules for Claude Code

Read DESIGN.md first: it is the complete spec (mechanics, numbers, roster, look); its section 14
holds the owner's clarifications and wins over anything above it. Then look at
every image in reference/. The images define the look and the cast, DESIGN.md defines everything else; where they
disagree, DESIGN.md wins.

## Stack
- Godot 4.3+ project, tested by the owner in Godot 4.7 on Android. GDScript, Compatibility
  renderer, 2D pixel art at a native 270 x 584 resolution scaled by a whole number, nearest-
  neighbour (DESIGN.md section 15).
- Everything is generated: sprites, tiles, fonts if needed, audio and music come from code or
  from the Python scripts in tools/ (PIL, numpy). Never add hand-made or downloaded binary
  assets. Generated PNG and WAV files are committed, but regenerate them with the script rather
  than editing them.
- Godot binary: set GODOT in the shell. On a fresh cloud machine fetch the headless-capable
  Linux build from the godotengine/godot GitHub release page for the version in project.godot,
  unzip it, chmod +x, and export GODOT=./Godot_v4.x-stable_linux.x86_64.

Python tools need PIL and numpy (`pip install pillow numpy`). Regenerate assets with
`cd tools && python3 gen_fonts.py && python3 gen_pixel_art.py`. reference/ carries a .gdignore
so Godot never imports or exports the concept images.

## Before running anything
The class-name cache lives in .godot/. After a fresh clone or after deleting .godot, run:
    $GODOT --headless --path . --import
Without this, scripts fail with "Could not find type Outlaw" and similar.

## Tests (all headless, all must pass before a change is done)
    $GODOT --headless --path . -- --autotest
    $GODOT --headless --path . -- --deathtest
    $GODOT --headless --path . -- --flowtest
    $GODOT --headless --path . -- --dailytest
    $GODOT --headless --path . -- --aimtest
Each prints [autotest] lines and exits 0 or 1. Ignore renderer spam from the dummy display
server. Write the tests as DESIGN.md section 12 describes them, in main.gd, before the
features they cover exist if that helps; a failing test that describes the target is fine
inside a milestone, never at its end.

## Looking at the game without a phone
    xvfb-run -a -s "-screen 0 1200x1200x24" $GODOT --path . --rendering-driver opengl3 \
      --resolution 540x1168 -- --shot --when=ready --round=3 --out=/tmp/shot.png
This writes /tmp/shot.png (2x) and /tmp/shot_native.png (270 x 584). Add --screen=howto (or any
menu card id) to capture a card. Look at the PNG before calling a visual
task done, and compare it against the matching image in reference/. Install xvfb with apt if it
is missing.

## Milestones (one session each, commit at the end of each)
1. Project skeleton, SubViewport pipeline, pixel_art.gd palette and raster tools, title screen
   with all buttons, tests scaffolded.
2. World: street, town, sky bands, parallax, props, ambience. Frame: title, ready.
3. Characters: sprite rig, face library, clothes, the ten named outlaws, the dummy, idle
   and walk-in. Frame: lineup of the player and all ten outlaws next to reference/bas_characters.png.
4. Duel loop: hold, standoff, draw, aim, hit resolution, wounds, enemy fire and misses,
   quirks, wanted card, result card, death card. Tests: autotest, aimtest, flowtest.
5. Deaths and gore: tiers, variants, 2D ragdoll or fall controller, blood on bodies, pools,
   gibs. Test: deathtest. Frames: kill, corpse per tier.
6. Modes and persistence: run, daily, practice, high scores, outlaws, stats, how to play, pause.
   Test: dailytest.
7. Audio and haptics, music loop, reactive layer.
8. Visual review pass against every reference image, Android export preset, packaging.

## Working style
- One feature at a time. Run the tests, render a frame if it is visual, then commit with a
  short message describing the player-facing change.
- Never break pixel discipline: no filtering, no subpixel positions, no alpha-blended
  gradients, no post-processing. Glows and haze are dithered or stepped palette pixels only.
  If a shortcut needs one of these, find another shortcut.
- No em-dashes in any UI text. In-duel prompts are two or three words ("Missed · 4 left").
- Every UI string goes through ui.gd helpers; every sound through Sfx.play.
- Outlaw traits are data in outlaws.gd; quirk logic lives in main.gd next to the other quirks.
- When you change a number that affects feel (spread, hit radius, survival, draw times),
  say so in the commit message.
- The owner tests on a phone, not on this machine. At the end of each milestone list what to
  try on the phone and what to look for.

## Packaging for someone without the editor
    rm -rf .godot && find . -name "*.import" -delete && zip -qr ../blood-at-sundown.zip . -x ".git/*"
