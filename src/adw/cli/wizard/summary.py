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

if TYPE_CHECKING:
    from adw.models.wizard import WizardState


class ConfigWriteError(Exception):
    """Raised when configuration file writing fails."""

    pass


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
        console.print(f"\n[red]Error writing configuration:[/] {e}")
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
    if git.get("enabled", False):
        branch_prefix = git.get("branch_prefix", "feature/")
        auto_pr = "auto-PR" if git.get("auto_create_pr", True) else "manual PR"
        lines.append(f"[green]Git:[/] \u2713 Enabled ({branch_prefix}, {auto_pr})")
    else:
        lines.append("[dim]Git:[/] \u2717 Disabled")

    # Ports section
    backend_port = ports.get("backend_start", 9100)
    frontend_port = ports.get("frontend_start", 9200)
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
    customized_phases = phases.get("customized_phases", [])
    if customized_phases:
        phase_list = ", ".join(f"{p} \u270e" for p in customized_phases)
        lines.append(f"[cyan]Phases:[/] {phase_list}")
    else:
        lines.append("[dim]Phases:[/] Default")

    # LLM Retry section
    if llm_retry.get("customized", False):
        max_retries = llm_retry.get("max_retries", 3)
        base_delay = llm_retry.get("base_delay", 1.0)
        lines.append(
            f"[cyan]LLM Retry:[/] Custom ({max_retries} retries, {base_delay}s base)"
        )
    else:
        lines.append("[dim]LLM Retry:[/] Default")

    # Security section
    if security.get("allow_dangerous", False):
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
            provider_str = ", ".join(
                f"{p.title()} \u2713" for p in enabled_providers
            )
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
    files = ["project.yaml", ".gitignore"]

    # Add phase config files for customized phases
    phases = state.get_step_config("phases")
    for phase in phases.get("customized_phases", []):
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
    if git.get("enabled", False):
        config["git"] = {
            "enabled": True,
            "branch_prefix": git.get("branch_prefix", "feature/"),
            "auto_create_pr": git.get("auto_create_pr", True),
        }

    # Ports section (only if non-default)
    backend = ports.get("backend_start", 9100)
    frontend = ports.get("frontend_start", 9200)
    if backend != 9100 or frontend != 9200:
        config["ports"] = {
            "backend_start": backend,
            "frontend_start": frontend,
        }

    # Task manager section
    if task_manager.get("type", "none") != "none":
        tm_config: dict[str, Any] = {
            "type": task_manager["type"],
        }
        if task_manager.get("team_key"):
            tm_config["team_key"] = task_manager["team_key"]
        if task_manager.get("sync_comments"):
            tm_config["sync_comments"] = True
        config["task_manager"] = tm_config

    # LLM retry section (only if customized)
    if llm_retry.get("customized", False):
        config["llm"] = {
            "retry": {
                "max_retries": llm_retry.get("max_retries", 3),
                "base_delay": llm_retry.get("base_delay", 1.0),
                "max_delay": llm_retry.get("max_delay", 60.0),
                "multiplier": llm_retry.get("multiplier", 2.0),
            }
        }

    # Security section (only if modified from defaults)
    has_security_changes = (
        security.get("allow_dangerous", False)
        or security.get("blocked_patterns")
        or security.get("blocked_env_files")
    )
    if has_security_changes:
        security_config: dict[str, Any] = {}
        if security.get("allow_dangerous"):
            security_config["allow_dangerous"] = True
        if security.get("blocked_patterns"):
            security_config["blocked_patterns"] = security["blocked_patterns"]
        if security.get("blocked_env_files"):
            security_config["blocked_env_files"] = security["blocked_env_files"]
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

    Args:
        state: Current wizard state.

    Returns:
        Dict mapping relative file paths to their content.
    """
    import yaml

    files: dict[str, str] = {}
    phases = state.get_step_config("phases")

    customized_phases = phases.get("customized_phases", [])
    phase_configs = phases.get("phase_configs", {})

    for phase in customized_phases:
        phase_config = phase_configs.get(phase, {})
        if phase_config:
            # Build phase config dict
            config: dict[str, Any] = {}

            if phase_config.get("timeout_seconds"):
                config["timeout_seconds"] = phase_config["timeout_seconds"]
            if phase_config.get("pre_hook"):
                config["pre_hook"] = phase_config["pre_hook"]
            if phase_config.get("post_hook"):
                config["post_hook"] = phase_config["post_hook"]
            if phase_config.get("input_files"):
                config["input_files"] = phase_config["input_files"]

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
"""


def atomic_write_config(adw_dir: Path, files: dict[str, str]) -> None:
    """Write all config files atomically.

    Creates files atomically - if any write fails, rolls back
    all created files to prevent partial configuration.

    Args:
        adw_dir: Path to .adw/ directory.
        files: Dict of relative_path -> content.

    Raises:
        ConfigWriteError: If any write fails (partial writes rolled back).
    """
    created_paths: list[Path] = []
    created_dirs: list[Path] = []

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

            # Write file
            full_path.write_text(content)
            created_paths.append(full_path)

    except OSError as e:
        # Rollback: delete created files in reverse order
        for path in reversed(created_paths):
            if path.is_file():
                path.unlink(missing_ok=True)

        # Remove empty directories we created
        for dir_path in reversed(created_dirs):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                dir_path.rmdir()

        raise ConfigWriteError(f"Failed to write config: {e}") from e


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
