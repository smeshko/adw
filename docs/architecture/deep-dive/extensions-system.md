# Extensions System Deep Dive

This document explains the extensions architecture in ADW.

## Overview

Extensions provide **phase-specific hooks** that run at defined points in the phase lifecycle. They use Python's Protocol pattern for structural typing (duck typing), allowing any class with the right methods to be an extension.

**Design Principles:**
- Non-blocking: Extension failures don't fail the phase
- Stateless: No instance state beyond configuration
- Chainable: `on_complete` hooks chain context through extensions
- Decoupled: Extensions don't modify core orchestration code

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      ExtensionRegistry                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  extensions: dict[str, list[PhaseExtension]]            │   │
│  │                                                         │   │
│  │    "build"    → [BuildExtension]                        │   │
│  │    "document" → [DocumentExtension]                     │   │
│  │    "ship"     → [ShipExtension]                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Methods:                                                       │
│    register(extension)                                          │
│    get_extensions(phase) → list[PhaseExtension]                 │
│    should_skip_phase(phase, context) → (bool, str|None)         │
│    call_on_complete(phase, context, result) → RunContext        │
│    call_extra_artifacts(phase, context, llm_result) → list      │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    Orchestrator         PhaseRunner         Orchestrator
   (should_skip)     (extra_artifacts)      (on_complete)
```

## Extension Protocol

Defined in `src/adw/core/extensions/base.py`:

```python
@runtime_checkable
class PhaseExtension(Protocol):
    """Protocol for phase extensions."""

    phase: ClassVar[str]  # Phase this extension applies to

    def should_skip(
        self, context: "RunContext"
    ) -> tuple[bool, str | None]:
        """Return (True, reason) to skip phase, (False, None) to proceed."""
        ...

    def on_complete(
        self, context: "RunContext", result: "PhaseResult"
    ) -> "RunContext":
        """Post-processing after phase completes. Return updated context."""
        ...

    def extra_artifacts(
        self, context: "RunContext", llm_result: "LLMResult"
    ) -> list[tuple[str, str]]:
        """Return additional artifacts as (name, content) tuples."""
        ...
```

## Lifecycle Hooks

| Hook | Called By | When | Purpose | Returns |
|------|-----------|------|---------|---------|
| `should_skip()` | Orchestrator | Before phase execution | Conditionally skip phase | `(bool, reason)` |
| `extra_artifacts()` | PhaseRunner | During artifact capture | Generate additional artifacts | `list[(name, content)]` |
| `on_complete()` | Orchestrator | After phase success | Post-processing, side effects | `RunContext` |

## Execution Flow

```
┌─ Orchestrator ─────────────────────────────────────────────────┐
│  1. registry.should_skip_phase(phase, context)                 │
│     ├─ Calls extension.should_skip() for each extension        │
│     └─ Returns (True, reason) if ANY extension wants to skip   │
│                                                                 │
│  If skip: Log reason, continue to next phase                   │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌─ PhaseRunner ──────────────────────────────────────────────────┐
│  2. Pre-hook execution                                         │
│  3. Prompt loading & template rendering                        │
│  4. LLM execution                                              │
│  5. Artifact capture:                                          │
│     ├─ Store {phase}_output.md (LLM response)                  │
│     ├─ Store {phase}_tool_calls.json (if any)                  │
│     └─ registry.call_extra_artifacts(phase, context, llm)      │
│        ├─ Calls extension.extra_artifacts() for each extension │
│        └─ Stores all returned artifacts                        │
│  6. Post-hook execution                                        │
│  7. Auto-commit changes                                        │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌─ Orchestrator ─────────────────────────────────────────────────┐
│  8. registry.call_on_complete(phase, context, result)          │
│     ├─ Chains context through each extension's on_complete()   │
│     └─ Each extension receives context from previous extension │
│  9. Save updated context to disk                               │
└────────────────────────────────────────────────────────────────┘
```

## Built-in Extensions

### BuildExtension

**File:** `src/adw/core/extensions/build.py`
**Phase:** `build`

| Hook | Implementation |
|------|----------------|
| `should_skip()` | Always returns `(False, None)` |
| `on_complete()` | No-op, returns context unchanged |
| `extra_artifacts()` | Captures git diff artifacts |

**Artifacts produced:**
```
diff.txt        # Git diff since last commit (truncated if >100KB)
diff_stats.json # {"files_changed": 5, "insertions": 120, "deletions": 30,
                #  "files": [...], "binary_files": [...]}
```

**Implementation:**
```python
def extra_artifacts(self, context, llm_result):
    diff_content = capture_diff(since="HEAD~1", working_dir=context.worktree_path)
    stats = get_diff_stats(stat_output, diff_content)
    return [
        ("diff.txt", diff_content),
        ("diff_stats.json", json.dumps(stats)),
    ]
