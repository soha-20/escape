"""Tests for the graphical game window: figures, signs, lighting and keys.

These open real (hidden) tkinter windows. Since R15 the game makes no sound at all.
"""

import tkinter as tk

import pytest

from escape_game.game import Game, Status
from escape_game.gui import (GREEN, HEART_LOST, MOONLIGHT, RED, TILE, TORCH_REACH, VIEW_COLS, VIEW_ROWS, GameWindow,
                             camera_origin, danger_colour, heartbeat_period_ms, light_level, shade, torch_glow)


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
    win = GameWindow(tk.Toplevel(tk_root), animate=False)
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
    """Keys along the player's way (R7, R12) to goal (default: the exit). North is W: Up jumps (R10).

    R12: the hurdles on the path are always met running straight, so Up jumps the right way."""
    names = {(0, 1): "Right", (0, -1): "Left", (1, 0): "Down", (-1, 0): "w"}
    path = game.maze.player_route(game.player, goal or game.maze.exit)
    keys = []
    for a, b in zip(path, path[1:]):
        dr, dc = b[0] - a[0], b[1] - a[1]
        keys.append("Up" if abs(dr) + abs(dc) == 2 else names[(dr, dc)])
    return keys


FIRST_WARNING = (3, 26)  # the tile in front of the "Wanna get stuck?" signpost (R12 layout)
FIRST_GUIDE = (1, 25)    # the tile in front of the first guide, before the first bend


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
    assert not hasattr(window, "sound")  # R15: no heartbeat sound any more


