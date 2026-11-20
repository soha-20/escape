"""Tests for the graphical game window: figures, signs, lighting and keys.

These open real (hidden) tkinter windows but never play sound.
"""

import tkinter as tk

import pytest

from escape_game.game import Game, Status
from escape_game.gui import (GREEN, HEART_LOST, RED, TILE, VIEW_COLS, VIEW_ROWS, GameWindow, camera_origin,
                             danger_colour, heartbeat_period_ms, light_level, shade)


class FakeSound:
    def __init__(self):
        self.played = []

    def heartbeat(self, distance):
        self.played.append(("heartbeat", distance))

    def caught(self):
        self.played.append(("caught",))

    def escaped(self):
        self.played.append(("escaped",))

    def life_lost(self):
        self.played.append(("life_lost",))


@pytest.fixture(scope="module")
def tk_root():
    try:
        root = tk.Tk()
    except tk.TclError as exc:  # no display available
        pytest.skip(f"tkinter cannot open a window: {exc}")
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def window(tk_root):
    win = GameWindow(tk.Toplevel(tk_root), FakeSound(), threaded_sound=False)
    win.root.withdraw()
    yield win
    win.close()


def texts(win, tag):
    return [win.canvas.itemcget(i, "text") for i in win.canvas.find_withtag(tag)
            if win.canvas.type(i) == "text"]


def centre_of(win, tag):
    x0, y0, x1, y1 = win.canvas.bbox(tag)
    return (x0 + x1) / 2, (y0 + y1) / 2


def press(win, *keys):
    for k in keys:
        win.on_key(k)


CATCH = ("Left", "Left")  # from the start tiles, two steps back: the reaper lands on the player


def lose_all_lives(win):
    """From the title screen, get caught three times (resuming in between)."""
    press(win, "space", *CATCH, "r", *CATCH, "r", *CATCH)


def route_keys(game, goal=None):
    """Arrow keys along the shortest hazard-free way (R7) to goal (default: the exit)."""
    names = {(0, 1): "Right", (0, -1): "Left", (1, 0): "Down", (-1, 0): "Up"}
    path = game.maze.shortest_path(game.player, goal or game.maze.exit, avoid_hazards=True)
    return [names[(b[0] - a[0], b[1] - a[1])] for a, b in zip(path, path[1:])]


FIRST_WARNING = (4, 23)  # the tile in front of the "Wanna get stuck?" signpost
FIRST_GUIDE = (7, 28)    # the tile in front of the guide to the gate between the fields


# --- R1: the game starts; player and reaper are real figures ---------------

def test_R1_window_opens_on_a_title_screen(window):
    """R1: the game starts with a title screen showing the Grim Reaper and the player."""
    assert window.state == window.INTRO
    assert texts(window, "title") == ["ESCAPE THE GRIM REAPER"]
    assert window.canvas.find_withtag("overlay")


def test_R1_any_key_starts_the_chase(window):
    """R1: pressing a key leaves the title screen without moving the player."""
    press(window, "space")
    assert window.state == window.PLAYING
    assert window.game.turn == 0
    assert not window.canvas.find_withtag("overlay")
    assert window.sound.played == [("heartbeat", 4)]


