# Escape the Grim Reaper

A short, tense escape game you play right in your terminal.

You wake up in a dark maze and the Grim Reaper is four steps behind you. Every move you make, it makes one too. Find the exit (`E`) before it catches you.

- **The maze is dark.** You can only see 3 tiles around you.
- **Read the walls.** At every fork a sign (`!`) is scrawled on the wall. Red signs warn you away from dead ends (*"Wanna get stuck?"*). Green signs point toward freedom. One wrong turn into a dead end and the Reaper has you.
- **Listen.** A heartbeat plays every turn and gets faster and higher as the Reaper closes in.
- **Get caught and it's GAME OVER.**

```
  #######!#
    ...@...        @  you
  #######.#        R  the Grim Reaper
  #######.#        !  a sign on the wall
                   E  the exit

Turn 2   Something cold breathes down your neck... (4 steps away)
Move: w/a/s/d + Enter    Quit: q
```

## Requirements

- Python 3.10 or newer (no extra packages needed to play)
- Sound uses `winsound` on Windows. Other systems get the terminal bell.

## Run the game

```
py -m escape_game
```

Options:

| Option | Effect |
|---|---|
| `--mute` | play without sound |
| `--no-color` | plain text, for terminals without colour support |

Controls: type `w` (up), `a` (left), `s` (down) or `d` (right) and press Enter. Type `q` to give up. Bumping into a wall or mistyping doesn't cost you a turn.

## Run the tests

```
py -m pip install pytest   # once
py -m pytest
```

Every test is named after the requirement it checks (`test_R1_...`, `test_R2_...`, `test_R3_...`). See `problem.md` for the requirements and `spec.md` for how the game meets them.

## Project layout

```
escape_game/
  __main__.py   command-line entry point and input loop
  maze.py       the fixed maze, wall signs, shortest-path search
  game.py       turn order, reaper chase, win/lose rules
  render.py     what the player sees (fog of war, colours, messages)
  sound.py      heartbeat and win/lose tones
tests/          pytest tests, one or more per requirement
```
