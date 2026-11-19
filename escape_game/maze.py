"""The fixed maze, its wall signs, and pathfinding.

Legend for LAYOUT:
    #  wall          (space) floor
    P  player start  R  reaper start  E  exit
    !  wall carrying a sign (its text lives in SIGNS)
"""

from collections import deque
from dataclasses import dataclass

Pos = tuple[int, int]  # (row, column)

LAYOUT = """\
#########!##########!######
#R   P         ##        ##
######### ####### ## ### ##
######### ####### ## ### ##
######### ###!### ## ### ##
#########         ## ### ##
############# ########## ##
############# ####       !#
############# ########## ##
############# #E         ##
###########################"""

# Directions in a fixed order; BFS uses this order, which makes the reaper deterministic.
DIRECTIONS: dict[str, Pos] = {
    "up": (-1, 0),
    "down": (1, 0),
    "left": (0, -1),
    "right": (0, 1),
}

WARNING = "warning"  # red: marks the wrong way
GUIDE = "guide"      # green: points toward the exit


@dataclass(frozen=True)
class Sign:
    text: str
    kind: str        # WARNING or GUIDE
    points: str      # direction (key of DIRECTIONS) the sign refers to, seen from the fork


SIGNS: dict[Pos, Sign] = {
    (0, 9): Sign("Wanna get stuck? →", WARNING, "right"),
    (4, 13): Sign("The air smells of freedom →  Don't look down.", GUIDE, "right"),
    (0, 20): Sign("↓ Down there is where the last one died.", WARNING, "down"),
    (7, 25): Sign("Keep falling ↓ the way out is close.", GUIDE, "down"),
}


class Maze:
    def __init__(self, layout: str = LAYOUT, signs: dict[Pos, Sign] | None = None):
        rows = layout.splitlines()
        if not rows or any(len(r) != len(rows[0]) for r in rows):
            raise ValueError("maze layout must be a non-empty rectangle")
        self.height = len(rows)
        self.width = len(rows[0])
        self.signs = dict(SIGNS if signs is None else signs)
        self._walls: set[Pos] = set()
        marks: dict[str, Pos] = {}
        sign_marks: set[Pos] = set()
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                if ch in "#!":
                    self._walls.add((r, c))
                    if ch == "!":
                        sign_marks.add((r, c))
                elif ch in "PRE":
                    if ch in marks:
                        raise ValueError(f"more than one {ch!r} in maze layout")
                    marks[ch] = (r, c)
                elif ch != " ":
                    raise ValueError(f"unknown maze character {ch!r}")
        missing = set("PRE") - marks.keys()
        if missing:
            raise ValueError(f"maze layout is missing {sorted(missing)}")
        if sign_marks != set(self.signs):
            raise ValueError("'!' marks in the layout must match the sign table")
        self.player_start = marks["P"]
        self.reaper_start = marks["R"]
        self.exit = marks["E"]

    def is_wall(self, pos: Pos) -> bool:
        r, c = pos
        return not (0 <= r < self.height and 0 <= c < self.width) or pos in self._walls

    def neighbours(self, pos: Pos) -> list[Pos]:
        """Open floor tiles orthogonally adjacent to pos, in DIRECTIONS order."""
        result = []
        for dr, dc in DIRECTIONS.values():
            nxt = (pos[0] + dr, pos[1] + dc)
            if not self.is_wall(nxt):
                result.append(nxt)
        return result

    def shortest_path(self, start: Pos, goal: Pos) -> list[Pos] | None:
        """Tiles from start to goal inclusive (BFS), or None if unreachable."""
        came_from: dict[Pos, Pos | None] = {start: None}
        queue = deque([start])
        while queue:
            cur = queue.popleft()
            if cur == goal:
                path = [cur]
                while came_from[path[-1]] is not None:
                    path.append(came_from[path[-1]])
                return path[::-1]
            for nxt in self.neighbours(cur):
                if nxt not in came_from:
                    came_from[nxt] = cur
                    queue.append(nxt)
        return None

    def distance(self, a: Pos, b: Pos) -> int | None:
        path = self.shortest_path(a, b)
        return None if path is None else len(path) - 1

    def signs_next_to(self, pos: Pos) -> list[Sign]:
        """Signs on walls orthogonally adjacent to pos."""
        found = []
        for dr, dc in DIRECTIONS.values():
            sign = self.signs.get((pos[0] + dr, pos[1] + dc))
            if sign is not None:
                found.append(sign)
        return found
