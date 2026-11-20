# Escape Game — Specification

This document describes how the program meets each requirement in `problem.md`.

## Decisions agreed with the product owner

| Topic | Decision |
|---|---|
| Language | Python 3 (3.10+), standard library only (tkinter for graphics) |
| Interface | A **graphical game window** (tkinter) launched from the terminal with drawn figures for the player and the Grim Reaper. A plain terminal version is kept behind `--text`. |
| Pace | Turn-based: the reaper moves only when the player moves |
| Game area | One fixed, hand-designed layout (the game is meant to be short): a maze in rounds 1–2, a graveyard since round 3 (R6) |
| Reaper speed | The reaper moves one step after every player move |
| Tension | Visible chase plus a heartbeat **sound** that speeds up as the reaper closes in |
| Lives (round 2) | **3 lives.** Being caught costs one life; the game is lost when the last one goes |
| Resume (round 2) | After a catch the game pauses; **R** resumes with player and reaper **both back on their start tiles** |
| After the last life (round 2) | GAME OVER; **R** starts a fresh game with 3 lives |
| Lost hearts (round 2) | Stay in place as **grey empty hearts** (♥ ♥ ♡) |
| Text version (round 2) | Lives and hearts apply to `--text` too: `r` + Enter resumes |
| Game area (round 3) | The maze is replaced by a **new, more open graveyard** (open fields of graves, not a re-skin of the round-1 corridors) |
| Hurdles (round 3) | **Gravestones, iron fences and dead trees block** the way at no cost. **Open graves and thorn bushes are hazards:** stepping on one **costs a life** |
| IDs (round 4) | The two unnumbered round-4 bullets are **R10** (jumping) and **R11** (scary graphics) |
| Graphics (round 4) | **Richer tkinter drawing**, still standard library only: figures slide between tiles with walk cycles, a floating, tattered, scarier Reaper, drifting mist |
| Lighting (round 4) | **The whole view is moonlit.** No dark fog of war; the torch only adds a warm glow around the player. The Reaper is visible whenever it is on screen |
| Jump key (round 4) | **Up arrow = jump forward** (in the direction the player faces), landing 2 tiles on. **W/A/S/D and ← ↓ →** move; W moves north. One jump = one turn |
| Jumpable (round 4) | **New low hurdles** (fallen headstones, coffins) block walking but can be jumped; **open graves and thorn bushes can be jumped too**. Gravestones, fences, trees and signposts still block |
| Reaper and low hurdles (round 4) | **The Reaper glides over low hurdles**, as over hazards (decision 0004) |

*Revision (2026-11-18):* the first version drew the game as text in the terminal. The product owner found it unattractive: no real figures, and the colours didn't show. They chose a tkinter window over a terminal-only game, even though `problem.md` mentions the terminal. The game is still started from the terminal, and the terminal version is still available.

*Revision (2026-11-19, round 2):* R4 and R5 add three lives and a row of hearts. R3 changes meaning: a catch now costs a life, and the game is lost only when the last life is gone. See `docs/decisions/`.

*Revision (2026-11-19, round 3):* R6 replaces the maze with a graveyard, and R7 makes graves and other objects the hurdles, some of which hurt. The product owner chose a **new, more open layout** over re-skinning the old corridors, and chose **"graves block, some hazards hurt"** over hurdles that only block, hurdles that hurt when bumped, or hazards that only cost a turn. This changes R1 (what a blocked move says), R2 (signs and dead ends in open ground) and R4 (a life can also be lost to a hazard). The earlier tests were adapted, not deleted.

*Revision (2026-11-19, round 4):* R8 and R11 ask for better, scarier graphics with figures that move; R9 removes the dark screen; R10 adds jumpable hurdles on the Up arrow. This changes R1 (the Up arrow no longer moves north, and the torch-light fog of war is gone from both front ends) and R7 (hazards can be jumped). The earlier tests were adapted, not deleted. See `docs/decisions/0005-…` and `0006-…`.

Where `problem.md` and the answers above left a detail open, this spec picks a default, marked *(default)*. Each one can be changed.

## Overview

