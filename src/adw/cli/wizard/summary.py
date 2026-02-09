"""Summary and file generation step for the wizard.

This module handles the final step of the wizard where users see a summary
of their configuration choices, confirm, and have the configuration files
generated.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from adw.exceptions import ConfigError

if TYPE_CHECKING:
    from adw.models.wizard import WizardState


class ConfigWriteError(ConfigError):
    """Raised when configuration file writing fails.

    Inherits from ConfigError to integrate with ADW's exception hierarchy,
    providing structured error information with code, message, and suggestion.
    """

    def __init__(
        self,
        code: str = "CONFIG_WRITE_FAILED",
        message: str = "Failed to write configuration files",
        *,
        suggestion: str | None = "Check file permissions and disk space.",
        recoverable: bool = False,
    ) -> None:
        """Initialize a ConfigWriteError.

        Args:
            code: Unique error code.
            message: Human-readable error message.
            suggestion: Optional actionable next step.
            recoverable: Whether the operation can be retried.
        """
        super().__init__(
            code=code,
            message=message,
            suggestion=suggestion,
            recoverable=recoverable,
        )


class SummaryStepHandler:
    """Handler for the summary configuration wizard step.

    This step:
    - Displays a comprehensive summary panel of all configuration choices
    - Prompts user to confirm or start over
    - Generates all configuration files atomically
    - Shows success message with next steps
    """

    def __init__(self, project_root: Path | None = None) -> None:
        """Initialize the summary step handler.

        Args:
            project_root: The project root directory for file generation.
                         If None, uses current working directory.
        """
        self.project_root = project_root or Path.cwd()

    def execute(self, state: WizardState, console: Console) -> dict[str, Any]:
        """Execute the summary configuration step.

        Args:
            state: Current wizard state containing all collected config.
            console: Console for output.

        Returns:
            Configuration dict containing:
            - confirmed: Whether user confirmed the config
            - files_created: List of created file paths (if confirmed)
        """
        return run_summary_step(state, console, self.project_root)


def run_summary_step(
    state: WizardState,
    console: Console,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Execute the summary configuration step.

    This is the main entry point for the summary step, implementing
    the full interactive flow for summary display and file generation.

    Args:
        state: Current wizard state containing all collected config.
        console: Console for output.
        project_root: The project root directory. Defaults to cwd.

    Returns:
        Configuration dict containing confirmation status and created files.
    """
    root = project_root or Path.cwd()

    # Step 1: Generate and display summary panel
    panel = generate_summary_panel(state)
    console.print()
    console.print(panel)

    # Step 2: Prompt for confirmation
    confirmed = _prompt_confirmation(console)

    if not confirmed:
        # Handle start over or cancel
        action = _prompt_start_over_or_cancel(console)
        if action == "start_over":
            return {"confirmed": False, "action": "start_over", "files_created": []}
        else:
            return {"confirmed": False, "action": "cancel", "files_created": []}

    # Step 3: Generate and write configuration files
    try:
        files = _generate_all_files(state)
        adw_dir = root / ".adw"
        atomic_write_config(adw_dir, files)

        # Step 4: Register project in global dashboard if enabled
        global_registry = state.get_step_config("global_registry")
        if global_registry.get("global_registry_enabled", False):
            _register_in_global_dashboard(
                root,
                global_registry.get("global_registry_name"),
                console,
            )

        # Step 5: Show success message
        _show_success_message(console, list(files.keys()))

        return {
            "confirmed": True,
            "action": "complete",
            "files_created": [str(adw_dir / path) for path in files],
        }
    except ConfigWriteError as e:
        console.print(f"\n[red]Error writing configuration:[/] {e.message}")
        if e.suggestion:
            console.print(f"[dim]Suggestion: {e.suggestion}[/]")
        console.print("[dim]No files were created.[/]")
        return {
            "confirmed": True,
            "action": "error",
            "files_created": [],
            "error": str(e),
        }


