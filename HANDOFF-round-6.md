# Handoff — Escape the Grim Reaper, round 6

Session date: 2026-11-22 (the same session as round 5). **This is the current state.** Read first: `CLAUDE.md`, `problem.md` (R1–R18), `spec.md` and `docs/decisions/0001`–`0008`. They are up to date. Rounds 4 and 5 are in `HANDOFF-round-4.md` (written afterwards) and `HANDOFF-round-5.md`. Facts in the round-1 to round-3 handoffs about the maze, the open graveyard, the camera, turn-based play in the window and sound no longer hold.

## Where things stand

- **Round 6 is done, committed and pushed.** `main` = `origin/main` = `c3c5078`; the user pushed it.
- **Uncommitted on purpose:** `HANDOFF-round-4.md`, `HANDOFF-round-5.md`, this file, and the edits to `CLAUDE.md`. The user wants to read them first.
- **Tests:** `py -m pytest` → **288 passed** in about 15–20 s (Python 3.13, pytest 9.2). Round 5 ended with 256.
- **Requirements:** R1–R18. Every one has tests named `test_R<n>_...`.
  - R16–R18 were **written into `problem.md` by Claude**, from the three improvements the user picked in chat after saying the game was still boring. The user has not reviewed that wording.
  - R14 = no sound and R15 = smooth flow, as the user numbered them.

## How to run

```
py -m escape_game                 # game window, real time: hold arrows / WASD to run, ↑ to jump, R, Esc
py -m escape_game --text          # turn-based terminal version: w/a/s/d/j + Enter, r, q
py -m escape_game --text --no-color
py -m pytest                      # window tests use hidden windows driven by advance(ms)
```

The only file the game writes is `~/.escape_grim_reaper.json` (the best time, R18), and only from `py -m escape_game`.

## What round 6 added

- **Crash fix before the round** (`60ac88b`): a remembered jump that ran out with no key held crashed the window (`IndexError` in `Game._player_act`). The user reported it; it is now fixed and has a test.
- **R16, a key and a choice of ways.**
  - The gate is locked (`Game.gate_locked`; a padlock is drawn on it). The key `K` lies 2 tiles into a yard at the second bend (7,5), with a green sign at its entrance.
  - Walking onto the key takes it (`has_key`). The key is kept after a lost life, and a new game puts it back.
  - Near the end of lane C (column 24), a shortcut leads down past a thorn bush at (11,24): 2 moves instead of 7. The long way round the bend has no hazard.
  - `Maze.escape_route()` and `Game.route_out()` give the way out by way of the key.
- **R17, the surge.** After the player has stood still or bumped for 250 ms, the Reaper steps every 180 ms instead of 220 ms. It calms after 1 s of unbroken running. In the window the aura flares and the HUD says "The Reaper quickens! Keep running!". There is no surge in `--text`.
- **R18, best time.** `escape_game/records.py` (`BestTime`) keeps the best escape in `~/.escape_grim_reaper.json`. A missing, broken or unwritable file is ignored. The HUD shows the best; the win screen shows the time, the best and **NEW BEST!**. `GameWindow(best_file=None)` (the default, used by tests) keeps it in memory only; `gui.run()` passes the home file.
- **`--text`** gets the key (a gold `K`), the locked gate and a key status line, but no surge and no saved best.
- **Balance (simulated, pinned by `tests/test_chase.py`):**

  | Run | Result |
  |---|---|
  | Clean run, shortcut | 15.6 s |
  | Clean run, long way | 16.4 s |
  | Stop 0.3 s at every bend | still escapes, Reaper 3 tiles behind |
  | Stop 0.4 s at every bend | caught in the key yard |

  In `--text`, the Reaper is never closer than 4 steps.

## Decisions made in round 6, and why

**The user chose:**
- The key in a side yard plus a shortcut beside a safe way.
- A surge when stopping or dawdling, calming after running.
- The best time in a small home-folder file.
- `--text` gets the key only.

**Claude chose, not yet reviewed by the user:**
- **0008:** where the key and the shortcut go, and the Reaper's pace eased from 200 to 220 ms. The first draft (key 4 deep, a 16-tile shortcut) was simulated and was unfair:
  - stopping 0.2 s at each bend was fatal;
  - the Reaper took the shortcut itself, which made the "safe" long way a death trap.
- **The family-plot dead end became the key yard,** so two warned dead ends remain instead of three. The R2 test was adapted.
- **Surge numbers:** 250 ms of standing starts it, 180 ms per tile while it lasts, 1 s of running calms it. Bumping counts as standing.
- **Smaller defaults:** the key is kept after a lost life; only escapes count toward the best; the best is stored in milliseconds; the HUD and sign wording; the title-story line about the key.

## Unresolved / not yet confirmed with the user

- **Smoothness (R15) is still only partly met** on the user's laptop: about 11–13 fps in play. Speed is always right, but motion looks choppy. Much simpler figures would help, but trade against R8/R11. **Ask the user** before doing that.
- **Nobody has reported on how rounds 5 and 6 play.** The balance numbers come from simulation.
- **The user hasn't reviewed** decision records 0005–0008, the defaults above, or the R16–R18 wording in `problem.md`.

## Warnings for the next session

- **The balance is pinned by tests.** Moving a hurdle, the key or the shortcut, or changing a pace constant, will break `tests/test_chase.py` (`HESITANT_MS` = 300, `CAUGHT_MS` = 400, the clean-run time) and the layout tests. That is intended.
  - Re-simulate with `run_route()` in `tests/test_chase.py`; the scratchpad scripts from this session are gone.
  - **The Reaper glides over hazards, so it uses any shortcut too:** a much longer "safe" way becomes a trap.
- **The spec's layout block must equal `maze.LAYOUT` exactly.**
- **Routes in tests go by way of the key** (`Game.route_out()`, `Maze.escape_route()`). Walking straight to the gate without the key is a bump.
- **Tag discipline in `gui.py`:**
  - `world` holds only the graveyard drawn once (tested). The key and padlock are separate (`key`, `lock`).
  - Tk keeps **one** damage rectangle per canvas, so two small changes far apart repaint everything between them. Don't add per-frame changes outside the figures.
- **Frame-time measurements on this laptop drift a lot** (the CPU throttles). Use a live `autorun` window over a full scripted run, or compare variants interleaved. A bare Tk canvas only reaches a frame every ~31 ms here.
- **Making the window topmost fires `FocusOut`, which lets go of held keys** (by design). Scripts must press keys again after that.
- **Screenshots:**
  - Use the method in `CLAUDE.md` (DPI-aware, `tk scaling` 96/72, topmost, `ImageGrab.grab(bbox=…)`).
  - Once a capture caught the user's browser instead of the game; it was deleted at once. Look at every capture.
- **Requirement IDs follow `problem.md` as the user writes them.** In a regex, `R15\b` does not match `test_R15_...`.
- **Heredoc escapes** (see `CLAUDE.md`) bit this session several times. Write edit scripts with the Write tool.
- **`git` warns "LF will be replaced by CRLF"** on every commit. This is harmless.
