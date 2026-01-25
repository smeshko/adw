# Story 16.1: Project Registry

Status: ready
Linear Issue: not-configured
Epic: 16 - Cross-Project Dashboard
Created: 2026-01-25

---

## Story

As a user,
I want to explicitly register and manage projects with ADW,
So that I can control which projects appear in cross-project views.

## Acceptance Criteria

**Given** command `adw register` in a project directory
**When** executed
**Then** the project path and name are added to `~/.adw/projects.yaml`

**Given** command `adw register --name "my-api"`
**When** executed
**Then** the custom name is used instead of directory name

**Given** a project already registered
**When** `adw register` is run again
**Then** the registration is updated (not duplicated)

**Given** command `adw unregister`
**When** executed
**Then** the project is removed from the registry

**Given** command `adw projects`
**When** executed
**Then** all registered projects are listed with their paths and run counts

**Given** command `adw projects --discover`
**When** executed
**Then** unique projects from `~/.adw/index.jsonl` are listed (auto-discovery)

**Given** user runs `adw init` wizard
**When** the GLOBAL_REGISTRY step is reached (after BASICS step)
**Then** user is prompted: "Register this project in ADW global dashboard? (Y/n)"

**Given** user confirms registration in wizard
**When** wizard completes
**Then** project is automatically added to `~/.adw/projects.yaml`

**Given** user declines registration in wizard
**When** wizard completes
**Then** project is NOT added to registry (can be added later via `adw register`)

**Given** user confirms registration
**When** prompted for custom name
**Then** user can optionally provide a display name (default: directory name from BASICS step)

## Tasks / Subtasks

### Task 1: Create ProjectRegistry Model
- [x] Create `src/adw/models/registry.py` with:
  - `RegisteredProject` model: `path: str`, `name: str`, `registered_at: datetime`
  - `ProjectRegistry` model: `projects: list[RegisteredProject]`
- [x] Add YAML serialization support via Pydantic
- [x] Export from `src/adw/models/__init__.py`
- [x] Write unit tests in `tests/unit/models/test_registry.py`

### Task 2: Create ProjectRegistryManager Core Class
- [x] Create `src/adw/core/project_registry.py` with `ProjectRegistryManager` class
- [x] Implement methods:
  - `register(path: Path, name: str | None = None) -> RegisteredProject`
  - `unregister(path: Path) -> bool`
  - `get_all() -> list[RegisteredProject]`
  - `get_by_path(path: Path) -> RegisteredProject | None`
  - `discover_from_index() -> list[RegisteredProject]` (uses IndexManager)
- [x] Implement YAML file persistence at `~/.adw/projects.yaml`
- [x] Handle duplicate detection (update existing registration)
- [x] Support `ADW_TEST_REGISTRY_PATH` env var for testing (mirrors IndexManager pattern)
- [x] Write unit tests in `tests/unit/core/test_project_registry.py`

### Task 3: Implement `adw register` Command
- [ ] Add `register` command to `src/adw/cli/app.py`
- [ ] Accept optional `--name` parameter
- [ ] Validate current directory has `.adw/` folder (is an ADW project)
- [ ] Display success message with project path and name
- [ ] Handle already-registered case (update, show message)
- [ ] Write unit tests in `tests/unit/cli/test_register.py`

### Task 4: Implement `adw unregister` Command
- [ ] Add `unregister` command to `src/adw/cli/app.py`
- [ ] Remove current project from registry
- [ ] Display success message or "not registered" message
- [ ] Write unit tests in `tests/unit/cli/test_unregister.py`

### Task 5: Implement `adw projects` Command
- [ ] Add `projects` command to `src/adw/cli/app.py`
- [ ] Display table with: Name, Path, Registered At, Run Count
- [ ] Run count from IndexManager.get_recent_runs() filtered by project_path
- [ ] Implement `--discover` flag to show projects from `index.jsonl`
- [ ] Implement `--json` flag for machine-readable output
- [ ] Sort by name (alphabetical) by default
- [ ] Write unit tests in `tests/unit/cli/test_projects.py`

### Task 6: Create GLOBAL_REGISTRY Wizard Step
- [ ] Create `src/adw/cli/wizard/global_registry.py` with:
  - `GlobalRegistryStepHandler` class
  - `run_global_registry_step()` function
