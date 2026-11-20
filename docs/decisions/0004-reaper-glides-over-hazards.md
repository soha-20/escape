# 0004 — The Reaper glides over hazards; the layout makes that fair

- **Status:** accepted (2026-11-19, round 3)
- **Requirements:** R7 (hazards), R6 (the graveyard layout), R2 (difficulty of following the signs)
- **Decided by:** Claude; the product owner has not reviewed this yet.

## Decision (Y-statement)

In the context of **a graveyard with open graves and thorn bushes that hurt the player (R7), and a Reaper exactly as fast as the player that follows a shortest path**,
facing **the question of whether the hazards also affect the Reaper's movement**,
we decided for **letting the Reaper glide over hazards unharmed (its pathfinding treats them as open ground), and placing the hazards so that the shortest hazard-free route is exactly as long as the shortest route through them**
and neglected **(a) treating hazards as blocking for the Reaper (it walks around them like the player), and (b) letting hazards hurt or slow the Reaper too**,
to achieve **a Reaper that feels unstoppable (Death does not fall into graves), hazards that matter because any detour around them lets the Reaper gain two steps, and a safe route on which the Reaper still stays exactly 4 steps behind, so the round-1 difficulty rule ("one hesitation is survivable, a dead end is fatal") still holds**,
accepting that **the layout is harder to change: moving one hazard onto the route can silently make the game unfair, so tests guard it (`test_R2_following_the_safe_route_keeps_the_reaper_four_steps_behind`, `test_R7_safe_route_never_steps_on_a_hazard`)**.

## Alternatives considered

| Option | Pros | Cons |
|---|---|---|
| **Reaper glides over hazards (chosen)** | Thematic; detours really cost time; no new rule for the Reaper. | The layout must be tuned. An early draft let the Reaper close the gap from 4 to 2 for most of the game, because the route had to walk around thorns the Reaper crossed. |
| Hazards block the Reaper too | Gap stays 4 automatically, whatever the layout. | Hazards become just more walls for the Reaper. Nothing about them creates tension except the life they cost. |
| Hazards hurt or slow the Reaper | Could be used as traps by the player. | A new rule nobody asked for. It makes the Reaper beatable by luring it, and changes the chase from "escape" to "trap". |

## Consequences

- `Maze.neighbours()` and `Maze.shortest_path()` take `avoid_hazards`. The Reaper uses the default (`False`). The tests and the "safe route" use `True`.
- The graveyard layout was tuned in a prototype so the safe route (59 moves) and the unsafe one are equally long.
