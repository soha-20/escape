# Escape Game — Specification

This document describes how the program meets each requirement in `problem.md`.

## Decisions agreed with the product owner

| Topic | Decision |
|---|---|
| Language | Python 3 (3.10+), standard library only (tkinter for graphics) |
| Interface | A **graphical game window** (tkinter) launched from the terminal with drawn figures for the player and the Grim Reaper. A plain terminal version is kept behind `--text`. |
| Pace (round 5) | **Real-time in the game window** (R13, R14): the Reaper moves on its own clock, and holding a movement key keeps the player running. **`--text` stays turn-based**: there the Reaper moves one step after every player move |
| Game area | One fixed, hand-designed layout (the game is meant to be short): a maze in rounds 1–2, an open graveyard in rounds 3–4, **a graveyard laid out along a gravel path** since round 5 (R12) |
| Structure (round 5) | **A clear path through neat rows of graves** (R12): a gravel path winds from the start to the exit gate, with tidy rows of headstones on both sides. Hurdles and hazards lie on the path at planned points, and signposts mark the side paths that lead into dead ends |
| Chase (round 5) | **Real-time, hold to run** (R13): the Reaper moves whether or not the player does, a little slower than a running player, so a clean run escapes and every hesitation lets it catch up |
| Sound (round 5) | **Removed completely** (R15): no tones, no heartbeat, no `--mute`. The visual cues (beating hearts, pulsing red aura, red border) stay |
| IDs (round 5) | The unnumbered round-5 bullet (remove the sound) is **R15** |
| Lives (round 2) | **3 lives.** Being caught costs one life; the game is lost when the last one goes |
| Resume (round 2) | After a catch the game pauses; **R** resumes with player and reaper **both back on their start tiles** |
| After the last life (round 2) | GAME OVER; **R** starts a fresh game with 3 lives |
| Lost hearts (round 2) | Stay in place as **grey empty hearts** (♥ ♥ ♡) |
| Text version (round 2) | Lives and hearts apply to `--text` too: `r` + Enter resumes |
| Hurdles (round 3) | **Gravestones, iron fences and dead trees block** the way at no cost. **Open graves and thorn bushes are hazards:** stepping on one **costs a life** |
| IDs (round 4) | The two unnumbered round-4 bullets are **R10** (jumping) and **R11** (scary graphics) |
| Graphics (round 4) | **Richer tkinter drawing**, still standard library only: figures that move with walk cycles, a floating, tattered, scarier Reaper, mist |
| Lighting (round 4) | **The whole view is moonlit.** No dark fog of war. The Reaper is visible wherever it is |
| Jump key (round 4) | **Up arrow = jump forward** (in the direction the player faces), landing 2 tiles on. **W/A/S/D and ← ↓ →** move; W moves north |
| Jumpable (round 4) | **Low hurdles** (fallen headstones, coffins) block walking but can be jumped; **open graves and thorn bushes can be jumped too**. Gravestones, fences, trees and signposts still block |
| Reaper and low hurdles (round 4) | **The Reaper glides over low hurdles**, as over hazards (decision 0004) |

*Revision (2026-11-18):* the first version drew the game as text in the terminal. The product owner found it unattractive: no real figures, and the colours didn't show. They chose a tkinter window over a terminal-only game, even though `problem.md` mentions the terminal. The game is still started from the terminal, and the terminal version is still available.

*Revision (2026-11-19, round 2):* R4 and R5 add three lives and a row of hearts. R3 changes meaning: a catch now costs a life, and the game is lost only when the last life is gone. See `docs/decisions/`.

*Revision (2026-11-19, round 3):* R6 replaces the maze with a graveyard, and R7 makes graves and other objects the hurdles, some of which hurt. The product owner chose a **new, more open layout** over re-skinning the old corridors, and chose **"graves block, some hazards hurt"** over hurdles that only block, hurdles that hurt when bumped, or hazards that only cost a turn. This changes R1 (what a blocked move says), R2 (signs and dead ends in open ground) and R4 (a life can also be lost to a hazard). The earlier tests were adapted, not deleted.

