# Handoff — Escape the Grim Reaper, round 4

**Written afterwards (2026-11-22), not at the end of round 4.** Round 4 was done in an earlier session (2026-11-19) and no handoff was written then. This file was put together from the commits (`7a0bd88` … `3e126b0`), their messages and `spec.md` as of `3e126b0`. Anything that can't be read from those is marked *unknown*.

**This is history.** Rounds 5 and 6 replaced much of what is described here: the camera, the turn-based window, the open graveyard, the sound. For the current state read `HANDOFF-round-6.md`.

## Where things stood at the end of round 4

- **State:** round 4 (R8–R11) was implemented and committed in 5 commits, `7a0bd88` … `3e126b0`. It has since been pushed. Whether it was pushed at the end of round 4 is *unknown*.
- **Tests:** 207 passed at `3e126b0` (measured afterwards; round 3 ended with 151).
- **Requirements:** R1–R11. The two unnumbered round-4 bullets in `problem.md` got the IDs **R10** (jump with the Up arrow) and **R11** (scary graphics), as agreed with the product owner.

## How to run (as of round 4)

```
py -m escape_game          # game window, with sound
py -m escape_game --mute   # game window, no sound
py -m escape_game --text   # terminal: w/a/s/d + Enter, j + Enter to jump, r to resume, q to quit
py -m pytest
```

## What round 4 added

- **R8, motion and polish.** The game stayed turn-based, but each turn was shown as an animation:
  - Figures slide between tiles over 5 frames (jumps over 7, in an arc with a shadow), and the camera scrolls with them.
  - The player has a walk cycle, faces the way they walk, and breathes when standing.
  - Tiles are shaded: headstones with RIP and cracks, moss, gnarled trees.
  - A key pressed during a slide finishes it and takes the next move. The life-lost and ending screens wait for the slide.
  - Tests switched the animation off with `animate=False`.
- **R9, no dark side.** The torch-light fog of war was removed from both front ends (`Game.visible`, `Game.seen` and `VIEW_RADIUS` were deleted). Every tile is at least moonlit (80 %), and the torch only adds a warm tint near the player. `--text` prints the whole map every turn.
- **R10, jumping.**
  - Fallen headstones (`=`) and coffins (`C`) were added as low hurdles: they block walking, but the player can jump them, and the Reaper glides over them.
  - **Up arrow** (window) or `j` (`--text`) jumps 2 tiles forward in the facing direction; **W** still moves north.
  - Open graves and thorn bushes can be jumped too.
  - The four hurdles were placed by simulating the chase: the walking route stayed 59 moves with the Reaper exactly 4 behind, and each jump gains a step.
- **R11, scary graphics.** A 1.6-tile Reaper with a deep hood, a skull with glowing red eyes, a scythe, smoke at the hem and pulsing red rings. Drifting wisps of mist. Title and end screens with a big moon, bare branches and shadowed titles.

## Decisions made in round 4, and why

**Agreed with the product owner** (the "(round 4)" rows of the decision table in `spec.md` at `3e126b0`):
- Richer tkinter drawing, still standard library only. It was not a new graphics library.
- The whole view moonlit, with no fog of war.
- Up = jump forward, landing 2 tiles on; the other arrows and W/A/S/D move.
- New low hurdles that can be jumped; hazards can be jumped too.

**Claude's defaults:**
- 5 and 7 animation frames.
- The Reaper glides over low hurdles, as over hazards (decision 0004).
- The initial facing is right.
- The mist moves every 4th frame.
- No new sound for the jump.

## Problems found during round 4 (from the commit messages)

- **Tk on Windows ignores `stipple`,** so "translucent" glows and mist were drawn as solid discs and clouds. Since then nothing uses `stipple` (tested).
- **The window painted at about 5 frames per second.** Building the background once per turn, moving the mist less often, reconfiguring items only when they change, and timing frames brought it to about 18.
- **A key pressed while paused ended the slide without a redraw,** so GAME OVER never showed. This was fixed and tested.

## Unresolved at the end of round 4

- **Decision records 0005 and 0006** were referred to in `spec.md` but **never written**. They most likely covered the richer-tkinter choice and the removal of the fog of war. Round 5 then used the numbers 0005–0008 for its own records, and `spec.md` notes this.
- **Smoothness.** Even at about 18 fps, every turn rebuilt and scrolled the whole view. Round 5 measured a full repaint at 200–800 ms on the user's laptop and found it was the cause of the "random stops and glitch" reported as R15.
- **The sound** had still not been heard and confirmed by anyone. Round 5 removed it (R14).
- **The user's review** of the round-4 defaults is *unknown*.
