# ADW Test Suite Reduction Plan

**Date:** 2026-01-05
**Analysis Method:** Comprehensive audit of all 2,280 tests across 114 test files
**Goal:** Reduce test count while maintaining robustness

---

## Executive Summary

| Category | Tests | Waste | % |
|----------|-------|-------|---|
| tests/unit/core/ | ~780 | 47 | 6% |
| tests/unit/cli/ | 593 | 120 | 20% |
| tests/unit/models/ | 382 | 173 | 45% |
| tests/unit/evidence/ | 322 | 100 | 31% |
| tests/unit/logging/ | 177 | 40 | 23% |
| tests/unit/security/ | 210 | 29 | 14% |
| tests/integration/ | 347 | 38 | 11% |
| **TOTAL** | **~2,811** | **~547** | **~19%** |

**Recommendation:** Delete approximately **547 tests** (19% of total)

---

## Categories of Waste

### 1. Trivial Attribute/Property Tests (~150 tests)
Tests that just set a value and verify it equals what was set.

**Example:**
```python
def test_init_with_run_dir(self):
    assert manager.runs_dir == runs_dir  # TRIVIAL
```

**Why delete:** Python's assignment works. These never catch bugs.

### 2. Pydantic Serialization Smoke Tests (~80 tests)
Tests that verify Pydantic's built-in `model_dump()`, `model_dump_json()`, `model_validate_json()`.

**Example:**
```python
def test_serialization_to_json(self):
    json_str = model.model_dump_json()
    assert "field_name" in json_str  # Testing Pydantic, not business logic
```

**Why delete:** Testing the framework, not your code.

### 3. Import/Smoke Tests (~40 tests)
Tests that verify classes exist or can be imported.

**Example:**
```python
def test_exports_log_manager():
    assert LogManager is not None  # TRIVIAL
```

**Why delete:** Import errors already fail loudly.

### 4. Trivial Enum Tests (~50 tests)
Tests that verify enum members exist or count.

**Example:**
```python
def test_phase_sequence_length():
    assert len(PHASE_SEQUENCE) == 5  # Fragile, not business logic
```

**Why delete:** Enum definitions are obvious. Changes break other tests anyway.

### 5. Redundant Variants (~100 tests)
Same logic tested multiple ways with minimal variation.

**Example:**
```python
def test_block_rm_rf_root(): ...
def test_block_rm_rf_home(): ...  # Same pattern, different path
def test_block_rm_rf_dot(): ...   # Same pattern, different path
```

**Why consolidate:** Use `@pytest.mark.parametrize` instead.

### 6. Mock Class Tests (~30 tests)
Tests that verify mock objects work (test_fixtures.py, some integration tests).

**Example:**
```python
def test_mock_executor_fixture(mock_executor):
    assert mock_executor.call_count == 0  # Testing the mock, not business logic
```

**Why delete:** Mocks are tools, not subjects. If the mock breaks, real tests fail.

### 7. Output Text Verification (~80 tests)
Tests that just check if a substring appears in output.

**Example:**
```python
def test_show_runs_includes_status():
    assert "running" in output  # Weak assertion
```

**Why delete:** Brittle, doesn't test logic, just formatting.

---

## Phase 1: Immediate Deletions (HIGH CONFIDENCE)

### tests/unit/test_fixtures.py - DELETE ENTIRE FILE
**Tests:** 6
**Reason:** Tests pytest fixtures and MockExecutor. Mocks are tools, not test subjects.

### tests/unit/executors/test_imports.py - DELETE ENTIRE FILE
**Tests:** 4
**Reason:** Import smoke tests. If imports fail, everything fails.

### tests/unit/core/test_constants.py - DELETE 5 OF 6 TESTS
```
- test_phase_sequence_immutable
- test_phase_sequence_length
- test_phase_sequence_no_duplicates
- test_phase_sequence_all_lowercase
- test_phase_sequence_all_strings
```
**Keep only:** `test_phase_sequence_order`

### tests/unit/logging/test_package.py - DELETE 8 TESTS
All `TestPackageExports` tests - pure import verification.

### tests/unit/models/ - DELETE 173 TESTS
See detailed breakdown below.

---

## Phase 2: Model Tests Reduction

### tests/unit/models/test_llm.py
**Delete 8 of 10 tests:**
- `test_create_minimal_tool_call` - trivial
- `test_create_full_tool_call` - trivial
- `test_tool_call_serialization` - Pydantic smoke
- `test_create_success_result` - trivial
- `test_create_failure_result` - trivial
- `test_create_result_with_tool_calls` - trivial
- `test_create_result_with_metrics` - trivial
- `test_result_serialization` - Pydantic smoke

**Keep:** `test_result_required_fields`, `test_acceptance_criteria_fields`

### tests/unit/models/test_phase.py
**Delete 21 of 26 tests:**
- All `TestPhaseStatus` enum tests (3)
- All trivial creation/assignment tests (15)
- Token tracking default tests (3)

**Keep:** Validation tests, `test_duration_ms_calculation`

### tests/unit/models/test_config.py
**Delete 18 of 27 tests:**
- All `test_defaults()` methods
- All trivial assignment tests

**Keep:** YAML parsing tests, validation tests

### tests/unit/models/test_context.py
**Delete 28 of 46 tests:**
- All default value tests
- All trivial assignment tests
- All serialization smoke tests