*Revision (2026-11-19, round 4):* R8 and R11 ask for better, scarier graphics with figures that move; R9 removes the dark screen; R10 adds jumpable hurdles on the Up arrow. This changes R1 (the Up arrow no longer moves north, and the torch-light fog of war is gone from both front ends) and R7 (hazards can be jumped). The earlier tests were adapted, not deleted. (The round-4 spec referred to decision records 0005 and 0006; they were never written, so those numbers are used by round 5.)

*Revision (2026-11-21, round 5):* R12 asks for a structured graveyard instead of scattered graves; R13 asks for a Reaper that really chases; R14 asks for smooth play without stops or glitches; R15 removes the sound. The product owner chose a **real-time chase with hold-to-run** (over a same-speed Reaper, a Reaper that speeds up, or staying turn-based), **a gravel path through neat rows of graves** (over sections with checkpoints, or several levels), **removing sound completely as R15**, and **keeping `--text` turn-based**. This changes:
* R1: the window game runs in real time; the Reaper no longer waits for the player's move; there is no sound and no `--mute`; the HUD shows time instead of turns.
* R2: the dead ends are side paths off the gravel path; the safe route now includes jumps.
* R6: the graveyard is no longer open ground; it is rows of graves along a path.
* R7: some hazards lie on the path and must be jumped.
* R8: figures glide at a constant speed and the camera no longer scrolls, because the whole graveyard is on screen.
* R9: the torch is a glow around the player instead of a warm tint on the tiles.
* R10: a jump pressed a moment early is remembered.
* R11: the mist drifts only on the title and end screens.

The earlier tests were adapted, not deleted. See `docs/decisions/0005-…` to `0007-…`.

Where `problem.md` and the answers above left a detail open, this spec picks a default, marked *(default)*. Each one can be changed.

## Overview

The player wakes at midnight in a fenced, moonlit graveyard, carrying a torch, and the Grim Reaper is close behind. A gravel path winds back and forth between neat rows of graves to the exit gate in the south fence. Coffins, fallen headstones, open graves and thorn bushes lie across the path; the player must leap them while running. Side paths branch off into dead-end plots, and signposts warn about them.

### The graveyard (R6, R12)

```
#############################
#R...P...O....C....*...=...T#
#+++T+++++T+++++T+++++T++!.+#
#+++++++++++++++O*        .!#
#+++T+++++T+++++T+++++T+++.+#
#T.....*....O....C....*....T#
#+.+T+++++T+++++T+++++T+++++#
#!.        *O+++++++++++++++#
#+.+T+++++T+++++T+++++T+++++#
#T....O....=....*....O.....T#
#+++T+++++T+++++T+++++T+++.+#
#+++++++++++++!!++++++++++.+#
#O *          ....O...C....T#
##############E##############
```

* Size: 14 rows × 29 columns *(default)*, stored as text in `escape_game/maze.py`.
* Legend:

  | Mark | Tile | Effect |
  |---|---|---|
  | `.` | gravel path (R12) | walkable |
  | space | grass | walkable |
  | `#` | iron fence | blocks |
  | `+` | gravestone | blocks |
  | `T` | dead tree | blocks |
  | `!` | signpost (R2) | blocks |
  | `O` | open grave | **hazard**: costs a life (R7) |
  | `*` | thorn bush | **hazard**: costs a life (R7) |
  | `=` | fallen headstone | **low hurdle**: blocks walking, can be jumped (R10) |
  | `C` | coffin | **low hurdle**: blocks walking, can be jumped (R10) |
  | `P`, `R`, `E` | player start, reaper start, exit gate | walkable (drawn as path) |

* **Shape (R12)** *(default)*. The path is one tile wide and runs in four **lanes**, joined by short bends:
  * lane A (row 1) runs east, lane B (row 5) west, lane C (row 9) east, and lane D (row 12) west to the gate `E` in the south fence;
  * between the lanes stand **neat rows of gravestones**, with a dead tree every sixth column, so the rows read as tidy cemetery sections rather than scattered graves;
  * the lanes end at dead trees, so the turns are clear.
