# Story 14.2: Basics Configuration Step

Status: ready-for-dev
Linear Issue: pending
Epic: 14 - Interactive Init Wizard
Created: 2026-01-18

---

## Story

As a user in the wizard,
I want to configure basic project settings,
so that ADW knows what kind of project I'm working on.

## Acceptance Criteria

- [ ] Auto-detects language from project markers (pyproject.toml, package.json, go.mod, etc.)
- [ ] Shows "Language detected: {lang}. Correct? [Y/n]"
- [ ] If No, shows selection: python / javascript / go / rust / java / ruby / php / **other**
- [ ] If "other" selected, prompts for manual language entry
- [ ] Prompts for platform: "Platform type? [cli] / web / api / **other**"
- [ ] If "other" selected for platform, prompts for manual platform entry
- [ ] Auto-detects test command based on language (pytest, npm test, go test, etc.)
- [ ] Shows "Test command: {cmd} [Enter to accept or type custom command]"
- [ ] User can type any custom test command (not limited to predefined list)
- [ ] Prompts "Build command: [none] (Enter to skip or type custom command)"
- [ ] User can type any custom build command
- [ ] All values stored in wizard state for final generation

## Tasks / Subtasks

### Task 1: Create Basics Step Module
- [x] Create `src/adw/cli/wizard/basics.py`
- [x] Define `run_basics_step(state: WizardState) -> WizardState`
- [x] Import and register in flow controller

### Task 2: Implement Language Detection
- [x] Create language detection function
- [x] Check for project markers:
  - `pyproject.toml`, `setup.py` → Python
  - `package.json` → JavaScript/TypeScript
  - `go.mod` → Go
  - `Cargo.toml` → Rust
  - `pom.xml`, `build.gradle` → Java
  - `Gemfile` → Ruby
  - `composer.json` → PHP
- [x] Return detected language or "unknown"

### Task 3: Implement Test Command Detection
- [ ] Create test command detection function
- [ ] Map language to default test commands:
  - Python: `pytest`
  - JavaScript: `npm test`
  - Go: `go test ./...`
  - Rust: `cargo test`
  - Java: `./gradlew test` or `mvn test`
  - Ruby: `bundle exec rspec`
  - PHP: `./vendor/bin/phpunit`
- [ ] Check if test runner actually exists (optional enhancement)

### Task 4: Implement Interactive Prompts
- [ ] Show language detection result with Rich
- [ ] Prompt for language confirmation
- [ ] Show language selection if not confirmed (include "other" option)
- [ ] If "other" selected, prompt for manual language entry (free text)
- [ ] Prompt for platform type (cli/web/api/other)
- [ ] If "other" selected for platform, prompt for manual platform entry (free text)
- [ ] Show test command with override option (user can type any command)
- [ ] Prompt for optional build command (user can type any command)

### Task 5: Store Results in Wizard State
- [ ] Update WizardState with:
  - `language: str`
  - `platform: str` (cli/web/api)
  - `test_command: str | None`
  - `build_command: str | None`
- [ ] Mark basics step as completed

### Task 6: Write Unit Tests
- [ ] Test language detection for each marker file
- [ ] Test test command detection for each language
- [ ] Test prompt flow with mocked Rich prompts
- [ ] Test state update after step completion

---

## Dependencies

### Depends On
- 14.1 (Wizard Entry Point & Flow Control) - provides WizardState and flow controller

### Blocks
- 14.3 through 14.9 - need language/platform context
- 14.10 (Summary) - displays basics configuration

### Parallel With
- 14.1 (Wizard Entry Point & Flow Control) - can be developed in parallel if WizardState interface is agreed upon

---

## Developer Context

### Technical Requirements

**Language Detection Requirements:**
- Check project root for marker files
- Support multiple markers per language (e.g., pyproject.toml OR setup.py)
- Return lowercase language name
- Handle "unknown" case gracefully

**Platform Types:**
- `cli`: Command-line applications
- `web`: Web applications with frontend
- `api`: Backend API services
- `other`: Custom platform type (user enters manually)

**"Other" Option Handling:**
- When user selects "other" for language or platform, prompt for free-text entry
- Accept any non-empty string for custom values
- Custom languages won't have auto-detected test commands (user must enter manually)

**Test/Build Command Entry:**
- Test command prompt accepts any string (not restricted to choices)
- Build command prompt accepts any string (empty string = no build command)
- Users can override auto-detected commands with any custom command

**Test Command Detection:**
- Should be deterministic based on language
- For custom languages ("other"), default to empty and require user input
- Optional: verify command exists before suggesting

### Architecture Compliance

