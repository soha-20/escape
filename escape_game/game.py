"""Game state, turn order and (since round 5) the real-time chase. No input/output here.

Two ways to play:
* Turn-based (the --text game, and Game() by default): each move() or jump() is a turn, then the
  Reaper takes one step.
* Real time (the game window, Game(realtime=True)), R13/R15: the window says which keys are held
  (press/release/press_jump) and how much time has passed (update(ms)). The player runs a tile every
  PLAYER_STEP_MS while a key is held; the Reaper steps every REAPER_STEP_MS on its own clock.
  Time is a number the caller advances, so tests can run a whole chase in milliseconds.
"""

from enum import Enum

from .maze import DIRECTIONS, Maze, Pos

MAX_LIVES = 3  # R4

KEYS = {"w": "up", "s": "down", "a": "left", "d": "right"}
JUMP_KEY = "j"  # R10: the --text version's jump (the window uses the Up arrow)

# R13/R15: the pace of the real-time chase, in milliseconds
PLAYER_STEP_MS = 180   # one tile while a key is held
JUMP_MS = 270          # a jump: two tiles, faster than running
REAPER_STEP_MS = 220   # the Reaper at its normal pace: slower than a runner (R16 tuned it for the key detour)
JUMP_BUFFER_MS = 300   # R10/R15: an Up pressed this early is remembered
# R17: the Reaper surges when the player stops or dawdles, and calms down once they run on
REAPER_SURGE_MS = 180     # surging, it is as fast as a running player
SURGE_AFTER_IDLE_MS = 250  # standing still (or bumping) this long sets it off
CALM_AFTER_RUN_MS = 1000   # running without a break this long calms it again

