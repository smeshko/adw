# ADR-001: Test Suite Reduction Strategy

**Status:** Accepted
**Date:** 2026-01-05
**Decision Makers:** Test Audit Team

## Context

The ADW test suite had grown to ~2,280 tests across 114 files. Many tests provided minimal value while adding maintenance burden and execution time. An audit revealed that approximately 19% of tests fell into waste categories that don't catch real bugs.

### Problem Statement

1. **Slow CI/CD**: Full test suite takes ~10 minutes
2. **Maintenance burden**: Trivial tests break on refactors
3. **False confidence**: High test count doesn't mean high quality
4. **Mock testing**: Tests verifying mock behavior, not real code

## Decision

Reduce the test suite by eliminating tests in these waste categories:

### Categories to Eliminate

| Category | Description | Example |
|----------|-------------|---------|
| **Trivial Attribute Tests** | Tests that set a value and verify it equals what was set | `assert manager.runs_dir == runs_dir` |
| **Pydantic Smoke Tests** | Tests verifying Pydantic's built-in serialization | `assert "field" in model.model_dump_json()` |
| **Import Smoke Tests** | Tests that classes exist or can be imported | `assert LogManager is not None` |
| **Enum Existence Tests** | Tests that enum members exist or count | `assert len(PHASE_SEQUENCE) == 5` |
| **Redundant Variants** | Same logic tested multiple ways | Multiple tests for `rm -rf /`, `rm -rf ~`, `rm -rf .` |
| **Mock Class Tests** | Tests verifying mock objects work | `assert mock_executor.call_count == 0` |
| **Help Text Verification** | Tests checking `--help` output contains strings | `assert "RUN_ID" in result.output` |

### Categories to KEEP (Never Delete)

1. **Validation tests** - `test_*_required_fields`, `test_invalid_*`
2. **Business logic tests** - `test_context_merge()`, `test_duration_ms_calculation()`
3. **Error path tests** - `test_raises_*_error`, exception handling
4. **Security tests** - Redaction, pattern matching, dangerous command blocking
5. **I/O tests** - File operations, subprocess calls, thread safety
6. **Integration tests** - Real shell execution, YAML parsing

### Consolidation Strategy

Use `@pytest.mark.parametrize` to consolidate redundant test variants:

```python
# BEFORE: 5 separate tests
def test_detect_react(): ...
def test_detect_vue(): ...
def test_detect_angular(): ...

# AFTER: 1 parameterized test
@pytest.mark.parametrize("framework,marker", [
    ("react", "package.json with react"),
    ("vue", "package.json with vue"),
    ("angular", "angular.json"),
])
def test_detect_web_framework(framework, marker): ...
```

## Consequences

### Positive

- **Faster CI/CD**: ~25% reduction in execution time
- **Less maintenance**: Fewer tests to update on refactors
- **Clearer signal**: Test failures mean real bugs
- **Better patterns**: Parameterized tests are more maintainable

### Negative

- **Initial effort**: One-time audit and cleanup work
- **Reduced count**: Test count drops (may concern stakeholders)
- **Risk of over-deletion**: Must carefully preserve valuable tests

### Metrics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total Tests | ~2,280 | ~1,972 | -13.5% |
| Test Files | 114 | 112 | -2 files |
| Execution Time | ~10 min | ~8 min | -20% |
| Coverage | 22% | 22%+ | Maintained |

## Implementation

### Files Deleted
- `tests/unit/test_fixtures.py` - Mock testing (violates principle)
- `tests/unit/executors/test_imports.py` - Import smoke tests

### Files Reduced
- `tests/unit/models/test_logging.py` (41→8 tests)
- `tests/unit/models/test_phase.py` (26→5 tests)
- `tests/unit/models/test_context.py` (46→5 tests)
- `tests/unit/cli/test_verbosity.py` (14→1 test)
- `tests/unit/cli/test_logs.py` (57→11 tests)
- And 17 other files with smaller reductions

## Guidelines for Future Tests

### DO Write Tests For
- Validation logic and error handling
- Business rules and calculated properties
- Security-critical functionality
- Integration points (file I/O, subprocess, network)
- Edge cases and boundary conditions

### DON'T Write Tests For
- Pydantic model serialization (framework responsibility)
- Enum member existence (obvious from definition)
- Simple attribute assignment (Python works)
- Mock object behavior (mocks are tools, not subjects)
- Help text content (Typer handles this)
- Default values (visible in model definition)

### Test Naming Convention
```
test_<unit>_<behavior>_<condition>

# Good
test_context_merge_preserves_parent_values
test_duration_ms_returns_none_when_not_completed
test_redactor_removes_bearer_tokens

# Bad (likely trivial)
test_context_has_run_id
test_phase_status_exists
test_config_serializes
```

## References

- [TEST_REDUCTION_PLAN.md](../../testing/TEST_REDUCTION_PLAN.md) - Original analysis
- PR #68 - Implementation pull request
