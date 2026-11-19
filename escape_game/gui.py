"""Graphical game window (tkinter): drawn figures, torch light, glowing signs.

The rules all live in game.py; this module only draws the game and turns key presses into moves.
"""

import math
import queue
import threading
import tkinter as tk

from .game import Game, Outcome, Status
from .maze import WARNING
from .render import reaper_line
from .sound import Sound

TILE = 52            # pixels per maze tile
VIEW_COLS, VIEW_ROWS = 15, 9   # the camera shows this many tiles, centred on the player
SCALE = TILE / 40    # figures are designed on a 40-pixel tile
HUD_HEIGHT = 150
TICK_MS = 60

KEY_DIRECTIONS = {
    "Up": "up", "w": "up", "W": "up",
    "Down": "down", "s": "down", "S": "down",
    "Left": "left", "a": "left", "A": "left",
    "Right": "right", "d": "right", "D": "right",
}

# palette
BLACK = "#000000"
FLOOR = "#7a6450"
FLOOR_LINE = "#4a3a2c"
WALL = "#7d8396"
MORTAR = "#30333c"
PLANK = "#e0cf9f"
RED = "#ff3b3b"
GREEN = "#3ddc84"
DOOR = "#7a4a26"
HUD_BG = "#0d0b12"
GREY = "#9a9aa8"
ORANGE = "#ff9f43"

FONT = "Segoe UI"
TITLE_FONT = "Impact"  # Tk falls back to a default font if it is missing


# --- pure helpers (tested without a window) --------------------------------

