"""Tests for the graphical game window: figures, signs, lighting, keys, and (since round 5) real time.

These open real (hidden) tkinter windows. Since R15 the game makes no sound at all.

Round 5 (R13, R14) made the window real-time: a key pressed moves the player at once, a held key keeps
them running, and the Reaper moves on its own clock. The windows here run without their frame timer
(autorun=False); the tests let time pass with advance(ms). The round-1 to round-4 tests below were
adapted to that (keys are now tapped: pressed, released, and given the time a step takes) and to the
whole graveyard being on screen (no camera), keeping their requirement IDs; none were deleted.
"""

import time
import tkinter as tk

import pytest

from escape_game.game import JUMP_MS, PLAYER_STEP_MS, REAPER_STEP_MS, Status
from escape_game.gui import (BLOOD, BORDER, CONTROLS, GREEN, HEART_LOST, HUD_HEIGHT, MAX_FRAME_MS, MOONLIGHT,
                             RED, TILE, TORCH_TINT, GameWindow, danger_colour, heartbeat_period_ms, shade)


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
    win = GameWindow(tk.Toplevel(tk_root), autorun=False)
    win.root.withdraw()
    yield win
    win.close()


def canvas_for(win, tag):
    """The HUD has its own canvas since R14: look there if the graveyard canvas has nothing with the tag."""
    return win.canvas if win.canvas.find_withtag(tag) else win.hud


def texts(win, tag):
    cv = canvas_for(win, tag)
    return [cv.itemcget(i, "text") for i in cv.find_withtag(tag) if cv.type(i) == "text"]


def centre_of(win, tag, cv=None):
    cv = cv or canvas_for(win, tag)
    x0, y0, x1, y1 = cv.bbox(tag)
    return (x0 + x1) / 2, (y0 + y1) / 2


MOVE_KEYS = {"Right", "Left", "Down", "Up", "w", "W", "a", "A", "s", "S", "d", "D"}


def settle(win):
    """Let the player's step (or jump) finish; once the chase is over, let both figures finish theirs,
    so the screen that waits for them (R8) is shown."""
    g = win.game
    end = g.player_moved_at + g.player_move_ms
    if g.status is not Status.PLAYING:
        end = max(end, g.reaper_moved_at + g.reaper_move_ms)
    win.advance(max(0.0, end - g.clock))


def press(win, *keys):
    """Tap keys one after another like a player: a movement key goes down and up again, then the step
    it started is given the time it takes."""
    for k in keys:
        win.on_key(k)
        if k in MOVE_KEYS:
            win.on_key_up(k)
            settle(win)
        else:
            win.advance(0)


def get_caught(win):
    """From the start tiles, one step back toward the Reaper, then wait: it reaches the player (R13)."""
    press(win, "Left")
    while win.game.status is Status.PLAYING:
        win.advance(50)
    settle(win)


def lose_all_lives(win):
    """From the title screen, get caught three times (resuming in between)."""
    press(win, "space")
    get_caught(win)
    press(win, "r")
    get_caught(win)
    press(win, "r")
    get_caught(win)


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


def tile_of(win, tag="player"):
    """The (fractional) tile under the centre of the figure's feet."""
    x0, _, x1, y1 = win.canvas.bbox(tag)
    return (y1 - TILE * 0.8) / TILE, (x0 + x1) / 2 / TILE - 0.5


def heart_counts(win, full="heart", lost="heart_lost"):
    cv = win.canvas if (win.canvas.find_withtag(full) or win.canvas.find_withtag(lost)) else win.hud
    return len(cv.find_withtag(full)), len(cv.find_withtag(lost))


