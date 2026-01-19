"""Summary and file generation step for the wizard.

This module handles the final step of the wizard where users see a summary
of their configuration choices, confirm, and have the configuration files
generated.
"""

from __future__ import annotations

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

        # Step 4: Show success message
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
    git = state.get_step_config("git")
    ports = state.get_step_config("ports")
    task_manager = state.get_step_config("task_manager")
    phases = state.get_step_config("phases")
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

    # Git section
    # Git step returns: git_enabled, git_branch_prefix, git_auto_create_pr
    if git.get("git_enabled", False):
        branch_prefix = git.get("git_branch_prefix", "feature/")
        auto_pr = "auto-PR" if git.get("git_auto_create_pr", True) else "manual PR"
        lines.append(f"[green]Git:[/] \u2713 Enabled ({branch_prefix}, {auto_pr})")
    else:
        lines.append("[dim]Git:[/] \u2717 Disabled")

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
    # Security step returns: security_custom, security_allow_dangerous, etc.
    if security.get("security_allow_dangerous", False):
        lines.append("[yellow]Security:[/] Dangerous mode")
    else:
        lines.append("[dim]Security:[/] Default (safe mode)")

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

    Args:
        state: Current wizard state.

    Returns:
        List of relative file paths (within .adw/).
    """
    files = ["project.yaml", ".gitignore", ".env.template"]

    # Add phase config files for customized phases
    # Phases step returns: customized (bool), phases (dict of phase name -> config)
    phases = state.get_step_config("phases")
    phases_dict = phases.get("phases", {})
    if phases.get("customized", False):
        for phase in phases_dict:
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

    Args:
        state: Current wizard state.

    Returns:
        YAML content string.
    """
    from datetime import date

    import yaml

    basics = state.get_step_config("basics")
    git = state.get_step_config("git")
    ports = state.get_step_config("ports")
    task_manager = state.get_step_config("task_manager")
    llm_retry = state.get_step_config("llm_retry")
    security = state.get_step_config("security")
    webhooks = state.get_step_config("webhooks")

    # Build config dict
    config: dict[str, Any] = {}

    # Header comment will be added separately
    config["name"] = basics.get("project_name", basics.get("language", "my-project"))
    config["language"] = basics.get("language", "unknown")
    config["platform"] = basics.get("platform", "cli")

    # Commands section
    commands: dict[str, str] = {}
    if basics.get("test_command"):
        commands["test"] = basics["test_command"]
    if basics.get("build_command"):
        commands["build"] = basics["build_command"]
    if commands:
        config["commands"] = commands

    # Git section
    # Git step returns: git_enabled, git_branch_prefix, git_auto_create_pr
    if git.get("git_enabled", False):
        config["git"] = {
            "enabled": True,
            "branch_prefix": git.get("git_branch_prefix", "feature/"),
            "auto_create_pr": git.get("git_auto_create_pr", True),
        }

    # Ports section (only if non-default)
    # Ports step returns: port_config_custom, backend_port_start, frontend_port_start
    backend = ports.get("backend_port_start", 9100)
    frontend = ports.get("frontend_port_start", 9200)
    if backend != 9100 or frontend != 9200:
        config["ports"] = {
            "backend_start": backend,
            "frontend_start": frontend,
        }

    # Task manager section
    # Task manager step returns: enabled, type, team_key, etc.
    tm_enabled = task_manager.get("enabled", False)
    tm_type = task_manager.get("type", "none")
    if tm_enabled and tm_type != "none":
        tm_config: dict[str, Any] = {
            "type": task_manager["type"],
        }
        if task_manager.get("team_key"):
            tm_config["team_key"] = task_manager["team_key"]
        if task_manager.get("sync_comments"):
            tm_config["sync_comments"] = True
        config["task_manager"] = tm_config

    # LLM retry section (only if customized)
    # Retry step returns: retry_custom, retry_max_retries, retry_base_delay, etc.
    if llm_retry.get("retry_custom", False):
        config["llm"] = {
            "retry": {
                "max_retries": llm_retry.get("retry_max_retries", 3),
                "base_delay": llm_retry.get("retry_base_delay", 1.0),
                "max_delay": llm_retry.get("retry_max_delay", 60.0),
                "multiplier": llm_retry.get("retry_multiplier", 2.0),
            }
        }

    # Security section (only if modified from defaults)
    # Security step returns: security_custom, security_allow_dangerous,
    # security_blocked_commands, security_blocked_env_files
    allow_dangerous = security.get("security_allow_dangerous", False)
    blocked_cmds = security.get("security_blocked_commands")
    blocked_env = security.get("security_blocked_env_files")
    has_security_changes = allow_dangerous or blocked_cmds or blocked_env
    if has_security_changes:
        security_config: dict[str, Any] = {}
        if allow_dangerous:
            security_config["allow_dangerous"] = True
        if blocked_cmds:
            security_config["blocked_patterns"] = blocked_cmds
        if blocked_env:
            security_config["blocked_env_files"] = blocked_env
        if security_config:
            config["security"] = security_config

    # Webhooks section
    if webhooks.get("enabled", False):
        webhook_config: dict[str, Any] = {
            "port": webhooks.get("port", 8000),
            "host": webhooks.get("host", "0.0.0.0"),
        }
        providers = webhooks.get("providers", {})
        if providers:
            webhook_config["providers"] = {}
            for name, pcfg in providers.items():
                if pcfg.get("enabled", False):
                    webhook_config["providers"][name] = {
                        "enabled": True,
                        "secret_env": pcfg.get("secret_env"),
                        "command_prefix": pcfg.get("command_prefix", "/adw"),
                        "trigger_label": pcfg.get("trigger_label", "adw"),
                    }
        config["webhook"] = webhook_config

    # Generate YAML with header comment
    header = f"# Generated by ADW Init Wizard\n# Date: {date.today().isoformat()}\n\n"
    yaml_content = yaml.dump(config, default_flow_style=False, sort_keys=False)
    return header + yaml_content


def generate_phase_configs(state: WizardState) -> dict[str, str]:
    """Generate phase-specific config.yaml files.

    Only generates configs for phases that have custom settings.
    Preserves all collected configuration fields including phase-specific
    options like enable_review, enable_tests, max_iterations, etc.

    Args:
        state: Current wizard state.

    Returns:
        Dict mapping relative file paths to their content.
    """
    import yaml

    files: dict[str, str] = {}
    phases = state.get_step_config("phases")

    # Phases step returns: customized (bool), phases (dict of phase name -> config)
    phases_dict = phases.get("phases", {})

    if not phases.get("customized", False):
        return files

    for phase, phase_config in phases_dict.items():
        if phase_config:
            # Build phase config dict - include all non-None values
            # This preserves all fields including phase-specific options
            # like enable_review, enable_tests, max_iterations, triage_mode, etc.
            config: dict[str, Any] = {}

            for key, value in phase_config.items():
                # Include all values except None
                # This ensures booleans (False) and zero values are preserved
                if value is not None:
                    config[key] = value

            if config:
                header = (
                    f"# Phase configuration for {phase}\n"
                    "# Generated by ADW Init Wizard\n\n"
                )
                yaml_content = yaml.dump(
                    config, default_flow_style=False, sort_keys=False
                )
                files[f"commands/{phase}/config.yaml"] = header + yaml_content

    return files


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
        import contextlib

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
