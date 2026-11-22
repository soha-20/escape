"""Tests for turn order, the chase, winning and losing."""

import pytest

from escape_game.game import MAX_LIVES, Game, Outcome, Status
from escape_game.maze import DIRECTIONS, Maze, Sign, WARNING

STEP_TO_DIR = {v: k for k, v in DIRECTIONS.items()}


def walk(game, tiles):
    """Move the player along tiles 1 apart (a step) or 2 apart (a jump, R10); stop early if the game ends."""
    for nxt in tiles:
        if game.status is not Status.PLAYING:
            break
        delta = (nxt[0] - game.player[0], nxt[1] - game.player[1])
        if abs(delta[0]) + abs(delta[1]) == 2:  # face that way, then leap
            game.facing = STEP_TO_DIR[(delta[0] // 2, delta[1] // 2)]
            assert game.jump() is Outcome.MOVED
        else:
            assert game.move(STEP_TO_DIR[delta]) is Outcome.MOVED


def solution(game):
    """The shortest way to the exit that never lands on a hazard (R7), jumping the hurdles on the path (R12)."""
    return game.maze.player_route(game.player, game.maze.exit)[1:]


def path_to(game, goal):
    return game.maze.player_route(game.player, goal)[1:]


# --- R1: the game starts and the player escapes the reaper -----------------

def test_R1_game_starts_with_player_and_reaper_in_place():
    """R1: a new game puts the player at P and the reaper at R, close behind."""
    game = Game()
    assert game.status is Status.PLAYING
    assert game.player == game.maze.player_start
    assert game.reaper == game.maze.reaper_start
    assert game.turn == 0
    assert game.reaper_distance() == 4


def test_R1_reaper_moves_one_step_toward_player_every_turn():
    """R1: each player move is followed by one reaper step along the shortest path."""
    game = Game()
    before = game.reaper_distance()
    game.move("right")
    assert game.turn == 1
    assert game.reaper == (1, 2)
    assert game.reaper_distance() == before  # moved away 1, reaper closed 1


def test_R1_following_the_signs_escapes_the_reaper():
    """R1: walking the route the signs describe reaches the exit and wins."""
    game = Game()
    walk(game, solution(game))
    assert game.status is Status.WON
    assert game.player == game.maze.exit
    assert game.turn == 79  # R12: 65 steps and 14 jumps along the path


def test_R1_reaper_does_not_move_after_player_escapes():
    """R1: reaching the exit ends the game before the reaper's step."""
    game = Game()
    path = solution(game)
    walk(game, path[:-1])
    reaper_before = game.reaper
    walk(game, path[-1:])
    assert game.status is Status.WON
    assert game.reaper == reaper_before


def test_R1_bumping_a_wall_does_not_use_a_turn():
    """R1: obstacles (since R6: the graveyard fence) block the player and the reaper gets no free step."""
    game = Game()
    assert game.move("up") is Outcome.WALL
    assert game.turn == 0 and game.player == game.maze.player_start
    assert game.reaper == game.maze.reaper_start
    assert game.bumped == "iron fence"


@pytest.mark.parametrize("text,direction", [("w", "up"), ("S", "down"), (" a ", "left"), ("d\n", "right")])
def test_R1_wasd_commands_map_to_directions(text, direction, monkeypatch):
    """R1: w/a/s/d control the player, case- and whitespace-insensitive."""
    game = Game()
    calls = []
    monkeypatch.setattr(game, "move", lambda d: calls.append(d) or Outcome.MOVED)
    game.command(text)
    assert calls == [direction]


@pytest.mark.parametrize("text", ["", "x", "up", "ww"])
def test_R1_unknown_commands_do_not_use_a_turn(text):
    """R1: typos don't cost the player a turn."""
    game = Game()
    assert game.command(text) is Outcome.INVALID
    assert game.turn == 0


def test_R1_q_quits_the_game():
    """R1: the player can give up with q."""
    game = Game()
    assert game.command("q") is Outcome.QUIT
    assert game.status is Status.QUIT


def test_R1_nothing_is_hidden_by_fog_any_more():
    """R1 (changed by R9 in round 4): the rules no longer keep a fog of war; the whole graveyard is shown."""
    game = Game()
    assert not hasattr(game, "seen") and not hasattr(game, "visible")


# --- R2: following signs vs ignoring them ----------------------------------
# Adapted in round 3 (R6): the dead ends are fenced plots in open ground, not corridor branches.
# Adapted in round 5 (R12): the dead ends are side paths off the gravel path, and the route jumps hurdles.

def warned_plots(maze):
    """(entrance tile, first tile inside, every tile of the plot) for each warning sign."""
    plots = []
    for pos, sign in maze.signs.items():
        if sign.kind != WARNING:
            continue
        for dr, dc in DIRECTIONS.values():
            entrance = (pos[0] + dr, pos[1] + dc)
            if maze.is_wall(entrance):
                continue
            pr, pc = DIRECTIONS[sign.points]
            first = (entrance[0] + pr, entrance[1] + pc)
            if maze.is_wall(first):
                continue
            seen, stack = {entrance, first}, [first]
            while stack:
                for nxt in maze.neighbours(stack.pop()):
                    if nxt not in seen:
                        seen.add(nxt)
                        stack.append(nxt)
            seen.discard(entrance)
            if maze.exit not in seen and maze.player_start not in seen:
                plots.append((entrance, first, seen))
    return plots


def test_R2_following_the_safe_route_keeps_the_reaper_four_steps_behind():
    """R2: walking the way the signs describe, the reaper never gains on the player (in --text, turn-based).

    Changed by R12: each jump on the path gains the player a step, so the gap grows from 4."""
    game = Game()
    gaps = []
    for nxt in solution(game)[:-1]:
        walk(game, [nxt])
        gaps.append(game.reaper_distance())
    assert min(gaps) == 4 and gaps == sorted(gaps)
    walk(game, solution(game))
    assert game.status is Status.WON


@pytest.mark.parametrize("plot", range(3))
def test_R2_ignoring_a_warning_sign_gets_the_player_caught(plot):
    """R2: walking to the back of a plot a red sign warns about ends in capture."""
    game = Game()
    maze = game.maze
    entrance, first, tiles = sorted(warned_plots(maze))[plot]
    walk(game, path_to(game, entrance))
    assert game.status is Status.PLAYING
    deepest = max(tiles, key=lambda t: len(maze.player_route(entrance, t) or []))
    walk(game, path_to(game, deepest))
    walk(game, path_to(game, entrance))
    walk(game, solution(game))
    assert game.status is Status.CAUGHT and game.hurt_by == "reaper"
    assert game.lives == 2  # R4: a catch costs a life


def test_R2_one_hesitation_step_is_survivable():
    """R2: a single step into a warned plot and straight back does not kill you."""
    game = Game()
    entrance, first, _ = next(p for p in warned_plots(game.maze)
                              if game.maze.signs_next_to(p[0])[0].text.startswith("Wanna get stuck?"))
    walk(game, path_to(game, entrance))
    gap = game.reaper_distance()
    walk(game, [first, entrance])
    assert game.status is Status.PLAYING
    assert game.reaper_distance() == gap - 2
    walk(game, solution(game))
    assert game.status is Status.WON


# --- R3: losing when the reaper catches the player -------------------------
# Since round 2 (R4) a catch costs a life; these tests use a game on its last life,
# where a catch still means losing the game.

def test_R3_player_caught_when_reaper_reaches_their_tile():
    """R3: standing still next to the reaper (via wall bumps) is safe; moving toward it loses."""
    game = Game(lives=1)
    walk(game, [(1, 4)])  # step back toward the reaper: reaper (1,2), player (1,4)
    assert game.status is Status.PLAYING
    walk(game, [(1, 3)])  # reaper steps onto (1,3)
    assert game.status is Status.LOST
    assert game.player == game.reaper


def test_R3_player_caught_when_walking_into_the_reaper():
    """R3: stepping onto the reaper's tile also loses."""
    maze = Maze("######\n#RP  #\n####E#\n######", signs={})
    game = Game(maze, lives=1)
    game.move("left")
    assert game.status is Status.LOST


def test_R3_being_adjacent_to_the_reaper_is_not_caught():
    """R3: only sharing a tile counts as being caught."""
    game = Game()
    walk(game, [(1, 4)])
    assert game.reaper_distance() == 2
    walk(game, [(1, 5)])
    assert game.status is Status.PLAYING
    assert game.lives == 3


def test_R3_no_moves_accepted_after_losing():
    """R3: once caught on the last life, the game is over (R does not resume either)."""
    game = Game(lives=1)
    walk(game, [(1, 4), (1, 3)])
    assert game.status is Status.LOST
    turn, player = game.turn, game.player
    assert game.command("d") is Outcome.GAME_OVER
    assert game.move("right") is Outcome.GAME_OVER
    assert game.command("r") is Outcome.GAME_OVER
    assert (game.turn, game.player, game.status) == (turn, player, Status.LOST)


# --- R4: three lives; R resumes ----------------------------------------------

def get_caught(game):
    """From the start tiles, step back twice: the reaper lands on the player."""
    walk(game, [(1, 4), (1, 3)])


def test_R4_game_starts_with_three_lives():
    """R4: a new game has 3 lives."""
    assert MAX_LIVES == 3
    game = Game()
    assert game.lives == 3 and game.status is Status.PLAYING


def test_R4_a_catch_costs_one_life_and_pauses_the_game():
    """R4: being caught with lives left takes one life and waits for R."""
    game = Game()
    get_caught(game)
    assert game.status is Status.CAUGHT
    assert game.lives == 2
    assert game.player == game.reaper  # the catch stays visible until resume


def test_R4_walking_into_the_reaper_also_costs_a_life():
    """R4: stepping onto the reaper's tile costs a life as well."""
    maze = Maze("######\n#RP  #\n####E#\n######", signs={})
    game = Game(maze)
    game.move("left")
    assert game.status is Status.CAUGHT and game.lives == 2


def test_R4_moves_are_ignored_while_caught():
    """R4: until R is pressed, moves do nothing and use no turn."""
    game = Game()
    get_caught(game)
    turn, player = game.turn, game.player
    assert game.move("right") is Outcome.PAUSED
    assert game.command("d") is Outcome.PAUSED
    assert game.command("x") is Outcome.PAUSED
    assert (game.turn, game.player, game.status) == (turn, player, Status.CAUGHT)


def test_R4_r_resumes_with_both_back_on_their_start_tiles():
    """R4: R puts the player and the reaper back on their start tiles and the chase goes on."""
    game = Game()
    get_caught(game)
    assert game.command("r") is Outcome.RESUMED
    assert game.status is Status.PLAYING
    assert game.player == game.maze.player_start
    assert game.reaper == game.maze.reaper_start
    assert game.reaper_distance() == 4
    assert game.lives == 2


def test_R4_uppercase_r_and_resume_method_also_work():
    """R4: 'R' resumes too, and resume() is the same action."""
    game = Game()
    get_caught(game)
    assert game.command("R") is Outcome.RESUMED
    get_caught(game)
    assert game.resume() is Outcome.RESUMED and game.status is Status.PLAYING


def test_R4_turns_carry_over_after_resume():
    """R4: the turn counter keeps counting. (Explored tiles were remembered too until R9 removed the fog.)"""
    game = Game()
    get_caught(game)
    game.resume()
    assert game.turn == 2


def test_R4_r_while_playing_is_not_a_move():
    """R4: R only resumes after a catch; while playing it costs no turn."""
    game = Game()
    assert game.command("r") is Outcome.INVALID
    assert game.resume() is Outcome.INVALID
    assert game.turn == 0 and game.player == game.maze.player_start


def test_R4_the_third_catch_loses_the_game():
    """R4: the game is lost when the last of the 3 lives goes."""
    game = Game()
    for lives_left in (2, 1):
        get_caught(game)
        assert game.status is Status.CAUGHT and game.lives == lives_left
        game.resume()
    get_caught(game)
    assert game.status is Status.LOST and game.lives == 0


def test_R4_player_can_still_win_after_losing_lives():
    """R4: after resuming, following the signs still escapes the reaper."""
    game = Game()
    get_caught(game)
    game.resume()
    walk(game, solution(game))
    assert game.status is Status.WON and game.lives == 2


def test_R4_q_quits_while_caught():
    """R4: quitting still works while waiting to resume."""
    game = Game()
    get_caught(game)
    assert game.command("q") is Outcome.QUIT
    assert game.status is Status.QUIT


def test_R1_byte_order_mark_from_powershell_pipe_is_ignored():
    """R1: input piped from Windows PowerShell starts with a BOM; the first move still works."""
    game = Game()
    assert game.command("﻿d\n") is Outcome.MOVED
    assert game.player == (1, 6)


# --- R6: the game area is a graveyard ---------------------------------------

@pytest.mark.parametrize("layout,obstacle", [("#####\n#RP+#\n#  E#\n#####", "gravestone"),
                                             ("#####\n#RPT#\n#  E#\n#####", "dead tree"),
                                             ("#####\n#RP #\n#  E#\n#####", "iron fence")])
def test_R6_bumping_an_obstacle_names_it_and_costs_no_turn(layout, obstacle):
    """R6: gravestones, trees and fences block the way; the game says which one."""
    game = Game(Maze(layout, signs={}))
    direction = "up" if obstacle == "iron fence" else "right"
    assert game.move(direction) is Outcome.WALL
    assert game.bumped == obstacle
    assert game.turn == 0 and game.player == (1, 2) and game.reaper == (1, 1)
    game.move("down")
    assert game.bumped is None


# --- R7: hazards hurt the player ---------------------------------------------

def test_R7_stepping_into_an_open_grave_costs_a_life():
    """R7: the open grave four steps east of the start takes a life; the reaper stays put."""
    game = Game()
    assert game.maze.hazard((1, 9)) == "open grave"
    walk(game, [(1, 6), (1, 7), (1, 8)])
    reaper = game.reaper
    assert game.move("right") is Outcome.MOVED
    assert game.status is Status.CAUGHT
    assert game.hurt_by == "open grave"
    assert game.lives == 2 and game.turn == 4
    assert game.player == (1, 9) and game.reaper == reaper


def test_R7_thorn_bushes_also_cost_a_life():
    """R7: thorn bushes hurt just like open graves."""
    game = Game(Maze("#######\n#R P*E#\n#######", signs={}))
    game.move("right")
    assert game.status is Status.CAUGHT and game.hurt_by == "thorn bush" and game.lives == 2


def test_R7_hazard_on_the_last_life_loses_the_game():
    """R7: a hazard on the last life is GAME OVER, like the reaper's catch (R3)."""
    game = Game(Maze("#######\n#R P*E#\n#######", signs={}), lives=1)
    game.move("right")
    assert game.status is Status.LOST and game.lives == 0 and game.hurt_by == "thorn bush"
    assert game.command("r") is Outcome.GAME_OVER


def test_R7_r_resumes_from_the_start_after_a_hazard():
    """R7: after a hazard, R puts both figures back on their start tiles (as after a catch, R4)."""
    game = Game()
    walk(game, [(1, 6), (1, 7), (1, 8), (1, 9)])
    assert game.command("d") is Outcome.PAUSED
    assert game.command("r") is Outcome.RESUMED
    assert game.status is Status.PLAYING and game.hurt_by is None
    assert (game.player, game.reaper) == (game.maze.player_start, game.maze.reaper_start)
    assert game.lives == 2 and game.turn == 4


def test_R7_three_hazards_lose_the_game():
    """R7: hazards and the reaper share the same three lives."""
    game = Game()
    for _ in range(2):
        walk(game, [(1, 6), (1, 7), (1, 8), (1, 9)])
        game.resume()
    walk(game, [(1, 4), (1, 3)])  # and the reaper takes the last one
    assert game.status is Status.LOST and game.hurt_by == "reaper"


def test_R7_reaper_glides_over_hazards_unharmed():
    """R7: hazards only hurt the player; the reaper crosses them on its shortest path."""
    game = Game(Maze("########\n#RO P E#\n########", signs={}))
    game.move("right")  # the only way to the player runs over the open grave
    assert game.reaper == (1, 2) and game.maze.hazard(game.reaper) == "open grave"
    assert game.status is Status.PLAYING and game.lives == 3


def test_R7_walking_into_the_reaper_on_a_hazard_counts_as_the_reaper():
    """R7: if the reaper stands on a hazard, stepping onto it is a catch, not a fall."""
    game = Game(Maze("#######\n#ROP E#\n#######", signs={}))
    game.reaper = (1, 2)
    game.move("left")
    assert game.status is Status.CAUGHT and game.hurt_by == "reaper"


def test_R7_the_reaper_catch_is_named_too():
    """R7: hurt_by tells the front ends who took the life; it is empty while playing."""
    game = Game()
    assert game.hurt_by is None
    walk(game, [(1, 4), (1, 3)])
    assert game.hurt_by == "reaper"


# --- R10: jumping over low hurdles (and hazards) with the Up arrow ------------

JUMP_YARD = "########\n#R P=  #\n#      #\n######E#\n########"  # a fallen headstone right of P


def test_R10_walking_into_a_low_hurdle_is_blocked_and_costs_no_turn():
    """R10: a low hurdle blocks walking like any obstacle; the bump names it."""
    game = Game(Maze(JUMP_YARD, signs={}))
    assert game.move("right") is Outcome.WALL
    assert game.bumped == "fallen headstone" and game.turn == 0 and game.player == (1, 3)


def test_R10_jump_leaps_over_a_low_hurdle_in_one_turn():
    """R10: a jump lands two tiles on, takes one turn, and the reaper takes one step."""
    game = Game(Maze(JUMP_YARD, signs={}))
    assert game.jump() is Outcome.MOVED
    assert game.player == (1, 5) and game.turn == 1 and game.jumped
    assert game.reaper == (1, 2)
    game.move("right")
    assert not game.jumped


def test_R10_the_player_faces_the_way_they_last_tried_to_move():
    """R10: the player starts facing right; every move or bump turns them."""
    game = Game()
    assert game.facing == "right"
    game.move("up")  # the graveyard fence: a bump, but it still turns the player
    assert game.facing == "up" and game.turn == 0
    game.move("down")
    assert game.facing == "down"


def test_R10_up_jumps_in_the_facing_direction():
    """R10: the jump goes the way the player faces, not always north."""
    game = Game(Maze("########\n#R P   #\n#   =  #\n#   C  #\n#   E  #\n########", signs={}))
    game.move("right")      # (1,4), facing right
    game.move("down")       # bumps the fallen headstone at (2,4): now facing down
    assert game.facing == "down"
    assert game.jump() is Outcome.NO_JUMP  # the landing tile (3,4) is a coffin
    assert game.jump_blocked == "coffin" and game.player == (1, 4)


def test_R10_nothing_to_jump_over_costs_no_turn():
    """R10: Up in front of plain grass does nothing (a jump is not a free double step)."""
    game = Game()
    assert game.jump() is Outcome.NO_JUMP
    assert game.jump_blocked == "nothing" and game.turn == 0 and game.player == game.maze.player_start


@pytest.mark.parametrize("ahead,blocker", [("=+", "gravestone"), ("=#", "iron fence"), ("=O", "open grave"),
                                          ("O*", "thorn bush"), ("==", "fallen headstone")])
def test_R10_cannot_land_on_an_obstacle_hazard_or_hurdle(ahead, blocker):
    """R10: the landing tile must be safe ground; otherwise no jump and no turn."""
    game = Game(Maze(f"##########\n#R P{ahead}   #\n#      E #\n##########", signs={}))
    assert game.jump() is Outcome.NO_JUMP
    assert game.jump_blocked == blocker and game.turn == 0


def test_R10_jumping_over_an_open_grave_does_no_harm():
    """R10 / R7: a hazard can be jumped over safely."""
    game = Game()
    walk(game, [(1, 6), (1, 7), (1, 8)])  # the open grave at (1,9) is ahead
    assert game.jump() is Outcome.MOVED
    assert game.player == (1, 10) and game.lives == 3 and game.status is Status.PLAYING


def test_R10_landing_on_the_exit_wins():
    """R10: a jump onto the exit escapes before the reaper moves."""
    game = Game(Maze("#######\n#R P=E#\n#######", signs={}))
    game.jump()
    assert game.status is Status.WON and game.reaper == (1, 1)


def test_R10_leaping_into_or_through_the_reaper_is_a_catch():
    """R10: the reaper cannot be jumped; landing on or passing through its tile is a catch."""
    game = Game(Maze("#######\n#  P=R#\n#E    #\n#######", signs={}))
    game.reaper = (1, 5)
    game.jump()
    assert game.status is Status.CAUGHT and game.hurt_by == "reaper"
    game = Game(Maze("########\n#  P= R#\n#E     #\n########", signs={}))
    game.reaper = (1, 4)  # gliding over the fallen headstone
    game.jump()
    assert game.status is Status.CAUGHT and game.hurt_by == "reaper"


def test_R10_j_command_jumps_in_the_terminal():
    """R10: in --text, j + Enter is the jump."""
    game = Game(Maze(JUMP_YARD, signs={}))
    assert game.command("j") is Outcome.MOVED and game.player == (1, 5)


def test_R10_no_jumping_while_caught_or_after_the_game():
    """R10: a jump is a move: ignored while waiting for R and after the game ends."""
    game = Game()
    get_caught(game)
    assert game.jump() is Outcome.PAUSED
    game = Game(lives=1)
    get_caught(game)
    assert game.jump() is Outcome.GAME_OVER


def test_R10_a_jump_on_the_way_gains_a_step_on_the_reaper():
    """R10: jumping the coffin on the path puts the reaper one more step behind, and the player still wins.

    Changed by R12: the coffin lies across the path, so it must be jumped."""
    game = Game()
    route = solution(game)
    walk(game, route[:route.index((1, 13)) + 1])
    gap = game.reaper_distance()
    assert game.move("right") is Outcome.WALL and game.bumped == "coffin"
    assert game.jump() is Outcome.MOVED and game.player == (1, 15)
    assert game.reaper_distance() == gap + 1
    walk(game, solution(game))
    assert game.status is Status.WON
