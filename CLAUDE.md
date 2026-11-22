# CLAUDE.md — standing rules for this project

## Project
A short escape game started from the terminal: the player runs a fixed graveyard path while the Grim Reaper chases them (real time in the window, turn-based in `--text`).
The main interface is a tkinter game window with drawn figures (`gui.py`); a plain terminal version remains behind `--text`.
Requirements are in `problem.md`; the design is in `spec.md`. Read both before changing behaviour.

## Language
- Python 3.10+ (developed on 3.13), **standard library only** for the game itself (tkinter for graphics). The game has no sound (R14).
- `pytest` is the only development dependency.
- Use `py` (the Windows Python launcher) in commands.

## Run the program
```
py -m escape_game          # game window (real time: hold keys to run)
py -m escape_game --text   # play inside the terminal instead
```

## Run the tests
```
py -m pytest
```

## Rules
- **Every test names the requirement ID it checks** (R1, R2, R3, ...). Put the ID in the test function name, e.g. `test_R3_player_caught_when_reaper_reaches_tile`, and repeat it in the docstring.
- Every requirement in `problem.md` has at least one test.
- Keep game logic (`maze.py`, `game.py`) free of input/output, so it can be tested directly. Drawing and input belong in `gui.py`, `__main__.py` and `render.py`. Real-time rules (the chase clock) live in `game.py` and are driven by `Game.update(ms)`.
- The game must stay silent (R14): no `winsound`, no terminal bell. `tests/test_silence.py` checks this.
- Window tests use hidden tkinter windows (`autorun=False`), let time pass with `advance(ms)`, and check tagged canvas items (the HUD is on `window.hud`); after a visual change, also look at a screenshot of the real window.
- When a requirement or decision changes, update `spec.md` in the same commit as the code.
- When a new requirement changes what an earlier one means (as R4 changed R3), adapt the earlier tests and keep their requirement ID. Don't delete them, and say so in the commit message.
- Record each decision that had real alternatives in `docs/decisions/` as a Y-statement. Number the files `0001-…`, `0002-…`, and so on.
- Commit in small steps. Each commit message says what changed and why.
- Never undo or amend a commit, and never force-push, unless the user explicitly asks. Ask before pushing.
- Handoff files (`HANDOFF-round-<n>.md`) are written only when the user asks. Leave them, and edits to this file, uncommitted until the user has reviewed them.
- If a requirement is unclear, ask the user before writing code.
- Before changing the layout in `maze.py`, simulate the chase on the new layout. The safe route must still win with the reaper 4 steps behind, and every grass tile must be reachable. The R2/R6/R7 layout tests check this.

## Tooling notes
- **Screenshots:** with Windows display scaling, `PIL.ImageGrab` coordinates are off. Grab the full screen, multiply window coordinates by `image.width / root.winfo_screenwidth()`, then crop. Pillow is for screenshots only, never a game dependency. Keep screenshot scripts in the session scratchpad.
- **Screenshots, first frame:** run `root.update()` a few times with short sleeps before the first grab. Otherwise the window isn't settled and desktop pixels end up in the crop.
- **Escapes in shell heredocs:** inline Python in heredocs can turn `\n` and `\u` escapes into real characters. This includes `\\n` inside Python string literals. Use the Edit tool for source lines that contain escapes, such as the BOM strip in `game.py`. For bigger scripted edits, write the Python script into the scratchpad with the Write tool and run it from there.
- Symbols such as ♥ ♡ → print as `?` when `--text` output is piped (cp1252). Set `PYTHONIOENCODING=utf-8` to see them.
