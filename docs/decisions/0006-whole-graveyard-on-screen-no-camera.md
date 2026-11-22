# 0006 — The whole graveyard is on screen, drawn once; no scrolling camera

- **Status:** accepted (2026-11-21, round 5)
- **Requirements:** R14 (smooth flow, no stops or glitches), also R9 (no dark side of the screen) and R12 (the path should read clearly)
- **Decided by:** Claude; the product owner has not reviewed this yet.

## Decision (Y-statement)

In the context of **a real-time chase (R13) that must run smoothly (R14), in a tkinter canvas where, on the development machine, a full repaint of the view takes 200–800 ms (measured), while moving only the figures over a still background takes about a tenth of that**,
facing **the round-4 camera, which followed the player, rebuilt the background on every step and scrolled it, repainting the whole view, which is what made play stop and stutter**,
we decided for **drawing the whole graveyard (29 × 14 tiles at 38 px, 1102 × 532, which fits a 1280 × 720 screen) once per window and never moving it. Each frame changes only the figures. The HUD gets its own canvas, the danger border is a frame colour, and the mist lies still during play**,
and neglected **(a) keeping the scrolling camera but making each scroll cheaper, (b) a flip-screen camera that jumps a whole screen when the player reaches an edge, and (c) rendering the background into a single image (Tk alone can't rasterise its canvas; Pillow is not allowed in the game)**,
to achieve **no full repaints at all during play, a graveyard whose structure (R12) and dead ends can be seen at a glance, and a view with no dark or hidden side (R9)**,
accepting that **tiles are smaller (38 px instead of 52), the tile art is drawn at its 52-px design size and scaled down once, the layout can't grow much beyond 29 × 14 without no longer fitting small screens, and the mist no longer drifts during play (R11). Even so, painting the detailed figures leaves frames at 75–90 ms on the throttled development laptop.**

## Alternatives considered

| Option | Pros | Cons |
|---|---|---|
| **Whole graveyard, drawn once (chosen)** | No full repaints; the path is visible end to end; simplest drawing code. | Smaller tiles; the layout size is capped by the screen. |
| Scrolling camera, made cheaper | Big tiles; the round-4 look. | Every scroll still repaints the whole view: 200–800 ms here. That is the stutter R14 complains about. |
| Flip-screen camera | Big tiles; repaints only at screen changes. | A long freeze at every screen change, in the middle of a chase. The player can't see the Reaper coming from the next screen. |
| Background as one image | Cheap repaints under the figures. | Needs Pillow or a hand-written rasteriser; Pillow is for screenshots only (CLAUDE.md). |

## Consequences

- `gui.py` no longer has `camera_at`, `camera_origin`, `in_view` or the torch tint on tiles. The torch is drawn as warm rings around the player.
- The round-4 camera tests were adapted (kept under R1/R8/R9) to check that the view is the whole graveyard and never moves.
- Screens (title, CAUGHT!, GAME OVER) hide the graveyard while they are up, so their drifting mist doesn't repaint it.
