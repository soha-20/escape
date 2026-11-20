"""Turn a Game into text for the terminal. Pure functions: no printing."""

from .game import MAX_LIVES, Game, Status
from .maze import GUIDE, WARNING

RESET = "\033[0m"
STYLES = {
    "player": "\033[1;93m",   # bold bright yellow
    "reaper": "\033[1;95m",   # bold bright magenta
    "exit": "\033[1;92m",     # bold bright green
    "wall": "\033[37m",
    "dim": "\033[2;90m",
    WARNING: "\033[1;91m",    # bold bright red
    GUIDE: "\033[1;92m",      # bold bright green
    "danger": "\033[1;91m",
}

INTRO = (
    "You wake on cold stone in the dark.\n"
    "Something breathes behind you. The Grim Reaper has come for you.\n"
    "Find the way out. Read the walls. Don't look back.\n"
)

CONTROLS = "Move: w/a/s/d + Enter    Quit: q"
RESUME_CONTROLS = "Resume: r + Enter    Quit: q"

FULL_HEART, EMPTY_HEART = "♥", "♡"


def paint(text: str, style: str, color: bool) -> str:
    return f"{STYLES[style]}{text}{RESET}" if color else text


def tile(game: Game, pos, color: bool) -> str:
    maze = game.maze
    visible = game.visible(pos)
    if not visible and pos not in game.seen:
        return " "
    if visible and pos == game.player:
        return paint("@", "player", color)
    if visible and pos == game.reaper:
        return paint("R", "reaper", color)
    if pos in maze.signs:
        sign = maze.signs[pos]
        return paint("!", sign.kind if visible else "dim", color)
    if pos == maze.exit:
        return paint("E", "exit" if visible else "dim", color)
    if maze.is_wall(pos):
        return paint("#", "wall" if visible else "dim", color)
    return paint(".", "dim", color) if visible else " "


def draw_map(game: Game, color: bool = True) -> str:
    return "\n".join(
        "".join(tile(game, (r, c), color) for c in range(game.maze.width))
        for r in range(game.maze.height)
    )


def reaper_line(distance: int, color: bool = True) -> str:
    steps = f"{distance} step{'s' if distance != 1 else ''}"
    if distance >= 6:
        return f"Distant footsteps echo behind you. ({steps} away)"
    if distance > 3:
        return f"Something cold breathes down your neck... ({steps} away)"
    return paint(f"RUN! The Reaper is right behind you! ({steps} away)", "danger", color)


def sign_lines(game: Game, color: bool = True) -> list[str]:
    lines = []
    for sign in game.signs_here():
        ink = "red" if sign.kind == WARNING else "green"
        lines.append(f"Scrawled on the wall in {ink}: " + paint(f'"{sign.text}"', sign.kind, color))
    return lines


def lives_line(game: Game, color: bool = True) -> str:
    """R5: one heart per life; lost lives become empty hearts on the right."""
    full = [paint(FULL_HEART, "danger", color)] * max(game.lives, 0)
    empty = [EMPTY_HEART] * (MAX_LIVES - len(full))
    return "Lives: " + " ".join(full + empty)


def ending(game: Game, color: bool = True) -> str | None:
    if game.status is Status.WON:
        return paint(f"You burst into the night air. You escaped the Reaper in {game.turn} turns!",
                     "exit", color)
    if game.status is Status.LOST:
        return paint("The Reaper's hand closes on your shoulder. GAME OVER.", "danger", color)
    if game.status is Status.QUIT:
        return "You gave up. The Reaper is patient."
    return None


def screen(game: Game, message: str = "", color: bool = True) -> str:
    """Everything shown for one turn."""
    parts = [draw_map(game, color), "", lives_line(game, color)]
    end = ending(game, color)
    if end:
        parts.append(end)
    elif game.status is Status.CAUGHT:
        parts.append(paint("The Reaper's cold hand grabs you! You lose a life.", "danger", color))
        parts.append(RESUME_CONTROLS)
    else:
        parts.append(f"Turn {game.turn}   " + reaper_line(game.reaper_distance(), color))
        parts.extend(sign_lines(game, color))
        if message:
            parts.append(message)
        parts.append(CONTROLS)
    return "\n".join(parts)