```

---

### DocumentExtension

**File:** `src/adw/core/extensions/document.py`
**Phase:** `document`
**Dependencies:** `git_config`, `runs_dir`

| Hook | Implementation |
|------|----------------|
| `should_skip()` | Always returns `(False, None)` |
| `on_complete()` | Creates PR if `auto_create_pr` enabled |
| `extra_artifacts()` | Returns `pr_description.md` |

**Context updates on PR creation:**
```python
context.model_copy(update={
    "pr_creation_attempted": True,
    "pr_url": "https://github.com/org/repo/pull/123",  # or None
    "pr_creation_failed": False,                        # or True
    "pr_failure_reason": None,                          # or error message
})
```

---

### ShipExtension

**File:** `src/adw/core/extensions/ship.py`
**Phase:** `ship`

| Hook | Implementation |
|------|----------------|
| `should_skip()` | Skips if PR creation failed |
| `on_complete()` | No-op, returns context unchanged |
| `extra_artifacts()` | Returns empty list |

**Skip logic:**
```python
def should_skip(self, context):
    if context.pr_creation_attempted and context.pr_creation_failed:
        return True, f"PR creation failed: {context.pr_failure_reason}"
    return False, None
```

## Registry & Registration

**Factory function** in `src/adw/core/extensions/__init__.py`:

```python
def create_default_registry(git_config, runs_dir) -> ExtensionRegistry:
    """Create registry with built-in extensions."""
    registry = ExtensionRegistry()
    registry.register(BuildExtension())
    registry.register(DocumentExtension(git_config, runs_dir))
    registry.register(ShipExtension())
    return registry
```

**Registration in bootstrap** (`src/adw/cli/bootstrap.py`):
```python
extension_registry = create_default_registry(config.git, runs_dir)
orchestrator = Orchestrator(..., extension_registry=extension_registry)
phase_runner = PhaseRunner(..., extension_registry=extension_registry)
```

## Error Handling

Extensions are **non-blocking**. All failures are caught and logged as warnings:

```python
# In ExtensionRegistry
def should_skip_phase(self, phase, context):
    for ext in self.get_extensions(phase):
        try:
            should_skip, reason = ext.should_skip(context)
            if should_skip:
                return True, reason
        except Exception as e:
            logger.warning(
                "Extension should_skip failed (non-blocking)",
                extra={"phase": phase, "extension": type(ext).__name__, "error": str(e)}
            )
    return False, None
```

## Context Chaining

The `on_complete` hook chains context through all extensions for a phase:

```python
def call_on_complete(self, phase, context, result):
    for ext in self.get_extensions(phase):
        try:
            context = ext.on_complete(context, result)
        except Exception as e:
            logger.warning("Extension on_complete failed (non-blocking)", ...)
    return context
```

Each extension receives the context returned by the previous extension, allowing sequential modifications.

## Creating a New Extension

```python
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from adw.models import LLMResult, PhaseResult, RunContext


class ValidateExtension:
    """Extension for validate phase."""

    phase: ClassVar[str] = "validate"

    def __init__(self, some_config: SomeConfig | None = None):
        self._config = some_config

    def should_skip(self, context: "RunContext") -> tuple[bool, str | None]:
        # Skip if tests already passed in a previous run
        if context.tests_passed:
            return True, "Tests already passed"
        return False, None

    def on_complete(
        self, context: "RunContext", result: "PhaseResult"
    ) -> "RunContext":
        # Parse validation result and update context
        validation_passed = self._parse_result(result)
        return context.model_copy(update={
            "validation_passed": validation_passed,
        })

    def extra_artifacts(
        self, context: "RunContext", llm_result: "LLMResult"
    ) -> list[tuple[str, str]]:
        # Generate a validation summary artifact
        summary = self._generate_summary(llm_result)
        return [("validation_summary.json", summary)]
```

**Register the extension:**
```python
# In create_default_registry() or custom setup
registry.register(ValidateExtension(config))
```

## Data Available to Extensions

### RunContext Fields

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | str | ULID identifier |
| `feature_description` | str | What's being developed |
| `current_phase` | str | Active phase |
| `phase_history` | list[str] | Completed phases |
| `worktree_path` | str \| None | Git worktree path |
| `branch_name` | str | Git branch |
| `pr_url` | str \| None | Created PR URL |
| `pr_creation_attempted` | bool | PR creation attempted |
| `pr_creation_failed` | bool | PR creation failed |
| `pr_failure_reason` | str \| None | Failure details |
| `status` | RunStatus | Current run status |

### LLMResult Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | bool | Execution completed |
| `content` | str | Full conversation text |
| `final_output` | str | Last assistant message |
| `tool_calls` | list | Tool calls made |
| `tokens_used` | int | Token count |
| `duration_ms` | int | Execution time |
| `error` | str \| None | Error if failed |

### PhaseResult Fields

| Field | Type | Description |
|-------|------|-------------|
| `phase` | str | Phase name |
| `status` | PhaseStatus | COMPLETED, FAILED, etc. |
| `artifacts` | list[str] | Artifact filenames |
| `tokens_used` | int | Token count |
| `error` | str \| None | Error if failed |

## Key Source Files

| File | Role |
|------|------|
| `src/adw/core/extensions/base.py` | `PhaseExtension` Protocol definition |
| `src/adw/core/extensions/registry.py` | `ExtensionRegistry` class |
| `src/adw/core/extensions/__init__.py` | `create_default_registry()` factory |
| `src/adw/core/extensions/build.py` | BuildExtension (diff capture) |
| `src/adw/core/extensions/document.py` | DocumentExtension (PR creation) |
| `src/adw/core/extensions/ship.py` | ShipExtension (skip logic) |
| `src/adw/core/orchestrator.py` | Calls `should_skip`, `on_complete` |
| `src/adw/core/phase_runner.py` | Calls `extra_artifacts` |
| `src/adw/cli/bootstrap.py` | Registry creation and wiring |
