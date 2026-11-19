# CLAUDE.md — standing rules for this project

## Project
A short, turn-based escape game started from the terminal: the player escapes a fixed maze while the Grim Reaper chases them.
The main interface is a tkinter game window with drawn figures (`gui.py`); a plain terminal version remains behind `--text`.
Requirements are in `problem.md`; the design is in `spec.md`. Read both before changing behaviour.

## Language
- Python 3.10+ (developed on 3.13), **standard library only** for the game itself (tkinter for graphics, winsound for sound).
- `pytest` is the only development dependency.
- Use `py` (the Windows Python launcher) in commands.

## Run the program
```
py -m escape_game          # game window, with sound
py -m escape_game --mute   # game window, no sound
py -m escape_game --text   # play inside the terminal instead
```

## Run the tests
```
py -m pytest
```

## Rules
- **Every test names the requirement ID it checks** (R1, R2, R3, ...). Put the ID in the test function name, e.g. `test_R3_player_caught_when_reaper_reaches_tile`, and repeat it in the docstring.
- Every requirement in `problem.md` has at least one test.
- Keep game logic (`maze.py`, `game.py`) free of input/output, so it can be tested directly. Drawing, input and sound belong in `gui.py`, `__main__.py`, `render.py` and `sound.py`.
- Tests must never play real sound. Inject a fake beep function or fake sound object instead.
- Window tests use hidden tkinter windows and check tagged canvas items; after a visual change, also look at a screenshot of the real window.
- When a requirement or decision changes, update `spec.md` in the same commit as the code.
- Commit in small steps. Each commit message says what changed and why.
