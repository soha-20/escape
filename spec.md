# Escape Game — Specification

This document describes how the program meets each requirement in `problem.md`.

## Decisions agreed with the product owner

| Topic | Decision |
|---|---|
| Language | Python 3 (3.10+), standard library only (tkinter for graphics) |
| Interface | A **graphical game window** (tkinter) launched from the terminal with drawn figures for the player and the Grim Reaper. A plain terminal version is kept behind `--text`. |
| Pace | Turn-based: the reaper moves only when the player moves |
| Maze | One fixed, hand-designed maze (the game is meant to be short) |
| Reaper speed | The reaper moves one step after every player move |
| Tension | Visible chase plus a heartbeat **sound** that speeds up as the reaper closes in |

*Revision (2026-11-18):* the first version drew the game as text in the terminal. The product owner found it unattractive: no real figures, and the colours didn't show. They chose a tkinter window over a terminal-only game, even though `problem.md` mentions the terminal. The game is still started from the terminal, and the terminal version is still available.

Where `problem.md` and the answers above left a detail open, this spec picks a default, marked *(default)*. Each one can be changed.

## Overview

The player wakes up in a dark maze, carrying a torch, and the Grim Reaper is close behind. The player must reach the exit door before the reaper reaches them. Signs on the walls at each fork warn the player away from dead ends or point the way to freedom.

### The maze

```
#########!##########!######
#R   P         ##        ##
######### ####### ## ### ##
######### ####### ## ### ##
######### ###!### ## ### ##
#########         ## ### ##
############# ########## ##
############# ####       !#
############# ########## ##
############# #E         ##
###########################
```

* Size: 11 rows × 27 columns. `#` is a wall, a space is floor, `!` is a wall carrying a sign.
* The player starts at `P`, the reaper at `R`, which is **4 steps** behind along the corridor.
* The shortest route to `E` is 44 moves long and passes through **4 forks**. Each fork has one wrong branch that ends in a dead end 4–6 tiles deep.
* Because the reaper is exactly as fast as the player, walking the correct route keeps the 4-step gap. Each step into a wrong branch and back costs 2 steps of that gap. Walking to the end of any dead end gets the player caught. One hesitation is survivable, but a real wrong turn is fatal.

## R1 — The game starts and the player must escape from the Grim Reaper

* **Start.** `py -m escape_game` opens the game window on a title screen. The screen shows "ESCAPE THE GRIM REAPER", a large drawn Reaper and the player, a moonlit graveyard and a short story. Any key starts the chase.
* **Figures.** Both characters are drawn from shapes, not letters:
  * **Player:** an adventurer in a blue tunic holding a torch whose flame flickers.
  * **Grim Reaper:** a black hooded cloak, a skull face with glowing red eyes that pulse, a bony hand and a scythe.
* **Controls.** Arrow keys or `W`/`A`/`S`/`D` move with a **single keypress**. `Esc` closes the game. After a game ends, `R` plays again *(default)*.
* **Turn order.**
  1. The player moves one tile.
  2. If the player is now on the exit, the player **wins**. The reaper does not move after that.
  3. Otherwise the reaper moves one tile along a shortest path to the player (breadth-first search through floor tiles; ties are broken in a fixed order so the game is deterministic).
  4. The game checks whether the player has been caught (see R3).
* **Turns that don't count.** Moving into a wall doesn't use a turn. The reaper doesn't move, and the message "A cold stone wall blocks your way." appears *(default)*. Other keys are ignored.
* **Display.**
  * **Camera:** a 15 × 9-tile view (52 px tiles) that follows the player and never shows anything outside the maze.
  * **Torch light (fog of war):** tiles within 3 of the player are lit, brightest next to the torch and fading with distance. Tiles seen earlier stay faintly visible. Tiles never seen are pitch black, so the player has to rely on the signs *(default)*.
  * **Walls:** stone bricks. **Floor:** flagstones. **Exit:** a wooden door with a green glow and the label "EXIT".
  * **The reaper** is drawn only when it is inside the torch light.
  * **Status panel (HUD):** the turn number, a heart that beats faster as the reaper approaches, and a status line ("Distant footsteps…" in grey, "Something cold breathes down your neck…" in orange, "RUN! The Reaper is right behind you!" in red).
  * **Danger:** when the reaper is 3 steps or fewer away, a red border flashes around the view.