def torch_rings(win):
    return [(win.canvas.bbox(i), win.canvas.itemcget(i, "outline")) for i in win.canvas.find_withtag("torch_glow")]


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
    assert (int(y // TILE), int(x // TILE)) == window.game.player
    assert len(window.canvas.find_withtag("player")) > 5  # a figure, not a single character


def test_R1_reaper_figure_is_drawn_whenever_it_is_in_view(window):
    """R1 (changed by R9, R14): the reaper (cloak, skull, scythe, eyes) is always drawn: all is in view."""
    press(window, "space")
    assert window.canvas.find_withtag("reaper")
    assert len(window.canvas.find_withtag("reaper_eyes")) == 2


@pytest.mark.parametrize("key,start,expected", [("Right", None, (1, 6)), ("d", None, (1, 6)), ("D", None, (1, 6)),
                                                ("Left", None, (1, 4)), ("a", None, (1, 4)),
                                                ("Down", (1, 26), (2, 26)), ("s", (1, 26), (2, 26))])
def test_R1_arrow_keys_and_wasd_move_with_one_keypress(window, key, start, expected):
    """R1: one keypress = one move, no Enter needed; since R14 the move starts the moment the key goes down.
    (R12: down from the start is a gravestone, so the downward keys are tried at the first bend.)"""
    press(window, "space")
    if start:
        window.game.player = start
    window.on_key(key)
    assert window.game.player == expected
    assert window.game.turn == 1


def test_R1_wall_bump_shows_a_message_and_costs_no_turn(window):
    """R1: walking into something (since R6: the graveyard fence) is explained and does not move the player.

    Since R10 the Up arrow jumps, so north is W."""
    press(window, "space", "w")
    assert window.game.turn == 0
    assert texts(window, "hud_message") == ["An iron fence blocks your way."]


def test_R1_hud_shows_time_and_reaper_distance(window):
    """R1 (changed by R13): the status panel shows the running time (no turns in real time) and how close
    the reaper is."""
    press(window, "space", "Right")
    assert texts(window, "hud_turn") == [f"Time {PLAYER_STEP_MS / 1000:.1f} s"]
    assert "steps away" in texts(window, "hud_status")[0]
    assert window.hud.find_withtag("heart")


def test_R1_red_border_warns_when_the_reaper_is_close(window):
    """R1 (changed by R14): the frame around the graveyard glows red when the reaper is 3 steps or fewer away."""
    press(window, "space")
    assert window.border.cget("bg") == "#000000"
    press(window, "Left")  # (1,4): the reaper comes on
    window.advance(REAPER_STEP_MS)
    assert window.game.reaper_distance() <= 3
    assert window.border.cget("bg") in (RED, BLOOD)
    assert not window.canvas.find_withtag("danger")  # a frame colour, not canvas items (R14)


def test_R1_escaping_shows_victory_screen(window):
    """R1: reaching the exit shows YOU ESCAPED! (Changed by R15: no rising tune any more.)"""
    press(window, "space", *route_keys(window.game))
    assert window.game.status is Status.WON
    assert texts(window, "ending_title") == ["YOU ESCAPED!"]
    assert any("seconds" in t for t in texts(window, "overlay"))  # R13: the run's time


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
    """R1: the heart, flame, eyes and border animate on the frame timer without errors."""
    press(window, "space", "Left")
    window._last = time.perf_counter()
    window._next_frame = window._last
    for _ in range(10):
        window._tick()
    assert window.ticks >= 10


# --- R1: drawing helpers ------------------------------------------------------

def test_R1_torch_light_is_brightest_next_to_the_player(window):
    """R1 (changed by R9, R14): the torch glows in warm rings centred on the player; the inner ring is the
    brightest, and the tiles themselves stay moonlit."""
    press(window, "space")
    rings = sorted(torch_rings(window), key=lambda r: r[0][2] - r[0][0])
    assert len(rings) == 2
    (inner, inner_colour), (outer, outer_colour) = rings
    px, _ = centre_of(window, "player_shadow")
    assert abs((inner[0] + inner[2]) / 2 - px) < 2 and abs((outer[0] + outer[2]) / 2 - px) < 2
    assert inner_colour == TORCH_TINT and outer_colour == shade(TORCH_TINT, 0.55)


def test_R1_tiles_behind_the_player_stay_moonlit(window):
    """R1 (changed by R9, R14): the tiles never change as the player moves: they are all equally moonlit."""
    press(window, "space")
    before = {i: window.canvas.itemcget(i, "fill") for i in window.canvas.find_withtag("floor")}
    press(window, "Right", "Right")
    after = {i: window.canvas.itemcget(i, "fill") for i in window.canvas.find_withtag("floor")}
    assert after == before


def test_R1_heart_beats_faster_as_the_reaper_closes_in():
    """R1: the on-screen heartbeat speeds up with danger."""
    assert heartbeat_period_ms(8) > heartbeat_period_ms(5) > heartbeat_period_ms(2)
    assert danger_colour(2) == RED


def test_R1_the_whole_graveyard_is_in_view_and_fits_the_screen(window):
    """R1 (changed by R14): instead of a camera following the player, the whole graveyard is shown at once,
    and the window fits a 1280 x 720 screen."""
    maze = window.game.maze
    size = (int(window.canvas.cget("width")), int(window.canvas.cget("height")))
    assert size == (maze.width * TILE, maze.height * TILE)
    assert maze.width * TILE + 2 * BORDER <= 1280
    assert maze.height * TILE + 2 * BORDER + HUD_HEIGHT <= 720 - 48 - 32  # taskbar and title bar


def test_R1_shade_darkens_colours():
    """R1: lighting is done by darkening colours."""
    assert shade("#ff8040", 1) == "#ff8040"
    assert shade("#ff8040", 0.5) == "#7f4020"
    assert shade("#ff8040", 0) == "#000000"


# --- R2: signs on signposts -------------------------------------------------

def test_R2_sign_message_appears_in_red_at_the_first_fork(window):
    """R2: standing at the first dead end's entrance shows "Wanna get stuck?" as a red warning."""
    press(window, "space", *route_keys(window.game, FIRST_WARNING))
    banner = window.hud.find_withtag("sign_banner")
    assert len(banner) == 1
    assert "Wanna get stuck?" in window.hud.itemcget(banner[0], "text")
    assert window.hud.itemcget(banner[0], "fill") == RED


def test_R2_guide_sign_message_is_green(window):
    """R2: a guide sign's message is shown in green."""
    press(window, "space", *route_keys(window.game, FIRST_GUIDE))
    assert window.game.player == FIRST_GUIDE
    banner = window.hud.find_withtag("sign_banner")
    assert window.hud.itemcget(banner[0], "fill") == GREEN


def test_R2_signs_are_drawn_as_glowing_signposts(window):
    """R2: signs are drawn as glowing plaques on signposts (R6), and read only when standing next to one."""
    press(window, "space")
    assert window.canvas.find_withtag("sign_warning") and window.canvas.find_withtag("sign_guide")
    assert not window.hud.find_withtag("sign_banner")  # not standing next to one yet


def test_R2_exit_door_is_drawn_when_seen(window):
    """R2: the goal of the graveyard is a visible exit gate (since R14 in view from the start)."""
    press(window, "space")
    assert "EXIT" in texts(window, "exit")


def test_R2_every_sign_message_fits_inside_the_window(window):
    """R2: even the longest signpost text is fully readable in the status panel."""
    press(window, "space")
    for pos in window.game.maze.signs:
        reader = next(p for p in window.game.maze.neighbours(pos))
        window.game.player = reader
        window.advance(0)
        x0, _, x1, _ = window.hud.bbox("sign_banner")
        assert x0 >= 0 and x1 <= int(window.hud.cget("width")), f"sign at {pos} overflows the window"


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
    press(window, "space")
    get_caught(window)
    assert window.game.status is Status.CAUGHT
    assert window.state == window.CAUGHT
    assert texts(window, "caught_title") == ["CAUGHT!"]
    assert any("Press R to resume" in t for t in texts(window, "blink"))
    assert not window.canvas.find_withtag("ending_title")


def test_R4_moves_are_ignored_until_r_is_pressed(window):
    """R4: while caught, arrow keys do nothing."""
    press(window, "space")
    get_caught(window)
    turn = window.game.turn
    press(window, "Right", "Down", "space")
    assert window.game.turn == turn and window.state == window.CAUGHT


def test_R4_r_resumes_from_the_start_tiles(window):
    """R4: R resumes the chase with the player and reaper back on their start tiles."""
    press(window, "space")
    get_caught(window)
    press(window, "R")
    game = window.game
    assert window.state == window.PLAYING and game.status is Status.PLAYING
    assert (game.player, game.reaper) == (game.maze.player_start, game.maze.reaper_start)
    assert not window.canvas.find_withtag("caught_title")
    turn = game.turn
    press(window, "Right")
    assert game.turn == turn + 1


def test_R4_third_catch_is_game_over_and_r_gives_three_new_lives(window):
    """R4: losing all 3 lives ends the game; R then starts over with 3 lives."""
    lose_all_lives(window)
    assert window.state == window.OVER and window.game.lives == 0
    press(window, "r")
    assert window.game.lives == 3 and len(window.hud.find_withtag("heart")) == 3


# --- R5: three red hearts that empty one by one ------------------------------

def test_R5_hud_shows_three_red_hearts_at_the_start(window):
    """R5: the status panel shows three red hearts."""
    press(window, "space")
    assert heart_counts(window) == (3, 0)
    assert all(window.hud.itemcget(i, "fill") == RED for i in window.hud.find_withtag("heart"))
    assert set(texts(window, "heart")) == {"♥"}


def test_R5_each_lost_life_turns_one_heart_grey_and_empty(window):
    """R5: the hearts go ♥♥♥ → ♥♥♡ → ♥♡♡, the empty ones grey and on the right."""
    press(window, "space")
    get_caught(window)
    press(window, "r")
    assert heart_counts(window) == (2, 1)
    hud = window.hud
    lost = hud.find_withtag("heart_lost")
    assert texts(window, "heart_lost") == ["♡"]
    assert hud.itemcget(lost[0], "fill") == HEART_LOST
    rightmost_full = max(centre_of(window, i, hud)[0] for i in hud.find_withtag("heart"))
    assert centre_of(window, lost[0], hud)[0] > rightmost_full
    get_caught(window)
    press(window, "r")
    assert heart_counts(window) == (1, 2)


def test_R5_caught_screen_shows_the_hearts_left(window):
    """R5: the CAUGHT! screen shows the lives left as big hearts."""
    press(window, "space")
    get_caught(window)
    assert heart_counts(window, "big_heart", "big_heart_lost") == (2, 1)
    press(window, "r")
    get_caught(window)
    assert heart_counts(window, "big_heart", "big_heart_lost") == (1, 2)


def test_R5_game_over_shows_all_hearts_empty(window):
    """R5: when all lives are lost, GAME OVER shows three empty hearts."""
    lose_all_lives(window)
    assert heart_counts(window, "big_heart", "big_heart_lost") == (0, 3)


def test_R5_hearts_still_beat_with_the_heartbeat(window):
    """R5: the remaining red hearts pulse with the heartbeat; empty ones stay still."""
    press(window, "space")
    get_caught(window)
    press(window, "r")
    sizes, lost_fonts = set(), set()
    for _ in range(30):
        window.advance(40)
        sizes.add(window.hud.itemcget(window.hud.find_withtag("heart")[0], "font"))
        lost_fonts.add(window.hud.itemcget(window.hud.find_withtag("heart_lost")[0], "font"))
    assert len(sizes) > 1 and len(lost_fonts) == 1


# --- R6: the game area is a graveyard ------------------------------------------

def test_R6_graveyard_objects_are_drawn_around_the_player(window):
    """R6: grass, gravestones, the iron fence and dead trees are drawn (since R14: the whole graveyard)."""
    press(window, "space")
    for tag in ("grass", "grave", "fence", "tree", "obstacle", "path"):
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
    """R7 (changed by R9): hazards are drawn from the start, so they can be jumped or avoided."""
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
    press(window, "space")
    get_caught(window)
    press(window, "r")
    get_caught(window)
    press(window, "r", "Right", "Right", "Right", "Right")
    assert window.game.status is Status.LOST
    assert texts(window, "ending_title") == ["GAME OVER"]
    assert any("You fell into an open grave." in t for t in texts(window, "overlay"))


# --- R9: the whole view is lit -------------------------------------------------

def test_R9_every_tile_in_view_is_at_least_moonlit(window):
    """R9: no tile is dark: every floor colour keeps at least 0.8 of its brightness (moonlight)."""
    press(window, "space")
    fills = {window.canvas.itemcget(i, "fill") for i in window.canvas.find_withtag("floor")}
    for fill in fills:
        assert max(int(fill[k:k + 2], 16) for k in (1, 3, 5)) >= 0x50
    assert MOONLIGHT == 0.8


def test_R9_torch_glow_is_strongest_at_the_player_and_fades_out(window):
    """R9: the torch adds warm rings around the player: the inner one bright, the outer one fainter."""
    press(window, "space")
    colours = [c for _, c in sorted(torch_rings(window), key=lambda r: r[0][2] - r[0][0])]
    brightness = [sum(int(c[k:k + 2], 16) for k in (1, 3, 5)) for c in colours]
    assert brightness[0] > brightness[1]


def test_R9_the_whole_view_is_drawn_not_just_near_the_torch(window):
    """R9 (changed by R14): every tile of the graveyard has ground drawn on it, wherever the player is."""
    press(window, "space")
    maze = window.game.maze
    assert len(window.canvas.find_withtag("floor")) == maze.width * maze.height
    window.game.player = (12, 20)
    window.advance(0)
    assert len(window.canvas.find_withtag("floor")) == maze.width * maze.height


# --- R10: jumping in the window ---------------------------------------------------

def test_R10_up_arrow_jumps_the_open_grave_east_of_the_start(window):
    """R10: facing the open grave, Up leaps over it: two tiles, one move, no life lost."""
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
    turn = window.game.turn
    press(window, "Up")
    assert window.game.player == (1, 15) and window.game.turn == turn + 1


def test_R10_low_hurdles_are_drawn_as_a_fallen_headstone_and_coffins(window):
    """R10: low hurdles are drawn with their own tags, apart from blocking obstacles."""
    press(window, "space")
    assert window.canvas.find_withtag("coffin") and window.canvas.find_withtag("fallen_headstone")
    low = set(window.canvas.find_withtag("low_hurdle"))
    assert set(window.canvas.find_withtag("coffin")) <= low
    assert not low & set(window.canvas.find_withtag("obstacle"))


def test_R10_controls_and_title_screen_mention_the_jump(window):
    """R10: the title story and the controls line explain the Up arrow."""
    assert any("↑" in t and "leap" in t for t in texts(window, "overlay"))
    press(window, "space")
    assert any("↑  jump" in t for t in texts(window, "hud"))


def test_R10_a_jump_pressed_a_moment_early_still_clears_the_grave(window):
    """R10/R14: running with Right held, Up pressed a tile before the open grave still leaps it."""
    press(window, "space")
    window.on_key("Right")                     # held
    window.advance(PLAYER_STEP_MS * 2)         # on the way to (1,8)
    window.on_key("Up")
    window.on_key_up("Up")
    window.advance(PLAYER_STEP_MS + JUMP_MS)
    assert window.game.player[1] >= 10 and window.game.lives == 3


# --- R8: figures that move -------------------------------------------------------

from escape_game.gui import hover, jump_height, lit, progress, tween, walk_pose  # noqa: E402


def test_R8_ease_and_tween_slide_smoothly_from_tile_to_tile():
    """R8 (changed by R14): a step glides at a constant speed (no ease in and out, which stuttered at every
    tile), passing every point in between."""
    assert progress(0, 0, 180) == 0 and progress(90, 0, 180) == 0.5 and progress(400, 0, 180) == 1
    assert progress(5, float("-inf"), 180) == 1  # a figure that hasn't moved stands on its tile
    assert tween((1, 5), (1, 6), 0.5) == (1, 5.5) and tween((1, 5), (1, 6), 0.25) == (1, 5.25)


def test_R8_walk_pose_swings_legs_forward_and_back_once_per_step():
    """R8: the walk cycle swings one way, then the other, and ends where it started."""
    assert walk_pose(0) == 0 and abs(walk_pose(1)) < 1e-9
    assert walk_pose(0.25) == pytest.approx(1) and walk_pose(0.75) == pytest.approx(-1)


def test_R8_jump_rises_and_lands():
    """R8 / R10: the jump arc is highest in the middle and on the ground at both ends."""
    assert jump_height(0) == 0 and jump_height(1) == pytest.approx(0, abs=1e-9)
    assert jump_height(0.5) > jump_height(0.2) > 0


def test_R8_player_slides_to_the_next_tile_over_several_frames(window):
    """R8: after a move the figure is first still on the old tile, then between tiles, then on the new one."""
    press(window, "space")
    window.on_key("Right")
    window.on_key_up("Right")
    window.advance(0)
    assert window.game.player == (1, 6)              # the rules moved at once
    assert tile_of(window)[1] == pytest.approx(5, abs=0.15)
    window.advance(PLAYER_STEP_MS / 2)
    assert 5.3 < tile_of(window)[1] < 5.7
    window.advance(PLAYER_STEP_MS / 2)
    assert tile_of(window)[1] == pytest.approx(6, abs=0.15)


def test_R8_legs_move_while_walking(window):
    """R8: the legs are drawn in different poses during a step (R14: the pose is redrawn every few frames)."""
    press(window, "space")
    window.on_key("Right")
    poses = set()
    for _ in range(9):
        window.advance(PLAYER_STEP_MS / 10)
        poses.add(tuple(round(v - window.canvas.bbox("player")[0]) for i in window.canvas.find_withtag("player_leg")
                        for v in window.canvas.coords(i)[::2]))
    assert len(poses) >= 3


def test_R8_player_faces_the_way_they_walk(window):
    """R8: walking left mirrors the figure (the torch moves to the other side)."""
    press(window, "space")
    right_torch = centre_of(window, "flame")[0] - centre_of(window, "player")[0]
    press(window, "Left")
    left_torch = centre_of(window, "flame")[0] - centre_of(window, "player")[0]
    assert right_torch > 0 > left_torch


def test_R8_the_reaper_glides_and_hovers(window):
    """R8 / R11: the reaper glides after the player and keeps floating as it goes."""
    press(window, "space")
    window.on_key("Right")
    window.on_key_up("Right")
    window.advance(REAPER_STEP_MS * 1.5)  # half-way through its first step, from (1,1) to (1,2)
    x0, _, x1, _ = window.canvas.bbox("aura")  # the aura on the ground follows the reaper
    assert 1.2 < (x0 + x1) / 2 / TILE - 0.5 < 1.8
    tops = set()
    for _ in range(12):
        window.advance(30)
        tops.add(round(window.canvas.bbox("reaper")[1] - window.canvas.bbox("aura")[1]))
    assert len(tops) > 1
    assert abs(hover(0) - hover(1200)) > 0


def test_R8_the_camera_scrolls_smoothly(window):
    """R8 (changed by R14): the camera no longer scrolls at all; the graveyard stays put while the
    player runs, so there is nothing to jerk."""
    press(window, "space")
    world = {i: window.canvas.coords(i) for i in window.canvas.find_withtag("world")[::37]}
    window.on_key("Right")
    for _ in range(10):
        window.advance(40)
    assert {i: window.canvas.coords(i) for i in world} == world


def test_R8_a_key_during_a_slide_finishes_it_and_takes_the_next_move(window):
    """R8 (changed by R14): a key held during a step takes the next step the moment this one ends,
    without a pause (a step is no longer cut short; the player keeps a steady pace)."""
    press(window, "space")
    window.on_key("Right")
    window.advance(PLAYER_STEP_MS / 2)
    window.on_key("Right")                    # key repeat while held
    assert window.game.player == (1, 6)
    window.advance(PLAYER_STEP_MS / 2)
    assert window.game.player == (1, 7) and window.game.player_from == (1, 6)


def test_R8_the_caught_screen_waits_until_the_slide_is_seen(window):
    """R8: the life-lost screen appears after the reaper has visibly reached the player."""
    press(window, "space", "Left")
    while window.game.status is Status.PLAYING:
        window.advance(10)
    assert window.state == window.CAUGHT and not window.canvas.find_withtag("caught_title")
    window.advance(REAPER_STEP_MS)
    assert texts(window, "caught_title") == ["CAUGHT!"]


def test_R8_a_key_after_the_last_move_still_shows_the_end_screen(window):
    """R8: a key pressed while the final step plays shows the GAME OVER screen at once."""
    press(window, "space")
    get_caught(window)
    press(window, "r")
    get_caught(window)
    press(window, "r", "Left")
    while window.game.status is Status.PLAYING:
        window.advance(10)
    window.on_key("Left")
    assert texts(window, "ending_title") == ["GAME OVER"]


def test_R8_jump_lifts_the_player_off_the_ground(window):
    """R8 / R10: mid-jump the figure is above its shadow; it lands two tiles on."""
    press(window, "space", "Right", "Right", "Right")
    ground = window.canvas.bbox("player")[3]
    window.on_key("Up")
    window.advance(JUMP_MS / 2)
    assert window.canvas.bbox("player")[3] < ground - TILE * 0.3
    assert window.canvas.find_withtag("player_shadow")
    window.advance(JUMP_MS / 2)
    assert tile_of(window)[1] == pytest.approx(10, abs=0.15)


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
    """R11 (changed by R14): wisps of mist lie over the graveyard, still during play (moving them would
    repaint the whole graveyard), and drift on the title and end screens."""
    title_mist = [window.canvas.coords(i)[0] for i in window.canvas.find_withtag("screen_mist")]
    for _ in range(8):
        window.advance(40)
    drifted = [window.canvas.coords(i)[0] for i in window.canvas.find_withtag("screen_mist")]
    assert title_mist and drifted != title_mist
    press(window, "space")
    still = [window.canvas.coords(i) for i in window.canvas.find_withtag("mist")]
    assert len(still) >= 10
    for _ in range(8):
        window.advance(40)
    assert [window.canvas.coords(i) for i in window.canvas.find_withtag("mist")] == still


def test_R11_nothing_relies_on_transparency(window):
    """R11: Tk on Windows draws stippled shapes solid, so no item may use a stipple."""
    press(window, "space")
    get_caught(window)
    for cv in (window.canvas, window.hud):
        for i in cv.find_all():
            if "stipple" in cv.itemconfigure(i):
                assert cv.itemcget(i, "stipple") == ""


def test_R11_title_and_end_screens_have_a_moon_and_a_shadowed_title(window):
    """R11: the title is blood red with a dark shadow beneath it."""
    title = window.canvas.find_withtag("title")[0]
    shadows = [i for i in window.canvas.find_withtag("overlay")
               if window.canvas.type(i) == "text" and window.canvas.itemcget(i, "text") == "ESCAPE THE GRIM REAPER"]
    assert len(shadows) == 2 and window.canvas.itemcget(title, "fill") == RED


# --- R12: the path on screen ------------------------------------------------------------

def test_R12_the_gravel_path_is_drawn_under_the_route_and_its_hurdles(window):
    """R12: every tile of the route, and every hurdle lying across it, sits on gravel, not grass."""
    maze = window.game.maze
    route = maze.player_route(maze.player_start, maze.exit)
    assert all(window._path_like(t) for t in route)
    jumped = [((a[0] + b[0]) // 2, (a[1] + b[1]) // 2) for a, b in zip(route, route[1:])
              if abs(a[0] - b[0]) + abs(a[1] - b[1]) == 2]
    assert jumped and all(window._path_like(t) for t in jumped)
    assert not window._path_like((3, 20))  # the dead-end alleys are grass
    assert len(window.canvas.find_withtag("path")) > len(route)


# --- R13: the Reaper chases in the window --------------------------------------------

def test_R13_the_reaper_comes_on_while_the_player_stands_still(window):
    """R13: after the first step the Reaper keeps moving with the clock, key or no key."""
    press(window, "space", "Right")
    start = window.game.reaper
    window.advance(REAPER_STEP_MS * 2)
    assert window.game.reaper != start and window.game.reaper[1] > start[1]


def test_R13_the_title_screen_does_not_run_the_clock(window):
    """R13: nothing moves until the chase has begun."""
    window.advance(5000)
    assert window.game.clock == 0 and window.game.reaper == window.game.maze.reaper_start


# --- R14: smooth flow -------------------------------------------------------------------

def test_R14_holding_a_key_runs_without_stopping(window):
    """R14: with Right held, the figure moves forward on every frame by about the same amount."""
    press(window, "space")
    window.on_key("Right")
    xs = []
    for _ in range(12):  # 480 ms in 40 ms frames: three steps, no pause between them
        window.advance(40)
        xs.append(tile_of(window)[1])
    moves = [b - a for a, b in zip(xs, xs[1:])]
    assert all(m > 0 for m in moves)
    assert max(moves) - min(moves) < 0.08
    assert window.game.player == (1, 8)  # on the way there; the open grave at (1,9) is next


def test_R14_releasing_the_key_stops_at_the_next_tile(window):
    """R14: letting go stops the run cleanly on a tile."""
    press(window, "space")
    window.on_key("Right")
    window.advance(PLAYER_STEP_MS / 2)
    window.on_key_up("Right")
    for _ in range(10):
        window.advance(40)
    assert window.game.player == (1, 6) and tile_of(window)[1] == pytest.approx(6, abs=0.15)


def test_R14_the_graveyard_is_drawn_once(window):
    """R14: no frame, step or screen redraws the graveyard: its items stay the same items."""
    world = set(window.canvas.find_withtag("world"))
    press(window, "space", "Right", "Right")
    get_caught(window)
    press(window, "r")
    assert set(window.canvas.find_withtag("world")) == world


def test_R14_each_frame_changes_only_the_figures(window):
    """R14: a frame redraws or moves the figure items and touches nothing else on the graveyard canvas."""
    press(window, "space")
    window.on_key("Right")
    others = {i: window.canvas.coords(i) for i in window.canvas.find_all()
              if i not in window.canvas.find_withtag("actor")}
    for _ in range(4):
        window.advance(40)
        now = {i: window.canvas.coords(i) for i in window.canvas.find_all()
               if i not in window.canvas.find_withtag("actor")}
        assert now == others


def test_R14_the_hud_is_on_its_own_canvas(window):
    """R14: the beating hearts and the clock live on a separate canvas, so they never repaint the graveyard."""
    press(window, "space")
    assert window.hud is not window.canvas
    assert window.hud.find_withtag("heart") and not window.canvas.find_withtag("heart")
    assert window.hud.find_withtag("hud_turn") and not window.canvas.find_withtag("hud")
    assert any("Hold" in t for t in texts(window, "hud")) and "Hold" in CONTROLS


def test_R14_key_repeat_draws_no_extra_frames(window):
    """R14: Windows repeats a held key ~30 times a second; the repeats must not redraw the figures."""
    press(window, "space")
    window.on_key("Right")
    window.advance(0)
    actors = {i: window.canvas.coords(i) for i in window.canvas.find_withtag("actor")}
    for _ in range(5):
        window.on_key("Right")
    assert {i: window.canvas.coords(i) for i in window.canvas.find_withtag("actor")} == actors


def test_R14_a_stalled_frame_moves_the_game_on_by_at_most_MAX_FRAME_MS(window):
    """R14: if the computer stalls for a second, the figures don't leap: one frame is at most 100 ms."""
    press(window, "space", "Right")
    clock = window.game.clock
    window._last = time.perf_counter() - 1.0
    window._next_frame = time.perf_counter()
    window._tick()
    assert window.game.clock - clock <= MAX_FRAME_MS


def test_R14_losing_the_keyboard_lets_go_of_held_keys(window):
    """R14: if the window loses focus while a key is held, the player stops instead of running on."""
    press(window, "space")
    window.on_key("Right")
    window._release_all()
    window.advance(PLAYER_STEP_MS * 4)
    assert window.game.player == (1, 6)