* **Rhythm (R12).** Fourteen hurdles lie on the path, **3 to 5 tiles apart** *(default)*: four on each of lanes A–C and two on lane D. They are coffins and fallen headstones (bump and stop if not jumped) and open graves and thorn bushes (a life lost if not jumped). The run is: run, leap, run, leap, turn.
* **Dead ends (R2).** Three side paths leave the path and lead nowhere, each marked by a red warning sign:
  * a grass alley inside the graves between lanes A and B (entered from the first bend),
  * a grass alley between lanes B and C (entered from the second bend),
  * the crypt yard at the west end of lane D, beside the gate.

  Each ends in an open grave and a thorn bush.
* The player starts at `P`, the Reaper at `R`, **4 tiles** behind on the same lane.
* The way to the exit (walking and jumping, never stepping on a hazard) is **79 moves**: 65 steps and 14 jumps, covering 93 tiles. In `--text` the Reaper stays 4 steps behind on the walking stretches, and each jump gains the player one step.

## R1 — The game starts and the player must escape from the Grim Reaper

* **Start.** `py -m escape_game` opens the game window on a title screen. The screen shows:
  * "ESCAPE THE GRIM REAPER",
  * a large animated Reaper and the player,
  * a moonlit graveyard in drifting mist,
  * a short story that explains running, jumping and the hazards.

  Any key starts the game. The Reaper sets off at the player's first step *(default, so the player is never caught before they have touched the keys)*.
* **Figures.** Both characters are drawn from shapes, not letters (R8, R11):
  * **Player:** an adventurer in a blue tunic holding a torch whose flame flickers.
  * **Grim Reaper:** a tall, floating, tattered black cloak, a skull in a deep hood with glowing red eyes that pulse, bony fingers and a large scythe.
* **Controls (window).** *Changed in round 5 (R13, R14):*
  * `W`/`A`/`S`/`D` and `←` `↓` `→` **move while held**, see R14;
  * `↑` **jumps** (R10); `W` moves north;
  * `Esc` closes the game;
  * after a catch, `R` resumes (R4); after the game ends, `R` plays again *(default)*.
* **Rules in real time (window).** See R13 for the Reaper's clock and R14 for running. Whenever someone arrives on a tile, the game checks in this order:
  1. If the player is on the Reaper's tile, they are caught (R3).
  2. If the player is on the exit, the player **wins**. Nothing moves after that.
  3. If the player stepped onto a hazard, they lose a life (R7).
* **Turn order (`--text`).** Unchanged from round 4:
  1. The player moves (or jumps).
  2. The game checks the three cases above.
  3. Otherwise the Reaper takes one step along a shortest path to the player and the catch check follows.
  * The Reaper's path is a breadth-first search through every walkable tile, including hazards and low hurdles, which it glides over. Ties are broken in a fixed order, so the game is deterministic.
* **Moves that don't count.** Moving into a gravestone, fence, tree, signpost or low hurdle doesn't move the player. A message names what is in the way, e.g. "A gravestone blocks your way." In `--text` it uses no turn. In the window the Reaper keeps coming (R13).
* **Display (window).** *Changed in round 5 (R14):*
  * **The whole graveyard is on screen at once**, at 38 px per tile: 1102 × 532 px, which fits a 1280 × 720 screen. There is no scrolling camera.
  * **Tiles:** see R6, R7, R10 and R12. **Exit:** an iron cemetery gate with a green glow and the label "EXIT".
  * **Status panel (HUD)** below the graveyard, on its own canvas:
    * three life hearts (R5), whose red hearts beat faster as the Reaper approaches;
    * the **time** since the run began (`Time 12.3 s`) *(default; replaces the turn counter in the window)*;
    * a status line ("Distant footsteps…" in grey, "Something cold breathes down your neck…" in orange, "RUN! The Reaper is right behind you!" in red);
    * sign texts (R2), bump messages, and the controls.
  * **Danger:** when the Reaper is 3 steps or fewer away, the frame around the graveyard pulses red.
