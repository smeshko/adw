# Story 7.6: Implement Secret Redaction

Status: done
Linear Issue: not-configured
Epic: 7 - Observability & Logging
Created: 2026-01-03

---

## Story

As a developer,
I want sensitive data redacted from logs,
so that secrets are never exposed.

## Acceptance Criteria

**Given** log message containing API key pattern
**When** logged
**Then** the key is replaced with [REDACTED] (NFR14)

**Given** environment variables with sensitive names
**When** logged
**Then** values are redacted (API_KEY, SECRET, TOKEN, PASSWORD)

**Given** configurable redaction patterns in project.yaml
**When** logging
**Then** custom patterns are also redacted (NFR17)

**Given** a log export
**When** generated
**Then** all redaction rules are applied

## Tasks / Subtasks

### Task 1: Create Redaction Models (models/config.py)
- [x] Add `RedactionConfig` model to config
- [x] Define default redaction patterns
- [x] Support custom patterns from project.yaml

### Task 2: Implement Redactor (logging/redactor.py)
- [x] Create `Redactor` class
- [x] Implement pattern-based redaction
- [x] Support environment variable name matching
- [x] Implement `redact(content: str) -> str` method
- [x] Handle JSON content (deep redaction)

### Task 3: Define Default Patterns
- [x] API key patterns: `Bearer [A-Za-z0-9-_]+`, `sk-[A-Za-z0-9]+`
- [x] Environment variables: `*_KEY`, `*_SECRET`, `*_TOKEN`, `*_PASSWORD`
- [x] Common secrets: AWS keys, GitHub tokens, etc.
- [x] Document patterns in code comments

### Task 4: Integrate with Log Manager
- [x] Apply redaction before writing to all transports
- [x] Redact console output
- [x] Redact file logs (raw and structured)
- [x] Redact LLM captures (request/response)

### Task 5: Add Configuration Support
- [x] Load redaction patterns from project.yaml
- [x] Merge with default patterns
- [x] Support pattern enable/disable

### Task 6: Write Unit Tests
- [x] Test default pattern redaction
- [x] Test custom pattern addition
- [x] Test environment variable redaction
- [x] Test JSON deep redaction
- [x] Test log manager integration

---

## Relevant Feature Documentation

<!-- Secret redaction specified in architecture docs -->

---

## Developer Context

### Technical Requirements

**From PRD:**
- NFR14: No secrets in logs
- NFR17: Configurable redaction patterns

**Default Patterns:**
```python
DEFAULT_REDACTION_PATTERNS = [
    # API Keys
    r"Bearer\s+[A-Za-z0-9\-_\.]+",
    r"sk-[A-Za-z0-9]{20,}",        # OpenAI (20+ chars for flexibility)
    r"AKIA[A-Z0-9]{16}",           # AWS Access Key
    r"sk-ant-[A-Za-z0-9\-]{20,}",  # Anthropic (20+ chars for flexibility)
    r"ghp_[A-Za-z0-9]{36}",        # GitHub Personal Token
    r"gho_[A-Za-z0-9]{36}",        # GitHub OAuth Token
    r"github_pat_[A-Za-z0-9_]{82}", # GitHub PAT (fine-grained)

    # Generic patterns
    r"(?i)api[_-]?key['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9\-_\.]{8,}",
    r"(?i)secret[_-]?key['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9\-_\.]{8,}",
    r"(?i)password['\"]?\s*[:=]\s*['\"]?[^\s'\"]{4,}",
]

SENSITIVE_ENV_PATTERNS = [
    r".*_KEY$",
    r".*_SECRET$",
    r".*_TOKEN$",
    r".*_PASSWORD$",
    r".*_API_KEY$",
    r".*_AUTH$",
    r"^APIKEY$",       # Standalone without underscore
    r"^CREDENTIALS?$", # CREDENTIAL or CREDENTIALS
]
```

### Architecture Compliance

**Files to Create:**
```
src/adw/logging/
└── redactor.py       # Redaction logic (NEW)
```

**Files to Modify:**
```
src/adw/models/config.py     # Add RedactionConfig
src/adw/logging/manager.py   # Integrate redactor
src/adw/logging/file.py      # Apply redaction before write
src/adw/logging/console.py   # Apply redaction before display
src/adw/logging/llm_capture.py  # Apply to LLM captures
```

**Configuration in project.yaml:**
```yaml
logging:
  redaction:
    enabled: true
    patterns:
      - "my-custom-token-[A-Za-z0-9]+"
      - "ACME_[A-Z0-9]{20}"
    disable_defaults: false
```

### Library & Framework Requirements

**Regex Redaction:**
```python
import re
from typing import Pattern

class Redactor:
    REDACTED = "[REDACTED]"

    def __init__(self, patterns: list[str]):
        self.patterns = [re.compile(p) for p in patterns]

    def redact(self, content: str) -> str:
        result = content
        for pattern in self.patterns:
            result = pattern.sub(self.REDACTED, result)
        return result

    def redact_dict(self, data: dict) -> dict:
        """Deep redaction of dictionary values."""
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.redact(value)
            elif isinstance(value, dict):
                result[key] = self.redact_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self.redact_dict(v) if isinstance(v, dict)
                    else self.redact(v) if isinstance(v, str)
                    else v
                    for v in value
                ]
            else:
                result[key] = value
        return result
```

