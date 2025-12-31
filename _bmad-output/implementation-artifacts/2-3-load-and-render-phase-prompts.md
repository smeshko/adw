# Story 2.3: Load and Render Phase Prompts

Status: ready-for-dev
Linear Issue: not-configured
Epic: 2 - Command Resolution & Templates
Created: 2025-12-31

---

## Story

As a developer,
I want to load a phase prompt from the resolved command directory and render it,
so that each phase has its complete, rendered prompt ready for LLM execution.

## Acceptance Criteria

**Given** a phase "plan" with resolved command directory
**When** I call `load_prompt("plan", context)`
**Then** it reads `prompt.md` from the command directory
**And** renders all template variables using the context

**Given** a prompt that references artifacts from previous phases
**When** the template contains `{{artifacts.build.diff}}`
**Then** the artifact content is included in the rendered prompt

**Given** a command directory with pre-hook output
**When** pre-hook stdout is available as `{{pre_hook_output}}`
**Then** it's included in the template context for rendering

**Given** the rendered prompt
**When** I inspect it
**Then** no unresolved `{{...}}` patterns remain (in strict mode)

## Tasks / Subtasks

### Task 1: Create Command Loader Module
- [x] Create `src/adw/commands/loader.py` with `CommandLoader` class
- [x] Export `CommandLoader` from `src/adw/commands/__init__.py`
- [x] Integrate with `CommandResolver` from Story 2.1

### Task 2: Implement Prompt Loading
- [x] Implement `load_prompt(phase: str, context: RunContext) -> str`
- [x] Resolve command using `CommandResolver`
- [x] Read `prompt.md` from resolved directory
- [x] Handle file encoding (UTF-8)

### Task 3: Implement Context Building
- [x] Build template context dict from `RunContext`
- [x] Include `run_id`, `feature_request`, `current_phase`
- [x] Include previous phase artifacts via `artifacts.{phase}.{name}` namespace
- [x] Include `pre_hook_output` if available

### Task 4: Implement Prompt Rendering
- [x] Use `TemplateEngine` from Story 2.2 to render prompt
- [x] Pass built context to template engine
- [x] Use strict mode by default (error on unknown variables)
- [x] Return fully rendered prompt string

### Task 5: Implement LoadedCommand Model
- [x] Add `LoadedCommand` model to `src/adw/models/command.py`
- [x] Fields: `name`, `resolved`, `prompt_content`, `output_schema`, `has_pre_hook`, `has_post_hook`
- [x] Include rendered prompt content

### Task 6: Implement Optional Schema Loading
- [ ] Load `schema.json` if present in command directory
- [ ] Parse and validate as valid JSON Schema
- [ ] Store in `LoadedCommand.schema` field
- [ ] Return `None` if no schema file

### Task 7: Write Unit Tests
- [ ] Test basic prompt loading from resolved directory
- [ ] Test template variable substitution in prompt
- [ ] Test artifact inclusion via context
- [ ] Test pre-hook output inclusion
- [ ] Test strict mode error for unknown variables
- [ ] Test schema loading (present and absent)

---

## Relevant Feature Documentation

_No conditional docs matched for this story context._

---

## Developer Context

### Technical Requirements

- **FR22:** System renders prompt templates with variable substitution
- **FR24:** System executes pre-hooks and captures stdout for prompt context
- This story bridges command resolution (2.1) and template rendering (2.2)
- Output is a fully rendered prompt string ready for LLM execution

### Architecture Compliance

**From architecture.md - Command Loading:**

The command loader combines resolution and rendering:

1. **Resolution:** Use `CommandResolver` to find command directory
2. **Loading:** Read prompt.md and optional schema.json
3. **Context Building:** Construct template context from run state
4. **Rendering:** Apply template substitution

**Context Namespace Structure:**
```python
context = {
    "run_id": "01HQ...",
    "feature_request": "Add user auth",
    "current_phase": "plan",
    "project_name": "my-app",
    "artifacts": {
        "plan": {
            "plan": "... plan content ...",
        },
        "build": {
            "diff": "... git diff ...",
        }
    },
    "pre_hook_output": "... hook stdout ...",
}
```

**Module Location:**
- `src/adw/commands/loader.py` - CommandLoader class
- Depends on: `resolver.py` (2.1), `template.py` (2.2)

### Library & Framework Requirements

| Library | Version | Usage |
|---------|---------|-------|
| Pydantic | 2.12+ | LoadedCommand model, RunContext access |
| pathlib | stdlib | File path handling |
| json | stdlib | Schema parsing |

**Pattern for Optional Schema Loading:**
```python
def load_schema(command_path: Path) -> dict | None:
    schema_path = command_path / "schema.json"
    if not schema_path.exists():
        return None
    return json.loads(schema_path.read_text())
```

### File Structure Requirements

**Files to Create:**
```
src/adw/
└── commands/
    └── loader.py    # CommandLoader class

tests/
└── unit/
    └── commands/
        └── test_loader.py
```

