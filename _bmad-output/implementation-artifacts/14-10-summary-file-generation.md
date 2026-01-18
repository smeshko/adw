# Story 14.10: Summary & File Generation

Status: ready-for-dev
Linear Issue: pending
Epic: 14 - Interactive Init Wizard
Created: 2026-01-18

---

## Story

As a user completing the wizard,
I want to see a summary and confirm before files are created,
so that I can verify my choices before committing.

## Acceptance Criteria

- [ ] Displays Rich panel with full configuration summary:
  ```
  ╭─ Configuration Summary ─────────────────────────────────╮
  │                                                         │
  │  Basics:                                                │
  │    Name: my-project                                     │
  │    Language: python                                     │
  │    Platform: api                                        │
  │    Test: pytest                                         │
  │    Build: python -m build                               │
  │                                                         │
  │  Git: ✓ Enabled (feature/, auto-PR)                    │
  │  Ports: Default (9100/9200)                            │
  │  Task Manager: Linear (RULE-xxx)                       │
  │  Phases: plan ✎, build ✎, validate (default), doc     │
  │  LLM Retry: Custom (5 retries, 2s base)                │
  │  Security: Default (safe mode)                         │
  │  Webhooks: Linear ✓, GitHub ✗                          │
  │                                                         │
  │  Files to create:                                       │
  │    .adw/project.yaml                                    │
  │    .adw/commands/plan/config.yaml                      │
  │    .adw/commands/build/config.yaml                     │
  │                                                         │
  ╰─────────────────────────────────────────────────────────╯
  ```
- [ ] Prompts "Create configuration? [Y/n]"
- [ ] If No, prompts "Start over or cancel? [s/C]"
- [ ] If Yes:
  - [ ] Creates `.adw/` directory if not exists
  - [ ] Generates `project.yaml` with all settings
  - [ ] Generates `commands/{phase}/config.yaml` for customized phases only
  - [ ] Creates `.adw/.gitignore` (ignore runs/, logs)
- [ ] Shows success message:
  ```
  ✓ Configuration created!

  Next steps:
    adw run "your feature description"
    adw --help for more commands
  ```
- [ ] If file write fails, shows error and doesn't create partial config

## Tasks / Subtasks

### Task 1: Create Summary Step Module
- [x] Create `src/adw/cli/wizard/summary.py`
- [x] Define `run_summary_step(state: WizardState) -> bool`
- [x] Import and register in flow controller

### Task 2: Implement Summary Panel Generation
- [x] Create function to generate summary panel from WizardState
- [x] Format each section concisely
- [x] Use checkmarks/icons for enabled features
- [x] List files that will be created

### Task 3: Implement Configuration Confirmation
- [x] Display summary panel
- [x] Prompt for confirmation
- [x] Handle "Start over" option (return to step 1)
- [x] Handle "Cancel" option (exit wizard)

### Task 4: Implement project.yaml Generation
- [x] Create function to generate project.yaml from WizardState
- [x] Map all wizard state fields to config structure
- [x] Use Pydantic model for serialization
- [x] Handle optional sections (null/empty when disabled)

### Task 5: Implement Phase config.yaml Generation
- [x] For each customized phase, generate config.yaml
- [x] Create `commands/{phase}/` directory
- [x] Generate phase-specific config file
- [x] Only create for phases with custom settings

### Task 6: Implement .gitignore Generation
- [x] Create `.adw/.gitignore` with:
  - `runs/`
  - `logs/`
  - `*.log`
  - `state.json`

### Task 7: Implement Atomic File Writing
- [x] Collect all files to create
- [x] Validate all can be written before starting
- [x] Write files with error handling
- [x] Rollback on any failure (delete partial)

### Task 8: Implement Success Message
- [x] Display success message with Rich formatting
- [x] Show next steps
- [x] Include helpful command examples

### Task 9: Write Unit Tests
- [ ] Test summary panel generation
- [ ] Test project.yaml generation
- [ ] Test phase config generation
- [ ] Test .gitignore generation
- [ ] Test atomic write success
- [ ] Test atomic write rollback on failure
- [ ] Test start over flow
- [ ] Test cancel flow

---

## Dependencies