* **Sound.** *Removed in round 5 (R15).* The game makes no sound.
* **Win.** Reaching the exit shows a "YOU ESCAPED!" screen with the time (window) or turn count (`--text`).
* **Fallback.** If the window can't open (no tkinter, no display), the program says so and starts the terminal version instead.
* **Terminal version (`--text`).** Turn-based (see the turn order above):
  * It draws the whole graveyard with `@` (player), `R` (reaper), `E`, and the layout marks, using ANSI colours (`--no-color` for plain text). The path is `.` in dim yellow and grass is `,` (R12). Hazards are red, low hurdles cyan.
  * Each move is `w`/`a`/`s`/`d` + Enter, `j` + Enter jumps forward (R10), and `q` quits.
  * Unknown commands cost no turn.
  * It ignores the BOM (byte-order mark) that Windows PowerShell adds to piped input.

## R2 — Hurdles with hints and signs telling which way to go

*Changed in round 5 (R12):* the dead ends are side paths that leave the gravel path. The safe route is the way to the exit by walking and jumping, never landing on a hazard (`Maze.player_route`).

* **Signs** are wooden **signposts** next to the decision points. In the window each is drawn as a post with a parchment plaque, a glowing red or green border and `!`. A sign's message appears in the HUD when the player stands on a walkable tile orthogonally next to it: *Painted on a signpost: "…"*. A text too long for the window is drawn in a smaller font (down to 10 pt) until it fits.
* There are two kinds of sign, and every sign is honest:
  * **Warning (red, ⚠):** stands at the entrance of a dead end and points into it.
    * *"Wanna get stuck? ←"* (the example in problem.md) at the first alley;
    * *"The family plot. Nobody leaves it. →"* at the second;
    * *"← The crypt yard. Nobody came back."* beside the gate.
  * **Guide (green, ✔):** points toward the exit.
    * *"→ Round the bend and down. Hurry."* before the first bend;
    * *"← The gate is right here! RUN!"* on lane D.
* **Validity checks (tested):**
  * the exit can be reached from the start without stepping on a hazard;
  * there are at least 3 dead ends, and each one has a warning sign at its entrance pointing into it;
  * every dead end next to the safe route is marked by a warning;
  * each guide sign points one step along a shortest safe way to the exit;
  * in `--text`, following the safe route wins, and the Reaper is never closer than 4 steps;
  * in `--text`, walking to the back of any warned dead end gets the player caught;
  * in `--text`, one step into a dead end and straight back is survivable.

## R3 — The player loses once the Grim Reaper catches them

*Changed in round 2:* a catch costs one life (R4). The player **loses the game** when they are caught with their last life. Everything below describes a catch. The GAME OVER screen appears only after the last life is gone.

* The player is **caught** when the player and the Reaper are on the same tile. Being next to the Reaper is still safe. This happens if:
  * the Reaper steps onto the player's tile, or
  * the player steps or jumps onto (or through) the Reaper's tile.
* When caught with the last life, the window shows a "GAME OVER" screen under a blood-red moon, with a large Reaper, three grey empty hearts and the line "The Reaper's hand closes on your shoulder."
* Once the game is over, movement keys are ignored. Only `R` (play again) and `Esc` (quit) work.

## R4 — Three lives; R resumes

*Changed in round 3:* a life can also be lost to a hazard (R7). Everything in this section about a catch also applies to a hazard, except for the wording on the screen.

* A new game starts with **3 lives** (`MAX_LIVES = 3` in `game.py`).
* **Catch with lives left.** Being caught (as in R3) takes one life. If at least one life remains, the game enters the **caught** state (`Status.CAUGHT`):
  * Everything stops where the catch happened. Moves are ignored.
  * The window shows a "CAUGHT!" screen with the hearts left and "Press R to resume    Esc to quit".
  * The terminal version prints "The Reaper's cold hand grabs you! You lose a life." and "Resume: r + Enter    Quit: q".