The player wakes at midnight in a fenced, moonlit graveyard, carrying a torch, and the Grim Reaper is close behind. The player must reach the graveyard's exit gate before the reaper reaches them. Gravestones, iron fences and dead trees stand in the way, and open graves and thorn bushes hurt anyone who steps on them. Fallen headstones and coffins lie low enough to jump over (R10). Signposts warn the player away from fenced dead-end plots, or point the way out.

### The graveyard (R6)

```
###############################
#R   P   O   *   *    ++#     #
#       +   +   +   + T+# + + #
#  T                = +!#     #
#     +   +   +   +        +  #
#           *  O    O + #    +#
#  +    +*  +   +   + T #######
#            T        +      !#
############################ ##
#            O #!   O      C  #
#  +   +   +      +   +   +   #
#              #    *      = *#
################ T  +   +  C  #
# +  #! * +    #              #
#                 +   +   +   #
#  + #E  +  O  #!      *  O   #
###############################
```

* Size: 17 rows × 31 columns *(default)*, stored as text in `escape_game/maze.py`.
* Legend:

  | Mark | Tile | Effect |
  |---|---|---|
  | space | grass | walkable |
  | `#` | iron fence | blocks |
  | `+` | gravestone | blocks |
  | `T` | dead tree | blocks |
  | `!` | signpost (R2) | blocks |
  | `O` | open grave | **hazard**: costs a life (R7) |
  | `*` | thorn bush | **hazard**: costs a life (R7) |
  | `=` | fallen headstone | **low hurdle**: blocks walking, can be jumped (R10) |
  | `C` | coffin | **low hurdle**: blocks walking, can be jumped (R10) |
  | `P`, `R`, `E` | player start, reaper start, exit gate | walkable |

* **Shape** *(default)*. There are two open fields, each 7 rows tall, with rows of graves, trees and hazards scattered across them. A small yard in the south-west holds the exit gate.
  * Field A (top): the player runs east. Field B (middle and bottom): the player runs west. In the yard, the exit is at `E`.
  * An iron fence between the fields leaves one gate at the far east, so the reaper can't cut across.
  * Three **fenced plots** are dead ends with a single narrow entrance:
    * a family plot in the north-east of field A
    * the north-west of field B
    * a crypt yard next to the exit
* The player starts at `P`, the reaper at `R`, which is **4 steps** behind.
* The shortest route to `E` that avoids every hazard is **59 moves**. Hazards are placed so that walking around them on that route costs no extra steps, and the reaper stays exactly 4 steps behind the whole way.
* **Low hurdles (R10)** *(default)*: four of them, at (3,20), (9,27), (11,27) and (12,27), lie on open grass beside the safe route. They don't lengthen the walking route (still 59 moves, Reaper exactly 4 behind), but each one gives a jump that lands 2 walking steps closer to the exit, so a jump there gains the player one step on the Reaper.
* As before, each step into a wrong place and back costs 2 steps of the gap. Walking to the back of any fenced plot gets the player caught. One hesitation is survivable.

## R1 — The game starts and the player must escape from the Grim Reaper

* **Start.** `py -m escape_game` opens the game window on a title screen. The screen shows "ESCAPE THE GRIM REAPER", a large animated Reaper and the player, a moonlit graveyard in drifting mist, and a short story that warns about open graves and thorns and explains the jump. Any key starts the chase.
* **Figures.** Both characters are drawn from shapes, not letters. Since round 4 they move and animate (R8, R11):
  * **Player:** an adventurer in a blue tunic holding a torch whose flame flickers.
  * **Grim Reaper:** a tall, floating, tattered black cloak, a skull in a deep hood with glowing red eyes that pulse, bony fingers and a large scythe.
* **Controls.** `W`/`A`/`S`/`D` and the `←` `↓` `→` arrow keys move with a **single keypress**. *Changed in round 4 (R10):* the `↑` arrow **jumps** instead of moving north; `W` still moves north. `Esc` closes the game. After a catch, `R` resumes (R4). After the game ends, `R` plays again *(default)*.
* **Turn order.**
  1. The player moves one tile.
  2. If the player stepped onto the reaper, they are caught (R3).
  3. If the player is now on the exit, the player **wins**. The reaper does not move after that.
  4. If the player stepped onto a hazard, they lose a life (R7). The reaper does not move after that.
  5. Otherwise the reaper moves one tile along a shortest path to the player. This is a breadth-first search through every walkable tile, **including hazards**, which the reaper glides over unharmed *(default)*. Ties are broken in a fixed order, so the game is deterministic.
  6. The game checks whether the player has been caught (see R3 and R4).
