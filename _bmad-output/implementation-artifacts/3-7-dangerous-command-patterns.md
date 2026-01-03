# Story 3.7: Dangerous Command Patterns

Status: ready-for-dev
Linear Issue: not-configured
Epic: 3 - Hook & Phase Execution
Created: 2026-01-03

---

## Story

As a developer,
I want a default set of blocked command patterns,
So that common destructive operations are prevented out of the box.

## Acceptance Criteria

**Given** default security configuration
**When** ADW initializes
**Then** these patterns are blocked by default:
- `rm -rf /` and variants (`rm -rf ~`, `rm -rf .`)
- `chmod 777` on sensitive paths
- `git push --force` to main/master
- Direct writes to `.env` files

**Given** a blocked pattern is triggered
**When** the block occurs
**Then** error includes: pattern matched, suggested alternative, how to override

**Given** user needs to override a block
**When** `--allow-dangerous` flag is passed
**Then** blocks are logged as warnings but not enforced

## Tasks / Subtasks

### Task 1: Define Comprehensive Default Patterns
- [x] Create `src/adw/security/defaults.py` with:
  - `DEFAULT_SHELL_PATTERNS`: List of blocked shell command patterns
  - `DEFAULT_FILE_PATTERNS`: List of blocked file access patterns
  - `PATTERN_METADATA`: Dictionary mapping patterns to descriptions and alternatives

### Task 2: Implement Pattern Categories
- [x] Create categories in `BlockedPattern` model:
  - `destructive`: rm -rf, format, dd commands
  - `permission`: chmod 777, chown root
  - `git_dangerous`: force push, reset --hard
  - `secret_access`: .env, credentials, secrets
- [x] Add `category` field to BlockedPattern model

### Task 3: Implement Pattern Matching Engine
- [x] Enhance `src/adw/security/patterns.py` with:
  - `PatternMatcher` class
  - `match_command(command: str) -> list[PatternMatch]`
  - `match_file_access(path: str) -> list[PatternMatch]`
  - Context-aware matching (distinguish between safe and dangerous uses)

### Task 4: Add Alternative Suggestions
- [x] Create `src/adw/security/suggestions.py` with:
  - Mapping of blocked patterns to safe alternatives
  - Examples for each blocked pattern
  - Override instructions with `--allow-dangerous`

### Task 5: Enhance SecurityError with Rich Context
- [ ] Update `SecurityError` to include:
  - `alternatives`: List of safe alternative commands
  - `override_instruction`: How to bypass if needed
  - `severity`: "critical", "warning", "info"

### Task 6: Implement Override Logging
- [ ] When `--allow-dangerous` is active:
  - Log blocked patterns as warnings (not errors)
  - Continue execution instead of blocking
  - Track all overridden blocks in run log

### Task 7: Write Unit Tests
- [ ] Test each default pattern category
- [ ] Test pattern matching edge cases
- [ ] Test alternative suggestions
- [ ] Test override behavior
- [ ] Test context-aware matching (safe vs dangerous uses)

---

## Relevant Feature Documentation

**Dependency**: Story 3.6 (Security Hook Infrastructure) must be completed first.

---

## Developer Context

### Technical Requirements

- **Pattern Format**: Regular expressions with named groups where helpful
- **Context Awareness**: Some patterns should only block in certain contexts
- **Performance**: Pre-compile all patterns at module load time
- **Extensibility**: Allow project-level pattern additions/removals

### Architecture Compliance

**From architecture.md:**

1. **Module Location**: Add to `src/adw/security/` package
2. **Configuration**: Patterns configurable via `project.yaml`
3. **Logging**: Use structured logging for all blocked patterns
4. **Error Messages**: Must include actionable suggestions (NFR18)

### Library & Framework Requirements

- **re**: Standard library regex (already in use)
- **Pydantic v2**: For pattern metadata models
- **No additional dependencies**

### File Structure Requirements

**New Files:**
- `src/adw/security/defaults.py` - Default pattern definitions
- `src/adw/security/suggestions.py` - Alternative command suggestions

**Modified Files:**
- `src/adw/security/patterns.py` - Enhanced pattern matching
- `src/adw/security/interceptor.py` - Category-based blocking
- `src/adw/exceptions.py` - Enhanced SecurityError fields
- `src/adw/models/security.py` - Add category field to BlockedPattern

**Test Files:**
- `tests/unit/security/test_defaults.py`
- `tests/unit/security/test_suggestions.py`
- `tests/unit/security/test_patterns.py` (extend existing)

### Testing Requirements

**Unit Tests:**
- Each default pattern has specific test cases
- Edge cases for each pattern (valid vs blocked)
- Override behavior with `--allow-dangerous`
- Alternative suggestion generation

**Test Coverage:** >80% for security module

---

## Previous Story Intelligence

**From Story 3.6 (Security Hook Infrastructure):**
- SecurityInterceptor class handles the blocking
- SecurityError exception for blocked operations
- ToolLogger for tracking blocked/allowed calls
- This story extends with comprehensive patterns

---

## Git Intelligence

Relevant patterns from codebase:
- Secret redaction patterns in `logging/redactor.py`
- Pattern-based matching for log categories

---