NEVER = float("-inf")


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
    def __init__(self, maze: Maze | None = None, lives: int = MAX_LIVES, realtime: bool = False):
        self.maze = maze or Maze()
        self.lives = lives
        self.realtime = realtime          # R13: the window's real-time chase
        self.player: Pos = self.maze.player_start
        self.reaper: Pos = self.maze.reaper_start
        self.turn = 0
        self.status = Status.PLAYING
        self.hurt_by: str | None = None   # R7: "reaper", "open grave" or "thorn bush" after a lost life
        self.bumped: str | None = None    # R6: the obstacle the last move ran into
        self.facing = "right"             # R10: the way the player last tried to move; jumps go this way
        self.jumped = False               # R10: the last turn was a jump
        self.jump_blocked: str | None = None  # R10: why the last jump failed: "nothing" or what is in the way
        # --- real time (R13, R15) ---
        self.clock = 0.0                  # ms; advanced by update()
        self.run_ms = 0.0                 # time spent running (from the first step), shown in the window
        self.held: list[str] = []         # movement keys held down, oldest first
        self.events: list[Outcome] = []   # what each real-time action did, for the window's messages
        self._jump_until: float | None = None  # R10: a remembered Up, until this time
        self._ready_at = 0.0              # the player can act again from this time
        self._stalled = False             # bumped into something: wait for a new key
        self._reaper_next: float | None = None  # the Reaper's next step; None until the player's first step
        self.has_key = False              # R16: picked up the gate key
        self.surging = False              # R17: the Reaper is in a fury: as fast as a runner
        self._running_since: float | None = None  # R17: when the player's current unbroken run began
        self._reset_motion()

    # --- turn-based commands (--text) ---------------------------------------------------
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
        """Player moves one tile, then (unless they escaped or got hurt) the reaper does (turn-based)."""
        if self.status is Status.CAUGHT:
            return Outcome.PAUSED
        if self.status is not Status.PLAYING:
            return Outcome.GAME_OVER
        return self._walk(direction)

    def jump(self) -> Outcome:
        """R10: leap over the low hurdle or hazard in front of the player, landing two tiles on (one turn)."""
        if self.status is Status.CAUGHT:
            return Outcome.PAUSED
        if self.status is not Status.PLAYING:
            return Outcome.GAME_OVER
        return self._leap()

    def resume(self) -> Outcome:
        """After a lost life (catch or hazard): both go back to their start tiles and the chase goes on."""
        if self.status is not Status.CAUGHT:
            return Outcome.INVALID if self.status is Status.PLAYING else Outcome.GAME_OVER
        self.player = self.maze.player_start
        self.reaper = self.maze.reaper_start
        self.status = Status.PLAYING
        self.hurt_by = None
        # R13: in real time the Reaper waits for the player's first step again; held keys are forgotten
        self.held = []
        self._jump_until = None
        self._stalled = False
        self._ready_at = self.clock
        self._reaper_next = None
        self.surging = False
        self._running_since = None
        self._reset_motion()
        return Outcome.RESUMED  # R16: the key, once found, is kept

    # --- real-time commands (the window), R13/R15 -------------------------------------------
    def press(self, direction: str) -> None:
        """R15: a movement key went down. The newest held key leads; the player moves at once if ready."""
        if direction in self.held:
            self.held.remove(direction)
        self.held.append(direction)
        self._stalled = False
        self.update(0)

    def release(self, direction: str) -> None:
        """R15: a movement key came up: the player finishes the step under way, then stops (or follows
        another key still held)."""
        if direction in self.held:
            self.held.remove(direction)

    def press_jump(self) -> None:
        """R10/R15: Up went down: jump now if possible, otherwise remember it for JUMP_BUFFER_MS."""
        self._jump_until = self.clock + JUMP_BUFFER_MS
        self._stalled = False
        self.update(0)

    def update(self, ms: float) -> None:
        """R13: let ms milliseconds pass. Player actions and Reaper steps happen in time order."""
        end = self.clock + ms
        while self.realtime and self.status is Status.PLAYING:
            player_at = self._player_due()
            reaper_at = self._reaper_next if self._reaper_next is not None else float("inf")
            due = min(player_at, reaper_at)
            if due > end:
                break
            self._advance_to(max(self.clock, due))
            if player_at <= reaper_at:
                self._player_act()
            else:
                self._reaper_act()
        self._advance_to(end)

    # --- queries --------------------------------------------------------
    def reaper_distance(self) -> int:
        """Steps the reaper needs to reach the player."""
        return self.maze.distance(self.reaper, self.player)

    def signs_here(self):
        return self.maze.signs_next_to(self.player)

    @property
    def gate_locked(self) -> bool:
        """R16: the exit gate stays locked until the player has the key (if the graveyard has one)."""
        return self.maze.key is not None and not self.has_key

    def route_out(self) -> list[Pos] | None:
        """R16: the player's shortest way out from where they stand (by way of the key if still needed)."""
        return self.maze.escape_route(self.player, has_key=not self.gate_locked)

    # --- internals ------------------------------------------------------
    def _walk(self, direction: str) -> Outcome:
        self.facing = direction
        dr, dc = DIRECTIONS[direction]
        target = (self.player[0] + dr, self.player[1] + dc)
        self.bumped = self._blocker(target)
        if self.bumped is not None:
            return Outcome.WALL
        return self._take_turn(target, jumped=False)

    def _blocker(self, pos: Pos) -> str | None:
        """What stops the player walking onto pos: an obstacle, a low hurdle, or (R16) the locked gate."""
        if pos == self.maze.exit and self.gate_locked:
            return "locked gate"
        return self.maze.obstacle(pos) or self.maze.low_hurdle(pos)

    def _leap(self) -> Outcome:
        maze = self.maze
        dr, dc = DIRECTIONS[self.facing]
        over = (self.player[0] + dr, self.player[1] + dc)
        land = (self.player[0] + 2 * dr, self.player[1] + 2 * dc)
        if maze.low_hurdle(over) is None and maze.hazard(over) is None:
            self.jump_blocked = "nothing"
            return Outcome.NO_JUMP
        self.jump_blocked = self._blocker(land) or maze.hazard(land)
        if self.jump_blocked is not None:
            return Outcome.NO_JUMP
        if over == self.reaper:                 # nobody leaps over Death
            return self._take_turn(over, jumped=True)
        return self._take_turn(land, jumped=True)

    def _take_turn(self, target: Pos, jumped: bool) -> Outcome:
        """The player arrives on target; then the R1 checks (and, turn-based, the reaper's step) follow."""
        self.turn += 1
        self.player_from, self.player = self.player, target
        self.player_moved_at = self.clock
        self.player_move_ms = JUMP_MS if jumped else PLAYER_STEP_MS
        self.jumped = jumped
        self.jump_blocked = None
        self.bumped = None
        if self.realtime:
            if self._running_since is None or self.clock > self._ready_at:  # R17: a new run begins
                self._running_since = self.clock
            self._ready_at = self.clock + self.player_move_ms
            if self._reaper_next is None:       # R13: the first step sets the Reaper off
                self._reaper_next = self.clock + REAPER_STEP_MS
        if self.player == self.maze.key:        # R16: the key is picked up by walking (or leaping) onto it
            self.has_key = True
        if self.player == self.reaper:          # walked (or leapt) into the reaper
            self._lose_life("reaper")
        elif self.player == self.maze.exit:     # escaped before the reaper moves
            self.status = Status.WON
        elif self.maze.hazard(self.player):     # R7: fell into an open grave / thorns
            self._lose_life(self.maze.hazard(self.player))
        elif not self.realtime:
            self._reaper_step()
            if self.reaper == self.player:
                self._lose_life("reaper")
        return Outcome.MOVED

    def _player_due(self) -> float:
        """When the player next acts in real time: as soon as they are ready, if a key asks for it."""
        wants_jump = self._jump_until is not None
        wants_run = bool(self.held) and not self._stalled
        return self._ready_at if wants_jump or wants_run else float("inf")

    def _player_act(self) -> None:
        """R15: one real-time action: a remembered jump if it can be made, else a step along the newest
        held key whose way is open (cornering), else a bump that stops the run."""
        if self._jump_until is not None and self.clock > self._jump_until:
            self._jump_until = None             # R10: remembered too long ago
        if self._jump_until is not None:
            outcome = self._leap()
            if outcome is Outcome.MOVED:
                self._jump_until = None
                self.events.append(outcome)
                return
            if not self.held or self._stalled:  # nothing else to do: say why, and forget it
                self._jump_until = None
                self.events.append(outcome)
                return
        if not self.held:  # a remembered jump ran out and no key is held: nothing to do
            return
        for direction in reversed(self.held):
            dr, dc = DIRECTIONS[direction]
            target = (self.player[0] + dr, self.player[1] + dc)
            if self._blocker(target) is None:
                self.events.append(self._walk(direction))
                return
        self.events.append(self._walk(self.held[-1]))  # every way is blocked: bump the newest
        self._stalled = True

    def _reaper_act(self) -> None:
        """R13: the Reaper's own clock ticks: one step toward the player, at its normal pace or (R17)
        surging."""
        self._update_surge()
        pace = REAPER_SURGE_MS if self.surging else REAPER_STEP_MS
        self.reaper_from = self.reaper
        self.reaper_moved_at = self.clock
        self.reaper_move_ms = pace
        self._reaper_step()
        self._reaper_next += pace
        if self.reaper == self.player:
            self._lose_life("reaper")

    def _update_surge(self) -> None:
        """R17: a player who has stood still (or bumped about) for SURGE_AFTER_IDLE_MS sets the Reaper
        surging; one who has then run without a break for CALM_AFTER_RUN_MS calms it."""
        idle_ms = self.clock - self._ready_at  # how long the player has been standing, if positive
        if idle_ms >= SURGE_AFTER_IDLE_MS:
            self.surging = True
        if idle_ms > 0:
            self._running_since = None
        elif self.surging and self._running_since is not None \
                and self.clock - self._running_since >= CALM_AFTER_RUN_MS:
            self.surging = False

    def _advance_to(self, time: float) -> None:
        if self.status is Status.PLAYING and self._reaper_next is not None:
            self.run_ms += time - self.clock
        self.clock = time

    def _reset_motion(self) -> None:
        """Nobody is under way: both figures stand on their tiles (R8: the window draws them there)."""
        self.player_from, self.player_moved_at, self.player_move_ms = self.player, NEVER, PLAYER_STEP_MS
        self.reaper_from, self.reaper_moved_at, self.reaper_move_ms = self.reaper, NEVER, REAPER_STEP_MS

    def _lose_life(self, cause: str) -> None:
        self.hurt_by = cause
        self.lives -= 1
        self.status = Status.CAUGHT if self.lives > 0 else Status.LOST

    def _reaper_step(self) -> None:
        path = self.maze.shortest_path(self.reaper, self.player)
        if path and len(path) > 1:
            self.reaper = path[1]
