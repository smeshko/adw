"""Wizard package for interactive init setup.

This package provides the wizard flow controller and related components
for guiding users through interactive project initialization.

Exports:
    WizardFlowController: Main controller for wizard flow execution.
    WizardStep: Enumeration of wizard steps.
    StepHandler: Protocol for implementing wizard step handlers.
    BasicsStepHandler: Handler for the basics configuration step.
    run_basics_step: Function to execute the basics step.
"""

from adw.cli.wizard.basics import (
    BasicsStepHandler,
    detect_language,
    run_basics_step,
)

from adw.cli.wizard.flow import StepHandler, WizardFlowController, WizardStep

__all__ = [
    "BasicsStepHandler",
    "StepHandler",
    "WizardFlowController",
    "WizardStep",
    "detect_language",
    "run_basics_step",
]