- [ ] Prompt: "Register this project in ADW global dashboard? (Y/n)"
- [ ] If yes, prompt: "Custom display name (Enter for 'project-name'):"
- [ ] Store in wizard state: `global_registry_enabled: bool`, `global_registry_name: str | None`
- [ ] Write unit tests in `tests/unit/cli/wizard/test_global_registry.py`

### Task 7: Integrate GLOBAL_REGISTRY into Wizard Flow
- [ ] Update `src/adw/cli/wizard/flow.py`:
  - Add `GLOBAL_REGISTRY = "global_registry"` to `WizardStep` enum (after BASICS)
  - Add to `STEP_SEQUENCE` list (between BASICS and GIT)
  - Add title: `"Global Dashboard Registration"`
- [ ] Update `src/adw/cli/wizard/__init__.py` to export new handler
- [ ] Update `src/adw/cli/wizard/summary.py` to call `ProjectRegistryManager.register()` if enabled
- [ ] Write integration test for wizard flow with GLOBAL_REGISTRY

### Task 8: Write Integration Tests
- [ ] Test full flow: `adw register` -> `adw projects` -> `adw unregister`
- [ ] Test wizard flow with GLOBAL_REGISTRY step
- [ ] Test `--discover` with IndexManager integration
- [ ] Test run count calculation
- [ ] Test edge cases: invalid paths, permissions, concurrent access

---

## Dependencies

- **Depends On:** None (Wave 1 - start immediately)
- **Blocks:** 16.2 (Global Run List), 16.3 (Cross-Project Statistics), 16.5 (TUI Dashboard)
- **Can Parallel With:** None

### Dependency Rationale
- This is the foundation story for Epic 16
- All subsequent stories depend on the project registry for filtering and display
- Story 16.2 needs `adw projects` to list registered projects
- Story 16.5 dashboard needs registry for project breakdown panel

---

## Relevant Feature Documentation

**Related Patterns:**
- CLI commands: See `src/adw/cli/app.py` for command registration patterns
- Wizard steps: See `src/adw/cli/wizard/basics.py`, `src/adw/cli/wizard/git.py` for step handler patterns
- File persistence: See `src/adw/core/index_manager.py` for `~/.adw/` file management patterns
- Pydantic models: See `src/adw/models/index.py` for model patterns

**Key Files to Reference:**
- `/Users/A1E6E98/Developer/Projects/adw/adw-final/src/adw/cli/wizard/flow.py` - WizardStep enum, STEP_SEQUENCE
- `/Users/A1E6E98/Developer/Projects/adw/adw-final/src/adw/cli/wizard/basics.py` - Step handler pattern
- `/Users/A1E6E98/Developer/Projects/adw/adw-final/src/adw/core/index_manager.py` - File persistence pattern
- `/Users/A1E6E98/Developer/Projects/adw/adw-final/src/adw/cli/list.py` - CLI command pattern with Rich tables

---

## Developer Context

### Technical Requirements

1. **Registry File Location**
   - Path: `~/.adw/projects.yaml`
   - Format: YAML (human-readable, easily editable)
   - Create parent directories if needed

2. **Schema Definition**
   ```yaml
   projects:
     - path: /Users/dev/my-api
       name: my-api
       registered_at: 2026-01-25T10:00:00Z
     - path: /Users/dev/frontend
       name: frontend-app
       registered_at: 2026-01-25T14:30:00Z
   ```

3. **Environment Variable Override**
   - `ADW_TEST_REGISTRY_PATH` - Override registry path for testing
   - Mirrors the `ADW_TEST_INDEX_PATH` pattern in IndexManager

4. **Run Count Calculation**
   - Use `IndexManager.get_recent_runs(project_path=path)` to count runs
   - Only count runs from the main index (not archives)

### Architecture Compliance

