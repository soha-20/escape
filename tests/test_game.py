"""Tests for turn order, the chase, winning and losing."""

import pytest

from escape_game.game import Game, Outcome, Status
from escape_game.maze import DIRECTIONS, Maze, Sign, WARNING

STEP_TO_DIR = {v: k for k, v in DIRECTIONS.items()}


def walk(game, tiles):
    """Move the player along consecutive tiles; stop early if the game ends."""
    for nxt in tiles:
        if game.status is not Status.PLAYING:
            break
        delta = (nxt[0] - game.player[0], nxt[1] - game.player[1])
        assert game.move(STEP_TO_DIR[delta]) is Outcome.MOVED


def solution(game):
    return game.maze.shortest_path(game.player, game.maze.exit)[1:]


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
    assert game.turn == 44


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
    """R1: walls block the player and the reaper gets no free step."""
    game = Game()
    assert game.move("up") is Outcome.WALL
    assert game.turn == 0 and game.player == game.maze.player_start
    assert game.reaper == game.maze.reaper_start


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


def test_R1_fog_of_war_reveals_tiles_near_the_player():
    """R1: only tiles within the view radius are visible; seen tiles are remembered."""
    game = Game()
    assert game.visible((1, 8)) and not game.visible((1, 9))
    assert (1, 9) not in game.seen
    game.move("right")
    assert (1, 9) in game.seen
    game.move("left")
    assert (1, 9) in game.seen and not game.visible((1, 9))


# --- R2: following signs vs ignoring them ----------------------------------

def fork_next_to(maze, sign_pos):
    return next((sign_pos[0] + dr, sign_pos[1] + dc) for dr, dc in DIRECTIONS.values()
                if not maze.is_wall((sign_pos[0] + dr, sign_pos[1] + dc)))


@pytest.mark.parametrize("sign_pos", [p for p, s in Maze().signs.items() if s.kind == WARNING])
def test_R2_ignoring_a_warning_sign_gets_the_player_caught(sign_pos):
    """R2: exploring the branch a red sign warns about, then turning back, ends in capture."""
    game = Game()
    maze = game.maze
    fork = fork_next_to(maze, sign_pos)
    route = solution(game)
    walk(game, route[: route.index(fork) + 1])
    assert game.status is Status.PLAYING
    # go to the end of the warned branch ...
    dr, dc = DIRECTIONS[maze.signs[sign_pos].points]
    branch = []
    nxt = (fork[0] + dr, fork[1] + dc)
    while not maze.is_wall(nxt):
        branch.append(nxt)
        nxt = (nxt[0] + dr, nxt[1] + dc)
    walk(game, branch)
    assert game.status is Status.PLAYING
    # ... it is a dead end, so the only way out is back past the reaper
    walk(game, branch[-2::-1] + [fork] + route[route.index(fork) + 1:])
    assert game.status is Status.LOST


def test_R2_one_hesitation_step_is_survivable():
    """R2: a single step into a wrong branch and straight back does not kill you."""
    game = Game()
    walk(game, [(1, 6), (1, 7), (1, 8), (1, 9), (1, 10), (1, 9)])
    assert game.status is Status.PLAYING
    walk(game, solution(game))
    assert game.status is Status.WON


# --- R3: losing when the reaper catches the player -------------------------

def test_R3_player_caught_when_reaper_reaches_their_tile():
    """R3: standing still next to the reaper (via wall bumps) is safe; moving toward it loses."""
    game = Game()
    walk(game, [(1, 4)])  # step back toward the reaper: reaper (1,2), player (1,4)
    assert game.status is Status.PLAYING
    walk(game, [(1, 3)])  # reaper steps onto (1,3)
    assert game.status is Status.LOST
    assert game.player == game.reaper


def test_R3_player_caught_when_walking_into_the_reaper():
    """R3: stepping onto the reaper's tile also loses."""
    maze = Maze("######\n#RP  #\n####E#\n######", signs={})
    game = Game(maze)
    game.move("left")
    assert game.status is Status.LOST


def test_R3_being_adjacent_to_the_reaper_is_not_caught():
    """R3: only sharing a tile counts as being caught."""
    game = Game()
    walk(game, [(1, 4)])
    assert game.reaper_distance() == 2
    walk(game, [(1, 5)])
    assert game.status is Status.PLAYING


def test_R3_no_moves_accepted_after_losing():
    """R3: once caught, the game is over."""
    game = Game()
    walk(game, [(1, 4), (1, 3)])
    assert game.status is Status.LOST
    turn, player = game.turn, game.player
    assert game.command("d") is Outcome.GAME_OVER
    assert game.move("right") is Outcome.GAME_OVER
    assert (game.turn, game.player) == (turn, player)


def test_R1_byte_order_mark_from_powershell_pipe_is_ignored():
    """R1: input piped from Windows PowerShell starts with a BOM; the first move still works."""
    game = Game()
    assert game.command("﻿d\n") is Outcome.MOVED
    assert game.player == (1, 6)
