"""Command-line entry point.

    py -m escape_game                     graphical game window (default)
    py -m escape_game --text [--no-color] play inside the terminal instead

The game makes no sound (R14).
"""

import argparse
import os
import sys

from .game import Game, Outcome, Status
from .render import INTRO, KEY_FOUND, bump_line, jump_line, screen

CLEAR = "\033[2J\033[H"

MESSAGES = {
    Outcome.INVALID: "Unknown command. Use w/a/s/d to move, j to jump or q to quit.",
    Outcome.PAUSED: "You are in the Reaper's grip. Type r to resume.",
}


def _enable_windows_ansi() -> None:
    if os.name == "nt":
        os.system("")  # turns on ANSI escape processing in the Windows console


def main(argv=None, stdin=None, stdout=None) -> int:
    parser = argparse.ArgumentParser(prog="py -m escape_game",
                                     description="Escape the Grim Reaper through a dark graveyard.")
    parser.add_argument("--text", action="store_true", help="play inside the terminal instead of a window")
    parser.add_argument("--no-color", action="store_true", help="with --text: plain text, no ANSI colours")
    args = parser.parse_args(argv)

    if not args.text:
        try:
            from . import gui
            return gui.run()
        except Exception as exc:  # no tkinter or no display: fall back to the terminal game
            (stdout or sys.stdout).write(f"Could not open the game window ({exc}); playing in the terminal.\n")

    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    if hasattr(stdout, "reconfigure"):
        stdout.reconfigure(errors="replace")  # arrows in signs on odd consoles
    interactive = stdout.isatty() if hasattr(stdout, "isatty") else False
    color = not args.no_color
    if color and interactive:
        _enable_windows_ansi()

    game = Game()

    def show(message: str = "") -> None:
        if interactive:
            stdout.write(CLEAR)
        stdout.write(screen(game, message, color) + "\n")
        stdout.flush()

    stdout.write(INTRO + "\n")
    show()
    while game.status in (Status.PLAYING, Status.CAUGHT):
        stdout.write("> ")
        stdout.flush()
        line = stdin.readline()
        if line == "":  # end of input: treat as quitting
            line = "q"
        had_key = game.has_key
        outcome = game.command(line)
        if outcome is Outcome.WALL:  # R6: say what is in the way
            show(f"{bump_line(game.bumped, 'Type j')} You lose no time, but don't waste any either.")
        elif outcome is Outcome.NO_JUMP:  # R10: say why
            show(jump_line(game.jump_blocked))
        elif game.has_key and not had_key:  # R16
            show(KEY_FOUND)
        else:
            show(MESSAGES.get(outcome, ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