* **Resume.** Pressing `R` (`r` + Enter in `--text`) puts the player and the Reaper **back on their start tiles**, 4 tiles apart. *Changed in round 5 (R13):* in the window the Reaper sets off again at the player's first step, and keys still held from before are forgotten. Then:
  * the turn counter and the clock keep counting, so the win screen shows the total *(default)*.
* **Last life.** A catch with the last life ends the game: `Status.LOST` and the R3 GAME OVER screen. From there, `R` starts a fresh game with 3 lives in the window. The terminal version ends, as before.
* `R` does nothing while playing. In `--text`, `r` while playing is an unknown command and costs no turn. `q` still quits while caught.
* Why both figures reset rather than only the Reaper: see `docs/decisions/0001-resume-from-start.md`.

## R5 — Three red hearts that empty as lives are lost

* **Window.** The status panel shows a row of three hearts at the left. Each remaining life is a red ♥ (tag `heart`) that beats in time with the on-screen heartbeat. Each lost life is a grey empty ♡ (tag `heart_lost`) in the same place, so the row reads ♥ ♥ ♥ → ♥ ♥ ♡ → ♥ ♡ ♡. The CAUGHT! and GAME OVER screens show the same row, large (tags `big_heart` and `big_heart_lost`). GAME OVER shows ♡ ♡ ♡.
* **Terminal.** Each screen shows `Lives: ♥ ♥ ♡`, with the full hearts in red when colour is on.
* Lost hearts come back only with a new game (`R` after GAME OVER).
* A heart lost to a hazard (R7) empties in exactly the same way.

## R6 — The game area is a graveyard

* The game area is the graveyard described in the Overview. *Changed in round 5 (R12):* it is no longer open ground. It is a gravel path between rows of graves, with iron fences around the grounds and an iron exit gate in the south fence.
* **Window drawing.** Every walkable tile is dark grass or, on the path, gravel:
  * gravel path (tag `path`): a pale, speckled strip (R12);
  * gravestone (tag `grave`): a rounded grey headstone with a cross;
  * iron fence (tag `fence`): black bars with spear tips on two rails;
  * dead tree (tag `tree`): a bare trunk with crooked branches;
  * signpost (tags `sign`, `sign_warning` / `sign_guide`): see R2;
  * the exit (tag `exit`): see R1.

  Every blocking object also carries the tag `obstacle`. The intro and the ending screens show a moonlit graveyard.
* **Text.** The intro and the screens say "graveyard". A sign is "painted on a signpost".
* Inside the code, `Maze` keeps its name and `is_wall()` keeps meaning "blocked" *(default, to limit churn)*.

## R7 — Graves and other objects are the hurdles; some can hurt

* **Blocking hurdles:** gravestones, iron fences, dead trees and signposts. Walking into one costs no life. The message names the object (R1).
* **Hazards:** open graves (`O`) and thorn bushes (`*`). They are walkable, but **stepping onto one costs a life**. Jumping over one is safe (R10). *Changed in round 5 (R12):* most hazards lie **on the path**, so the player must jump them; the others lie at the back of the dead ends.
  * The player stays on the hazard and nothing else moves.
  * With lives left, the game goes to the same paused state as a catch (`Status.CAUGHT`). `Game.hurt_by` names what took the life: `"reaper"`, `"open grave"` or `"thorn bush"`. **R** resumes with both figures back on their start tiles, exactly as after a catch (R4, decision 0001).
  * With the last life, the game is lost (GAME OVER), as in R3.
* **Screens.**
  * Window: the life-lost screen is titled **"HURT!"** (tag `caught_title`) instead of "CAUGHT!". It says *"You tumble into an open grave! You lose a life."* or *"A thorn bush tears into you! You lose a life."* and shows the big player figure instead of the Reaper.
  * GAME OVER caused by a hazard says *"You fell into an open grave. The Reaper only had to wait."* (or the thorn-bush version).
  * Terminal: the same sentences.
