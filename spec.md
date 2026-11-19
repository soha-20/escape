# Escape Game — Specification

This document describes how the program meets each requirement in `problem.md`.

## Decisions agreed with the product owner

| Topic | Decision |
|---|---|
| Language | Python 3 (3.10+), standard library only |
| Interface | Terminal, turn-based: the player types a command and presses Enter |
| Maze | One fixed, hand-designed maze (the game is meant to be short) |
| Reaper speed | The reaper moves one step after every player move |
| Tension | Visible chase plus a heartbeat **sound** that speeds up as the reaper closes in |

Where `problem.md` and the answers above left a detail open, this spec picks a default, marked *(default)*. Each one can be changed.

## Overview

The player (`@`) wakes up in a dark maze and the Grim Reaper (`R`) is close behind. The player must reach the exit (`E`) before the reaper reaches them. Signs on the walls (`!`) at each fork warn the player away from dead ends or point the way to freedom.

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

* Size: 11 rows × 27 columns. `#` is a wall, a space is floor.
* The player starts at `P`, the reaper at `R`, which is **4 steps** behind along the corridor.
* The shortest route to `E` is 44 moves long and passes through **4 forks**. Each fork has one wrong branch that ends in a dead end 4–6 tiles deep.
* Because the reaper is exactly as fast as the player, walking the correct route keeps the 4-step gap. Each step into a wrong branch and back costs 2 steps of that gap. Walking to the end of any dead end gets the player caught. This is where the rushed feeling comes from: one hesitation is survivable, but a real wrong turn is fatal.

## R1 — The game starts and the player must escape from the Grim Reaper

* **Start.** `py -m escape_game` prints a short intro: "You wake in the dark. Something cold breathes behind you…". It then shows the first frame of the maze.
* **Controls.** `w` / `a` / `s` / `d` move up / left / down / right. `q` quits. Input is case-insensitive and ignores surrounding whitespace.
* **Turn order.**
  1. The player moves one tile.
  2. If the player is now on `E`, the player **wins** ("You escaped the Reaper in N turns."). The reaper does not move after that.
  3. Otherwise the reaper moves one tile along a shortest path to the player (breadth-first search through floor tiles; ties are broken in a fixed order so the game is deterministic).
  4. The game checks whether the player has been caught (see R3).
* **Turns that don't count.** Moving into a wall, or typing an unknown command, doesn't use a turn. The reaper does not move, and the player sees a message such as "A cold stone wall." *(default)*
* **Display.** Each turn the screen is cleared and redrawn. It shows:
  * The maze around the player within a view radius of **3 tiles** (fog of war), so the player can't see the whole solution and has to rely on the signs *(default)*. Tiles seen earlier stay drawn dimly.
  * The reaper, if it is within view.
  * A status line: the turn number and how close the reaper is ("The Reaper is 4 steps behind you…").
* **Sound (tension).** After each turn the game plays a heartbeat based on the reaper's distance (shortest-path steps):
  * 6 or more steps: one slow, low beat
  * 4–5 steps: two beats
  * 3 steps or fewer: three fast, high beats

  The game also plays a falling tone when the player is caught and a rising tone when the player escapes. On Windows sound uses `winsound.Beep`. Elsewhere it falls back to the terminal bell (`\a`). `--mute` turns sound off. If sound fails, the game keeps running silently. The sound code is kept apart from the game logic so tests can check which tones would play without making any noise.
* **Win.** Reaching `E` ends the game with a victory message and the turn count, and the program exits with code 0.
* **Quit.** `q` ends the game with "You gave up. The Reaper is patient." and the program exits with code 0.

## R2 — Maze hurdles with hints and signs telling which way to go

* The maze is the fixed layout described above, stored as text in `escape_game/maze.py`.
* **Signs** sit on wall tiles next to each of the 4 forks and are drawn as `!`. A sign's message appears when the player stands on a floor tile orthogonally next to it.
* There are two kinds of sign, and every sign is honest *(default)*:
  * **Warning (red text):** marks the wrong branch, e.g. *"Wanna get stuck?"* (the example in problem.md) at the first fork, pointing to the dead end.
  * **Guide (green text):** points toward the exit, e.g. *"The air smells of freedom ↓"*.
* Colours use ANSI escape codes. On Windows the program enables virtual-terminal processing at startup so colours work in PowerShell and cmd.
* **Validity checks (tested):** the exit is reachable from the start; every fork on the solution path has a sign next to it; each warning sign is next to the entrance of a dead-end branch; following the guidance wins; walking to the end of any wrong branch gets the player caught.

## R3 — The player loses once the Grim Reaper catches them

* The player is **caught** when the player and the reaper are on the same tile *(default: being next to the reaper is still safe)*. This happens if:
  * the reaper steps onto the player's tile, or
  * the player steps onto the reaper's tile (walking back into it).
* When caught, the screen shows "The Reaper's hand closes on your shoulder. GAME OVER." and the falling tone plays. The program exits with code 0. There is no replay prompt *(default)*; the player runs the command again to play again.
* Once the game is over, no further moves are accepted.

## Program structure

```
escape_game/
  __init__.py
  __main__.py    # command-line entry: argument parsing, input loop
  maze.py        # fixed maze layout, sign definitions, parsing, pathfinding (BFS)
  game.py        # Game state: player/reaper positions, move(), turn order, win/lose
  render.py      # turns game state into text: fog of war, colours, status line, sign messages
  sound.py       # heartbeat/win/lose tones; beep function injectable for tests
tests/
  test_*.py      # pytest; every test names the requirement it checks (R1/R2/R3)
```

The game logic (`game.py`, `maze.py`) does no input/output, so tests can call it directly. `__main__.py` reads input, calls `Game.move()`, renders, and plays sounds. It takes its input and output streams as parameters, so tests can feed scripted moves through it.

## Out of scope for this version

Multiple levels, random mazes, a real-time (non-turn-based) reaper, high scores, saving.
