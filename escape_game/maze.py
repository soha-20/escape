"""The fixed graveyard (R6, R12), its hurdles and hazards (R7), low hurdles (R10), its signs (R2), and pathfinding.

Since round 5 (R12) a gravel path winds in four lanes between neat rows of graves, from the start to
the gate in the south fence; the hurdles lie on the path and must be jumped.

The class keeps its round-1 name, Maze. Legend for LAYOUT:
    .  gravel path       (space) grass   P  player start  R  reaper start  E  exit gate
    #  iron fence        +  gravestone    T  dead tree     !  signpost (text in SIGNS)
    K  the gate key (R16: the exit is locked until the player has it; drawn as path)
    O  open grave        *  thorn bush    (hazards: walkable, but they cost the player a life)
    =  fallen headstone  C  coffin        (low hurdles: block walking, but the player can jump them;
                                           the reaper glides over them)
"""

from collections import deque
from dataclasses import dataclass

Pos = tuple[int, int]  # (row, column)

LAYOUT = """\
#############################
#R...P...O....C....*...=...T#
#+++T+++++T+++++T+++++T++!.+#
#+++++++++++++++O*        .!#
#+++T+++++T+++++T+++++T+++.+#
#T.....*....O....C....*....T#
#+.+T+++++T+++++T+++++T+++++#
#!...K++++++++++++++++++++++#
#+.+T+++++T+++++T+++++T+++++#
#T....O....=....*....O.....T#
#+++T+++++T+++++T+++++T!.+.+#
#+++++++++++++!!++++++++*+.+#
#O *          ....O...C....T#
##############E##############"""

PATH = "."  # R12: the gravel path (walkable, like grass)
KEY = "K"   # R16: the gate key; the exit stays locked until the player has picked it up

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
    (2, 25): Sign("→ Round the bend and down. Hurry.", GUIDE, "right"),
    (3, 27): Sign("Wanna get stuck? ←", WARNING, "left"),
    (7, 1): Sign("The gate key is buried here. →", GUIDE, "right"),  # R16: the key yard
    (10, 23): Sign("→ A short way down. Mind the thorns!", GUIDE, "right"),  # R16: the shortcut
    (11, 14): Sign("← The crypt yard. Nobody came back.", WARNING, "left"),
    (11, 15): Sign("← The gate is right here! RUN!", GUIDE, "left"),
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
        self._path: set[Pos] = set()
        self.key: Pos | None = None  # R16: where the gate key lies; None: the gate is open from the start
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
                elif ch == PATH:
                    self._path.add((r, c))
                elif ch == KEY:  # R16: the gate key, lying on the path
                    if self.key is not None:
                        raise ValueError("more than one key in maze layout")
                    self.key = (r, c)
                    self._path.add((r, c))
                elif ch in "PRE":
                    self._path.add((r, c))  # the start tiles and the gate are drawn as path
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

    def on_path(self, pos: Pos) -> bool:
        """R12: True if pos is part of the gravel path (the start tiles and the exit count too)."""
        return pos in self._path

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

    def player_moves(self, pos: Pos) -> list[tuple[Pos, bool]]:
        """R10/R12: where the player can get to in one move, as (tile, jumped), in DIRECTIONS order.

        A step onto safe ground, or a jump over a low hurdle or hazard onto safe ground two tiles on."""
        moves = []
        for dr, dc in DIRECTIONS.values():
            over = (pos[0] + dr, pos[1] + dc)
            land = (pos[0] + 2 * dr, pos[1] + 2 * dc)
            if self._safe(over):
                moves.append((over, False))
            elif (over in self._low or over in self._hazards) and self._safe(land):
                moves.append((land, True))
        return moves

    def player_route(self, start: Pos, goal: Pos) -> list[Pos] | None:
        """R12: a shortest way for the player (fewest moves), walking and jumping, never landing on a hazard.

        Tiles from start to goal inclusive; consecutive tiles are 1 apart (a step) or 2 apart (a jump)."""
        came_from: dict[Pos, Pos | None] = {start: None}
        queue = deque([start])
        while queue:
            cur = queue.popleft()
            if cur == goal:
                path = [cur]
                while came_from[path[-1]] is not None:
                    path.append(came_from[path[-1]])
                return path[::-1]
            for nxt, _ in self.player_moves(cur):
                if nxt not in came_from:
                    came_from[nxt] = cur
                    queue.append(nxt)
        return None

    def escape_route(self, start: Pos, has_key: bool = False) -> list[Pos] | None:
        """R16: the player's shortest way out from start: by way of the key first, unless they have it
        (or the graveyard has no key). Tiles inclusive, as player_route."""
        if self.key is None or has_key:
            return self.player_route(start, self.exit)
        to_key = self.player_route(start, self.key)
        on = self.player_route(self.key, self.exit)
        return None if to_key is None or on is None else to_key + on[1:]

    def _safe(self, pos: Pos) -> bool:
        """Ground the player can stand on: no obstacle, hazard or low hurdle."""
        return not self.is_wall(pos) and pos not in self._hazards and pos not in self._low

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