def generate_summary_panel(state: WizardState) -> Panel:
    """Generate Rich panel with full configuration summary.

    Args:
        state: Current wizard state containing all collected config.

    Returns:
        Rich Panel with formatted configuration summary.
    """
    lines = []

    # Get configs from collected_config
    basics = state.get_step_config("basics")
    global_registry = state.get_step_config("global_registry")
    git = state.get_step_config("git")
    ports = state.get_step_config("ports")
    task_manager = state.get_step_config("task_manager")
    phases = state.get_step_config("phases")
    ship = state.get_step_config("ship")
    llm_retry = state.get_step_config("llm_retry")
    security = state.get_step_config("security")
    webhooks = state.get_step_config("webhooks")

    # Basics section
    lines.append("[bold]Basics:[/]")
    name = basics.get("project_name", basics.get("language", "unknown"))
    lines.append(f"  Name: {name}")
    lines.append(f"  Language: {basics.get('language', 'unknown')}")
    lines.append(f"  Platform: {basics.get('platform', 'unknown')}")
    lines.append(f"  Test: {basics.get('test_command') or 'none'}")
    lines.append(f"  Build: {basics.get('build_command') or 'none'}")
    lines.append("")

    # Global Registry section
    if global_registry.get("global_registry_enabled", False):
        reg_name = global_registry.get("global_registry_name", "unknown")
        lines.append(f"[green]Global Dashboard:[/] ✓ Registered as '{reg_name}'")
    else:
        lines.append("[dim]Global Dashboard:[/] ✗ Not registered")

    # Git section
    branch_prefix = git.get("git_branch_prefix", "feature/")
    lines.append(f"[green]Git:[/] \u2713 Enabled ({branch_prefix})")

    # Ports section
    # Ports step returns: port_config_custom, backend_port_start, frontend_port_start
    backend_port = ports.get("backend_port_start", 9100)
    frontend_port = ports.get("frontend_port_start", 9200)
    if backend_port == 9100 and frontend_port == 9200:
        lines.append(f"[dim]Ports:[/] Default ({backend_port}/{frontend_port})")
    else:
        lines.append(f"[cyan]Ports:[/] Custom ({backend_port}/{frontend_port})")

    # Task Manager section
    tm_type = task_manager.get("type", "none")
    if tm_type == "none":
        lines.append("[dim]Task Manager:[/] None")
    else:
        team_key = task_manager.get("team_key", "")
        lines.append(f"[cyan]Task Manager:[/] {tm_type.title()} ({team_key}-xxx)")

    # Phases section
    # Phases step returns: customized (bool), phases (dict of phase name -> config)
    phases_dict = phases.get("phases", {})
    if phases.get("customized", False) and phases_dict:
        phase_list = ", ".join(f"{p} \u270e" for p in phases_dict)
        lines.append(f"[cyan]Phases:[/] {phase_list}")
    else:
        lines.append("[dim]Phases:[/] Default")

    # Ship section
    # Ship step returns: enabled, commands (dict), post_publish (list), pr (dict)
    ship_commands = ship.get("commands", {})
    ship_post_publish = ship.get("post_publish", [])
    ship_pr = ship.get("pr", {})
    has_ship_config = (
        ship_commands or ship_post_publish or ship_pr.get("merge_on_success")
    )

    if has_ship_config:
        parts = []
        if ship_commands:
            cmd_names = list(ship_commands.keys())
            parts.append(", ".join(cmd_names))
        if ship_post_publish:
            parts.append(f"{len(ship_post_publish)} hook(s)")
        if ship_pr.get("merge_on_success"):
            merge_method = ship_pr.get("merge_method", "squash")
            delete_on_merge = ship_pr.get("delete_branch_on_merge", True)
            auto_delete = ", auto-delete" if delete_on_merge else ""
            parts.append(f"{merge_method} merge{auto_delete}")
        lines.append(f"[cyan]Ship:[/] {'; '.join(parts)}")
    else:
        lines.append("[dim]Ship:[/] Default (no commands, manual merge)")

    # LLM Retry section
    # Retry step returns: retry_custom, retry_max_retries, retry_base_delay, etc.
    if llm_retry.get("retry_custom", False):
        max_retries = llm_retry.get("retry_max_retries", 3)
        base_delay = llm_retry.get("retry_base_delay", 1.0)
        lines.append(
            f"[cyan]LLM Retry:[/] Custom ({max_retries} retries, {base_delay}s base)"
        )
    else:
        lines.append("[dim]LLM Retry:[/] Default")

    # Security section
    blocked_cmds = security.get("security_blocked_commands", [])
    blocked_files = security.get("security_blocked_env_files", [])
    if blocked_cmds or blocked_files:
        lines.append(
            f"[cyan]Security:[/] Custom ({len(blocked_cmds)} cmd, "
            f"{len(blocked_files)} file patterns)"
        )
    else:
        lines.append("[dim]Security:[/] Default")

    # Webhooks section
    if webhooks.get("enabled", False):
        providers = webhooks.get("providers", {})
        enabled_providers = [
            p for p, cfg in providers.items() if cfg.get("enabled", False)
        ]
        if enabled_providers:
            provider_str = ", ".join(f"{p.title()} \u2713" for p in enabled_providers)
            lines.append(f"[cyan]Webhooks:[/] {provider_str}")
        else:
            lines.append("[dim]Webhooks:[/] Enabled (no providers)")
    else:
        lines.append("[dim]Webhooks:[/] Disabled")

    lines.append("")

    # Files to create section
    lines.append("[bold]Files to create:[/]")
    files = _get_files_to_create(state)
    for file_path in sorted(files):
        lines.append(f"  .adw/{file_path}")

    return Panel(
        "\n".join(lines),
        title="Configuration Summary",
        border_style="green",
    )


