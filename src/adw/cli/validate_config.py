"""CLI command for validating ADW configuration files.

This module provides the `adw validate` command that checks project.yaml
and phase config.yaml files for errors and warnings.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from adw.cli.validate_config_display import ValidateConfigDisplay
from adw.cli.validators import validate_phase
from adw.config.checker import CheckReport, ConfigChecker

console = Console()

__all__ = ["validate_config_command"]


def validate_config_command(
    phase: str | None = typer.Option(
        None,
        "--phase",
        "-p",
        help="Validate a specific phase config only",
        callback=validate_phase,
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output results as JSON",
    ),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Treat warnings as errors (exit code 1)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output",
    ),
) -> None:
    """Validate ADW configuration files.

    Checks project.yaml and phase config files for syntax errors,
    schema violations, and semantic issues (missing files, executables).

    Examples:
        adw validate                    # Validate all configs
        adw validate --phase build      # Validate build phase only
        adw validate --json             # Machine-readable JSON output
        adw validate --strict           # Treat warnings as errors
    """
    project_root = Path.cwd()
    checker = ConfigChecker(project_root=project_root)

    if phase:
        report = checker.check_project_config()
        report.merge(checker.check_phase_config(phase))
    else:
        report = checker.check_all()

    # JSON output mode
    if json_output:
        output = report.to_dict()
        console.print_json(json.dumps(output))
        exit_code = _get_exit_code(report, strict=strict)
        raise typer.Exit(exit_code)

    # Rich display mode
    display = ValidateConfigDisplay(console)
    display.show(report, verbose=verbose)

    exit_code = _get_exit_code(report, strict=strict)
    if exit_code != 0:
        raise typer.Exit(exit_code)


def _get_exit_code(report: CheckReport, *, strict: bool = False) -> int:
    """Determine exit code from report.

    Args:
        report: The validation report.
        strict: If True, warnings also cause exit code 1.

    Returns:
        0 for success, 1 for failure.
    """
    if report.errors:
        return 1
    if strict and report.warnings:
        return 1
    return 0