* **Drawing.** In the window, an open grave (tags `hazard`, `open_grave`) is a black pit with a heap of dug earth. A thorn bush (tags `hazard`, `thorn_bush`) is a tangle of dark red spiky branches. In `--text` both are drawn in red.
* **The Reaper is not hurt by hazards** and glides over them. Why: `docs/decisions/0004-reaper-glides-over-hazards.md`.
* Why a hazard reuses the catch state instead of a new one: `docs/decisions/0003-hazards-reuse-the-life-lost-state.md`.

## R8 — An eye-catching interface; figures that move; a scary Reaper

*(Window only. The `--text` version keeps its letters.)*

* **Motion.** *Changed in round 5 (R14):* each step **glides at a constant speed** from tile to tile. The old ease-in-ease-out slowed down at every tile, and that made a run stutter. A run of steps therefore looks like one smooth run. The camera no longer moves: the whole graveyard is on screen.
* **Walk cycle (player).** While moving, the legs and arms swing (one stride per tile) and the body bobs. The player faces left or right according to the last sideways move and is drawn mirrored when facing left. Standing still, the player breathes (a slight bob) and the torch flame flickers.
* **The Reaper moves too.** It floats above the ground (a slow up-and-down hover, with a shadow beneath it). Its tattered hem flutters, its cloak leans into the direction it moves, and its scythe sways.
* **Polish.** Tiles are drawn with light and dark sides (gravestones with an "RIP" inscription and cracks, gnarled trees, shaded iron), and the HUD has a framed panel with a controls line.
* **Keeping frames cheap (R14).** See R14.
* **Testable parts.** Pure helpers (`tween`, `walk_pose`, `jump_height`, `hover`) compute the animation. `Game` records when each figure last started moving (`player_from`, `player_moved_at`, `player_move_ms`, and the same for the Reaper). The window draws each figure at `progress = (clock − moved_at) / move_ms` of the way. Window tests drive the clock by hand (`advance(ms)`) instead of waiting.
* **Screens wait for the motion.** The CAUGHT!/HURT!/GAME OVER/YOU ESCAPED! screens appear once the last step has been seen on screen (at most one step later).

## R9 — The whole screen is lit, not just one side

* **Moonlight everywhere.** Every tile is drawn clearly, in a cool, moonlit colour (80 % brightness, `MOONLIGHT`). There is no fog of war in either front end. *Changed in round 5 (R14):* the whole graveyard is on screen, so nothing is ever off to one side.
* **Torch glow.** *Changed in round 5:* the tiles are drawn once per window (R14), so the torch no longer tints them. Instead, warm rings of torchlight glow on the ground around the player and move with them (tag `torch_glow`).
* **The Reaper and hazards** are always drawn.
* **Text version:** the whole graveyard map is printed every turn.

## R10 — Low hurdles the player can jump with the Up arrow

* **Low hurdles** (`=` fallen headstone, `C` coffin) lie on the path. Walking into one does not move the player, and the message adds a hint: *"A coffin blocks your way. Press ↑ to jump over it."* (`--text`: *"Type j to jump over it."*).
* **Facing.** The player faces the direction of their last move attempt (a bump counts). At the start they face right (east), along lane A.
* **Jump** (`↑` in the window, `j` + Enter in `--text`): the player leaps over the tile in front of them and lands on the tile after it, **2 tiles at once**.
  * Jumpable: low hurdles, open graves and thorn bushes (a hazard jumped over does no harm).
  * The landing tile must be ground the player could walk on: not an obstacle, not another low hurdle, not a hazard.
  * If the tile in front is plain ground (or anything not jumpable), or the landing tile is not safe, nothing happens. The message says why: *"There is nothing here to jump over."* or *"You can't land there: a gravestone is in the way."*
  * Leaping onto or through the Reaper's tile is a catch. Landing on the exit wins.
  * `--text`: a jump takes one turn, then the Reaper takes its one step.
  * Window *(changed in round 5, R13/R14)*: a jump takes `JUMP_MS` = 270 ms for 2 tiles, which is faster than running (180 ms per tile). If the jump can't be made yet, an `↑` pressed while running is **remembered for 300 ms** (`JUMP_BUFFER_MS`) *(default)*. The player keeps running and leaps as soon as a hurdle is in front, so a jump pressed a moment early still works.
