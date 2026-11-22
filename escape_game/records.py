"""R18: the best escape time, kept in a small JSON file in the player's home folder.

This is the only file the game writes. If it can't be read or written, the game carries on without it.
"""

import json
import pathlib

DEFAULT_PATH = pathlib.Path.home() / ".escape_grim_reaper.json"


class BestTime:
    """The fastest escape so far, in milliseconds. path=None keeps it only while the game is open."""

    def __init__(self, path: pathlib.Path | str | None = None):
        self.path = pathlib.Path(path) if path is not None else None
        self.best_ms: float | None = self._load()

    def record(self, ms: float) -> bool:
        """Note an escape that took ms; True if it is a new best (then it is saved)."""
        if self.best_ms is not None and ms >= self.best_ms:
            return False
        self.best_ms = ms
        self._save()
        return True

    def _load(self) -> float | None:
        if self.path is None:
            return None
        try:
            best = float(json.loads(self.path.read_text(encoding="utf-8"))["best_ms"])
        except (OSError, ValueError, KeyError, TypeError):
            return None  # no file yet, or one we can't make sense of: start afresh
        return best if best > 0 else None

    def _save(self) -> None:
        if self.path is None:
            return
        try:
            self.path.write_text(json.dumps({"best_ms": round(self.best_ms)}), encoding="utf-8")
        except OSError:
            pass  # a read-only home folder must not stop the game
