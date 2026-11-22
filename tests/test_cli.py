"""End-to-end tests: scripted keystrokes through the command-line entry point."""

import io

import pytest

from escape_game.__main__ import main
from escape_game.game import Game
from escape_game.maze import DIRECTIONS

KEY_FOR = {(-1, 0): "w", (1, 0): "s", (0, -1): "a", (0, 1): "d"}


def keys_to(goal=None):
    """Enter-separated keys along the player's way from the start (R7: no hazards; R12: j over the
    hurdles on the path, which are always met running straight, so the player already faces them)."""
    game = Game()
    path = game.maze.player_route(game.player, goal) if goal else game.route_out()  # R16: by the key
    keys = []
    for a, b in zip(path, path[1:]):
        dr, dc = b[0] - a[0], b[1] - a[1]
        keys.append("j" if abs(dr) + abs(dc) == 2 else KEY_FOR[(dr, dc)])
    return "".join(k + "\n" for k in keys)


def winning_keys():
    return keys_to()


FIRST_WARNING = (3, 26)  # the tile in front of the "Wanna get stuck?" signpost (R12 layout)


def play(keys, *extra_args):
    """Run the terminal game on scripted keys. R14: the game is silent, so the third value, kept for the
    callers, is the list of terminal bells rung (always empty)."""
    out = io.StringIO()
    code = main(["--text", "--no-color", *extra_args], stdin=io.StringIO(keys), stdout=out)
    text = out.getvalue()
    return code, text, ["bell"] * text.count("\a")


def test_R1_game_starts_with_intro_and_maze():
    """R1: launching the game shows the intro about the Grim Reaper and the player."""
    code, out, _ = play("q\n")
    assert code == 0
    assert "Grim Reaper" in out
    assert "@" in out


def test_R1_full_game_escape_through_the_cli():
    """R1: typing the right moves escapes the reaper. (Changed by R14: no escape tune any more.)"""
    code, out, beeps = play(winning_keys())
    assert code == 0
    assert "You escaped the Reaper in 80 turns!" in out
    assert beeps == []


def test_R1_heartbeat_is_no_longer_heard_every_turn():
    """R1 (changed by R14): there is no heartbeat sound; the status line still tells how close the Reaper is."""
    _, out, beeps = play("d\nd\nq\n")
    assert beeps == []
    assert out.count("Something cold breathes down your neck") == 3


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
    main(["--text"], stdin=io.StringIO(keys_to(FIRST_WARNING) + "q\n"), stdout=out)
    assert '\033[1;91m"Wanna get stuck?' in out.getvalue()


CATCH = "a\na\n"  # two steps back toward the reaper: caught


def test_R3_caught_through_the_cli():
    """R3: being caught on the last life ends the game with GAME OVER. (R14: no caught tone any more.)"""
    code, out, beeps = play(CATCH + "r\n" + CATCH + "r\n" + CATCH + "d\n")
    assert code == 0
    assert "GAME OVER" in out
    assert beeps == []
    assert out.rstrip().endswith("GAME OVER.")  # the last key was never read


# --- R4 / R5: lives in the terminal version ---------------------------------

def test_R4_caught_with_lives_left_waits_for_r_then_resumes():
    """R4: a catch costs a life and r + Enter resumes the chase. (R14: no life-lost tone any more.)"""
    code, out, beeps = play(CATCH + "d\nr\nq\n")
    assert code == 0
    assert "You lose a life" in out
    assert "r + Enter" in out
    assert beeps == []
    assert "GAME OVER" not in out
    # 'd' while caught is ignored; after r the player is back at the start, turn count kept
    resumed = out.split("You lose a life")[-1]
    assert "Turn 2" in resumed
    assert out.rstrip().endswith("You gave up. The Reaper is patient.")


def test_R4_win_after_losing_a_life():
    """R4: after resuming, the player can still escape."""
    code, out, beeps = play(CATCH + "r\n" + winning_keys())
    assert "You escaped the Reaper" in out
    assert beeps == []


def test_R5_hearts_go_from_three_to_none_in_the_terminal():
    """R5: the terminal shows ♥ ♥ ♥, then ♥ ♥ ♡, ♥ ♡ ♡ and finally ♡ ♡ ♡."""
    code, out, _ = play(CATCH + "r\n" + CATCH + "r\n" + CATCH)
    positions = [out.find(f"Lives: {h}") for h in ("♥ ♥ ♥", "♥ ♥ ♡", "♥ ♡ ♡", "♡ ♡ ♡")]
    assert all(p >= 0 for p in positions)
    assert positions == sorted(positions)


def test_R1_mute_flag_is_gone_because_there_is_no_sound():
    """R1 (changed by R14): --mute used to turn sound off; with no sound left, the option is gone."""
    with pytest.raises(SystemExit):
        main(["--text", "--mute", "--no-color"], stdin=io.StringIO("d\nq\n"), stdout=io.StringIO())


def test_R1_game_window_is_the_default(monkeypatch):
    """R1: with no options the graphical window opens."""
    import escape_game.gui as gui
    calls = []
    monkeypatch.setattr(gui, "run", lambda: calls.append("window") or 0)
    assert main([]) == 0
    assert calls == ["window"]


def test_R1_falls_back_to_terminal_if_window_cannot_open(monkeypatch):
    """R1: if no window can be opened, the game is still playable in the terminal."""
    import escape_game.gui as gui

    def broken():
        raise RuntimeError("no display")

    monkeypatch.setattr(gui, "run", broken)
    out = io.StringIO()
    assert main([], stdin=io.StringIO("q\n"), stdout=out) == 0
    assert "Could not open the game window" in out.getvalue()
    assert "You gave up" in out.getvalue()


# --- R6 / R7: the graveyard in the terminal version ---------------------------

def test_R6_intro_mentions_the_graveyard():
    """R6: the terminal story is set in a graveyard."""
    _, out, _ = play("q\n")
    assert "graveyard" in out


def test_R7_open_grave_costs_a_life_in_the_terminal():
    """R7: walking into the open grave east of the start costs a life. (R14: silently.)"""
    code, out, beeps = play("d\nd\nd\nd\nr\nq\n")
    assert "You tumble into an open grave! You lose a life." in out
    assert "Lives: ♥ ♥ ♡" in out
    assert beeps == []
    assert out.rstrip().endswith("You gave up. The Reaper is patient.")



# --- R10: jumping in the terminal ----------------------------------------------

def test_R10_j_jumps_over_an_open_grave_in_the_terminal():
    """R10: j + Enter leaps the open grave east of the start without losing a life."""
    _, out, beeps = play("d\nd\nd\nj\nq\n")
    assert "You tumble into an open grave" not in out
    assert "Turn 4" in out and "♡" not in out


def test_R10_failed_jump_and_low_hurdle_bump_are_explained():
    """R10: the terminal says why a jump failed, and how to jump a low hurdle that blocks the way."""
    _, out, _ = play("j\nq\n")
    assert "There is nothing here to jump over." in out
    keys = keys_to((1, 13)) + "d\n"  # run up to the coffin on the path and bump into it
    _, out, _ = play(keys + "q\n")
    assert "A coffin blocks your way. Type j to jump over it." in out



# --- R16: the key in the terminal ---------------------------------------------------------

def test_R16_picking_up_the_key_is_announced_in_the_terminal():
    """R16: walking onto the key prints that it was found; the winning keys go by way of it."""
    game = Game()
    _, out, _ = play(keys_to(game.maze.key) + "q\n")
    assert "You found the key! Now run for the gate." in out
    assert "You have the key. Run for the gate!" in out