* **The Reaper glides over low hurdles** (as over hazards, decision 0004). Jumping is how the player gains ground.
* **Window:** the player rises in an arc (about 0.6 tile high) with a shadow on the ground. A low hurdle is drawn as a cracked headstone lying flat (tags `low_hurdle`, `fallen_headstone`) or a wooden coffin with a cross (tags `low_hurdle`, `coffin`).
* **Logic:** `Game.jump()`, `Game.facing`, `Game.jumped`, `Outcome.NO_JUMP` with `Game.jump_blocked` (`"nothing"` or what is in the way). `Maze.low_hurdle(pos)`. `Maze.player_route(a, b)` is a shortest way for the player, by walking and jumping.

## R11 — Graphics that make the game look scary

* **The Reaper** is about 1.6 tiles tall, so it towers over the player. It has:
  * a deep, empty hood around a skull with black, sunken sockets;
  * **glowing red eyes with white-hot cores** that pulse;
  * bony fingers around a long scythe with a curved, gleaming blade;
  * a tattered hem that flutters over puffs of black smoke.

  **Rings of red light pulse** on the ground under it, faster as it gets closer to the player.
* **Atmosphere:** thin **wisps of pale mist** lie over the graveyard. *Changed in round 5 (R14):* during play the mist stays still, because moving it repaints the whole graveyard (about 100 ms a frame, measured). It **drifts on the title and end screens**. Those screens have:
  * a big moon (blood red at GAME OVER) behind bare branches;
  * ground mist over the graves;
  * a blood-red title with a dark shadow;
  * the hovering Reaper.
* **No transparency:** Tk on Windows ignores the `stipple` option and draws such shapes solid. So glows are drawn as rings and cores, mist as thin lines, and no item uses `stipple` (tested).
* **Danger:** when the Reaper is 3 steps or fewer away, the frame around the graveyard pulses red.
* Tags for tests:
  * Reaper: `reaper` (all of it), `reaper_eyes`, `reaper_glow`, `scythe`, `aura`;
  * player: `player_leg`, `player_arm`, `player_shadow`, `flame`, `flame_core`, `torch_glow`;
  * `mist`.

## R12 — A structured graveyard, not scattered graves

* *Problem:* in rounds 3–4 the graves stood scattered over open fields. The way on was unclear, and running felt like random bumping.
* **A path to follow.** A gravel path (`.`) runs from the start to the exit gate. The safe route (walking and jumping) uses **only path tiles** (and the start and exit).
* **Neat rows.** Between the lanes, gravestones stand in **unbroken rows**. Every grave row is solid from fence to fence except for the bends and the dead-end entrances, with a dead tree every sixth column.
* **Planned hurdles.** All 14 hurdles on the route lie **on the path**, 3 to 5 tiles apart, and each one must be jumped. None stands at a bend, so a jump never has to turn.
* **No stray branches.** The path forks only where a warning sign stands (R2). Every other tile of the path has exactly two ways on: back and forward.
* **Clear turns.** Each lane ends against a dead tree, and the bends are part of the path.
* Layout tests: see R2 and R6; `test_R12_…` in `tests/test_maze.py`.

## R13 — The Grim Reaper really chases