def _get_files_to_create(state: WizardState) -> list[str]:
    """Get list of files that will be created.

    Now generates config files for ALL phases (not just customized ones)
    per ISS-032 requirements for full configuration visibility.

    Args:
        state: Current wizard state.

    Returns:
        List of relative file paths (within .adw/).
    """
    from adw.core.constants import PHASE_SEQUENCE

    files = ["project.yaml", ".gitignore", ".env.template"]

    # Add phase config files for ALL phases (ISS-032 change)
    for phase in PHASE_SEQUENCE:
        files.append(f"commands/{phase}/config.yaml")

    return files


def _prompt_confirmation(console: Console) -> bool:
    """Prompt user to confirm configuration.

    Args:
        console: Console for output.

    Returns:
        True if user confirms, False otherwise.
    """
    console.print()
    return Confirm.ask(
        "Create configuration?",
        default=True,
        console=console,
    )


def _prompt_start_over_or_cancel(console: Console) -> str:
    """Prompt user to start over or cancel.

    Args:
        console: Console for output.

    Returns:
        "start_over" or "cancel".
    """
    console.print()
    choice = Prompt.ask(
        "Start over or cancel?",
        choices=["s", "c"],
        default="c",
        console=console,
    )
    return "start_over" if choice.lower() == "s" else "cancel"


def _generate_all_files(state: WizardState) -> dict[str, str]:
    """Generate all configuration files from wizard state.

    Args:
        state: Current wizard state.

    Returns:
        Dict mapping relative file paths to their content.
    """
    files: dict[str, str] = {}

    # Generate project.yaml
    files["project.yaml"] = generate_project_yaml(state)

    # Generate .gitignore
    files[".gitignore"] = generate_gitignore()

    # Generate .env.template
    files[".env.template"] = generate_env_template()

    # Generate phase config files
    phase_files = generate_phase_configs(state)
    files.update(phase_files)

    return files


def generate_project_yaml(state: WizardState) -> str:
    """Generate project.yaml content from wizard state.

    Uses the new YAMLWithComments generator for comprehensive config
    with commented defaults (ISS-032).

    Args:
        state: Current wizard state.

    Returns:
        YAML content string with all settings visible.
    """
    from adw.config.registry import ConfigRegistry
    from adw.config.yaml_generator import YAMLWithComments

    registry = ConfigRegistry()
    generator = YAMLWithComments(registry)
    return generator.generate_project_yaml(state)