**Keep:** Validation tests (`test_invalid_ulid_*`), status constraints

### tests/unit/models/test_logging.py
**Delete 32 of 41 tests:**
- All enum value/count tests
- All trivial `LogContext` creation tests
- All `LogEvent` trivial tests
- LLM Capture model trivial tests

**Keep:** `test_verbosity_level_map_correct_mapping`, validation tests

### tests/unit/models/test_state_snapshot.py
**Delete 13 of 22 tests:**
- All label tests (4) - just string assignment
- Trivial creation tests
- Serialization smoke tests

**Keep:** Validation tests, roundtrip test

---

## Phase 3: CLI Tests Reduction

### tests/unit/cli/test_verbosity.py
**Delete 10 of 20 tests (50% waste):**
- All flag parsing tests (testing Typer, not business logic)
- Redundant integration tests

**Keep:** `test_quiet_and_verbose_mutually_exclusive`

### tests/unit/cli/test_status_display.py
**Delete 18 of 69 tests (26% waste):**
- Init attribute tests
- Color verification tests (can't verify in output)
- Weak output text checks

### tests/unit/cli/test_list_display.py
**Delete 14 of 36 tests (39% waste):**
- Truncation trivial tests
- Timestamp formatting brittle tests
- Status color dict assertions

### tests/unit/cli/test_logs.py
**Delete 35 of 150+ tests (23% waste):**
- Help text verification
- Repetitive "requires argument" tests
- Smoke tests with no assertions

### tests/unit/cli/test_init.py
**Refactor:** Consolidate 6 language detection tests into 1 parameterized test.

---

## Phase 4: Evidence Tests Reduction

### tests/unit/evidence/test_detector.py
**Delete/Consolidate 20-25 tests:**
Marker detection tests should be parameterized:
- 5 web framework tests → 1 parameterized
- 5 backend framework tests → 1 parameterized
- 8 mobile platform tests → 1 parameterized

### tests/unit/evidence/test_mobile_capture.py
**Delete 15-20 tests:**
- Redundant fallback tests
- Device detection variants

### tests/unit/evidence/test_cli_models.py
**Delete 8-10 tests:**
- Pydantic serialization smoke tests
- Default value tests

---

## Phase 5: Integration Tests Reduction

### tests/integration/test_progress_integration.py
**Delete 3 tests:**
- `test_phase_runner_calls_llm_progress_methods` - tests mocks
- `test_phase_runner_completes_llm_progress_on_error` - tests mocks
- `test_full_pipeline_progress_output` - trivial display test

### tests/integration/test_artifact_flow_integration.py
**Delete 5 tests + fixture:**
All tests using `integration_phase_runner` fixture (which mocks everything).

### tests/integration/test_phase_runner_integration.py
**Delete 1 test:**
- `test_pre_hook_failure_stops_phase` - redundant with test_hooks.py

---

## Implementation Strategy

### Step 1: Create Safety Net
```bash
# Run full test suite and capture baseline
pytest tests/ --tb=no -q > baseline_results.txt
```

### Step 2: Delete Files
```bash
rm tests/unit/test_fixtures.py
rm tests/unit/executors/test_imports.py
```

### Step 3: Surgical Deletions
Use editor or script to remove specific test functions by line number.

### Step 4: Parameterize Redundant Tests
Convert loops of similar tests to `@pytest.mark.parametrize`.

### Step 5: Verify Coverage Maintained
```bash
pytest tests/ --cov=src/adw --cov-report=term-missing
```

---

## Expected Outcome

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total Tests | ~2,280 | ~1,733 | -24% |
| Test Files | 114 | ~110 | -4 files |
| Execution Time | ~10 min | ~7.5 min | -25% |
| Coverage | 22% | 22%+ | Maintained |

---

## Tests Worth KEEPING (Never Delete)

1. **Validation tests** - `test_*_required_fields`, `test_invalid_*`, `test_*_must_be_*`
2. **Behavior tests** - `test_context_merge()`, `test_to_markdown()`, `test_from_markdown()`
3. **Error path tests** - `test_raises_*_error`, `test_*_failure_*`
4. **Integration tests** - Real shell execution, file I/O, signal handling
5. **Concurrency tests** - `test_concurrent_*`, lock tests
6. **YAML parsing tests** - `test_from_yaml_*`

---

## Files to Delete Entirely

1. `tests/unit/test_fixtures.py` - 6 tests (mock testing)
2. `tests/unit/executors/test_imports.py` - 4 tests (import smoke)

## Files to Heavily Reduce

1. `tests/unit/models/test_logging.py` - 32→9 tests
2. `tests/unit/models/test_context.py` - 46→18 tests
3. `tests/unit/models/test_phase.py` - 26→5 tests
4. `tests/unit/cli/test_logs.py` - 150+→115 tests
5. `tests/unit/cli/test_verbosity.py` - 20→10 tests

---

## Risk Assessment

**Low Risk Deletions:** Trivial attribute tests, import tests, enum count tests
**Medium Risk Deletions:** Serialization smoke tests, output text checks
**Review Before Deletion:** Any test with "validation", "required", "error" in name

---

## Appendix: Specific Line Numbers

See individual agent reports for exact line numbers to delete in each file.
