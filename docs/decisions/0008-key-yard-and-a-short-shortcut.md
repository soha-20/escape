# 0008 — The key lies in a short yard on the way; the shortcut saves only a few tiles

- **Status:** accepted (2026-11-22, round 6)
- **Requirements:** R16 (a key to fetch and a choice of ways), R17 (the surge), R13 (the chase must stay fair)
- **Decided by:** the product owner chose "key in a side yard + a shortcut full of hazards beside a longer, safer way". Claude chose where they go and how big they are (this record), after simulating the chase; the product owner has not reviewed it yet.

## Decision (Y-statement)

In the context of **a real-time chase where the Reaper follows the shortest way to the player and glides over every hazard (decision 0004), on the one-tile path of round 5 (decision 0007)**,
facing **two problems found by simulating the first draft: (1) a key 4 tiles deep in a side yard meant running back toward the Reaper for 8 moves, so stopping just 0.2 s at each bend got the player caught; and (2) a shortcut that skipped 16 tiles made the "safe" long way a death trap, because the Reaper took the shortcut itself and cut the player off (caught on the long way with only 0.1 s of hesitation)**,
we decided for **a key 2 tiles into the old family plot at the second bend (gate key detour of 4 moves), a shortcut near the end of lane C that saves only 5 moves (2 against 7, about 0.8 s) past one thorn bush, and the Reaper's normal pace eased from 200 to 220 ms per tile, with the R17 surge at 180 ms**,
and neglected **(a) the key at the back of the crypt yard beside the gate (a long detour at the very end), (b) a big shortcut between lanes, (c) making the Reaper unable to use the shortcut (a new rule for it), and (d) keeping the 200 ms pace**,
to achieve **a choice that is real both ways (shortcut 15.6 s with a leap over thorns that costs a life if missed; long way 16.4 s with no hazard, both survivable), a key detour that is tense but fair (stopping 0.3 s at every bend still escapes; 0.4 s is caught in the key yard), and in `--text` a Reaper that is still never closer than 4 steps**,
accepting that **one of the three warned dead ends became the key yard (two warnings remain, and the R2 test was adapted), the layout tests now have to tell the long way (a loop) from a dead end, and the balance numbers depend on the pace constants and are pinned by `tests/test_chase.py`**.

## Alternatives considered

| Option | Pros | Cons |
|---|---|---|
| **Key 2 deep at the second bend; small shortcut; 220 ms pace (chosen)** | Simulated fair; both ways viable; the key detour comes mid-run, when the gap tells whether the player has been quick. | One fewer warned dead end. |
| Key at the back of the crypt yard by the gate | Dramatic finish. | A long run back toward the Reaper at the very end: either too easy (big lead) or certain death. |
| Big shortcut between lanes (16 tiles) | Very tempting. | The Reaper uses it too, so the long way loses outright: no real choice. |
| The Reaper may not use the shortcut | Keeps a big shortcut. | A new rule, and a way to trap the Reaper; it breaks decision 0004's "Death glides over everything". |
| Keep the 200 ms pace | No change to R13's numbers. | With the key detour and the surge, stopping 0.2 s at a bend was fatal; too harsh. |

## Consequences

- `REAPER_STEP_MS` = 220, `REAPER_SURGE_MS` = 180, `SURGE_AFTER_IDLE_MS` = 250, `CALM_AFTER_RUN_MS` = 1000 in `game.py`.
- The simulation used for this is `tests/test_chase.py::run_route` (hesitating at every bend), so a change to the layout or the constants shows up as a failing R13/R17 test.
