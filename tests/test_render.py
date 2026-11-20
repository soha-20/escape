"""Tests for what the player sees."""

from escape_game.game import Game, Status
from escape_game.render import draw_map, lives_line, reaper_line, screen


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
    path = game.maze.shortest_path(game.player, (4, 21), avoid_hazards=True)
    for a, b in zip(path, path[1:]):
        game.move({(0, 1): "right", (0, -1): "left", (1, 0): "down", (-1, 0): "up"}[(b[0] - a[0], b[1] - a[1])])
    assert rows(game)[3][23] == "!"


def test_R1_screen_shows_turn_and_controls_while_playing():
    """R1: during play the screen shows the turn number and controls."""
    text = screen(Game(), color=False)
    assert "Turn 0" in text and "w/a/s/d" in text


def test_R3_screen_shows_game_over_when_caught():
    """R3: once caught on the last life the screen says GAME OVER and drops the controls."""
    game = Game(lives=1)
    game.move("left")
    game.move("left")
    assert game.status is Status.LOST
    text = screen(game, color=False)
    assert "GAME OVER" in text and "w/a/s/d" not in text


# --- R4 / R5: lives and hearts in the terminal ------------------------------

def caught_once():
    game = Game()
    game.move("left")
    game.move("left")
    assert game.status is Status.CAUGHT
    return game


def test_R5_screen_shows_three_full_hearts_at_the_start():
    """R5: the terminal screen shows three hearts while all lives are left."""
    assert "Lives: ♥ ♥ ♥" in screen(Game(), color=False)


def test_R5_a_lost_life_turns_a_heart_into_an_empty_one():
    """R5: each lost life replaces a full heart with an empty one, from the right."""
    game = caught_once()
    assert "Lives: ♥ ♥ ♡" in screen(game, color=False)
    game.resume()
    game.move("left")
    game.move("left")
    assert "Lives: ♥ ♡ ♡" in screen(game, color=False)


def test_R5_all_hearts_empty_on_game_over():
    """R5: when every life is lost all three hearts are empty."""
    game = Game()
    for _ in range(3):
        game.resume()
        game.move("left")
        game.move("left")
    assert game.status is Status.LOST
    text = screen(game, color=False)
    assert "Lives: ♡ ♡ ♡" in text and "GAME OVER" in text


def test_R5_full_hearts_are_red_when_colour_is_on():
    """R5: the remaining hearts are printed in red."""
    assert lives_line(Game(lives=2), color=True).count("\033[1;91m♥") == 2


def test_R4_caught_screen_says_a_life_was_lost_and_how_to_resume():
    """R4: after a catch with lives left the screen explains how to resume."""
    text = screen(caught_once(), color=False)
    assert "You lose a life" in text
    assert "r + Enter" in text
    assert "GAME OVER" not in text and "w/a/s/d" not in text