### Depends On
- 14.1 (Wizard Entry Point & Flow Control) - provides WizardState
- 14.2 (Basics Configuration Step) - basics config to display/generate
- 14.3 (Git Integration Step) - git config to display/generate
- 14.4 (Port Configuration Step) - port config to display/generate
- 14.5 (Task Manager Setup) - task manager config to display/generate
- 14.6 (Phase Customization) - phase config to display/generate
- 14.7 (LLM Retry Configuration) - retry config to display/generate
- 14.8 (Security Configuration) - security config to display/generate
- 14.9 (Webhook Server Setup) - webhook config to display/generate

### Blocks
- None (final step)

### Parallel With
- None (must follow all other steps)

---

## Developer Context

### Technical Requirements

**project.yaml Structure:**
```yaml
# Generated by ADW Init Wizard
# Date: 2026-01-18

name: my-project
language: python
platform: api

commands:
  test: pytest
  build: python -m build

git:
  enabled: true
  branch_prefix: feature/
  auto_create_pr: true

ports:
  backend_start: 9100
  frontend_start: 9200

task_manager:
  type: linear
  team_key: RULE
  sync_comments: true
  # ... other fields

llm:
  retry:
    max_retries: 3
    base_delay: 1.0
    max_delay: 60.0
    multiplier: 2.0

security:
  allow_dangerous: false
  blocked_command_patterns: []
  blocked_env_files: []

webhooks:
  enabled: false
  # ... when enabled
```

**Atomic Write Pattern:**
```python
import tempfile
import shutil
from pathlib import Path

def atomic_write_config(adw_dir: Path, files: dict[str, str]) -> None:
    """Write all config files atomically.

    Args:
        adw_dir: Path to .adw/ directory
        files: Dict of relative_path -> content

    Raises:
        ConfigWriteError: If any write fails (partial writes rolled back)
    """
    created_paths: list[Path] = []

    try:
        # Create .adw directory
        adw_dir.mkdir(parents=True, exist_ok=True)
        created_paths.append(adw_dir)

        # Write each file
        for rel_path, content in files.items():
            full_path = adw_dir / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
            created_paths.append(full_path)

    except Exception as e:
        # Rollback: delete created files in reverse order
        for path in reversed(created_paths):
            if path.is_file():
                path.unlink()
            elif path.is_dir() and not any(path.iterdir()):
                path.rmdir()
        raise ConfigWriteError(f"Failed to write config: {e}") from e
```

### Architecture Compliance

**Layer Boundaries:**
- Wizard step in `src/adw/cli/wizard/summary.py`
- Config models in `src/adw/models/config.py`
- YAML serialization via Pydantic

**Existing Config Structure:**
- Check `src/adw/models/config.py` for `ProjectConfig`
- Ensure generated YAML matches expected structure
- Use existing config loading to validate output

### Library & Framework Requirements

| Library | Usage | Import Pattern |
|---------|-------|----------------|
| Rich | Panels, formatting | `from rich.panel import Panel` |
| PyYAML | YAML generation | `import yaml` |
| Pydantic | Model serialization | Model's `model_dump()` |

**Summary Panel Pattern:**
```python
from rich.panel import Panel
from rich.table import Table
from rich.console import Console

console = Console()

def generate_summary_panel(state: WizardState) -> Panel:
    """Generate Rich panel with configuration summary."""
    lines = []

    # Basics section
    lines.append("[bold]Basics:[/]")
    lines.append(f"  Name: {state.project_name}")
    lines.append(f"  Language: {state.language}")
    lines.append(f"  Platform: {state.platform}")
    lines.append(f"  Test: {state.test_command or 'none'}")
    lines.append(f"  Build: {state.build_command or 'none'}")
    lines.append("")

    # Git section
    if state.git_enabled:
        lines.append(f"[green]Git:[/] ✓ Enabled ({state.git_branch_prefix}, {'auto-PR' if state.git_auto_create_pr else 'manual PR'})")
    else:
        lines.append("[dim]Git:[/] ✗ Disabled")

    # ... more sections

    return Panel(
        "\n".join(lines),
        title="Configuration Summary",
        border_style="green"
    )
```

### File Structure Requirements

**New Files to Create:**
```
src/adw/cli/wizard/
└── summary.py            # Summary and file generation step
```

