# Story: Per-Phase Config.yaml Loading

<!-- TEMPLATE SECTION: story_header -->
Status: completed
Linear Issue: not-configured
Epic: 12 - Task Manager Integration / Tech Debt
Created: 2026-01-06

---

## Story

<!-- TEMPLATE SECTION: story_requirements -->
As a developer extending ADW or customizing phases,
I want each phase command folder to support an optional `config.yaml` that defines phase-specific defaults,
so that commands can be self-contained packages with bundled configuration that projects can override.

## Acceptance Criteria

- [x] Each phase command folder can have an optional `config.yaml`
- [x] `CommandResolver` detects presence of `config.yaml` in command directories
- [x] `CommandLoader` loads and parses `config.yaml` using Pydantic model
- [x] `CommandConfig` model supports: `timeout_seconds`, `input_files`, `llm`, `artifacts`
- [x] Config is merged with project `adw.yaml` PhaseConfig (project takes precedence)
- [x] Default `config.yaml` files created for bundled phases (plan, build, verify, validate, document)
- [x] Existing behavior preserved when no `config.yaml` exists (backward compatible)
- [x] All existing tests pass
- [x] New tests cover config loading and merging

## Tasks / Subtasks

### Task 1: Create CommandConfig Model
- [x] Add `CommandConfig` model to `src/adw/models/command.py`
- [x] Support fields: `timeout_seconds`, `input_files`, `llm`, `artifacts`, `pre_hook`, `post_hook`
- [x] Add `LLMConfig` nested model for phase-specific LLM settings (model, temperature)
- [x] Add `ArtifactConfig` for artifact capture rules (unifies with ISS-012)
- [x] Add model validation and docstrings

### Task 2: Update CommandResolver
- [x] Add `has_config` detection to `_create_resolved_command()` method
- [x] Check for `config.yaml` presence in command directory
- [x] Update `ResolvedCommand` model with `has_config: bool = False` field

### Task 3: Implement Config Loading in CommandLoader
- [x] Add `_load_config()` method to load and parse `config.yaml`
- [x] Return `CommandConfig | None` (None if no config.yaml exists)
- [x] Handle YAML parsing errors with `ConfigError`
- [x] Add config to `LoadedCommand` model

### Task 4: Implement Config Merging in PhaseRunner
- [x] Add `_merge_configs()` method to PhaseRunner
- [x] Merge command config with project PhaseConfig (project overrides command defaults)
- [x] Apply merged config to: timeout, input_files, llm settings
- [x] Integrate with existing `_load_input_files()` (ISS-015)

### Task 5: Create Default Config Files
- [x] Create `src/adw/defaults/commands/plan/config.yaml`
- [x] Create `src/adw/defaults/commands/build/config.yaml`
- [x] Create `src/adw/defaults/commands/verify/config.yaml`
- [x] Create `src/adw/defaults/commands/validate/config.yaml`
- [x] Create `src/adw/defaults/commands/document/config.yaml`

### Task 6: Testing
- [x] Unit tests for `CommandConfig` model validation
- [x] Unit tests for config loading in CommandLoader
- [x] Unit tests for config merging in PhaseRunner
- [x] Integration tests for end-to-end config flow
- [x] Regression tests ensuring existing behavior unchanged

---

## Relevant Feature Documentation

<!-- TEMPLATE SECTION: conditional_docs_section -->
**Source:** `docs/architecture/adrs/ADR-001-test-reduction-strategy.md`

**Test Writing Guidelines:**
- DO write tests for: validation logic, business rules, error paths, I/O operations
- DON'T write tests for: Pydantic serialization, enum existence, simple attribute assignment
- Use `@pytest.mark.parametrize` to consolidate redundant test variants
- Follow naming: `test_<unit>_<behavior>_<condition>`

---

## Developer Context

<!-- TEMPLATE SECTION: developer_context_section -->
<!-- Critical context extracted from exhaustive artifact analysis -->

### Technical Requirements

<!-- TEMPLATE SECTION: technical_requirements -->
- Python 3.13+
- Pydantic 2.12+ for config model validation
- PyYAML 6.0+ (already used) for YAML parsing
- Maintain backward compatibility - config.yaml is OPTIONAL
- Follow Open/Closed Principle - new config fields without code changes

### Architecture Compliance

<!-- TEMPLATE SECTION: architecture_compliance -->
**Architecture Reference:** `_bmad-output/architecture.md` lines 857-879, 1075

