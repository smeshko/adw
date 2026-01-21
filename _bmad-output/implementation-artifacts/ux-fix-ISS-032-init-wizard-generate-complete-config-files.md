# Story: UX Fix - Init Wizard Complete Config File Generation

Status: ready-for-dev
Linear Issue: not-configured
Epic: 14 - Interactive Init Wizard
Created: 2026-01-21

---

## Story

As a first-time user completing the init wizard,
I want ALL configuration files generated with every available setting visible,
so that I can discover and customize options directly from my config files without consulting documentation.

## Acceptance Criteria

- [ ] **AC1**: `project.yaml` contains ALL available project-level settings
  - Settings changed by user are written as active YAML
  - Settings NOT changed are written as YAML comments with default values
  - Each commented setting includes a brief description

- [ ] **AC2**: Phase config files (`.adw/commands/{phase}/config.yaml`) generated for ALL phases
  - Currently only generated for phases with `customized=True`
  - After: Always generate for all phases (plan, build, validate, document, ship)
  - Include all available phase settings (enabled, timeout_seconds, input_files, artifacts)
  - Non-customized settings appear as comments with defaults

- [ ] **AC3**: Settings grouped logically with section headers
  - Core settings first (name, language, platform, commands)
  - Git, Task Manager, Ports in logical order
  - LLM, Security, Webhook, Ship at end

- [ ] **AC4**: Comment format is consistent and parseable
  ```yaml
  # timeout_seconds: 300  # Max execution time in seconds (default)
  retry_attempts: 5  # User configured
  ```

- [ ] **AC5**: All existing tests pass
- [ ] **AC6**: New tests verify commented defaults appear correctly

## Tasks / Subtasks

### Task 1: Create Config Registry Module
**Files**: `src/adw/config/registry.py` (NEW)

- [x] 1.1 Create `ConfigRegistry` class with complete settings catalog
  - Store setting name, type, default value, description for every setting
  - Organized by section (project, llm, git, task_manager, etc.)
  - Extract defaults from existing Pydantic models

- [x] 1.2 Add helper method `get_all_settings(section: str) -> list[SettingDefinition]`
  - Returns ordered list of settings for a section
  - SettingDefinition: name, type, default, description, is_nested

- [x] 1.3 Add helper method `get_phase_settings(phase: str) -> list[SettingDefinition]`
  - Returns settings specific to a phase (timeout, enabled, input_files, artifacts)

### Task 2: Create YAML Generator with Comments
**Files**: `src/adw/config/yaml_generator.py` (NEW)

- [x] 2.1 Create `YAMLWithComments` class
  - Track which settings are user-modified vs defaults
  - Generate YAML with inactive settings as comments

