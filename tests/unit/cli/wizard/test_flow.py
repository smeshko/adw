"""Tests for run_wizard, which asks the init wizard's steps in order.

The transcript tests drive `adw init --wizard` through stdin in a scratch git
repo (the autouse isolated_cwd fixture puts each test in its own tmp_path).
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from contextlib import ExitStack
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from rich.console import Console
from typer.testing import CliRunner

from adw.cli.app import app
from adw.cli.wizard.flow import run_wizard
from adw.cli.wizard.summary import ConfigWriteError
from adw.core.constants import PHASE_SEQUENCE

SECTIONS = ["basics", "global_registry", "git", "task_manager", "phases"]
TITLES = [
    "Project Basics",
    "Web Dashboard Registration",
    "Git Configuration",
    "Task Manager Integration",
    "Phase Configuration",
    "Configuration Summary",
]
# Every prompt takes its default on an empty line; unread lines are ignored.
ACCEPT_DEFAULTS = "\n" * 40

runner = CliRunner()


@pytest.fixture
def scratch_repo() -> Path:
    """Make the test's cwd a fresh git repository."""
    subprocess.run(["git", "init", "-q"], check=True)
    return Path.cwd()


def test_run_wizard_calls_steps_in_order_and_hands_cfg_to_summary(
    tmp_path: Path,
) -> None:
    """Each step runs once, in order, and the summary gets their dicts by section."""
    calls: list[tuple[str, tuple[Any, ...]]] = []
    captured: dict[str, Any] = {}

    def step(section: str) -> Callable[..., dict[str, Any]]:
        def run(*args: Any) -> dict[str, Any]:
            calls.append((section, args))
            return {"from": section}

        return run

    def summary(cfg: dict[str, Any], console: Console, root: Path) -> bool:
        captured.update(cfg=cfg, root=root)
        return True

    with ExitStack() as stack:
        for section in SECTIONS:
            stack.enter_context(
                patch(
                    f"adw.cli.wizard.flow.run_{section}_step", side_effect=step(section)
                )
            )
        stack.enter_context(
            patch("adw.cli.wizard.flow.run_summary_step", side_effect=summary)
        )
        run_wizard(tmp_path)

    assert [section for section, _ in calls] == SECTIONS
    assert calls[0][1][1] == tmp_path  # basics gets the project root
    assert captured["cfg"] == {section: {"from": section} for section in SECTIONS}
    assert captured["root"] == tmp_path


def test_accept_defaults_writes_files_that_validate(scratch_repo: Path) -> None:
    """Accepting every default writes a config that adw validate accepts."""
    result = runner.invoke(app, ["init", "--wizard"], input=ACCEPT_DEFAULTS)

    assert result.exit_code == 0, result.output
    adw_dir = scratch_repo / ".adw"
    assert (adw_dir / "project.yaml").is_file()
    for phase in PHASE_SEQUENCE:
        assert (adw_dir / "commands" / phase / "config.yaml").is_file()
    headers = [
        f"Step {number}/{len(TITLES)}: {title}"
        for number, title in enumerate(TITLES, start=1)
    ]
    positions = [result.output.index(header) for header in headers]
    assert positions == sorted(positions)
    assert result.output.count("Configuration written") == 1
    for stale in ("LLM Retry", "b - Go back", "c - Cancel wizard", "Wizard Complete"):
        assert stale not in result.output

    validate = runner.invoke(app, ["validate"])
    assert validate.exit_code == 0, validate.output
    assert "0 errors" in validate.output


def test_decline_at_summary_writes_nothing(scratch_repo: Path) -> None:
    """Answering no at the summary writes nothing, says so and exits 1."""
    with patch("adw.cli.wizard.summary._prompt_confirmation", return_value=False):
        result = runner.invoke(app, ["init", "--wizard"], input=ACCEPT_DEFAULTS)

    assert result.exit_code == 1, result.output
    assert not (scratch_repo / ".adw").exists()
    assert "Nothing was written" in result.output
    assert "Configuration written" not in result.output


def test_write_failure_exits_non_zero(scratch_repo: Path) -> None:
    """A failed write prints the error, says nothing was written and exits 1."""
    error = ConfigWriteError(message="Failed to write config: disk full")
    with patch("adw.cli.wizard.summary.atomic_write_config", side_effect=error):
        result = runner.invoke(app, ["init", "--wizard"], input=ACCEPT_DEFAULTS)

    assert result.exit_code == 1, result.output
    assert "disk full" in result.output
    assert "No files were written" in result.output
    assert "Configuration written" not in result.output


def test_end_of_input_cancels(scratch_repo: Path) -> None:
    """Running out of input cancels, says nothing was written and exits 1."""
    result = runner.invoke(app, ["init", "--wizard"], input="\n")

    assert result.exit_code == 1, result.output
    assert not (scratch_repo / ".adw").exists()
    assert "Nothing was written" in result.output
