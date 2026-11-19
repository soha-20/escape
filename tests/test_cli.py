"""End-to-end tests: scripted keystrokes through the command-line entry point."""

import io

from escape_game.__main__ import main
from escape_game.game import Game
from escape_game.maze import DIRECTIONS
from escape_game.sound import CAUGHT_TONES, ESCAPED_TONES, Sound

KEY_FOR = {(-1, 0): "w", (1, 0): "s", (0, -1): "a", (0, 1): "d"}


class Recorder:
    def __init__(self):
        self.beeps = []

    def beep(self, freq, ms):
        self.beeps.append((freq, ms))


def winning_keys():
    game = Game()
    path = game.maze.shortest_path(game.player, game.maze.exit)
    return "".join(KEY_FOR[(b[0] - a[0], b[1] - a[1])] + "\n" for a, b in zip(path, path[1:]))


def play(keys, *extra_args):
    rec = Recorder()
    out = io.StringIO()
    code = main(["--no-color", *extra_args], stdin=io.StringIO(keys), stdout=out,
                sound=Sound(beep=rec.beep, sleep=lambda s: None))
    return code, out.getvalue(), rec.beeps


def test_R1_game_starts_with_intro_and_maze():
    """R1: launching the game shows the intro about the Grim Reaper and the player."""
    code, out, _ = play("q\n")
    assert code == 0
    assert "Grim Reaper" in out
    assert "@" in out


def test_R1_full_game_escape_through_the_cli():
    """R1: typing the right moves escapes the reaper and plays the escape tune."""
    code, out, beeps = play(winning_keys())
    assert code == 0
    assert "You escaped the Reaper in 44 turns!" in out
    assert beeps[-len(ESCAPED_TONES):] == ESCAPED_TONES


def test_R1_heartbeat_plays_every_turn():
    """R1: a heartbeat sounds at the start and after every move while the chase is on."""
    _, _, beeps = play("d\nd\nq\n")
    assert len(beeps) == 3 * 2  # distance 4 -> two beats, three times


def test_R1_end_of_input_quits_cleanly():
    """R1: closing input (Ctrl+Z / Ctrl+D) ends the game instead of hanging."""
    code, out, _ = play("")
    assert code == 0 and "You gave up" in out


def test_R1_wall_and_typo_messages_are_shown():
    """R1: the player is told when a move was not taken."""
    _, out, _ = play("w\nzz\nq\n")
    assert "cold stone wall" in out
    assert "Unknown command" in out


def test_R2_sign_text_appears_at_the_fork():
    """R2: arriving next to the first sign shows 'Wanna get stuck?' in the warning colour."""
    _, out, _ = play("d\nd\nd\nd\nq\n")
    assert 'Scrawled on the wall in red: "Wanna get stuck?' in out


def test_R2_warning_signs_are_red_and_guides_green_when_colour_is_on():
    """R2: the warning text is printed in red (ANSI 91)."""
    out = io.StringIO()
    main([], stdin=io.StringIO("d\nd\nd\nd\nq\n"), stdout=out, sound=Sound(enabled=False))
    assert '\033[1;91m"Wanna get stuck?' in out.getvalue()


def test_R3_caught_through_the_cli():
    """R3: walking back into the reaper ends the game with GAME OVER and the caught tone."""
    code, out, beeps = play("a\na\nd\n")
    assert code == 0
    assert "GAME OVER" in out
    assert beeps[-len(CAUGHT_TONES):] == CAUGHT_TONES
    assert out.rstrip().endswith("GAME OVER.")  # third key was never read


def test_R1_mute_flag_disables_sound():
    """R1: --mute plays nothing."""
    out = io.StringIO()
    main(["--mute", "--no-color"], stdin=io.StringIO("d\nq\n"), stdout=out)
    assert "Turn 1" in out.getvalue()
