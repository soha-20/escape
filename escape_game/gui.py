"""Graphical game window (tkinter): animated figures, a moonlit graveyard, glowing signs.

Since round 5 the window plays in real time (R13, R15): keys held down are passed to the rules
(Game.press/release/press_jump) and every frame advances the game clock by the real time that passed.

Smooth frames (R15): on Windows a full repaint of the canvas takes 200-800 ms, so nothing may repaint
it during play. The whole graveyard is drawn once per window and never moves (no camera); each frame
redraws only the figures and the glows around them; the HUD lives on its own canvas; and the red danger
border is the colour of a frame around the canvas, not canvas items.

Tk on Windows ignores the canvas `stipple` option, so nothing here relies on transparency:
glows are rings, and mist is drawn as thin wisps.

The rules all live in game.py; this module only draws the game and passes on keys and time.
"""

import math
import time
import tkinter as tk

from .game import MAX_LIVES, Game, Outcome, Status
from .maze import WARNING
from .render import GAME_OVER, LIFE_LOST, bump_line, jump_line, reaper_line

TILE = 38            # pixels per graveyard tile: the whole 29 x 14 graveyard fits a 1280 x 720 screen
SCALE = TILE / 40    # figures are designed on a 40-pixel tile
ART = 52             # the tile art is designed on 52-pixel tiles, then scaled to TILE
ART_SCALE = ART / 40
HUD_HEIGHT = 90
BORDER = 5           # R15: the danger frame around the graveyard
FRAME_MS = 20        # R15: one animation frame
MAX_FRAME_MS = 100   # R15: a stalled frame never moves the game on by more than this
JUMP_LIFT = 24       # R10: how high the player rises, in design pixels (0.6 tile)
HEART_SIZES = (26, 21)   # HUD heart font size: beat, rest
HEART_GAP = 36           # pixels between HUD hearts

KEY_DIRECTIONS = {  # R10: the Up arrow jumps; W still moves north
    "w": "up", "W": "up",
    "Down": "down", "s": "down", "S": "down",
    "Left": "left", "a": "left", "A": "left",
    "Right": "right", "d": "right", "D": "right",
}
JUMP_KEYS = {"Up"}  # R10
CONTROLS = "Hold W A S D / ← ↓ →  to run     ↑  jump     Esc  quit"

# palette
BLACK = "#000000"
GRASS = "#4f7a3c"        # R6: the graveyard lawn
GRASS_DARK = "#2f4a25"
GRASS_BLADE = "#7fae5a"
GRAVEL = "#a39478"       # R12: the path
GRAVEL_DARK = "#6e6352"
GRAVEL_LIGHT = "#cfc2a6"
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


MOONLIGHT = 0.8     # R9: every tile is drawn at this brightness


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


def danger_colour(distance: int) -> str:
    if distance >= 6:
        return GREY
    if distance > 3:
        return ORANGE
    return RED


def progress(clock: float, started: float, duration: float) -> float:
    """R15: how far (0 .. 1) a figure is through a move that started at `started` and lasts `duration`."""
    return max(0.0, min(1.0, (clock - started) / duration))


def tween(a, b, t: float) -> tuple[float, float]:
    """R8: the point a fraction t of the way from tile a to tile b (R15: at a constant speed)."""
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

# --- the window ------------------------------------------------------------

