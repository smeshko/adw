# System-Level Test Design: adw-sdk

**Date:** 2025-12-31
**Author:** Ivo
**Status:** Draft
**Mode:** System-Level Testability Review (Phase 3 - Solutioning)

---

## Executive Summary

This document provides a system-level testability assessment of the ADW-SDK architecture before implementation begins. It evaluates the architecture's controllability, observability, and reliability from a testing perspective, identifies architecturally significant requirements (ASRs) with risk scores, and recommends a test strategy for Sprint 0 setup.

**Overall Assessment:** PASS - The architecture is well-designed for testability with no critical blockers.

---

## Testability Assessment

### Controllability

**Status: PASS**

The architecture provides excellent controllability for testing:

| Aspect | Assessment | Evidence |
|--------|------------|----------|
| **System State Control** | PASS | Run context persisted as Pydantic JSON in `.adw/runs/<id>/context.json`. State snapshots at phase boundaries enable precise test setup. |
| **External Dependencies Mockable** | PASS | `LLMExecutor` is Protocol-based with explicit `MockExecutor` class in `executors/mock.py`. Claude Code CLI is only external dependency. |
| **Error Condition Triggering** | PASS | Custom exception hierarchy (`ADWError`, `LLMError`, `HookError`, etc.) with `recoverable` flags enables controlled failure injection. |
| **Configuration Override** | PASS | Three-tier resolution (project → user → bundled) allows test configs to override defaults. |

**Test Enablement:**
- Tests can seed run state via JSON fixtures
- MockExecutor returns controlled LLM responses
- Exception injection via mocked components
- Config fixtures for different scenarios

### Observability

**Status: PASS (with minor concerns)**

The architecture provides strong observability for debugging test failures:

| Aspect | Assessment | Evidence |
|--------|------------|----------|
| **System State Inspection** | PASS | Multi-tier logging: Console (Rich), raw `.log`, structured `.jsonl`. Full LLM stream capture in `.adw/runs/<id>/llm/`. |
| **Deterministic Test Results** | CONCERNS | LLM responses are inherently non-deterministic. Tests MUST use MockExecutor for determinism. |
| **NFR Validation** | PASS | Structured logging with `LogCategory` enum enables performance metrics extraction. Timeout configs allow SLO validation. |
| **State Snapshots** | PASS | `StateSnapshot` model at key moments enables "time travel" debugging. Stored in `snapshots/<seq>_<label>.json`. |

**Test Enablement:**
- Structured logs parseable for assertions
- LLM stream capture for replay testing
- Snapshots enable bisecting failures

**Concern:** LLM non-determinism requires MockExecutor for all automated tests. Real Claude Code integration should be validated separately in manual smoke tests.

### Reliability

**Status: PASS**

The architecture supports reliable, isolated test execution:

| Aspect | Assessment | Evidence |
|--------|------------|----------|
| **Test Isolation** | PASS | Each run isolated in `.adw/runs/<run_id>/`. ULID provides unique IDs. `filelock` prevents concurrent corruption. |
| **Failure Reproduction** | PASS | Full LLM stream capture + state snapshots enable deterministic replay. Actionable errors with `suggestion` field. |
| **Loose Coupling** | PASS | Protocol-based executors, clear boundaries (CLI → Core → Executors). Models centralized in `models/`. |

**Test Enablement:**
- pytest `tmp_path` fixture for isolated directories
- Parallel test execution safe (no shared state)
- Failures reproducible from captured artifacts

---

## Architecturally Significant Requirements (ASRs)

Based on PRD non-functional requirements, scored by risk (Probability × Impact):

### High-Priority Risks (Score ≥ 6)

| ID | NFR | Requirement | Probability | Impact | Score | Mitigation | Owner |
|----|-----|-------------|-------------|--------|-------|------------|-------|
| ASR-5 | NFR6 | State persistence before phase transitions | 3 | 3 | **9** | Atomic writes with fsync, validate on load | Core team |
| ASR-4 | NFR5 | Graceful LLM failure handling with retry | 2 | 3 | **6** | Custom exception hierarchy, exponential backoff | Executor team |
| ASR-6 | NFR8 | Resume from any phase boundary | 2 | 3 | **6** | State machine validation, checkpoint tests | Core team |
| ASR-8 | NFR14 | No secrets in logs | 2 | 3 | **6** | Redaction patterns, env var scanning | Security review |