def shade(colour: str, factor: float) -> str:
    """Darken a #rrggbb colour by factor (0 = black, 1 = unchanged)."""
    factor = max(0.0, min(1.0, factor))
    r, g, b = (int(colour[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % (int(r * factor), int(g * factor), int(b * factor))


def light_level(game: Game, pos) -> float:
    """How brightly a tile is lit by the player's torch: 1 next to them, fading out; 0 if never seen."""
    if game.visible(pos):
        dist = math.hypot(pos[0] - game.player[0], pos[1] - game.player[1])
        return max(0.32, 1.0 - dist / 5.0)
    if pos in game.seen:
        return 0.16
    return 0.0


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


class GameWindow:
    INTRO, PLAYING, OVER = "intro", "playing", "over"

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
        self.message = "A cold stone wall blocks your way." if outcome is Outcome.WALL else ""
        if self.game.status is not Status.PLAYING:
            self.state = self.OVER
        self.redraw()
        if outcome is Outcome.MOVED:
            if self.game.status is Status.PLAYING:
                self.sound.heartbeat(self.game.reaper_distance())
            elif self.game.status is Status.LOST:
                self.sound.caught()
            elif self.game.status is Status.WON:
                self.sound.escaped()

    # --- drawing ---
    def redraw(self) -> None:
        cv = self.canvas
        cv.delete("all")
        self.origin = camera_origin(self.game)
        self._draw_maze()
        game = self.game
        self._draw_sprite(game.player, draw_player)
        if game.visible(game.reaper) or game.status is Status.LOST:
            self._draw_sprite(game.reaper, draw_reaper)
        self._draw_danger_border()
        self._draw_hud()
        if self.state == self.INTRO:
            self._draw_intro()
        elif self.state == self.OVER:
            self._draw_ending()

    def _xy(self, pos):
        """Top-left pixel of a maze tile inside the camera view."""
        return (pos[1] - self.origin[1]) * TILE, (pos[0] - self.origin[0]) * TILE

    def _draw_sprite(self, pos, painter):
        x, y = self._xy(pos)
        painter(self.canvas, x + TILE / 2, y + TILE / 2, SCALE)

    def _draw_maze(self):
        maze, cv = self.game.maze, self.canvas
        top, left = self.origin
        for r in range(top, min(top + VIEW_ROWS, maze.height)):
            for c in range(left, min(left + VIEW_COLS, maze.width)):
                light = light_level(self.game, (r, c))
                if light == 0:
                    continue
                x0, y0 = self._xy((r, c))
                x1, y1 = x0 + TILE, y0 + TILE
                pos = (r, c)
                if maze.is_wall(pos):
                    self._draw_wall(x0, y0, x1, y1, light, (r + c) % 2)
                    if pos in maze.signs:
                        self._draw_sign_plank(x0, y0, x1, y1, light, maze.signs[pos].kind)
                else:
                    variation = 0.9 + 0.1 * ((r * 31 + c * 17) % 3) / 2
                    cv.create_rectangle(x0, y0, x1, y1, fill=shade(FLOOR, light * variation),
                                        outline=shade(FLOOR_LINE, light), tags="floor")
                    if pos == maze.exit:
                        self._draw_exit(x0, y0, light)

    def _draw_wall(self, x0, y0, x1, y1, light, offset):
        cv = self.canvas
        cv.create_rectangle(x0, y0, x1, y1, fill=shade(WALL, light), outline=shade(MORTAR, light), tags="wall")
        mortar = shade(MORTAR, light)
        for i in range(1, 3):
            y = y0 + i * TILE / 3
            cv.create_line(x0, y, x1, y, fill=mortar, tags="wall")
        for row in range(3):
            shift = TILE / 4 if (row + offset) % 2 else TILE * 3 / 4
            ya, yb = y0 + row * TILE / 3, y0 + (row + 1) * TILE / 3
            cv.create_line(x0 + shift, ya, x0 + shift, yb, fill=mortar, tags="wall")

    def _draw_sign_plank(self, x0, y0, x1, y1, light, kind):
        cv = self.canvas
        glow = RED if kind == WARNING else GREEN
        cv.create_rectangle(x0 + 3, y0 + 6, x1 - 3, y1 - 6, fill=shade(PLANK, light),
                            outline=shade(glow, light), width=3, tags=("sign", f"sign_{kind}"))
        cv.create_text((x0 + x1) / 2, (y0 + y1) / 2, text="!", fill=shade(glow, light),
                       font=(FONT, 20, "bold"), tags=("sign", f"sign_{kind}"))

    def _draw_exit(self, x0, y0, light):
        cv = self.canvas
        k = SCALE
        cx = x0 + TILE / 2
        cv.create_oval(x0 + 1, y0 + 1, x0 + TILE - 1, y0 + TILE - 1, fill=shade("#1e6b3a", light),
                       outline=shade(GREEN, light), width=2, tags="exit")
        cv.create_rectangle(cx - 11 * k, y0 + 14 * k, cx + 11 * k, y0 + TILE - 2, fill=shade(DOOR, light),
                            outline=shade("#3b2412", light), width=2, tags="exit")
        cv.create_arc(cx - 11 * k, y0 + 3 * k, cx + 11 * k, y0 + 25 * k, start=0, extent=180,
                      fill=shade(DOOR, light), outline=shade("#3b2412", light), width=2, tags="exit")
        cv.create_oval(cx + 4 * k, y0 + 24 * k, cx + 8 * k, y0 + 28 * k, fill=shade("#ffd34d", light),
                       outline="", tags="exit")
        cv.create_text(cx, y0 + 18 * k, text="EXIT", fill=shade("#b8ffcf", light), font=(FONT, 8, "bold"),
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
        cv.create_text(50, top + 50, text="♥", fill=RED, font=(FONT, 40, "bold"), tags=("hud", "heart"))
        cv.create_text(95, top + 28, anchor="w", text=f"Turn {game.turn}", fill="#d0d0e0",
                       font=(FONT, 14, "bold"), tags=("hud", "hud_turn"))
        cv.create_text(95, top + 60, anchor="w", text=reaper_line(dist, color=False),
                       fill=danger_colour(dist), font=(FONT, 14, "bold"), tags=("hud", "hud_status"))
        y = top + 100
        for sign in game.signs_here():
            colour = RED if sign.kind == WARNING else GREEN
            icon = "⚠" if sign.kind == WARNING else "✔"
            cv.create_text(self.width / 2, y, text=f'{icon}  Scrawled on the wall: "{sign.text}"',
                           fill=colour, font=(FONT, 18, "bold"), tags=("hud", "sign_banner"))
            y += 30
        if self.message:
            cv.create_text(self.width / 2, top + 100, text=self.message, fill=GREY,
                           font=(FONT, 12, "italic"), tags=("hud", "hud_message"))
        cv.create_text(self.width - 12, top + HUD_HEIGHT - 14, anchor="e",
                       text="Arrow keys / WASD to move    Esc to quit", fill="#6c6c80",
                       font=(FONT, 10), tags="hud")

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
        cv.create_text(mid, 250, text="You wake on cold stone in the dark.\n"
                                      "Something breathes behind you.\n\n"
                                      "Read the signs on the walls.\nFind the EXIT. Don't look back.",
                       fill="#e0e0ea", font=(FONT, 15), justify="center", tags="overlay")
        cv.create_text(mid, self.map_height + 70, text="Press any key to begin", fill="#ffe066",
                       font=(FONT, 18, "bold"), tags=("overlay", "blink"))

    def _draw_ending(self):
        cv, game = self.canvas, self.game
        mid = self.width / 2
        self._shade_screen("#c0392b" if game.status is Status.LOST else "#e8e2c8")
        if game.status is Status.WON:
            draw_player(cv, mid, 330, 5, tag="overlay")
            title, colour = "YOU ESCAPED!", GREEN
            sub = f"You burst into the night air after {game.turn} turns."
        elif game.status is Status.LOST:
            draw_reaper(cv, mid, 330, 6, tag="overlay")
            title, colour = "GAME OVER", RED
            sub = "The Reaper's hand closes on your shoulder."
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
        size = 46 if phase < 0.12 or 0.22 < phase < 0.3 else 38
        cv.itemconfigure("heart", font=(FONT, size, "bold"))
        cv.itemconfigure("danger", state="normal" if (t // 300) % 2 == 0 else "hidden")
        cv.itemconfigure("blink", state="normal" if (t // 600) % 2 == 0 else "hidden")
        self._after = self.root.after(TICK_MS, self._tick)


def run(mute: bool = False) -> int:
    root = tk.Tk()
    GameWindow(root, Sound(enabled=not mute))
    root.mainloop()
    return 0