**File Locations:**
```
src/adw/
├── models/
│   └── registry.py          # NEW: RegisteredProject, ProjectRegistry models
├── core/
│   └── project_registry.py  # NEW: ProjectRegistryManager class
├── cli/
│   ├── app.py               # MODIFY: Add register, unregister, projects commands
│   └── wizard/
│       ├── flow.py          # MODIFY: Add GLOBAL_REGISTRY to WizardStep enum
│       ├── global_registry.py  # NEW: GlobalRegistryStepHandler
│       ├── summary.py       # MODIFY: Call registry on wizard complete
│       └── __init__.py      # MODIFY: Export new handler
```

**Model Pattern (from models/index.py):**
```python
# src/adw/models/registry.py
from datetime import datetime
from pydantic import BaseModel, Field

class RegisteredProject(BaseModel):
    """A project registered in the global registry."""
    path: str = Field(..., description="Absolute path to project directory")
    name: str = Field(..., description="Display name for the project")
    registered_at: datetime = Field(..., description="When project was registered (UTC)")

class ProjectRegistry(BaseModel):
    """Global project registry stored at ~/.adw/projects.yaml."""
    projects: list[RegisteredProject] = Field(default_factory=list)
```

**CLI Command Pattern (from cli/status.py):**
```python
@app.command()
def register(
    name: str | None = typer.Option(
        None,
        "--name",
        "-n",
        help="Custom display name for the project",
    ),
) -> None:
    """Register current project in global ADW dashboard."""
    # Implementation here
```

**Wizard Step Pattern (from cli/wizard/git.py):**
```python
class GlobalRegistryStepHandler:
    """Handler for the global registry wizard step."""

    def execute(self, state: WizardState, console: Console) -> dict[str, Any]:
        """Execute the global registry step."""
        return run_global_registry_step(state, console)


def run_global_registry_step(
    state: WizardState,
    console: Console,
) -> dict[str, Any]:
    """Execute the global registry step."""
    # Prompt for registration
    register = Confirm.ask(
        "Register this project in ADW global dashboard?",
        default=True,
        console=console,
    )

    if not register:
        return {"global_registry_enabled": False, "global_registry_name": None}

    # Get project name from basics step
    basics_config = state.config.get("basics", {})
    default_name = Path.cwd().name

    # Prompt for custom name
    custom_name = Prompt.ask(
        f"Custom display name",
        default=default_name,
        console=console,
    )

    return {
        "global_registry_enabled": True,
        "global_registry_name": custom_name.strip() or default_name,
    }
```