def test_R1_player_figure_is_drawn_on_the_player_tile(window):
    """R1: the player is a drawn figure standing on their tile."""
    press(window, "space")
    x, y = centre_of(window, "player")
    col = int(x // TILE) + window.origin[1]
    row = int(y // TILE) + window.origin[0]
    assert (row, col) == window.game.player
    assert len(window.canvas.find_withtag("player")) > 5  # a figure, not a single character


def test_R1_reaper_figure_is_drawn_whenever_it_is_in_view(window):
    """R1 (changed by R9): the reaper (cloak, skull, scythe, eyes) is drawn as soon as it is on screen."""
    press(window, "space")
    assert window.canvas.find_withtag("reaper")
    assert len(window.canvas.find_withtag("reaper_eyes")) == 2


@pytest.mark.parametrize("key,start,expected", [("Right", None, (1, 6)), ("d", None, (1, 6)), ("D", None, (1, 6)),
                                                ("Left", None, (1, 4)), ("a", None, (1, 4)),
                                                ("Down", (1, 26), (2, 26)), ("s", (1, 26), (2, 26))])
def test_R1_arrow_keys_and_wasd_move_with_one_keypress(window, key, start, expected):
    """R1: one keypress = one move, no Enter needed. (R12: down from the start is a gravestone, so the
    downward keys are tried at the first bend.)"""
    press(window, "space")
    if start:
        window.game.player = start
    press(window, key)
    assert window.game.player == expected
    assert window.game.turn == 1


def test_R1_wall_bump_shows_a_message_and_costs_no_turn(window):
    """R1: walking into something (since R6: the graveyard fence) is explained and does not let the reaper move.

    Since R10 the Up arrow jumps, so north is W."""
    press(window, "space", "w")
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


def test_R1_escaping_shows_victory_screen(window):
    """R1: reaching the exit shows YOU ESCAPED! (Changed by R15: no rising tune any more.)"""
    press(window, "space", *route_keys(window.game))
    assert window.game.status is Status.WON
    assert texts(window, "ending_title") == ["YOU ESCAPED!"]


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
    win = GameWindow(tk.Toplevel(tk_root))
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
    """R1 (changed by R9): tiles near the torch are brightest; far tiles are moonlit, never black."""
    game = Game()
    near = light_level(game, (1, 6))
    far = light_level(game, (1, 8))
    assert 1 >= near > far >= MOONLIGHT
    assert light_level(game, (9, 15)) == MOONLIGHT


def test_R1_tiles_behind_the_player_stay_moonlit():
    """R1 (changed by R9): tiles you walked past are as bright as any other tile away from the torch."""
    game = Game()
    for _ in range(4):
        game.move("right")
    assert light_level(game, (1, 2)) == MOONLIGHT == light_level(game, (14, 25))


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
    press(window, "space", *route_keys(window.game, (1, 20)))  # well short of the signposts
    assert window.canvas.find_withtag("sign_warning")
    assert not window.canvas.find_withtag("sign_banner")  # not standing next to it yet


def test_R2_exit_door_is_drawn_when_seen(window):
    """R2: the goal of the graveyard is a visible exit gate."""
    keys = route_keys(window.game)
    press(window, "space", *keys[:-2])
    assert "EXIT" in texts(window, "exit")


# --- R3: losing --------------------------------------------------------------

def test_R3_caught_shows_game_over_with_the_reaper(window):
    """R3: being caught on the last life shows GAME OVER and a big reaper. (R15: silently.)"""
    lose_all_lives(window)
    assert window.game.status is Status.LOST
    assert texts(window, "ending_title") == ["GAME OVER"]
    assert window.canvas.find_withtag("overlay") and window.canvas.find_withtag("reaper_eyes")


def test_R3_moves_are_ignored_after_game_over(window):
    """R3: once caught on the last life, arrow keys do nothing."""
    lose_all_lives(window)
    turn = window.game.turn
    press(window, "Right", "Right")
    assert window.game.turn == turn and window.game.status is Status.LOST


# --- R4: three lives; R resumes ------------------------------------------------

def test_R4_catch_with_lives_left_shows_caught_screen(window):
    """R4: a catch with lives left shows CAUGHT! and explains R. (R15: no life-lost tone any more.)"""
    press(window, "space", *CATCH)
    assert window.game.status is Status.CAUGHT
    assert window.state == window.CAUGHT
    assert texts(window, "caught_title") == ["CAUGHT!"]
    assert any("Press R to resume" in t for t in texts(window, "blink"))
    assert not window.canvas.find_withtag("ending_title")


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
    press(window, "space", *route_keys(window.game, (1, 8)), "s")  # (2,8) is a gravestone
    turn = window.game.turn
    press(window, "s")
    assert window.game.turn == turn
    assert texts(window, "hud_message") == ["A gravestone blocks your way."]


# --- R7: hazards ------------------------------------------------------------------

def test_R7_open_graves_and_thorns_are_drawn_when_in_light(window):
    """R7 (changed by R9): hazards on screen are drawn from the start, so they can be avoided."""
    press(window, "space")
    assert window.canvas.find_withtag("open_grave") and window.canvas.find_withtag("thorn_bush")
    assert set(window.canvas.find_withtag("open_grave")) <= set(window.canvas.find_withtag("hazard"))


def test_R7_stepping_into_an_open_grave_shows_hurt_screen(window):
    """R7: a hazard costs a life: HURT! names the open grave and shows the player. (R15: silently.)"""
    press(window, "space", "Right", "Right", "Right", "Right")
    assert window.state == window.CAUGHT and window.game.hurt_by == "open grave"
    assert texts(window, "caught_title") == ["HURT!"]
    assert any("You tumble into an open grave!" in t for t in texts(window, "overlay"))
    overlay = set(window.canvas.find_withtag("overlay"))
    assert overlay & set(window.canvas.find_withtag("flame"))          # the big figure is the player...
    assert not overlay & set(window.canvas.find_withtag("reaper_eyes"))  # ...not the reaper
    assert heart_counts(window, "big_heart", "big_heart_lost") == (2, 1)


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


def test_R2_every_sign_message_fits_inside_the_window(window):
    """R2: even the longest signpost text is fully readable in the status panel."""
    press(window, "space")
    for pos in window.game.maze.signs:
        reader = next(p for p in window.game.maze.neighbours(pos))
        window.game.player = reader
        window.redraw()
        x0, _, x1, _ = window.canvas.bbox("sign_banner")
        assert x0 >= 0 and x1 <= window.width, f"sign at {pos} overflows the window"


# --- R9: the whole view is lit -------------------------------------------------

def test_R9_every_tile_in_view_is_at_least_moonlit():
    """R9: wherever the player stands, no tile on screen is darker than moonlight."""
    game = Game()
    for player in [game.maze.player_start, (7, 27), (13, 3), game.maze.exit]:
        game.player = player
        top, left = camera_origin(game)
        for r in range(top, top + VIEW_ROWS):
            for c in range(left, left + VIEW_COLS):
                assert light_level(game, (r, c)) >= MOONLIGHT


def test_R9_torch_glow_is_strongest_at_the_player_and_fades_out():
    """R9: the torch only adds a warm glow around the player."""
    assert torch_glow((5, 5), (5, 5)) == 1
    assert 1 > torch_glow((5, 5), (5, 6)) > torch_glow((5, 5), (5, 7)) > 0
    assert torch_glow((5, 5), (5, 5 + TORCH_REACH)) == 0


def test_R9_the_whole_view_is_drawn_not_just_near_the_torch(window):
    """R9: every tile on screen has ground drawn on it, at the start and far from it."""
    press(window, "space")
    assert len(window.canvas.find_withtag("floor")) >= VIEW_ROWS * VIEW_COLS
    window.game.player = (12, 20)
    window.redraw()
    assert len(window.canvas.find_withtag("floor")) >= VIEW_ROWS * VIEW_COLS


# --- R10: jumping in the window ---------------------------------------------------

def test_R10_up_arrow_jumps_the_open_grave_east_of_the_start(window):
    """R10: facing the open grave, Up leaps over it: two tiles, one turn, no life lost."""
    press(window, "space", "Right", "Right", "Right", "Up")
    game = window.game
    assert game.player == (1, 10) and game.turn == 4 and game.lives == 3
    assert window.state == window.PLAYING


def test_R10_w_still_moves_north_but_up_no_longer_does(window):
    """R10: north is W; Up in front of plain ground does nothing and says so. (R12: tried on the first bend.)"""
    press(window, "space")
    window.game.player = (4, 26)
    press(window, "w")
    assert window.game.player == (3, 26) and window.game.turn == 1
    press(window, "Up")
    assert window.game.player == (3, 26) and window.game.turn == 1
    assert texts(window, "hud_message") == ["There is nothing here to jump over."]


def test_R10_bumping_a_low_hurdle_tells_how_to_jump_it(window):
    """R10: walking into a coffin explains the Up arrow; then Up clears it."""
    press(window, "space", *route_keys(window.game, (1, 13)), "Right")
    assert texts(window, "hud_message") == ["A coffin blocks your way. Press ↑ to jump over it."]
    turn, gap = window.game.turn, window.game.reaper_distance()
    press(window, "Up")
    assert window.game.player == (1, 15) and window.game.turn == turn + 1
    assert window.game.reaper_distance() == gap + 1  # the jump gained a step on the reaper


def test_R10_low_hurdles_are_drawn_as_a_fallen_headstone_and_coffins(window):
    """R10: low hurdles on screen are drawn with their own tags, apart from blocking obstacles."""
    press(window, "space")
    window.game.player = (1, 20)
    window.redraw()
    assert window.canvas.find_withtag("coffin") and window.canvas.find_withtag("fallen_headstone")
    low = set(window.canvas.find_withtag("low_hurdle"))
    assert set(window.canvas.find_withtag("coffin")) <= low
    assert not low & set(window.canvas.find_withtag("obstacle"))


def test_R10_controls_and_title_screen_mention_the_jump(window):
    """R10: the title story and the controls line explain the Up arrow."""
    assert any("↑" in t and "leap" in t for t in texts(window, "overlay"))
    press(window, "space")
    assert any("↑  jump" in t for t in texts(window, "hud"))


# --- R8: figures that move -------------------------------------------------------

from escape_game.gui import (JUMP_FRAMES, SLIDE_FRAMES, camera_at, ease, hover, jump_height,  # noqa: E402
                             lit, tween, walk_pose)


@pytest.fixture
def animated(tk_root):
    """A window that shows each turn as a slide, driven by calling _tick() by hand."""
    win = GameWindow(tk.Toplevel(tk_root), animate=True)
    win.root.withdraw()
    win.root.after_cancel(win._after)
    real_after = win.root.after
    win.root.after = lambda ms, func: real_after(10 ** 7, lambda: None)  # the test drives the frames
    yield win
    win.close()


def tile_of(win, tag):
    """The (fractional) tile under the centre of the figure's feet."""
    x0, _, x1, y1 = win.canvas.bbox(tag)
    return (y1 - TILE * 0.8) / TILE + win.origin[0], (x0 + x1) / 2 / TILE - 0.5 + win.origin[1]


def test_R8_ease_and_tween_slide_smoothly_from_tile_to_tile():
    """R8: a slide starts and ends gently and passes every point in between."""
    assert ease(0) == 0 and ease(1) == 1 and ease(0.5) == 0.5
    assert ease(0.1) < 0.1 and ease(0.9) > 0.9
    assert tween((1, 5), (1, 6), 0.5) == (1, 5.5)


def test_R8_walk_pose_swings_legs_forward_and_back_once_per_step():
    """R8: the walk cycle swings one way, then the other, and ends where it started."""
    assert walk_pose(0) == 0 and abs(walk_pose(1)) < 1e-9
    assert walk_pose(0.25) == pytest.approx(1) and walk_pose(0.75) == pytest.approx(-1)


def test_R8_jump_rises_and_lands():
    """R8 / R10: the jump arc is highest in the middle and on the ground at both ends."""
    assert jump_height(0) == 0 and jump_height(1) == pytest.approx(0, abs=1e-9)
    assert jump_height(0.5) > jump_height(0.2) > 0


def test_R8_player_slides_to_the_next_tile_over_several_frames(animated):
    """R8: after a move the figure is first still on the old tile, then between tiles, then on the new one."""
    press(animated, "space", "Right")
    assert animated.game.player == (1, 6)              # the rules moved at once
    assert tile_of(animated, "player")[1] == pytest.approx(5, abs=0.15)
    animated._tick()
    animated._tick()
    middle = tile_of(animated, "player")[1]
    assert 5.1 < middle < 5.9
    for _ in range(SLIDE_FRAMES):
        animated._tick()
    assert animated.motion is None
    assert tile_of(animated, "player")[1] == pytest.approx(6, abs=0.15)


def test_R8_legs_move_while_walking(animated):
    """R8: the legs are drawn in a different pose on different frames of a step."""
    press(animated, "space", "Right")
    poses = set()
    for _ in range(SLIDE_FRAMES - 1):
        animated._tick()
        poses.add(tuple(round(v) for i in animated.canvas.find_withtag("player_leg")
                        for v in animated.canvas.coords(i)))
    assert len(poses) >= 3


def test_R8_player_faces_the_way_they_walk(animated):
    """R8: walking left mirrors the figure (the torch moves to the other side)."""
    press(animated, "space")
    right_torch = centre_of(animated, "flame")[0] - centre_of(animated, "player")[0]
    press(animated, "Left")
    for _ in range(SLIDE_FRAMES):
        animated._tick()
    left_torch = centre_of(animated, "flame")[0] - centre_of(animated, "player")[0]
    assert right_torch > 0 > left_torch


def test_R8_the_reaper_glides_and_hovers(animated):
    """R8 / R11: the reaper slides after the player and keeps floating while it waits."""
    press(animated, "space", "Right")  # the reaper glides from (1,1) to (1,2)
    animated._tick()
    animated._tick()
    x0, _, x1, _ = animated.canvas.bbox("aura")  # the aura on the ground follows the reaper
    assert 1.1 < (x0 + x1) / 2 / TILE - 0.5 < 1.9
    for _ in range(SLIDE_FRAMES):
        animated._tick()
    tops = set()
    for _ in range(12):
        animated._tick()
        tops.add(round(animated.canvas.bbox("reaper")[1]))
    assert len(tops) > 1
    assert abs(hover(0) - hover(1200)) > 0


def test_R8_the_camera_scrolls_smoothly(animated):
    """R8: when the view has to follow the player, it moves part of a tile per frame, not all at once."""
    press(animated, "space")
    animated.game.player = (1, 12)
    animated.redraw()
    left = animated.origin[1]
    press(animated, "Right")
    animated._tick()
    animated._tick()
    assert left < animated.origin[1] < left + 1
    for _ in range(SLIDE_FRAMES):
        animated._tick()
    assert animated.origin == camera_at(animated.game.maze, animated.game.player)


def test_R8_a_key_during_a_slide_finishes_it_and_takes_the_next_move(animated):
    """R8: fast typing never lags: the next key finishes the slide and moves again."""
    press(animated, "space", "Right")
    animated._tick()
    press(animated, "Right")
    assert animated.game.player == (1, 7) and animated.game.turn == 2
    assert animated.motion.player_from == (1, 6)


def test_R8_the_caught_screen_waits_until_the_slide_is_seen(animated):
    """R8: the life-lost screen appears after the reaper has visibly reached the player."""
    press(animated, "space", *CATCH)
    assert animated.state == animated.CAUGHT and not animated.canvas.find_withtag("caught_title")
    for _ in range(SLIDE_FRAMES):
        animated._tick()
    assert texts(animated, "caught_title") == ["CAUGHT!"]


def test_R8_a_key_after_the_last_move_still_shows_the_end_screen(animated):
    """R8: a key pressed while the final slide plays shows the GAME OVER screen at once."""
    press(animated, "space", *CATCH, "r", *CATCH, "r", *CATCH)
    press(animated, "Left")
    assert texts(animated, "ending_title") == ["GAME OVER"]


def test_R8_jump_lifts_the_player_off_the_ground(animated):
    """R8 / R10: mid-jump the figure is above its shadow; it lands two tiles on."""
    press(animated, "space", "Right", "Right", "Right")
    for _ in range(SLIDE_FRAMES):
        animated._tick()
    ground = animated.canvas.bbox("player")[3]
    press(animated, "Up")
    for _ in range(JUMP_FRAMES // 2):
        animated._tick()
    assert animated.canvas.bbox("player")[3] < ground - TILE * 0.3
    assert animated.canvas.find_withtag("player_shadow")
    for _ in range(JUMP_FRAMES):
        animated._tick()
    assert tile_of(animated, "player")[1] == pytest.approx(10, abs=0.15)


# --- R9 / R11: light and colour ---------------------------------------------------

def test_R9_the_torch_warms_colours_and_the_moon_cools_them():
    """R9: near the torch colours turn orange-warm; far away they turn moon-blue, never black."""
    near, far = lit("#808080", 1.0, 1.0), lit("#808080", 0.8, 0.0)
    r_near, b_near = int(near[1:3], 16), int(near[5:7], 16)
    r_far, b_far = int(far[1:3], 16), int(far[5:7], 16)
    assert r_near > b_near and b_far > r_far
    assert min(r_far, b_far) > 0x50


# --- R11: a scary reaper and a haunted graveyard ----------------------------------

def test_R11_the_reaper_towers_over_the_player(window):
    """R11: the reaper is about 1.6 tiles tall, much taller than the player."""
    press(window, "space")
    _, top, _, bottom = window.canvas.bbox("reaper")
    _, ptop, _, pbottom = window.canvas.bbox("player")
    assert bottom - top > 1.4 * TILE
    assert bottom - top > 1.3 * (pbottom - ptop)


def test_R11_the_reaper_has_glowing_eyes_a_scythe_and_an_aura(window):
    """R11: glowing eyes, a scythe blade and a red aura on the ground."""
    press(window, "space")
    for tag in ("reaper_eyes", "reaper_glow", "scythe", "aura"):
        assert window.canvas.find_withtag(tag), f"nothing tagged {tag!r}"


def test_R11_the_aura_pulses_faster_when_the_reaper_is_close():
    """R11: the aura beats with the heartbeat, which speeds up as the reaper closes in."""
    assert heartbeat_period_ms(2) < heartbeat_period_ms(8)


def test_R11_mist_drifts_across_the_graveyard(window):
    """R11: wisps of mist are drawn over the graveyard and drift with time."""
    press(window, "space")
    before = [window.canvas.coords(i)[0] for i in window.canvas.find_withtag("mist")]
    assert before
    for _ in range(8):
        window._tick()
    after = [window.canvas.coords(i)[0] for i in window.canvas.find_withtag("mist")]
    assert after != before


def test_R11_nothing_relies_on_transparency(window):
    """R11: Tk on Windows draws stippled shapes solid, so no item may use a stipple."""
    for state_keys in ((), ("space",), CATCH):
        press(window, *state_keys)
        for i in window.canvas.find_all():
            if "stipple" in window.canvas.itemconfigure(i):
                assert window.canvas.itemcget(i, "stipple") == ""


def test_R11_title_and_end_screens_have_a_moon_and_a_shadowed_title(window):
    """R11: the title is blood red with a dark shadow beneath it."""
    title = window.canvas.find_withtag("title")[0]
    shadows = [i for i in window.canvas.find_withtag("overlay")
               if window.canvas.type(i) == "text" and window.canvas.itemcget(i, "text") == "ESCAPE THE GRIM REAPER"]
    assert len(shadows) == 2 and window.canvas.itemcget(title, "fill") == RED
