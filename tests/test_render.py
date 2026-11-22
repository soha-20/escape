"""Tests for what the player sees."""

from escape_game.game import Game, Status
from escape_game.render import draw_map, lives_line, reaper_line, screen


def rows(game):
    return draw_map(game, color=False).splitlines()


def test_R1_player_is_drawn_and_far_tiles_are_shown():
    """R1 (changed by R9): the player is drawn, and so is the far end of the graveyard: no fog of war."""
    game = Game()
    lines = rows(game)
    assert lines[1][5] == "@"
    assert lines[13][14] == "E"  # the exit, far away, is already on the map
    assert " " not in "".join(lines)  # no blacked-out tiles


def test_R1_reaper_drawn_wherever_it_is():
    """R1 (changed by R9): the reaper is on the map from the start, not only once it is close."""
    game = Game()
    assert rows(game)[1][1] == "R"
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
    walk_to(game, (3, 26))
    assert rows(game)[3][27] == "!"


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


# --- R6 / R7: the graveyard in the terminal ---------------------------------

def walk_to(game, goal):
    """Walk (and, since R12, jump) along the player's route to goal."""
    path = game.maze.player_route(game.player, goal)
    names = {(0, 1): "right", (0, -1): "left", (1, 0): "down", (-1, 0): "up"}
    for a, b in zip(path, path[1:]):
        dr, dc = b[0] - a[0], b[1] - a[1]
        if abs(dr) + abs(dc) == 2:
            game.facing = names[(dr // 2, dc // 2)]
            game.jump()
        else:
            game.move(names[(dr, dc)])


def test_R6_graveyard_objects_are_drawn_with_their_own_marks():
    """R6: fences '#', gravestones '+' and dead trees 'T' appear around the player."""
    game = Game()
    lines = rows(game)
    assert lines[0][5] == "#"   # the graveyard fence
    assert lines[2][5] == "+"   # a gravestone
    assert lines[2][4] == "T"   # a dead tree


def test_R6_intro_and_signs_speak_of_a_graveyard():
    """R6: the story is set in a graveyard; signs are painted on signposts, not walls."""
    from escape_game.render import INTRO, sign_lines
    assert "graveyard" in INTRO and "maze" not in INTRO.lower()
    game = Game()
    walk_to(game, (3, 26))
    assert sign_lines(game, color=False) == ['Painted on a signpost in red: "Wanna get stuck? ←"']


def test_R6_bump_line_names_the_obstacle():
    """R6: walking into something says what it was."""
    from escape_game.render import bump_line
    assert bump_line("iron fence") == "An iron fence blocks your way."
    assert bump_line("gravestone") == "A gravestone blocks your way."
    assert bump_line("dead tree") == "A dead tree blocks your way."


def test_R7_hazards_are_drawn_in_red():
    """R7: open graves 'O' and thorn bushes '*' are marked in red so the player can avoid them."""
    game = Game()
    assert rows(game)[1][9] == "O" and rows(game)[1][19] == "*"  # R9: shown from the start
    coloured = draw_map(game, color=True)
    assert "\033[1;91mO" in coloured and "\033[1;91m*" in coloured


def test_R7_screen_says_which_hazard_took_the_life():
    """R7: after a hazard the screen names it and explains how to resume."""
    game = Game()
    walk_to(game, (1, 8))
    game.move("right")
    text = screen(game, color=False)
    assert "You tumble into an open grave! You lose a life." in text
    assert "r + Enter" in text and "Reaper's cold hand" not in text


def test_R7_game_over_by_hazard_has_its_own_line():
    """R7: losing the last life to a thorn bush says so on the GAME OVER line."""
    from escape_game.maze import Maze
    game = Game(Maze("#######\n#R P*E#\n#######", signs={}), lives=1)
    game.move("right")
    text = screen(game, color=False)
    assert "A thorn bush held you fast. The Reaper only had to wait. GAME OVER." in text


# --- R9: the whole screen is shown --------------------------------------------

def test_R9_the_text_map_shows_the_whole_graveyard_from_the_first_turn():
    """R9: no part of the map is dark: every row is as wide as the graveyard and nothing is blank."""
    game = Game()
    lines = rows(game)
    assert len(lines) == game.maze.height
    assert all(len(line) == game.maze.width and " " not in line for line in lines)


def test_R12_the_text_map_shows_the_gravel_path():
    """R12: the path is drawn as '.' (dim yellow), the grass beside it as ','."""
    game = Game()
    lines = rows(game)
    assert lines[1][6:9] == "..." and lines[3][20] == ","
    assert "\033[2;33m." in draw_map(game, color=True)


# --- R10: low hurdles and the jump in the terminal ------------------------------

def test_R10_low_hurdles_are_drawn_with_their_marks_in_cyan():
    """R10: fallen headstones '=' and coffins 'C' are on the map, coloured so they stand out."""
    game = Game()
    lines = rows(game)
    assert lines[1][23] == "=" and lines[1][14] == "C"
    assert "\033[1;96m=" in draw_map(game, color=True)


def test_R10_bumping_a_low_hurdle_says_how_to_jump_it():
    """R10: the bump message for a low hurdle adds a hint; other obstacles get none."""
    from escape_game.render import bump_line
    assert bump_line("coffin", "Press ↑") == "A coffin blocks your way. Press ↑ to jump over it."
    assert bump_line("gravestone", "Press ↑") == "A gravestone blocks your way."


def test_R10_jump_line_says_why_no_jump_happened():
    """R10: a failed jump is explained."""
    from escape_game.render import jump_line
    assert jump_line("nothing") == "There is nothing here to jump over."
    assert jump_line("gravestone") == "You can't land there: a gravestone is in the way."
    assert jump_line("open grave") == "You can't land there: an open grave is in the way."


def test_R10_controls_and_intro_mention_the_jump():
    """R10: the terminal tells the player that j jumps."""
    from escape_game.render import CONTROLS, INTRO
    assert "j + Enter" in CONTROLS and "type j" in INTRO



# --- R16: the key and the locked gate in the terminal ------------------------------------

def test_R16_the_key_is_drawn_until_it_is_picked_up():
    """R16: the key shows as a gold 'K' on its tile; once taken, the tile is path again."""
    game = Game()
    r, c = game.maze.key
    assert rows(game)[r][c] == "K" and "\033[1;33mK" in draw_map(game, color=True)
    game.has_key = True
    assert rows(game)[r][c] == "."


def test_R16_the_screen_says_whether_the_gate_is_still_locked():
    """R16: the status says to fetch the key, then to run for the gate."""
    game = Game()
    assert "The gate is locked. Fetch the key (K)." in screen(game, color=False)
    game.has_key = True
    assert "You have the key. Run for the gate!" in screen(game, color=False)


def test_R16_bumping_the_locked_gate_says_to_find_the_key():
    """R16: the locked gate has its own bump message (no jump hint)."""
    from escape_game.render import INTRO, bump_line
    assert bump_line("locked gate", "Press ↑") == "The gate is locked. Find the key first."
    assert "key (K)" in INTRO
