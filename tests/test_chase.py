"""Tests for the real-time chase of the game window (R13, R15) and the remembered jump (R10).

The rules for time live in game.py on a clock the tests advance by hand (Game.update(ms)), so a whole
chase runs in milliseconds and every result is exact.
"""

from escape_game.game import (CALM_AFTER_RUN_MS, JUMP_BUFFER_MS, JUMP_MS, PLAYER_STEP_MS, REAPER_STEP_MS,
                              REAPER_SURGE_MS, SURGE_AFTER_IDLE_MS, Game, Outcome, Status)
from escape_game.maze import DIRECTIONS, Maze

STEP_TO_DIR = {v: k for k, v in DIRECTIONS.items()}
HESITANT_MS = 300  # R13/R17: stopping this long at each bend still escapes (measured: gap 3)
CAUGHT_MS = 400    # R13/R17: stopping this long at each bend is caught (in the key yard, R16)
LANE = "############\n#R  P      #\n#+++++++++ #\n#E         #\n############"  # a short run east


def realtime(maze=None, lives=3):
    return Game(Maze(maze, signs={}) if maze else None, lives=lives, realtime=True)


def run_route(game, hesitate_ms=0):
    """Play the safe route like a person holding keys. Up is tapped while running onto the tile before
    each hurdle (a remembered jump, R10). At every bend the player stops, hesitates `hesitate_ms`, then
    presses the new direction. Returns the smallest gap to the Reaper seen on the way."""
    route = game.route_out()  # R16: by way of the key
    held, smallest = None, game.reaper_distance()

    def wait(until):
        nonlocal smallest
        while game.clock < until and game.status is Status.PLAYING:
            game.update(min(10, until - game.clock))
            smallest = min(smallest, game.reaper_distance())

    for a, b in zip(route, route[1:]):
        while game.player != a and game.status is Status.PLAYING:  # running toward a
            wait(game.clock + 1)
        if game.status is not Status.PLAYING:
            break
        dr, dc = b[0] - a[0], b[1] - a[1]
        jump = abs(dr) + abs(dc) == 2
        direction = STEP_TO_DIR[(dr // 2, dc // 2) if jump else (dr, dc)]
        if direction != held:
            if held:
                game.release(held)
                wait(game.player_moved_at + game.player_move_ms + hesitate_ms)  # arrive, then hesitate
            game.press(direction)
            held = direction
        if jump:
            game.press_jump()
    while game.status is Status.PLAYING and game.player != game.maze.exit:
        wait(game.clock + 1)
    return smallest


# --- R13: the Reaper chases on its own clock -------------------------------------------

def test_R13_the_reaper_waits_for_the_first_step_then_moves_on_its_own_clock():
    """R13: the chase starts at the player's first step; after that the Reaper steps every REAPER_STEP_MS."""
    game = realtime()
    game.update(5000)
    assert game.reaper == game.maze.reaper_start  # nobody has moved yet
    game.press("right")
    game.release("right")
    assert game.player == (1, 6)
    start = game.reaper
    game.update(REAPER_STEP_MS - 1)
    assert game.reaper == start
    game.update(1)
    assert game.reaper == (1, 2)
    game.update(REAPER_STEP_MS)
    assert game.reaper == (1, 3)


def test_R13_a_player_who_stands_still_is_caught():
    """R13: there is no standing 'four blocks away' any more: the Reaper closes in on a still player."""
    game = realtime()
    game.press("right")
    game.release("right")  # one step, then nothing
    game.update(REAPER_STEP_MS * 4)
    assert game.reaper == (1, 5) and game.status is Status.PLAYING  # right behind
    game.update(REAPER_STEP_MS)
    assert game.status is Status.CAUGHT and game.hurt_by == "reaper" and game.lives == 2


def test_R13_the_reaper_closes_in_while_the_player_hesitates():
    """R13: the gap shrinks with every Reaper step the player doesn't answer."""
    game = realtime()
    game.press("right")
    game.release("right")
    gaps = []
    for _ in range(4):
        game.update(REAPER_STEP_MS)
        gaps.append(game.reaper_distance())
    assert gaps == [4, 3, 2, 1]


def test_R13_the_reaper_is_a_little_slower_than_a_runner():
    """R13: running beats the Reaper's pace, and jumping beats it by more."""
    assert REAPER_STEP_MS > PLAYER_STEP_MS
    assert JUMP_MS / 2 < PLAYER_STEP_MS < REAPER_STEP_MS
    game = realtime(LANE)
    game.press("right")
    game.update(PLAYER_STEP_MS * 5)
    assert game.reaper_distance() > 3


def test_R13_a_clean_run_escapes_with_the_reaper_never_closer_than_4():
    """R13: holding the keys along the path wins, and the gap never drops below the start gap."""
    game = realtime()
    smallest = run_route(game)
    assert game.status is Status.WON
    assert smallest >= 4
    assert 14_000 < game.run_ms < 17_000  # about 15.6 s


def test_R13_a_hesitant_player_still_escapes_but_a_dawdler_is_caught():
    """R13: stopping HESITANT_MS at every bend still escapes, with the Reaper close (3 tiles or fewer);
    stopping CAUGHT_MS at every bend gets the player caught."""
    game = realtime()
    smallest = run_route(game, hesitate_ms=HESITANT_MS)
    assert game.status is Status.WON and smallest <= 3
    game = realtime()
    run_route(game, hesitate_ms=CAUGHT_MS)
    assert game.status is Status.CAUGHT and game.hurt_by == "reaper"


def test_R13_resume_puts_both_back_and_waits_for_the_first_step_again():
    """R13 / R4: after a lost life the Reaper waits at its start until the player moves again."""
    game = realtime()
    game.press("right")
    game.update(PLAYER_STEP_MS * 3 + 1)  # (1,6) (1,7) (1,8), then into the open grave at (1,9)
    assert game.status is Status.CAUGHT and game.hurt_by == "open grave"
    assert game.resume() is Outcome.RESUMED
    assert game.held == []  # keys held before the fall are forgotten
    game.update(3000)
    assert (game.player, game.reaper) == (game.maze.player_start, game.maze.reaper_start)
    game.press("right")
    game.update(REAPER_STEP_MS)
    assert game.reaper == (1, 2)


def test_R13_nothing_moves_once_the_game_has_ended():
    """R13: after a catch, a fall or a win, the clock runs on but nobody moves."""
    game = realtime()
    game.press("left")
    game.update(PLAYER_STEP_MS * 2)  # walks into the Reaper
    assert game.status is Status.CAUGHT
    player, reaper = game.player, game.reaper
    game.press("right")
    game.update(5000)
    assert (game.player, game.reaper) == (player, reaper)


def test_R13_turn_based_games_are_unchanged():
    """R13: without realtime (the --text game) the Reaper still steps once per move and update() does nothing."""
    game = Game()
    game.update(10_000)
    assert game.reaper == game.maze.reaper_start
    game.move("right")
    assert game.reaper == (1, 2)


# --- R15: smooth flow: hold to run, cornering, no stalls ------------------------------------

def test_R15_a_press_moves_at_once():
    """R15: a key pressed while the player is ready moves them straight away, with no wait for a frame."""
    game = realtime()
    game.press("right")
    assert game.player == (1, 6) and game.player_moved_at == game.clock


def test_R15_holding_a_key_runs_at_a_steady_pace():
    """R15: while a key is held the player moves a tile every PLAYER_STEP_MS, with no gap between steps."""
    game = realtime(LANE)
    game.press("right")
    starts = [game.player_moved_at]
    for _ in range(4):
        game.update(PLAYER_STEP_MS)
        starts.append(game.player_moved_at)
    assert game.player == (1, 9)
    assert [b - a for a, b in zip(starts, starts[1:])] == [PLAYER_STEP_MS] * 4


def test_R15_releasing_the_key_stops_at_the_next_tile():
    """R15: letting go finishes the step under way and then stops."""
    game = realtime(LANE)
    game.press("right")
    game.update(PLAYER_STEP_MS / 2)
    game.release("right")
    game.update(PLAYER_STEP_MS * 5)
    assert game.player == (1, 5)


def test_R15_presses_during_a_step_wait_for_it_to_finish():
    """R15: the player can't outrun their own legs: a tap mid-step acts when the step ends."""
    game = realtime(LANE)
    game.press("right")
    game.release("right")
    game.press("right")  # tapped again at once
    game.release("right")
    assert game.player == (1, 5)  # still on the first step


def test_R15_motion_records_where_and_when_each_figure_set_off():
    """R15: the window draws each figure part of the way from where it was, so Game records the motion."""
    game = realtime(LANE)
    game.press("right")
    assert (game.player_from, game.player, game.player_move_ms) == ((1, 4), (1, 5), PLAYER_STEP_MS)
    game.update(REAPER_STEP_MS)
    assert (game.reaper_from, game.reaper, game.reaper_moved_at) == ((1, 1), (1, 2), REAPER_STEP_MS)
    assert game.reaper_move_ms == REAPER_STEP_MS


def test_R15_cornering_turns_as_soon_as_the_way_opens():
    """R15: holding Right and pressing Down early keeps running right until Down is open, then turns."""
    game = realtime(LANE)
    game.press("right")
    game.press("down")  # pressed early: below is a row of gravestones
    assert game.player == (1, 5) and game.bumped is None
    game.update(PLAYER_STEP_MS * 6)
    assert game.player == (2, 10)  # ran right to the gap at column 10, then turned down
    assert game.facing == "down"


def test_R15_releasing_the_newer_key_falls_back_to_the_older_one():
    """R15: with Right still held, letting go of Down carries on running right."""
    game = realtime(LANE)
    game.press("right")
    game.press("down")
    game.release("down")
    game.update(PLAYER_STEP_MS * 2)
    assert game.player == (1, 7)


def test_R15_a_bump_stops_the_run_but_a_new_key_acts_at_once():
    """R15: running into an obstacle stops and says so once; another key then moves without delay."""
    game = realtime("#########\n#R  P+  #\n#     E #\n#########")
    game.press("right")
    assert game.events[-1] is Outcome.WALL and game.bumped == "gravestone"
    game.events.clear()
    game.update(PLAYER_STEP_MS * 3)
    assert game.events == [] and game.player == (1, 4)  # no repeated bumping
    game.press("down")
    assert game.player == (2, 4)


def test_R15_events_tell_the_window_what_each_action_did():
    """R15: moves, bumps and failed jumps are queued as Outcome events for the window's messages."""
    game = realtime()
    game.press_jump()  # nothing to jump at the start
    game.press("up")    # the fence
    game.release("up")
    game.press("right")
    assert game.events == [Outcome.NO_JUMP, Outcome.WALL, Outcome.MOVED]


# --- R10 in real time: the jump --------------------------------------------------------------

def test_R10_a_jump_covers_two_tiles_in_JUMP_MS():
    """R10/R13: a jump lands two tiles on and the next action waits JUMP_MS."""
    game = realtime()
    for _ in range(3):
        game.press("right")
        game.release("right")
        game.update(PLAYER_STEP_MS)
    assert game.player == (1, 8)
    game.press_jump()
    assert game.player == (1, 10) and game.jumped and game.player_move_ms == JUMP_MS
    game.press("right")
    assert game.player == (1, 10)
    game.update(JUMP_MS)
    assert game.player == (1, 11)


def test_R10_a_jump_pressed_a_moment_early_is_remembered():
    """R10/R15: Up pressed a tile before the hurdle, while running, leaps it as soon as it is in front."""
    game = realtime()
    game.press("right")
    game.update(PLAYER_STEP_MS * 2)  # on the way from (1,7) to (1,8), running
    game.press_jump()                # a tile too early: the open grave is at (1,9)
    assert game.player == (1, 8)
    game.update(PLAYER_STEP_MS)
    assert game.player == (1, 10) and game.lives == 3 and game.status is Status.PLAYING


def test_R10_a_remembered_jump_is_forgotten_after_JUMP_BUFFER_MS():
    """R10: an Up pressed too early does not hang around: after JUMP_BUFFER_MS it is dropped."""
    assert 150 <= JUMP_BUFFER_MS <= 500
    game = realtime(LANE)
    game.press("right")
    game.press_jump()  # nothing to jump on this lane
    game.update(JUMP_BUFFER_MS + PLAYER_STEP_MS * 2)
    assert game.player == (1, 8) and not game.jumped


def test_R10_up_in_front_of_a_hurdle_after_a_bump_jumps_at_once():
    """R10: a player who stopped against a coffin leaps it the moment Up is pressed."""
    game = realtime("##########\n#R  PC   #\n#      E #\n##########")
    game.press("right")
    assert game.bumped == "coffin" and game.player == (1, 4)
    game.press_jump()
    assert game.player == (1, 6)


def test_R10_running_into_a_hazard_without_jumping_costs_a_life():
    """R7/R15: holding a key straight into an open grave loses a life, as stepping on it always did."""
    game = realtime()
    game.press("right")
    game.update(PLAYER_STEP_MS * 3)
    assert game.status is Status.CAUGHT and game.hurt_by == "open grave" and game.player == (1, 9)


def test_R13_reaching_the_exit_wins_and_records_the_time():
    """R13: the run's time counts from the first step to the exit (shown on the win screen)."""
    game = realtime("#########\n#R  P  E#\n#########")
    game.update(1000)
    game.press("right")
    game.update(PLAYER_STEP_MS * 2)
    assert game.status is Status.WON
    assert game.run_ms == PLAYER_STEP_MS * 2
    game.update(1000)
    assert game.run_ms == PLAYER_STEP_MS * 2


def test_R10_a_remembered_jump_that_runs_out_with_no_key_held_does_nothing():
    """R10/R15: an Up remembered while running, which runs out after the key is let go, does nothing
    (it used to crash the window with an IndexError, as reported by the product owner).

    Checked against the code before the fix (60ac88b^): this exact sequence raised the IndexError."""
    game = realtime()
    game.press("right")              # (1,6), running
    game.press_jump()                # nothing to jump yet: remembered, and the run goes on
    game.update(PLAYER_STEP_MS + 20)  # (1,7); the remembered Up is still alive
    game.release("right")            # let go during this step
    game.update(PLAYER_STEP_MS)      # the step ends after the Up ran out, with no key held
    assert game.player == (1, 7) and game.status is Status.PLAYING and game.events[-1] is Outcome.MOVED
    assert JUMP_BUFFER_MS < 2 * PLAYER_STEP_MS  # the Up must run out within the second step for this to bite



# --- R17: the Reaper surges when the player stops ---------------------------------------------

def test_R17_the_reaper_surges_when_the_player_stands_still():
    """R17: once the player has stood still for SURGE_AFTER_IDLE_MS, the Reaper steps every REAPER_SURGE_MS,
    as fast as a running player."""
    assert REAPER_SURGE_MS == PLAYER_STEP_MS < REAPER_STEP_MS
    game = realtime(LANE)
    game.press("right")
    game.release("right")
    game.update(REAPER_STEP_MS)          # first step, at the normal pace
    assert not game.surging and game.reaper_move_ms == REAPER_STEP_MS
    game.update(REAPER_STEP_MS)          # the player has stood still since 180 ms: 260 ms by now
    assert game.surging and game.reaper_move_ms == REAPER_SURGE_MS
    before = game.reaper_moved_at
    game.update(REAPER_SURGE_MS)
    assert game.reaper_moved_at == before + REAPER_SURGE_MS


def test_R17_a_clean_run_never_sets_the_reaper_surging():
    """R17: a player who keeps running is chased at the normal pace all the way."""
    game = realtime()
    paces = set()
    original = game._reaper_act

    def act():
        original()
        paces.add(game.reaper_move_ms)

    game._reaper_act = act
    run_route(game)
    assert game.status is Status.WON and paces == {REAPER_STEP_MS}


def test_R17_running_on_for_a_second_calms_the_reaper():
    """R17: after a surge, CALM_AFTER_RUN_MS of unbroken running brings the Reaper back to its normal pace."""
    game = realtime("##########################\n#R  P                    #\n#                       E#\n##########################")
    game.press("right")
    game.release("right")
    game.update(REAPER_STEP_MS + SURGE_AFTER_IDLE_MS + REAPER_SURGE_MS)
    assert game.surging
    game.press("right")                  # run on, without stopping
    game.update(CALM_AFTER_RUN_MS - 200)
    assert game.surging
    game.update(400)
    assert not game.surging


def test_R17_bumping_into_something_counts_as_standing_still():
    """R17: running into a gravestone and staying there sets the Reaper off just like stopping."""
    game = realtime("##########\n#R     P+#\n#       E#\n##########")
    game.press("left")                   # a first step (1,6) sets the chase off
    game.release("left")
    game.update(PLAYER_STEP_MS)
    game.press("right")                  # back to (1,7), then held into the gravestone at (1,8)
    game.update(REAPER_STEP_MS * 2)
    assert game.bumped == "gravestone" and game.player == (1, 7)
    game.update(REAPER_STEP_MS)
    assert game.surging and game.status is Status.PLAYING


def test_R17_turn_based_games_never_surge():
    """R17: the --text game has no clock, so the Reaper keeps to one step per move."""
    game = Game()
    for _ in range(3):
        game.move("up")  # bumps the fence: no turn, no surge
    game.update(5000)
    assert not game.surging
