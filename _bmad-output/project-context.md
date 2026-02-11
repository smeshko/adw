---
project_name: 'adw-sdk'
user_name: 'Ivo'
date: '2025-12-31'
sections_completed: [technology_stack, critical_rules, patterns, testing, anti_patterns]
---

# Project Context for AI Agents

_Critical rules and patterns for implementing adw-sdk. Read this before writing any code._

---

## Technology Stack & Versions

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.13+ | Runtime (use modern syntax) |
| Typer | 0.21.0 | CLI framework |
| Rich | 14.1.0 | Terminal output, progress, logging |
| Pydantic | 2.12+ | Data validation, serialization |
| PyYAML | 6.0+ | Config parsing |
| filelock | latest | Concurrency control |
| python-ulid | latest | Run ID generation |
| FastAPI | latest | Server framework (webhook + dashboard) |
| Jinja2 | 3.1.6 | Template engine for dashboard |
| HTMX | 2.0.8 | Hypermedia interactions (vendored) |
| DaisyUI | 5 | Component library (CDN) |
| Tailwind CSS | v4 | Utility CSS (CDN) |
| pytest | latest | Testing |
| ruff | latest | Linting |
| mypy | latest | Type checking |

**Package Manager:** uv (NOT pip, NOT poetry)

---

## Critical Implementation Rules

### 1. Naming Conventions (PEP 8 Strict)

```python
# CORRECT
class PhaseRunner:           # Classes: PascalCase
def run_phase():             # Functions: snake_case
phase_result = ...           # Variables: snake_case
DEFAULT_TIMEOUT = 300        # Constants: SCREAMING_SNAKE_CASE
_internal_state = ...        # Private: _underscore prefix

# WRONG - will fail review
class phase_runner:          # NO
def RunPhase():              # NO
phaseResult = ...            # NO
```

### 2. All Models in models/

```python
# CORRECT - models live in src/adw/models/
from adw.models import RunContext, PhaseResult

# WRONG - never define models elsewhere
class RunContext(BaseModel):  # NO - not in models/
    ...
```

### 3. Exception Hierarchy - Never Bare Exception

```python
# CORRECT
from adw.exceptions import HookError

raise HookError(
    code="HOOK_FAILED",
    message="Pre-hook exited with code 1",
    suggestion="Check hook script for errors",
    recoverable=False,
    phase="build"
)

# WRONG
raise Exception("Hook failed")  # NO - use hierarchy
raise HookError("failed")       # NO - missing required fields
```

### 4. Type Annotations Required

```python
# CORRECT - full annotations, modern syntax
def run_phase(
    self,
    phase: str,
    context: RunContext,
    *,
    timeout: int | None = None,
) -> PhaseResult:
    ...

# WRONG
def run_phase(self, phase, context, timeout=None):  # NO
    ...
```

### 5. Rich for All CLI Output

```python
# CORRECT
from rich.console import Console
console = Console()
console.print("[bold green]✓[/] Phase completed")

# WRONG
print("Phase completed")  # NO - use Rich
```

### 6. Structured Logging

```python
# CORRECT
logger.info("Phase completed", phase="plan", duration_ms=1234)

# WRONG
logger.info(f"The plan phase completed in 1234ms")  # NO - unstructured
```

### 7. Immutable State Updates

```python
# CORRECT - Pydantic model_copy
new_context = context.model_copy(update={"current_phase": "build"})

# WRONG - direct mutation
context.current_phase = "build"  # NO - loses audit trail
```

### 8. Context Managers for Resources

```python
# CORRECT
with filelock.FileLock(lock_path):
    with open(path, "w") as f:
        f.write(data)

# WRONG
lock.acquire()  # NO - might not release on error
f = open(path)  # NO - use context manager
```

---

## Project Structure Rules

```
src/adw/
├── cli/           # Typer commands ONLY - no business logic
├── core/          # Orchestration logic + shared services
├── commands/      # Command resolution
├── executors/     # LLM abstraction (Protocol-based)
├── hooks/         # Shell script execution
├── logging/       # Multi-tier logging
├── models/        # ALL Pydantic models here
├── exceptions.py  # Exception hierarchy
├── utils/         # Shared utilities
├── server/        # Shared FastAPI infrastructure (factory, config, middleware)
├── dashboard/     # Web dashboard (routes, templates, static assets)
└── webhook/       # Webhook server (routes, providers)
```

**Boundary Rules:**
- CLI layer: Parse input, format output, delegate to core
- Core layer: All business logic, no CLI dependencies
- Executors: Protocol-based for testability
- Dashboard: NEVER imports from webhook — both use shared server/ and core/
- Server: Shared factory creates app with feature flags; no feature-specific logic

---

## Testing Requirements

```python
# Test files mirror source structure
tests/unit/core/test_phase_runner.py  # for src/adw/core/phase_runner.py

# Use MockExecutor for LLM tests
from adw.executors.mock import MockExecutor

# Fixtures in tests/fixtures/
# Coverage requirement: >80%
```

---

## CLI Command Patterns

```python
# Commands: kebab-case
# adw run, adw list-runs, adw logs show

# Options: double-dash + kebab-case
# --run-id, --from-phase, --verbose

# Short options: single letter
# -v, -q, -f
```