* **Turns that don't count.** Moving into a gravestone, fence, tree, signpost or low hurdle doesn't use a turn, and the reaper doesn't move. A message names what is in the way, e.g. "An iron fence blocks your way." or "A gravestone blocks your way." *(default)*. Other keys are ignored.
* **Display.**
  * **Camera:** a 15 × 9-tile view (52 px tiles) that follows the player and never shows anything outside the graveyard. Since round 4 it scrolls smoothly (R8).
  * **Light:** *changed in round 4 (R9):* the whole view is lit by moonlight; see R9. (Rounds 1–3 had a torch-light fog of war.)
  * **Tiles:** see R6, R7 and R10. **Exit:** an iron cemetery gate with a green glow and the label "EXIT".
  * **The reaper** is drawn whenever it is inside the camera view (R9).
  * **Status panel (HUD):** three life hearts (R5) whose red hearts beat faster as the reaper approaches, the turn number, and a status line ("Distant footsteps…" in grey, "Something cold breathes down your neck…" in orange, "RUN! The Reaper is right behind you!" in red).
  * **Danger:** when the reaper is 3 steps or fewer away, a red border flashes around the view.
* **Sound (tension).** After each turn the game plays a heartbeat based on the reaper's distance (shortest-path steps):
  * 6 or more steps: one slow, low beat
  * 4–5 steps: two beats
  * 3 steps or fewer: three fast, high beats

  The game also plays a short two-note drop when a life is lost *(default)*, a long falling tone when the last life is lost, and a rising tone when the player escapes.
  * On Windows sound uses `winsound.Beep`. Elsewhere it falls back to the terminal bell (`\a`).
  * In the window, sounds play on a background thread so the window never freezes.
  * `--mute` turns sound off. If sound fails, the game keeps running silently.
* **Win.** Reaching the exit shows a "YOU ESCAPED!" screen with the turn count.
* **Fallback.** If the window can't open (no tkinter, no display), the program says so and starts the terminal version instead.
* **Terminal version (`--text`).** This is the original text version:
  * It draws the **whole** graveyard (R9: no fog) with `@` (player), `R` (reaper), `E`, and the layout marks from R6 and R10 (`#`, `+`, `T`, `!`, `O`, `*`, `=`, `C`), using ANSI colours (`--no-color` for plain text). Hazards are red, low hurdles yellow.
  * Each move is `w`/`a`/`s`/`d` + Enter, `j` + Enter jumps forward (R10), and `q` quits.
  * Unknown commands cost no turn.
  * It ignores the BOM (byte-order mark) that Windows PowerShell adds to piped input.

## R2 — Hurdles with hints and signs telling which way to go

*Changed in round 3:* the hurdles are now the graveyard of R6 and R7 instead of maze corridors. Open ground has no corridor "forks", so the signs now mark the entrances of the fenced dead-end plots and the gates that lead on.

* **Signs** are wooden **signposts** standing next to the decision points *(default)*. In the window each is drawn as a post with a parchment plaque, a glowing red or green border and `!`. A sign's message appears when the player stands on a walkable tile orthogonally next to it, shown in large text in the HUD as *Painted on a signpost: "…"*. A text too long for the window is drawn in a smaller font (down to 10 pt) until it fits *(default)*.
* There are two kinds of sign, and every sign is honest *(default)*:
  * **Warning (red, ⚠):** stands at the entrance of a fenced dead-end plot and points into it, e.g. *"Wanna get stuck? →"* (the example in problem.md) at the first plot.
  * **Guide (green, ✔):** points toward the exit, e.g. *"↓ The gate lies this way. Hurry."*