- [x] 2.2 Implement `generate_project_yaml(state: WizardState, registry: ConfigRegistry) -> str`
  - For each section: write user values as active, defaults as comments
  - Include section headers (# === Git Integration ===)
  - Include descriptions for commented settings

- [x] 2.3 Implement `generate_phase_yaml(phase: str, config: dict, registry: ConfigRegistry) -> str`
  - Generate complete phase config with commented defaults
  - Always include: enabled, timeout_seconds, input_files, artifacts sections

### Task 3: Update Summary Step to Use New Generator
**Files**: `src/adw/cli/wizard/summary.py`

- [x] 3.1 Import and instantiate ConfigRegistry
- [x] 3.2 Replace `_generate_project_yaml()` with new `YAMLWithComments.generate_project_yaml()`
- [x] 3.3 Update `_generate_phase_configs()` to always generate for all phases
  - Previously: `if phase_config.get("customized"):`
  - After: Always generate, use registry for defaults

- [x] 3.4 Update `_generate_all_files()` to include all phase configs in files dict

### Task 4: Extract Default Values from Models
**Files**: `src/adw/config/registry.py`

- [ ] 4.1 Parse `ProjectConfig` model for field defaults and descriptions
  - Use Pydantic's `model_fields` to extract Field definitions
  - Map Field(default=X, description=Y) to SettingDefinition

- [ ] 4.2 Parse nested configs (LLMConfig, GitConfig, etc.)
  - Recursively extract from nested BaseModel fields
  - Track full path: `llm.timeout_seconds`, `git.branch_prefix`

- [ ] 4.3 Parse PhaseConfig for phase-level defaults
  - Include all: enabled, timeout_seconds, pre_hook, post_hook, input_files

### Task 5: Update Tests
**Files**: `tests/unit/config/test_registry.py` (NEW), `tests/unit/cli/wizard/test_summary.py`

- [ ] 5.1 Test ConfigRegistry returns all expected settings
- [ ] 5.2 Test YAMLWithComments generates correct format
- [ ] 5.3 Test commented settings are syntactically valid (can be uncommented)
- [ ] 5.4 Test all phases generate config files (not just customized ones)
- [ ] 5.5 Update existing summary tests for new generation pattern

---

## Relevant Feature Documentation

**ISS-027 Fix Story** (Prior UX fixes for wizard):
- Established comma-separated phase selection pattern
- Removed unused hook path prompts (SDK uses fixed `pre.sh`/`post.sh`)
- Removed unused review_focus collection
- Pattern for parsing input and providing user feedback on invalid entries

---

## Developer Context

### Technical Requirements

- Use Pydantic v2 `model_fields` API to extract field metadata
- YAML output must be valid (commented lines start with `# `)
- Comments should align for readability
- Maintain backward compatibility - existing configs must still load

### Architecture Compliance

**Config Generation Architecture:**
- `summary.py:_generate_all_files()` orchestrates file generation
- `summary.py:_generate_project_yaml()` builds project.yaml content
- `summary.py:_generate_phase_configs()` builds phase configs
- `atomic_write_config()` writes all files transactionally

**Pattern from ISS-027**: Helper functions with clear responsibility separation:
```python
def _parse_phase_selection(input_str: str) -> tuple[list[str], list[str]]:
    """Returns (valid_phases, invalid_entries) for user feedback."""
```

Apply same pattern:
```python
def _format_setting_as_comment(setting: SettingDefinition) -> str:
    """Format a setting with its default as a YAML comment."""
```

### Library & Framework Requirements

**Pydantic v2 Field Metadata Extraction:**
```python
from pydantic import BaseModel
from pydantic.fields import FieldInfo

class ProjectConfig(BaseModel):
    name: str = Field(..., description="Project name")

# Extract metadata
for name, field_info in ProjectConfig.model_fields.items():
    default = field_info.default
    description = field_info.description
    # Handle Field(default_factory=...) for nested models
```

**YAML with Comments (ruamel.yaml alternative - NOT NEEDED):**
Standard PyYAML cannot preserve comments. Instead, generate YAML as string:
```python
def _yaml_with_comments(active: dict, defaults: list[SettingDefinition]) -> str:
    """Generate YAML string with commented defaults."""
    lines = []
    for setting in defaults:
        if setting.name in active:
            lines.append(f"{setting.name}: {_yaml_value(active[setting.name])}")
        else:
            lines.append(f"# {setting.name}: {_yaml_value(setting.default)}  # {setting.description}")
    return "\n".join(lines)
```

### File Structure Requirements

```
src/adw/config/
├── __init__.py          # Export new classes
├── loader.py            # Existing - no changes needed
├── detector.py          # Existing - no changes needed
├── initializer.py       # Existing - no changes needed
├── registry.py          # NEW - Settings registry with defaults
└── yaml_generator.py    # NEW - YAML generation with comments

src/adw/cli/wizard/
└── summary.py           # MODIFY - Use new generator

tests/unit/config/
├── test_registry.py     # NEW - Registry tests
└── test_yaml_generator.py # NEW - Generator tests

tests/unit/cli/wizard/
└── test_summary.py      # MODIFY - Update for new generation
```

### Testing Requirements

- All tests in `tests/unit/cli/wizard/` must pass
- New tests for ConfigRegistry and YAMLWithComments
- Test that generated YAML with comments is valid when uncommented
- Test backward compatibility: existing project.yaml files still load

**Test Pattern from ISS-027:**
```python
@patch("rich.prompt.Confirm.ask")
@patch("rich.prompt.Prompt.ask")
def test_example(mock_prompt, mock_confirm):
    mock_confirm.side_effect = [True, False]
    mock_prompt.side_effect = ["value1", "value2"]
    # Execute and assert
```

---

## Previous Story Intelligence

**From ISS-027 (Init Wizard Phase Config UX Issues):**
- Established pattern for separating concerns in wizard code
- Helper functions return tuples for success/failure feedback
- User feedback on invalid input before proceeding
- Tests use `side_effect` lists for sequential mock responses

**From Epic 14 Stories (14.1-14.10):**
- `WizardState.collected_config` stores all user input by step name
- `summary.py:_generate_project_yaml()` builds from `state.collected_config`
- Only sections with user input are currently written
- `atomic_write_config()` handles rollback on failure

**Key Learning**: Currently `_generate_phase_configs()` skips phases without `customized=True`:
```python
# summary.py line ~550
if phase_config.get("customized"):
    files[f"commands/{phase}/config.yaml"] = _generate_phase_yaml(phase, phase_config)
```
This must change to always generate.

---

## Git Intelligence

**Recent relevant commits:**
- `589a051` fix(ISS-031): Move PR creation to after document phase
- `251b6c1` fix(ISS-029): Honor phase configuration from command configs
- `1c46dfe` feat(story-15-8): Init Wizard Ship Phase Integration

**Patterns from commits:**
- Config loading now properly merges project.yaml with command configs
- Phase configs at `.adw/commands/{phase}/config.yaml` take precedence
- Ship phase added to wizard flow (14.9)

---

## Latest Technical Information

**Pydantic v2 Field API (current version 2.12+):**
```python
# Access field metadata
field_info: FieldInfo = MyModel.model_fields["field_name"]
field_info.default          # Default value or PydanticUndefined
field_info.default_factory  # Factory function for mutable defaults
field_info.description      # Field description from Field()
field_info.annotation       # Type annotation
```

**YAML Formatting Best Practices:**
- Use 2-space indentation (matches existing configs)
- Place comments on same line as value when brief
- Use block comments for multi-line descriptions
- Align values for visual consistency

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules:
- **All Models in models/**: SettingDefinition model should go in `src/adw/models/config.py` or new `src/adw/models/settings.py`
- **Rich for CLI output**: Summary step uses Rich panels - maintain consistency
- **Type annotations required**: Full typing on all new functions
- **Exception hierarchy**: Use `ConfigError` for config-related failures

---

## Dev Notes

### Implementation Strategy

1. **Registry First**: Create ConfigRegistry with hardcoded settings initially
   - Can later refactor to auto-extract from Pydantic models
   - Allows fine-tuning of descriptions and ordering

2. **Incremental Migration**:
   - Don't remove existing `_generate_project_yaml()` immediately
   - Create new generator alongside, test, then replace

3. **Comment Format Decision**:
   ```yaml
   # Option A: Inline description
   # timeout_seconds: 300  # Max execution time in seconds

   # Option B: Description above
   # Max execution time in seconds
   # timeout_seconds: 300
   ```
   Recommend Option A for compactness.

4. **Handling Nested Configs**:
   ```yaml
   llm:
     # path: claude  # Path to Claude Code executable
     timeout_seconds: 300  # User configured
     # max_retries: 3  # Retry attempts for transient errors
   ```

### Complete Settings Reference

**Project Level:**
| Setting | Default | Description |
|---------|---------|-------------|
| name | Required | Project name |
| language | Required | Programming language |
| platform | "cli" | Target platform (cli/web/api) |
| test_command | None | Command to run tests |
| build_command | None | Command to build project |

**LLM Settings:**
| Setting | Default | Description |
|---------|---------|-------------|
| llm.path | "claude" | Path to Claude Code executable |
| llm.timeout_seconds | 300 | Max execution time |
| llm.max_retries | 3 | Retry attempts |
| llm.model | None | Model override |

**Git Settings:**
| Setting | Default | Description |
|---------|---------|-------------|
| git.enabled | False | Enable git automation |
| git.branch_prefix | "feature/" | Branch name prefix |
| git.auto_commit | True | Commit after phases |
| git.skip_hooks | False | Use --no-verify |
| git.auto_create_pr | True | Create PR on success |
| git.base_branch | None | PR base branch |

**Task Manager:**
| Setting | Default | Description |
|---------|---------|-------------|
| task_manager.type | "none" | Task manager type |
| task_manager.team_key | None | Team ID prefix |
| task_manager.sync_comments | False | Post status comments |
| task_manager.auto_close | False | Close on PR merge |

**Worktree:**
| Setting | Default | Description |
|---------|---------|-------------|
| worktree.enabled | True | Use worktree isolation |
| worktree.base_dir | "trees" | Directory name |
| worktree.max_concurrent | 15 | Concurrent run slots |
| worktree.port_range.backend_start | 9100 | Backend port base |
| worktree.port_range.frontend_start | 9200 | Frontend port base |

**Phase Defaults:**
| Setting | Default | Description |
|---------|---------|-------------|
| enabled | True | Phase enabled |
| timeout_seconds | 300-900 | Varies by phase |
| input_files | {} | Variable→file mappings |

### Source References

- [Source: src/adw/cli/wizard/summary.py:375-534] - Current project.yaml generation
- [Source: src/adw/cli/wizard/summary.py:537-584] - Current phase config generation
- [Source: src/adw/models/config.py:706-878] - ProjectConfig model with defaults
- [Source: src/adw/models/config.py:75-100] - LLMConfig defaults
- [Source: src/adw/models/config.py:638-703] - GitConfig defaults
- [Source: _bmad-output/implementation-artifacts/ux-fix-ISS-027-init-wizard-phase-config-ux-issues.md] - Previous UX fix patterns

---

## Dev Agent Record

### Context Reference

Issue: `_bmad-output/implementation-artifacts/issues/ISS-032-init-wizard-generate-complete-config-files.md`

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

N/A

### Completion Notes List

_To be filled by dev agent_

### File List

_To be filled by dev agent_