### Medium-Priority Risks (Score 3-4)

| ID | NFR | Requirement | Probability | Impact | Score | Mitigation |
|----|-----|-------------|-------------|--------|-------|------------|
| ASR-1 | NFR1 | CLI startup <2s | 2 | 2 | **4** | Lazy imports, benchmark tests |
| ASR-3 | NFR3 | Non-blocking artifact writes | 2 | 2 | **4** | asyncio in executor, background writes |
| ASR-7 | NFR12 | Reproducible LLM interactions from logs | 2 | 2 | **4** | Full stream capture, replay tests |
| ASR-9 | NFR22 | >80% test coverage for core logic | 2 | 2 | **4** | pytest-cov, CI gates |

### Low-Priority Risks (Score 1-2)

| ID | NFR | Requirement | Probability | Impact | Score | Action |
|----|-----|-------------|-------------|--------|-------|--------|
| ASR-2 | NFR2 | Phase transitions <1s | 1 | 3 | **3** | Monitor |

---

## Test Levels Strategy

Based on architecture type (CLI Tool / SDK with async subprocess):

### Recommended Test Pyramid

```
        ╭─────────────╮
        │   E2E (10%) │  Critical CLI paths only
        ├─────────────┤
        │Integration  │  Component boundaries
        │   (30%)     │
        ├─────────────┤
        │    Unit     │  Business logic, pure functions
        │   (60%)     │
        ╰─────────────╯
```

### Test Level Distribution

| Level | Percentage | Focus Areas | Framework |
|-------|------------|-------------|-----------|
| **Unit** | 60% | Template engine, config parsing, state machine, exception handling, Pydantic models, ULID generation | pytest |
| **Integration** | 30% | Orchestrator → PhaseRunner → HookRunner flow, Context persistence, Command resolution, Executor protocol | pytest, pytest-asyncio |
| **E2E** | 10% | `adw run`, `adw resume`, `adw status`, interrupt handling (Ctrl+C), config override inheritance | pytest with subprocess |

### Module-to-Test-Level Mapping

| Module | Primary Level | Rationale |
|--------|---------------|-----------|
| `src/adw/models/` | Unit | Pure data structures, validation |
| `src/adw/commands/template.py` | Unit | Regex parsing, pure transformation |
| `src/adw/commands/resolver.py` | Integration | File system interaction |
| `src/adw/utils/` | Unit | Pure utilities |
| `src/adw/exceptions.py` | Unit | Exception hierarchy |
| `src/adw/executors/mock.py` | Unit | Controlled responses |
| `src/adw/executors/claude_code.py` | Integration | Subprocess streaming |
| `src/adw/hooks/runner.py` | Integration | Shell execution |
| `src/adw/core/orchestrator.py` | Integration | Component coordination |
| `src/adw/core/phase_runner.py` | Integration | Hook + executor flow |
| `src/adw/core/context_manager.py` | Integration | File I/O |
| `src/adw/logging/` | Integration | File + console output |
| `src/adw/cli/` | E2E | Full user experience |

---

## NFR Testing Approach

### Performance (NFR1-NFR4)

| Requirement | Test Type | Tool | Threshold |
|-------------|-----------|------|-----------|
| CLI startup <2s | Benchmark | pytest-benchmark | p95 < 2000ms |
| Phase transitions <1s | Benchmark | pytest-benchmark | p99 < 1000ms |
| Non-blocking artifacts | Async test | pytest-asyncio | No blocking on writes |
| State snapshots <500ms | Benchmark | pytest-benchmark | p95 < 500ms |

