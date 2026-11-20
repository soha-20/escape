# 0001 — After a catch, resume with both figures on their start tiles

- **Status:** accepted (2026-11-19, round 2)
- **Requirement:** R4 ("3 lives ... press R to resume")
- **Decided by:** the product owner chose this option when asked; the record explains the trade-off.

## Decision (Y-statement)

In the context of **R4, where a catch costs one of three lives and R resumes the game**,
facing **the question of where the player and the Grim Reaper continue from after R**,
we decided for **putting both the player and the reaper back on their start tiles (the same 4-step gap), keeping the turn count and the explored tiles**
and neglected **(a) leaving the player where they were caught and moving only the reaper back to its start, and (b) leaving the player in place and pushing the reaper a few steps back along the path**,
to achieve **a maze that stays exactly as hard after a lost life as before, a resume that is easy to explain and to test, and keeping the round-1 difficulty tests valid (the 4-step gap that makes one hesitation survivable but a dead end fatal)**,
accepting that **a player caught near the exit loses all their progress, so a late catch feels harsher than an early one**.

## Alternatives considered

| Option | Pros | Cons |
|---|---|---|
| **Both back to start (chosen)** | Same difficulty every life; the gap is always 4; simple rule. | Progress is lost; repeating the first part of the maze. |
| Player stays, reaper back to its start | Keeps progress; very forgiving. | Near the exit the reaper would be ~40 steps away, so the last life is almost free; the chase loses its tension. |
| Player stays, reaper pushed back *n* steps | Keeps progress and some tension. | Needs a new tuning number *n*; at a dead end there may be no tile "behind" the player that isn't also between them and the exit. |

## Consequences

- `Game.resume()` resets `player` and `reaper` to `maze.player_start` / `maze.reaper_start`; `turn` and `seen` carry over.
- Remembered tiles soften the cost of a restart: the player can see where they have been.
