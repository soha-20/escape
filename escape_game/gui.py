"""Graphical game window (tkinter): animated figures, a moonlit graveyard, glowing signs.

Tk on Windows ignores the canvas `stipple` option, so nothing here relies on transparency:
glows are rings, mist is drawn as thin wisps, and the torch light is a warm tint on the tiles.

The rules all live in game.py; this module only draws the game and turns key presses into moves.
The game is turn-based, but each turn is shown as a short slide (R8): the background is built
once per turn and scrolled, while the figures, mist and glows are redrawn every frame.
"""

import math
import queue
import threading
import time
import tkinter as tk
from dataclasses import dataclass

from .game import MAX_LIVES, Game, Outcome, Status
from .maze import WARNING
from .render import GAME_OVER, LIFE_LOST, bump_line, jump_line, reaper_line
from .sound import Sound

TILE = 52            # pixels per maze tile
VIEW_COLS, VIEW_ROWS = 15, 9   # the camera shows this many tiles, centred on the player
SCALE = TILE / 40    # figures are designed on a 40-pixel tile
HUD_HEIGHT = 150
TICK_MS = 40         # one animation frame
SLIDE_FRAMES = 5     # R8: a step slides over 5 frames (0.2 s)
JUMP_FRAMES = 7      # R10: a jump takes a little longer
JUMP_LIFT = 24       # R10: how high the player rises, in design pixels (0.6 tile)
HEART_SIZES = (30, 25)   # HUD heart font size: beat, rest
HEART_GAP = 40           # pixels between HUD hearts

KEY_DIRECTIONS = {  # R10: the Up arrow jumps; W still moves north
    "w": "up", "W": "up",
    "Down": "down", "s": "down", "S": "down",
    "Left": "left", "a": "left", "A": "left",
    "Right": "right", "d": "right", "D": "right",
}
JUMP_KEYS = {"Up"}  # R10
CONTROLS = "W A S D / ← ↓ →  move     ↑  jump     Esc  quit"

# palette
BLACK = "#000000"
GRASS = "#4f7a3c"        # R6: the graveyard lawn
GRASS_DARK = "#2f4a25"
GRASS_BLADE = "#7fae5a"
DIRT = "#6b4f33"
DIRT_DARK = "#3e2c1c"
PIT = "#050304"
STONE = "#a7adb6"        # gravestones
STONE_DARK = "#555b66"
STONE_LIGHT = "#d3d8de"
MOSS = "#4d6b3a"
IRON = "#1a1a20"         # fences and the gate
BARK = "#5a4030"         # dead trees and signposts
BARK_DARK = "#33241a"
THORN = "#c23a4a"        # R7: thorn bushes, bright enough to stand out on the grass
THORN_TIP = "#ffb3b3"
PLANK = "#e0cf9f"
RED = "#ff3b3b"
BLOOD = "#8a0f1c"
GREEN = "#3ddc84"
DOOR = "#7a4a26"
COFFIN = "#6e4a2c"       # R10: low hurdles
COFFIN_DARK = "#3a2616"
HUD_BG = "#0d0b12"
HUD_EDGE = "#3b2a4d"
GREY = "#9a9aa8"
ORANGE = "#ff9f43"
HEART_LOST = "#5c5668"   # R5: grey empty heart for a lost life
MOON_TINT = "#9ab4e0"    # R9: the cool colour of moonlight
TORCH_TINT = "#ffae5c"   # R9: the warm colour of the torch
MIST = "#c9d3e6"         # R11
CLOAK = "#0c0910"        # R11: the reaper
CLOAK_EDGE = "#3d2a4a"
BONE = "#ddd5c0"
BLADE = "#c9d3da"

FONT = "Segoe UI"
TITLE_FONT = "Impact"  # Tk falls back to a default font if it is missing


# --- pure helpers (tested without a window) --------------------------------

