# Story 8.1: Detect Project Platform Type

Status: ready-for-dev
Linear Issue: not-configured
Epic: 8 - Evidence Gathering
Created: 2026-01-03

---

## Story

As a developer,
I want the system to detect the project platform type,
so that appropriate evidence gathering strategies are used.

## Acceptance Criteria

**Given** project config with `platform: cli`
**When** evidence gathering starts
**Then** CLI evidence strategy is used

**Given** project config with `platform: web`
**When** evidence gathering starts
**Then** web screenshot strategy is used

**Given** project config with `platform: backend`
**When** evidence gathering starts
**Then** API capture strategy is used

**Given** no platform specified
**When** detection is attempted
**Then** it's inferred from project markers (e.g., package.json with react → web)

**Given** platform cannot be determined
**When** Verify phase runs
**Then** default CLI strategy is used with warning

## Tasks / Subtasks

### Task 1: Create Platform Type Models (models/evidence.py)
- [ ] Create `PlatformType` enum (CLI, WEB, BACKEND, UNKNOWN)
- [ ] Create `PlatformDetectionResult` model with platform, confidence, markers
- [ ] Create `EvidenceStrategy` enum or Protocol for strategy selection
- [ ] Export from `models/__init__.py`

### Task 2: Implement Configuration-Based Detection
- [ ] Read `platform` key from `.adw/project.yaml`
- [ ] Parse and validate platform value against PlatformType enum
- [ ] Return immediately if explicit platform is configured
- [ ] Log platform source as "config" for traceability

### Task 3: Implement Project Marker Detection (evidence/detector.py)
- [ ] Create `PlatformDetector` class in `src/adw/evidence/`
- [ ] Implement marker detection for web projects:
  - `package.json` with react/vue/angular/svelte → WEB
  - `next.config.js`, `nuxt.config.ts` → WEB
  - `index.html` at root → WEB
- [ ] Implement marker detection for backend projects:
  - `main.py` with fastapi/flask/django → BACKEND
  - `app.py` with API patterns → BACKEND
  - `requirements.txt` with web frameworks → BACKEND
  - `Dockerfile` with EXPOSE → BACKEND
- [ ] Implement marker detection for CLI projects:
  - `pyproject.toml` with `[project.scripts]` → CLI
  - `setup.py` with `entry_points` → CLI
  - No web/backend markers → default CLI

### Task 4: Implement Confidence Scoring
- [ ] Assign confidence levels (HIGH, MEDIUM, LOW) based on marker strength
- [ ] Multiple corroborating markers increase confidence
- [ ] Log all detected markers for debugging
- [ ] Include confidence in detection result

### Task 5: Integrate with Evidence System
- [ ] Create factory function `get_evidence_strategy(platform: PlatformType)`
- [ ] Wire detection into Verify phase startup
- [ ] Emit appropriate warning for UNKNOWN platform
- [ ] Store detected platform in RunContext for downstream use

### Task 6: Write Unit Tests
- [ ] Test explicit config detection
- [ ] Test web marker detection (React, Vue, Next.js, etc.)
- [ ] Test backend marker detection (FastAPI, Django, etc.)
- [ ] Test CLI marker detection (pyproject.toml scripts)
- [ ] Test fallback to CLI with warning when unknown
- [ ] Test confidence scoring logic

---

## Relevant Feature Documentation

<!-- From PRD FR13-FR18 (Verify Phase) and Architecture -->

**From Architecture (Evidence Gathering MVP):**
- MVP Scope: API evidence, terminal output capture, JSON storage
- Platform detection informs which evidence strategy to use
- Default to CLI strategy when platform unknown

---

## Developer Context

### Technical Requirements

**From PRD FR13-FR18 (Verify Phase):**
- FR13: Verify phase gathers evidence based on project type
- FR14: Platform detection determines evidence strategy
- FR15: CLI projects capture terminal output
- FR16: Web projects capture screenshots (future enhancement)
- FR17: Backend projects capture API responses

**From Architecture (Evidence Gathering MVP):**
> MVP Scope:
> - API responses via subprocess calls to `curl`
> - Terminal output capture for CLI commands
> - JSON response storage in `artifacts/verify/api/`
>
> Deferred: Web screenshots (Playwright), mobile screenshots, video recording.

### Architecture Compliance

**Module Location:** `src/adw/evidence/`

**Files to Create:**
```
src/adw/evidence/
├── __init__.py         # Package exports
├── detector.py         # PlatformDetector class
└── strategies/         # Strategy implementations (future)
    └── __init__.py

src/adw/models/
└── evidence.py         # PlatformType, DetectionResult models
```

**Dependencies:**
- Pydantic for models (already installed)
- PyYAML for config parsing (already installed)
- pathlib for file detection (stdlib)

