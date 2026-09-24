"""Tests for the git() and gh() runners: results, errors, timeouts, interrupts.

The timeout and interrupt tests put fake `git`/`gh` scripts first on PATH and
always pass cwd=tmp_path, so a PATH slip can never reach the checkout.
"""

import os
import signal
import stat
import subprocess
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from types import FrameType

import pytest

import adw.git
from adw.exceptions import ADWError
from adw.git import gh, git

# Dies on SIGTERM at once, so the kill grace period is never spent
SLEEPER = "exec sleep 30"
# Writes $MARK and exits on SIGTERM, like git removing its lockfiles
TERM_TRAP = "trap 'echo cleaned > \"$MARK\"; kill $! 2>/dev/null; exit 143' TERM; sleep 30 & wait"
# Ignores SIGTERM (an ignored signal survives exec), so only SIGKILL stops it
TERM_IGNORER = "trap '' TERM; exec sleep 30"

FakeBin = Callable[[str, str], None]


@pytest.fixture
def fake_bin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeBin:
    """Return a writer for fake executables placed first on PATH."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

    def write(name: str, body: str) -> None:
        script = bin_dir / name
        script.write_text(f"#!/bin/sh\n{body}\n")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)

    return write


@pytest.fixture
def interrupt_after() -> Iterator[Callable[[float], None]]:
    """Schedule a KeyboardInterrupt via SIGALRM; always cancel and restore."""
    old = signal.getsignal(signal.SIGALRM)

    def raise_interrupt(signum: int, frame: FrameType | None) -> None:
        raise KeyboardInterrupt

    def schedule(seconds: float) -> None:
        signal.signal(signal.SIGALRM, raise_interrupt)
        signal.setitimer(signal.ITIMER_REAL, seconds)

    try:
        yield schedule
    finally:
        # An alarm left pending after git() returns would kill pytest
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def test_git_returns_the_completed_process(git_repo: Path) -> None:
    result = git("rev-parse", "--is-inside-work-tree", cwd=git_repo)

    assert result.returncode == 0
    assert result.stdout.strip() == "true"


def test_git_check_raises_called_process_error(tmp_path: Path) -> None:
    with pytest.raises(subprocess.CalledProcessError) as exc_info:
        git("rev-parse", "HEAD", cwd=tmp_path, check=True)

    assert exc_info.value.returncode != 0
    assert "not a git repository" in exc_info.value.stderr


def test_git_fetch_times_out_against_a_sleeping_git(
    fake_bin: FakeBin, tmp_path: Path
) -> None:
    fake_bin("git", SLEEPER)

    start = time.monotonic()
    with pytest.raises(ADWError) as exc_info:
        git("fetch", "origin", cwd=tmp_path, timeout=0.5)
    elapsed = time.monotonic() - start

    assert exc_info.value.code == "GIT_TIMEOUT"
    assert exc_info.value.recoverable
    assert "`git fetch origin` timed out after 0.5s" in exc_info.value.message
    assert "credential" in (exc_info.value.suggestion or "")
    assert elapsed < 5


def test_gh_times_out_against_a_sleeping_gh(fake_bin: FakeBin, tmp_path: Path) -> None:
    fake_bin("gh", SLEEPER)

    with pytest.raises(ADWError) as exc_info:
        gh("pr", "view", "b", "--json", "state", cwd=tmp_path, timeout=0.5)

    assert exc_info.value.code == "GH_TIMEOUT"
    assert exc_info.value.recoverable
    # The label stops after two leading arguments
    assert "`gh pr view` timed out" in exc_info.value.message


def test_timeout_sends_sigterm_first(
    fake_bin: FakeBin, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mark = tmp_path / "cleaned"
    monkeypatch.setenv("MARK", str(mark))
    fake_bin("git", TERM_TRAP)

    with pytest.raises(ADWError) as exc_info:
        git("commit", "-m", "x", cwd=tmp_path, timeout=1.0)

    assert mark.exists()
    # The label stops at the first flag, so the message never carries it
    assert "`git commit` timed out" in exc_info.value.message


@pytest.mark.parametrize("trigger", ["timeout", "interrupt"])
def test_escalates_to_sigkill_only_after_the_grace_period(
    trigger: str,
    fake_bin: FakeBin,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    interrupt_after: Callable[[float], None],
) -> None:
    fake_bin("git", TERM_IGNORER)
    monkeypatch.setattr(adw.git, "KILL_GRACE", 0.5)

    start = time.monotonic()
    if trigger == "timeout":
        with pytest.raises(ADWError):
            git("fetch", cwd=tmp_path, timeout=1.0)
    else:
        interrupt_after(1.0)
        with pytest.raises(KeyboardInterrupt):
            git("fetch", cwd=tmp_path, timeout=30)
    elapsed = time.monotonic() - start

    # An immediate SIGKILL would finish right after 1.0 s
    assert 1.0 + 0.5 <= elapsed < 5


def test_interrupt_stops_git_and_propagates(
    fake_bin: FakeBin,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    interrupt_after: Callable[[float], None],
) -> None:
    mark = tmp_path / "cleaned"
    monkeypatch.setenv("MARK", str(mark))
    fake_bin("git", TERM_TRAP)

    interrupt_after(1.0)
    with pytest.raises(KeyboardInterrupt):
        git("fetch", cwd=tmp_path, timeout=30)

    assert mark.exists()