def generate_phase_configs(state: WizardState) -> dict[str, str]:
    """Generate phase-specific config.yaml files for ALL phases.

    Now generates configs for ALL phases (not just customized ones)
    with commented defaults per ISS-032 requirements.

    Args:
        state: Current wizard state.

    Returns:
        Dict mapping relative file paths to their content.
    """
    from adw.config.registry import ConfigRegistry
    from adw.config.yaml_generator import generate_all_phase_configs

    registry = ConfigRegistry()
    return generate_all_phase_configs(state, registry)


def generate_gitignore() -> str:
    """Generate .gitignore content for .adw directory.

    Returns:
        Gitignore file content.
    """
    return """# ADW runtime artifacts
runs/
logs/
*.log
state.json

# Environment files with secrets
.env
"""


def generate_env_template() -> str:
    """Generate .env.template content for credential setup.

    Returns:
        Environment template file content with placeholder credentials.
    """
    return """\
# ADW Credentials
# Copy this file to .env and fill in your values
# The .env file is gitignored and will NOT be committed

# Linear Task Manager (required if using linear task manager)
# Get your API key from: Linear Settings > API > Personal API keys
LINEAR_API_KEY=

# Linear Team ID (UUID format)
# Find via: Linear Settings > Workspace > Copy team ID
LINEAR_TEAM_ID=
"""


def atomic_write_config(adw_dir: Path, files: dict[str, str]) -> None:
    """Write all config files atomically.

    Creates files atomically - if any write fails, rolls back
    only newly created files to prevent partial configuration.
    Pre-existing files that were overwritten are backed up and restored on failure.

    Args:
        adw_dir: Path to .adw/ directory.
        files: Dict of relative_path -> content.

    Raises:
        ConfigWriteError: If any write fails (partial writes rolled back).
    """
    newly_created_paths: list[Path] = []
    created_dirs: list[Path] = []
    backups: dict[Path, str] = {}  # Maps file path to original content

    try:
        # Create .adw directory if needed
        if not adw_dir.exists():
            adw_dir.mkdir(parents=True, exist_ok=True)
            created_dirs.append(adw_dir)

        # Write each file
        for rel_path, content in files.items():
            full_path = adw_dir / rel_path

            # Create parent directories if needed
            parent = full_path.parent
            if parent != adw_dir and not parent.exists():
                parent.mkdir(parents=True, exist_ok=True)
                created_dirs.append(parent)

            # Track if file existed before and backup its content
            file_existed = full_path.exists()
            if file_existed:
                backups[full_path] = full_path.read_text()

            # Write file
            full_path.write_text(content)

            # Only track newly created files for deletion on rollback
            if not file_existed:
                newly_created_paths.append(full_path)

    except OSError as e:
        # Rollback: restore backups for overwritten files
        for path, original_content in backups.items():
            with contextlib.suppress(OSError):
                path.write_text(original_content)

        # Delete only newly created files (not pre-existing ones)
        for path in reversed(newly_created_paths):
            if path.is_file():
                path.unlink(missing_ok=True)

        # Remove empty directories we created
        for dir_path in reversed(created_dirs):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                dir_path.rmdir()

        raise ConfigWriteError(
            code="CONFIG_WRITE_FAILED",
            message=f"Failed to write config: {e}",
            suggestion="Check file permissions and disk space.",
        ) from e


def _register_in_global_dashboard(
    project_root: Path,
    name: str | None,
    console: Console,
) -> None:
    """Register project in the global ADW dashboard.

    Args:
        project_root: The project root directory.
        name: Custom display name for the project.
        console: Console for output.
    """
    from adw.core.project_registry import ProjectRegistryManager

    try:
        manager = ProjectRegistryManager()
        manager.register(project_root, name)
    except Exception as e:
        # Non-fatal: warn but continue
        console.print(
            f"[yellow]Warning: Could not register in global dashboard: {e}[/]"
        )


def _show_success_message(console: Console, files: list[str]) -> None:
    """Display success message after configuration creation.

    Args:
        console: Console for output.
        files: List of created file paths.
    """
    console.print()
    console.print("[bold green]\u2713 Configuration created![/]")
    console.print()
    console.print("[bold]Next steps:[/]")
    console.print('  adw run "your feature description"')
    console.print("  adw --help for more commands")
