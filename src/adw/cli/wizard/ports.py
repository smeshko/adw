"""Port configuration step for the wizard.

This module handles the optional port configuration step where users can
customize port ranges for concurrent ADW runs to avoid conflicts with
other services.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

if TYPE_CHECKING:
    from adw.models.wizard import WizardState

# Import default values from the canonical source (worktree/ports.py)
from adw.worktree.ports import (
    DEFAULT_BACKEND_START as DEFAULT_BACKEND_PORT,
    DEFAULT_FRONTEND_START as DEFAULT_FRONTEND_PORT,
    DEFAULT_MAX_CONCURRENT,
)

# Port range limits
MIN_PORT = 1
MAX_PORT = 65535

# Common development ports that may cause conflicts
COMMON_PORTS: set[int] = {
    3000,  # React dev server, Rails
    3001,  # Alternative React port
    5000,  # Flask default
    8000,  # Django, FastAPI
    8080,  # Common HTTP alternative
    8443,  # HTTPS alternative
    8888,  # Jupyter notebooks
}


def validate_port(port_str: str) -> tuple[bool, int | str]:
    """Validate a port number string.

    Validates that the input is a valid integer within the port range 1-65535.

    Args:
        port_str: The port number as a string.

    Returns:
        A tuple of (is_valid, result) where result is either the parsed
        port number (if valid) or an error message string (if invalid).
    """
    try:
        port = int(port_str)
    except ValueError:
        return (False, "Port must be a number")

    if port < MIN_PORT or port > MAX_PORT:
        return (False, f"Port must be between {MIN_PORT} and {MAX_PORT}")

    return (True, port)


def check_port_overlap(
    backend_start: int,
    frontend_start: int,
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
) -> bool:
    """Check if backend and frontend port ranges would overlap.

    Calculates the port ranges based on the starting ports and max concurrent
    runs, then checks if they intersect.

    Args:
        backend_start: Starting port for backend services.
        frontend_start: Starting port for frontend services.
        max_concurrent: Maximum number of concurrent runs (determines range size).

    Returns:
        True if the ranges overlap, False if they are disjoint.
    """
    backend_end = backend_start + max_concurrent - 1
    frontend_end = frontend_start + max_concurrent - 1

    # Ranges overlap if they intersect
    # No overlap when: backend_end < frontend_start OR frontend_end < backend_start
    return not (backend_end < frontend_start or frontend_end < backend_start)


def is_common_port(port: int) -> bool:
    """Check if a port is commonly used by development services.

    Args:
        port: The port number to check.

    Returns:
        True if the port is in the common ports set.
    """
    return port in COMMON_PORTS


def check_range_conflicts(
    start_port: int,
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
) -> list[int]:
    """Check if a port range contains any common ports.

    Args:
        start_port: Starting port of the range.
        max_concurrent: Size of the port range.

    Returns:
        List of common ports that fall within the range.
    """
    end_port = start_port + max_concurrent - 1
    conflicts = []
    for port in COMMON_PORTS:
        if start_port <= port <= end_port:
            conflicts.append(port)
    return sorted(conflicts)


class PortsStepHandler:
    """Handler for the port configuration wizard step.

    This step:
    - Prompts user if they want to configure custom port ranges
    - If yes, prompts for backend and frontend starting ports
    - Validates ports are in valid range
    - Checks for range overlap between backend and frontend
    - Warns about common port conflicts
    """

    def execute(self, state: WizardState, console: Console) -> dict[str, Any]:
        """Execute the port configuration step.

        Args:
            state: Current wizard state.
            console: Console for output.

        Returns:
            Configuration collected from this step containing:
            - port_config_custom: Whether user customized ports
            - backend_port_start: Starting port for backend services
            - frontend_port_start: Starting port for frontend services
        """
        return run_ports_step(state, console)


def run_ports_step(
    state: WizardState,
    console: Console,
) -> dict[str, Any]:
    """Execute the port configuration step.

    This is the main entry point for the ports step, implementing
    the full interactive flow for port configuration.

    Args:
        state: Current wizard state.
        console: Console for output.

    Returns:
        Configuration dict containing port_config_custom, backend_port_start,
        and frontend_port_start values.
    """
    console.print()
    console.print(
        "[dim]ADW allocates ports for backend and frontend services during "
        "concurrent runs.[/]"
    )
    console.print(
        f"[dim]Default: Backend {DEFAULT_BACKEND_PORT}+, "
        f"Frontend {DEFAULT_FRONTEND_PORT}+[/]"
    )
    console.print()

    # Ask if user wants to configure custom ports
    configure = Confirm.ask(
        "Configure port ranges for concurrent runs?",
        default=False,
        console=console,
    )

    if not configure:
        # Use defaults
        return {
            "port_config_custom": False,
            "backend_port_start": DEFAULT_BACKEND_PORT,
            "frontend_port_start": DEFAULT_FRONTEND_PORT,
        }

    # Interactive configuration
    console.print()

    # Get backend port
    backend_port = _prompt_port(
        console,
        "Backend services start port",
        DEFAULT_BACKEND_PORT,
    )

    # Get frontend port
    frontend_port = _prompt_port(
        console,
        "Frontend services start port",
        DEFAULT_FRONTEND_PORT,
    )

    # Check for overlap - loop until valid
    while check_port_overlap(backend_port, frontend_port):
        _show_overlap_warning(console, backend_port, frontend_port)
        # Re-prompt for frontend port
        console.print()
        frontend_port = _prompt_port(
            console,
            "Frontend services start port (adjusted)",
            max(backend_port + DEFAULT_MAX_CONCURRENT, DEFAULT_FRONTEND_PORT),
        )

    # Check for common port conflicts
    _check_and_warn_common_ports(console, backend_port, "backend")
    _check_and_warn_common_ports(console, frontend_port, "frontend")

    return {
        "port_config_custom": True,
        "backend_port_start": backend_port,
        "frontend_port_start": frontend_port,
    }


def _prompt_port(console: Console, prompt_text: str, default: int) -> int:
    """Prompt user for a port number with validation loop.

    Args:
        console: Console for output.
        prompt_text: The prompt to display.
        default: Default port value.

    Returns:
        The validated port number.
    """
    while True:
        port_str = Prompt.ask(
            prompt_text,
            default=str(default),
            console=console,
        )

        is_valid, result = validate_port(port_str)
        if is_valid:
            port = int(result)  # result is the port number when valid
            # Warn about privileged ports
            if port < 1024:
                console.print(
                    Panel(
                        f"[yellow]Port {port} is privileged (< 1024).[/]\n"
                        "You may need root/admin access to bind to this port.",
                        title="Privileged Port",
                        border_style="yellow",
                    )
                )
            return port
        else:
            console.print(f"[red]Invalid port: {result}. Please try again.[/]")


def _show_overlap_warning(
    console: Console,
    backend_port: int,
    frontend_port: int,
) -> None:
    """Display warning about overlapping port ranges.

    Args:
        console: Console for output.
        backend_port: Backend starting port.
        frontend_port: Frontend starting port.
    """
    backend_end = backend_port + DEFAULT_MAX_CONCURRENT - 1
    frontend_end = frontend_port + DEFAULT_MAX_CONCURRENT - 1

    console.print(
        Panel(
            f"[red]Port ranges overlap![/]\n\n"
            f"Backend range: {backend_port}-{backend_end}\n"
            f"Frontend range: {frontend_port}-{frontend_end}\n\n"
            "Please choose a different frontend starting port.",
            title="⚠️ Range Overlap",
            border_style="red",
        )
    )


def _check_and_warn_common_ports(
    console: Console,
    start_port: int,
    service_type: str,
) -> None:
    """Check for common port conflicts and display warning if found.

    Args:
        console: Console for output.
        start_port: Starting port of the range.
        service_type: "backend" or "frontend" for display.
    """
    conflicts = check_range_conflicts(start_port)
    if conflicts:
        conflict_list = ", ".join(str(p) for p in conflicts)
        console.print(
            Panel(
                f"[yellow]{service_type.title()} port range includes commonly "
                f"used ports: {conflict_list}[/]\n"
                "These may conflict with other development services.",
                title="Port Warning",
                border_style="yellow",
            )
        )