**Environment Variable Redaction:**
```python
def should_redact_env(name: str) -> bool:
    for pattern in SENSITIVE_ENV_PATTERNS:
        if re.match(pattern, name):
            return True
    return False

def redact_env_dict(env: dict[str, str]) -> dict[str, str]:
    return {
        k: "[REDACTED]" if should_redact_env(k) else v
        for k, v in env.items()
    }
```

### File Structure Requirements

**Redactor Location:** `src/adw/logging/redactor.py`

**Integration Points:**
1. LogManager.log() → applies redaction
2. FileTransport.write() → already redacted
3. ConsoleTransport.write() → already redacted
4. LLMCaptureManager.capture_*() → apply redaction

### Testing Requirements

**Test Cases:**
```python
def test_redacts_bearer_token():
    redactor = Redactor(DEFAULT_REDACTION_PATTERNS)
    content = "Authorization: Bearer abc123xyz"
    result = redactor.redact(content)
    assert "abc123xyz" not in result
    assert "[REDACTED]" in result

def test_redacts_nested_dict():
    redactor = Redactor(DEFAULT_REDACTION_PATTERNS)
    data = {"config": {"api_key": "sk-abc123"}}
    result = redactor.redact_dict(data)
    assert result["config"]["api_key"] == "[REDACTED]"

def test_custom_patterns():
    patterns = DEFAULT_REDACTION_PATTERNS + ["ACME_[A-Z0-9]+"]
    redactor = Redactor(patterns)
    assert "[REDACTED]" in redactor.redact("Token: ACME_ABC123")
```

---

## Previous Story Intelligence

**From Story 7.1:**
- LogManager central hub for logging
- All transports receive events through manager
- Apply redaction at manager level before routing

**From Story 7.3:**
- LLMCaptureManager writes request/response files
- Placeholder `redact_secrets()` function
- Replace placeholder with real Redactor

**Dependency:** Story 7.1 must be completed first.

---

## Git Intelligence

**Existing patterns:**
- Config loading in `config/loader.py`
- Pydantic models in `models/config.py`
- Manager patterns in logging module

---

## Latest Technical Information

**Regex Performance:**
- Compile patterns once at initialization
- Use `re.compile()` for repeated matching
- Consider `regex` library for complex patterns

**Security Considerations:**
- Redact before writing, not after
- Cover all output paths (console, file, LLM)
- Test with real secret patterns

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:
- Configuration in Pydantic models
- Logging module isolated
- All output through logging system

---

## Dev Notes

- Redaction is a cross-cutting concern
- Must be applied before ANY output
- Default patterns should cover common cases
- Custom patterns allow project-specific secrets
- Performance: compile patterns once, reuse
- Consider allowing pattern disable for debugging (with warning)

### Project Structure Notes

- New file: `logging/redactor.py`
- Modify LogManager to apply redaction
- Update config model for redaction settings

### References

- [Source: docs/arch-logging.md#Log-Configuration] - Redaction config example
- [Source: _bmad-output/architecture.md] - NFR14, NFR17 requirements
- [Source: src/adw/logging/manager.py] - Integration point

---

## Dependencies

**Depends On:**
- Story 7.1: Multi-Tier Logging System (provides LogManager)

**Blocks:** None

**Parallel With:**
- Story 7.2, 7.3, 7.5 can run in parallel

---

## Dev Agent Record

### Context Reference
- PRD: NFR14 (No secrets in logs), NFR17 (Configurable redaction patterns)
- Architecture: logging module, config models

### Agent Model Used
claude-opus-4-5-20251101

### Debug Log References
N/A

### Completion Notes List
1. Created `RedactionConfig` and `LoggingConfig` models in `models/config.py`
2. Implemented `Redactor` class in `logging/redactor.py` with:
   - Pattern-based string redaction
   - Environment variable name detection
   - Deep dictionary redaction for JSON logs
3. Defined comprehensive default patterns covering:
   - Bearer tokens, OpenAI keys, AWS keys, GitHub PATs
   - Anthropic keys, generic api_key/password/token patterns
   - Sensitive env var suffixes (_KEY, _SECRET, _TOKEN, _PASSWORD)
4. Integrated redactor with `LogManager` - redaction applied before all transports
5. Added configuration support via `configure_default_logger()` and `create_redactor_from_config()`
6. Wrote 48 comprehensive unit tests with 90%+ coverage on new code

### File List
**New Files:**
- `src/adw/logging/redactor.py` - Redactor class and patterns
- `tests/unit/logging/test_redactor.py` - 39 tests for redactor

**Modified Files:**
- `src/adw/models/config.py` - Added RedactionConfig, LoggingConfig
- `src/adw/logging/manager.py` - Integrated redactor with LogManager
- `src/adw/logging/__init__.py` - Exported redaction functions
- `tests/unit/logging/test_manager.py` - Added 9 redaction tests