class GameWindow:
    INTRO, PLAYING, CAUGHT, OVER = "intro", "playing", "caught", "over"
    SCREEN_MIST = 4
    POSE_EVERY = 3   # R15: rebuild the figures' shapes every 3rd frame; move them in between

    def __init__(self, root: tk.Tk, autorun: bool = True):
        """autorun=False leaves the frame timer off: tests then drive time with advance(ms)."""
        self.root = root
        self.game = Game(realtime=True)
        maze = self.game.maze
        self.width = maze.width * TILE
        self.map_height = maze.height * TILE
        root.title("Escape the Grim Reaper")
        root.configure(bg=BLACK)
        root.resizable(False, False)
        self.border = tk.Frame(root, bg=BLACK, padx=BORDER, pady=BORDER)  # R15: the danger frame
        self.border.pack()
        self.canvas = tk.Canvas(self.border, width=self.width, height=self.map_height, bg=BLACK,
                                highlightthickness=0)
        self.canvas.pack()
        self.hud = tk.Canvas(root, width=self.width + 2 * BORDER, height=HUD_HEIGHT, bg=HUD_BG,
                             highlightthickness=0)  # R15: its own canvas, so it never repaints the graveyard
        self.hud.pack()
        root.bind("<KeyPress>", lambda e: self.on_key(e.keysym))
        root.bind("<KeyRelease>", lambda e: self.on_key_up(e.keysym))
        root.bind("<FocusOut>", lambda e: self._release_all())
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.state = self.INTRO
        self.message = ""
        self.ticks = 0
        self.ms = 0.0                 # animation time (flicker, hover, beats)
        self.face = 1
        self._screen_shown = False
        self._hud_key = None
        self._configured = {}
        self._title_lift = 0.0
        self._drawn = None            # R15: where the figures were last drawn, and in what pose
        self._draw_graveyard()        # R15: once per window; it never changes or moves
        self.redraw()
        self._after = None
        if autorun:
            self._last = time.perf_counter()
            self._next_frame = self._last
            self._after = root.after(FRAME_MS, self._tick)

    # --- input (R13, R15) ---
    def on_key(self, keysym: str) -> None:
        """A key went down (Windows repeats this while it is held)."""
        if keysym == "Escape":
            self.close()
            return
        game = self.game
        if self.state == self.INTRO:
            self.state = self.PLAYING
            self.redraw()
            return
        if self.state in (self.CAUGHT, self.OVER) and not self._screen_shown:
            self._show_screen()  # a key while the last step is still on its way shows the screen at once
        if self.state == self.CAUGHT:  # R4: wait for R, then back to the start tiles
            if keysym in ("r", "R") and game.resume() is Outcome.RESUMED:
                self.state = self.PLAYING
                self.message = ""
                self.redraw()
            return
        if self.state == self.OVER:
            if keysym in ("r", "R"):
                self.game = Game(realtime=True)
                self.face = 1
                self.state = self.PLAYING
                self.message = ""
                self.redraw()
            return
        if keysym in JUMP_KEYS:  # R10
            game.press_jump()
        elif keysym in KEY_DIRECTIONS:  # R15: held keys run
            game.press(KEY_DIRECTIONS[keysym])
        else:
            return
        # R15: no drawing here. Windows repeats a held key ~30 times a second, and drawing a frame
        # for each repeat doubled the work; the next frame (at most FRAME_MS away) shows the step.
        self._after_rules()

    def on_key_up(self, keysym: str) -> None:
        """R15: a movement key came up: the player stops at the next tile."""
        if keysym in KEY_DIRECTIONS:
            self.game.release(KEY_DIRECTIONS[keysym])

    def _release_all(self) -> None:
        """R15: if the window loses the keyboard, no key stays 'held' and the player doesn't run off."""
        for direction in list(self.game.held):
            self.game.release(direction)

    # --- time (R13, R15) ---
    def advance(self, ms: float) -> None:
        """Let ms milliseconds pass: the rules move on, then one frame is drawn."""
        self.ticks += 1
        self.ms += ms
        if self.state != self.INTRO:
            self.game.update(ms)
            self._after_rules()
        self._frame()

    def _tick(self):
        now = time.perf_counter()
        self.advance(min(MAX_FRAME_MS, (now - self._last) * 1000))
        self._last = now
        # Keep a steady frame rate: the time spent drawing comes out of the next wait, not on top of it.
        now = time.perf_counter()
        self._next_frame = max(self._next_frame + FRAME_MS / 1000, now + 0.005)
        self._after = self.root.after(round((self._next_frame - now) * 1000), self._tick)

    def _after_rules(self) -> None:
        """Turn what the rules did into messages and screens."""
        game = self.game
        for outcome in game.events:
            if outcome is Outcome.WALL:
                self.message = bump_line(game.bumped, "Press ↑")
            elif outcome is Outcome.NO_JUMP:
                self.message = jump_line(game.jump_blocked)
            else:
                self.message = ""
        game.events.clear()
        if game.facing in ("left", "right"):
            self.face = -1 if game.facing == "left" else 1
        if self.state == self.PLAYING and game.status is not Status.PLAYING:
            self.state = self.CAUGHT if game.status is Status.CAUGHT else self.OVER
            self._screen_shown = False

    def _motion_done(self) -> bool:
        """R8: both figures have finished the step they were taking."""
        g = self.game
        return (g.clock >= g.player_moved_at + g.player_move_ms
                and g.clock >= g.reaper_moved_at + g.reaper_move_ms)

    # --- where the figures are shown (R8, R15) ---
    def _shown(self):
        """(player tile, reaper tile, lift, swing, reaper lean) as drawn now: part of the way through a step."""
        g = self.game
        pt = progress(g.clock, g.player_moved_at, g.player_move_ms)
        rt = progress(g.clock, g.reaper_moved_at, g.reaper_move_ms)
        player = tween(g.player_from, g.player, pt)  # R15: a constant speed, so a run never stutters
        reaper = tween(g.reaper_from, g.reaper, rt)
        moving = pt < 1 and g.player_from != g.player
        lift = jump_height(pt) if moving and g.jumped else 0.0
        swing = walk_pose(pt) if moving and not g.jumped else 0.0
        lean = float(g.reaper[1] - g.reaper_from[1]) * math.sin(math.pi * rt) if rt < 1 else 0.0
        return player, reaper, lift, swing, lean

    # --- drawing ---
    def redraw(self) -> None:
        """Rebuild everything but the graveyard: figures, HUD and the screen for the current state."""
        cv = self.canvas
        cv.delete("actor", "overlay")
        self._drawn = None
        cv.itemconfigure("world", state="normal")
        self._screen_shown = False
        self._hud_key = None
        self._frame()

    def _show_screen(self) -> None:
        self.canvas.delete("actor", "overlay")
        if self.state == self.INTRO:
            self._draw_intro()
        elif self.state == self.CAUGHT:
            self._draw_caught()
        elif self.state == self.OVER:
            self._draw_ending()
        # R15: the graveyard under a screen is hidden, or the drifting mist would repaint all of it
        self.canvas.itemconfigure("world", state="hidden")
        self._screen_shown = True
        self._hud_key = None

    def _frame(self) -> None:
        """One frame. During play only the figures, the HUD values and the danger frame change (R15)."""
        cv = self.canvas
        if self.state != self.PLAYING and not self._screen_shown and (self.state == self.INTRO
                                                                      or self._motion_done()):
            self._show_screen()   # R8: the screens wait until the last step has been seen
        if not self._screen_shown:
            self._draw_actors()
        self._draw_hud()
        t = self.ms
        flicker = 0.75 + 0.25 * math.sin(t / 70.0) * math.sin(t / 23.0)
        self._config(cv, "flame", fill=shade("#ff9f1a", 0.7 + 0.3 * flicker))
        self._config(cv, "flame_core", fill=mix("#ffe066", "#fff6c8", flicker))
        glow = 0.55 + 0.45 * abs(math.sin(t / 300.0))
        self._config(cv, "reaper_eyes", fill=shade(RED, glow))
        lift = hover(t) * 4.6  # the reaper on the title screen floats too
        cv.move("title_reaper", 0, lift - self._title_lift)
        self._title_lift = lift
        if self._screen_shown and self.ticks % 2 == 0:  # R11: mist drifts on the screens (not during play)
            cv.move("screen_mist", 1, 0)
        playing = self.state == self.PLAYING
        distance = self.game.reaper_distance() if playing else 99
        period = heartbeat_period_ms(distance)
        phase = (t % period) / period
        size = HEART_SIZES[0] if phase < 0.12 or 0.22 < phase < 0.3 else HEART_SIZES[1]
        self._config(self.hud, "heart", font=(FONT, size, "bold"))
        danger = playing and distance <= 3 and (t // 250) % 2 == 0
        colour = RED if danger else (BLOOD if playing and distance <= 3 else BLACK)
        if self.border.cget("bg") != colour:  # R15: a frame colour, not canvas items: the map is not repainted
            self.border.configure(bg=colour)
        self._config(cv, "blink", state="normal" if (t // 600) % 2 == 0 else "hidden")

    def close(self) -> None:
        """Stop the animation timer and close the window."""
        try:
            if self._after is not None:
                self.root.after_cancel(self._after)
            self.root.destroy()
        except tk.TclError:
            pass  # already closed

    def _config(self, cv, tag, **options):
        """itemconfigure, but only when something changed: every change repaints the items (R15)."""
        items = cv.find_withtag(tag)
        if not items:
            return
        key = (str(cv), tag)
        if self._configured.get(key) != (items, options):
            cv.itemconfigure(tag, **options)
            self._configured[key] = (items, options)

    # --- the graveyard: drawn once (R6, R12, R15) ---
    def _xy(self, pos):
        """Top-left of a graveyard tile, in tile-art units (scaled to TILE once everything is drawn)."""
        return pos[1] * ART, pos[0] * ART

    def _path_like(self, pos) -> bool:
        """R12: gravel under a tile: the path itself, or a hurdle lying across it."""
        maze = self.game.maze
        if maze.on_path(pos):
            return True
        if maze.hazard(pos) or maze.low_hurdle(pos):
            r, c = pos
            return ((maze.on_path((r, c - 1)) and maze.on_path((r, c + 1)))
                    or (maze.on_path((r - 1, c)) and maze.on_path((r + 1, c))))
        return False

    def _draw_graveyard(self):
        """R6/R12: grass or gravel on every tile, then whatever stands or lies on it; all moonlit (R9)."""
        maze = self.game.maze
        light = MOONLIGHT
        self._warmth = 0.0
        for r in range(maze.height):
            for c in range(maze.width):
                pos = (r, c)
                x0, y0 = self._xy(pos)
                if self._path_like(pos):
                    self._draw_path(x0, y0, light, r, c)
                else:
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
        self.canvas.scale("all", 0, 0, TILE / ART, TILE / ART)
        self._draw_mist()
        self.canvas.addtag_withtag("world", "all")

    def _lit(self, colour, light):
        """R9: colour of a thing on a tile: moonlit."""
        return lit(colour, light, self._warmth)

    def _draw_grass(self, x0, y0, light, r, c):
        cv = self.canvas
        variation = 0.88 + 0.12 * ((r * 31 + c * 17) % 3) / 2
        cv.create_rectangle(x0, y0, x0 + ART, y0 + ART, fill=self._lit(GRASS, light * variation),
                            outline=self._lit(GRASS_DARK, light), tags=("grass", "floor"))
        if (r * 13 + c * 7) % 4 == 0:  # a darker patch here and there
            ox, oy = (r * 11 + c * 5) % 20, (r * 3 + c * 13) % 22
            cv.create_oval(x0 + ox + 4, y0 + oy + 6, x0 + ox + 26, y0 + oy + 20,
                           fill=self._lit(GRASS_DARK, light), outline="", tags="grass")
        if (r + c) % 2 == 0:  # a tuft on every other tile
            gx, gy = 12 + (r * 5 + c * 11) % 24, 18 + (r * 7 + c * 3) % 24
            cv.create_line(x0 + gx - 3, y0 + gy - 6, x0 + gx, y0 + gy, x0 + gx + 3, y0 + gy - 7,
                           fill=self._lit(mix(GRASS_BLADE, GRASS, 0.45), light), tags="grass")

    def _draw_path(self, x0, y0, light, r, c):
        """R12: a pale gravel path with a few pebbles, so the way through reads at a glance."""
        cv = self.canvas
        variation = 0.92 + 0.08 * ((r * 7 + c * 13) % 3) / 2
        cv.create_rectangle(x0, y0, x0 + ART, y0 + ART, fill=self._lit(GRAVEL, light * variation),
                            outline=self._lit(mix(GRAVEL, GRAVEL_DARK, 0.4), light), tags=("path", "floor"))
        for k in range(3):
            px = 5 + (r * 11 + c * 7 + k * 13) % (ART - 10)
            py = 5 + (r * 5 + c * 17 + k * 11) % (ART - 10)
            colour = GRAVEL_LIGHT if k % 2 else GRAVEL_DARK
            cv.create_oval(x0 + px, y0 + py, x0 + px + 3, y0 + py + 2, fill=self._lit(colour, light),
                           outline="", tags="path")


    def _draw_fence(self, x0, y0, light):
        """Iron railings: two rails and four bars with spear tips, with a moonlit edge."""
        cv = self.canvas
        iron = self._lit(IRON, light)
        shine = self._lit("#5a5a70", light)
        tags = ("fence", "obstacle")
        for y in (y0 + 18, y0 + 40):
            cv.create_line(x0, y, x0 + ART, y, fill=iron, width=3, tags=tags)
        tips = []
        for i in range(4):
            x = x0 + 6.5 + i * 13
            cv.create_line(x, y0 + 12, x, y0 + ART - 4, fill=iron, width=3, tags=tags)
            tips += [x - 4, y0 + 13, x, y0 + 4, x + 4, y0 + 13]
        cv.create_polygon(*tips, fill=iron, outline=shine, tags=tags)

    def _draw_gravestone(self, x0, y0, light, style):
        """A rounded headstone with a cross, a shaded side, a crack and moss, on a mound of earth."""
        cv = self.canvas
        tags = ("grave", "obstacle")
        stone, edge = self._lit(STONE, light), self._lit(STONE_DARK, light)
        cx = x0 + ART / 2
        cv.create_oval(x0 + 6, y0 + ART - 14, x0 + ART - 6, y0 + ART - 1, fill=self._lit(DIRT, light),
                       outline="", tags=tags)
        half = (12, 14, 11)[style]
        cv.create_rectangle(cx - half, y0 + 18, cx + half, y0 + ART - 8, fill=stone, outline=edge, tags=tags)
        cv.create_arc(cx - half, y0 + 6, cx + half, y0 + 30, start=0, extent=180, fill=stone, outline=edge,
                      style="chord", tags=tags)
        cv.create_rectangle(cx - half + 1, y0 + 17, cx + half - 1, y0 + 20, fill=stone, outline="", tags=tags)
        cv.create_rectangle(cx + half - 5, y0 + 18, cx + half, y0 + ART - 8, fill=edge, outline="", tags=tags)
        cv.create_arc(cx - half + 3, y0 + 8, cx + half - 6, y0 + 26, start=100, extent=70, style="arc",
                      outline=self._lit(STONE_LIGHT, light), width=2, tags=tags)
        cv.create_line(cx, y0 + 13, cx, y0 + 27, fill=edge, width=3, tags=tags)
        cv.create_line(cx - 5, y0 + 18, cx + 5, y0 + 18, fill=edge, width=3, tags=tags)
        cv.create_text(cx, y0 + 34, text="RIP", fill=edge, font=(FONT, 7, "bold"), tags=tags)
        if style != 1:  # a crack
            cv.create_line(cx - half + 2, y0 + 24, cx - half + 6, y0 + 29, cx - half + 4, y0 + 34, fill=edge,
                           tags=tags)
        cv.create_oval(cx - half - 1, y0 + ART - 13, cx - half + 8, y0 + ART - 7, fill=self._lit(MOSS, light),
                       outline="", tags=tags)

    def _draw_tree(self, x0, y0, light, flip):
        """A dead tree: a gnarled trunk with a dark side and bare, clawing branches."""
        cv = self.canvas
        tags = ("tree", "obstacle")
        bark, dark = self._lit(BARK, light), self._lit(BARK_DARK, light)
        s = -1 if flip else 1
        cx = x0 + ART / 2
        cv.create_oval(cx - 12, y0 + ART - 7, cx + 12, y0 + ART - 1, fill=self._lit(GRASS_DARK, light),
                       outline="", tags=tags)
        cv.create_polygon(cx - 7, y0 + ART - 3, cx - 3, y0 + 30, cx - 2, y0 + 18, cx + 3, y0 + 18,
                          cx + 3, y0 + 30, cx + 8, y0 + ART - 3, fill=bark, outline="", tags=tags)
        cv.create_polygon(cx + 1, y0 + 20, cx + 3, y0 + 30, cx + 8, y0 + ART - 3, cx + 2, y0 + ART - 3,
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
        cx = x0 + ART / 2
        cv.create_rectangle(cx - 3, y0 + 24, cx + 3, y0 + ART - 2, fill=self._lit(BARK, light),
                            outline="", tags=tags)
        cv.create_rectangle(x0 + 2, y0 + 3, x0 + ART - 2, y0 + 32, fill="", outline=shade(glow, 0.6), width=2,
                            tags=tags)  # the glow around the plaque
        cv.create_rectangle(x0 + 4, y0 + 5, x0 + ART - 4, y0 + 30, fill=self._lit(PLANK, light),
                            outline=glow, width=3, tags=tags)
        cv.create_text(cx, y0 + 18, text="!", fill=shade(glow, 0.85), font=(FONT, 14, "bold"), tags=tags)

    def _draw_open_grave(self, x0, y0, light):
        """R7: a freshly dug pit with the earth heaped behind it."""
        cv = self.canvas
        tags = ("hazard", "open_grave")
        cv.create_oval(x0 + 6, y0 + 2, x0 + ART - 6, y0 + 20, fill=self._lit(DIRT, light),
                       outline=self._lit(DIRT_DARK, light), tags=tags)
        cv.create_rectangle(x0 + 11, y0 + 13, x0 + ART - 11, y0 + ART - 4, fill=self._lit(DIRT_DARK, light),
                            outline=self._lit(DIRT, light), width=2, tags=tags)
        cv.create_rectangle(x0 + 15, y0 + 17, x0 + ART - 15, y0 + ART - 8, fill=PIT, outline="", tags=tags)
        cv.create_line(x0 + ART - 9, y0 + 4, x0 + ART - 14, y0 + 22, fill=self._lit(BARK, light), width=2,
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
        cv.create_oval(x0 + 4, y0 + 30, x0 + ART - 4, y0 + 46, fill=self._lit(DIRT_DARK, light), outline="",
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
        cx = x0 + ART / 2
        outline = (cx - 9, y0 + 3, cx + 9, y0 + 3, cx + 15, y0 + 15, cx + 10, y0 + ART - 3, cx - 10, y0 + ART - 3,
                   cx - 15, y0 + 15)
        cv.create_polygon(*[v + (3 if i % 2 else 2) for i, v in enumerate(outline)], fill=BLACK,
                          outline="", tags=tags)  # shadow
        cv.create_polygon(*outline, fill=wood, outline=dark, width=2, tags=tags)
        cv.create_line(cx, y0 + 12, cx, y0 + 34, fill=dark, width=3, tags=tags)       # the cross on the lid
        cv.create_line(cx - 6, y0 + 19, cx + 6, y0 + 19, fill=dark, width=3, tags=tags)

    def _draw_exit(self, x0, y0, light):
        """The way out: an iron cemetery gate in a green glow."""
        cv = self.canvas
        k = ART_SCALE
        cx = x0 + ART / 2
        iron = self._lit(IRON, light)
        cv.create_oval(x0 + 1, y0 + 1, x0 + ART - 1, y0 + ART - 1, fill=self._lit("#1e6b3a", light),
                       outline=GREEN, width=2, tags="exit")
        for side in (-1, 1):  # stone posts
            cv.create_rectangle(cx + side * 14 * k - 3, y0 + 8, cx + side * 14 * k + 3, y0 + ART - 3,
                                fill=self._lit(STONE, light), outline="", tags="exit")
        cv.create_arc(cx - 11 * k, y0 + 6 * k, cx + 11 * k, y0 + 22 * k, start=0, extent=180, style="arc",
                      outline=iron, width=2, tags="exit")
        for i in range(5):
            x = cx - 10 * k + i * 5 * k
            cv.create_line(x, y0 + 13 * k, x, y0 + ART - 4, fill=iron, width=2, tags="exit")
        cv.create_text(cx, y0 + 26 * k, text="EXIT", fill="#b8ffcf", font=(FONT, 8, "bold"), tags="exit")

    def _draw_mist(self):
        """R11: pale wisps of mist lying over the graveyard. R15: they stay still during play, because
        moving them would repaint most of the graveyard every frame."""
        cv = self.canvas
        for i in range(7):
            x = (i * 389) % self.width
            y = TILE * (1.5 + (i * 5) % 12)
            for j, (dy, length) in enumerate(((0, 170), (8, 110))):
                pts = []
                for k in range(6):
                    px = x - length / 2 + k * length / 5
                    pts += [px, y + dy + 4 * math.sin(k * 1.6 + i + j)]
                cv.create_line(*pts, fill=mix(MIST, GRASS, 0.3 + 0.2 * j), width=2, smooth=True,
                               capstyle="round", tags="mist")

    # --- the figures: redrawn every frame (R8, R11, R15) ---
    def _draw_actors(self):
        """The torch glow, the reaper's aura and both figures at their shown (maybe mid-step) positions.

        R15: building the ~100 figure items is the costliest part of a frame, so their shapes (walk pose,
        fluttering hem, hover) are rebuilt only every POSE_EVERY frames (and every frame of a jump); in
        between, the figures already drawn are just moved to where they now are, so the motion stays smooth."""
        cv = self.canvas
        player, reaper, lift, swing, lean = self._shown()

        def centre(pos):
            return pos[1] * TILE + TILE / 2, pos[0] * TILE + TILE / 2

        px, py = centre(player)
        rx, ry = centre(reaper)
        pose = (self.face, lift > 0)
        drawn = self._drawn
        if (drawn is not None and drawn[2] == pose and not lift and cv.find_withtag("actor")
                and self.ticks % self.POSE_EVERY):
            cv.move("player_group", px - drawn[0][0], py - drawn[0][1])
            cv.move("reaper_group", rx - drawn[1][0], ry - drawn[1][1])
            self._drawn = ((px, py), (rx, ry), pose)
            return
        self._drawn = ((px, py), (rx, ry), pose)
        cv.delete("actor")
        t = self.ms

        for k, colour in ((1.25, shade(TORCH_TINT, 0.55)), (0.8, TORCH_TINT)):  # R9: warm torchlight rings
            gr = TILE * k * (0.95 + 0.05 * math.sin(t / 90.0))
            cv.create_oval(px - gr, py + 10 - gr * 0.4, px + gr, py + 10 + gr * 0.4, fill="", outline=colour,
                           width=2, tags=("actor", "torch_glow", "player_group"))
        period = heartbeat_period_ms(self.game.reaper_distance())
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * (t % period) / period)
        for k, colour in ((1.0, BLOOD), (0.7, RED)):  # R11: rings of red light pulse on the ground
            ar = TILE * k * (0.5 + 0.15 * pulse)
            cv.create_oval(rx - ar, ry + 11 - ar * 0.35, rx + ar, ry + 11 + ar * 0.35, fill="", outline=colour,
                           width=2, tags=("actor", "aura", "reaper_group"))
        figures = [(player[0], self._draw_player_at, (px, py, lift, swing)),
                   (reaper[0], self._draw_reaper_at, (rx, ry, t, lean))]
        for _, painter, args in sorted(figures, key=lambda f: f[0]):  # the lower one is drawn in front
            painter(*args)
        cv.tag_lower("actor", "mist")  # under the mist; lowering the few figure items is cheap (R15)

    def _draw_player_at(self, x, y, lift, swing):
        cv = self.canvas
        shadow = 12 * SCALE * (1 - 0.4 * lift / JUMP_LIFT)
        cv.create_oval(x - shadow, y + 15 * SCALE, x + shadow, y + 20 * SCALE, fill="#0a0c08", outline="",
                       tags=("actor", "player_shadow", "player_group"))
        bob = 0.0 if lift or swing else 0.6 * math.sin(self.ms / 500.0)  # breathing
        draw_player(cv, x, y, SCALE, tag=("player", "actor", "player_group"), swing=swing, face=self.face, lift=lift + bob)

    def _draw_reaper_at(self, x, y, t, lean):
        draw_reaper(self.canvas, x, y, SCALE, tag=("reaper", "actor", "reaper_group"), t=t, lean=lean)

    # --- the status panel: its own canvas (R1, R5, R15) ---
    def _draw_hud(self):
        """Rebuilt only when what it shows changes; the time and the status line are just updated."""
        hud, game = self.hud, self.game
        playing = self.state == self.PLAYING and not self._screen_shown
        signs = tuple(s.text for s in game.signs_here()) if playing else ()
        key = (self.state, playing, game.lives, self.message, signs)
        if key != self._hud_key:
            self._hud_key = key
            self._build_hud(playing)
        if playing:
            dist = game.reaper_distance()
            self._config(hud, "hud_turn", text=f"Time {game.run_ms / 1000:.1f} s")
            self._config(hud, "hud_status", text=reaper_line(dist, color=False), fill=danger_colour(dist))

    def _build_hud(self, playing):
        hud, game = self.hud, self.game
        hud.delete("all")
        w = self.width + 2 * BORDER
        hud.create_line(0, 1, w, 1, fill="#6b4a8a", width=2, tags="hud")
        hud.create_rectangle(5, 6, w - 6, HUD_HEIGHT - 5, outline=HUD_EDGE, tags="hud")
        hud.create_text(w - 16, 22, anchor="e", text=CONTROLS, fill="#7c7c94", font=(FONT, 10), tags="hud")
        if not playing:
            return
        self._draw_hearts(hud, 24, 30, HEART_GAP, HEART_SIZES[1], "heart", "heart_lost", "hud", anchor="w")
        text_x = 24 + HEART_GAP * MAX_LIVES
        hud.create_text(text_x, 19, anchor="w", text="", fill="#d0d0e0", font=(FONT, 13, "bold"),
                        tags=("hud", "hud_turn"))
        hud.create_text(text_x, 42, anchor="w", text="", fill=GREY, font=(FONT, 13, "bold"),
                        tags=("hud", "hud_status"))
        if self.message:  # bump and jump messages, right under the controls line
            hud.create_text(w - 16, 46, anchor="e", text=self.message, fill=GREY, font=(FONT, 12, "italic"),
                            tags=("hud", "hud_message"))
        y = 70
        for sign in game.signs_here():
            colour = RED if sign.kind == WARNING else GREEN
            icon = "⚠" if sign.kind == WARNING else "✔"
            item = hud.create_text(w / 2, y, text=f'{icon}  Painted on a signpost: "{sign.text}"',
                                   fill=colour, font=(FONT, 16, "bold"), tags=("hud", "sign_banner"))
            size = 16
            while size > 10:  # shrink long signs until they fit the window
                x0, _, x1, _ = hud.bbox(item)
                if x1 - x0 <= w - 20:
                    break
                size -= 1
                hud.itemconfigure(item, font=(FONT, size, "bold"))
            return
        hud.create_text(w / 2, y, text="Follow the gravel path to the gate. Don't stop.",
                        fill="#6c6c84", font=(FONT, 11, "italic"), tags=("hud", "hud_hint"))

    def _draw_hearts(self, cv, x, y, gap, size, full_tag, lost_tag, layer, anchor="center"):
        """R5: one red heart per life left, then grey empty hearts for the lives lost."""
        for i in range(MAX_LIVES):
            alive = i < self.game.lives
            cv.create_text(x + i * gap, y, anchor=anchor, text="♥" if alive else "♡",
                           fill=RED if alive else HEART_LOST, font=(FONT, size, "bold"),
                           tags=(layer, full_tag if alive else lost_tag))

    def _draw_big_hearts(self, y):
        gap = 90
        self._draw_hearts(self.canvas, self.width / 2 - gap, y, gap, 40, "big_heart", "big_heart_lost", "overlay")

    # --- the screens: drawn over the graveyard (R1, R3, R4, R11) ---
    def _shade_screen(self, moon: str = "#e8e2c8"):
        """R11: a night backdrop for the title and ending screens: sky, a big moon behind bare branches,
        gravestones in drifting mist."""
        cv = self.canvas
        h = self.map_height
        w = self.width
        for i, colour in enumerate(("#07050c", "#0b0814", "#100b1c", "#160f24")):  # sky, darker at the top
            cv.create_rectangle(0, i * h / 6, w, h, fill=colour, outline="", tags="overlay")
        mx, my = w - 130, 105
        cv.create_oval(mx - 90, my - 90, mx + 90, my + 90, fill=shade(moon, 0.22), outline="",
                       tags="overlay")  # halo
        cv.create_oval(mx - 66, my - 66, mx + 66, my + 66, fill=moon, outline="", tags="overlay")
        for (ox, oy, rr) in ((-25, -20, 14), (20, 15, 10), (-10, 30, 7)):  # craters
            cv.create_oval(mx + ox - rr, my + oy - rr, mx + ox + rr, my + oy + rr, fill=shade(moon, 0.86),
                           outline="", tags="overlay")
        tree = "#05030a"  # a bare tree across the moon
        cv.create_polygon(w - 40, h, w - 28, 120, w - 18, h, fill=tree, outline="", tags="overlay")
        for (ax, ay, bx, by, wd) in ((-32, 200, -120, 90, 6), (-120, 90, -170, 70, 3), (-90, 120, -95, 40, 3),
                                     (-28, 150, -60, 20, 4), (-60, 20, -40, -10, 2), (-150, 75, -200, 95, 2)):
            cv.create_line(w + ax, ay, w + bx, by, fill=tree, width=wd, capstyle="round", tags="overlay")
        cv.create_rectangle(0, h - 95, w, h, fill="#141019", outline="", tags="overlay")
        for x in range(40, int(w), 150):  # gravestones
            cv.create_rectangle(x, h - 125, x + 34, h - 87, fill="#2b2833", outline="#3d3946", tags="overlay")
            cv.create_arc(x, h - 143, x + 34, h - 109, start=0, extent=180, fill="#2b2833",
                          outline="#3d3946", tags="overlay")
            cv.create_text(x + 17, h - 110, text="RIP", fill="#4a4656", font=(FONT, 8, "bold"), tags="overlay")
        for row in range(self.SCREEN_MIST):  # R11: wisps of low mist drift over the graves
            y = h - 128 + row * 14
            pts = []
            for k in range(26):
                pts += [-w + k * w / 12, y + 6 * math.sin(k * 1.3 + row * 2)]
            cv.create_line(*pts, fill=shade(MIST, 0.75 - 0.12 * row), width=2, smooth=True,
                           tags=("overlay", "mist", "screen_mist"))

    def _title(self, y, text, colour, size):
        """R11: a big title with a dark, blood-red drop shadow."""
        cv = self.canvas
        cv.create_text(self.width / 2 + 4, y + 4, text=text, fill="#2a0006", font=(TITLE_FONT, size),
                       tags="overlay")
        return cv.create_text(self.width / 2, y, text=text, fill=colour, font=(TITLE_FONT, size), tags="overlay")

    def _prompt(self, text):
        self.canvas.create_text(self.width / 2, self.map_height - 40, text=text, fill="#ffe066",
                                font=(FONT, 18, "bold"), tags=("overlay", "blink"))

    def _draw_intro(self):
        cv = self.canvas
        mid = self.width / 2
        self._shade_screen()
        self._title_lift = 0.0
        draw_reaper(cv, mid - 360, 330, 4.2, tag=("overlay", "title_reaper"), t=0)
        draw_player(cv, mid + 330, 350, 3.6, tag="overlay")
        title = self._title(62, "ESCAPE THE GRIM REAPER", RED, 44)
        cv.addtag_withtag("title", title)
        cv.create_text(mid, 235, text="You wake among the graves at midnight.\n"
                                      "Something breathes behind you. It will not wait.\n\n"
                                      "Hold an arrow key to run along the gravel path.\n"
                                      "Press ↑ to leap coffins, open graves and thorns.\n"
                                      "Read the signposts. Find the EXIT gate.\n"
                                      "Don't stop. Don't look back.",
                       fill="#e0e0ea", font=(FONT, 15), justify="center", tags="overlay")
        self._prompt("Press any key to begin")

    def _draw_caught(self):
        """R4 / R7: a life is lost to the reaper (CAUGHT!) or a hazard (HURT!); wait for R."""
        cv, game = self.canvas, self.game
        mid = self.width / 2
        self._shade_screen("#a8432f")
        by_reaper = game.hurt_by == "reaper"
        if by_reaper:
            draw_reaper(cv, mid, 400, 3.0, tag="overlay", t=self.ms)
        else:
            draw_player(cv, mid, 350, 4.4, tag="overlay")
        caught = self._title(62, "CAUGHT!" if by_reaper else "HURT!", ORANGE, 50)
        cv.addtag_withtag("caught_title", caught)
        left = f"{game.lives} {'life' if game.lives == 1 else 'lives'} left"
        cv.create_text(mid, 125, text=f"{LIFE_LOST[game.hurt_by or 'reaper']} ({left})",
                       fill="#e0e0ea", font=(FONT, 16), tags="overlay")
        self._draw_big_hearts(180)
        self._prompt("Press R to resume    Esc to quit")

    def _draw_ending(self):
        cv, game = self.canvas, self.game
        mid = self.width / 2
        self._shade_screen("#c0392b" if game.status is Status.LOST else "#e8e2c8")
        if game.status is Status.WON:
            draw_player(cv, mid, 330, 4.4, tag="overlay")
            title, colour = "YOU ESCAPED!", GREEN
            sub = f"You burst into the night air after {game.run_ms / 1000:.1f} seconds."
        elif game.status is Status.LOST:
            draw_reaper(cv, mid, 400, 3.0, tag="overlay", t=self.ms)
            self._draw_big_hearts(180)
            title, colour = "GAME OVER", RED
            sub = GAME_OVER[game.hurt_by or "reaper"]
        else:
            title, colour, sub = "YOU GAVE UP", GREY, "The Reaper is patient."
        ending = self._title(62, title, colour, 50)
        cv.addtag_withtag("ending_title", ending)
        cv.create_text(mid, 125, text=sub, fill="#e0e0ea", font=(FONT, 16), tags="overlay")
        self._prompt("Press R to play again    Esc to quit")


def run() -> int:
    root = tk.Tk()
    GameWindow(root)
    root.mainloop()
    return 0
