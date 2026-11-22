"""R14: the game makes no sound.

Until round 5 this file (then test_sound.py) tested the chase sounds, filed under R1 and R4. R14 removed
the sound, so those tests were adapted to check that nothing sounds, keeping their requirement IDs; the
heartbeat they described is now only seen (the beating hearts and the Reaper's pulsing aura).
"""

import importlib
import io
import pathlib
import sys
import types

import pytest

import escape_game
from escape_game.__main__ import main
from escape_game.gui import heartbeat_period_ms

PACKAGE = pathlib.Path(escape_game.__file__).parent
CATCH = "a\na\n"  # two steps back toward the reaper: caught


@pytest.fixture
def speaker(monkeypatch):
    """A fake winsound module that records any attempt to make a sound."""
    calls = []
    fake = types.ModuleType("winsound")
    fake.Beep = lambda *args: calls.append(("Beep", args))
    fake.PlaySound = lambda *args: calls.append(("PlaySound", args))
    fake.MessageBeep = lambda *args: calls.append(("MessageBeep", args))
    monkeypatch.setitem(sys.modules, "winsound", fake)
    return calls


def play(keys):
    out = io.StringIO()
    main(["--text", "--no-color"], stdin=io.StringIO(keys), stdout=out)
    return out.getvalue()


def winning_keys():
    from escape_game.game import Game
    game = Game()
    path = game.maze.player_route(game.player, game.maze.exit)
    names = {(-1, 0): "w", (1, 0): "s", (0, -1): "a", (0, 1): "d"}
    keys = ["j" if abs(b[0] - a[0]) + abs(b[1] - a[1]) == 2 else names[(b[0] - a[0], b[1] - a[1])]
            for a, b in zip(path, path[1:])]
    return "".join(k + "\n" for k in keys)


# --- R14: no sound -------------------------------------------------------------------

def test_R14_the_sound_module_is_gone():
    """R14: escape_game.sound no longer exists."""
    assert not (PACKAGE / "sound.py").exists()
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("escape_game.sound")


def test_R14_no_part_of_the_game_can_make_a_sound():
    """R14: no module imports winsound, rings the terminal bell or calls Tk's bell."""
    for source in PACKAGE.glob("*.py"):
        text = source.read_text(encoding="utf-8")
        assert "winsound" not in text, source.name
        assert "\\a" not in text and "\a" not in text, source.name
        assert ".bell(" not in text, source.name


def test_R14_a_whole_game_in_the_terminal_is_silent(speaker):
    """R14: losing lives, losing the game and winning make no sound in --text."""
    out = play(CATCH + "r\n" + winning_keys()) + play(CATCH + "r\n" + CATCH + "r\n" + CATCH)
    assert "You escaped the Reaper" in out and "GAME OVER" in out
    assert "\a" not in out and speaker == []


def test_R14_the_mute_option_is_gone():
    """R14: --mute is no longer an option (there is nothing to mute)."""
    with pytest.raises(SystemExit):
        main(["--mute"], stdin=io.StringIO("q\n"), stdout=io.StringIO())


# --- R1 / R4: the old sound tests, adapted -----------------------------------------------

def test_R1_heartbeat_gets_faster_as_reaper_closes_in():
    """R1 (changed by R14): the heartbeat is now only seen: the hearts beat faster as the Reaper closes in."""
    assert heartbeat_period_ms(8) > heartbeat_period_ms(5) > heartbeat_period_ms(2)


def test_R1_heartbeat_thresholds():
    """R1: the boundaries are still 6+ far, 4-5 medium, 3 or fewer close (now for the on-screen beat)."""
    assert heartbeat_period_ms(6) == heartbeat_period_ms(100)
    assert heartbeat_period_ms(4) == heartbeat_period_ms(5) != heartbeat_period_ms(6)
    assert heartbeat_period_ms(3) == heartbeat_period_ms(0) != heartbeat_period_ms(4)


def test_R1_no_beep_function_is_called_during_a_game(speaker):
    """R1 (changed by R14): a heartbeat used to beep every turn; now no turn makes a sound."""
    out = play("d\nd\nd\nq\n")
    assert speaker == [] and "\a" not in out


def test_R1_caught_and_escaped_are_silent(speaker):
    """R1/R3 (changed by R14): capture and escape no longer play a falling or rising tone."""
    out = play(CATCH + "r\n" + CATCH + "r\n" + CATCH) + play(winning_keys())
    assert "GAME OVER" in out and "You escaped the Reaper" in out
    assert speaker == []


def test_R1_mute_makes_no_sound():
    """R1 (changed by R14): the game is always silent, so --mute is gone."""
    with pytest.raises(SystemExit):
        main(["--text", "--mute"], stdin=io.StringIO("q\n"), stdout=io.StringIO())


def test_R1_game_runs_where_there_is_no_sound_device(monkeypatch):
    """R1 (changed by R14): the game no longer needs winsound at all, so it runs without it."""
    monkeypatch.setitem(sys.modules, "winsound", None)  # importing winsound now fails
    import escape_game.__main__ as entry
    import escape_game.gui as gui
    importlib.reload(gui)
    importlib.reload(entry)
    assert "You escaped the Reaper" in play(winning_keys())


def test_R4_losing_a_life_is_silent(speaker):
    """R4 (changed by R14): losing a life no longer plays a falling tone."""
    out = play(CATCH + "r\nq\n")
    assert "You lose a life" in out and speaker == []