**File Persistence Pattern (from core/index_manager.py):**
```python
class ProjectRegistryManager:
    """Manages the global project registry at ~/.adw/projects.yaml."""

    def __init__(self, registry_path: Path | None = None) -> None:
        import os
        env_path = os.environ.get("ADW_TEST_REGISTRY_PATH")
        if registry_path is not None:
            self.registry_path = registry_path
        elif env_path:
            self.registry_path = Path(env_path)
        else:
            self.registry_path = Path.home() / ".adw" / "projects.yaml"

    def register(self, path: Path, name: str | None = None) -> RegisteredProject:
        """Register or update a project in the registry."""
        # Load existing registry
        registry = self._load_registry()

        # Check for existing entry
        path_str = str(path.resolve())
        existing = next((p for p in registry.projects if p.path == path_str), None)

        if existing:
            # Update existing
            existing.name = name or path.name
            existing.registered_at = datetime.now(UTC)
        else:
            # Add new
            project = RegisteredProject(
                path=path_str,
                name=name or path.name,
                registered_at=datetime.now(UTC),
            )
            registry.projects.append(project)

        # Save
        self._save_registry(registry)
        return existing or project
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| Typer | 0.21.0 | CLI commands |
| Rich | 14.1.0 | Table display, prompts |
| Pydantic | 2.12+ | Model validation |
| PyYAML | 6.0+ | Registry file format |

**No New Dependencies Required**

### File Structure Requirements

**New Files:**
- `src/adw/models/registry.py`
- `src/adw/core/project_registry.py`
- `src/adw/cli/wizard/global_registry.py`
- `tests/unit/models/test_registry.py`
- `tests/unit/core/test_project_registry.py`
- `tests/unit/cli/test_register.py`
- `tests/unit/cli/test_unregister.py`
- `tests/unit/cli/test_projects.py`
- `tests/unit/cli/wizard/test_global_registry.py`

**Modified Files:**
- `src/adw/models/__init__.py` - Export RegisteredProject, ProjectRegistry
- `src/adw/cli/app.py` - Add register, unregister, projects commands
- `src/adw/cli/wizard/flow.py` - Add GLOBAL_REGISTRY enum and step
- `src/adw/cli/wizard/summary.py` - Register project on wizard completion
- `src/adw/cli/wizard/__init__.py` - Export GlobalRegistryStepHandler

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/models/test_registry.py
class TestRegisteredProject:
    def test_create_with_required_fields(self): ...
    def test_path_is_string(self): ...
    def test_registered_at_is_datetime(self): ...

class TestProjectRegistry:
    def test_empty_projects_list_by_default(self): ...
    def test_yaml_serialization(self): ...

# tests/unit/core/test_project_registry.py
class TestProjectRegistryManager:
    def test_register_new_project(self): ...
    def test_register_with_custom_name(self): ...
    def test_register_updates_existing(self): ...
    def test_unregister_removes_project(self): ...
    def test_unregister_nonexistent_returns_false(self): ...
    def test_get_all_returns_registered_projects(self): ...
    def test_get_by_path_finds_project(self): ...
    def test_discover_from_index_returns_unique_projects(self): ...
    def test_uses_env_var_for_path(self): ...

# tests/unit/cli/test_register.py
class TestRegisterCommand:
    def test_register_current_directory(self): ...
    def test_register_with_custom_name(self): ...
    def test_register_requires_adw_project(self): ...
    def test_register_updates_existing(self): ...

# tests/unit/cli/test_projects.py
class TestProjectsCommand:
    def test_list_registered_projects(self): ...
    def test_list_empty_registry(self): ...
    def test_discover_flag(self): ...
    def test_json_output(self): ...
    def test_includes_run_count(self): ...

# tests/unit/cli/wizard/test_global_registry.py
class TestGlobalRegistryStep:
    def test_prompts_for_registration(self): ...
    def test_default_is_yes(self): ...
    def test_prompts_for_custom_name(self): ...
    def test_uses_directory_name_as_default(self): ...
    def test_declined_sets_enabled_false(self): ...
```

**Test Coverage Target:** >80%

---

## Previous Story Intelligence

This is the first story in Epic 16 (Cross-Project Dashboard). No previous story learnings available.

**Relevant Patterns from Other Epics:**
- Epic 12 established the wizard step pattern with TaskManagerStepHandler
- IndexManager established the `~/.adw/` file management pattern
- CLI commands follow consistent patterns with `--json` flags for machine output

---

## Git Intelligence

**Recent Relevant Commits:**
- Wizard steps: Stories in Epic 6 (BASICS, GIT, etc.)
- IndexManager: Story 7.0 (Workflow Execution Index)
- CLI commands: Stories 6.3-6.4 (status, list)

**Established Patterns:**
- Wizard handlers in separate files per step
- `WizardStep` enum defines step order
- Commands registered in `app.py` with `@app.command()` decorator
- Rich tables for CLI list output
- `--json` flag for machine-readable output

---

## Latest Technical Information

**Pydantic YAML Support (2025):**
- Use `pydantic-yaml` or manual `yaml.safe_dump()` with `model_dump()`
- For simplicity, use `yaml.safe_load()` and `yaml.safe_dump()`
- Pydantic 2.x supports `model_validate()` from dict

