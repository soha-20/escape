# 0005 — The real-time chase runs on a game clock inside the rules, not on window timers

- **Status:** accepted (2026-11-21, round 5)
- **Requirements:** R13 (the Reaper really chases), R15 (smooth flow), R10 (the jump)
- **Decided by:** the product owner chose a real-time chase with hold-to-run, with `--text` staying turn-based. Claude chose how to build it (this record); the product owner has not reviewed it yet.

## Decision (Y-statement)

In the context of **making the game window real-time, so the Reaper moves on its own and a held key keeps the player running (R13, R15), while the `--text` game stays turn-based and CLAUDE.md requires the game logic to be free of input/output and testable directly**,
facing **the question of where time lives: who decides when the player and the Reaper step**,
we decided for **a clock inside `Game` that the window advances (`Game(realtime=True)`, `update(ms)`, with `press`/`release`/`press_jump` for the keys). Player actions and Reaper steps happen in time order inside `update`, and `Game` records each figure's last motion (from, when, how long) for drawing**,
and neglected **(a) separate `root.after` timers in the window for the Reaper and the player, calling `move()`, and (b) a fixed-tick simulation (the rules step every N ms and the window interpolates between ticks)**,
to achieve **rules that are exact and testable without a window: a whole chase runs in milliseconds in a test, so the balance (a clean run wins, half a second of hesitation at every bend still wins, 0.6 s is caught) is checked by tests. The window also can't change the rules by being slow: a frame advances the clock by the real time passed, at most 100 ms**,
accepting that **`Game` now has two modes (turn-based for `--text`, real-time for the window), with a little more state (held keys, a remembered jump, the Reaper's next step time) that only the real-time mode uses**.

## Alternatives considered

| Option | Pros | Cons |
|---|---|---|
| **Clock in `Game`, advanced by the window (chosen)** | Deterministic; tests drive time; one source of truth for pace, cornering and the remembered jump; the window only draws. | Two modes in one class. |
| Window timers (`after`) call `move()` and a Reaper step | Least code to write. | Timing rules (pace, key repeat, cornering, jump buffer) would live in `gui.py`, which can only be tested through a real window and real time. A slow frame would slow the game down. |
| Fixed-tick simulation (e.g. 20 ms ticks) | Common in games. | Pace values must be multiples of the tick. Tests would step thousands of ticks. Exact event times are lost to rounding. |

## Consequences

- `PLAYER_STEP_MS` (180), `JUMP_MS` (270), `REAPER_STEP_MS` (200) and `JUMP_BUFFER_MS` (300) are in `game.py`, and `tests/test_chase.py` checks the balance with them.
- The Reaper waits for the player's first step, at the start and after every resume, so nobody is caught before touching the keys.
- `--text` calls `move()`/`jump()` as before; `update()` does nothing there.
