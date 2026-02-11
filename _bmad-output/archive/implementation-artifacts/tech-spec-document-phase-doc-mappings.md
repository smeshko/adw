# Tech-Spec: Document Phase - Automatic Doc Mappings

**Created:** 2026-01-22
**Status:** Completed

## Overview

### Problem Statement

When the Document phase runs after code changes, it currently creates new feature docs and updates inline documentation, but it does not automatically update **existing project documentation** that describes the changed source files. For example, if `src/adw/core/orchestrator.py` is modified, the corresponding `docs/architecture/deep-dive/orchestrator.md` should be surgically updated to reflect the changes.

### Solution

Add a configurable `doc_mappings` field to the Document phase's `config.yaml` that maps source file patterns to documentation directories. During execution, the Document phase will:
1. Identify changed source files from build artifacts
2. Match them against configured `doc_mappings` patterns
3. Find corresponding documentation files (by matching filename)
4. Surgically update those docs based on the source changes

### Scope

**In Scope:**
- `DocumentCommandConfig` class extending `CommandConfig` with `doc_mappings` field
- Wizard integration for configuring doc mappings during `adw init`
- Instructions update to consume mappings and update existing docs
- Config.yaml schema update with doc_mappings example

**Out of Scope:**
- Auto-creating docs if no match exists (skip instead)
- Protected/frozen sections in docs
- Full doc regeneration (surgical updates only)
- Convention-based auto-discovery (explicit config only)

## Context for Development

### Codebase Patterns

**CommandConfig Subclass Pattern:**
```python
# In src/adw/models/command.py
class ValidateCommandConfig(CommandConfig):
    """Extends CommandConfig with phase-specific fields."""

    model_config = ConfigDict(extra="forbid")

    enable_tests: bool = Field(default=True, description="...")
    # ... additional fields
```

**Config Class Registration:**
```python
# In src/adw/commands/loader.py
PHASE_CONFIG_CLASSES: dict[str, type[CommandConfig]] = {
    "validate": ValidateCommandConfig,
    "ship": ShipCommandConfig,
    # Add: "document": DocumentCommandConfig,
}
```

**Wizard Phase Configuration:**
```python
# In src/adw/cli/wizard/phases.py
def _configure_phase(phase: str, console: Console) -> dict[str, Any]:
    # ... base config ...
    if phase == "validate":
        validate_config = _configure_validate_phase(console)
        config.update(validate_config)
    # Add: if phase == "document": ...
```

### Files to Reference

| File | Purpose |
|------|---------|
| `src/adw/models/command.py` | Add `DocumentCommandConfig` class |
| `src/adw/commands/loader.py` | Register in `PHASE_CONFIG_CLASSES` |
| `src/adw/models/__init__.py` | Export `DocumentCommandConfig` |
| `src/adw/cli/wizard/phases.py` | Add `_configure_document_phase()` |
| `src/adw/defaults/commands/document/config.yaml` | Add `doc_mappings` schema |
| `src/adw/defaults/commands/document/document-feature/instructions.xml` | Consume mappings |

### Technical Decisions

1. **Explicit config over convention**: User must explicitly configure mappings rather than auto-discovering via filename matching. This is more predictable and gives users control.

2. **Surgical updates**: The LLM will analyze what changed in the source file and make targeted updates to corresponding doc sections, rather than regenerating entire documents.

3. **Skip on no match**: If a source file matches a pattern but no corresponding doc exists, skip it silently (no auto-creation).

4. **Glob patterns**: Use standard glob patterns (e.g., `src/adw/core/**/*.py`) for flexible matching.

## Implementation Plan

### Tasks

- [x] Task 1: Create `DocMappingConfig` and `DocumentCommandConfig` models
  - Add to `src/adw/models/command.py`
  - `DocMappingConfig`: `source_pattern: str`, `docs_dir: str`
  - `DocumentCommandConfig(CommandConfig)`: `doc_mappings: list[DocMappingConfig] | None`

