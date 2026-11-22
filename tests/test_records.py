"""R18: the best escape time is kept, so there is a reason to play again."""

import pathlib

from escape_game.records import DEFAULT_PATH, BestTime


def test_R18_the_best_time_starts_empty_and_keeps_the_fastest(tmp_path):
    """R18: with no file yet there is no best; a first escape sets it; only a faster one replaces it."""
    best = BestTime(tmp_path / "best.json")
    assert best.best_ms is None
    assert best.record(16_400) is True and best.best_ms == 16_400
    assert best.record(17_000) is False and best.best_ms == 16_400
    assert best.record(15_600) is True and best.best_ms == 15_600


def test_R18_the_best_time_survives_closing_the_game(tmp_path):
    """R18: the best time is saved to its file and read back by the next game."""
    path = tmp_path / "best.json"
    BestTime(path).record(15_600)
    assert BestTime(path).best_ms == 15_600


def test_R18_a_broken_or_unwritable_file_does_not_stop_the_game(tmp_path):
    """R18: nonsense in the file is ignored, and a file that can't be written is skipped quietly."""
    path = tmp_path / "best.json"
    path.write_text("not json", encoding="utf-8")
    assert BestTime(path).best_ms is None
    path.write_text('{"best_ms": -5}', encoding="utf-8")
    assert BestTime(path).best_ms is None
    folder = tmp_path / "a_folder"
    folder.mkdir()
    best = BestTime(folder)  # a folder, not a file: reading and writing both fail
    assert best.best_ms is None and best.record(15_000) is True and best.best_ms == 15_000


def test_R18_without_a_file_the_best_is_kept_only_while_the_game_is_open(tmp_path, monkeypatch):
    """R18: BestTime(None) remembers in memory and writes nothing."""
    monkeypatch.chdir(tmp_path)
    best = BestTime(None)
    assert best.record(15_000) and best.best_ms == 15_000
    assert list(tmp_path.iterdir()) == []


def test_R18_the_file_lives_in_the_home_folder():
    """R18: the default place is a small hidden file in the player's home folder."""
    assert DEFAULT_PATH == pathlib.Path.home() / ".escape_grim_reaper.json"