**Files to Modify:**
- `src/adw/models/command.py` - Add LoadedCommand model
- `src/adw/commands/__init__.py` - Export CommandLoader

### Testing Requirements

**Test File:** `tests/unit/commands/test_loader.py`

**Test Cases (>80% coverage):**

1. **Basic Loading:**
   ```python
   def test_load_prompt_from_resolved_directory(tmp_path):
       # Create command directory with prompt.md
       # Assert prompt content loaded correctly

   def test_load_prompt_applies_template_substitution(tmp_path):
       # Prompt with {{feature_request}}
       # Assert substituted in output
   ```

2. **Context Building:**
   ```python
   def test_artifact_inclusion_in_context():
       # Context with artifacts.build.diff
       # Assert artifact content accessible in template

   def test_pre_hook_output_in_context():
       # Context with pre_hook_output
       # Assert accessible as {{pre_hook_output}}
   ```

3. **Schema Loading:**
   ```python
   def test_schema_loaded_when_present(tmp_path):
       # Command with schema.json
       # Assert loaded_command.schema is not None

   def test_schema_none_when_absent(tmp_path):
       # Command without schema.json
       # Assert loaded_command.schema is None
   ```

4. **Error Handling:**
   ```python
   def test_unknown_variable_raises_in_strict_mode():
       # Prompt with {{unknown}}
       # Assert ConfigError raised
   ```

**Fixtures Needed:**
- Mock command directories with prompt.md and optional schema.json
- Mock RunContext with artifacts
- Temporary directories for test isolation

---

## Previous Story Intelligence

**From Story 2.1 (Command Resolution):**
- `CommandResolver.resolve(name)` returns `ResolvedCommand` with `path`
- Use `resolved.path` to locate prompt.md

**From Story 2.2 (Template Engine):**
- `TemplateEngine.render(template, context, strict=True)` returns rendered string
- Supports `{{variable}}` and `{{file:path}}` patterns

---

## Git Intelligence

**Recent Commits (Epic 1):**
- Pydantic models pattern with `model_dump()` for dict conversion
- Exception handling with ConfigError

**Expected Files from Epic 2:**
- `src/adw/commands/resolver.py` (from 2.1)
- `src/adw/commands/template.py` (from 2.2)

---

## Latest Technical Information

**Pydantic Model Integration:**
```python
from adw.models import RunContext, LoadedCommand

def load_prompt(self, phase: str, context: RunContext) -> LoadedCommand:
    # Convert RunContext to dict for template context
    template_context = context.model_dump()

    # Add artifacts namespace
    template_context["artifacts"] = self._build_artifacts_context(context)

    # Render prompt
    rendered = self.template_engine.render(prompt_content, template_context)

    return LoadedCommand(
        name=phase,
        resolved=resolved_command,
        prompt_content=rendered,
        schema=self._load_schema(resolved_command.path),
    )
```

**Artifact Namespace Access:**
```python
def _build_artifacts_context(self, context: RunContext) -> dict:
    """Build artifacts namespace for template access."""
    artifacts = {}
    for phase_name, phase_artifacts in context.artifacts.items():
        artifacts[phase_name] = {}
        for artifact_name, artifact in phase_artifacts.items():
            artifacts[phase_name][artifact_name] = artifact.content
    return artifacts
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- All Pydantic models in `src/adw/models/`
- Use exception hierarchy, never bare Exception
- Full type annotations required
- Context managers for file operations

---

## Dev Notes

### Key Implementation Decisions:

1. **Strict Mode Default:** Always use strict mode for production prompts. Unknown variables indicate a bug.

2. **Artifact Access:** Use dot notation `artifacts.phase.name` for clean template access.

3. **Pre-Hook Integration:** Pre-hook output is injected as `pre_hook_output` in context. Story 3.1 will capture this.

4. **Schema Validation Deferred:** Schema is loaded but validation happens in Story 2.4.

5. **UTF-8 Encoding:** All file reads use UTF-8 encoding explicitly.

### Project Structure Notes

- `src/adw/commands/loader.py` - Integrates resolver + template
- `src/adw/models/command.py` - ResolvedCommand + LoadedCommand

### References

- [Source: _bmad-output/architecture.md#Command Boundary]
- [Source: _bmad-output/architecture.md#Hook Execution Environment]
- [Source: _bmad-output/prd.md#FR22-FR24 (Template Rendering)]
- [Source: _bmad-output/epics/epic-2-command-resolution-templates.md#Story 2.3]

---

## Dependencies

**Depends On:**
- Story 2.1: Implement Three-Tier Command Resolution (provides `CommandResolver`)
- Story 2.2: Create Template Engine with Variable Substitution (provides `TemplateEngine`)

**Blocks:** None within Epic 2

**Note:** This story is in Wave 2 - cannot start until Stories 2.1 AND 2.2 are complete.

---

## Dev Agent Record

### Context Reference

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