The architecture explicitly specifies `config.yaml` in each phase folder:
```
├── defaults/commands/
│   ├── plan/
│   │   ├── prompt.md
│   │   ├── config.yaml    ← SPECIFIED but NOT IMPLEMENTED
│   │   └── schema.json
```

**Current Implementation Gap:**
- `CommandResolver` only checks for `prompt.md`, `schema.json`, `pre.sh`, `post.sh`
- No `config.yaml` detection or loading exists
- `ResolvedCommand` model has no `has_config` field
- `CommandLoader` has no config loading capability

**Related Component:** ISS-012 (Config-Driven Artifact Capture)
- ISS-012 plans to add `command.yaml` for artifact config
- This story should UNIFY the approach: use `config.yaml` for ALL phase config including artifacts
- Update ISS-012's approach to align with this story

### Library & Framework Requirements

<!-- TEMPLATE SECTION: library_framework_requirements -->
| Library | Version | Usage |
|---------|---------|-------|
| Pydantic | 2.12+ | `CommandConfig` model with nested `LLMConfig`, `ArtifactConfig` |
| PyYAML | 6.0+ | Parse `config.yaml` files (already used for `adw.yaml`) |

**No new dependencies required.**

**Pydantic Patterns to Use:**
```python
class CommandConfig(BaseModel):
    """Phase command configuration from config.yaml."""

    model_config = ConfigDict(extra="forbid")  # Strict validation

    timeout_seconds: int | None = None
    input_files: dict[str, str] | None = None
    llm: LLMConfig | None = None
    artifacts: list[ArtifactConfig] | None = None
    pre_hook: str | None = None
    post_hook: str | None = None
```

### File Structure Requirements

<!-- TEMPLATE SECTION: file_structure_requirements -->
**Files to Modify:**

| File | Changes |
|------|---------|
| `src/adw/models/command.py` | Add `CommandConfig`, `LLMConfig`, `ArtifactConfig` models |
| `src/adw/commands/resolver.py` | Add `has_config` detection |
| `src/adw/commands/loader.py` | Add `_load_config()` method, update `LoadedCommand` |
| `src/adw/core/phase_runner.py` | Add `_merge_configs()`, integrate with `_load_input_files()` |

**Files to Create:**

| File | Content |
|------|---------|
| `src/adw/defaults/commands/plan/config.yaml` | Default plan phase config |
| `src/adw/defaults/commands/build/config.yaml` | Default build phase config |
| `src/adw/defaults/commands/verify/config.yaml` | Default verify phase config |
| `src/adw/defaults/commands/validate/config.yaml` | Default validate phase config |
| `src/adw/defaults/commands/document/config.yaml` | Default document phase config |

**Test Files:**

| File | Tests |
|------|-------|
| `tests/unit/models/test_command.py` | CommandConfig validation |
| `tests/unit/commands/test_loader.py` | Config loading |
| `tests/unit/core/test_phase_runner.py` | Config merging |

### Testing Requirements

<!-- TEMPLATE SECTION: testing_requirements -->
**Per ADR-001 Guidelines:**

**DO Write Tests For:**
- `CommandConfig` validation (required fields, type coercion)
- Config loading error handling (malformed YAML, missing files)
- Config merging logic (project overrides command defaults)
- Integration with `_load_input_files()` (ISS-015)

**DON'T Write Tests For:**
- Simple attribute existence on models
- Pydantic serialization (`model_dump()`)
- Default values (visible in model definition)

**Test Naming:**
```python
def test_command_config_validates_timeout_is_positive(): ...
def test_load_config_returns_none_when_missing(): ...
def test_merge_configs_project_overrides_command(): ...
def test_merge_configs_preserves_command_defaults_when_project_empty(): ...
```

---

## Previous Story Intelligence

<!-- TEMPLATE SECTION: previous_story_intelligence -->
**ISS-015 (just completed):** Phase-Specific Input Context Injection

Key learnings from ISS-015 implementation:
1. Added `input_files: dict[str, str] | None` to `PhaseConfig` model
2. Added `_load_input_files()` method to `PhaseRunner`
3. Integrated with `_load_and_render_prompt()` - inputs available as `{{ inputs.name }}`
4. Added `project_config` parameter to `PhaseRunner.__init__`

**How this story builds on ISS-015:**
- The `input_files` from `config.yaml` will be loaded via `_load_input_files()`
- Project `adw.yaml` input_files override command config.yaml defaults
- Merging logic: `merged_input_files = {**command_config.input_files, **phase_config.input_files}`