**Integration Points:**
- PhaseRunner calls detector at Verify phase start
- RunContext stores detected platform
- Evidence strategies use platform to determine behavior

### Library & Framework Requirements

**Pydantic Models:**
```python
from pydantic import BaseModel, Field
from enum import Enum

class PlatformType(str, Enum):
    CLI = "cli"
    WEB = "web"
    BACKEND = "backend"
    UNKNOWN = "unknown"

class Confidence(str, Enum):
    HIGH = "high"      # Explicit config or strong markers
    MEDIUM = "medium"  # Multiple weak markers
    LOW = "low"        # Single weak marker or inference

class PlatformDetectionResult(BaseModel):
    platform: PlatformType
    confidence: Confidence
    source: str  # "config", "markers", "default"
    markers: list[str] = Field(default_factory=list)
```

**File Detection Patterns:**
```python
from pathlib import Path

def detect_web_markers(project_root: Path) -> list[str]:
    markers = []
    package_json = project_root / "package.json"
    if package_json.exists():
        content = package_json.read_text()
        if any(fw in content for fw in ["react", "vue", "angular", "svelte"]):
            markers.append("package.json:frontend-framework")
    return markers
```

### File Structure Requirements

**Naming Conventions:**
- Files: snake_case (e.g., `detector.py`)
- Classes: PascalCase (e.g., `PlatformDetector`)
- Enums: PascalCase (e.g., `PlatformType`)
- Constants: SCREAMING_SNAKE_CASE (e.g., `WEB_MARKERS`)

**Location Rules:**
- All models in `src/adw/models/evidence.py`
- Detection logic in `src/adw/evidence/detector.py`
- Tests in `tests/unit/evidence/`

### Testing Requirements

**Test File Structure:**
```
tests/unit/
├── evidence/
│   ├── __init__.py
│   └── test_detector.py
└── models/
    └── test_evidence.py
```

**Testing Patterns:**
- Use `tmp_path` fixture to create test project structures
- Create minimal marker files (package.json, pyproject.toml)
- Test each platform type detection separately
- Test confidence scoring with various marker combinations

**Coverage Target:** >80%

---

## Previous Story Intelligence

This is the first story in Epic 8. Relevant patterns from previous epics:

**From Epic 7 (Observability & Logging):**
- Use LogManager for detection logging
- Structured log events with context
- Reference: `src/adw/logging/manager.py`

**From Epic 6 (Run Management):**
- RunContext model holds run state
- Context can be extended with new fields
- Reference: `src/adw/models/context.py`

**From Epic 4 (State Persistence):**
- State stored in `.adw/runs/<run_id>/`
- Platform detection result should be persisted
- Reference: `src/adw/core/context_manager.py`

---

## Git Intelligence

Recent commits show patterns for:
- Pydantic model creation in `models/`
- Protocol-based abstractions for strategies
- Use of LogManager for structured logging

---

## Latest Technical Information

**Pydantic v2 (2.12+):**
- Use `model_dump()` for dictionary conversion
- Use `Field(default_factory=list)` for mutable defaults
- Enum values should inherit from `str` for JSON serialization

**Python 3.13+ File Operations:**
```python
from pathlib import Path

# Modern pathlib patterns
project_root = Path.cwd()
if (project_root / "package.json").exists():
    content = (project_root / "package.json").read_text()
```

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- All models in `src/adw/models/` - NO exceptions
- Use structured logging with context fields
- Full type annotations required
- Custom exception hierarchy for errors
- PEP 8 naming: snake_case functions, PascalCase classes

---

## Dev Notes

- Platform detection is a foundation for all evidence gathering
- Start simple: explicit config takes precedence
- Marker detection should be extensible for future platforms
- Log all detection decisions for debugging
- Consider caching detection result in RunContext

### Project Structure Notes

- Create new `evidence/` package in `src/adw/`
- Add `evidence.py` to models directory
- Evidence strategies will be added in subsequent stories

### References

- [Source: _bmad-output/architecture.md#Evidence-Gathering-MVP] - MVP scope definition
- [Source: _bmad-output/epics/epic-8-evidence-gathering.md] - Epic requirements
- [Source: _bmad-output/project-context.md] - Implementation rules

---

## Dependencies

- **Depends On:** None (foundation story for Epic 8)
- **Blocks:** Story 8.2, Story 8.3, Story 8.4, Story 8.5
- **Can Parallel With:** None

### Dependency Rationale
- All evidence capture stories (8.2, 8.3, 8.4) depend on platform detection to determine which strategy to use
- Story 8.5 (manifest) needs platform type metadata
- This is the foundation story that must be completed first

---

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

