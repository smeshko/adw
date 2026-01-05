"""Base validator infrastructure.

This module contains the Validator Protocol and ValidatorRegistry
for managing and executing validators in the unified validation phase.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from adw.validation.config import ValidationConfig
from adw.validation.models import ValidationIssue

if TYPE_CHECKING:
    from adw.models import RunContext

logger = logging.getLogger(__name__)


@runtime_checkable
class Validator(Protocol):
    """Protocol defining the interface for validation implementations.

    Each validator must implement:
    - name property: Returns a unique identifier for the validator
    - validate method: Executes validation and returns found issues

    Validators are executed in sequence by the ValidationPhase.
    """

    @property
    def name(self) -> str:
        """Return the validator's unique name.

        Returns:
            Unique identifier string (e.g., "test", "review", "evidence").
        """
        ...

    def validate(self, context: RunContext) -> list[ValidationIssue]:
        """Execute validation and return any issues found.

        Args:
            context: Current run context with phase history and artifacts.

        Returns:
            List of validation issues found, empty if validation passed.
        """
        ...


# Mapping from validator names to config enable flags
_VALIDATOR_CONFIG_MAP: dict[str, str] = {
    "test": "enable_tests",
    "review": "enable_review",
    "evidence": "enable_evidence",
}


class ValidatorRegistry:
    """Registry for managing and executing validators.

    The registry:
    - Stores validator instances
    - Filters validators based on configuration
    - Executes validators and collects issues
    - Handles validator errors gracefully

    Example:
        >>> registry = ValidatorRegistry()
        >>> registry.register(TestValidator())
        >>> registry.register(ReviewValidator())
        >>> issues = registry.run_enabled(context, config)
    """

    def __init__(self) -> None:
        """Initialize an empty validator registry."""
        self._validators: list[Validator] = []

    def register(self, validator: Validator) -> None:
        """Register a validator to be managed by the registry.

        Args:
            validator: Validator instance implementing the Validator protocol.
        """
        self._validators.append(validator)
        logger.debug(f"Registered validator: {validator.name}")

    def get_all(self) -> list[Validator]:
        """Get all registered validators.

        Returns:
            List of all registered validator instances.
        """
        return list(self._validators)

    def get_enabled(self, config: ValidationConfig) -> list[Validator]:
        """Get validators that are enabled in the configuration.

        Args:
            config: ValidationConfig with enable flags.

        Returns:
            List of validators that are enabled.
        """
        enabled: list[Validator] = []
        for validator in self._validators:
            # Check if this validator has a config flag
            config_attr = _VALIDATOR_CONFIG_MAP.get(validator.name)
            if config_attr:
                # If there's a config flag, check if enabled
                if getattr(config, config_attr, True):
                    enabled.append(validator)
            else:
                # Unknown validators are included by default
                enabled.append(validator)
        return enabled

    def run_all(self, context: RunContext) -> list[ValidationIssue]:
        """Run all registered validators and collect issues.

        All validators run regardless of individual failures.
        Errors are logged but don't stop execution.

        Args:
            context: Current run context.

        Returns:
            Aggregated list of issues from all validators.
        """
        return self._run_validators(self._validators, context)

    def run_enabled(
        self, context: RunContext, config: ValidationConfig
    ) -> list[ValidationIssue]:
        """Run only enabled validators and collect issues.

        Args:
            context: Current run context.
            config: Configuration specifying which validators are enabled.

        Returns:
            Aggregated list of issues from enabled validators.
        """
        enabled = self.get_enabled(config)
        return self._run_validators(enabled, context)

    def _run_validators(
        self, validators: list[Validator], context: RunContext
    ) -> list[ValidationIssue]:
        """Execute a list of validators and collect issues.

        Args:
            validators: List of validators to run.
            context: Current run context.

        Returns:
            Aggregated list of issues from all validators.
        """
        all_issues: list[ValidationIssue] = []

        for validator in validators:
            try:
                logger.debug(f"Running validator: {validator.name}")
                issues = validator.validate(context)
                all_issues.extend(issues)
                logger.debug(f"Validator {validator.name} found {len(issues)} issues")
            except Exception as e:
                # Log error but continue to next validator
                logger.warning(
                    f"Validator {validator.name} failed with error: {e}",
                    exc_info=True,
                )
                # Continue to next validator - don't add error as issue
                # The validator should handle its own errors and return appropriate issues

        return all_issues

    def clear(self) -> None:
        """Remove all registered validators."""
        self._validators.clear()
        logger.debug("Cleared all validators from registry")


__all__ = ["Validator", "ValidatorRegistry"]
