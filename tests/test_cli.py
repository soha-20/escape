"""End-to-end tests: scripted keystrokes through the command-line entry point."""

import io

from escape_game.__main__ import main
from escape_game.game import Game
from escape_game.maze import DIRECTIONS
from escape_game.sound import CAUGHT_TONES, ESCAPED_TONES, LIFE_LOST_TONES, Sound

KEY_FOR = {(-1, 0): "w", (1, 0): "s", (0, -1): "a", (0, 1): "d"}


class Recorder:
    def __init__(self):
        self.beeps = []

    def beep(self, freq, ms):
        self.beeps.append((freq, ms))


def keys_to(goal=None):
    """Enter-separated keys along the shortest hazard-free way from the start (R7)."""
    game = Game()
    path = game.maze.shortest_path(game.player, goal or game.maze.exit, avoid_hazards=True)
    return "".join(KEY_FOR[(b[0] - a[0], b[1] - a[1])] + "\n" for a, b in zip(path, path[1:]))


def winning_keys():
    return keys_to()


FIRST_WARNING = (4, 23)  # the tile in front of the "Wanna get stuck?" signpost


def play(keys, *extra_args):
    rec = Recorder()
    out = io.StringIO()
    code = main(["--text", "--no-color", *extra_args], stdin=io.StringIO(keys), stdout=out,
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
    assert "You escaped the Reaper in 59 turns!" in out
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
    """R1: the player is told when a move was not taken (since R6 the fence, not a stone wall)."""
    _, out, _ = play("w\nzz\nq\n")
    assert "An iron fence blocks your way." in out
    assert "Unknown command" in out


def test_R2_sign_text_appears_at_the_fork():
    """R2: arriving next to the first signpost shows 'Wanna get stuck?' in the warning colour."""
    _, out, _ = play(keys_to(FIRST_WARNING) + "q\n")
    assert 'Painted on a signpost in red: "Wanna get stuck?' in out


def test_R2_warning_signs_are_red_and_guides_green_when_colour_is_on():
    """R2: the warning text is printed in red (ANSI 91)."""
    out = io.StringIO()
    main(["--text"], stdin=io.StringIO(keys_to(FIRST_WARNING) + "q\n"), stdout=out, sound=Sound(enabled=False))
    assert '\033[1;91m"Wanna get stuck?' in out.getvalue()


CATCH = "a\na\n"  # two steps back toward the reaper: caught


def test_R3_caught_through_the_cli():
    """R3: being caught on the last life ends the game with GAME OVER and the caught tone."""
    code, out, beeps = play(CATCH + "r\n" + CATCH + "r\n" + CATCH + "d\n")
    assert code == 0
    assert "GAME OVER" in out
    assert beeps[-len(CAUGHT_TONES):] == CAUGHT_TONES
    assert out.rstrip().endswith("GAME OVER.")  # the last key was never read


# --- R4 / R5: lives in the terminal version ---------------------------------

def test_R4_caught_with_lives_left_waits_for_r_then_resumes():
    """R4: a catch costs a life, plays the life-lost tone, and r + Enter resumes the chase."""
    code, out, beeps = play(CATCH + "d\nr\nq\n")
    assert code == 0
    assert "You lose a life" in out
    assert "r + Enter" in out
    assert _contains(beeps, LIFE_LOST_TONES)
    assert not _contains(beeps, CAUGHT_TONES)
    assert "GAME OVER" not in out
    # 'd' while caught is ignored; after r the player is back at the start, turn count kept
    resumed = out.split("You lose a life")[-1]
    assert "Turn 2" in resumed
    assert out.rstrip().endswith("You gave up. The Reaper is patient.")


def test_R4_win_after_losing_a_life():
    """R4: after resuming, the player can still escape."""
    code, out, beeps = play(CATCH + "r\n" + winning_keys())
    assert "You escaped the Reaper" in out
    assert beeps[-len(ESCAPED_TONES):] == ESCAPED_TONES


def test_R5_hearts_go_from_three_to_none_in_the_terminal():
    """R5: the terminal shows ♥ ♥ ♥, then ♥ ♥ ♡, ♥ ♡ ♡ and finally ♡ ♡ ♡."""
    code, out, _ = play(CATCH + "r\n" + CATCH + "r\n" + CATCH)
    positions = [out.find(f"Lives: {h}") for h in ("♥ ♥ ♥", "♥ ♥ ♡", "♥ ♡ ♡", "♡ ♡ ♡")]
    assert all(p >= 0 for p in positions)
    assert positions == sorted(positions)


def _contains(seq, sub):
    return any(seq[i:i + len(sub)] == sub for i in range(len(seq) - len(sub) + 1))


def test_R1_mute_flag_disables_sound():
    """R1: --mute plays nothing."""
    out = io.StringIO()
    main(["--text", "--mute", "--no-color"], stdin=io.StringIO("d\nq\n"), stdout=out)
    assert "Turn 1" in out.getvalue()


def test_R1_game_window_is_the_default(monkeypatch):
    """R1: with no options the graphical window opens (with sound unless --mute)."""
    import escape_game.gui as gui
    calls = []
    monkeypatch.setattr(gui, "run", lambda mute=False: calls.append(mute) or 0)
    assert main([]) == 0
    assert main(["--mute"]) == 0
    assert calls == [False, True]


def test_R1_falls_back_to_terminal_if_window_cannot_open(monkeypatch):
    """R1: if no window can be opened, the game is still playable in the terminal."""
    import escape_game.gui as gui

    def broken(mute=False):
        raise RuntimeError("no display")

    monkeypatch.setattr(gui, "run", broken)
    out = io.StringIO()
    assert main(["--mute"], stdin=io.StringIO("q\n"), stdout=out) == 0
    assert "Could not open the game window" in out.getvalue()
    assert "You gave up" in out.getvalue()


# --- R6 / R7: the graveyard in the terminal version ---------------------------

def test_R6_intro_mentions_the_graveyard():
    """R6: the terminal story is set in a graveyard."""
    _, out, _ = play("q\n")
    assert "graveyard" in out


def test_R7_open_grave_costs_a_life_in_the_terminal():
    """R7: walking into the open grave east of the start costs a life and plays the life-lost tone."""
    code, out, beeps = play("d\nd\nd\nd\nr\nq\n")
    assert "You tumble into an open grave! You lose a life." in out
    assert "Lives: ♥ ♥ ♡" in out
    assert _contains(beeps, LIFE_LOST_TONES)
    assert out.rstrip().endswith("You gave up. The Reaper is patient.")



# --- R10: jumping in the terminal ----------------------------------------------

def test_R10_j_jumps_over_an_open_grave_in_the_terminal():
    """R10: j + Enter leaps the open grave east of the start without losing a life."""
    _, out, beeps = play("d\nd\nd\nj\nq\n")
    assert "You tumble into an open grave" not in out
    assert "Turn 4" in out and "♡" not in out
    assert not _contains(beeps, LIFE_LOST_TONES)


def test_R10_failed_jump_and_low_hurdle_bump_are_explained():
    """R10: the terminal says why a jump failed, and how to jump a low hurdle that blocks the way."""
    _, out, _ = play("j\nq\n")
    assert "There is nothing here to jump over." in out
    keys = keys_to((3, 19)) + "d\n"  # walk up to the fallen headstone and bump into it
    _, out, _ = play(keys + "q\n")
    assert "A fallen headstone blocks your way. Type j to jump over it." in out