**ISS-012 (ready-for-dev):** Config-Driven Artifact Capture

ISS-012 plans to add artifact config to `command.yaml`. This story should:
- Use `config.yaml` (not `command.yaml`) as the unified config file
- Include `artifacts` field in `CommandConfig` model
- ISS-012 can then focus on the artifact capture _logic_ using this config

---

## Git Intelligence

<!-- TEMPLATE SECTION: git_intelligence_summary -->
**Recent Commits:**
```
996e193 feat(ISS-015): Phase-Specific Input Context Injection (#82)
83d43ff feat(story-11-7): Validation Report Generation (#81)
b7141c0 refactor(orchestrator): remove set_phase_runner in favor of constructor injection
```

**Patterns to Follow:**
1. **Commit message format:** `feat(ISS-016): <description>` for feature commits
2. **Constructor injection:** Pass dependencies via `__init__`, not setters (see b7141c0)
3. **PR format:** Include Summary, Changes table, Test plan with checkboxes

**Files Recently Modified (relevant):**
- `src/adw/models/config.py` - PhaseConfig with input_files (ISS-015)
- `src/adw/core/phase_runner.py` - _load_input_files, project_config param (ISS-015)

---

## Latest Technical Information

<!-- TEMPLATE SECTION: latest_tech_information -->
**Pydantic 2.12+ Features:**
- `model_config = ConfigDict(extra="forbid")` - reject unknown fields
- `field_validator` with `mode="before"` for preprocessing
- `model_validator` for cross-field validation

**YAML Loading Pattern (already used in codebase):**
```python
import yaml
from pathlib import Path

def _load_config(path: Path) -> CommandConfig | None:
    config_path = path / "config.yaml"
    if not config_path.exists():
        return None

    content = config_path.read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    return CommandConfig.model_validate(data)
```

---

## Project Context Reference

<!-- TEMPLATE SECTION: project_context_reference -->
See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- **All models in `src/adw/models/`** - CommandConfig goes in command.py
- **Full type annotations required** - Use `X | None` not `Optional[X]`
- **Exception hierarchy** - Use `ConfigError` for YAML parsing errors
- **Pydantic for structured data** - Never use plain dicts for config

---

## Dev Notes

- **Effort:** Medium (similar scope to ISS-015)
- **Risk:** Low - additive feature, backward compatible
- **Dependencies:** None (ISS-015 already merged)

### Project Structure Notes

- `CommandConfig` model goes in `src/adw/models/command.py` (alongside existing `ResolvedCommand`, `LoadedCommand`)
- Config loading belongs in `src/adw/commands/loader.py` (follows existing YAML loading pattern)
- Config merging belongs in `src/adw/core/phase_runner.py` (where PhaseConfig is already used)

### References

- [Source: _bmad-output/architecture.md lines 857-879] - Architecture spec for config.yaml
- [Source: _bmad-output/implementation-artifacts/issues/ISS-016-per-phase-config-yaml-not-implemented.md]
- [Source: _bmad-output/implementation-artifacts/refactor-ISS-012-config-driven-artifact-capture.md] - Related story
- [Source: _bmad-output/implementation-artifacts/ux-fix-ISS-015-phase-specific-input-context.md] - Foundation for input_files

---

## Dev Agent Record

<!-- TEMPLATE SECTION: story_completion_status -->

### Context Reference

Story created from ISS-016 tech debt issue documenting architecture gap.

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

N/A

### Completion Notes List

- Story created: 2026-01-06
- Ultimate context engine analysis completed - comprehensive developer guide created
- Unified approach with ISS-012 (artifact capture) documented

### File List

Files to touch:
- `src/adw/models/command.py` - Add CommandConfig, LLMConfig, ArtifactConfig models
- `src/adw/commands/resolver.py` - Add has_config detection
- `src/adw/commands/loader.py` - Add _load_config() method
- `src/adw/core/phase_runner.py` - Add _merge_configs() method
- `src/adw/defaults/commands/plan/config.yaml` - Create
- `src/adw/defaults/commands/build/config.yaml` - Create
- `src/adw/defaults/commands/verify/config.yaml` - Create
- `src/adw/defaults/commands/validate/config.yaml` - Create
- `src/adw/defaults/commands/document/config.yaml` - Create
- `tests/unit/models/test_command.py` - Add CommandConfig tests
- `tests/unit/commands/test_loader.py` - Add config loading tests
- `tests/unit/core/test_phase_runner.py` - Add config merging tests
