"""Wizard package for interactive init setup.

This package provides the wizard flow controller and related components
for guiding users through interactive project initialization.

Exports:
    WizardFlowController: Main controller for wizard flow execution.
    WizardStep: Enumeration of wizard steps.
    StepHandler: Protocol for implementing wizard step handlers.
    BasicsStepHandler: Handler for the basics configuration step.
    run_basics_step: Function to execute the basics step.
    GitStepHandler: Handler for the git integration step.
    run_git_step: Function to execute the git step.
    GlobalRegistryStepHandler: Handler for the global dashboard registration step.
    run_global_registry_step: Function to execute the global registry step.
    PhasesStepHandler: Handler for the phases configuration step.
    run_phases_step: Function to execute the phases step.
    PortsStepHandler: Handler for the port configuration step.
    run_ports_step: Function to execute the ports step.
    RetryStepHandler: Handler for the LLM retry configuration step.
    run_retry_step: Function to execute the retry step.
    SecurityStepHandler: Handler for the security configuration step.
    run_security_step: Function to execute the security step.
    TaskManagerStepHandler: Handler for the task manager configuration step.
    run_task_manager_step: Function to execute the task manager step.
    WebhooksStepHandler: Handler for the webhooks configuration step.
    run_webhooks_step: Function to execute the webhooks step.
    ShipStepHandler: Handler for the ship phase configuration step.
    run_ship_step: Function to execute the ship step.
    SummaryStepHandler: Handler for the summary and file generation step.
    run_summary_step: Function to execute the summary step.
    generate_summary_panel: Function to generate the summary panel.
    generate_project_yaml: Function to generate project.yaml content.
    generate_phase_configs: Function to generate phase config files.
    generate_gitignore: Function to generate .gitignore content.
    atomic_write_config: Function to write config files atomically.
    ConfigWriteError: Exception for config write failures.
    validate_team_key: Function to validate Linear team keys.
"""

from adw.cli.wizard.basics import (
    BasicsStepHandler,
    detect_language,
    detect_test_command,
    run_basics_step,
)
from adw.cli.wizard.flow import StepHandler, WizardFlowController, WizardStep
from adw.cli.wizard.git import (
    GitStepHandler,
    run_git_step,
    validate_branch_prefix,
)
from adw.cli.wizard.global_registry import (
    GlobalRegistryStepHandler,
    run_global_registry_step,
)
from adw.cli.wizard.navigation import (
    NavigationError,
    NavigationSignal,
    check_navigation,
    nav_confirm_ask,
    nav_prompt_ask,
)
from adw.cli.wizard.phases import (
    PhasesStepHandler,
    run_phases_step,
)
from adw.cli.wizard.ports import (
    PortsStepHandler,
    check_port_overlap,
    is_common_port,
    run_ports_step,
    validate_port,
)
from adw.cli.wizard.retry import (
    RetryStepHandler,
    run_retry_step,
    validate_base_delay,
    validate_max_delay,
    validate_max_retries,
    validate_multiplier,
)
from adw.cli.wizard.security import (
    BUILTIN_BLOCKED_COMMANDS,
    BUILTIN_BLOCKED_ENV_FILES,
    SecurityStepHandler,
    run_security_step,
    validate_regex,
)
from adw.cli.wizard.ship import (
    ShipStepHandler,
    run_ship_step,
)
from adw.cli.wizard.summary import (
    ConfigWriteError,
    SummaryStepHandler,
    atomic_write_config,
    generate_gitignore,
    generate_phase_configs,
    generate_project_yaml,
    generate_summary_panel,
    run_summary_step,
)
from adw.cli.wizard.task_manager import (
    TaskManagerStepHandler,
    run_task_manager_step,
    validate_team_key,
)
from adw.cli.wizard.webhooks import (
    WebhooksStepHandler,
    run_webhooks_step,
)

__all__ = [
    "BasicsStepHandler",
    "BUILTIN_BLOCKED_COMMANDS",
    "BUILTIN_BLOCKED_ENV_FILES",
    "ConfigWriteError",
    "GitStepHandler",
    "GlobalRegistryStepHandler",
    "NavigationError",
    "NavigationSignal",
    "PhasesStepHandler",
    "PortsStepHandler",
    "RetryStepHandler",
    "SecurityStepHandler",
    "ShipStepHandler",
    "StepHandler",
    "SummaryStepHandler",
    "TaskManagerStepHandler",
    "WebhooksStepHandler",
    "WizardFlowController",
    "WizardStep",
    "atomic_write_config",
    "check_navigation",
    "check_port_overlap",
    "detect_language",
    "detect_test_command",
    "generate_gitignore",
    "generate_phase_configs",
    "generate_project_yaml",
    "generate_summary_panel",
    "is_common_port",
    "nav_confirm_ask",
    "nav_prompt_ask",
    "run_basics_step",
    "run_git_step",
    "run_global_registry_step",
    "run_phases_step",
    "run_ports_step",
    "run_retry_step",
    "run_security_step",
    "run_ship_step",
    "run_summary_step",
    "run_task_manager_step",
    "run_webhooks_step",
    "validate_base_delay",
    "validate_branch_prefix",
    "validate_max_delay",
    "validate_max_retries",
    "validate_multiplier",
    "validate_port",
    "validate_regex",
    "validate_team_key",
]
