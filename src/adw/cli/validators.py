"""Shared validators for CLI commands.

This module provides validation functions used across multiple CLI commands.
"""

import typer

from adw.core.constants import PHASE_SEQUENCE

__all__ = ["validate_phase"]


def validate_phase(value: str | None) -> str | None:
    """Validate that phase is one of PHASE_SEQUENCE.

    This is a Typer callback validator for --phase and --from-phase options.

    Args:
        value: Phase name to validate, or None.

    Returns:
        The validated phase name, or None if not provided.

    Raises:
        typer.BadParameter: If phase is not a valid phase name.

    Example:
        >>> from_phase: str | None = typer.Option(
        ...     None,
        ...     "--from-phase",
        ...     callback=validate_phase,
        ... )
    """
    if value is None:
        return None
    if value not in PHASE_SEQUENCE:
        valid_phases = ", ".join(PHASE_SEQUENCE)
        msg = f"Invalid phase: {value}. Valid phases: {valid_phases}"
        raise typer.BadParameter(msg)
    return value
