"""Tests for adw.fs.atomic_write."""

import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from adw.fs import atomic_write


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


@pytest.fixture
def state_dir(tmp_path: Path) -> Path:
    """An empty directory: tmp_path also holds the isolated HOME."""
    d = tmp_path / "state"
    d.mkdir()
    return d


def test_atomic_write_creates_and_replaces(state_dir: Path) -> None:
    text_file = state_dir / "state.json"
    atomic_write(text_file, '{"a": 1}')
    assert text_file.read_text() == '{"a": 1}'

    atomic_write(text_file, "ünïcode")
    assert text_file.read_text(encoding="utf-8") == "ünïcode"

    binary_file = state_dir / "blob.bin"
    atomic_write(binary_file, b"\x00\x01")
    assert binary_file.read_bytes() == b"\x00\x01"


def test_failed_write_keeps_the_old_file_and_leaves_no_temp(state_dir: Path) -> None:
    target = state_dir / "state.json"
    target.write_text("old")

    with (
        patch("adw.fs.os.fsync", side_effect=OSError("disk full")),
        pytest.raises(OSError, match="disk full"),
    ):
        atomic_write(target, "new")

    assert target.read_text() == "old"
    assert list(state_dir.iterdir()) == [target]


def test_failed_replace_keeps_the_old_file_and_leaves_no_temp(state_dir: Path) -> None:
    target = state_dir / "state.json"
    target.write_text("old")

    with (
        patch("adw.fs.os.replace", side_effect=OSError("busy")),
        pytest.raises(OSError, match="busy"),
    ):
        atomic_write(target, "new")

    assert target.read_text() == "old"
    assert list(state_dir.iterdir()) == [target]


def test_keyboard_interrupt_mid_write_cleans_up(state_dir: Path) -> None:
    target = state_dir / "state.json"

    with (
        patch("adw.fs.os.fsync", side_effect=KeyboardInterrupt),
        pytest.raises(KeyboardInterrupt),
    ):
        atomic_write(target, "new")

    assert list(state_dir.iterdir()) == []


def test_atomic_write_keeps_the_existing_mode(state_dir: Path) -> None:
    target = state_dir / "state.json"
    target.write_text("old")
    target.chmod(0o640)

    atomic_write(target, "new")

    assert _mode(target) == 0o640


def test_new_file_gets_the_umask_default(state_dir: Path) -> None:
    old_umask = os.umask(0o022)
    try:
        atomic_write(state_dir / "state.json", "new")
    finally:
        os.umask(old_umask)

    assert _mode(state_dir / "state.json") == 0o644