* There are 3 warnings (one per plot) and 2 guides (the gate between the fields, and the right gap in field B's divider).
* **Validity checks (tested):**
  * the exit is reachable from the start without stepping on a hazard;
  * there are at least 3 dead-end plots, and each one has a warning sign at its entrance pointing into it;
  * every dead end next to the safe route is marked by a warning;
  * each guide sign points one step along a shortest safe way to the exit;
  * following the safe route wins, with the reaper never closer than 4 steps;
  * walking to the back of any warned plot gets the player caught;
  * one step into a plot and straight back is survivable.

## R3 — The player loses once the Grim Reaper catches them

*Changed in round 2:* a catch costs one life (R4). The player **loses the game** when they are caught with their last life. Everything below describes a catch. The GAME OVER screen appears only after the last life is gone.

* The player is **caught** when the player and the reaper are on the same tile *(default: being next to the reaper is still safe)*. This happens if:
  * the reaper steps onto the player's tile, or
  * the player steps onto the reaper's tile (walking back into it).
* When caught with the last life, the window shows a "GAME OVER" screen under a blood-red moon, with a large Reaper, three grey empty hearts and the line "The Reaper's hand closes on your shoulder." The falling tone plays.
* Once the game is over, movement keys are ignored. Only `R` (play again) and `Esc` (quit) work.

## R4 — Three lives; R resumes

*Changed in round 3:* a life can also be lost to a hazard (R7). Everything in this section about a catch also applies to a hazard, except for the wording on the screen.

* A new game starts with **3 lives** (`MAX_LIVES = 3` in `game.py`).
* **Catch with lives left.** Being caught (as in R3) takes one life. If at least one life remains, the game enters the **caught** state (`Status.CAUGHT`):
  * The player and the reaper stay where the catch happened, so the player can see it. Moves are ignored.
  * The window shows a "CAUGHT!" screen with the hearts left and "Press R to resume    Esc to quit". The life-lost tone plays.
  * The terminal version prints "The Reaper's cold hand grabs you! You lose a life." and "Resume: r + Enter    Quit: q".
* **Resume.** Pressing `R` (`r` + Enter in `--text`) puts the player and the reaper **back on their start tiles**, the same 4 steps apart, and the chase goes on. Then:
  * The turn counter keeps counting, so the win screen shows the total turns *(default)*.
  * Tiles the player has already seen stay remembered *(default)*.
  * The heartbeat plays again.
* **Last life.** A catch with the last life ends the game: `Status.LOST` and the R3 GAME OVER screen. From there, `R` starts a fresh game with 3 lives in the window. The terminal version ends, as before.
* `R` does nothing while playing (it is not a move key). In `--text`, `r` while playing is an unknown command and costs no turn. `q` still quits while caught.
* Why both figures reset rather than only the reaper: see `docs/decisions/0001-resume-from-start.md`.

## R5 — Three red hearts that empty as lives are lost

* **Window.** The status panel shows a row of three hearts at the left. Each remaining life is a red ♥ (tag `heart`) that beats with the heartbeat. Each lost life is a grey empty ♡ (tag `heart_lost`) in the same place, so the row reads ♥ ♥ ♥ → ♥ ♥ ♡ → ♥ ♡ ♡. The CAUGHT! and GAME OVER screens show the same row, large (tags `big_heart` and `big_heart_lost`). GAME OVER shows ♡ ♡ ♡.
* **Terminal.** Each screen shows `Lives: ♥ ♥ ♡`, with the full hearts in red when colour is on.
* Lost hearts come back only with a new game (`R` after GAME OVER).
* A heart lost to a hazard (R7) empties in exactly the same way.

## R6 — The game area is a graveyard

* The maze is replaced by the graveyard layout described in the Overview: open grassy fields, rows of gravestones, dead trees, iron fences around the grounds and around the plots, and an iron exit gate.
* **Window drawing.** Every tile sits on dark grass, which gets brighter in the torch light:
  * gravestone (tag `grave`): a rounded grey headstone with a cross;
  * iron fence (tag `fence`): black bars with spear tips on two rails;
  * dead tree (tag `tree`): a bare trunk with crooked branches;
  * signpost (tags `sign`, `sign_warning` / `sign_guide`): see R2;
  * the exit (tag `exit`): see R1.

  Every blocking object also carries the tag `obstacle`. The intro and the ending screens already show a moonlit graveyard.
* **Text.** The intro and the screens say "graveyard" instead of "maze". A sign is "painted on a signpost" instead of "scrawled on the wall".
* Nothing in the game is called a "wall" or a "maze" any more. Inside the code, `Maze` keeps its name and `is_wall()` keeps meaning "blocked" *(default, to limit churn)*.

## R7 — Graves and other objects are the hurdles; some can hurt

* **Blocking hurdles:** gravestones, iron fences, dead trees and signposts. Walking into one costs no turn and no life. The message names the object (R1).
* **Hazards:** open graves (`O`) and thorn bushes (`*`). They are walkable, but **stepping onto one costs a life**. *Changed in round 4 (R10):* jumping over one is safe.
  * The turn counts. The player stays on the hazard, and the reaper does not move.
  * With lives left, the game goes to the same paused state as a catch (`Status.CAUGHT`). `Game.hurt_by` names what took the life: `"reaper"`, `"open grave"` or `"thorn bush"`. **R** resumes with both figures back on their start tiles, exactly as after a catch (R4, decision 0001).
  * With the last life, the game is lost (GAME OVER), as in R3.
  * Sounds are the same as for a catch: the two-note drop for a lost life, the long falling tone at GAME OVER.
* **Screens.**
  * Window: the life-lost screen is titled **"HURT!"** (tag `caught_title`) instead of "CAUGHT!". It says *"You tumble into an open grave! You lose a life."* or *"A thorn bush tears into you! You lose a life."* and shows the big player figure instead of the reaper.
  * GAME OVER caused by a hazard says *"You fell into an open grave. The Reaper only had to wait."* (or the thorn-bush version).
  * Terminal: the same sentences.
* **Drawing.** In the window, an open grave (tags `hazard`, `open_grave`) is a black pit with a heap of dug earth. A thorn bush (tags `hazard`, `thorn_bush`) is a tangle of dark red spiky branches. In `--text` both are drawn in red.
* **The reaper is not hurt by hazards** and glides over them *(default)*, so cutting a corner through a hazard is never an option for the player, but it is for the reaper. On the safe route this gives the reaper no advantage (see R6). Why: `docs/decisions/0004-reaper-glides-over-hazards.md`.
* Why a hazard reuses the catch state instead of a new one: `docs/decisions/0003-hazards-reuse-the-life-lost-state.md`.

## R8 — An eye-catching interface; figures that move; a scary Reaper

*(Window only. The `--text` version keeps its letters.)*

* **Motion between tiles.** The game stays turn-based, but each turn is animated: the player and the Reaper **slide** from their old tile to the new one over about 0.2 s (5 frames of 40 ms), and the camera scrolls with the player. A key pressed during a slide finishes the slide at once and takes the next move, so the game never lags behind the keyboard *(default)*.
* **Walk cycle (player).** While sliding, the legs and arms swing and the body bobs. The player faces left or right according to the last sideways move and is drawn mirrored when facing left. Standing still, the player breathes (a slight bob) and the torch flame flickers.
* **The Reaper moves too.** It floats above the ground (a slow up-and-down hover, with a shadow beneath it). Its tattered hem flutters, its cloak leans into the direction it moves, and its scythe sways.
* **Polish.** Tiles are drawn with light and dark sides (gravestones with an "RIP" inscription and cracks, gnarled trees, shaded iron), and the HUD has a framed panel with a controls line.
* **Testable parts.** Pure helpers (`ease`, `tween`, `walk_pose`, `hover`) compute the animation; window tests check that the figures change between frames and end on the right tile. Tests turn the slide off (`animate=False`) unless they test it.

## R9 — The whole screen is lit, not just one side

* *Problem:* in rounds 1–3 only tiles within 3 of the torch were lit; the rest of the view was dark or black. Near the camera's edge this left one side of the screen bright and the rest dark.
* **Moonlight everywhere.** Every tile in the camera view is drawn clearly, in a cool, moonlit colour (never darker than 80 % brightness). There is no fog of war and no "seen tiles" memory any more, in either front end (decision 0006).
* **Torch glow.** Tiles near the player are brighter and warmer (orange-tinted), fading out over about 3 tiles. The glow moves with the player.
* **The Reaper and hazards** are drawn whenever they are in the camera view.
* **Text version:** the whole graveyard map is printed every turn.
* *Changes R1:* the fog-of-war rules of R1 are gone. Their tests were adapted to check the new light.

## R10 — Low hurdles the player can jump with the Up arrow

* **Low hurdles** (`=` fallen headstone, `C` coffin) lie on the grass. Walking into one costs no turn, like any obstacle, and the message adds a hint: *"A coffin blocks your way. Press ↑ to jump over it."* (`--text`: *"Type j to jump over it."*).
* **Facing.** The player faces the direction of their last move attempt (a bump counts). At the start they face right (east), toward the Reaper-free side *(default)*.
* **Jump** (`↑` in the window, `j` + Enter in `--text`): the player leaps over the tile in front of them and lands on the tile after it, **2 tiles in one turn**.
  * Jumpable: low hurdles, open graves and thorn bushes (a hazard jumped over does no harm).
  * The landing tile must be ground the player could walk on: not an obstacle, not another low hurdle, not a hazard.
  * If the tile in front is plain grass (or anything not jumpable), or the landing tile is not safe, nothing happens and no turn is used. The message says why: *"There is nothing here to jump over."* or *"You can't land there: a gravestone is in the way."*
  * A jump takes **one turn**; then the same checks as a move follow (R1 turn order): landing on (or leaping through) the Reaper's tile is a catch, landing on the exit wins, and otherwise the Reaper takes its one step.
* **The Reaper glides over low hurdles** (as over hazards, decision 0004). So jumping is how the player gains ground: every jump covers 2 tiles while the Reaper covers 1.
* **Window:** the player rises in an arc (about 0.6 tile high) with a shadow on the ground. A low hurdle is drawn as a cracked headstone lying flat (tags `low_hurdle`, `fallen_headstone`) or a wooden coffin with a cross (tags `low_hurdle`, `coffin`). Sound: no new tone *(default)*.
* **Logic:** `Game.jump()`, `Game.facing`, `Game.jumped` (the last turn was a jump), `Outcome.NO_JUMP` with `Game.jump_blocked` (`"nothing"` or what is in the way). `Maze.low_hurdle(pos)`; `avoid_hazards=True` paths (the player on foot) also avoid low hurdles.

## R11 — Graphics that make the game look scary

* **The Reaper** is about 1.6 tiles tall, so it towers over the player. It has a deep, empty hood around a skull with sunken sockets, **glowing red eyes with a red halo**, bony fingers around a long scythe with a curved, gleaming blade, and a tattered hem that frays into wisps of black smoke. A dark red aura pulses on the ground under it, faster as it gets closer to the player.
* **Atmosphere:** banks of pale **mist drift** slowly across the graveyard. The title screen has a full moon behind bare branches, a blood-red title with a dark shadow, and the animated Reaper.
* **Danger:** when the Reaper is 3 steps or fewer away, the red border pulses (as before) and the view edges glow red.
* Tags for tests: `reaper` (all of it), `reaper_eyes`, `reaper_glow`, `scythe`, `aura`, `mist`.

## Program structure

```
escape_game/
  __init__.py
  __main__.py    # command-line entry: options, opens the window (or the --text loop)
  maze.py        # fixed graveyard layout, obstacles, hazards, sign definitions, parsing, pathfinding (BFS)
  game.py        # Game state: player/reaper positions, move(), turn order, hazards, lives, resume, win/lose
  gui.py         # tkinter window: figures, moonlight and torch glow, signs, HUD, motion and animation, screens
  render.py      # text drawing for --text mode, and the shared status-line wording
  sound.py       # heartbeat/win/lose tones; beep function injectable for tests
tests/
  test_*.py      # pytest; every test names the requirement it checks (R1–R11)
docs/decisions/   # decision records (Y-statements), numbered 0001, 0002, ...
```

The game logic (`game.py`, `maze.py`) does no input/output, so tests can call it directly. `gui.py` only draws the game and turns key presses into `Game.move()` calls. Its lighting and camera helpers are pure functions. The window tests open hidden windows, send key presses to them, and inspect the tagged canvas items. They never play sound.

## Out of scope for this version

Multiple levels, random graveyards, moving hazards, a real-time (non-turn-based) reaper, high scores, saving.
