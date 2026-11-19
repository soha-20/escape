"""Heartbeat and end-of-game sounds that build tension during the chase.

A tone is (frequency_hz, duration_ms); frequency 0 means silence for that long.
The beep and sleep functions are injectable so tests never make real noise.
"""

import sys
import time
from typing import Callable

Tone = tuple[int, int]

FAR, NEAR = 6, 3  # distance thresholds (shortest-path steps)


def heartbeat_tones(distance: int) -> list[Tone]:
    """Slow and low when the reaper is far; fast, high and triple when it is close."""
    if distance >= FAR:
        return [(150, 180)]
    if distance > NEAR:
        return [(180, 140), (0, 90), (180, 140)]
    return [(260, 90), (0, 50), (260, 90), (0, 50), (300, 120)]


CAUGHT_TONES: list[Tone] = [(400, 200), (300, 200), (200, 250), (100, 600)]
ESCAPED_TONES: list[Tone] = [(523, 150), (659, 150), (784, 150), (1047, 400)]


def _default_beep() -> Callable[[int, int], None]:
    try:
        import winsound
        return winsound.Beep
    except ImportError:
        def bell(_freq: int, _ms: int) -> None:
            sys.stdout.write("\a")
            sys.stdout.flush()
        return bell


class Sound:
    def __init__(self, enabled: bool = True,
                 beep: Callable[[int, int], None] | None = None,
                 sleep: Callable[[float], None] = time.sleep):
        self.enabled = enabled
        self._beep = beep if beep is not None else (_default_beep() if enabled else None)
        self._sleep = sleep

    def play(self, tones: list[Tone]) -> None:
        if not self.enabled:
            return
        try:
            for freq, ms in tones:
                if freq <= 0:
                    self._sleep(ms / 1000)
                else:
                    self._beep(max(37, freq), ms)  # 37 Hz is winsound's minimum
        except Exception:
            self.enabled = False  # no sound device etc.: keep playing silently

    def heartbeat(self, distance: int) -> None:
        self.play(heartbeat_tones(distance))

    def caught(self) -> None:
        self.play(CAUGHT_TONES)

    def escaped(self) -> None:
        self.play(ESCAPED_TONES)
