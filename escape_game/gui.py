"""Graphical game window (tkinter): drawn figures, torch light, glowing signs.

The rules all live in game.py; this module only draws the game and turns key presses into moves.
"""

import math
import queue
import threading
import tkinter as tk

from .game import MAX_LIVES, Game, Outcome, Status
from .maze import WARNING
from .render import GAME_OVER, LIFE_LOST, bump_line, reaper_line
from .sound import Sound

TILE = 52            # pixels per maze tile
VIEW_COLS, VIEW_ROWS = 15, 9   # the camera shows this many tiles, centred on the player
SCALE = TILE / 40    # figures are designed on a 40-pixel tile
HUD_HEIGHT = 150
TICK_MS = 60
HEART_SIZES = (30, 25)   # HUD heart font size: beat, rest
HEART_GAP = 40           # pixels between HUD hearts

KEY_DIRECTIONS = {
    "Up": "up", "w": "up", "W": "up",
    "Down": "down", "s": "down", "S": "down",
    "Left": "left", "a": "left", "A": "left",
    "Right": "right", "d": "right", "D": "right",
}

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
IRON = "#1a1a20"         # fences and the gate
BARK = "#5a4030"         # dead trees and signposts
THORN = "#c23a4a"        # R7: thorn bushes, bright enough to stand out on the grass
THORN_TIP = "#ffb3b3"
PLANK = "#e0cf9f"
RED = "#ff3b3b"
GREEN = "#3ddc84"
DOOR = "#7a4a26"
HUD_BG = "#0d0b12"
GREY = "#9a9aa8"
ORANGE = "#ff9f43"
HEART_LOST = "#5c5668"   # R5: grey empty heart for a lost life

FONT = "Segoe UI"
TITLE_FONT = "Impact"  # Tk falls back to a default font if it is missing


# --- pure helpers (tested without a window) --------------------------------