* *Problem:* the Reaper moved only when the player moved, so it always stood "4 blocks away" and could never close in on a player who stopped.
* **Its own clock (window).** After the player's first step, the Reaper takes one step along a shortest path to the player every `REAPER_STEP_MS` = **200 ms** *(default)*, whether or not the player moves. A player who stands still is caught.
* **A little slower than a runner.** The player runs one tile per `PLAYER_STEP_MS` = **180 ms** and jumps 2 tiles in `JUMP_MS` = **270 ms** *(defaults)*. On a clean run the gap grows; every bump, pause or wrong turn lets the Reaper close in.
  * Simulated: a perfect run takes about 15 s and the Reaper is never closer than 4 tiles.
  * A player who loses 150 ms at every jump and every turn still escapes, with the Reaper at times 3 tiles behind.
  * One who loses 250 ms at each is caught.
* **Logic, not timers.** The rules for time live in `game.py`, on a clock that the window advances: `Game(realtime=True)` and `Game.update(ms)`. Tests can then run a whole chase in a few milliseconds. Why: `docs/decisions/0005-realtime-chase-on-a-game-clock.md`.
* `--text` stays turn-based (the product owner's choice): a line-based terminal can't run a clock.

## R14 — Smooth flow, no stops or glitches

* *Problem:* the round-4 window had three causes of stops:
  * each key press was a separate turn;
  * each slide eased in and out, so a run stopped at every tile;
  * worst, each turn rebuilt and scrolled the whole view, and on the development machine a full repaint takes 200–800 ms.
* **Hold to run.** Holding a movement key keeps the player running, one tile every 180 ms with no pause between tiles. Releasing it stops the player at the next tile. A key pressed while the player is ready moves at once.
* **Cornering** *(default)*. If two movement keys are held, the most recently pressed one wins. If its way is blocked, the player keeps running in the other held direction. So pressing `↓` a moment before a bend turns the corner smoothly instead of bumping a grave. Releasing a key falls back to the one still held.
* **A bump stops the run without stalling the keys.** Running into an obstacle or a low hurdle stops the player and shows the message. Any new key press acts at once.
* **Remembered jumps:** see R10.
* **Cheap frames.** Each canvas repaint must stay small:
  * The graveyard is drawn **once per window** and never moves (no camera; decision 0006).
  * Each frame redraws only the figures and the glows around them.
  * The HUD is on a separate canvas, so the beating hearts never repaint the graveyard.
  * The red danger frame is the colour of a frame around the canvas, not canvas items.
  * The mist lies still during play (R11).

  Measured: about 10 ms per frame, against 200–800 ms for a full repaint.
* **Real time, steadily.** The window runs a frame every 20 ms. It advances the game clock by the real time that has passed, at most 100 ms at once, so a stalled frame never makes figures jump.

## R15 — No sound

* The game makes **no sound** at all, in either front end: no heartbeat, no tones, no terminal bell (`\a`).
* `escape_game/sound.py` is deleted. No module imports `winsound`.
* The `--mute` option is removed *(default)*. There is nothing to mute.
* The tension cues that used to be heard are now only seen: beating hearts, the Reaper's pulsing aura, the status line, the red danger frame.
* *Changes R1 and R4:* their sound tests were adapted to check that nothing sounds.

## Program structure

```
escape_game/
  __init__.py
  __main__.py    # command-line entry: options, opens the window (or the --text loop)
  maze.py        # fixed graveyard layout, path, obstacles, hazards, signs, parsing, pathfinding (BFS)
  game.py        # Game state: positions, move()/jump(), turn order, the real-time clock, lives, win/lose
  gui.py         # tkinter window: the whole graveyard, figures and motion, HUD, screens
  render.py      # text drawing for --text mode, and the shared wording
tests/
  test_*.py      # pytest; every test names the requirement it checks (R1–R15)
docs/decisions/   # decision records (Y-statements), numbered 0001, 0002, ...
```

The game logic (`game.py`, `maze.py`) does no input/output, so tests can call it directly. `gui.py` only draws the game and turns key presses and the passing of time into `Game` calls. The window tests open hidden windows, send key presses, advance the clock by hand and inspect the tagged canvas items.

## Out of scope for this version

Multiple levels, random graveyards, moving hazards, checkpoints, a Reaper that speeds up, high scores, saving, sound.
