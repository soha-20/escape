"""Tests for the chase sounds (part of R1: the tension of being chased)."""

from escape_game.sound import CAUGHT_TONES, ESCAPED_TONES, Sound, heartbeat_tones


class Recorder:
    def __init__(self):
        self.beeps, self.sleeps = [], []

    def beep(self, freq, ms):
        self.beeps.append((freq, ms))

    def sleep(self, seconds):
        self.sleeps.append(seconds)


def beats(tones):
    return [t for t in tones if t[0] > 0]


def test_R1_heartbeat_gets_faster_and_higher_as_reaper_closes_in():
    """R1: one slow beat when far, two when nearer, three fast high beats when close."""
    far, mid, near = heartbeat_tones(8), heartbeat_tones(5), heartbeat_tones(2)
    assert [len(beats(t)) for t in (far, mid, near)] == [1, 2, 3]
    assert max(f for f, _ in beats(far)) < max(f for f, _ in beats(mid)) < max(f for f, _ in beats(near))


def test_R1_heartbeat_thresholds():
    """R1: the boundaries are 6+ far, 4-5 medium, 3 or fewer close."""
    assert heartbeat_tones(6) == heartbeat_tones(100)
    assert heartbeat_tones(4) == heartbeat_tones(5) != heartbeat_tones(6)
    assert heartbeat_tones(3) == heartbeat_tones(0) != heartbeat_tones(4)


def test_R1_sound_plays_beeps_and_pauses_through_injected_functions():
    """R1: tones go to the beep function; silences become sleeps."""
    rec = Recorder()
    Sound(beep=rec.beep, sleep=rec.sleep).heartbeat(5)
    assert rec.beeps == [(180, 140), (180, 140)]
    assert rec.sleeps == [0.09]


def test_R1_caught_and_escaped_sounds():
    """R1/R3: a falling tone on capture, a rising tone on escape."""
    rec = Recorder()
    sound = Sound(beep=rec.beep, sleep=rec.sleep)
    sound.caught()
    sound.escaped()
    assert rec.beeps == CAUGHT_TONES + ESCAPED_TONES
    assert [f for f, _ in CAUGHT_TONES] == sorted((f for f, _ in CAUGHT_TONES), reverse=True)
    assert [f for f, _ in ESCAPED_TONES] == sorted(f for f, _ in ESCAPED_TONES)


def test_R1_mute_makes_no_sound():
    """R1: --mute turns all sound off."""
    rec = Recorder()
    sound = Sound(enabled=False, beep=rec.beep, sleep=rec.sleep)
    sound.heartbeat(1)
    sound.caught()
    assert rec.beeps == [] and rec.sleeps == []


def test_R1_sound_failure_does_not_crash_the_game():
    """R1: if the sound device fails, the game carries on silently."""
    calls = []

    def broken(freq, ms):
        calls.append(freq)
        raise RuntimeError("no sound device")

    sound = Sound(beep=broken, sleep=lambda s: None)
    sound.heartbeat(1)
    sound.heartbeat(1)
    assert len(calls) == 1 and sound.enabled is False