* **Sound (tension).** After each turn the game plays a heartbeat based on the reaper's distance (shortest-path steps):
  * 6 or more steps: one slow, low beat
  * 4–5 steps: two beats
  * 3 steps or fewer: three fast, high beats

  The game also plays a falling tone when the player is caught and a rising tone when the player escapes.
  * On Windows sound uses `winsound.Beep`. Elsewhere it falls back to the terminal bell (`\a`).
  * In the window, sounds play on a background thread so the window never freezes.
  * `--mute` turns sound off. If sound fails, the game keeps running silently.
* **Win.** Reaching the exit shows a "YOU ESCAPED!" screen with the turn count.
* **Fallback.** If the window can't open (no tkinter, no display), the program says so and starts the terminal version instead.
* **Terminal version (`--text`).** This is the original text version:
  * It draws the maze with `@`, `R`, `E`, `#` and `!`, using ANSI colours (`--no-color` for plain text).
  * Each move is `w`/`a`/`s`/`d` + Enter, and `q` quits.
  * Unknown commands cost no turn.
  * It ignores the BOM (byte-order mark) that Windows PowerShell adds to piped input.

## R2 — Maze hurdles with hints and signs telling which way to go

* The maze is the fixed layout described above, stored as text in `escape_game/maze.py`.
* **Signs** sit on wall tiles next to each of the 4 forks. In the window they are drawn as parchment plaques with a glowing red or green border and `!`. A sign's message appears when the player stands on a floor tile orthogonally next to it, shown in large text in the HUD.
* There are two kinds of sign, and every sign is honest *(default)*:
  * **Warning (red, ⚠):** marks the wrong branch, e.g. *"Wanna get stuck? →"* (the example in problem.md) at the first fork, pointing to the dead end.
  * **Guide (green, ✔):** points toward the exit, e.g. *"The air smells of freedom →"*.
* **Validity checks (tested):** the exit is reachable from the start; every fork on the solution path has a sign next to it; each warning sign is next to the entrance of a dead-end branch; following the guidance wins; walking to the end of any wrong branch gets the player caught.

## R3 — The player loses once the Grim Reaper catches them

* The player is **caught** when the player and the reaper are on the same tile *(default: being next to the reaper is still safe)*. This happens if:
  * the reaper steps onto the player's tile, or
  * the player steps onto the reaper's tile (walking back into it).
* When caught, the window shows a "GAME OVER" screen under a blood-red moon, with a large Reaper and the line "The Reaper's hand closes on your shoulder." The falling tone plays.
* Once the game is over, movement keys are ignored. Only `R` (play again) and `Esc` (quit) work.

## Program structure

```
escape_game/
  __init__.py
  __main__.py    # command-line entry: options, opens the window (or the --text loop)
  maze.py        # fixed maze layout, sign definitions, parsing, pathfinding (BFS)
  game.py        # Game state: player/reaper positions, move(), turn order, win/lose
  gui.py         # tkinter window: figures, torch light, signs, HUD, animation, screens
  render.py      # text drawing for --text mode, and the shared status-line wording
  sound.py       # heartbeat/win/lose tones; beep function injectable for tests
tests/
  test_*.py      # pytest; every test names the requirement it checks (R1/R2/R3)
```

The game logic (`game.py`, `maze.py`) does no input/output, so tests can call it directly. `gui.py` only draws the game and turns key presses into `Game.move()` calls. Its lighting and camera helpers are pure functions. The window tests open hidden windows, send key presses to them, and inspect the tagged canvas items. They never play sound.

## Out of scope for this version

Multiple levels, random mazes, a real-time (non-turn-based) reaper, high scores, saving.
