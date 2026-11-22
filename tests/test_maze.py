"""Tests for the fixed graveyard layout and its signs.

Round 3 (R6) replaced the corridor maze with an open graveyard. The R2 tests below were adapted:
open ground has no corridor forks, so the signs now mark fenced dead-end plots and the gates that lead on.
Round 5 (R12) lays the graveyard out along a gravel path whose hurdles must be jumped, so the R2, R6,
R7 and R10 tests were adapted again: the safe route is Maze.player_route (walking and jumping).
"""

import pytest

from escape_game.maze import DIRECTIONS, GUIDE, HAZARDS, LOW_HURDLES, OBSTACLES, WARNING, Maze, Sign


@pytest.fixture
def maze():
    return Maze()


def safe_route(maze):
    """R12: the player's way to the exit, walking and jumping, never landing on a hazard."""
    return maze.player_route(maze.player_start, maze.exit)


def jumped_tiles(route):
    """The tiles the route leaps over (between two route tiles 2 apart)."""
    return [((a[0] + b[0]) // 2, (a[1] + b[1]) // 2) for a, b in zip(route, route[1:])
            if abs(a[0] - b[0]) + abs(a[1] - b[1]) == 2]


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
    for tile in route[1:]:  # R12: behind the start lies only the stretch the Reaper comes from
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
        return len(maze.player_route(p, maze.exit)) - 1

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


def test_R6_graveyard_is_a_path_through_graves_not_a_maze(maze):
    """R6 (changed by R12 in round 5): no longer open ground, but not a maze either: one path to
    follow, which forks only where a warning sign stands."""
    route = safe_route(maze)
    jumped = set(jumped_tiles(route))
    forks = [t for t in route[1:] if any(n not in route and n not in jumped for n in maze.neighbours(t))]
    warned = {warned_entrance(maze, p) for p, s in maze.signs.items() if s.kind == WARNING}
    assert forks and set(forks) <= warned


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


def test_R6_every_patch_of_grass_can_be_reached(maze):
    """R6: no walled-in grass the player (or the reaper) could never get to."""
    reach, stack = {maze.player_start}, [maze.player_start]
    while stack:
        for nxt in maze.neighbours(stack.pop()):
            if nxt not in reach:
                reach.add(nxt)
                stack.append(nxt)
    walkable = {(r, c) for r in range(maze.height) for c in range(maze.width) if not maze.is_wall((r, c))}
    assert walkable == reach


# --- R10: low hurdles the player can jump -------------------------------------

def test_R10_low_hurdles_are_fallen_headstones_and_coffins(maze):
    """R10: the graveyard has low hurdles of two kinds: fallen headstones (=) and coffins (C)."""
    assert LOW_HURDLES == {"=": "fallen headstone", "C": "coffin"}
    assert tiles_of(maze, "=") and tiles_of(maze, "C")
    assert len(tiles_of(maze, "=") + tiles_of(maze, "C")) >= 4
    for p in tiles_of(maze, "C"):
        assert maze.low_hurdle(p) == "coffin" and maze.obstacle(p) is None and maze.hazard(p) is None
    assert maze.low_hurdle(maze.player_start) is None


def test_R10_low_hurdles_block_the_player_on_foot_but_not_the_reaper():
    """R10: a player route walks around a low hurdle; the reaper glides over it."""
    small = Maze("######\n#R= E#\n#    #\n#P   #\n######", signs={})
    assert small.shortest_path((1, 1), (1, 4)) == [(1, 1), (1, 2), (1, 3), (1, 4)]
    assert (1, 2) not in small.shortest_path((1, 1), (1, 4), avoid_hazards=True)
    assert not small.is_wall((1, 2))


def test_R10_every_low_hurdle_lies_on_the_route_and_is_jumped(maze):
    """R10 (changed by R12 in round 5): each low hurdle lies across the path, and the route leaps it."""
    jumped = jumped_tiles(safe_route(maze))
    for hurdle in tiles_of(maze, "=") + tiles_of(maze, "C"):
        assert hurdle in jumped, f"the low hurdle at {hurdle} is not on the route"


def test_R10_walking_and_jumping_reach_every_patch_of_ground(maze):
    """R10 (changed by R12): hurdles block walking, but with jumps the player can reach every safe tile."""
    reach, stack = {maze.player_start}, [maze.player_start]
    while stack:
        for nxt, _ in maze.player_moves(stack.pop()):
            if nxt not in reach:
                reach.add(nxt)
                stack.append(nxt)
    grass = {(r, c) for r in range(maze.height) for c in range(maze.width)
             if not maze.is_wall((r, c)) and not maze.hazard((r, c)) and not maze.low_hurdle((r, c))}
    assert grass == reach


def test_R10_player_moves_step_or_jump_onto_safe_ground():
    """R10: one move is a step onto safe ground or a leap over a hurdle or hazard onto safe ground."""
    small = Maze("#######\n#RP= E#\n# O   #\n#     #\n#######", signs={})
    assert small.player_moves((1, 2)) == [((3, 2), True), ((1, 1), False), ((1, 4), True)]
    assert small.player_route((1, 2), (1, 5)) == [(1, 2), (1, 4), (1, 5)]


# --- R12: a structured graveyard, not scattered graves -----------------------

def test_R12_a_gravel_path_leads_from_the_start_to_the_exit(maze):
    """R12: every tile the safe route touches is gravel path (or the start or the gate)."""
    route = safe_route(maze)
    assert route[0] == maze.player_start and route[-1] == maze.exit
    assert all(maze.on_path(t) for t in route)
    assert not maze.on_path((3, 20))  # the dead-end alleys are grass, not path
    assert len(tiles_of(maze, ".")) >= 60


def test_R12_graves_stand_in_neat_rows(maze):
    """R12: no gravestone stands alone; each is part of a row, and there are long, unbroken rows."""
    for r, c in tiles_of(maze, "+"):
        assert maze.is_wall((r, c - 1)) or maze.is_wall((r, c + 1)), f"stray gravestone at {(r, c)}"
    rows = maze.layout.splitlines()
    long_rows = [row for row in rows[1:-1] if sum(ch in "+T!" for ch in row[1:-1]) >= len(row) - 4]
    assert len(long_rows) >= 5


def test_R12_trees_punctuate_the_rows_at_a_steady_spacing(maze):
    """R12: in the grave rows, a dead tree stands every sixth column."""
    rows = maze.layout.splitlines()
    for r in (2, 4, 6, 8, 10):
        assert [c for c, ch in enumerate(rows[r]) if ch == "T"] == [4, 10, 16, 22]


def test_R12_hurdles_lie_on_the_path_at_a_steady_rhythm(maze):
    """R12: the route leaps at least 12 hurdles, 3 to 5 tiles apart along each lane."""
    route = safe_route(maze)
    jumps = [i for i, (a, b) in enumerate(zip(route, route[1:])) if abs(a[0] - b[0]) + abs(a[1] - b[1]) == 2]
    assert len(jumps) >= 12
    for a, b in zip(jumps, jumps[1:]):
        if route[a][0] == route[b][0]:  # same lane
            tiles_between = sum(abs(p[1] - q[1]) for p, q in zip(route[a + 1:b + 1], route[a + 2:b + 1])) + 1
            assert 3 <= tiles_between <= 5, f"jumps at {route[a]} and {route[b]} are {tiles_between} apart"


def test_R12_every_jump_is_taken_running_straight(maze):
    """R12/R15: no hurdle lies at a bend, so the player reaches each one running in the jump's direction."""
    route = safe_route(maze)
    for i in range(1, len(route) - 1):
        a, b = route[i], route[i + 1]
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) == 2:
            before = (a[0] - route[i - 1][0], a[1] - route[i - 1][1])
            jump = ((b[0] - a[0]) // 2, (b[1] - a[1]) // 2)
            assert before == jump, f"the jump from {a} needs a turn first"


def test_R12_each_lane_ends_against_a_dead_tree(maze):
    """R12: where the path turns off a lane into a bend, a dead tree stands straight ahead."""
    route = safe_route(maze)
    for prev, cur, nxt in zip(route, route[1:], route[2:]):
        came = (cur[0] - prev[0], cur[1] - prev[1])
        goes = (nxt[0] - cur[0], nxt[1] - cur[1])
        if came[0] == 0 and goes[1] == 0 and nxt != maze.exit:  # off a lane, into a bend
            ahead = (cur[0] + came[0], cur[1] + came[1] // abs(came[1]))
            assert maze.obstacle(ahead) == "dead tree", f"the lane ending at {cur} has no tree"


def test_R12_the_exit_gate_is_in_the_south_fence(maze):
    """R12: the path ends at an iron gate set in the graveyard fence."""
    assert maze.exit[0] == maze.height - 1
    assert maze.on_path((maze.exit[0] - 1, maze.exit[1]))
