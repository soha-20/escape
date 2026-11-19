"""Tests for the fixed maze and its signs."""

import pytest

from escape_game.maze import DIRECTIONS, GUIDE, WARNING, Maze, Sign


@pytest.fixture
def maze():
    return Maze()


def route(maze):
    return maze.shortest_path(maze.player_start, maze.exit)


def fork_of(maze, sign_pos):
    """The single floor tile a sign can be read from."""
    readers = [p for p in [(sign_pos[0] + dr, sign_pos[1] + dc) for dr, dc in DIRECTIONS.values()]
               if not maze.is_wall(p)]
    assert len(readers) == 1, f"sign at {sign_pos} should be readable from exactly one tile"
    return readers[0]


def branch_reaches_exit(maze, fork, first):
    """Can you reach the exit from `first` without going back through `fork`?"""
    seen, stack = {fork, first}, [first]
    while stack:
        cur = stack.pop()
        if cur == maze.exit:
            return True
        for nxt in maze.neighbours(cur):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return False


def step(pos, direction):
    dr, dc = DIRECTIONS[direction]
    return (pos[0] + dr, pos[1] + dc)


def test_R2_exit_is_reachable_from_start(maze):
    """R2: the maze is a hurdle, but it can be solved."""
    assert route(maze) is not None


def test_R2_maze_has_forks_that_force_a_choice(maze):
    """R2: the route has several forks where the player must pick a way."""
    forks = [p for p in route(maze) if len(maze.neighbours(p)) >= 3]
    assert len(forks) >= 3


def test_R2_every_fork_on_the_route_has_a_sign(maze):
    """R2: at every fork there is a sign telling the player which way to go."""
    forks = {p for p in route(maze) if len(maze.neighbours(p)) >= 3}
    signed = {fork_of(maze, pos) for pos in maze.signs}
    assert forks <= signed


def test_R2_warning_signs_point_into_dead_ends(maze):
    """R2: red warning signs mark the branch that leads nowhere."""
    warnings = {p: s for p, s in maze.signs.items() if s.kind == WARNING}
    assert warnings
    for pos, sign in warnings.items():
        fork = fork_of(maze, pos)
        first = step(fork, sign.points)
        assert not maze.is_wall(first), f"warning at {pos} points into a wall"
        assert not branch_reaches_exit(maze, fork, first), f"warning at {pos} points toward the exit"


def test_R2_guide_signs_point_along_the_route(maze):
    """R2: green guide signs point the way out."""
    guides = {p: s for p, s in maze.signs.items() if s.kind == GUIDE}
    assert guides
    path = route(maze)
    for pos, sign in guides.items():
        fork = fork_of(maze, pos)
        nxt = path[path.index(fork) + 1]
        assert step(fork, sign.points) == nxt


def test_R2_example_sign_wanna_get_stuck_is_a_red_warning(maze):
    """R2: the example from problem.md appears as a warning (red) sign."""
    matches = [s for s in maze.signs.values() if "Wanna get stuck?" in s.text]
    assert len(matches) == 1 and matches[0].kind == WARNING


def test_R2_signs_are_read_from_the_adjacent_tile(maze):
    """R2: standing next to a sign shows it; standing elsewhere does not."""
    for pos, sign in maze.signs.items():
        assert sign in maze.signs_next_to(fork_of(maze, pos))
    assert maze.signs_next_to(maze.player_start) == []


def test_R2_layout_and_sign_table_must_agree():
    """R2: a '!' with no sign text (or vice versa) is rejected."""
    layout = "#!###\n#RPE#\n#####"
    with pytest.raises(ValueError):
        Maze(layout, signs={})
    Maze(layout, signs={(0, 1): Sign("hi", GUIDE, "down")})  # agrees: no error


@pytest.mark.parametrize("layout", ["", "###\n#P", "#####\n#P E#\n#####", "#####\n#PRE?\n#####"])
def test_R2_malformed_layouts_are_rejected(layout):
    """R2: the maze loader refuses broken layouts instead of building a broken hurdle."""
    with pytest.raises(ValueError):
        Maze(layout, signs={})