**Layer Boundaries:**
- Wizard step in `src/adw/cli/wizard/basics.py`
- No business logic in CLI layer (detection is simple enough)
- If detection becomes complex, move to `src/adw/core/detection/`

**Existing Patterns:**
- Similar detection logic may exist in codebase (search for it)
- Follow the same prompt patterns used elsewhere in CLI

### Library & Framework Requirements

| Library | Usage | Import Pattern |
|---------|-------|----------------|
| Rich | Interactive prompts | `from rich.prompt import Prompt, Confirm` |
| pathlib | File existence checks | `from pathlib import Path` |

**Rich Prompt Patterns:**
```python
from rich.prompt import Prompt, Confirm

# Confirmation with default
confirmed = Confirm.ask(
    f"Language detected: [cyan]{language}[/]. Correct?",
    default=True
)

# Selection prompt with "other" option
language = Prompt.ask(
    "Select language",
    choices=["python", "javascript", "go", "rust", "java", "ruby", "php", "other"]
)

# If "other" selected, prompt for custom entry
if language == "other":
    language = Prompt.ask("Enter language name")

# Platform with "other" option
platform = Prompt.ask(
    "Platform type",
    choices=["cli", "web", "api", "other"],
    default="cli"
)

if platform == "other":
    platform = Prompt.ask("Enter platform type")

# Text with default - accepts any input (no choices restriction)
test_cmd = Prompt.ask(
    "Test command",
    default="pytest"  # User can type anything, not restricted to choices
)

# Optional text (empty allowed) - accepts any input
build_cmd = Prompt.ask(
    "Build command (Enter to skip)",
    default=""
)
```

### File Structure Requirements

**New Files to Create:**
```
src/adw/cli/wizard/
└── basics.py             # Basics configuration step
```

**Files to Modify:**
```
src/adw/cli/wizard/flow.py    # Register basics step
src/adw/models/wizard.py      # Add basics fields to WizardState
```

### Testing Requirements

**Test Files:**
```
tests/unit/cli/wizard/
└── test_basics.py        # Basics step tests
```

**Test Cases:**
- Language detection with pyproject.toml present → "python"
- Language detection with package.json present → "javascript"
- Language detection with no markers → "unknown"
- Test command for each language
- Full step flow with mocked prompts
- State contains all expected fields after step
- "Other" language selection triggers free-text prompt
- "Other" platform selection triggers free-text prompt
- Custom test command entry (overriding auto-detected)
- Custom build command entry

**Mock Requirements:**
- Mock `Path.exists()` for marker file detection
- Mock Rich prompts for automated testing

---

## Previous Story Intelligence

**From Story 14.1 (if implemented):**
- WizardState model structure
- Flow controller integration pattern
- Step registration mechanism

**Expected Interface:**
```python
# Expected function signature
def run_basics_step(state: WizardState) -> WizardState:
    """Execute the basics configuration step."""
    ...
```

---

## Git Intelligence

**Related Patterns:**
- Check for existing language/test detection in codebase
- `src/adw/core/config/` may have similar detection logic

**Search Commands:**
```bash
grep -r "pyproject.toml" src/
grep -r "detect" src/
```

---

## Latest Technical Information

**Rich Prompt Features:**
- `choices` parameter for selection prompts
- `default` parameter for pre-filled values
- Color markup in prompt text
- Validation via `show_choices=True`

**Python Pathlib:**
```python
from pathlib import Path

def detect_language(project_root: Path) -> str:
    markers = {
        "python": ["pyproject.toml", "setup.py", "setup.cfg"],
        "javascript": ["package.json"],
        "go": ["go.mod"],
        "rust": ["Cargo.toml"],
        "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
        "ruby": ["Gemfile"],
        "php": ["composer.json"],
    }

    for language, files in markers.items():
        if any((project_root / f).exists() for f in files):
            return language

    return "unknown"
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- All models in `src/adw/models/`
- Rich for all CLI output (no print())
- Full type annotations required
- snake_case for functions and variables

---

## Dev Notes

- Language detection should be fast (just file existence checks)
- Consider caching detection results in WizardState
- The platform type affects later steps (e.g., evidence gathering strategy)
- Test command detection is best-effort; users can always override

### Project Structure Notes

- basics.py follows the pattern of other wizard step modules
- Detection functions could be extracted to utilities if reused elsewhere

### References

- [Source: _bmad-output/epics/epic-14-interactive-init-wizard.md#Story-14.2]
- [Source: _bmad-output/project-context.md#CLI-Command-Patterns]
- [Source: _bmad-output/architecture-summary.md#Configuration-Driven]

---

## Dev Agent Record

### Context Reference

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

### File List