**Files to Modify:**
```
src/adw/cli/wizard/flow.py    # Register summary step (final)
```

**Files Generated by Wizard:**
```
.adw/
├── project.yaml          # Main configuration
├── .gitignore            # Ignore runs/logs
└── commands/             # Only if phases customized
    ├── plan/
    │   └── config.yaml
    ├── build/
    │   └── config.yaml
    └── validate/
        └── config.yaml
```

### Testing Requirements

**Test Files:**
```
tests/unit/cli/wizard/
└── test_summary.py       # Summary step tests
```

**Test Cases:**
```python
# Summary generation
def test_summary_panel_basics(mocker):
    state = WizardState(language="python", platform="cli", ...)
    panel = generate_summary_panel(state)
    assert "python" in str(panel)
    assert "cli" in str(panel)

def test_summary_panel_all_features(mocker):
    # Full state with all features
    # Verify all sections present

# File generation
def test_project_yaml_generation():
    state = WizardState(...)
    yaml_content = generate_project_yaml(state)
    # Parse and verify structure

def test_phase_config_generation():
    state = WizardState(phases_customized=True, ...)
    files = generate_phase_configs(state)
    assert "commands/plan/config.yaml" in files

# Atomic write
def test_atomic_write_success(tmp_path):
    files = {"project.yaml": "...", ".gitignore": "..."}
    atomic_write_config(tmp_path / ".adw", files)
    assert (tmp_path / ".adw/project.yaml").exists()

def test_atomic_write_rollback(tmp_path, mocker):
    # Mock write failure on second file
    # Verify first file rolled back

# Confirmation flow
def test_confirm_create(mocker):
    # Mock Yes response
    # Verify files created

def test_confirm_start_over(mocker):
    # Mock No, then 's'
    # Verify returns to step 1

def test_confirm_cancel(mocker):
    # Mock No, then 'c'
    # Verify clean exit
```

**Mock Requirements:**
- Mock Rich prompts
- Mock file system for write tests
- Use `tmp_path` fixture for real file tests

---

## Previous Story Intelligence

**From Stories 14.1-14.9:**
- Complete WizardState structure with all fields
- All configuration options and their defaults
- Validation rules for each field

**Expected WizardState Input:**
- All fields from all previous steps
- No additional input needed - this step only consumes state

---

## Git Intelligence

**Existing Config Files:**
- Check `.adw/project.yaml` examples in test fixtures
- Check `src/adw/models/config.py` for field names
- Ensure YAML keys match expected config structure

**Search Commands:**
```bash
grep -r "project.yaml" tests/
grep -r "model_dump" src/adw/models/
```

---

## Latest Technical Information

**Pydantic YAML Serialization:**
```python
import yaml
from pydantic import BaseModel

class ProjectConfig(BaseModel):
    name: str
    language: str
    ...

config = ProjectConfig(...)
yaml_str = yaml.dump(
    config.model_dump(exclude_none=True),
    default_flow_style=False,
    sort_keys=False
)
```

**Rich Panel Formatting:**
- Use `[bold]`, `[dim]`, `[green]`, etc. for emphasis
- Use `✓` and `✗` for enabled/disabled
- Use consistent indentation for nested items

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- YAML config in `.adw/project.yaml`
- Config models in `src/adw/models/`
- Rich for all CLI output

---

## Dev Notes

- This is the final step that produces actual output
- Atomic writing prevents partial/corrupt configs
- Summary should be comprehensive but not overwhelming
- "Start over" is important for users who made mistakes

### Summary Panel Sections
1. **Basics**: Name, language, platform, test, build
2. **Git**: Enabled/disabled, branch prefix, auto-PR
3. **Ports**: Custom or default values
4. **Task Manager**: Type, team key, key options
5. **Phases**: Which customized, key settings
6. **LLM Retry**: Custom or default
7. **Security**: Safe mode or custom
8. **Webhooks**: Which providers enabled
9. **Files to Create**: List of paths

### References

- [Source: _bmad-output/epics/epic-14-interactive-init-wizard.md#Story-14.10]
- [Source: _bmad-output/architecture-summary.md#Configuration-Driven]
- [Source: src/adw/models/config.py - config models]

---

## Dev Agent Record

### Context Reference

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

### File List