---

## Config & Serialization

```yaml
# Config keys: snake_case
llm:
  claude_code:
    path: /usr/bin/claude
    timeout_seconds: 300
```

```python
# JSON output: snake_case (Pydantic default)
context.model_dump_json()
# {"run_id": "01HQ...", "current_phase": "plan"}
```

---

## Web Dashboard Rules

_Architecture: `architecture-web-dashboard.md`. These rules apply to all code in `server/`, `dashboard/`, and related templates._

### Dual-Response Pattern (MANDATORY for all page routes)

```python
@router.get("/runs/{run_id}")
async def run_detail(
    request: Request,
    run_id: str,
    index: IndexManager = Depends(get_index_manager),
) -> HTMLResponse:
    run = index.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    context = {"run": run, "request": request}
    template = "pages/run_detail.html"
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(template, context)
    return templates.TemplateResponse("base.html", {**context, "page_template": template})
```

### Route Organization

| Category | File | Response Type |
|----------|------|--------------|
| Page routes | `dashboard/routes.py` | Dual-response (full page or fragment) |
| Partial routes | `dashboard/partials.py` | Always HTML fragment |
| SSE routes | `dashboard/sse.py` | `StreamingResponse` |
| Mutation routes | `dashboard/mutations.py` | Redirect or HTMX swap |

### Data Access — Always via Depends()

```python
# CORRECT
@router.get("/")
async def overview(
    index: IndexManager = Depends(get_index_manager),
    stats: StatsAggregator = Depends(get_stats_aggregator),
): ...

# WRONG — direct import in route handler
index = IndexManager()  # NO
```

### Template Context — Plain Dicts

```python
# CORRECT
context = {"runs": index.get_recent_runs(), "request": request}

# WRONG — no Pydantic models for template context
class OverviewContext(BaseModel): ...  # NO
```

### Dashboard Error Handling — HTML Only

```python
# Dashboard routes NEVER return JSON errors
# HTMX requests → HTML error banner fragment
# Full page requests → HTML error page
```

### Naming Conventions (Dashboard-Specific)

- Template files: `snake_case.html` (match route function name)
- SSE event names: `kebab-case` (e.g., `phase-update`, `run-complete`)
- Custom CSS classes: `kebab-case` (e.g., `chart-bar`, `phase-active`)
- HTMX target IDs match partial template names

### HTMX Attribute Order

```html
<div hx-get="/partials/active-runs"
     hx-trigger="every 3s"
     hx-target="#active-runs"
     hx-swap="outerHTML"
     hx-indicator="#loading">
```

Order: action → trigger → target → swap → push-url (if nav) → indicator

### SSE Events Carry HTML Fragments

```python
# CORRECT — SSE data is rendered HTML
yield f"event: phase-update\ndata: {html_fragment}\n\n"

# WRONG — SSE data is JSON
yield f"event: phase-update\ndata: {json.dumps(data)}\n\n"  # NO
```

---

## Anti-Patterns to Avoid

| Don't | Do Instead |
|-------|-----------|
| `print()` | `console.print()` |
| `raise Exception()` | Use `ADWError` hierarchy |
| Models outside `models/` | Centralize in `models/` |
| `Optional[X]` | `X \| None` |
| `dict` for structured data | Pydantic `BaseModel` |
| Manual file cleanup | Context managers |
| Untyped functions | Full type annotations |
| `def run(phases=[])` | `def run(phases=None)` |
| JSON from dashboard routes | HTML (full page or fragment) |
| Pydantic models for template context | Plain dicts with existing model objects |
| `hx-push-url` on polling | Only on navigation actions |
| Import from `webhook/` in dashboard | Use shared `server/` and `core/` |
| Inline styles for layout | Tailwind utility classes |
| Mix route categories in one file | Separate pages, partials, SSE, mutations |

---

## Async Model

**Pattern:** Sync with Async Islands

- Orchestrator/PhaseRunner: Synchronous
- LLM Executor internals: `asyncio.run()` for streaming

```python
# Orchestrator (sync)
def run_phase(self, phase: str) -> PhaseResult:
    return self.executor.execute(prompt)

# Executor (async internally)
def execute(self, prompt: str) -> LLMResult:
    return asyncio.run(self._stream_subprocess(prompt))
```

---

## Quick Reference

**Before writing code, verify:**
1. [ ] Models in `src/adw/models/`?
2. [ ] Using exception hierarchy?
3. [ ] Full type annotations?
4. [ ] Rich for CLI output?
5. [ ] Structured logging?
6. [ ] Tests in correct location?
7. [ ] Following naming conventions?

**Before writing dashboard code, also verify:**
8. [ ] Page routes use dual-response pattern?
9. [ ] Data access via `Depends()` only?
10. [ ] Template context is plain dict (no Pydantic)?
11. [ ] Routes in correct file (pages/partials/SSE/mutations)?
12. [ ] No imports from `webhook/`?
13. [ ] Error responses are HTML, not JSON?

---

_Last updated: 2026-02-11_
_Sources: architecture.md, architecture-web-dashboard.md_
