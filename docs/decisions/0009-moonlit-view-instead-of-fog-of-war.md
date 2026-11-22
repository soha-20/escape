# 0009 — The whole view is moonlit; the torch-light fog of war is removed

- **Status:** accepted (2026-11-19, round 4). **Written afterwards (2026-11-22).** No decision record was written during round 4. This one was put together from commit `28020c3`, `spec.md` as of `3e126b0`, and `HANDOFF-round-4.md`.
- **Requirements:** R9 (the screen is bright on one side only and dark everywhere else). It also changes what R1, R4 and R7 meant by "visible".
- **Decided by:** the product owner chose "the whole view moonlit, no fog of war" (the "Lighting (round 4)" row of the decision table in `spec.md`). Claude chose the 80 % moonlight level and kept the torch as a warm tint only.

## Decision (Y-statement)

In the context of **a graveyard where the player saw only the tiles within 3 of the torch (`VIEW_RADIUS = 3`), with the rest of the screen dark or black, which the player found "only one side bright, the rest dark" (R9)**,
facing **the question of whether to keep hiding the graveyard and just light more of it, or to stop hiding it at all**,
we decided for **removing the fog of war from the game rules (`Game.visible`, `Game.seen`, `VIEW_RADIUS` and `_look` deleted). Both versions now show everything: in the window every tile is drawn at least at moonlight (`MOONLIGHT = 0.8`) and the torch only adds a warm glow near the player, and `--text` prints the whole map every turn**,
and neglected **(a) a bigger torch radius, (b) keeping the fog but showing tiles the player had already seen in a dim light, and (c) a moonlit view where the Reaper stays hidden until it is near**,
to achieve **a screen that is evenly lit, as R9 asks, where the player can read signposts and see hazards and hurdles ahead (R2, R7, R10), and where the Reaper is always visible when it is on screen, so the chase is something you can see, not a surprise**,
accepting that **the game loses the tension of not knowing what is ahead, dead ends can be spotted from a distance so the signposts (R2) matter less, and earlier tests that checked the fog (R1, R4, R7) had to be adapted (their IDs were kept and none were deleted)**.

## Alternatives considered

| Option | Pros | Cons |
|---|---|---|
| **Whole view moonlit, no fog (chosen)** | Does exactly what R9 asks. It's simpler, since a whole rule and its state are gone. Both front ends behave the same. | Less mystery. Dead ends can be seen before the signposts warn about them. |
| Bigger torch radius | Small change that keeps the fog idea. | The edges of the screen are still dark, so R9's complaint remains, only smaller. |
| Fog, but remembered tiles stay dimly lit | Rewards exploring, and the part already walked looks less empty. | The part ahead is still dark, which is the side the player is looking at. |
| Moonlit tiles, but the Reaper hidden until near | Keeps a scare. | Being caught by something you couldn't see feels unfair. It also adds a special case that the player would see as a bug. |

## Consequences

- `game.py` no longer tracks what the player has seen. Lighting is only a drawing concern in `gui.py` (`MOONLIGHT`, the torch glow).
- Tests that guard this decision: `test_R9_every_tile_in_view_is_at_least_moonlit`, `test_R9_torch_glow_is_strongest_at_the_player_and_fades_out`, `test_R9_the_whole_view_is_drawn_not_just_near_the_torch`, `test_R9_the_torch_warms_colours_and_the_moon_cools_them` (`tests/test_gui.py`), and `test_R9_the_text_map_shows_the_whole_graveyard_from_the_first_turn` (`tests/test_render.py`).
- Round 5 later removed the camera and drew the whole graveyard on screen (decision 0006). That only works because nothing is hidden any more.
- The `spec.md` of round 4 referred to records `0005-…` and `0006-…` for round 4, but they were never written, and round 5 used those numbers for its own records. This record takes the next free number instead.