**Implementation:**
```python
# tests/performance/test_startup.py
import subprocess
import time

def test_cli_startup_time():
    start = time.perf_counter()
    result = subprocess.run(["adw", "--help"], capture_output=True)
    duration = time.perf_counter() - start

    assert result.returncode == 0
    assert duration < 2.0, f"CLI startup took {duration:.2f}s, expected <2s"
```

### Reliability (NFR5-NFR9)

| Requirement | Test Type | Scenario |
|-------------|-----------|----------|
| Graceful LLM failure | Integration | MockExecutor raises `LLMTimeoutError`, verify retry |
| State persistence | Integration | Kill process mid-phase, verify context.json valid |
| Interrupt recovery | E2E | Send SIGINT, verify checkpoint saved |
| Resume success | E2E | Create failed run, verify `adw resume` works |
| Config validation | Unit | Invalid YAML, verify helpful error message |

**Implementation:**
```python
# tests/integration/test_retry.py
from adw.executors.mock import MockExecutor
from adw.exceptions import LLMTimeoutError

def test_executor_retries_on_transient_failure(mock_executor):
    mock_executor.configure_failures([
        LLMTimeoutError("timeout"),
        LLMTimeoutError("timeout"),
        None  # Success on 3rd attempt
    ])

    result = mock_executor.execute("test prompt")

    assert result.success
    assert mock_executor.attempt_count == 3
```

### Security (NFR14-NFR17)

| Requirement | Test Type | Scenario |
|-------------|-----------|----------|
| No secrets in logs | Unit | Log message with API_KEY, verify redacted |
| Env var support | Unit | Sensitive config via env, verify not logged |
| Hook permissions | Integration | Hook attempts `../` traversal, verify blocked |
| Redaction patterns | Unit | Configurable patterns, verify all match |

**Implementation:**
```python
# tests/unit/logging/test_redaction.py
def test_api_key_redacted_from_logs(caplog):
    from adw.logging.manager import log

    log.info("Request with key", api_key="sk-12345abcdef")

    assert "sk-12345abcdef" not in caplog.text
    assert "[REDACTED]" in caplog.text or "api_key" not in caplog.text
```

### Maintainability (NFR22-NFR25)

| Requirement | Test Type | Tool | Threshold |
|-------------|-----------|------|-----------|
| >80% test coverage | CI gate | pytest-cov | `--cov-fail-under=80` |
| Type hints on public APIs | CI gate | mypy | `--strict` |
| Extensible phases | Architecture | - | New phase = no core changes |
| Extensible executors | Architecture | - | New executor = single file |

**CI Configuration:**
```yaml
# .github/workflows/ci.yml
- name: Type check
  run: uv run mypy src/

- name: Test with coverage
  run: uv run pytest --cov=adw --cov-fail-under=80 tests/
```

---

## Test Environment Requirements

### Local Development

| Requirement | Solution |
|-------------|----------|
| Python 3.13+ | Required for type hints |
| pytest ecosystem | pytest, pytest-asyncio, pytest-cov, pytest-benchmark |
| MockExecutor | Replaces Claude Code for deterministic tests |
| tmp_path fixture | Isolated `.adw/` directories per test |

### CI Pipeline

| Stage | Tests | Duration Target |
|-------|-------|-----------------|
| Lint | ruff check | <30s |
| Type | mypy strict | <60s |
| Unit | tests/unit/ | <2m |
| Integration | tests/integration/ | <5m |
| E2E | tests/integration/ (subprocess) | <3m |
| Coverage | All with --cov | Gate: 80% |

### Test Data Strategy

| Data Type | Source | Cleanup |
|-----------|--------|---------|
| Run contexts | JSON fixtures in `tests/fixtures/runs/` | pytest tmp_path |
| Config files | YAML fixtures in `tests/fixtures/configs/` | pytest tmp_path |
| LLM responses | Mock responses in `tests/fixtures/llm/` | In-memory |
| Hook scripts | Shell scripts in `tests/fixtures/hooks/` | pytest tmp_path |

---

## Testability Concerns

### Identified Concerns (Non-Blocking)

