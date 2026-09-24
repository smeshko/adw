"""Tests for run_wizard, which asks the init wizard's steps in order."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import ExitStack
from pathlib import Path
from typing import Any
from unittest.mock import patch

from rich.console import Console

from adw.cli.wizard.flow import run_wizard

SECTIONS = ["basics", "global_registry", "git", "task_manager", "phases", "webhooks"]


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
