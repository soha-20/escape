"""The fixed graveyard (R6), its hurdles and hazards (R7), low hurdles (R10), its signs (R2), and pathfinding.

The class keeps its round-1 name, Maze. Legend for LAYOUT:
    (space) grass        P  player start  R  reaper start  E  exit gate
    #  iron fence        +  gravestone    T  dead tree     !  signpost (text in SIGNS)
    O  open grave        *  thorn bush    (hazards: walkable, but they cost the player a life)
    =  fallen headstone  C  coffin        (low hurdles: block walking, but the player can jump them;
                                           the reaper glides over them)
"""

from collections import deque
from dataclasses import dataclass

Pos = tuple[int, int]  # (row, column)

LAYOUT = """\
###############################
#R   P   O   *   *    ++#     #
#       +   +   +   + T+# + + #
#  T                = +!#     #
#     +   +   +   +        +  #
#           *  O    O + #    +#
#  +    +*  +   +   + T #######
#            T        +      !#
############################ ##
#            O #!   O      C  #
#  +   +   +      +   +   +   #
#              #    *      = *#
################ T  +   +  C  #
# +  #! * +    #              #
#                 +   +   +   #
#  + #E  +  O  #!      *  O   #
###############################"""

OBSTACLES: dict[str, str] = {"#": "iron fence", "+": "gravestone", "T": "dead tree", "!": "signpost"}
HAZARDS: dict[str, str] = {"O": "open grave", "*": "thorn bush"}
LOW_HURDLES: dict[str, str] = {"=": "fallen headstone", "C": "coffin"}  # R10

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
    (3, 23): Sign("Wanna get stuck? →", WARNING, "right"),
    (7, 29): Sign("↓ The gate lies this way. Hurry.", GUIDE, "down"),
    (9, 16): Sign("← The family plot. Nobody leaves it.", WARNING, "left"),
    (15, 16): Sign("← Through the old yard. Mind the graves.", GUIDE, "left"),
    (13, 6): Sign("← The crypt yard. Nobody came back.", WARNING, "left"),
}


class Maze:
    def __init__(self, layout: str = LAYOUT, signs: dict[Pos, Sign] | None = None):
        rows = layout.splitlines()
        if not rows or any(len(r) != len(rows[0]) for r in rows):
            raise ValueError("maze layout must be a non-empty rectangle")
        self.height = len(rows)
        self.width = len(rows[0])
        self.layout = layout
        self.signs = dict(SIGNS if signs is None else signs)
        self._obstacles: dict[Pos, str] = {}
        self._hazards: dict[Pos, str] = {}
        self._low: dict[Pos, str] = {}
        marks: dict[str, Pos] = {}
        sign_marks: set[Pos] = set()
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                if ch in OBSTACLES:
                    self._obstacles[(r, c)] = OBSTACLES[ch]
                    if ch == "!":
                        sign_marks.add((r, c))
                elif ch in HAZARDS:
                    self._hazards[(r, c)] = HAZARDS[ch]
                elif ch in LOW_HURDLES:
                    self._low[(r, c)] = LOW_HURDLES[ch]
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

    def obstacle(self, pos: Pos) -> str | None:
        """The name of what blocks pos ("gravestone", "iron fence", ...), or None if it is walkable.

        Everything outside the grounds counts as the graveyard fence."""
        r, c = pos
        if not (0 <= r < self.height and 0 <= c < self.width):
            return OBSTACLES["#"]
        return self._obstacles.get(pos)

    def is_wall(self, pos: Pos) -> bool:
        """True if an obstacle blocks pos (the round-1 name: since R6 there are no walls, only objects)."""
        return self.obstacle(pos) is not None

    def hazard(self, pos: Pos) -> str | None:
        """R7: "open grave" or "thorn bush" if stepping on pos hurts the player, else None."""
        return self._hazards.get(pos)

    def low_hurdle(self, pos: Pos) -> str | None:
        """R10: "fallen headstone" or "coffin" if pos holds a low hurdle the player can jump, else None."""
        return self._low.get(pos)

    def neighbours(self, pos: Pos, avoid_hazards: bool = False) -> list[Pos]:
        """Tiles orthogonally adjacent to pos that can be entered, in DIRECTIONS order.

        By default this is the reaper's view: it glides over hazards and low hurdles.
        avoid_hazards=True is the player on foot: it leaves out hazards and low hurdles (R7, R10)."""
        result = []
        for dr, dc in DIRECTIONS.values():
            nxt = (pos[0] + dr, pos[1] + dc)
            if self.is_wall(nxt):
                continue
            if avoid_hazards and (nxt in self._hazards or nxt in self._low):
                continue
            result.append(nxt)
        return result

    def shortest_path(self, start: Pos, goal: Pos, avoid_hazards: bool = False) -> list[Pos] | None:
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
            for nxt in self.neighbours(cur, avoid_hazards):
                if nxt not in came_from:
                    came_from[nxt] = cur
                    queue.append(nxt)
        return None

    def distance(self, a: Pos, b: Pos) -> int | None:
        path = self.shortest_path(a, b)
        return None if path is None else len(path) - 1

    def signs_next_to(self, pos: Pos) -> list[Sign]:
        """Signposts orthogonally adjacent to pos."""
        found = []
        for dr, dc in DIRECTIONS.values():
            sign = self.signs.get((pos[0] + dr, pos[1] + dc))
            if sign is not None:
                found.append(sign)
        return found
