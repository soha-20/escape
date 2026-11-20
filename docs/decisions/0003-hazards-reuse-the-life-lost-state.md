# 0003 — A hazard costs a life through the same paused state as a catch

- **Status:** accepted (2026-11-19, round 3)
- **Requirements:** R7 ("objects that could hurt the player"), with R4 and R5
- **Decided by:** the product owner chose "graves block, some hazards hurt (cost a life)"; Claude chose how the rules represent it. The product owner has not reviewed this yet.

## Decision (Y-statement)

In the context of **R7, where stepping on an open grave or a thorn bush costs one of the three lives that R4 introduced**,
facing **the question of how the game rules and the two front ends represent "hurt by a hazard"**,
we decided for **reusing `Status.CAUGHT` (now meaning "lost a life, waiting for R") and recording the cause in a new `Game.hurt_by` field (`"reaper"`, `"open grave"` or `"thorn bush"`), with R resuming from the start tiles exactly as after a catch**
and neglected **(a) a separate `Status.HURT` with its own resume rule, and (b) letting the player continue on the spot after a hazard, with no pause and no reset**,
to achieve **one life-losing path for both causes, so hearts, sounds, resume and GAME OVER behave the same whatever took the life; front ends that only change their wording by `hurt_by`; and the 4-step gap from decision 0001 staying true after every lost life**,
accepting that **the name `CAUGHT` is now slightly inaccurate for a hazard, every front end must look at `hurt_by` to pick the right sentence, and a hazard near the exit costs all progress, just like a late catch**.

## Alternatives considered

| Option | Pros | Cons |
|---|---|---|
| **Reuse `CAUGHT` + `hurt_by` (chosen)** | No new status for the window and `--text` loops to handle; every R4/R5 behaviour carries over and is already tested. | `CAUGHT` reads oddly for a hazard; the cause lives in a second field. |
| New `Status.HURT` | The name says exactly what happened. | Every `status is CAUGHT` check (resume, sounds, screens, the text loop) needs a second condition. That is the very problem decision 0002 avoided for `LOST`. |
| Continue on the spot, no pause | Faster, less punishing. | The player stands in a hazard while the reaper keeps coming, which is confusing. A life could vanish without the player noticing, and R4's "press R to resume" wouldn't apply. |

## Consequences

- `Game._caught()` became `Game._lose_life(cause)`. `resume()` clears `hurt_by`.
- The window titles the paused screen "HURT!" instead of "CAUGHT!" and shows the player instead of the Reaper. Both front ends take their sentences from `render.LIFE_LOST` / `render.GAME_OVER`.
- Tests: `test_R7_*` in `tests/test_game.py`, `test_render.py`, `test_cli.py` and `test_gui.py`.