**Rich Table Best Practices:**
- Use `Table(title="...")` for headers
- Use `style="..."` for column styling
- Use `max_width` for path truncation

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **All models in models/**: RegisteredProject, ProjectRegistry go in `models/`
- **Exception hierarchy**: Use ADWError if registry operations fail
- **Type annotations required**: All functions fully typed
- **Rich for CLI output**: Use Rich Console and Tables
- **Structured logging**: Use logger with structured fields

---

## Dev Notes

### Implementation Approach

1. Start with models (RegisteredProject, ProjectRegistry)
2. Implement ProjectRegistryManager with file persistence
3. Add CLI commands (register, unregister, projects)
4. Create wizard step handler
5. Integrate wizard step into flow
6. Write comprehensive tests

### Key Design Decisions

1. **YAML over JSON**: Human-readable, easily editable by users
2. **Wizard Step Position**: After BASICS, before GIT (early in flow)
3. **Default Registration**: Default to Yes in wizard (encourage usage)
4. **Run Count**: Calculate on-demand from IndexManager (not stored)
5. **Path Storage**: Store absolute paths for unambiguous identification

### CLI Output Examples

**`adw register` output:**
```
[green]✓[/] Project registered: my-api
  Path: /Users/dev/projects/my-api
  Name: my-api
```

**`adw projects` output:**
```
┌─────────────────────────────────────────────────────────────────────┐
│                        Registered Projects                          │
├───────────────┬────────────────────────────────────┬───────┬────────┤
│ Name          │ Path                               │ Runs  │ Since  │
├───────────────┼────────────────────────────────────┼───────┼────────┤
│ my-api        │ /Users/dev/projects/my-api         │   42  │ 3d ago │
│ frontend-app  │ /Users/dev/projects/frontend       │   18  │ 1w ago │
└───────────────┴────────────────────────────────────┴───────┴────────┘
```

**`adw projects --discover` output:**
```
┌─────────────────────────────────────────────────────────────────────┐
│                   Discovered Projects (from runs)                   │
├───────────────┬────────────────────────────────────┬───────┬────────┤
│ Name          │ Path                               │ Runs  │ Last   │
├───────────────┼────────────────────────────────────┼───────┼────────┤
│ my-api        │ /Users/dev/projects/my-api         │   42  │ 2h ago │
│ other-project │ /Users/dev/other                   │    5  │ 3d ago │
└───────────────┴────────────────────────────────────┴───────┴────────┘

[dim]Tip:[/] Run 'adw register' in a project directory to add it to the registry.
```

### Wizard Step Flow Example

```
Step 2/10: Global Dashboard Registration
──────────────────────────────────────────────────────

Register this project in ADW global dashboard? [Y/n]: y
Custom display name [my-api]:

[dim]Project will be registered as 'my-api'[/]
```

### References

- [Source: _bmad-output/epics/epic-16-cross-project-dashboard.md#Story 16.1]
- [Source: _bmad-output/architecture.md#Future Enhancement: Cross-Project Run Visibility]
- [Source: _bmad-output/project-context.md#Critical Implementation Rules]
- [Source: src/adw/cli/wizard/flow.py#WizardStep enum]
- [Source: src/adw/core/index_manager.py#IndexManager pattern]

---

## Dev Agent Record

### Context Reference

Epic 16: Cross-Project Dashboard - Story 16.1

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

**Task 1 Completed (2026-01-25):**
- Created `RegisteredProject` model with `path`, `name`, `registered_at` fields
- Created `ProjectRegistry` model with `projects` list
- Both models support YAML serialization via Pydantic's `model_dump(mode="json")` + PyYAML
- Exported both models from `src/adw/models/__init__.py`
- 15 unit tests covering model instantiation, validation, and serialization round-trips

**Task 2 Completed (2026-01-25):**
- Created `ProjectRegistryManager` class following IndexManager patterns
- Implemented all required methods: register, unregister, get_all, get_by_path, discover_from_index
- YAML file persistence at `~/.adw/projects.yaml`
- Environment variable override `ADW_TEST_REGISTRY_PATH` for testing
- Duplicate detection updates existing entries rather than creating duplicates
- 25 unit tests covering initialization, registration, unregistration, queries, and persistence

### File List

**New Files:**
- `src/adw/models/registry.py` - RegisteredProject and ProjectRegistry models
- `src/adw/core/project_registry.py` - ProjectRegistryManager class
- `tests/unit/models/test_registry.py` - Unit tests for registry models
- `tests/unit/core/test_project_registry.py` - Unit tests for registry manager

**Modified Files:**
- `src/adw/models/__init__.py` - Added exports for registry models

---

## Dependencies

- **Depends On:** None
- **Blocks:** Story 16.2, Story 16.3, Story 16.5
- **Can Parallel With:** None

### Dependency Rationale
- Story 16.2: Global run list uses projects.yaml for project name resolution
- Story 16.3: Statistics command needs project registry for filtering
- Story 16.5: Dashboard displays registered projects
