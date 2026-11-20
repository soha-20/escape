# Handoff — Escape the Grim Reaper, round 3

Session date: 2026-11-19. Read `CLAUDE.md`, `problem.md`, `spec.md` and `docs/decisions/` (0001–0004) first. They are up to date. `HANDOFF-round-1.md` and `HANDOFF-round-2.md` cover the earlier rounds. Their design facts about the **maze** no longer apply: the maze is gone. Their facts about rules, lives, sound and the window still hold, except where this file says otherwise.

## Where things stand

- **State:** round 3 (R6, R7) is implemented and committed on `main` in 7 commits (`f5995e5` … `efbf683`). It is **not pushed**: `main` is 7 commits ahead of `origin/main` (`653c2bf`). Ask the user before pushing.
- **Uncommitted on purpose:** this file and the round-3 edits to `CLAUDE.md`. The user wants to read and edit them first.
- **Tests:** `py -m pytest` → **151 passed** in about 8 s (Python 3.13, pytest 9.2). Round 2 had 114.
- **Requirements:** R1–R7 in `problem.md`. Each one has tests named `test_R<n>_...`. (`problem.md` writes "agrave yard" in R6. It was left as the user wrote it.)

## How to run

```
py -m escape_game          # game window, with sound
py -m escape_game --mute   # game window, no sound
py -m escape_game --text   # play in the terminal (w/a/s/d + Enter, r + Enter to resume, q to quit)
py -m pytest               # all tests; window tests open hidden tkinter windows, no real sound
```

## What round 3 added

- **R6: the graveyard.** The corridor maze was replaced by a new 17×31 layout in `maze.py` (`LAYOUT`).
  - **Shape:** two open fields (A on top, running east; B below, running west) and a south-west yard with the exit `E` at (15,6).
  - **Gate:** an iron fence between the fields has one gate at (8,28).
  - **Dead ends:** three fenced dead-end plots.
  - **Legend:** `#` iron fence, `+` gravestone, `T` dead tree, `!` signpost, `O` open grave, `*` thorn bush, space grass.
- **R7: hazards.**
  - **Blocking objects:** gravestones, fences, trees and signposts cost no turn. `Game.bumped` names the object, e.g. "A gravestone blocks your way."
  - **Hazards:** stepping on an open grave or thorn bush costs a life.
    - The turn counts, the player stays on the hazard and the reaper doesn't move.
    - With lives left, the status is `CAUGHT`; with the last life, `LOST`.
    - `Game.hurt_by` is `"reaper"`, `"open grave"` or `"thorn bush"`. It is `None` while playing.
    - R resumes from the start tiles as after a catch.
  - **The Reaper glides over hazards.**
- **New API:**
  - `maze.py`: `OBSTACLES`, `HAZARDS`, `Maze.obstacle(pos)`, `Maze.hazard(pos)`, `Maze.layout`, and `avoid_hazards=False` on `neighbours()` and `shortest_path()`.
  - `game.py`: `Game.hurt_by`, `Game.bumped`. `_caught()` was renamed `_lose_life(cause)`.
  - `render.py`: `bump_line()`, `LIFE_LOST`, `GAME_OVER` (wording by cause, shared by both front ends), `MARKS`.
- **Window (`gui.py`):** grass tiles with drawn gravestones, railings, trees, signposts, open graves, thorns and an iron exit gate.
  - **Tags:** `grass`, `grave`, `fence`, `tree`, `obstacle`, `sign`, `hazard`, `open_grave`, `thorn_bush`, `exit`. Nothing is tagged `wall` any more.
  - **Hurt screen:** a hazard shows "HURT!" (still tag `caught_title`) with the big player instead of the Reaper.
  - **Sign text:** long sign texts shrink until they fit.
- **Text version:** the new marks, with hazards in red. Signs are "Painted on a signpost in red/green".
- **README and both screenshots in `docs/`** show the graveyard now.

## Decisions made this round, and why

The user decided these two when asked:

| Decision | Why |
|---|---|
| A **new, more open** graveyard rather than re-skinning the old corridors | They wanted a real graveyard feel; they accepted that difficulty had to be re-tuned and R2 tests reworked. |
| **Graves block, some hazards hurt (cost a life)** | Chosen over: hurdles only block; bumping any hurdle costs a life (too harsh); hazards only cost a turn. |

Claude decided these; **the user has not reviewed them yet**:

- **The Reaper glides over hazards** (`docs/decisions/0004-…`). This makes detours around hazards cost time. To keep it fair, the hazards are placed so that the shortest safe route (59 moves) is as long as the shortest route through them, and the Reaper stays exactly 4 steps behind.
- **A hazard reuses `Status.CAUGHT` plus `hurt_by`** instead of a new status (`docs/decisions/0003-…`). Everything from R4/R5 carries over: hearts, sounds, resume from start, GAME OVER.
- **Layout details:**
  - three warning signs (one per plot) and two guide signs;
  - five new sign texts (only "Wanna get stuck? →" is kept);
  - seven open graves and eight thorn bushes;
  - the same start: P at (1,5), R at (1,1), 4 steps apart.
- **Turn order:**
  1. Walking into the Reaper is a catch, even if it stands on a hazard.
  2. Reaching the exit is checked before hazards.
- **Wording:** signs are on wooden signposts ("Painted on a signpost"), blocked moves name the object, and there are new intro and title-screen stories.
- **Sound:** the same sounds as a catch. No new tones.
- **Naming:** `Maze` and `is_wall()` keep their names to avoid churn. `is_wall()` now means "blocked by an obstacle".

## Unresolved / not yet confirmed with the user

- **The user hasn't reviewed the Claude-made decisions above**, including 0003 and 0004.
- **Nobody has played the graveyard.** Open questions:
  - Is 59 moves with a full restart after each lost life fun, or tedious?
  - Are the hazards readable enough at night?
  - Is "every sign is honest" still the right default?
- **No sound has ever been heard** by anyone, since round 1. Ask the user to play once with speakers on.
- **Spec defaults still unconfirmed:**
  - from rounds 1–2: one level, honest signs, being next to the Reaper is safe, torch radius 3, turn counter and seen tiles carry over a resume;
  - new in round 3: the layout size and shape, the Reaper gliding over hazards, the HURT! screen, signposts.
- **Sound is still not a requirement in `problem.md`.** Its tests are filed under R1/R4.

## Warnings for the next session

- **The layout is fragile; tests guard it.** These fail when an edit to `LAYOUT` makes the game unfair:
  - `test_R2_following_the_safe_route_keeps_the_reaper_four_steps_behind`
  - `test_R7_safe_route_never_steps_on_a_hazard`
  - `test_R2_every_dead_end_beside_the_route_is_signed`
  - `test_R6_every_patch_of_grass_can_be_reached`

  Putting a hazard on the line between two route tiles lets the Reaper close the gap. An early draft dropped it from 4 to 2 for most of the game. Simulate the chase in the scratchpad before editing the layout. The round-3 prototype script is gone.
- **`shortest_path()` crosses hazards by default** because that is the Reaper's path. Any "route", key sequence or test path for the *player* must pass `avoid_hazards=True`, or it walks into an open grave.
- **Hard-coded paths the tests rely on:**
  - From the start, `Left, Left` (`a`, `a`) is still the quick catch (`CATCH`).
  - From the start, `Right ×4` (`d` ×4) falls into the open grave at (1,9). Several R7 tests use this.
  - `FIRST_WARNING = (4, 23)` (in front of "Wanna get stuck?") and `FIRST_GUIDE = (7, 28)` appear in `test_gui.py` / `test_cli.py`.
  - Moving the start, the first grave or those signposts breaks them.
- **Front ends must word lost lives by `game.hurt_by`.** Use `render.LIFE_LOST` / `render.GAME_OVER`, never a hard-coded "The Reaper's cold hand…". The window draws the Reaper on the map only if it is in the torch light or `hurt_by == "reaper"`.
- **HUD space:**
  - **Signs:** sign banners shrink to fit (down to 10 pt). A sign text much longer than about 40 characters will look small, so keep new texts short.
  - **Hearts:** the round-2 warning about `MAX_LIVES` and HUD width still applies.
- **Two new symbols print as `?` when piped:** the thorn bush is `*`, which is fine, but the sign arrows `← ↓ →` still print as `?`. Set `PYTHONIOENCODING=utf-8` to see them.
- **Window tests now take about 8 s.** Each redraw draws grass tufts and per-object shapes, so there are more canvas items per tile than before. That's fine at this size. Don't grow the view without checking speed.
- **Line endings:** git warns "LF will be replaced by CRLF" for files written from bash or Python. This is harmless.
