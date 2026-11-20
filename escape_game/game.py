"""Game state and turn order. No input/output here."""

from enum import Enum

from .maze import DIRECTIONS, Maze, Pos

MAX_LIVES = 3  # R4

KEYS = {"w": "up", "s": "down", "a": "left", "d": "right"}
JUMP_KEY = "j"  # R10: the --text version's jump (the window uses the Up arrow)


class Status(Enum):
    PLAYING = "playing"
    CAUGHT = "caught"   # lost a life (to the reaper or a hazard), waiting for R to resume (R4, R7)
    WON = "won"
    LOST = "lost"       # lost the last life
    QUIT = "quit"


class Outcome(Enum):
    """What a single command did."""
    MOVED = "moved"          # a turn was taken
    WALL = "wall"            # bumped an obstacle (gravestone, fence, low hurdle, ...); no turn used
    NO_JUMP = "no_jump"      # R10: nothing to jump over, or no safe landing; no turn used
    INVALID = "invalid"      # unknown command; no turn used
    QUIT = "quit"
    GAME_OVER = "game_over"  # game already finished; nothing happens
    PAUSED = "paused"        # caught and waiting for R; nothing happens
    RESUMED = "resumed"      # R after a catch: back to the start tiles


class Game:
    def __init__(self, maze: Maze | None = None, lives: int = MAX_LIVES):
        self.maze = maze or Maze()
        self.lives = lives
        self.player: Pos = self.maze.player_start
        self.reaper: Pos = self.maze.reaper_start
        self.turn = 0
        self.status = Status.PLAYING
        self.hurt_by: str | None = None   # R7: "reaper", "open grave" or "thorn bush" after a lost life
        self.bumped: str | None = None    # R6: the obstacle the last move ran into
        self.facing = "right"             # R10: the way the player last tried to move; jumps go this way
        self.jumped = False               # R10: the last turn was a jump
        self.jump_blocked: str | None = None  # R10: why the last jump failed: "nothing" or what is in the way

    # --- commands -------------------------------------------------------
    def command(self, text: str) -> Outcome:
        """Handle one line of player input (w/a/s/d to move, j to jump, r to resume, q to quit)."""
        key = text.replace("﻿", "").strip().lower()  # PowerShell pipes add a BOM
        if self.status not in (Status.PLAYING, Status.CAUGHT):
            return Outcome.GAME_OVER
        if key == "q":
            self.status = Status.QUIT
            return Outcome.QUIT
        if key == "r":
            return self.resume()
        if self.status is Status.CAUGHT:
            return Outcome.PAUSED
        if key == JUMP_KEY:
            return self.jump()
        if key not in KEYS:
            return Outcome.INVALID
        return self.move(KEYS[key])

    def move(self, direction: str) -> Outcome:
        """Player moves one tile, then (unless they escaped or got hurt) the reaper does."""
        if self.status is Status.CAUGHT:
            return Outcome.PAUSED
        if self.status is not Status.PLAYING:
            return Outcome.GAME_OVER
        self.facing = direction
        dr, dc = DIRECTIONS[direction]
        target = (self.player[0] + dr, self.player[1] + dc)
        self.bumped = self.maze.obstacle(target) or self.maze.low_hurdle(target)
        if self.bumped is not None:
            return Outcome.WALL
        return self._take_turn(target, jumped=False)

    def jump(self) -> Outcome:
        """R10: leap over the low hurdle or hazard in front of the player, landing two tiles on (one turn)."""
        if self.status is Status.CAUGHT:
            return Outcome.PAUSED
        if self.status is not Status.PLAYING:
            return Outcome.GAME_OVER
        maze = self.maze
        dr, dc = DIRECTIONS[self.facing]
        over = (self.player[0] + dr, self.player[1] + dc)
        land = (self.player[0] + 2 * dr, self.player[1] + 2 * dc)
        if maze.low_hurdle(over) is None and maze.hazard(over) is None:
            self.jump_blocked = "nothing"
            return Outcome.NO_JUMP
        self.jump_blocked = maze.obstacle(land) or maze.low_hurdle(land) or maze.hazard(land)
        if self.jump_blocked is not None:
            return Outcome.NO_JUMP
        if over == self.reaper:                 # nobody leaps over Death
            return self._take_turn(over, jumped=True)
        return self._take_turn(land, jumped=True)

    def _take_turn(self, target: Pos, jumped: bool) -> Outcome:
        """The player arrives on target; then the R1 turn order follows."""
        self.turn += 1
        self.player = target
        self.jumped = jumped
        self.jump_blocked = None
        if self.player == self.reaper:          # walked (or leapt) into the reaper
            self._lose_life("reaper")
        elif self.player == self.maze.exit:     # escaped before the reaper moves
            self.status = Status.WON
        elif self.maze.hazard(self.player):     # R7: fell into an open grave / thorns
            self._lose_life(self.maze.hazard(self.player))
        else:
            self._reaper_step()
            if self.reaper == self.player:
                self._lose_life("reaper")
        return Outcome.MOVED

    def resume(self) -> Outcome:
        """After a lost life (catch or hazard): both go back to their start tiles and the chase goes on."""
        if self.status is not Status.CAUGHT:
            return Outcome.INVALID if self.status is Status.PLAYING else Outcome.GAME_OVER
        self.player = self.maze.player_start
        self.reaper = self.maze.reaper_start
        self.status = Status.PLAYING
        self.hurt_by = None
        return Outcome.RESUMED

    # --- queries --------------------------------------------------------
    def reaper_distance(self) -> int:
        """Steps the reaper needs to reach the player."""
        return self.maze.distance(self.reaper, self.player)

    def signs_here(self):
        return self.maze.signs_next_to(self.player)

    # --- internals ------------------------------------------------------
    def _lose_life(self, cause: str) -> None:
        self.hurt_by = cause
        self.lives -= 1
        self.status = Status.CAUGHT if self.lives > 0 else Status.LOST

    def _reaper_step(self) -> None:
        path = self.maze.shortest_path(self.reaper, self.player)
        if path and len(path) > 1:
            self.reaper = path[1]

