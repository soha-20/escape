"""Tests for what the player sees."""

from escape_game.game import Game, Status
from escape_game.render import draw_map, reaper_line, screen


def rows(game):
    return draw_map(game, color=False).splitlines()


def test_R1_player_is_drawn_and_far_tiles_are_hidden():
    """R1: the player sees themselves and only the nearby maze (fog of war)."""
    game = Game()
    lines = rows(game)
    assert lines[1][5] == "@"
    assert lines[9][15] == " "  # exit is far away and unseen


def test_R1_reaper_drawn_only_when_in_view():
    """R1: the reaper appears on screen once it is within sight."""
    game = Game()
    assert "R" not in draw_map(game, color=False)
    game.move("left")  # player (1,4), reaper (1,2)
    assert rows(game)[1][2] == "R"


def test_R1_status_line_warns_how_close_the_reaper_is():
    """R1: the status text gets more urgent as the reaper approaches."""
    assert "Distant" in reaper_line(7, color=False)
    assert "breathes" in reaper_line(4, color=False)
    assert "RUN!" in reaper_line(3, color=False)
    assert "1 step away" in reaper_line(1, color=False)


def test_R2_signs_drawn_as_exclamation_marks_on_walls():
    """R2: signs on walls are marked '!' when in view."""
    game = Game()
    for _ in range(4):
        game.move("right")
    assert rows(game)[0][9] == "!"


def test_R1_screen_shows_turn_and_controls_while_playing():
    """R1: during play the screen shows the turn number and controls."""
    text = screen(Game(), color=False)
    assert "Turn 0" in text and "w/a/s/d" in text


def test_R3_screen_shows_game_over_when_caught():
    """R3: once caught the screen says GAME OVER and drops the controls."""
    game = Game()
    game.move("left")
    game.move("left")
    assert game.status is Status.LOST
    text = screen(game, color=False)
    assert "GAME OVER" in text and "w/a/s/d" not in text
