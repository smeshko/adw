"""Summary and file generation step for the wizard.

This module handles the final step of the wizard where users see a summary
of their configuration choices, confirm, and have the configuration files
generated.
"""

from __future__ import annotations

import contextlib
import signal
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from adw.config.initializer import generate_env_template, generate_gitignore
from adw.exceptions import ConfigError
from adw.fs import atomic_write

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


def run_summary_step(cfg: WizardConfig, console: Console, root: Path) -> bool:
    """Show the summary, ask to confirm, then write the configuration files.

    Args:
        cfg: The wizard's answers, keyed by section.
        console: Console for output.
        root: The project root directory; files go to root/.adw.

    Returns:
        True if the files were written; False if the user declined or the
        write failed, in which case nothing was written.
    """
    console.print()
    console.print(generate_summary_panel(cfg))

    if not _prompt_confirmation(console):
        console.print("\n[yellow]Setup cancelled. Nothing was written.[/]")
        return False

    adw_dir = root / ".adw"
    files = _generate_all_files(cfg)
    try:
        with _hold_interrupts():
            atomic_write_config(adw_dir, files)

            global_registry = cfg.get("global_registry", {})
            if global_registry.get("global_registry_enabled", False):
                _register_in_global_dashboard(
                    root,
                    global_registry.get("global_registry_name"),
                    console,
                )

            _show_success_message(console, adw_dir)
    except ConfigWriteError as e:
        console.print(f"\n[red]Error writing configuration:[/] {e.message}")
        if e.suggestion:
            console.print(f"[dim]Suggestion: {e.suggestion}[/]")
        console.print("[yellow]No files were written.[/]")
        return False
    return True


@contextlib.contextmanager
def _hold_interrupts() -> Iterator[None]:
    """Ignore Ctrl+C for the duration of the block.

    init's SIGINT handler reports "No files created" and exits. Holding it off
    while the files are written and reported keeps that true: an interrupt
    either lands before the write or is dropped.
    """
    previous = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, previous)


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
    """Write all config files as one transaction.

    Each file is replaced atomically (adw.fs.atomic_write), and the set is
    rolled back as a whole: if any write fails, pre-existing files that were
    overwritten are restored from backup and newly created files are removed.

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

            atomic_write(full_path, content)

            # Only track newly created files for deletion on rollback
            if not file_existed:
                newly_created_paths.append(full_path)

    except OSError as e:
        # Rollback: restore backups for overwritten files
        for path, original_content in backups.items():
            with contextlib.suppress(OSError):
                atomic_write(path, original_content)

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


def _show_success_message(console: Console, adw_dir: Path) -> None:
    """Report the written configuration and what to do next.

    Args:
        console: Console for output.
        adw_dir: The .adw directory the files were written to.
    """
    console.print()
    console.print(f"[bold green]\u2713 Configuration written to {adw_dir}[/]")
    console.print()
    console.print("[bold]Next steps:[/]")
    console.print('  adw run "your feature description"')
    console.print("  adw --help for more commands")
