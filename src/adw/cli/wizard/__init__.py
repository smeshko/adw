"""Wizard package for interactive init setup.

This package provides the wizard flow controller and related components
for guiding users through interactive project initialization.

Exports:
    WizardFlowController: Main controller for wizard flow execution.
    WizardStep: Enumeration of wizard steps.
    StepHandler: Protocol for implementing wizard step handlers.
    BasicsStepHandler: Handler for the basics configuration step.
    run_basics_step: Function to execute the basics step.
    PhasesStepHandler: Handler for the phases configuration step.
    run_phases_step: Function to execute the phases step.
    TaskManagerStepHandler: Handler for the task manager configuration step.
    run_task_manager_step: Function to execute the task manager step.
    validate_team_key: Function to validate Linear team keys.
"""

from adw.cli.wizard.basics import (
    BasicsStepHandler,
    detect_language,
    detect_test_command,
    run_basics_step,
)
from adw.cli.wizard.flow import StepHandler, WizardFlowController, WizardStep
from adw.cli.wizard.phases import (
    PhasesStepHandler,
    run_phases_step,
)
from adw.cli.wizard.task_manager import (
    TaskManagerStepHandler,
    run_task_manager_step,
    validate_team_key,
)

__all__ = [
    "BasicsStepHandler",
    "PhasesStepHandler",
    "StepHandler",
    "TaskManagerStepHandler",
    "WizardFlowController",
    "WizardStep",
    "detect_language",
    "detect_test_command",
    "run_basics_step",
    "run_phases_step",
    "run_task_manager_step",
    "validate_team_key",
]
