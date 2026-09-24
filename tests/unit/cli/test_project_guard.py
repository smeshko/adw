"""Read-only commands refuse to run outside a project and create nothing."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from adw.cli.app import app

RUN_ID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"


@pytest.mark.parametrize(
    "args",
    [
        ["status"],
        ["status", RUN_ID],
        ["abort", RUN_ID],
        ["resume", RUN_ID],
        ["pr", RUN_ID],
        ["cleanup", RUN_ID],
        ["logs", "state", RUN_ID],
    ],
)
def test_read_only_commands_outside_a_project_create_nothing(
    args: list[str], tmp_path: Path
) -> None:
    before = set(tmp_path.iterdir())

    result = CliRunner().invoke(app, args)

    assert result.exit_code == 1, result.output
    assert "No .adw directory found" in result.output
    assert set(tmp_path.iterdir()) == before


def test_status_in_a_project_without_runs_creates_nothing(tmp_path: Path) -> None:
    (tmp_path / ".adw").mkdir()

    result = CliRunner().invoke(app, ["status"])

    assert result.exit_code == 0, result.output
    assert "No runs found" in result.output
    assert not (tmp_path / ".adw" / "runs").exists()