def shade(colour: str, factor: float) -> str:
    """Darken a #rrggbb colour by factor (0 = black, 1 = unchanged)."""
    factor = max(0.0, min(1.0, factor))
    r, g, b = (int(colour[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % (int(r * factor), int(g * factor), int(b * factor))


def mix(a: str, b: str, t: float) -> str:
    """Blend colour a toward colour b by t (0 = a, 1 = b)."""
    t = max(0.0, min(1.0, t))
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(ca, cb))


MOONLIGHT = 0.8     # R9: every tile in view is at least this bright
TORCH_REACH = 3.5   # tiles; the torch glow fades to nothing at this distance


def torch_glow(centre, pos) -> float:
    """R9: how strongly the torch warms a tile: 1 under the player, fading to 0 at TORCH_REACH."""
    dist = math.hypot(pos[0] - centre[0], pos[1] - centre[1])
    return max(0.0, 1.0 - dist / TORCH_REACH)


def light_level(game: Game, pos) -> float:
    """R9: moonlight everywhere, a little brighter near the torch. Never dark."""
    return MOONLIGHT + (1 - MOONLIGHT) * torch_glow(game.player, pos)


def lit(colour: str, light: float, warmth: float) -> str:
    """R9: a colour as seen at night: dimmed by light, tinted cool by the moon and warm by the torch."""
    moonlit = mix(shade(colour, light), MOON_TINT, 0.12 * (1 - warmth))
    return mix(moonlit, TORCH_TINT, 0.22 * warmth)


def heartbeat_period_ms(distance: int) -> int:
    """The on-screen heart (and the reaper's aura) beat faster as the reaper closes in."""
    if distance >= 6:
        return 1200
    if distance > 3:
        return 800
    return 450


def camera_at(maze, pos) -> tuple[float, float]:
    """Top-left tile of a camera centred on pos (may be fractional while sliding), kept inside the maze."""
    top = min(max(pos[0] - VIEW_ROWS // 2, 0), max(maze.height - VIEW_ROWS, 0))
    left = min(max(pos[1] - VIEW_COLS // 2, 0), max(maze.width - VIEW_COLS, 0))
    return top, left


def camera_origin(game: Game) -> tuple[int, int]:
    """Top-left tile of the camera view: centred on the player, kept inside the maze."""
    return camera_at(game.maze, game.player)


def in_view(origin, pos) -> bool:
    """True if pos lies (at least partly) inside the camera view whose top-left tile is origin."""
    return (origin[0] - 1 < pos[0] < origin[0] + VIEW_ROWS
            and origin[1] - 1 < pos[1] < origin[1] + VIEW_COLS)


def danger_colour(distance: int) -> str:
    if distance >= 6:
        return GREY
    if distance > 3:
        return ORANGE
    return RED


def ease(t: float) -> float:
    """R8: smooth start and stop for a slide (0 -> 0, 1 -> 1)."""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def tween(a, b, t: float) -> tuple[float, float]:
    """R8: the point a fraction t of the way from tile a to tile b."""
    return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t


def walk_pose(t: float) -> float:
    """R8: leg and arm swing (-1 .. 1) at fraction t of a step: one full stride per tile."""
    return math.sin(2 * math.pi * t)


def jump_height(t: float) -> float:
    """R10: how high the player is (design pixels) at fraction t of a jump."""
    return JUMP_LIFT * math.sin(math.pi * max(0.0, min(1.0, t)))


def hover(ms: float) -> float:
    """R11: the reaper floats up and down (design pixels)."""
    return 2.5 * math.sin(ms / 380.0)


def _tags(tag) -> tuple:
    return (tag,) if isinstance(tag, str) else tuple(tag)


def _rotate(points, centre, angle):
    cx, cy = centre
    ca, sa = math.cos(angle), math.sin(angle)
    out = []
    for x, y in points:
        dx, dy = x - cx, y - cy
        out.append((cx + dx * ca - dy * sa, cy + dx * sa + dy * ca))
    return out


# --- figures ---------------------------------------------------------------

def draw_player(cv: tk.Canvas, cx: float, cy: float, s: float = 1.0, tag="player",
                swing: float = 0.0, face: int = 1, lift: float = 0.0) -> None:
    """A young adventurer in a blue tunic and a red cape, holding a burning torch.

    R8: swing (-1 .. 1) moves the legs and arms in a walk cycle, face (1 right, -1 left) mirrors
    the figure, lift raises it off the ground (R10 jump)."""
    tags = _tags(tag)

    def p(dx, dy):
        return cx + dx * s * face, cy + (dy - lift) * s

    w = max(1, round(3 * s))
    skin, skin_edge = "#f5cba7", "#a0522d"
    # cape behind the body, flaring as they run
    cv.create_polygon(*p(-5, -6), *p(-12 - 3 * abs(swing), 9), *p(-2, 10), fill="#8e1f2f", outline="#5a1320",
                      tags=tags)
    # legs: the front and back leg swing in opposite directions
    for side, k, colour in ((-1, -swing, "#1d2a36"), (1, swing, "#2c3e50")):
        foot = side * 2.5 + k * 6
        knee = side * 2.5 + k * 3.5
        cv.create_line(*p(side * 3, 8), *p(knee, 12.5 - abs(k)), *p(foot, 16.5), fill=colour, width=w,
                       capstyle="round", joinstyle="round", tags=tags + ("player_leg",))
        cv.create_oval(*p(foot - 2.5, 15), *p(foot + 3.5, 18.5), fill="#3b2614", outline="", tags=tags)
    # back arm swings against the front leg
    cv.create_line(*p(-6, -3), *p(-8 - swing * 4, 5), fill=shade(skin, 0.8), width=w, capstyle="round",
                   tags=tags + ("player_arm",))
    # tunic with a shaded side, belt and buckle
    cv.create_polygon(*p(-7, -5), *p(7, -5), *p(9, 10), *p(-9, 10), fill="#2e86de", outline="#1b4f8a",
                      width=max(1, s), tags=tags)
    cv.create_polygon(*p(-7, -5), *p(-2, -5), *p(-3, 10), *p(-9, 10), fill="#2468b0", outline="", tags=tags)
    cv.create_line(*p(-8, 6), *p(8, 6), fill="#8b5a2b", width=w, tags=tags)
    cv.create_rectangle(*p(1, 4.5), *p(4, 7.5), fill="#e8c547", outline="", tags=tags)
    # head: hair, wide frightened eyes looking ahead
    cv.create_oval(*p(-6, -17), *p(6, -5), fill=skin, outline=skin_edge, width=max(1, s), tags=tags)
    cv.create_arc(*p(-6.5, -18.5), *p(6.5, -7), start=10, extent=190, fill="#5d3a1a", outline="", tags=tags)
    for ex in (0.5, 3.5):
        cv.create_oval(*p(ex - 1.2, -13), *p(ex + 1.2, -10.2), fill="white", outline="", tags=tags)
        cv.create_oval(*p(ex - 0.2, -12.2), *p(ex + 1.0, -10.8), fill=BLACK, outline="", tags=tags)
    cv.create_oval(*p(1.5, -8.6), *p(3.2, -7), fill="#7a2e2e", outline="", tags=tags)  # a gasping mouth
    # torch arm, stick and flame (in front)
    cv.create_line(*p(6, -3), *p(12, -6 + swing * 1.5), fill=skin, width=w, capstyle="round",
                   tags=tags + ("player_arm",))
    cv.create_line(*p(12, -4 + swing * 1.5), *p(14, -15 + swing * 1.5), fill="#6d4c2f", width=w, tags=tags)
    fy = swing * 1.5
    cv.create_oval(*p(9.5, -25 + fy), *p(19.5, -12 + fy), fill="#ff7b00", outline="", tags=tags + ("flame",))
    cv.create_oval(*p(12, -21 + fy), *p(17, -13 + fy), fill="#ffe066", outline="", tags=tags + ("flame_core",))


def draw_reaper(cv: tk.Canvas, cx: float, cy: float, s: float = 1.0, tag="reaper",
                t: float = 0.0, lean: float = 0.0) -> None:
    """R11: the Grim Reaper, about 1.6 tiles tall: a floating, tattered black cloak, a skull deep in its hood
    with glowing red eyes, bony fingers and a long scythe. t (ms) drives the hover and the fluttering
    hem; lean (-1 .. 1) tilts the cloak into the direction it glides (R8)."""
    tags = _tags(tag)
    up = hover(t)

    def p(dx, dy):
        k = (18 - dy) / 64.0          # the top of the cloak leans more than the hem
        return cx + (dx + lean * 7 * k) * s, cy + (dy + up) * s

    def flat(points):
        return [v for xy in points for v in xy]

    # ground shadow: it stays on the ground while the reaper hovers
    cv.create_oval(cx - 14 * s, cy + 15 * s, cx + 14 * s, cy + 21 * s, fill="#050208", outline="",
                   tags=tags)
    # wisps of black smoke trailing from the hem
    for i in range(5):
        wx = -14 + i * 7 + 2 * math.sin(t / 260.0 + i)
        wy = 15 + 3 * math.sin(t / 330.0 + i * 1.7)
        cv.create_oval(*p(wx - 4, wy - 3), *p(wx + 4, wy + 3), fill="#1c1424", outline="",
                       tags=tags)
    # the scythe: a long shaft and a curved, gleaming blade; it sways in the bony hand
    hand = p(12, -6)
    shaft = [p(15, -42), p(9, 17)]
    blade = [p(15, -42), p(6, -49), p(-10, -49), p(-26, -40), p(-11, -43), p(4, -41)]
    edge = [p(-24, -40), p(-10, -46.5), p(5, -46.5)]
    angle = 0.07 * math.sin(t / 520.0) + 0.12 * lean
    shaft, blade, edge = (_rotate(pts, hand, angle) for pts in (shaft, blade, edge))
    cv.create_line(*flat(shaft), fill="#3e2a1c", width=max(1, round(3 * s)), tags=tags + ("scythe",))
    cv.create_polygon(*flat(blade), fill=BLADE, outline="#5d6b75", width=max(1, s), smooth=True,
                      tags=tags + ("scythe",))
    cv.create_line(*flat(edge), fill="white", width=max(1, s * 0.8), smooth=True, tags=tags + ("scythe",))
    # the cloak: broad shoulders, a ragged hem that flutters
    hem = []
    for i in range(10):
        x = 16 - i * 32 / 9
        y = 13 + (6 if i % 2 == 0 else 0) + 2 * math.sin(t / 180.0 + i * 1.3)
        hem.append(p(x, y))
    cloak = [p(0, -40), p(12, -27), p(16, -8)] + hem + [p(-16, -8), p(-12, -27)]
    cv.create_polygon(*flat(cloak), fill=CLOAK, outline=CLOAK_EDGE, width=max(1, s), tags=tags)
    for fx in (-7, -1, 6):  # folds
        cv.create_line(*p(fx * 0.5, -14), *p(fx, 14), fill="#231a2b", width=max(1, s), tags=tags)
    # hood around a hollow, black opening
    hood = [p(0, -44), p(10, -36), p(11, -24), p(7, -18), p(-7, -18), p(-11, -24), p(-10, -36)]
    cv.create_polygon(*flat(hood), fill="#15101b", outline="#4a3560", width=max(1, s), smooth=True, tags=tags)
    cv.create_oval(*p(-7, -36), *p(7, -19), fill=BLACK, outline="", tags=tags)
    # the skull, sunk deep in the hood
    cv.create_oval(*p(-5, -33), *p(5, -22), fill=BONE, outline="#8d8573", tags=tags)
    cv.create_rectangle(*p(-3, -24), *p(3, -20.5), fill=BONE, outline="#8d8573", tags=tags)  # jaw
    for tx in (-1.5, 0, 1.5):
        cv.create_line(*p(tx, -24), *p(tx, -20.5), fill="#5a5448", tags=tags)
    cv.create_polygon(*p(0, -27), *p(-1, -25), *p(1, -25), fill="#2a2620", outline="", tags=tags)  # nose
    for ex in (-2.2, 2.2):
        cv.create_oval(*p(ex - 2.1, -31.4), *p(ex + 2.1, -26.8), fill=BLACK, outline="", tags=tags)  # socket
        cv.create_oval(*p(ex - 0.8, -29.9), *p(ex + 0.8, -28.3), fill=RED, outline="",
                       tags=tags + ("reaper_eyes",))
        cv.create_oval(*p(ex - 0.3, -29.4), *p(ex + 0.3, -28.8), fill="#fff0e0", outline="",
                       tags=tags + ("reaper_glow",))                       # white-hot core of the eye
    # sleeve and bony fingers wrapped round the shaft
    cv.create_polygon(*flat([p(8, -26), p(15, -12), p(14, -4), p(9, -6), p(6, -18)]), fill="#120d17",
                      outline=CLOAK_EDGE, tags=tags)
    hx, hy = hand
    for i in range(4):
        fy = hy + (i - 1.5) * 2 * s
        cv.create_line(hx - 3 * s, fy, hx + 3 * s, fy + 0.5 * s, fill=BONE, width=max(1, round(1.2 * s)),
                       capstyle="round", tags=tags)


# --- the window ------------------------------------------------------------

class SoundWorker:
    """Plays sounds on a background thread so beeps never freeze the window."""

    def __init__(self, sound: Sound):
        self.sound = sound
        self.jobs: queue.Queue = queue.Queue()
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while True:
            name, args = self.jobs.get()
            getattr(self.sound, name)(*args)

    def heartbeat(self, distance):
        if self.jobs.empty():  # skip a beat rather than fall behind
            self.jobs.put(("heartbeat", (distance,)))

    def caught(self):
        self.jobs.put(("caught", ()))

    def escaped(self):
        self.jobs.put(("escaped", ()))

    def life_lost(self):
        self.jobs.put(("life_lost", ()))


@dataclass
class Motion:
    """R8: one turn being shown as a slide (or, R10, a jump) from the old tiles to the new ones."""
    player_from: tuple
    player_to: tuple
    reaper_from: tuple
    reaper_to: tuple
    jump: bool
    frames: int
    frame: int = 0

    @property
    def t(self) -> float:
        return self.frame / self.frames


class GameWindow:
    INTRO, PLAYING, CAUGHT, OVER = "intro", "playing", "caught", "over"
    MIST_PUFFS = 6

    def __init__(self, root: tk.Tk, sound=None, threaded_sound: bool = True, animate: bool = True):
        self.root = root
        sound = sound if sound is not None else Sound()
        self.sound = SoundWorker(sound) if threaded_sound else sound
        self.animate = animate
        self.game = Game()
        self.motion: Motion | None = None
        self.face = 1
        self.width = VIEW_COLS * TILE
        self.map_height = VIEW_ROWS * TILE
        self.mist = [((i * 197) % self.width, 60 + (i * 131) % (self.map_height - 120), 0.6 + 0.25 * (i % 3))
                     for i in range(self.MIST_PUFFS)]  # (x, y, speed in px per frame)
        root.title("Escape the Grim Reaper")
        root.configure(bg=BLACK)
        root.resizable(False, False)
        self.canvas = tk.Canvas(root, width=self.width, height=self.map_height + HUD_HEIGHT,
                                bg=BLACK, highlightthickness=0)
        self.canvas.pack()
        root.bind("<Key>", lambda e: self.on_key(e.keysym))
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.state = self.INTRO
        self.message = ""
        self.ticks = 0
        self._title_lift = 0.0
        self.redraw()
        self._after = root.after(TICK_MS, self._tick)

    # --- input ---
    def on_key(self, keysym: str) -> None:
        if keysym == "Escape":
            self.close()
            return
        if self.motion is not None:  # a key during a slide finishes it at once (R8)
            self.motion = None
            self.redraw()
        if self.state == self.INTRO:
            self.state = self.PLAYING
            self.redraw()
            self.sound.heartbeat(self.game.reaper_distance())
            return
        if self.state == self.CAUGHT:  # R4: wait for R, then back to the start tiles
            if keysym in ("r", "R") and self.game.resume() is Outcome.RESUMED:
                self.state = self.PLAYING
                self.message = ""
                self.redraw()
                self.sound.heartbeat(self.game.reaper_distance())
            return
        if self.state == self.OVER:
            if keysym in ("r", "R"):
                self.game = Game()
                self.face = 1
                self.state = self.PLAYING
                self.message = ""
                self.redraw()
                self.sound.heartbeat(self.game.reaper_distance())
            return
        game = self.game
        before = game.player, game.reaper
        if keysym in JUMP_KEYS:  # R10
            outcome = game.jump()
        elif keysym in KEY_DIRECTIONS:
            outcome = game.move(KEY_DIRECTIONS[keysym])
        else:
            return
        if game.facing in ("left", "right"):
            self.face = -1 if game.facing == "left" else 1
        if outcome is Outcome.WALL:
            self.message = bump_line(game.bumped, "Press ↑")
        elif outcome is Outcome.NO_JUMP:
            self.message = jump_line(game.jump_blocked)
        else:
            self.message = ""
        if game.status is Status.CAUGHT:
            self.state = self.CAUGHT
        elif game.status is not Status.PLAYING:
            self.state = self.OVER
        if outcome is Outcome.MOVED and self.animate:
            self.motion = Motion(before[0], game.player, before[1], game.reaper, game.jumped,
                                 JUMP_FRAMES if game.jumped else SLIDE_FRAMES)
        self.redraw()
        if outcome is Outcome.MOVED:
            if game.status is Status.PLAYING:
                self.sound.heartbeat(game.reaper_distance())
            elif game.status is Status.CAUGHT:
                self.sound.life_lost()
            elif game.status is Status.LOST:
                self.sound.caught()
            elif game.status is Status.WON:
                self.sound.escaped()

    # --- where things are shown (R8) ---
    def _shown(self):
        """(player tile, reaper tile, lift, swing, reaper lean) as drawn now: fractional mid-slide."""
        m = self.motion
        if m is None:
            return self.game.player, self.game.reaper, 0.0, 0.0, 0.0
        player = tween(m.player_from, m.player_to, m.t if m.jump else ease(m.t))
        reaper = tween(m.reaper_from, m.reaper_to, ease(m.t))
        lift = jump_height(m.t) if m.jump else 0.0
        swing = 0.0 if m.jump or m.player_from == m.player_to else walk_pose(m.t)
        lean = float(m.reaper_to[1] - m.reaper_from[1]) * math.sin(math.pi * m.t)
        return player, reaper, lift, swing, lean

    # --- drawing ---
    def redraw(self) -> None:
        cv = self.canvas
        cv.delete("all")
        player, _, _, _, _ = self._shown()
        self.origin = camera_at(self.game.maze, player)
        self._draw_graveyard()
        cv.addtag_withtag("world", "all")
        self.world_origin = self.origin
        self._draw_mist()
        self._draw_actors()
        self._draw_danger_border()
        self._draw_hud()
        if self.motion is None:  # the screens wait until the last slide has been seen
            if self.state == self.INTRO:
                self._draw_intro()
            elif self.state == self.CAUGHT:
                self._draw_caught()
            elif self.state == self.OVER:
                self._draw_ending()
        self._restack()

    def _restack(self):
        for tag in ("mist", "danger", "hud", "overlay"):
            self.canvas.tag_raise(tag)

    def _xy(self, pos):
        """Top-left pixel of a maze tile inside the camera view."""
        return (pos[1] - self.origin[1]) * TILE, (pos[0] - self.origin[0]) * TILE

    def _draw_graveyard(self):
        """R6: grass everywhere, then whatever stands or lies on each tile (all moonlit since R9)."""
        maze = self.game.maze
        tops, lefts = [self.origin[0]], [self.origin[1]]
        if self.motion is not None:  # also build the tiles the camera will scroll onto
            end = camera_at(maze, self.motion.player_to)
            tops.append(end[0])
            lefts.append(end[1])
        r0, r1 = max(0, math.floor(min(tops))), min(maze.height, math.ceil(max(tops)) + VIEW_ROWS)
        c0, c1 = max(0, math.floor(min(lefts))), min(maze.width, math.ceil(max(lefts)) + VIEW_COLS)
        for r in range(r0, r1):
            for c in range(c0, c1):
                pos = (r, c)
                light = light_level(self.game, pos)
                self._warmth = torch_glow(self.game.player, pos)
                x0, y0 = self._xy(pos)
                self._draw_grass(x0, y0, light, r, c)
                obstacle = maze.obstacle(pos)
                hazard = maze.hazard(pos)
                if pos in maze.signs:
                    self._draw_signpost(x0, y0, light, maze.signs[pos].kind)
                elif obstacle == "iron fence":
                    self._draw_fence(x0, y0, light)
                elif obstacle == "gravestone":
                    self._draw_gravestone(x0, y0, light, (r * 7 + c * 3) % 3)
                elif obstacle == "dead tree":
                    self._draw_tree(x0, y0, light, (r + c) % 2)
                elif hazard == "open grave":
                    self._draw_open_grave(x0, y0, light)
                elif hazard == "thorn bush":
                    self._draw_thorns(x0, y0, light)
                elif maze.low_hurdle(pos) == "fallen headstone":
                    self._draw_fallen_headstone(x0, y0, light)
                elif maze.low_hurdle(pos) == "coffin":
                    self._draw_coffin(x0, y0, light)
                elif pos == maze.exit:
                    self._draw_exit(x0, y0, light)

    def _lit(self, colour, light):
        """R9: colour of a thing on the tile being drawn: moon-cool far away, torch-warm close by."""
        return lit(colour, light, self._warmth)

    def _draw_grass(self, x0, y0, light, r, c):
        cv = self.canvas
        variation = 0.88 + 0.12 * ((r * 31 + c * 17) % 3) / 2
        cv.create_rectangle(x0, y0, x0 + TILE, y0 + TILE, fill=self._lit(GRASS, light * variation),
                            outline=self._lit(GRASS_DARK, light), tags=("grass", "floor"))
        if (r * 13 + c * 7) % 4 == 0:  # a darker patch here and there
            ox, oy = (r * 11 + c * 5) % 20, (r * 3 + c * 13) % 22
            cv.create_oval(x0 + ox + 4, y0 + oy + 6, x0 + ox + 26, y0 + oy + 20,
                           fill=self._lit(GRASS_DARK, light), outline="", tags="grass")
        if (r + c) % 2 == 0:  # a tuft on every other tile (each line item costs paint time on every frame)
            gx, gy = 12 + (r * 5 + c * 11) % 24, 18 + (r * 7 + c * 3) % 24
            cv.create_line(x0 + gx - 3, y0 + gy - 6, x0 + gx, y0 + gy, x0 + gx + 3, y0 + gy - 7,
                           fill=self._lit(mix(GRASS_BLADE, GRASS, 0.45), light), tags="grass")

    def _draw_fence(self, x0, y0, light):
        """Iron railings: two rails and four bars with spear tips, with a moonlit edge."""
        cv = self.canvas
        iron = self._lit(IRON, light)
        shine = self._lit("#5a5a70", light)
        tags = ("fence", "obstacle")
        for y in (y0 + 18, y0 + 40):
            cv.create_line(x0, y, x0 + TILE, y, fill=iron, width=3, tags=tags)
        tips = []
        for i in range(4):
            x = x0 + 6.5 + i * 13
            cv.create_line(x, y0 + 12, x, y0 + TILE - 4, fill=iron, width=3, tags=tags)
            tips += [x - 4, y0 + 13, x, y0 + 4, x + 4, y0 + 13]
        cv.create_polygon(*tips, fill=iron, outline=shine, tags=tags)

    def _draw_gravestone(self, x0, y0, light, style):
        """A rounded headstone with a cross, a shaded side, a crack and moss, on a mound of earth."""
        cv = self.canvas
        tags = ("grave", "obstacle")
        stone, edge = self._lit(STONE, light), self._lit(STONE_DARK, light)
        cx = x0 + TILE / 2
        cv.create_oval(x0 + 6, y0 + TILE - 14, x0 + TILE - 6, y0 + TILE - 1, fill=self._lit(DIRT, light),
                       outline="", tags=tags)
        half = (12, 14, 11)[style]
        cv.create_rectangle(cx - half, y0 + 18, cx + half, y0 + TILE - 8, fill=stone, outline=edge, tags=tags)
        cv.create_arc(cx - half, y0 + 6, cx + half, y0 + 30, start=0, extent=180, fill=stone, outline=edge,
                      style="chord", tags=tags)
        cv.create_rectangle(cx - half + 1, y0 + 17, cx + half - 1, y0 + 20, fill=stone, outline="", tags=tags)
        cv.create_rectangle(cx + half - 5, y0 + 18, cx + half, y0 + TILE - 8, fill=edge, outline="", tags=tags)
        cv.create_arc(cx - half + 3, y0 + 8, cx + half - 6, y0 + 26, start=100, extent=70, style="arc",
                      outline=self._lit(STONE_LIGHT, light), width=2, tags=tags)
        cv.create_line(cx, y0 + 13, cx, y0 + 27, fill=edge, width=3, tags=tags)
        cv.create_line(cx - 5, y0 + 18, cx + 5, y0 + 18, fill=edge, width=3, tags=tags)
        cv.create_text(cx, y0 + 34, text="RIP", fill=edge, font=(FONT, 7, "bold"), tags=tags)
        if style != 1:  # a crack
            cv.create_line(cx - half + 2, y0 + 24, cx - half + 6, y0 + 29, cx - half + 4, y0 + 34, fill=edge,
                           tags=tags)
        cv.create_oval(cx - half - 1, y0 + TILE - 13, cx - half + 8, y0 + TILE - 7, fill=self._lit(MOSS, light),
                       outline="", tags=tags)

    def _draw_tree(self, x0, y0, light, flip):
        """A dead tree: a gnarled trunk with a dark side and bare, clawing branches."""
        cv = self.canvas
        tags = ("tree", "obstacle")
        bark, dark = self._lit(BARK, light), self._lit(BARK_DARK, light)
        s = -1 if flip else 1
        cx = x0 + TILE / 2
        cv.create_oval(cx - 12, y0 + TILE - 7, cx + 12, y0 + TILE - 1, fill=self._lit(GRASS_DARK, light),
                       outline="", tags=tags)
        cv.create_polygon(cx - 7, y0 + TILE - 3, cx - 3, y0 + 30, cx - 2, y0 + 18, cx + 3, y0 + 18,
                          cx + 3, y0 + 30, cx + 8, y0 + TILE - 3, fill=bark, outline="", tags=tags)
        cv.create_polygon(cx + 1, y0 + 20, cx + 3, y0 + 30, cx + 8, y0 + TILE - 3, cx + 2, y0 + TILE - 3,
                          fill=dark, outline="", tags=tags)
        for (ax, ay, bx, by, w) in ((0, 24, -16, 8, 3), (0, 20, 15, 4, 3), (-9, 14, -14, 2, 2),
                                    (8, 10, 18, 12, 2), (0, 18, 2, 2, 2), (-16, 8, -21, 10, 1),
                                    (15, 4, 20, 0, 1), (2, 2, -2, -2, 1)):
            cv.create_line(cx + s * ax, y0 + ay, cx + s * bx, y0 + by, fill=bark, width=w,
                           capstyle="round", tags=tags)

    def _draw_signpost(self, x0, y0, light, kind):
        """R2: a wooden post with a glowing plaque."""
        cv = self.canvas
        glow = RED if kind == WARNING else GREEN
        tags = ("sign", f"sign_{kind}", "obstacle")
        cx = x0 + TILE / 2
        cv.create_rectangle(cx - 3, y0 + 24, cx + 3, y0 + TILE - 2, fill=self._lit(BARK, light),
                            outline="", tags=tags)
        cv.create_rectangle(x0 + 2, y0 + 3, x0 + TILE - 2, y0 + 32, fill="", outline=shade(glow, 0.6), width=2,
                            tags=tags)  # the glow around the plaque
        cv.create_rectangle(x0 + 4, y0 + 5, x0 + TILE - 4, y0 + 30, fill=self._lit(PLANK, light),
                            outline=glow, width=3, tags=tags)
        cv.create_text(cx, y0 + 18, text="!", fill=shade(glow, 0.85), font=(FONT, 16, "bold"), tags=tags)

    def _draw_open_grave(self, x0, y0, light):
        """R7: a freshly dug pit with the earth heaped behind it."""
        cv = self.canvas
        tags = ("hazard", "open_grave")
        cv.create_oval(x0 + 6, y0 + 2, x0 + TILE - 6, y0 + 20, fill=self._lit(DIRT, light),
                       outline=self._lit(DIRT_DARK, light), tags=tags)
        cv.create_rectangle(x0 + 11, y0 + 13, x0 + TILE - 11, y0 + TILE - 4, fill=self._lit(DIRT_DARK, light),
                            outline=self._lit(DIRT, light), width=2, tags=tags)
        cv.create_rectangle(x0 + 15, y0 + 17, x0 + TILE - 15, y0 + TILE - 8, fill=PIT, outline="", tags=tags)
        cv.create_line(x0 + TILE - 9, y0 + 4, x0 + TILE - 14, y0 + 22, fill=self._lit(BARK, light), width=2,
                       tags=tags)  # a spade left in the heap

    def _draw_thorns(self, x0, y0, light):
        """R7: a tangle of dark red, spiky branches."""
        cv = self.canvas
        tags = ("hazard", "thorn_bush")
        stem, spike = self._lit(THORN, light), self._lit(THORN_TIP, light)
        for (ax, ay, bx, by) in ((6, 44, 46, 10), (6, 12, 46, 42), (26, 4, 26, 48), (4, 28, 48, 26)):
            cv.create_line(x0 + ax, y0 + ay, x0 + bx, y0 + by, fill=stem, width=3, tags=tags)
            length = math.hypot(bx - ax, by - ay)
            nx, ny = -(by - ay) / length * 5, (bx - ax) / length * 5  # sideways, 5 px
            zig = []
            for i in range(7):  # thorns stick out on alternate sides
                t = (i + 1) / 8
                side = 1 if i % 2 else -1
                zig += [x0 + ax + (bx - ax) * t + side * nx, y0 + ay + (by - ay) * t + side * ny]
            cv.create_line(*zig, fill=spike, width=1, tags=tags)

    def _draw_fallen_headstone(self, x0, y0, light):
        """R10: a cracked headstone lying flat in the grass, low enough to jump."""
        cv = self.canvas
        tags = ("low_hurdle", "fallen_headstone")
        stone, edge = self._lit(STONE, light), self._lit(STONE_DARK, light)
        cv.create_oval(x0 + 4, y0 + 30, x0 + TILE - 4, y0 + 46, fill=self._lit(DIRT_DARK, light), outline="",
                       tags=tags)
        cv.create_polygon(x0 + 6, y0 + 38, x0 + 10, y0 + 24, x0 + 40, y0 + 20, x0 + 47, y0 + 30, x0 + 44, y0 + 40,
                          fill=edge, outline="", tags=tags)  # the side of the slab
        cv.create_polygon(x0 + 6, y0 + 34, x0 + 10, y0 + 20, x0 + 40, y0 + 16, x0 + 47, y0 + 26, x0 + 44, y0 + 36,
                          fill=stone, outline=edge, tags=tags)
        cv.create_line(x0 + 22, y0 + 19, x0 + 26, y0 + 27, x0 + 22, y0 + 34, fill=edge, width=2, tags=tags)  # crack
        cv.create_text(x0 + 33, y0 + 27, text="RIP", fill=edge, font=(FONT, 7, "bold"), angle=8, tags=tags)

    def _draw_coffin(self, x0, y0, light):
        """R10: a wooden coffin lying on the grass, low enough to jump."""
        cv = self.canvas
        tags = ("low_hurdle", "coffin")
        wood, dark = self._lit(COFFIN, light), self._lit(COFFIN_DARK, light)
        cx = x0 + TILE / 2
        outline = (cx - 9, y0 + 3, cx + 9, y0 + 3, cx + 15, y0 + 15, cx + 10, y0 + TILE - 3, cx - 10, y0 + TILE - 3,
                   cx - 15, y0 + 15)
        cv.create_polygon(*[v + (3 if i % 2 else 2) for i, v in enumerate(outline)], fill=BLACK,
                          outline="", tags=tags)  # shadow
        cv.create_polygon(*outline, fill=wood, outline=dark, width=2, tags=tags)
        cv.create_line(cx, y0 + 12, cx, y0 + 34, fill=dark, width=3, tags=tags)       # the cross on the lid
        cv.create_line(cx - 6, y0 + 19, cx + 6, y0 + 19, fill=dark, width=3, tags=tags)

    def _draw_exit(self, x0, y0, light):
        """The way out: an iron cemetery gate in a green glow."""
        cv = self.canvas
        k = SCALE
        cx = x0 + TILE / 2
        iron = self._lit(IRON, light)
        cv.create_oval(x0 + 1, y0 + 1, x0 + TILE - 1, y0 + TILE - 1, fill=self._lit("#1e6b3a", light),
                       outline=GREEN, width=2, tags="exit")
        for side in (-1, 1):  # stone posts
            cv.create_rectangle(cx + side * 14 * k - 3, y0 + 8, cx + side * 14 * k + 3, y0 + TILE - 3,
                                fill=self._lit(STONE, light), outline="", tags="exit")
        cv.create_arc(cx - 11 * k, y0 + 6 * k, cx + 11 * k, y0 + 22 * k, start=0, extent=180, style="arc",
                      outline=iron, width=2, tags="exit")
        for i in range(5):
            x = cx - 10 * k + i * 5 * k
            cv.create_line(x, y0 + 13 * k, x, y0 + TILE - 4, fill=iron, width=2, tags="exit")
        cv.create_text(cx, y0 + 26 * k, text="EXIT", fill="#b8ffcf", font=(FONT, 8, "bold"), tags="exit")

    # --- things redrawn every frame (R8, R11) ---
    def _draw_mist(self):
        """R11: pale wisps of mist drifting across the graveyard (thin curls, so the ground stays visible)."""
        cv = self.canvas
        cv.delete("mist")
        for i, (x, y, _) in enumerate(self.mist):
            x -= 110  # wisps enter from the left edge and wrap round
            for j, (dy, length) in enumerate(((0, 200), (9, 130))):
                pts = []
                for k in range(6):
                    px = x - length / 2 + k * length / 5
                    pts += [px, y + dy + 5 * math.sin(k * 1.6 + i + j)]
                cv.create_line(*pts, fill=mix(MIST, GRASS, 0.25 + 0.2 * j), width=2, smooth=True,
                               capstyle="round", tags="mist")
        for layer in ("danger", "hud", "overlay"):  # new mist goes just under the first layer above it
            if cv.find_withtag(layer):
                cv.tag_lower("mist", layer)
                break

    def _draw_actors(self):
        """The reaper's aura and both figures at their shown (maybe mid-slide) positions."""
        cv = self.canvas
        player, reaper, lift, swing, lean = self._shown()
        cv.delete("actor")
        t = self.ticks * TICK_MS
        top, left = self.origin

        def centre(pos):
            return (pos[1] - left) * TILE + TILE / 2, (pos[0] - top) * TILE + TILE / 2

        px, py = centre(player)
        figures = [(player[0], self._draw_player_at, (px, py, lift, swing))]
        if in_view(self.origin, reaper):  # R9: no fog; the reaper is seen wherever it is on screen
            rx, ry = centre(reaper)
            period = heartbeat_period_ms(self.game.reaper_distance())
            pulse = 0.5 + 0.5 * math.sin(2 * math.pi * (t % period) / period)
            for k, colour in ((1.0, BLOOD), (0.7, RED)):  # R11: rings of red light pulse on the ground
                ar = TILE * k * (0.5 + 0.15 * pulse)
                cv.create_oval(rx - ar, ry + 14 - ar * 0.35, rx + ar, ry + 14 + ar * 0.35, fill="", outline=colour,
                               width=2, tags=("actor", "aura"))
            figures.append((reaper[0], self._draw_reaper_at, (rx, ry, t, lean)))
        for _, painter, args in sorted(figures, key=lambda f: f[0]):  # the lower one is drawn in front
            painter(*args)
        if cv.find_withtag("mist"):  # keep the figures under the mist without raising the mist:
            cv.tag_lower("actor", "mist")  # raising a layer repaints all of it (R8: keep frames cheap)

    def _draw_player_at(self, x, y, lift, swing):
        cv = self.canvas
        shadow = 12 * SCALE * (1 - 0.4 * lift / JUMP_LIFT)
        cv.create_oval(x - shadow, y + 15 * SCALE, x + shadow, y + 20 * SCALE, fill="#0a0c08", outline="",
                       tags=("actor", "player_shadow"))
        bob = 0.0 if lift or swing else 0.6 * math.sin(self.ticks * TICK_MS / 500.0)  # breathing
        draw_player(cv, x, y, SCALE, tag=("player", "actor"), swing=swing, face=self.face,
                    lift=lift + bob)

    def _draw_reaper_at(self, x, y, t, lean):
        draw_reaper(self.canvas, x, y, SCALE, tag=("reaper", "actor"), t=t, lean=lean)

    def _scroll_world(self):
        """R8: move the background with the camera instead of rebuilding it."""
        player, _, _, _, _ = self._shown()
        self.origin = camera_at(self.game.maze, player)
        dy = (self.world_origin[0] - self.origin[0]) * TILE
        dx = (self.world_origin[1] - self.origin[1]) * TILE
        if dx or dy:
            self.canvas.move("world", dx, dy)
        self.world_origin = self.origin

    def _draw_danger_border(self):
        if self.state == self.PLAYING and self.game.reaper_distance() <= 3:
            cv = self.canvas
            cv.create_rectangle(3, 3, self.width - 3, self.map_height - 3, outline=RED, width=6, tags="danger")
            cv.create_rectangle(9, 9, self.width - 9, self.map_height - 9, outline=BLOOD, width=5,
                                tags="danger")  # R11: the edges glow red

    def _draw_hud(self):
        cv, game = self.canvas, self.game
        top = self.map_height
        cv.create_rectangle(0, top, self.width, top + HUD_HEIGHT, fill=HUD_BG, outline=HUD_EDGE, tags="hud")
        cv.create_line(0, top + 1, self.width, top + 1, fill="#6b4a8a", width=2, tags="hud")
        cv.create_rectangle(6, top + 8, self.width - 6, top + HUD_HEIGHT - 6, outline=HUD_EDGE, tags="hud")
        if self.state != self.PLAYING:
            return
        dist = game.reaper_distance()
        self._draw_hearts(30, top + 45, HEART_GAP, HEART_SIZES[1], "heart", "heart_lost", "hud", anchor="w")
        text_x = 30 + HEART_GAP * MAX_LIVES
        cv.create_text(text_x, top + 28, anchor="w", text=f"Turn {game.turn}", fill="#d0d0e0",
                       font=(FONT, 14, "bold"), tags=("hud", "hud_turn"))
        cv.create_text(text_x, top + 60, anchor="w", text=reaper_line(dist, color=False),
                       fill=danger_colour(dist), font=(FONT, 14, "bold"), tags=("hud", "hud_status"))
        y = top + 100
        for sign in game.signs_here():
            colour = RED if sign.kind == WARNING else GREEN
            icon = "⚠" if sign.kind == WARNING else "✔"
            item = cv.create_text(self.width / 2, y, text=f'{icon}  Painted on a signpost: "{sign.text}"',
                                  fill=colour, font=(FONT, 18, "bold"), tags=("hud", "sign_banner"))
            size = 18
            while size > 10:  # shrink long signs until they fit the window
                x0, _, x1, _ = cv.bbox(item)
                if x1 - x0 <= self.width - 20:
                    break
                size -= 1
                cv.itemconfigure(item, font=(FONT, size, "bold"))
            y += 30
        if self.message:
            cv.create_text(self.width / 2, top + 100, text=self.message, fill=GREY,
                           font=(FONT, 12, "italic"), tags=("hud", "hud_message"))
        cv.create_text(self.width - 16, top + HUD_HEIGHT - 18, anchor="e", text=CONTROLS, fill="#7c7c94",
                       font=(FONT, 10), tags="hud")

    def _draw_hearts(self, x, y, gap, size, full_tag, lost_tag, layer, anchor="center"):
        """R5: one red heart per life left, then grey empty hearts for the lives lost."""
        for i in range(MAX_LIVES):
            alive = i < self.game.lives
            self.canvas.create_text(x + i * gap, y, anchor=anchor, text="♥" if alive else "♡",
                                    fill=RED if alive else HEART_LOST, font=(FONT, size, "bold"),
                                    tags=(layer, full_tag if alive else lost_tag))

    def _draw_big_hearts(self, y):
        gap = 90
        self._draw_hearts(self.width / 2 - gap, y, gap, 44, "big_heart", "big_heart_lost", "overlay")

    def _shade_screen(self, moon: str = "#e8e2c8"):
        """R11: a night backdrop for the title and ending screens: sky, a big moon behind bare branches,
        gravestones in low mist."""
        cv = self.canvas
        h = self.map_height + HUD_HEIGHT
        w = self.width
        for i, colour in enumerate(("#07050c", "#0b0814", "#100b1c", "#160f24")):  # sky, darker at the top
            cv.create_rectangle(0, i * h / 6, w, h, fill=colour, outline="", tags="overlay")
        mx, my = w - 120, 110
        cv.create_oval(mx - 95, my - 95, mx + 95, my + 95, fill=shade(moon, 0.22), outline="",
                       tags="overlay")  # halo
        cv.create_oval(mx - 70, my - 70, mx + 70, my + 70, fill=moon, outline="", tags="overlay")
        for (ox, oy, rr) in ((-25, -20, 14), (20, 15, 10), (-10, 30, 7)):  # craters
            cv.create_oval(mx + ox - rr, my + oy - rr, mx + ox + rr, my + oy + rr, fill=shade(moon, 0.86),
                           outline="", tags="overlay")
        tree = "#05030a"  # a bare tree across the moon
        cv.create_polygon(w - 40, h, w - 28, 120, w - 18, h, fill=tree, outline="", tags="overlay")
        for (ax, ay, bx, by, wd) in ((-32, 200, -120, 90, 6), (-120, 90, -170, 70, 3), (-90, 120, -95, 40, 3),
                                     (-28, 150, -60, 20, 4), (-60, 20, -40, -10, 2), (-150, 75, -200, 95, 2)):
            cv.create_line(w + ax, ay, w + bx, by, fill=tree, width=wd, capstyle="round", tags="overlay")
        cv.create_rectangle(0, h - 120, w, h, fill="#141019", outline="", tags="overlay")
        for x in range(40, int(w), 150):  # gravestones
            cv.create_rectangle(x, h - 150, x + 34, h - 112, fill="#2b2833", outline="#3d3946", tags="overlay")
            cv.create_arc(x, h - 168, x + 34, h - 134, start=0, extent=180, fill="#2b2833",
                          outline="#3d3946", tags="overlay")
            cv.create_text(x + 17, h - 135, text="RIP", fill="#4a4656", font=(FONT, 8, "bold"), tags="overlay")
        for row in range(3):  # wisps of low mist over the graves
            y = h - 150 + row * 16
            pts = []
            for k in range(13):
                pts += [k * w / 12, y + 6 * math.sin(k * 1.3 + row * 2)]
            cv.create_line(*pts, fill=shade(MIST, 0.75 - 0.15 * row), width=2, smooth=True, tags="overlay")

    def _title(self, y, text, colour, size):
        """R11: a big title with a dark, blood-red drop shadow."""
        cv = self.canvas
        cv.create_text(self.width / 2 + 4, y + 4, text=text, fill="#2a0006", font=(TITLE_FONT, size),
                       tags="overlay")
        return cv.create_text(self.width / 2, y, text=text, fill=colour, font=(TITLE_FONT, size), tags="overlay")

    def _draw_intro(self):
        cv = self.canvas
        mid = self.width / 2
        self._shade_screen()
        self._title_lift = 0.0
        draw_reaper(cv, mid - 270, 380, 4.6, tag=("overlay", "title_reaper"), t=0)
        draw_player(cv, mid + 260, 400, 4, tag="overlay")
        title = self._title(80, "ESCAPE THE GRIM REAPER", RED, 44)
        cv.addtag_withtag("title", title)
        cv.create_text(mid, 260, text="You wake among the graves at midnight.\n"
                                      "Something breathes behind you.\n\n"
                                      "Read the signposts.\nMind the open graves and thorns.\n"
                                      "Press ↑ to leap coffins and open graves.\n"
                                      "Find the EXIT gate. Don't look back.",
                       fill="#e0e0ea", font=(FONT, 15), justify="center", tags="overlay")
        cv.create_text(mid, self.map_height + 70, text="Press any key to begin", fill="#ffe066",
                       font=(FONT, 18, "bold"), tags=("overlay", "blink"))

    def _draw_caught(self):
        """R4 / R7: a life is lost to the reaper (CAUGHT!) or a hazard (HURT!); wait for R."""
        cv, game = self.canvas, self.game
        mid = self.width / 2
        self._shade_screen("#a8432f")
        by_reaper = game.hurt_by == "reaper"
        if by_reaper:
            draw_reaper(cv, mid, 440, 4, tag="overlay", t=self.ticks * TICK_MS)
        else:
            draw_player(cv, mid, 410, 5, tag="overlay")
        caught = self._title(75, "CAUGHT!" if by_reaper else "HURT!", ORANGE, 54)
        cv.addtag_withtag("caught_title", caught)
        left = f"{game.lives} {'life' if game.lives == 1 else 'lives'} left"
        cv.create_text(mid, 145, text=f"{LIFE_LOST[game.hurt_by or 'reaper']} ({left})",
                       fill="#e0e0ea", font=(FONT, 16), tags="overlay")
        self._draw_big_hearts(205)
        cv.create_text(mid, self.map_height + 70, text="Press R to resume    Esc to quit",
                       fill="#ffe066", font=(FONT, 18, "bold"), tags=("overlay", "blink"))

    def _draw_ending(self):
        cv, game = self.canvas, self.game
        mid = self.width / 2
        self._shade_screen("#c0392b" if game.status is Status.LOST else "#e8e2c8")
        if game.status is Status.WON:
            draw_player(cv, mid, 360, 5, tag="overlay")
            title, colour = "YOU ESCAPED!", GREEN
            sub = f"You burst into the night air after {game.turn} turns."
        elif game.status is Status.LOST:
            draw_reaper(cv, mid, 440, 4, tag="overlay", t=self.ticks * TICK_MS)
            self._draw_big_hearts(205)
            title, colour = "GAME OVER", RED
            sub = GAME_OVER[game.hurt_by or "reaper"]
        else:
            title, colour, sub = "YOU GAVE UP", GREY, "The Reaper is patient."
        ending = self._title(75, title, colour, 54)
        cv.addtag_withtag("ending_title", ending)
        cv.create_text(mid, 145, text=sub, fill="#e0e0ea", font=(FONT, 16), tags="overlay")
        cv.create_text(mid, self.map_height + 70, text="Press R to play again    Esc to quit",
                       fill="#ffe066", font=(FONT, 18, "bold"), tags=("overlay", "blink"))

    def close(self) -> None:
        """Stop the animation timer and close the window."""
        try:
            self.root.after_cancel(self._after)
            self.root.destroy()
        except tk.TclError:
            pass  # already closed

    # --- animation ---
    def _config(self, tag, **options):
        """itemconfigure, but only when something changed: every change repaints the items (R8: cheap frames)."""
        items = self.canvas.find_withtag(tag)
        if not items:
            return
        cache = self.__dict__.setdefault("_configured", {})
        if cache.get(tag) != (items, options):
            self.canvas.itemconfigure(tag, **options)
            cache[tag] = (items, options)

    def _tick(self):
        self.ticks += 1
        t = self.ticks * TICK_MS
        cv = self.canvas
        if self.motion is not None:  # R8: advance the slide
            self.motion.frame += 1
            if self.motion.frame >= self.motion.frames:
                self.motion = None
                self.redraw()  # rebuilds the background for the new tile and shows any screen
            else:
                self._scroll_world()
        if self.state != self.INTRO and not cv.find_withtag("overlay"):
            self._draw_actors()
        if self.ticks % 4 == 0:  # R11: the mist drifts; moving it repaints the whole view, so not every frame
            self.mist = [((x + 4 * v) % (self.width + 220), y, v) for x, y, v in self.mist]
            self._draw_mist()
        flicker = 0.75 + 0.25 * math.sin(t / 70.0) * math.sin(t / 23.0)
        self._config("flame", fill=shade("#ff9f1a", 0.7 + 0.3 * flicker))
        self._config("flame_core", fill=mix("#ffe066", "#fff6c8", flicker))
        glow = 0.55 + 0.45 * abs(math.sin(t / 300.0))
        self._config("reaper_eyes", fill=shade(RED, glow))
        lift = hover(t) * 4.6  # the reaper on the title screen floats too
        cv.move("title_reaper", 0, lift - self._title_lift)
        self._title_lift = lift
        period = heartbeat_period_ms(self.game.reaper_distance())
        phase = (t % period) / period
        size = HEART_SIZES[0] if phase < 0.12 or 0.22 < phase < 0.3 else HEART_SIZES[1]
        self._config("heart", font=(FONT, size, "bold"))
        self._config("danger", state="normal" if (t // 300) % 2 == 0 else "hidden")
        self._config("blink", state="normal" if (t // 600) % 2 == 0 else "hidden")
        # Keep a steady frame rate: the time spent drawing comes out of the next wait, not on top of it.
        now = time.perf_counter()
        self._next_frame = max(getattr(self, "_next_frame", now) + TICK_MS / 1000, now + 0.005)
        self._after = self.root.after(round((self._next_frame - now) * 1000), self._tick)


def run(mute: bool = False) -> int:
    root = tk.Tk()
    GameWindow(root, Sound(enabled=not mute))
    root.mainloop()
    return 0
