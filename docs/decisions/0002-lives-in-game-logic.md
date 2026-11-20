# 0002 — Lives are part of the game rules, with a separate CAUGHT status

- **Status:** accepted (2026-11-19, round 2)
- **Requirements:** R4, R5 (and the changed meaning of R3)

## Decision (Y-statement)

In the context of **adding three lives and a resume key to a game whose rules live in `game.py` and which has two front ends (the tkinter window and `--text`)**,
facing **the question of where lives are counted and how "lost a life, waiting for R" is represented**,
we decided for **counting lives in `Game` (`lives`, `MAX_LIVES = 3`) and adding a new `Status.CAUGHT` plus `Game.resume()`, so `Status.LOST` keeps meaning "the game is lost"**
and neglected **(a) counting lives only in the window (`gui.py`) by creating a fresh `Game` after each catch, and (b) reusing `Status.LOST` for every catch and letting each front end decide whether it is final**,
to achieve **one rule shared by both front ends, logic that is testable without a window (as `CLAUDE.md` requires), and front ends that only react to a status instead of re-implementing the rule**,
accepting that **round-1 tests which expected a single catch to be final had to be rewritten to use `Game(lives=1)`, and every front end must now handle one more status**.

## Alternatives considered

| Option | Why not |
|---|---|
| Lives only in `gui.py`, new `Game()` after each catch | Puts a game rule in the drawing code; `--text` would not get lives; a fresh `Game` would also reset the turn count and explored tiles. |
| Reuse `Status.LOST` + a lives counter | "LOST" would mean two different things; every check of `status is LOST` (sounds, screens, the text loop) would need a second condition. |

## Consequences

- `Outcome.PAUSED` (input while caught) and `Outcome.RESUMED` (R after a catch) were added.
- `Game(lives=n)` makes it easy to test the last-life case directly.
