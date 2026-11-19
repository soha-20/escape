"""Command-line entry point: py -m escape_game [--mute] [--no-color]"""

import argparse
import os
import sys

from .game import Game, Outcome, Status
from .render import INTRO, screen
from .sound import Sound

CLEAR = "\033[2J\033[H"

MESSAGES = {
    Outcome.WALL: "A cold stone wall. You lose no time, but don't waste any either.",
    Outcome.INVALID: "Unknown command. Use w/a/s/d to move or q to quit.",
}


def _enable_windows_ansi() -> None:
    if os.name == "nt":
        os.system("")  # turns on ANSI escape processing in the Windows console


def main(argv=None, stdin=None, stdout=None, sound: Sound | None = None) -> int:
    parser = argparse.ArgumentParser(prog="py -m escape_game",
                                     description="Escape the Grim Reaper through a dark maze.")
    parser.add_argument("--mute", action="store_true", help="play without sound")
    parser.add_argument("--no-color", action="store_true", help="plain text, no ANSI colours")
    args = parser.parse_args(argv)

    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    if hasattr(stdout, "reconfigure"):
        stdout.reconfigure(errors="replace")  # arrows in signs on odd consoles
    interactive = stdout.isatty() if hasattr(stdout, "isatty") else False
    color = not args.no_color
    if color and interactive:
        _enable_windows_ansi()
    if sound is None:
        sound = Sound(enabled=not args.mute)

    game = Game()

    def show(message: str = "") -> None:
        if interactive:
            stdout.write(CLEAR)
        stdout.write(screen(game, message, color) + "\n")
        stdout.flush()

    stdout.write(INTRO + "\n")
    show()
    sound.heartbeat(game.reaper_distance())
    while game.status is Status.PLAYING:
        stdout.write("> ")
        stdout.flush()
        line = stdin.readline()
        if line == "":  # end of input: treat as quitting
            line = "q"
        outcome = game.command(line)
        show(MESSAGES.get(outcome, ""))
        if outcome is Outcome.MOVED:
            if game.status is Status.PLAYING:
                sound.heartbeat(game.reaper_distance())
            elif game.status is Status.LOST:
                sound.caught()
            elif game.status is Status.WON:
                sound.escaped()
    return 0


if __name__ == "__main__":
    sys.exit(main())