def shade(colour: str, factor: float) -> str:
    """Darken a #rrggbb colour by factor (0 = black, 1 = unchanged)."""
    factor = max(0.0, min(1.0, factor))
    r, g, b = (int(colour[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % (int(r * factor), int(g * factor), int(b * factor))


MOONLIGHT = 0.8     # R9: every tile in view is at least this bright
TORCH_REACH = 3.5   # tiles; the torch glow fades to nothing at this distance


def torch_glow(centre, pos) -> float:
    """R9: how strongly the torch warms a tile: 1 under the player, fading to 0 at TORCH_REACH."""
    dist = math.hypot(pos[0] - centre[0], pos[1] - centre[1])
    return max(0.0, 1.0 - dist / TORCH_REACH)


def light_level(game: Game, pos) -> float:
    """R9: moonlight everywhere, a little brighter near the torch. Never dark."""
    return MOONLIGHT + (1 - MOONLIGHT) * torch_glow(game.player, pos)


def in_view(origin, pos) -> bool:
    """True if pos lies inside the camera view whose top-left tile is origin."""
    return origin[0] <= pos[0] < origin[0] + VIEW_ROWS and origin[1] <= pos[1] < origin[1] + VIEW_COLS


def heartbeat_period_ms(distance: int) -> int:
    """The on-screen heart beats faster as the reaper closes in."""
    if distance >= 6:
        return 1200
    if distance > 3:
        return 800
    return 450


def camera_origin(game: Game) -> tuple[int, int]:
    """Top-left tile of the camera view: centred on the player, kept inside the maze."""
    maze = game.maze
    top = min(max(game.player[0] - VIEW_ROWS // 2, 0), max(maze.height - VIEW_ROWS, 0))
    left = min(max(game.player[1] - VIEW_COLS // 2, 0), max(maze.width - VIEW_COLS, 0))
    return top, left


def danger_colour(distance: int) -> str:
    if distance >= 6:
        return GREY
    if distance > 3:
        return ORANGE
    return RED


# --- figures ---------------------------------------------------------------

def draw_player(cv: tk.Canvas, cx: float, cy: float, s: float = 1.0, tag: str = "player") -> None:
    """A small adventurer in a blue tunic holding a burning torch."""
    def p(dx, dy):
        return cx + dx * s, cy + dy * s
    w = max(1, round(3 * s))
    cv.create_line(*p(-4, 8), *p(-6, 17), fill="#2c3e50", width=w, capstyle="round", tags=tag)
    cv.create_line(*p(4, 8), *p(6, 17), fill="#2c3e50", width=w, capstyle="round", tags=tag)
    cv.create_line(*p(-7, -2), *p(-12, 6), fill="#f5cba7", width=w, capstyle="round", tags=tag)
    cv.create_polygon(*p(-7, -5), *p(7, -5), *p(9, 10), *p(-9, 10),
                      fill="#2e86de", outline="#1b4f8a", width=max(1, s), tags=tag)
    cv.create_line(*p(-8, 6), *p(8, 6), fill="#8b5a2b", width=w, tags=tag)  # belt
    cv.create_oval(*p(-6, -17), *p(6, -5), fill="#f5cba7", outline="#a0522d", width=max(1, s), tags=tag)
    cv.create_arc(*p(-6, -18), *p(6, -8), start=0, extent=180, fill="#5d3a1a", outline="", tags=tag)
    cv.create_oval(*p(-3, -12), *p(-1.5, -10.5), fill=BLACK, outline="", tags=tag)
    cv.create_oval(*p(1.5, -12), *p(3, -10.5), fill=BLACK, outline="", tags=tag)
    # torch arm, stick and flame
    cv.create_line(*p(7, -2), *p(13, -5), fill="#f5cba7", width=w, capstyle="round", tags=tag)
    cv.create_line(*p(13, -3), *p(15, -14), fill="#6d4c2f", width=w, tags=tag)
    cv.create_oval(*p(10, -24), *p(20, -12), fill="#ff7b00", outline="", tags=(tag, "flame"))
    cv.create_oval(*p(12.5, -20), *p(17.5, -13), fill="#ffe066", outline="", tags=(tag, "flame"))


def draw_reaper(cv: tk.Canvas, cx: float, cy: float, s: float = 1.0, tag: str = "reaper") -> None:
    """The Grim Reaper: black hooded cloak, skull face, glowing red eyes and a scythe."""
    def p(dx, dy):
        return cx + dx * s, cy + dy * s
    cv.create_line(*p(13, -20), *p(8, 19), fill="#8b5a2b", width=max(1, round(3 * s)), tags=tag)
    cv.create_polygon(*p(13, -20), *p(2, -25), *p(-12, -21), *p(-17, -14), *p(-6, -18), *p(12, -15),
                      fill="#d5dde2", outline="#7f8c95", width=max(1, s), smooth=True, tags=tag)
    cv.create_polygon(*p(0, -19), *p(9, -10), *p(11, 4), *p(13, 19), *p(7, 15), *p(3, 20), *p(-2, 15),
                      *p(-7, 20), *p(-13, 19), *p(-11, 4), *p(-9, -10),
                      fill="#141018", outline="#5b3a70", width=max(1, s), tags=tag)
    cv.create_oval(*p(-6.5, -15), *p(6.5, -1), fill=BLACK, outline="", tags=tag)
    cv.create_oval(*p(-4.5, -13), *p(4.5, -3), fill="#ece6d6", outline="", tags=tag)
    cv.create_oval(*p(-3.5, -10.5), *p(-1, -8), fill=RED, outline="", tags=(tag, "reaper_eyes"))
    cv.create_oval(*p(1, -10.5), *p(3.5, -8), fill=RED, outline="", tags=(tag, "reaper_eyes"))
    cv.create_polygon(*p(0, -7.5), *p(-1, -5.8), *p(1, -5.8), fill="#3a3a3a", outline="", tags=tag)  # nose
    cv.create_rectangle(*p(-2.5, -5), *p(2.5, -3.6), fill="#ece6d6", outline="#555", tags=tag)  # teeth
    for tx in (-0.8, 0.8):
        cv.create_line(*p(tx, -5), *p(tx, -3.6), fill="#555", tags=tag)
    for fx in (-4, 4):  # cloak folds
        cv.create_line(*p(fx * 0.6, 2), *p(fx, 16), fill="#2c2234", width=max(1, s), tags=tag)
    cv.create_oval(*p(6, 1), *p(11, 5), fill="#ece6d6", outline="", tags=tag)  # bony hand on the scythe


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


class GameWindow:
    INTRO, PLAYING, CAUGHT, OVER = "intro", "playing", "caught", "over"

    def __init__(self, root: tk.Tk, sound=None, threaded_sound: bool = True):
        self.root = root
        sound = sound if sound is not None else Sound()
        self.sound = SoundWorker(sound) if threaded_sound else sound
        self.game = Game()
        self.width = VIEW_COLS * TILE
        self.map_height = VIEW_ROWS * TILE
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
        self.redraw()
        self._after = root.after(TICK_MS, self._tick)

    # --- input ---
    def on_key(self, keysym: str) -> None:
        if keysym == "Escape":
            self.close()
            return
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
                self.state = self.PLAYING
                self.message = ""
                self.redraw()
                self.sound.heartbeat(self.game.reaper_distance())
            return
        direction = KEY_DIRECTIONS.get(keysym)
        if direction is None:
            return
        outcome = self.game.move(direction)
        self.message = bump_line(self.game.bumped) if outcome is Outcome.WALL else ""
        if self.game.status is Status.CAUGHT:
            self.state = self.CAUGHT
        elif self.game.status is not Status.PLAYING:
            self.state = self.OVER
        self.redraw()
        if outcome is Outcome.MOVED:
            if self.game.status is Status.PLAYING:
                self.sound.heartbeat(self.game.reaper_distance())
            elif self.game.status is Status.CAUGHT:
                self.sound.life_lost()
            elif self.game.status is Status.LOST:
                self.sound.caught()
            elif self.game.status is Status.WON:
                self.sound.escaped()

    # --- drawing ---
    def redraw(self) -> None:
        cv = self.canvas
        cv.delete("all")
        self.origin = camera_origin(self.game)
        self._draw_graveyard()
        game = self.game
        self._draw_sprite(game.player, draw_player)
        if in_view(self.origin, game.reaper):  # R9: no fog; the reaper is seen wherever it is on screen
            self._draw_sprite(game.reaper, draw_reaper)
        self._draw_danger_border()
        self._draw_hud()
        if self.state == self.INTRO:
            self._draw_intro()
        elif self.state == self.CAUGHT:
            self._draw_caught()
        elif self.state == self.OVER:
            self._draw_ending()

    def _xy(self, pos):
        """Top-left pixel of a maze tile inside the camera view."""
        return (pos[1] - self.origin[1]) * TILE, (pos[0] - self.origin[0]) * TILE

    def _draw_sprite(self, pos, painter):
        x, y = self._xy(pos)
        painter(self.canvas, x + TILE / 2, y + TILE / 2, SCALE)

    def _draw_graveyard(self):
        """R6: grass everywhere, then whatever stands or lies on each tile (all moonlit since R9)."""
        maze = self.game.maze
        top, left = self.origin
        for r in range(top, min(top + VIEW_ROWS, maze.height)):
            for c in range(left, min(left + VIEW_COLS, maze.width)):
                light = light_level(self.game, (r, c))
                pos = (r, c)
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
                elif pos == maze.exit:
                    self._draw_exit(x0, y0, light)

    def _draw_grass(self, x0, y0, light, r, c):
        cv = self.canvas
        variation = 0.88 + 0.12 * ((r * 31 + c * 17) % 3) / 2
        cv.create_rectangle(x0, y0, x0 + TILE, y0 + TILE, fill=shade(GRASS, light * variation),
                            outline=shade(GRASS_DARK, light), tags=("grass", "floor"))
        blade = shade(GRASS_BLADE, light)
        for i, (gx, gy) in enumerate(((10, 40), (30, 16), (40, 34))):  # a few tufts
            gx += (r * 5 + c * 11 + i * 7) % 9
            cv.create_line(x0 + gx, y0 + gy, x0 + gx - 2, y0 + gy - 6, fill=blade, tags="grass")
            cv.create_line(x0 + gx, y0 + gy, x0 + gx + 2, y0 + gy - 7, fill=blade, tags="grass")

    def _draw_fence(self, x0, y0, light):
        """Iron railings: two rails and four bars with spear tips."""
        cv = self.canvas
        iron = shade(IRON, max(light, 0.5))
        tags = ("fence", "obstacle")
        for y in (y0 + 18, y0 + 40):
            cv.create_line(x0, y, x0 + TILE, y, fill=iron, width=3, tags=tags)
        for i in range(4):
            x = x0 + 6.5 + i * 13
            cv.create_line(x, y0 + 12, x, y0 + TILE - 4, fill=iron, width=3, tags=tags)
            cv.create_polygon(x - 4, y0 + 13, x, y0 + 4, x + 4, y0 + 13, fill=iron, outline="", tags=tags)

    def _draw_gravestone(self, x0, y0, light, style):
        """A rounded headstone with a cross, on a little mound of earth."""
        cv = self.canvas
        tags = ("grave", "obstacle")
        stone, edge = shade(STONE, light), shade(STONE_DARK, light)
        cx = x0 + TILE / 2
        cv.create_oval(x0 + 8, y0 + TILE - 14, x0 + TILE - 8, y0 + TILE - 2, fill=shade(DIRT, light),
                       outline="", tags=tags)
        half = (12, 14, 11)[style]
        cv.create_rectangle(cx - half, y0 + 18, cx + half, y0 + TILE - 8, fill=stone, outline=edge, tags=tags)
        cv.create_arc(cx - half, y0 + 6, cx + half, y0 + 30, start=0, extent=180, fill=stone, outline=edge,
                      style="chord", tags=tags)
        cv.create_rectangle(cx - half + 1, y0 + 17, cx + half - 1, y0 + 20, fill=stone, outline="", tags=tags)
        cv.create_line(cx, y0 + 15, cx, y0 + 33, fill=edge, width=3, tags=tags)
        cv.create_line(cx - 6, y0 + 21, cx + 6, y0 + 21, fill=edge, width=3, tags=tags)

    def _draw_tree(self, x0, y0, light, flip):
        """A dead tree: a crooked trunk and bare branches."""
        cv = self.canvas
        tags = ("tree", "obstacle")
        bark = shade(BARK, max(light, 0.45))
        s = -1 if flip else 1
        cx = x0 + TILE / 2
        cv.create_polygon(cx - 5, y0 + TILE - 3, cx - 2, y0 + 18, cx + 3, y0 + 18, cx + 6, y0 + TILE - 3,
                          fill=bark, outline="", tags=tags)
        for (ax, ay, bx, by, w) in ((0, 24, -16, 8, 3), (0, 20, 15, 4, 3), (-9, 14, -14, 2, 2),
                                    (8, 10, 18, 12, 2), (0, 18, 2, 2, 2)):
            cv.create_line(cx + s * ax, y0 + ay, cx + s * bx, y0 + by, fill=bark, width=w,
                           capstyle="round", tags=tags)

    def _draw_signpost(self, x0, y0, light, kind):
        """R2: a wooden post with a glowing plaque."""
        cv = self.canvas
        glow = RED if kind == WARNING else GREEN
        tags = ("sign", f"sign_{kind}", "obstacle")
        cx = x0 + TILE / 2
        cv.create_rectangle(cx - 3, y0 + 24, cx + 3, y0 + TILE - 2, fill=shade(BARK, max(light, 0.5)),
                            outline="", tags=tags)
        cv.create_rectangle(x0 + 4, y0 + 5, x0 + TILE - 4, y0 + 30, fill=shade(PLANK, light),
                            outline=shade(glow, light), width=3, tags=tags)
        cv.create_text(cx, y0 + 18, text="!", fill=shade(glow, light), font=(FONT, 16, "bold"), tags=tags)

    def _draw_open_grave(self, x0, y0, light):
        """R7: a freshly dug pit with the earth heaped behind it."""
        cv = self.canvas
        tags = ("hazard", "open_grave")
        cv.create_oval(x0 + 6, y0 + 2, x0 + TILE - 6, y0 + 20, fill=shade(DIRT, light),
                       outline=shade(DIRT_DARK, light), tags=tags)
        cv.create_rectangle(x0 + 11, y0 + 13, x0 + TILE - 11, y0 + TILE - 4, fill=shade(DIRT_DARK, light),
                            outline=shade(DIRT, light), width=2, tags=tags)
        cv.create_rectangle(x0 + 15, y0 + 17, x0 + TILE - 15, y0 + TILE - 8, fill=PIT, outline="", tags=tags)

    def _draw_thorns(self, x0, y0, light):
        """R7: a tangle of dark red, spiky branches."""
        cv = self.canvas
        tags = ("hazard", "thorn_bush")
        stem, spike = shade(THORN, max(light, 0.4)), shade(THORN_TIP, max(light, 0.4))
        for (ax, ay, bx, by) in ((6, 44, 46, 10), (6, 12, 46, 42), (26, 4, 26, 48), (4, 28, 48, 26)):
            cv.create_line(x0 + ax, y0 + ay, x0 + bx, y0 + by, fill=stem, width=3, tags=tags)
            for t in (0.25, 0.5, 0.75):  # thorns along each branch
                px, py = x0 + ax + (bx - ax) * t, y0 + ay + (by - ay) * t
                cv.create_line(px - 4, py - 4, px + 4, py + 4, fill=spike, width=1, tags=tags)
                cv.create_line(px - 4, py + 4, px + 4, py - 4, fill=spike, width=1, tags=tags)

    def _draw_exit(self, x0, y0, light):
        """The way out: an iron cemetery gate in a green glow."""
        cv = self.canvas
        k = SCALE
        cx = x0 + TILE / 2
        iron = shade(IRON, max(light, 0.6))
        cv.create_oval(x0 + 1, y0 + 1, x0 + TILE - 1, y0 + TILE - 1, fill=shade("#1e6b3a", light),
                       outline=shade(GREEN, light), width=2, tags="exit")
        for side in (-1, 1):  # stone posts
            cv.create_rectangle(cx + side * 14 * k - 3, y0 + 8, cx + side * 14 * k + 3, y0 + TILE - 3,
                                fill=shade(STONE, light), outline="", tags="exit")
        cv.create_arc(cx - 11 * k, y0 + 6 * k, cx + 11 * k, y0 + 22 * k, start=0, extent=180, style="arc",
                      outline=iron, width=2, tags="exit")
        for i in range(5):
            x = cx - 10 * k + i * 5 * k
            cv.create_line(x, y0 + 13 * k, x, y0 + TILE - 4, fill=iron, width=2, tags="exit")
        cv.create_text(cx, y0 + 26 * k, text="EXIT", fill=shade("#b8ffcf", light), font=(FONT, 8, "bold"),
                       tags="exit")

    def _draw_danger_border(self):
        if self.state == self.PLAYING and self.game.reaper_distance() <= 3:
            self.canvas.create_rectangle(3, 3, self.width - 3, self.map_height - 3,
                                         outline=RED, width=6, tags="danger")

    def _draw_hud(self):
        cv, game = self.canvas, self.game
        top = self.map_height
        cv.create_rectangle(0, top, self.width, top + HUD_HEIGHT, fill=HUD_BG, outline="#2a2235", tags="hud")
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
        cv.create_text(self.width - 12, top + HUD_HEIGHT - 14, anchor="e",
                       text="Arrow keys / WASD to move    Esc to quit", fill="#6c6c80",
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
        """A night backdrop for the title and ending screens: dark sky, moon, graveyard ground."""
        cv = self.canvas
        h = self.map_height + HUD_HEIGHT
        cv.create_rectangle(0, 0, self.width, h, fill="#07050c", outline="", tags="overlay")
        cv.create_oval(self.width - 82, 14, self.width - 18, 78, fill=moon, outline="", tags="overlay")
        cv.create_oval(self.width - 70, 26, self.width - 56, 40, fill=shade(moon, 0.85), outline="",
                       tags="overlay")
        cv.create_rectangle(0, h - 120, self.width, h, fill="#141019", outline="", tags="overlay")
        for x in range(40, int(self.width), 150):  # gravestones
            cv.create_rectangle(x, h - 150, x + 34, h - 112, fill="#2b2833", outline="#3d3946", tags="overlay")
            cv.create_arc(x, h - 168, x + 34, h - 134, start=0, extent=180, fill="#2b2833",
                          outline="#3d3946", tags="overlay")
            cv.create_text(x + 17, h - 135, text="RIP", fill="#4a4656", font=(FONT, 8, "bold"), tags="overlay")

    def _draw_intro(self):
        cv = self.canvas
        mid = self.width / 2
        self._shade_screen()
        draw_reaper(cv, mid - 250, 300, 5, tag="overlay")
        draw_player(cv, mid + 250, 310, 4, tag="overlay")
        cv.create_text(mid, 80, text="ESCAPE THE GRIM REAPER", fill=RED,
                       font=(TITLE_FONT, 44), tags=("overlay", "title"))
        cv.create_text(mid, 250, text="You wake among the graves at midnight.\n"
                                      "Something breathes behind you.\n\n"
                                      "Read the signposts.\nMind the open graves and thorns.\n"
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
            draw_reaper(cv, mid, 375, 5, tag="overlay")
        else:
            draw_player(cv, mid, 385, 5, tag="overlay")
        cv.create_text(mid, 75, text="CAUGHT!" if by_reaper else "HURT!", fill=ORANGE, font=(TITLE_FONT, 54),
                       tags=("overlay", "caught_title"))
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
            draw_player(cv, mid, 330, 5, tag="overlay")
            title, colour = "YOU ESCAPED!", GREEN
            sub = f"You burst into the night air after {game.turn} turns."
        elif game.status is Status.LOST:
            draw_reaper(cv, mid, 375, 5, tag="overlay")
            self._draw_big_hearts(205)
            title, colour = "GAME OVER", RED
            sub = GAME_OVER[game.hurt_by or "reaper"]
        else:
            title, colour, sub = "YOU GAVE UP", GREY, "The Reaper is patient."
        cv.create_text(mid, 75, text=title, fill=colour, font=(TITLE_FONT, 54),
                       tags=("overlay", "ending_title"))
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
    def _tick(self):
        self.ticks += 1
        t = self.ticks * TICK_MS
        cv = self.canvas
        flicker = 0.75 + 0.25 * math.sin(t / 70.0) * math.sin(t / 23.0)
        cv.itemconfigure("flame", fill=shade("#ff9f1a", 0.7 + 0.3 * flicker))
        glow = 0.55 + 0.45 * abs(math.sin(t / 300.0))
        cv.itemconfigure("reaper_eyes", fill=shade(RED, glow))
        period = heartbeat_period_ms(self.game.reaper_distance())
        phase = (t % period) / period
        size = HEART_SIZES[0] if phase < 0.12 or 0.22 < phase < 0.3 else HEART_SIZES[1]
        cv.itemconfigure("heart", font=(FONT, size, "bold"))
        cv.itemconfigure("danger", state="normal" if (t // 300) % 2 == 0 else "hidden")
        cv.itemconfigure("blink", state="normal" if (t // 600) % 2 == 0 else "hidden")
        self._after = self.root.after(TICK_MS, self._tick)


def run(mute: bool = False) -> int:
    root = tk.Tk()
    GameWindow(root, Sound(enabled=not mute))
    root.mainloop()
    return 0
