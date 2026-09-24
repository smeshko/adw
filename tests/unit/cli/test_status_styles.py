"""Every CLI surface colours a run status the same way (adw.format.STATUS_STYLES)."""

import re
from datetime import UTC, datetime
from io import StringIO

import pytest
from rich.console import Console

from adw.cli.list_display import ListDisplay
from adw.cli.progress import ProgressDisplay
from adw.cli.status_display import StatusDisplay
from adw.format import status_style
from adw.models import RunContext, RunStatus


def _console(out: StringIO) -> Console:
    return Console(file=out, force_terminal=True, color_system="256", width=200)


def _sgr_before(text: str, word: str) -> str:
    """Return the ANSI escape sequence(s) directly in front of ``word``."""
    match = re.search(r"((?:\x1b\[[0-9;]*m)+)" + re.escape(word), text)
    assert match, f"{word!r} not styled in output"
    return match.group(1)


def _expected_sgr(color: str) -> str:
    out = StringIO()
    _console(out).print(f"[{color}]X[/]")
    return _sgr_before(out.getvalue(), "X")


def _context(status: RunStatus) -> RunContext:
    return RunContext(
        run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
        feature_description="Add auth",
        current_phase="build",
        started_at=datetime.now(UTC),
        status=status,
    )


@pytest.mark.parametrize("status", list(RunStatus))
def test_list_and_status_colour_each_status_alike(status: RunStatus) -> None:
    listed, shown, summary = StringIO(), StringIO(), StringIO()

    ListDisplay(_console(listed)).show_runs([_context(status)])
    StatusDisplay(_console(shown)).show_status(_context(status))
    ProgressDisplay(_console(summary)).show_pipeline_summary(
        completed_phases=["plan"],
        status=status,
        total_duration_ms=1000,
        total_tokens=10,
    )

    expected = _expected_sgr(status_style(status).color)
    assert _sgr_before(listed.getvalue(), status) == expected
    assert _sgr_before(shown.getvalue(), status) == expected
    assert _sgr_before(summary.getvalue(), status) == expected