| Concern | Category | Impact | Mitigation | Status |
|---------|----------|--------|------------|--------|
| LLM Non-Determinism | TECH | Medium | MockExecutor for all automated tests; manual smoke tests for real Claude Code | PLANNED |
| Subprocess Testing | TECH | Low | MockExecutor eliminates need for real subprocess in most tests | PLANNED |
| File System State | OPS | Low | pytest `tmp_path` fixture for isolation | PLANNED |
| asyncio Complexity | TECH | Low | pytest-asyncio handles event loop lifecycle | PLANNED |

### No Critical Blockers

The architecture has been designed with testability in mind:
- Protocol-based abstractions enable mocking
- State serialization enables fixtures
- Logging enables observability
- Isolation prevents test pollution

---

## Recommendations for Sprint 0

### Framework Setup (`/framework` workflow)

1. **pytest Configuration**
   ```toml
   # pyproject.toml
   [tool.pytest.ini_options]
   testpaths = ["tests"]
   asyncio_mode = "auto"
   addopts = "--cov=adw --cov-report=html --cov-fail-under=80"
   ```

2. **MockExecutor Implementation**
   - Create `src/adw/executors/mock.py` early
   - Support configurable responses
   - Support configurable failures for retry testing
   - Track invocation count and arguments

3. **Fixture Library**
   - `conftest.py` with `tmp_adw_dir` fixture
   - `create_run_context()` factory
   - `create_config()` factory
   - `create_phase_result()` factory

### CI Setup (`/ci` workflow)

1. **GitHub Actions Pipeline**
   ```yaml
   jobs:
     lint:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: astral-sh/setup-uv@v1
         - run: uv sync
         - run: uv run ruff check src/

     type-check:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: astral-sh/setup-uv@v1
         - run: uv sync
         - run: uv run mypy src/

     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: astral-sh/setup-uv@v1
         - run: uv sync
         - run: uv run pytest --cov=adw --cov-fail-under=80 tests/
   ```

2. **Coverage Gates**
   - Minimum: 80% overall
   - Critical modules (`core/`, `executors/`): 90% recommended

3. **Performance Baseline**
   - Establish baseline benchmarks in Sprint 0
   - Track regression in CI

### Test Priority by Module

| Priority | Module | Rationale |
|----------|--------|-----------|
| P0 | `models/` | Data integrity, used everywhere |
| P0 | `exceptions.py` | Error handling consistency |
| P1 | `commands/template.py` | Core functionality |
| P1 | `core/context_manager.py` | State persistence (ASR-5) |
| P1 | `executors/mock.py` | Test infrastructure |
| P2 | `core/orchestrator.py` | Integration flows |
| P2 | `hooks/runner.py` | Shell execution |
| P3 | `cli/` | E2E validation |

---

## Quality Gate Criteria

### Phase 3 Gate (Before Implementation)

- [x] Testability assessment: PASS (all three dimensions)
- [x] ASRs identified and scored
- [x] Test strategy defined (60/30/10 split)
- [x] NFR testing approach documented
- [x] No critical testability concerns
- [x] Sprint 0 recommendations documented

### Pre-Release Gate (Future)

- [ ] All P0 tests pass (100%)
- [ ] P1 tests pass rate ≥95%
- [ ] No high-risk (≥6) items unmitigated
- [ ] Test coverage ≥80% for critical paths
- [ ] Performance baselines met (CLI <2s, transitions <1s)
- [ ] Security tests pass (no secrets in logs)

---

## Appendix

### Knowledge Base References

- `nfr-criteria.md` - NFR validation approach
- `test-levels-framework.md` - Test levels strategy guidance
- `risk-governance.md` - Risk scoring methodology
- `test-quality.md` - Quality standards and Definition of Done

### Related Documents

- PRD: `_bmad-output/prd.md`
- Architecture: `_bmad-output/architecture.md`
- UX Design: `_bmad-output/ux-design-specification.md`

---

**Generated by**: BMad TEA Agent - Test Architect Module
**Workflow**: `_bmad/bmm/workflows/testarch/test-design`
**Mode**: System-Level (Phase 3)
**Version**: 4.0 (BMad v6)
