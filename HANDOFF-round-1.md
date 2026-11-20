# Handoff — Escape the Grim Reaper

Session dates: 2026-11-18 to 2026-11-19. Read `CLAUDE.md`, `problem.md` and `spec.md` first. They are up to date.

## Where things stand

- **State:** working and pushed. `main` = `origin/main` at `e73a93f`, and the working tree is clean.
- **Tests:** `py -m pytest` → 85 passed in about 2.5 s on Python 3.13 with pytest 9.2. Every test is named `test_R<n>_...`.
- **Running it:** `py -m escape_game` opens the tkinter game window. `--mute` turns sound off. `--text` plays the original terminal version.
- **How it looks:** the window was checked with real screenshots. Two are committed in `docs/`.

## What happened, in order

1. **First commit fixed.** The first commit's message said "R1-R4" by mistake; it now says R1-R3. Rewriting it needed a force-push to `main`, which the user approved.
2. **Spec written.** `spec.md` was written with the user's answers: Python, turn-based, one fixed maze, the reaper moves every turn. The user also asked for **sound** to add tension. Everything they didn't decide is marked *(default)* in the spec.
3. **Terminal game built.** The first version was a coloured-text terminal game: `maze.py`, `game.py`, `render.py`, `sound.py`, `__main__.py`.
4. **User rejected the terminal look.** Their words: "no graphical elements and the no colors not a real figure user and grip reaper". They chose a **tkinter window** over pygame and rich terminal graphics, and chose to **stay turn-based** rather than real-time.
5. **Game window built.** `gui.py` was added and became the default. `problem.md` was then updated to say the game opens in a window.

## Design facts worth knowing

- **Maze** (`maze.py`): 11×27, fixed layout.
  - The player starts 4 steps ahead of the reaper. The route to the exit is 44 moves and passes through 4 forks.
  - Each fork has a sign. 2 are red warnings over dead ends (including "Wanna get stuck?"). 2 are green guides along the route.
  - The reaper is exactly as fast as the player, so a single step into a wrong branch and back is survivable, but walking to the end of a dead end means capture. Tests check this, so changing the layout or the starting gap will break them.
- **Rules** (`game.py`, no input/output): the player moves; if they're on the exit they win before the reaper moves; otherwise the reaper takes one BFS step. Sharing a tile in either direction is a loss. A wall bump or an unknown command costs no turn.
- **Window** (`gui.py`):
  - The camera shows 15×9 tiles at 52 px each and follows the player.
  - Torch light reaches 3 tiles (Chebyshev distance). Tiles the player has already seen stay dim; tiles never seen are black.
  - Canvas items are tagged (`player`, `reaper`, `reaper_eyes`, `sign_banner`, `danger`, `overlay`, `ending_title`, …), and the tests rely on those tags.
  - Sounds play on a background `SoundWorker` thread. Tests pass `threaded_sound=False` and a fake sound object.
- **Sound** (`sound.py`): `winsound.Beep`. Elsewhere it falls back to the terminal bell. The heartbeat changes at 6+, 4–5 and ≤3 steps. Tones are 150 Hz or higher so laptop speakers can play them.

## Not yet confirmed with the user

- **The sound has never been heard.** Neither the user nor Claude has heard it; the tests only check which tones would play. Ask the user to play once with speakers on.
- **Spec defaults the user hasn't explicitly approved:**
  - one level
  - every sign is honest
  - being next to the reaper is safe
  - `R` replays (window only)
  - wall bumps are free
  - torch light reaches 3 tiles
- **Difficulty is untested on a real player.** Any wrong turn that goes deep into a dead end is fatal.
- **Sound isn't a requirement in `problem.md`.** It's tested under R1. If the user adds it as R4, rename those tests.

## Gotchas hit this session

- **Screenshots:** Windows display scaling made `PIL.ImageGrab` capture the wrong area. Grab the full screen, multiply by `image.width / root.winfo_screenwidth()`, then crop. The screenshot script lived in the session scratchpad and is gone, so rebuild it with that rule.
  - The screen is 1280×720 logical pixels and the window is about 780×618, so don't grow it much.
- **Shell heredocs** turned `\n` and `\u` escapes in inline Python into real characters. Use the Edit tool for lines that contain escapes.
- **Windows PowerShell 5.1** adds a BOM to piped input. `Game.command` strips it.
- **Fonts:** the "Chiller" font isn't installed. Titles use "Impact" and body text uses "Segoe UI".
- **Window tests:** they open hidden `Toplevel` windows on one shared `Tk` root and skip if no display is available. `GameWindow.close()` cancels the animation timer before destroying the window, so always close through it.
