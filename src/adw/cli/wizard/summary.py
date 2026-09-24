"""Summary and file generation step for the wizard.

This module handles the final step of the wizard where users see a summary
of their configuration choices, confirm, and have the configuration files
generated.
"""

from __future__ import annotations

import contextlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from adw.config.initializer import generate_env_template, generate_gitignore
from adw.exceptions import ConfigError

WizardConfig = Mapping[str, dict[str, Any]]
"""The wizard's answers: each step's dict, keyed by its section name."""


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


def run_summary_step(
    cfg: WizardConfig,
    console: Console,
    root: Path,
) -> dict[str, Any]:
    """Execute the summary configuration step.

    This is the main entry point for the summary step, implementing
    the full interactive flow for summary display and file generation.

    Args:
        cfg: The wizard's answers, keyed by section.
        console: Console for output.
        root: The project root directory; files go to root/.adw.

    Returns:
        Configuration dict containing confirmation status and created files.
    """
    # Step 1: Generate and display summary panel
    panel = generate_summary_panel(cfg)
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
        files = _generate_all_files(cfg)
        adw_dir = root / ".adw"
        atomic_write_config(adw_dir, files)

        # Step 4: Register project in web dashboard if enabled
        global_registry = cfg.get("global_registry", {})
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


def generate_summary_panel(cfg: WizardConfig) -> Panel:
    """Generate Rich panel with full configuration summary.

    Args:
        cfg: The wizard's answers, keyed by section.

    Returns:
        Rich Panel with formatted configuration summary.
    """
    lines = []

    # Get configs from collected_config
    basics = cfg.get("basics", {})
    global_registry = cfg.get("global_registry", {})
    git = cfg.get("git", {})
    task_manager = cfg.get("task_manager", {})
    phases = cfg.get("phases", {})
    webhooks = cfg.get("webhooks", {})

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
        lines.append(f"[green]Web Dashboard:[/] ✓ Registered as '{reg_name}'")
    else:
        lines.append("[dim]Web Dashboard:[/] ✗ Not registered")

    # Git section
    branch_prefix = git.get("git_branch_prefix", "feature/")
    lines.append(f"[green]Git:[/] \u2713 Enabled ({branch_prefix})")

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

    # Webhooks section
    if webhooks.get("enabled", False):
        providers = webhooks.get("providers", {})
        enabled_providers = [
            p for p, provider in providers.items() if provider.get("enabled", False)
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
    files = _get_files_to_create()
    for file_path in sorted(files):
        lines.append(f"  .adw/{file_path}")

    return Panel(
        "\n".join(lines),
        title="Configuration Summary",
        border_style="green",
    )


def _get_files_to_create() -> list[str]:
    """Get list of files that will be created.

    Includes a config file for every phase, not just customized ones, so the
    full configuration is visible.

    Returns:
        List of relative file paths (within .adw/).
    """
    from adw.core.constants import PHASE_SEQUENCE

    files = ["project.yaml", ".gitignore", ".env.template"]

    # Add phase config files for ALL phases
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


def _generate_all_files(cfg: WizardConfig) -> dict[str, str]:
    """Generate all configuration files from the wizard's answers.

    Args:
        cfg: The wizard's answers, keyed by section.

    Returns:
        Dict mapping relative file paths to their content.
    """
    files: dict[str, str] = {}

    # Generate project.yaml
    files["project.yaml"] = generate_project_yaml(cfg)

    # Generate .gitignore
    files[".gitignore"] = generate_gitignore()

    # Generate .env.template
    files[".env.template"] = generate_env_template()

    # Generate phase config files
    phase_files = generate_phase_configs(cfg)
    files.update(phase_files)

    return files


def generate_project_yaml(cfg: WizardConfig) -> str:
    """Generate project.yaml content from the wizard's answers.

    Uses the YAMLWithComments generator for comprehensive config
    with commented defaults.

    Args:
        cfg: The wizard's answers, keyed by section.

    Returns:
        YAML content string with all settings visible.
    """
    from adw.config.registry import ConfigRegistry
    from adw.config.yaml_generator import YAMLWithComments

    registry = ConfigRegistry()
    generator = YAMLWithComments(registry)
    return generator.generate_project_yaml(cfg)


def generate_phase_configs(cfg: WizardConfig) -> dict[str, str]:
    """Generate phase-specific config.yaml files for ALL phases.

    Covers every phase, not just customized ones, with commented defaults.

    Args:
        cfg: The wizard's answers, keyed by section.

    Returns:
        Dict mapping relative file paths to their content.
    """
    from adw.config.registry import ConfigRegistry
    from adw.config.yaml_generator import generate_all_phase_configs

    registry = ConfigRegistry()
    return generate_all_phase_configs(cfg, registry)


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
    """Register project in the ADW web dashboard.

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
        console.print(f"[yellow]Warning: Could not register in web dashboard: {e}[/]")


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
