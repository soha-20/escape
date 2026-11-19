"""Game state and turn order. No input/output here."""

from enum import Enum

from .maze import DIRECTIONS, Maze, Pos

VIEW_RADIUS = 3

KEYS = {"w": "up", "s": "down", "a": "left", "d": "right"}


class Status(Enum):
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"
    QUIT = "quit"


class Outcome(Enum):
    """What a single command did."""
    MOVED = "moved"          # a turn was taken
    WALL = "wall"            # bumped a wall; no turn used
    INVALID = "invalid"      # unknown command; no turn used
    QUIT = "quit"
    GAME_OVER = "game_over"  # game already finished; nothing happens


class Game:
    def __init__(self, maze: Maze | None = None):
        self.maze = maze or Maze()
        self.player: Pos = self.maze.player_start
        self.reaper: Pos = self.maze.reaper_start
        self.turn = 0
        self.status = Status.PLAYING
        self.seen: set[Pos] = set()
        self._look()

    # --- commands -------------------------------------------------------
    def command(self, text: str) -> Outcome:
        """Handle one line of player input (w/a/s/d/q)."""
        key = text.replace("﻿", "").strip().lower()  # PowerShell pipes add a BOM
        if self.status is not Status.PLAYING:
            return Outcome.GAME_OVER
        if key == "q":
            self.status = Status.QUIT
            return Outcome.QUIT
        if key not in KEYS:
            return Outcome.INVALID
        return self.move(KEYS[key])

    def move(self, direction: str) -> Outcome:
        """Player moves one tile, then (unless they escaped) the reaper does."""
        if self.status is not Status.PLAYING:
            return Outcome.GAME_OVER
        dr, dc = DIRECTIONS[direction]
        target = (self.player[0] + dr, self.player[1] + dc)
        if self.maze.is_wall(target):
            return Outcome.WALL

        self.turn += 1
        self.player = target
        self._look()
        if self.player == self.reaper:          # walked into the reaper
            self.status = Status.LOST
        elif self.player == self.maze.exit:     # escaped before the reaper moves
            self.status = Status.WON
        else:
            self._reaper_step()
            if self.reaper == self.player:
                self.status = Status.LOST
        return Outcome.MOVED

    # --- queries --------------------------------------------------------
    def reaper_distance(self) -> int:
        """Steps the reaper needs to reach the player."""
        return self.maze.distance(self.reaper, self.player)

    def visible(self, pos: Pos) -> bool:
        return max(abs(pos[0] - self.player[0]), abs(pos[1] - self.player[1])) <= VIEW_RADIUS

    def signs_here(self):
        return self.maze.signs_next_to(self.player)

    # --- internals ------------------------------------------------------
    def _reaper_step(self) -> None:
        path = self.maze.shortest_path(self.reaper, self.player)
        if path and len(path) > 1:
            self.reaper = path[1]

    def _look(self) -> None:
        r0, c0 = self.player
        for r in range(r0 - VIEW_RADIUS, r0 + VIEW_RADIUS + 1):
            for c in range(c0 - VIEW_RADIUS, c0 + VIEW_RADIUS + 1):
                if 0 <= r < self.maze.height and 0 <= c < self.maze.width:
                    self.seen.add((r, c))
