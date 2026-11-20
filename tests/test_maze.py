"""Tests for the fixed graveyard layout and its signs.

Round 3 (R6) replaced the corridor maze with an open graveyard. The R2 tests below were adapted:
open ground has no corridor forks, so the signs now mark fenced dead-end plots and the gates that lead on.
"""

import pytest

from escape_game.maze import DIRECTIONS, GUIDE, HAZARDS, OBSTACLES, WARNING, Maze, Sign


@pytest.fixture
def maze():
    return Maze()


def safe_route(maze):
    return maze.shortest_path(maze.player_start, maze.exit, avoid_hazards=True)


def step(pos, direction):
    dr, dc = DIRECTIONS[direction]
    return (pos[0] + dr, pos[1] + dc)


def readers(maze, sign_pos):
    """Walkable tiles a sign can be read from."""
    return [p for p in (step(sign_pos, d) for d in DIRECTIONS) if not maze.is_wall(p)]


def region_beyond(maze, entrance, first):
    """Every tile reachable from `first` without passing through `entrance`."""
    seen, stack = {entrance, first}, [first]
    while stack:
        for nxt in maze.neighbours(stack.pop()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    seen.discard(entrance)
    return seen


def is_dead_end(maze, entrance, first, route=()):
    """A pocket behind `entrance` that holds neither the exit, the start nor any other part of the route."""
    region = region_beyond(maze, entrance, first)
    return not region & ({maze.exit, maze.player_start} | set(route))


def warned_entrance(maze, sign_pos):
    """The tile in front of a warning sign from which it points into a dead end, or None."""
    sign = maze.signs[sign_pos]
    for reader in readers(maze, sign_pos):
        first = step(reader, sign.points)
        if not maze.is_wall(first) and is_dead_end(maze, reader, first):
            return reader
    return None


# --- R2: hints and signs ----------------------------------------------------

def test_R2_exit_is_reachable_from_start(maze):
    """R2: the graveyard is a hurdle, but it can be crossed without stepping on a hazard."""
    assert safe_route(maze) is not None


def test_R2_graveyard_has_dead_end_plots_that_force_a_choice(maze):
    """R2: at least 3 places where the player must choose, each a warned dead end."""
    warnings = [p for p, s in maze.signs.items() if s.kind == WARNING]
    assert len(warnings) >= 3
    assert all(warned_entrance(maze, p) is not None for p in warnings)


def test_R2_every_dead_end_beside_the_route_is_signed(maze):
    """R2: wherever the safe route passes a dead end, a warning sign stands there."""
    route = safe_route(maze)
    warned = {warned_entrance(maze, p) for p, s in maze.signs.items() if s.kind == WARNING}
    for tile in route:
        for first in maze.neighbours(tile):
            if first not in route and is_dead_end(maze, tile, first, route):
                if len(region_beyond(maze, tile, first)) >= 3:  # deep enough to be fatal
                    assert tile in warned, f"dead end at {first} beside the route has no warning"


def test_R2_warning_signs_point_into_dead_ends(maze):
    """R2: red warning signs mark the place that leads nowhere."""
    for pos, sign in maze.signs.items():
        if sign.kind == WARNING:
            assert warned_entrance(maze, pos) is not None, f"warning at {pos} does not point into a dead end"


def test_R2_guide_signs_point_along_a_shortest_safe_way(maze):
    """R2: green guide signs point one step closer to the exit."""
    guides = {p: s for p, s in maze.signs.items() if s.kind == GUIDE}
    assert len(guides) >= 2

    def safe_dist(p):
        return len(maze.shortest_path(p, maze.exit, avoid_hazards=True)) - 1

    route = safe_route(maze)
    for pos, sign in guides.items():
        on_route = [r for r in readers(maze, pos) if r in route]
        assert on_route, f"guide at {pos} cannot be read from the route"
        r = on_route[0]
        assert safe_dist(step(r, sign.points)) == safe_dist(r) - 1


def test_R2_example_sign_wanna_get_stuck_is_a_red_warning(maze):
    """R2: the example from problem.md appears as a warning (red) sign."""
    matches = [s for s in maze.signs.values() if "Wanna get stuck?" in s.text]
    assert len(matches) == 1 and matches[0].kind == WARNING


def test_R2_signs_are_read_from_the_adjacent_tile(maze):
    """R2: standing next to a sign shows it; standing elsewhere does not."""
    for pos, sign in maze.signs.items():
        assert sign in maze.signs_next_to(readers(maze, pos)[0])
    assert maze.signs_next_to(maze.player_start) == []


def test_R2_layout_and_sign_table_must_agree():
    """R2: a '!' with no sign text (or vice versa) is rejected."""
    layout = "#!###\n#RPE#\n#####"
    with pytest.raises(ValueError):
        Maze(layout, signs={})
    Maze(layout, signs={(0, 1): Sign("hi", GUIDE, "down")})  # agrees: no error


@pytest.mark.parametrize("layout", ["", "###\n#P", "#####\n#P E#\n#####", "#####\n#PRE?\n#####"])
def test_R2_malformed_layouts_are_rejected(layout):
    """R2: the loader refuses broken layouts instead of building a broken hurdle."""
    with pytest.raises(ValueError):
        Maze(layout, signs={})


# --- R6: the game area is a graveyard ----------------------------------------

def tiles_of(maze, mark):
    return [(r, c) for r, row in enumerate(maze.layout.splitlines()) for c, ch in enumerate(row) if ch == mark]


def test_R6_graveyard_is_fenced_and_full_of_graves(maze):
    """R6: the area is a fenced graveyard with many gravestones and some dead trees."""
    assert len(tiles_of(maze, "+")) >= 30
    assert len(tiles_of(maze, "T")) >= 4
    for r in range(maze.height):
        assert maze.obstacle((r, 0)) == maze.obstacle((r, maze.width - 1)) == "iron fence"
    for c in range(maze.width):
        assert maze.obstacle((0, c)) == "iron fence" or (0, c) in maze.signs


def test_R6_graveyard_is_open_ground_not_corridors(maze):
    """R6: unlike the old maze, most walkable tiles have room on three or four sides."""
    walkable = [(r, c) for r in range(maze.height) for c in range(maze.width) if not maze.is_wall((r, c))]
    roomy = [p for p in walkable if len(maze.neighbours(p)) >= 3]
    assert len(roomy) > len(walkable) / 2


def test_R6_every_layout_mark_has_a_graveyard_name():
    """R6: the obstacles are fences, gravestones, trees and signposts; nothing is a plain wall."""
    assert OBSTACLES == {"#": "iron fence", "+": "gravestone", "T": "dead tree", "!": "signpost"}
    maze = Maze("#####\n#RP+#\n#T E#\n#####", signs={})
    assert maze.obstacle((1, 3)) == "gravestone"
    assert maze.obstacle((2, 1)) == "dead tree"
    assert maze.obstacle((0, 0)) == "iron fence"
    assert maze.obstacle((-1, 2)) == "iron fence"  # outside the grounds
    assert maze.obstacle((1, 2)) is None


# --- R7: graves and other objects are the hurdles; some can hurt -------------

def test_R7_open_graves_and_thorns_are_hazards_on_walkable_ground(maze):
    """R7: open graves and thorn bushes can be stepped on (and hurt); graves etc. block."""
    assert HAZARDS == {"O": "open grave", "*": "thorn bush"}
    graves, thorns = tiles_of(maze, "O"), tiles_of(maze, "*")
    assert len(graves) >= 5 and len(thorns) >= 5
    for p in graves:
        assert maze.hazard(p) == "open grave" and not maze.is_wall(p)
    for p in thorns:
        assert maze.hazard(p) == "thorn bush" and not maze.is_wall(p)
    assert maze.hazard(maze.player_start) is None
    assert maze.hazard((0, 0)) is None


def test_R7_safe_route_never_steps_on_a_hazard(maze):
    """R7: there is always a way through that avoids every hazard."""
    assert all(maze.hazard(p) is None for p in safe_route(maze))


def test_R7_hazards_sit_where_a_careless_player_would_walk(maze):
    """R7: hazards are in the open fields, next to the safe route, not hidden in corners."""
    route = set(safe_route(maze))
    hazards = tiles_of(maze, "O") + tiles_of(maze, "*")
    beside = [h for h in hazards if any(n in route for n in maze.neighbours(h))]
    assert len(beside) >= 4


def test_R7_pathfinding_can_cross_or_avoid_hazards():
    """R7: the reaper's path may cross a hazard; a safe path goes around it."""
    maze = Maze("######\n#RO E#\n#    #\n#P   #\n######", signs={})
    assert maze.shortest_path((1, 1), (1, 4)) == [(1, 1), (1, 2), (1, 3), (1, 4)]
    safe = maze.shortest_path((1, 1), (1, 4), avoid_hazards=True)
    assert (1, 2) not in safe and len(safe) == 6
    assert maze.neighbours((1, 1), avoid_hazards=True) == [(2, 1)]