- [x] Task 2: Register `DocumentCommandConfig` in loader
  - Update `src/adw/commands/loader.py` `PHASE_CONFIG_CLASSES`
  - Add import for `DocumentCommandConfig`

- [x] Task 3: Export from models package
  - Update `src/adw/models/__init__.py` to export `DocumentCommandConfig` and `DocMappingConfig`

- [x] Task 4: Add wizard configuration for document phase
  - Add `_configure_document_phase()` function in `src/adw/cli/wizard/phases.py`
  - Prompt for doc mappings (source pattern + docs dir pairs)
  - Wire into `_configure_phase()` for `phase == "document"`

- [x] Task 5: Update default config.yaml
  - Add `doc_mappings` section to `src/adw/defaults/commands/document/config.yaml`
  - Include commented example mappings

- [x] Task 6: Update instructions.xml to consume doc_mappings
  - Add step in `document-feature/instructions.xml` to:
    1. Load `doc_mappings` from config
    2. For each changed file, match against patterns
    3. Find corresponding doc file in `docs_dir` (match by filename stem)
    4. If found, read doc and surgically update based on source changes
  - Insert this logic after Step 1 (change detection) and before Step 2 (analysis)

- [x] Task 7: Add unit tests
  - Test `DocumentCommandConfig` validation
  - Test config loading via `CommandLoader`
  - Test wizard `_configure_document_phase()`

- [x] Task 8: Add integration test
  - Test end-to-end doc mapping flow with mock files

### Acceptance Criteria

- [x] AC 1: Given a config.yaml with `doc_mappings: [{source_pattern: "src/core/**/*.py", docs_dir: "docs/architecture"}]`, when orchestrator.py is in changed files, then the document phase attempts to update docs/architecture/orchestrator.md

- [x] AC 2: Given a matching source pattern but no corresponding doc file exists, when the document phase runs, then it skips that file without error

- [x] AC 3: Given `adw init` wizard, when user selects document phase customization, then they can add source_pattern → docs_dir mappings

- [x] AC 4: Given an existing doc file that matches, when the source file has changes, then only relevant sections of the doc are updated (surgical, not full rewrite)

- [x] AC 5: Given multiple doc_mappings entries, when a file matches multiple patterns, then the first matching pattern wins

## Additional Context

### Dependencies

- Pydantic v2 for model validation
- Rich for wizard prompts
- Existing `CommandConfig` base class
- Existing wizard infrastructure in `src/adw/cli/wizard/`

### Testing Strategy

**Unit Tests:**
- `tests/unit/models/test_command.py` - Add tests for `DocumentCommandConfig` validation
- `tests/unit/commands/test_loader.py` - Test config class selection for document phase
- `tests/unit/cli/wizard/test_phases.py` - Test `_configure_document_phase()`

**Integration Tests:**
- `tests/integration/cli/test_document_phase.py` - Test full doc mapping flow

### Config YAML Schema

```yaml
# Document phase configuration
timeout_seconds: 600

# NEW: Map source files to documentation directories
# When files matching source_pattern change, look for corresponding
# docs in docs_dir (matched by filename stem: foo.py -> foo.md)
doc_mappings:
  - source_pattern: "src/adw/core/**/*.py"
    docs_dir: "docs/architecture/deep-dive"
  - source_pattern: "src/adw/cli/**/*.py"
    docs_dir: "docs/cli"
  - source_pattern: "src/adw/models/**/*.py"
    docs_dir: "docs/models"

artifacts:
  - name: document_output
    pattern: "document_output.md"
    required: true
```

### Notes

- The instructions.xml update is the most complex part - it needs to integrate with the existing change detection flow and add a new substep for doc mapping resolution
- Consider adding a `--dry-run` output that shows which docs would be updated without making changes
- Future enhancement: support `docs_file` for explicit single-file mapping (e.g., `orchestrator.py` → `ARCHITECTURE.md#orchestrator-section`)