## Latest Technical Information

**Regex Patterns for Common Dangerous Commands:**

```python
# rm -rf patterns
r"rm\s+(-[rRfFiI]+\s+)*(/|~|\.|\.\.)"   # rm with flags pointing to root/home/current
r"rm\s+-rf?\s+\*"                        # rm -rf * (wildcard in current dir)

# chmod patterns
r"chmod\s+777\s+"                        # chmod 777 anything
r"chmod\s+-R\s+777"                      # recursive chmod 777

# git dangerous patterns
r"git\s+push\s+.*--force"                # force push
r"git\s+push\s+-f\s+"                    # short form force
r"git\s+reset\s+--hard"                  # hard reset
r"git\s+clean\s+-fd"                     # clean with force and directories

# env file writes
r">\s*\.env\b"                           # redirect to .env
r"echo\s+.*>\s*\.env"                    # echo to .env
r"cat\s+.*>\s*\.env"                     # cat to .env
```

---

## Project Context Reference

See: `docs/project-context.md` (if exists)

Key patterns and rules:
- Follow existing regex patterns from `logging/redactor.py`
- Use constants for default values
- Compile patterns once at module load

---

## Dev Notes

### Default Pattern Categories

**Category: destructive**
```python
DESTRUCTIVE_PATTERNS = [
    BlockedPattern(
        pattern=r"rm\s+(-[rRfFiI]+\s+)*(/|~|\.)",
        description="Recursive delete of root, home, or current directory",
        severity="critical",
        category="destructive",
        alternative="Use specific paths: rm -rf ./node_modules",
    ),
    BlockedPattern(
        pattern=r"mkfs\.",
        description="Format filesystem",
        severity="critical",
        category="destructive",
        alternative="This operation requires manual execution",
    ),
]
```

**Category: permission**
```python
PERMISSION_PATTERNS = [
    BlockedPattern(
        pattern=r"chmod\s+777",
        description="Setting world-writable permissions",
        severity="warning",
        category="permission",
        alternative="Use more restrictive permissions: chmod 755 or chmod 644",
    ),
]
```

**Category: git_dangerous**
```python
GIT_DANGEROUS_PATTERNS = [
    BlockedPattern(
        pattern=r"git\s+push\s+.*--force",
        description="Force push to remote",
        severity="warning",
        category="git_dangerous",
        alternative="Use --force-with-lease for safer force push",
    ),
]
```

**Category: secret_access**
```python
SECRET_ACCESS_PATTERNS = [
    BlockedPattern(
        pattern=r"cat\s+\.env\b(?!\.example|\.sample|\.template)",
        description="Reading .env file",
        severity="warning",
        category="secret_access",
        alternative="Use environment variables directly: $VAR_NAME",
    ),
]
```

### Override Message Format

When a pattern is blocked:
```
Error [DANGEROUS_COMMAND_BLOCKED]: Command matches dangerous pattern
Pattern: rm -rf with root/home path
Category: destructive

Suggested alternative:
  Use specific paths: rm -rf ./node_modules

To override (use with caution):
  adw run --allow-dangerous "your feature"
```

### Project Structure Notes

- Builds on Story 3.6 SecurityInterceptor
- Patterns defined in separate `defaults.py` for easy modification
- Suggestions in `suggestions.py` for maintainability

### References

- [Source: _bmad-output/architecture.md#Error Handling]
- [Source: _bmad-output/epics/epic-3-hook-phase-execution.md#Story 3.7]
- [Source: src/adw/logging/redactor.py - Pattern matching examples]
- [Source: src/adw/exceptions.py - Error formatting patterns]

---

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

### Completion Notes List

- Task 1: Created comprehensive defaults.py with DESTRUCTIVE_PATTERNS, PERMISSION_PATTERNS, GIT_DANGEROUS_PATTERNS, SECRET_ACCESS_PATTERNS, FILE_ACCESS_PATTERNS. Also created BlockedPattern model in models/security.py with category field. 20 tests written and passing.
- Task 2: BlockedPattern model already includes PatternCategory type with all four categories (destructive, permission, git_dangerous, secret_access). Added 17 comprehensive tests for security models (BlockedPattern, SecurityConfig, ToolCallLog).
- Task 3: Implemented PatternMatcher class with match_command() and match_file_access() methods. Supports custom patterns, allow_dangerous mode, and ALLOWED_ENV_PATTERNS for exceptions (.env.example, .env.sample). 25 tests added.
- Task 4: Created SuggestionFormatter class with format_single() and format_multiple() methods. Added CATEGORY_EXAMPLES and get_override_instruction(). 11 tests added.

### File List

**New Files:**
- src/adw/security/__init__.py
- src/adw/security/defaults.py
- src/adw/security/patterns.py
- src/adw/security/suggestions.py
- src/adw/models/security.py
- tests/unit/security/__init__.py
- tests/unit/security/test_defaults.py
- tests/unit/security/test_patterns.py
- tests/unit/security/test_suggestions.py
- tests/unit/models/test_security.py

**Modified Files:**
- src/adw/models/__init__.py

## Dependencies

- **Depends On:** None
- **Blocks:** None
- **Can Parallel With:** Story 3.6, Story 3.8