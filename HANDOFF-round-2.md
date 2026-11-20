# Handoff — Escape the Grim Reaper, round 2

Session date: 2026-11-19. Read `CLAUDE.md`, `problem.md`, `spec.md` and `docs/decisions/` first. They are up to date. `HANDOFF-round-1.md` covers round 1. Its design facts still hold, except where this file says otherwise.

## Where things stand

- **State:** round 2 (R4, R5) is implemented and committed on `main` in 5 commits (`044b741` … `a786240`). It is **not pushed**: `main` is 5 commits ahead of `origin/main` (`2efc722`). Ask the user before pushing.
- **Uncommitted on purpose:** this file and the round-2 edits to `CLAUDE.md`. The user wanted to read and edit them before committing.
- **Tests:** `py -m pytest` → **114 passed** in about 5 s (Python 3.13, pytest 9.2). Round 1 had 85.
- **Requirements:** R1–R5 in `problem.md`. Each one has tests named `test_R<n>_...`.

## How to run

```
py -m escape_game          # game window, with sound
py -m escape_game --mute   # game window, no sound
py -m escape_game --text   # play in the terminal (w/a/s/d + Enter, r + Enter to resume, q to quit)
py -m pytest               # all tests; window tests open hidden tkinter windows, no real sound
```

## What round 2 added

- **R4, three lives.**
  - A catch costs one life. With lives left, the game goes to `Status.CAUGHT` and both figures stay on the catch tile.
  - **R** (`r` + Enter in `--text`) calls `Game.resume()`. Player and reaper go back to their start tiles, the same 4 steps apart.
  - The last catch gives `Status.LOST` (GAME OVER). In the window, R then starts a fresh game with 3 lives.
- **R5, hearts.**
  - Window HUD: three hearts at the left. Red ♥ (tag `heart`) means a life left, and these beat with the heartbeat. Grey ♡ (tag `heart_lost`, colour `HEART_LOST`) means a life lost. Hearts empty from the right.
  - The CAUGHT! and GAME OVER screens show the same row, large (tags `big_heart` / `big_heart_lost`).
  - `--text` shows `Lives: ♥ ♥ ♡` (`render.lives_line`).
- **New API:**
  - `game.py`: `MAX_LIVES`, `Game(maze=None, lives=MAX_LIVES)`, `Game.lives`, `Game.resume()`, `Status.CAUGHT`, `Outcome.PAUSED` (input while caught) and `Outcome.RESUMED`.
  - `sound.py`: `LIFE_LOST_TONES`, `Sound.life_lost()`.
  - `gui.py`: `GameWindow.CAUGHT` state, caught-title tag `caught_title`.
- **README** now explains lives and the R key.

## Decisions made this round, and why

The user decided these four when asked:

| Decision | Why |
|---|---|
| Resume puts **both** player and reaper back on their start tiles | Keeps the maze exactly as hard on every life and keeps the round-1 difficulty tests valid. The alternatives (player keeps progress) made the last life nearly free. See `docs/decisions/0001-resume-from-start.md`. |
| R after GAME OVER = new game with 3 lives | Same as round 1's "play again". |
| Lost hearts become grey empty ♡, not removed | The player sees how many lives they started with. |
| Lives also apply to `--text` | Both front ends share one rule. |

Claude decided these; the user hasn't reviewed them yet:

- **Lives live in `game.py`**, with a separate `CAUGHT` status. Counting them only in the GUI was the other option. This keeps rules testable and shared, and `LOST` keeps meaning "game lost". See `docs/decisions/0002-lives-in-game-logic.md`.
- **What carries over a resume:** the turn counter keeps counting (the win screen shows total turns), and explored tiles stay remembered.
- **New sound:** losing a life plays a short two-note drop (440 → 220 Hz). The long falling tone is kept for the final GAME OVER.
- **New window screen:** a "CAUGHT!" screen with an orange title, dim red moon, big Reaper, big hearts, "(N lives left)" and "Press R to resume". The GAME OVER Reaper is now drawn smaller and lower (scale 5 at y=375) to make room for the hearts.
- **Keys:**
  - R while playing does nothing and costs no turn.
  - While caught, Esc / `q` still quit.
  - In `--text`, any other key while caught prints "Type r to resume".

## Unresolved / not yet confirmed with the user

- **No sound has been heard by anyone yet**, including the new life-lost tone. The round-1 item still stands: ask the user to play once with speakers on.
- **Difficulty with lives is untested on a real player.** Three lives with a full restart might now feel easy, or tedious because the first corridor repeats.
- **Round-1 spec defaults still unconfirmed:** one level, all signs honest, adjacent-to-reaper is safe, wall bumps are free, torch radius 3.
- **Sound is still not a requirement in `problem.md`.** Sound tests are filed under R1; the life-lost sound test is under R4.
- **The README screenshots in `docs/` are from round 1** and don't show the three hearts. Retake them if the user wants them current.

## Warnings for the next session

- **Old R3 tests were adapted, not deleted.** Tests that expected one catch to end the game now use `Game(lives=1)`. The window and CLI R3 tests now get caught three times (`lose_all_lives()` in `test_gui.py`, `CATCH` in `test_cli.py`). If R4 changes again, these tests change with it.
- **The quick-catch path:**
  - From the start tiles, two steps left (`a`, `a` / `Left`, `Left`) gets the player caught. Tests rely on this; changing the maze start or the 4-step gap breaks them.
  - A **third** `Left` while caught is ignored. The screenshot script relied on that.
- **Every front end must handle `Status.CAUGHT`.** A loop written as `while status is PLAYING` would quit at the first catch; the `--text` loop uses `status in (PLAYING, CAUGHT)`.
- **HUD space:** the three hearts take the left ~150 px of the 780 px HUD, and the turn/status text starts at `30 + HEART_GAP * MAX_LIVES`. A larger `MAX_LIVES` would push the long status line ("Something cold breathes down your neck… (N steps away)") toward the right edge. Re-screenshot after any change.
- **Heart symbols and code pages:** ♥/♡ print as `?` when `--text` output is piped (cp1252 code page). The sign arrows from round 1 do the same, and a real console shows them. To see them while piping, set `PYTHONIOENCODING=utf-8`.
- **Screenshots:** the round-2 script lived in the session scratchpad and is gone.
  - Rebuild it: open `GameWindow(root, <silent fake sound>, threaded_sound=False)` and drive it with `win.on_key(...)`. Grab the full screen with `PIL.ImageGrab` (Pillow 12.3 is installed), scale by `image.width / root.winfo_screenwidth()`, and crop to the window.
  - Pillow is only for screenshots, never a game dependency.
- **Line endings:** git warns "LF will be replaced by CRLF" on files written from the bash shell. This is harmless; don't "fix" it with a mass rewrite.
