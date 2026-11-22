# Handoff — Escape the Grim Reaper, round 5

Session date: 2026-11-21. Round 5 (R12–R15) was done in the same session as round 6, so this file was written at the end of round 6 and describes the state **at the end of round 5** (`95d9728`). For the current state read **`HANDOFF-round-6.md`**. Round 4 is in `HANDOFF-round-4.md` (written afterwards).

## Where things stood at the end of round 5

- **State:** round 5 was committed in 8 commits, `87500ff` … `95d9728`, and pushed by the user (with a push from Claude at the user's request, for the README screenshot).
- **Tests:** 256 passed (round 4 ended with 207).
- **Requirements:** R1–R15. **The user numbered R14 = "remove the sound" and R15 = "smooth flow"** in `problem.md` (commit `b37d5d1`, made during the round). Claude had used the opposite numbers. Commit `95d9728` swapped them everywhere, but the commit messages before it still carry the old numbers.

## How to run (from round 5 on)

```
py -m escape_game                 # game window, real time: hold arrows / WASD to run, ↑ to jump, R, Esc
py -m escape_game --text          # turn-based terminal version: w/a/s/d/j + Enter, r, q
py -m pytest
```

`--mute` is gone, because the game is silent (R14).

## What round 5 changed

- **R12, structure.**
  - A new 14×29 graveyard: a gravel path (`.`) in four lanes between unbroken rows of graves, ending at a gate in the south fence.
  - 14 hurdles lie across the path, 3–5 tiles apart, and must be jumped.
  - Three signed dead ends.
  - `Maze.player_route()` finds a route that walks and jumps.
- **R13, a real chase.**
  - `Game(realtime=True)` runs on a clock that the window advances with `update(ms)`.
  - The Reaper steps every 200 ms on its own, from the player's first step. The player runs at 180 ms per tile and jumps 2 tiles in 270 ms.
- **R14, no sound.** `sound.py`, every tone and `--mute` were deleted. `tests/test_silence.py` keeps it that way.
- **R15, smooth flow.**
  - Holding a key runs; cornering with two keys held; Up is remembered for 300 ms.
  - Figures glide at a constant speed.
  - The whole graveyard is drawn once (no camera); the HUD has its own canvas; the danger border is a frame colour; the mist is still during play.

## Decisions made in round 5, and why

**The user chose:**

| Decision | Instead of |
|---|---|
| Real-time chase, hold to run, Reaper a bit slower than a runner | same-speed Reaper, Reaper that speeds up over time, staying turn-based |
| A gravel path through neat rows of graves | sections with checkpoints; several levels |
| Delete the sound completely (R14) | off by default behind `--sound` |
| `--text` stays turn-based | removing `--text` |

**Claude chose, recorded and not yet reviewed by the user:**
- **0005:** the real-time rules live in `game.py` on a game clock (not window timers, not fixed ticks), so the balance is testable in milliseconds.
- **0006:** the whole graveyard is on screen and drawn once, with no camera. A full repaint takes 200–800 ms on the user's laptop; that was the round-4 stutter.
- **0007:** hurdles lie across a one-tile path and must be jumped.

**Smaller defaults Claude picked:**
- The Reaper waits for the first step.
- Cornering rules.
- Up is remembered for 300 ms.
- A bump stops the run once.
- Losing focus lets go of held keys.
- The HUD shows time, not turns.
- The torch is drawn as rings.
- 38 px tiles.
- The mist drifts only on the screens.
- The layout and its sign texts.

## Unresolved at the end of round 5

- **Smoothness (R15) only partly met.** In play the window drew about 11–13 frames per second on the user's laptop, whose CPU was held at 1.1 GHz during the measurements. The game's own work is about 9 ms per frame; the rest is Tk painting the figures. Much simpler figures would help, but trade against R8/R11. This is still open (see round 6).
- **The balance came from simulation only:** a clean run took about 15 s, and 0.5 s of hesitation at each bend still escaped.
- **The user hadn't reviewed** 0005–0007 or the defaults.

## What came right after

The user played, found a crash (fixed in `60ac88b`), said the game was still boring, and chose three improvements. Those became round 6.
