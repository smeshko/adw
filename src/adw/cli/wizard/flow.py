"""Wizard flow controller for interactive init setup.

This module provides the WizardFlowController class that coordinates
the step-by-step wizard experience for project initialization.
"""

from __future__ import annotations

import signal
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol

from rich.console import Console
from rich.panel import Panel

if TYPE_CHECKING:
    from adw.models.wizard import WizardState


class StepHandler(Protocol):
    """Protocol for wizard step handlers."""

    def execute(self, state: WizardState, console: Console) -> dict[str, Any]:
        """Execute the step and return collected configuration.

        Args:
            state: Current wizard state.
            console: Console for output.

        Returns:
            Configuration collected from this step.
        """
        ...


class WizardStep(Enum):
    """Enumeration of wizard steps in execution order."""

    BASICS = "basics"
    GIT = "git"
    PORTS = "ports"
    TASK_MANAGER = "task_manager"
    PHASES = "phases"
    SHIP = "ship"
    LLM_RETRY = "llm_retry"
    SECURITY = "security"
    WEBHOOKS = "webhooks"
    SUMMARY = "summary"


class WizardFlowController:
    """Controls the wizard flow for interactive project initialization.

    The flow controller manages the sequence of wizard steps, handles
    navigation between steps, and coordinates state updates.

    Attributes:
        state: The current wizard state tracking progress and config.
        steps: Ordered list of wizard steps to execute.
        current_index: Index of the current step in the sequence.
        console: Rich console for output.
        interrupted: Flag indicating if wizard was interrupted.
    """

    STEP_SEQUENCE: list[WizardStep] = [
        WizardStep.BASICS,
        WizardStep.GIT,
        WizardStep.PORTS,
        WizardStep.TASK_MANAGER,
        WizardStep.PHASES,
        WizardStep.SHIP,
        WizardStep.LLM_RETRY,
        WizardStep.SECURITY,
        WizardStep.WEBHOOKS,
        WizardStep.SUMMARY,
    ]

    STEP_TITLES: dict[WizardStep, str] = {
        WizardStep.BASICS: "Project Basics",
        WizardStep.GIT: "Git Configuration",
        WizardStep.PORTS: "Port Allocation",
        WizardStep.TASK_MANAGER: "Task Manager Integration",
        WizardStep.PHASES: "Phase Configuration",
        WizardStep.SHIP: "Ship Phase Configuration",
        WizardStep.LLM_RETRY: "LLM Retry Settings",
        WizardStep.SECURITY: "Security Settings",
        WizardStep.WEBHOOKS: "Webhook Configuration",
        WizardStep.SUMMARY: "Configuration Summary",
    }

    def __init__(self, state: WizardState | None = None) -> None:
        """Initialize the flow controller.

        Args:
            state: Optional initial wizard state. If None, creates new state.
        """
        # Import here to avoid circular dependency at module level
        from adw.models.wizard import WizardState

        self.state = state if state is not None else WizardState()
        self.steps = self.STEP_SEQUENCE.copy()
        self.current_index = 0
        self.console = Console()
        self.interrupted = False
        self._step_handlers: dict[WizardStep, StepHandler] = {}
        # Type is signal handler (Callable | int | None) returned by signal.signal()
        self._original_sigint_handler: Any = None

    def _install_interrupt_handler(self) -> None:
        """Install SIGINT handler for clean Ctrl+C handling."""
        self._original_sigint_handler = signal.signal(
            signal.SIGINT, self._handle_interrupt
        )

    def _restore_interrupt_handler(self) -> None:
        """Restore original SIGINT handler."""
        if self._original_sigint_handler is not None:
            signal.signal(signal.SIGINT, self._original_sigint_handler)

    def _handle_interrupt(self, signum: int, frame: Any) -> None:
        """Handle Ctrl+C interrupt.

        Args:
            signum: Signal number.
            frame: Current stack frame.
        """
        self.interrupted = True
        self.console.print()
        self.console.print("[yellow]Setup cancelled. No files created.[/]")
        raise SystemExit(0)

    def register_step_handler(self, step: WizardStep, handler: StepHandler) -> None:
        """Register a handler for a wizard step.

        Args:
            step: The step to register a handler for.
            handler: The handler to execute for this step.
        """
        self._step_handlers[step] = handler

    def run(self) -> bool:
        """Execute the wizard flow sequentially.

        Runs through all wizard steps in order, updating state
        as each step completes. Supports back/forward navigation.

        Returns:
            True if wizard completed successfully, False if cancelled.
        """
        self._install_interrupt_handler()

        try:
            self._show_welcome()

            while self.current_index < len(self.steps):
                if self.interrupted:
                    return False

                current_step = self.steps[self.current_index]
                self._show_step_header(current_step)

                # Execute step handler if registered
                if current_step in self._step_handlers:
                    handler = self._step_handlers[current_step]
                    config = handler.execute(self.state, self.console)
                    self.state.update_config(current_step.value, config)
                else:
                    # Default placeholder for unimplemented steps
                    self._show_step_placeholder(current_step)

                # Auto-advance to next step
                self.state.mark_completed(current_step.value)
                self.state.navigate_to(
                    self.steps[self.current_index + 1].value
                    if self.current_index < len(self.steps) - 1
                    else "complete"
                )
                self.current_index += 1

            self._show_completion()
            return True
        finally:
            self._restore_interrupt_handler()

    def _show_welcome(self) -> None:
        """Display wizard welcome message."""
        self.console.print()
        self.console.print(
            Panel(
                "[bold]Welcome to the ADW Configuration Wizard![/]\n\n"
                "This wizard will guide you through setting up your project.\n"
                "You can navigate using:\n"
                "  • [bold]n[/] or [bold]Enter[/] - Next step\n"
                "  • [bold]b[/] - Go back\n"
                "  • [bold]c[/] - Cancel wizard",
                title="[blue]ADW Setup Wizard[/]",
                border_style="blue",
            )
        )

    def _show_step_header(self, step: WizardStep) -> None:
        """Display header for current step.

        Args:
            step: The current wizard step.
        """
        title = self.STEP_TITLES.get(step, step.value.replace("_", " ").title())
        step_num = self.current_index + 1
        total_steps = len(self.steps)

        self.console.print()
        self.console.print(
            f"[bold blue]Step {step_num}/{total_steps}:[/] [bold]{title}[/]"
        )
        self.console.print("[dim]" + "─" * 50 + "[/]")

    def _show_step_placeholder(self, step: WizardStep) -> None:
        """Display placeholder for unimplemented step.

        Args:
            step: The step to show placeholder for.
        """
        title = self.STEP_TITLES.get(step, step.value)
        self.console.print(
            f"\n[dim]Step '{title}' will be implemented in subsequent stories.[/]\n"
        )

    def _show_completion(self) -> None:
        """Display wizard completion message."""
        self.console.print()
        self.console.print(
            Panel(
                "[bold green]Wizard Complete![/]\n\n"
                "Your project has been configured and files have been written.",
                title="[green]Setup Complete[/]",
                border_style="green",
            )
        )

    def get_current_step(self) -> WizardStep | None:
        """Get the current wizard step.

        Returns:
            The current WizardStep or None if wizard is complete.
        """
        if self.current_index >= len(self.steps):
            return None
        return self.steps[self.current_index]

    def advance(self) -> bool:
        """Advance to the next wizard step.

        Returns:
            True if advanced successfully, False if already at end.
        """
        if self.current_index >= len(self.steps) - 1:
            return False
        # Mark current step as completed (uses mark_completed to prevent duplicates)
        current_step_value = self.steps[self.current_index].value
        self.state.mark_completed(current_step_value)
        # Move to next step
        self.current_index += 1
        next_step_value = self.steps[self.current_index].value
        # Update navigation state properly
        self.state.navigate_to(next_step_value)
        return True

    def go_back(self) -> bool:
        """Go back to the previous wizard step.

        Returns:
            True if went back successfully, False if already at start.
        """
        if self.current_index <= 0:
            return False
        # Remove current step from completed (we're revisiting it)
        current_step_value = self.steps[self.current_index].value
        if current_step_value in self.state.completed_steps:
            self.state.completed_steps.remove(current_step_value)
        # Move back in history and update index
        self.state.go_back_in_history()
        self.current_index -= 1
        return True

    def cancel(self) -> None:
        """Cancel the wizard execution."""
        self.interrupted = True
