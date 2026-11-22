# 0007 — Hurdles lie across a one-tile-wide path and must be jumped

- **Status:** accepted (2026-11-21, round 5)
- **Requirements:** R12 (structure and flow, not scattered graves), R10 (jumping), R7 (hazards), R2 (signs and dead ends)
- **Decided by:** the product owner chose "a clear path through neat rows of graves, with hurdles and hazards on or beside the path". Claude chose to make the path one tile wide with the hurdles across it (this record); the product owner has not reviewed it yet.

## Decision (Y-statement)

In the context of **a graveyard that should have structure and flow (R12) rather than graves scattered over open fields, with jumpable hurdles (R10) and hazards (R7)**,
facing **the question of whether the hurdles on the path can be walked around, or must be leapt**,
we decided for **a gravel path one tile wide, in four lanes between unbroken rows of graves, with 14 hurdles lying across it 3–5 tiles apart, so every one must be jumped. The player's route (`Maze.player_route`) is a mix of steps and jumps, and the layout tests use it**,
and neglected **(a) a path two tiles wide with hurdles that can be walked around, (b) hurdles beside the path as optional shortcuts (the round-4 design), and (c) open graveyard sections with a path drawn only as a hint**,
to achieve **a clear rhythm (run, leap, run, leap, turn) like a runner game, a route that can't be mistaken, a Reaper that follows the same lane (it glides over hurdles but not through grave rows), and dead ends that are side paths with a signpost at each**,
accepting that **there is no longer a "safe route on foot": several round-3/4 tests that walked around hazards had to be adapted to a route that jumps; mistiming a jump over an open grave or thorns costs a life; and in `--text`, where each jump gains a step, the chase is easier than in the window**.

## Alternatives considered

| Option | Pros | Cons |
|---|---|---|
| **One-tile path, hurdles across it (chosen)** | Strong rhythm; obvious route; the Reaper can't cut corners. | Missing a jump is punished; looks a little like corridors (but the rows of graves read as a cemetery). |
| Two-tile path, hurdles avoidable | Forgiving. | Jumping becomes optional; the flow R12 asks for is weaker; the Reaper can weave past the player. |
| Hurdles beside the path as shortcuts (round 4) | Keeps round-4 tests. | The player found that design random. |
| Open sections with a drawn path | Most "graveyard"-like. | Structure only on paper; the Reaper cuts across open ground. |

## Consequences

- `tests/test_maze.py` checks the rhythm: every hurdle is jumped, 3–5 tiles apart, never at a bend, every grave stands in a row, and the path forks only at warning signs.
- In the window the player gets help to hit the jumps: an Up pressed up to 300 ms early is remembered (R10, R14).