def test_R1_player_figure_is_drawn_on_the_player_tile(window):
    """R1: the player is a drawn figure standing on their tile."""
    press(window, "space")
    x, y = centre_of(window, "player")
    col = int(x // TILE) + window.origin[1]
    row = int(y // TILE) + window.origin[0]
    assert (row, col) == window.game.player
    assert len(window.canvas.find_withtag("player")) > 5  # a figure, not a single character


def test_R1_reaper_figure_appears_only_when_in_torch_light(window):
    """R1: the reaper is drawn (cloak, skull, scythe, eyes) once it is close enough to see."""
    press(window, "space")
    assert not window.canvas.find_withtag("reaper")
    press(window, "Left")  # player (1,4), reaper (1,2): now in view
    assert window.canvas.find_withtag("reaper")
    assert len(window.canvas.find_withtag("reaper_eyes")) == 2


@pytest.mark.parametrize("key,expected", [("Right", (1, 6)), ("d", (1, 6)), ("D", (1, 6)),
                                          ("Left", (1, 4)), ("a", (1, 4))])
def test_R1_arrow_keys_and_wasd_move_with_one_keypress(window, key, expected):
    """R1: one keypress = one move, no Enter needed."""
    press(window, "space", key)
    assert window.game.player == expected
    assert window.game.turn == 1


def test_R1_wall_bump_shows_a_message_and_costs_no_turn(window):
    """R1: walking into something (since R6: the graveyard fence) is explained and does not let the reaper move."""
    press(window, "space", "Up")
    assert window.game.turn == 0
    assert texts(window, "hud_message") == ["An iron fence blocks your way."]


def test_R1_hud_shows_turn_and_reaper_distance(window):
    """R1: the status panel shows the turn and how close the reaper is."""
    press(window, "space", "Right")
    assert texts(window, "hud_turn") == ["Turn 1"]
    assert "4 steps away" in texts(window, "hud_status")[0]
    assert window.canvas.find_withtag("heart")


def test_R1_red_border_warns_when_the_reaper_is_close(window):
    """R1: a red danger border appears when the reaper is 3 steps or fewer away."""
    press(window, "space")
    assert not window.canvas.find_withtag("danger")
    press(window, "Left")
    assert window.canvas.find_withtag("danger")
    assert window.canvas.itemcget("danger", "outline") == RED


def test_R1_escaping_shows_victory_screen_and_plays_escape_sound(window):
    """R1: reaching the exit shows YOU ESCAPED! and plays the rising tune."""
    press(window, "space", *route_keys(window.game))
    assert window.game.status is Status.WON
    assert texts(window, "ending_title") == ["YOU ESCAPED!"]
    assert window.sound.played[-1] == ("escaped",)


def test_R1_r_restarts_after_the_game_ends(window):
    """R1: after the game ends, R starts a fresh chase (with all 3 lives, R4)."""
    lose_all_lives(window)
    assert window.game.status is Status.LOST
    press(window, "r")
    assert window.state == window.PLAYING
    assert window.game.status is Status.PLAYING and window.game.turn == 0
    assert window.game.lives == 3


def test_R1_escape_key_closes_the_window(tk_root):
    """R1: Esc quits the game."""
    win = GameWindow(tk.Toplevel(tk_root), FakeSound(), threaded_sound=False)
    toplevel = win.root
    win.on_key("Escape")
    assert toplevel not in tk_root.winfo_children()


def test_R1_animation_tick_runs(window):
    """R1: the heart, flame, eyes and border animate without errors."""
    press(window, "space", "Left")
    for _ in range(10):
        window._tick()
    assert window.ticks >= 10


# --- R1: pure drawing helpers ---------------------------------------------

def test_R1_torch_light_is_brightest_next_to_the_player():
    """R1: tiles fade with distance from the torch; unseen tiles are pitch black."""
    game = Game()
    near = light_level(game, (1, 6))
    far = light_level(game, (1, 8))
    assert 1 >= near > far > 0
    assert light_level(game, (9, 15)) == 0


def test_R1_remembered_tiles_stay_dimly_lit():
    """R1: tiles you walked past stay faintly visible behind you."""
    game = Game()
    for _ in range(4):
        game.move("right")
    assert 0 < light_level(game, (1, 2)) < light_level(game, (1, 8))


def test_R1_heart_beats_faster_as_the_reaper_closes_in():
    """R1: the on-screen heartbeat speeds up with danger."""
    assert heartbeat_period_ms(8) > heartbeat_period_ms(5) > heartbeat_period_ms(2)
    assert danger_colour(2) == RED


def test_R1_camera_follows_the_player_and_stays_inside_the_maze():
    """R1: the view is centred on the player but never shows outside the maze."""
    game = Game()
    top, left = camera_origin(game)
    assert (top, left) == (0, 0)
    game.player = (9, 20)
    top, left = camera_origin(game)
    assert top + VIEW_ROWS <= game.maze.height and left + VIEW_COLS <= game.maze.width
    assert left <= 20 < left + VIEW_COLS


def test_R1_shade_darkens_colours():
    """R1: lighting is done by darkening colours."""
    assert shade("#ff8040", 1) == "#ff8040"
    assert shade("#ff8040", 0.5) == "#7f4020"
    assert shade("#ff8040", 0) == "#000000"


# --- R2: signs on signposts -------------------------------------------------

def test_R2_sign_message_appears_in_red_at_the_first_fork(window):
    """R2: standing at the first plot's entrance shows "Wanna get stuck?" as a red warning."""
    press(window, "space", *route_keys(window.game, FIRST_WARNING))
    banner = window.canvas.find_withtag("sign_banner")
    assert len(banner) == 1
    assert "Wanna get stuck?" in window.canvas.itemcget(banner[0], "text")
    assert window.canvas.itemcget(banner[0], "fill") == RED


def test_R2_guide_sign_message_is_green(window):
    """R2: a guide sign's message is shown in green."""
    press(window, "space", *route_keys(window.game, FIRST_GUIDE))
    assert window.game.player == FIRST_GUIDE
    banner = window.canvas.find_withtag("sign_banner")
    assert window.canvas.itemcget(banner[0], "fill") == GREEN


def test_R2_signs_are_drawn_as_glowing_signposts(window):
    """R2: signs are drawn as glowing plaques on signposts (R6) once in view."""
    press(window, "space", *route_keys(window.game, (4, 21)))  # two tiles short of the signpost
    assert window.canvas.find_withtag("sign_warning")
    assert not window.canvas.find_withtag("sign_banner")  # not standing next to it yet


def test_R2_exit_door_is_drawn_when_seen(window):
    """R2: the goal of the graveyard is a visible exit gate."""
    keys = route_keys(window.game)
    press(window, "space", *keys[:-2])
    assert "EXIT" in texts(window, "exit")


# --- R3: losing --------------------------------------------------------------

def test_R3_caught_shows_game_over_with_the_reaper(window):
    """R3: being caught on the last life shows GAME OVER, a big reaper and plays the caught sound."""
    lose_all_lives(window)
    assert window.game.status is Status.LOST
    assert texts(window, "ending_title") == ["GAME OVER"]
    assert window.canvas.find_withtag("overlay") and window.canvas.find_withtag("reaper_eyes")
    assert window.sound.played[-1] == ("caught",)


def test_R3_moves_are_ignored_after_game_over(window):
    """R3: once caught on the last life, arrow keys do nothing."""
    lose_all_lives(window)
    turn = window.game.turn
    press(window, "Right", "Right")
    assert window.game.turn == turn and window.game.status is Status.LOST


# --- R4: three lives; R resumes ------------------------------------------------

def test_R4_catch_with_lives_left_shows_caught_screen(window):
    """R4: a catch with lives left shows CAUGHT!, explains R, and plays the life-lost tone."""
    press(window, "space", *CATCH)
    assert window.game.status is Status.CAUGHT
    assert window.state == window.CAUGHT
    assert texts(window, "caught_title") == ["CAUGHT!"]
    assert any("Press R to resume" in t for t in texts(window, "blink"))
    assert not window.canvas.find_withtag("ending_title")
    assert window.sound.played[-1] == ("life_lost",)


def test_R4_moves_are_ignored_until_r_is_pressed(window):
    """R4: while caught, arrow keys do nothing."""
    press(window, "space", *CATCH)
    turn = window.game.turn
    press(window, "Right", "Down", "space")
    assert window.game.turn == turn and window.state == window.CAUGHT


def test_R4_r_resumes_from_the_start_tiles(window):
    """R4: R resumes the chase with the player and reaper back on their start tiles."""
    press(window, "space", *CATCH, "R")
    game = window.game
    assert window.state == window.PLAYING and game.status is Status.PLAYING
    assert (game.player, game.reaper) == (game.maze.player_start, game.maze.reaper_start)
    assert not window.canvas.find_withtag("caught_title")
    assert window.sound.played[-1] == ("heartbeat", 4)
    press(window, "Right")
    assert game.turn == 3


def test_R4_third_catch_is_game_over_and_r_gives_three_new_lives(window):
    """R4: losing all 3 lives ends the game; R then starts over with 3 lives."""
    lose_all_lives(window)
    assert window.state == window.OVER and window.game.lives == 0
    press(window, "r")
    assert window.game.lives == 3 and len(window.canvas.find_withtag("heart")) == 3


# --- R5: three red hearts that empty one by one ------------------------------

def heart_counts(win, full="heart", lost="heart_lost"):
    return len(win.canvas.find_withtag(full)), len(win.canvas.find_withtag(lost))


def test_R5_hud_shows_three_red_hearts_at_the_start(window):
    """R5: the status panel shows three red hearts."""
    press(window, "space")
    assert heart_counts(window) == (3, 0)
    assert all(window.canvas.itemcget(i, "fill") == RED for i in window.canvas.find_withtag("heart"))
    assert set(texts(window, "heart")) == {"♥"}


def test_R5_each_lost_life_turns_one_heart_grey_and_empty(window):
    """R5: the hearts go ♥♥♥ → ♥♥♡ → ♥♡♡, the empty ones grey and on the right."""
    press(window, "space", *CATCH, "r")
    assert heart_counts(window) == (2, 1)
    lost = window.canvas.find_withtag("heart_lost")
    assert texts(window, "heart_lost") == ["♡"]
    assert window.canvas.itemcget(lost[0], "fill") == HEART_LOST
    rightmost_full = max(centre_of(window, i)[0] for i in window.canvas.find_withtag("heart"))
    assert centre_of(window, lost[0])[0] > rightmost_full
    press(window, *CATCH, "r")
    assert heart_counts(window) == (1, 2)


def test_R5_caught_screen_shows_the_hearts_left(window):
    """R5: the CAUGHT! screen shows the lives left as big hearts."""
    press(window, "space", *CATCH)
    assert heart_counts(window, "big_heart", "big_heart_lost") == (2, 1)
    press(window, "r", *CATCH)
    assert heart_counts(window, "big_heart", "big_heart_lost") == (1, 2)


def test_R5_game_over_shows_all_hearts_empty(window):
    """R5: when all lives are lost, GAME OVER shows three empty hearts."""
    lose_all_lives(window)
    assert heart_counts(window, "big_heart", "big_heart_lost") == (0, 3)


def test_R5_hearts_still_beat_with_the_heartbeat(window):
    """R5: the remaining red hearts pulse with the heartbeat; empty ones stay still."""
    press(window, "space", *CATCH, "r")
    sizes = set()
    lost_fonts = set()
    for _ in range(30):
        window._tick()
        sizes.add(window.canvas.itemcget(window.canvas.find_withtag("heart")[0], "font"))
        lost_fonts.add(window.canvas.itemcget(window.canvas.find_withtag("heart_lost")[0], "font"))
    assert len(sizes) > 1 and len(lost_fonts) == 1


# --- R6: the game area is a graveyard ------------------------------------------

def test_R6_graveyard_objects_are_drawn_around_the_player(window):
    """R6: grass, gravestones, the iron fence and a dead tree are drawn in the torch light."""
    press(window, "space")
    for tag in ("grass", "grave", "fence", "tree", "obstacle"):
        assert window.canvas.find_withtag(tag), f"nothing tagged {tag!r} is drawn"
    assert not window.canvas.find_withtag("wall")
    assert len(window.canvas.find_withtag("grave")) >= 3 * 2  # several headstones, each more than one shape


def test_R6_title_screen_tells_of_the_graveyard(window):
    """R6: the story on the title screen is set in a graveyard."""
    story = " ".join(texts(window, "overlay"))
    assert "graves" in story and "maze" not in story.lower()


def test_R6_bumping_a_gravestone_names_it(window):
    """R6: walking into a gravestone says so and costs no turn."""
    press(window, "space", *route_keys(window.game, (3, 8)), "Up")  # (2,8) is a gravestone
    turn = window.game.turn
    press(window, "Up")
    assert window.game.turn == turn
    assert texts(window, "hud_message") == ["A gravestone blocks your way."]


# --- R7: hazards ------------------------------------------------------------------

def test_R7_open_graves_and_thorns_are_drawn_when_in_light(window):
    """R7: hazards are drawn (so they can be avoided) once the torch reaches them."""
    press(window, "space")
    assert not window.canvas.find_withtag("hazard")
    press(window, *route_keys(window.game, (3, 10)))
    assert window.canvas.find_withtag("open_grave") and window.canvas.find_withtag("thorn_bush")
    assert set(window.canvas.find_withtag("open_grave")) <= set(window.canvas.find_withtag("hazard"))


def test_R7_stepping_into_an_open_grave_shows_hurt_screen(window):
    """R7: a hazard costs a life: HURT! names the open grave, shows the player, plays the life-lost tone."""
    press(window, "space", "Right", "Right", "Right", "Right")
    assert window.state == window.CAUGHT and window.game.hurt_by == "open grave"
    assert texts(window, "caught_title") == ["HURT!"]
    assert any("You tumble into an open grave!" in t for t in texts(window, "overlay"))
    assert window.canvas.find_withtag("flame") and not window.canvas.find_withtag("reaper_eyes")
    assert heart_counts(window, "big_heart", "big_heart_lost") == (2, 1)
    assert window.sound.played[-1] == ("life_lost",)


def test_R7_r_resumes_after_a_hazard(window):
    """R7: R after a hazard puts both figures back on their start tiles, with one heart less."""
    press(window, "space", "Right", "Right", "Right", "Right", "r")
    game = window.game
    assert window.state == window.PLAYING
    assert (game.player, game.reaper) == (game.maze.player_start, game.maze.reaper_start)
    assert heart_counts(window) == (2, 1)


def test_R7_game_over_by_hazard_names_it(window):
    """R7: losing the last life in an open grave says so on the GAME OVER screen."""
    press(window, "space", *CATCH, "r", *CATCH, "r", "Right", "Right", "Right", "Right")
    assert window.game.status is Status.LOST
    assert texts(window, "ending_title") == ["GAME OVER"]
    assert any("You fell into an open grave." in t for t in texts(window, "overlay"))
    assert window.sound.played[-1] == ("caught",)


def test_R2_every_sign_message_fits_inside_the_window(window):
    """R2: even the longest signpost text is fully readable in the status panel."""
    press(window, "space")
    for pos in window.game.maze.signs:
        reader = next(p for p in window.game.maze.neighbours(pos))
        window.game.player = reader
        window.redraw()
        x0, _, x1, _ = window.canvas.bbox("sign_banner")
        assert x0 >= 0 and x1 <= window.width, f"sign at {pos} overflows the window"
