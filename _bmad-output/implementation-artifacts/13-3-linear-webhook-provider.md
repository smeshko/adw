# Story 13.3: Linear Webhook Provider

Status: done
Linear Issue: not-configured
Epic: 13 - Webhook Infrastructure
Created: 2026-01-09

---

## Story

As a user,
I want Linear issue events to trigger ADW runs,
so that I can automate feature development from Linear task management.

## Acceptance Criteria

**Given** Linear webhook configured
**When** issue created with label `adw:auto`
**Then** ADW run starts with issue as feature description

**Given** Linear issue comment containing `@adw run`
**When** comment is posted
**Then** ADW run starts for that issue

**Given** Linear webhook
**When** received
**Then** signature is verified using `LINEAR_WEBHOOK_SECRET`

**Given** Linear issue event
**When** parsed
**Then** extracts: issue_id, title, description, labels, assignee

**Given** ADW command in comment (e.g., `@adw run --phase plan`)
**When** parsed
**Then** command flags are respected

## Tasks / Subtasks

### Task 1: Create Linear Provider Package
- [x] Create `src/adw/webhook/providers/linear.py`
- [x] Implement `LinearProvider` class conforming to `WebhookProvider` Protocol
- [x] Add provider to registry on initialization

### Task 2: Implement Signature Verification
- [x] Implement `verify_signature()` using HMAC-SHA256
- [x] Read secret from environment variable specified in config
- [x] Handle missing secret gracefully (log warning, verification skipped)
- [x] Parse `X-Linear-Signature` header

### Task 3: Implement Event Parsing
- [ ] Create `LinearEvent` model for Linear-specific payload structure
- [ ] Map Linear event types: issue_created, issue_updated, comment_created
- [ ] Extract issue data: id, identifier, title, description, state
- [ ] Extract labels, assignee, project information
- [ ] Handle malformed payloads gracefully

### Task 4: Implement Run Trigger Logic
- [ ] Check for `adw:auto` label on issue created events
- [ ] Check for `@adw run` pattern in comment text
- [ ] Parse command flags from comment (--phase, --skip-verify, etc.)
- [ ] Respect event mapping configuration from project.yaml

### Task 5: Implement Run Parameter Extraction
- [ ] Build feature_request from issue title + description
- [ ] Include issue identifier in source_info metadata
- [ ] Parse phases from comment command or use defaults
- [ ] Include Linear issue URL for reference

### Task 6: Add Linear-Specific Models
- [ ] Add `LinearEvent` model to `src/adw/models/webhook.py`
- [ ] Add `LinearIssue` model for issue data structure
- [ ] Add `LinearComment` model for comment data structure
- [ ] Document Linear webhook payload structure

### Task 7: Add Configuration Support
- [ ] Support Linear configuration in project.yaml
- [ ] Configuration options: enabled, secret_env, auto_label, mention_pattern
- [ ] Default values for all configuration options

### Task 8: Write Tests
- [ ] Create `tests/unit/webhook/providers/test_linear.py`
- [ ] Test signature verification with known payloads
- [ ] Test event parsing for each event type
- [ ] Test trigger logic for various scenarios
- [ ] Test parameter extraction accuracy
- [ ] Create test fixtures for Linear webhook payloads

---

## Developer Context

### Technical Requirements

**From Linear Webhook Documentation:**
- Webhooks are sent as POST requests with JSON bodies
- `X-Linear-Signature` header contains HMAC-SHA256 signature
- Event type indicated by `action` field and resource type
- Nested objects for related resources (issue, comment, etc.)

**Integration Requirements:**
- Must handle all relevant Linear events: Issue, Comment
- Must support label-based triggering (adw:auto)
- Must support comment-based triggering (@adw run)
- Must parse command flags from comments

### Architecture Compliance

**File Locations:**
```
src/adw/webhook/providers/
├── __init__.py                # Modified: export LinearProvider
├── base.py                    # Existing: Protocol definition
├── registry.py                # Existing: ProviderRegistry
└── linear.py                  # New: LinearProvider implementation
```

**Model Additions:**
```
src/adw/models/
└── webhook.py                 # Add: LinearEvent, LinearIssue, LinearComment
```

### Library & Framework Requirements

**Linear Signature Verification:**
```python
import hmac
import hashlib

def verify_linear_signature(
    payload: bytes,
    signature: str,
    secret: str,
) -> bool:
    """Verify Linear webhook signature.

    Args:
        payload: Raw request body bytes
        signature: Value from X-Linear-Signature header
        secret: Webhook secret from LINEAR_WEBHOOK_SECRET env var

    Returns:
        True if signature is valid
    """
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

**Linear Event Structure:**
```python
class LinearEvent(BaseModel):
    """Parsed Linear webhook event."""
    action: str  # "create", "update", "remove"
    type: str  # "Issue", "Comment", etc.
    data: dict  # Event-specific payload
    created_at: datetime
    webhook_timestamp: int
    webhook_id: str
    url: str | None = None

class LinearIssue(BaseModel):
    """Linear issue data."""
    id: str
    identifier: str  # e.g., "ENG-123"
    title: str
    description: str | None
    state: dict  # {id, name, color, type}
    labels: list[dict]  # [{id, name, color}]
    assignee: dict | None  # {id, name, email}
    url: str
```

**Command Parsing:**
```python
import re

COMMAND_PATTERN = r'@adw\s+run\s*(.*)'

def parse_adw_command(text: str) -> dict | None:
    """Parse @adw run command from comment text.

    Args:
        text: Comment body text

    Returns:
        Dict with parsed options or None if no command found
    """
    match = re.search(COMMAND_PATTERN, text, re.IGNORECASE)
    if not match:
        return None

    args = match.group(1).strip()
    options = {}

    # Parse --phase flag
    phase_match = re.search(r'--phase\s+(\w+)', args)
    if phase_match:
        options['from_phase'] = phase_match.group(1)

    # Parse other flags as needed
    return options
```

### File Structure Requirements

**New Files to Create:**
1. `src/adw/webhook/providers/linear.py` - Linear provider implementation
2. `tests/unit/webhook/providers/test_linear.py` - Linear provider tests
3. `tests/fixtures/webhook/linear/` - Test fixture directory
4. `tests/fixtures/webhook/linear/issue_created.json` - Sample payload
5. `tests/fixtures/webhook/linear/comment_created.json` - Sample payload

**Files to Modify:**
1. `src/adw/webhook/providers/__init__.py` - Export LinearProvider
2. `src/adw/models/webhook.py` - Add Linear-specific models
3. `src/adw/webhook/server.py` - Auto-register LinearProvider if enabled

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/webhook/providers/test_linear.py
import pytest
from adw.webhook.providers.linear import LinearProvider
from adw.models.webhook import LinearEvent

@pytest.fixture
def linear_provider():
    return LinearProvider(secret="test_secret")

@pytest.fixture
def issue_created_payload():
    return {
        "action": "create",
        "type": "Issue",
        "data": {
            "id": "abc123",
            "identifier": "ENG-42",
            "title": "Add dark mode",
            "description": "Implement dark mode toggle",
            "labels": [{"name": "adw:auto"}],
        },
        "createdAt": "2024-01-15T10:00:00Z",
    }

def test_parse_issue_created_event(linear_provider, issue_created_payload):
    event = linear_provider.parse_event_from_payload(issue_created_payload)
    assert event.action == "create"
    assert event.type == "Issue"
    assert event.data["identifier"] == "ENG-42"

def test_should_trigger_on_adw_auto_label(linear_provider, issue_created_payload):
    event = linear_provider.parse_event_from_payload(issue_created_payload)
    assert linear_provider.should_trigger_run(event) is True

def test_should_not_trigger_without_label(linear_provider):
    payload = {"action": "create", "type": "Issue", "data": {"labels": []}}
    event = linear_provider.parse_event_from_payload(payload)
    assert linear_provider.should_trigger_run(event) is False

def test_parse_adw_command_from_comment():
    text = "Let's implement this. @adw run --phase build"
    result = parse_adw_command(text)
    assert result["from_phase"] == "build"
```

**Signature Verification Tests:**
```python
def test_verify_valid_signature(linear_provider):
    payload = b'{"action":"create"}'
    secret = "test_secret"
    signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    assert verify_linear_signature(payload, signature, secret) is True

def test_verify_invalid_signature(linear_provider):
    payload = b'{"action":"create"}'
    assert verify_linear_signature(payload, "invalid", "test_secret") is False
```

---

## Previous Story Intelligence

**From Story 13.2:**
- `WebhookProvider` Protocol defined with all required methods
- `ProviderRegistry` available for registration
- `WebhookEvent` and `RunParams` models exist

**Key Interfaces to Implement:**
- `verify_signature(request: Request) -> bool`
- `parse_event(request: Request) -> WebhookEvent`
- `should_trigger_run(event: WebhookEvent) -> bool`
- `extract_run_params(event: WebhookEvent) -> RunParams`

---

## Git Intelligence

**Recent Patterns:**
- Provider implementations as separate modules
- Model-first approach with comprehensive Pydantic models
- Extensive test fixtures for external service mocking

**Recommended Commit Pattern:**
```
feat(webhook): implement Linear webhook provider

- Add LinearProvider implementing WebhookProvider Protocol
- Implement HMAC-SHA256 signature verification
- Parse issue_created and comment_created events
- Support adw:auto label and @adw run triggers
- Extract run parameters from Linear issues
- Include comprehensive test suite with fixtures
```

---

## Latest Technical Information

**Linear Webhook Events (2025):**
- Event structure: `{action, type, data, createdAt, webhookTimestamp, webhookId}`
- Issue events: create, update, remove
- Comment events: create, update, remove
- Label data nested in issue data as array

**Linear API Identifiers:**
- Issue IDs are UUIDs (internal)
- Identifiers are team-prefix + number (e.g., ENG-123)
- URLs follow pattern: `https://linear.app/{workspace}/issue/{identifier}`

---

## Project Context Reference

See: _bmad-output/project-context.md

Key patterns and rules from project context:
- Use Pydantic for all external data validation
- Environment variables for secrets
- Structured logging for all events
- Protocol-based providers for extensibility

---

## Dev Notes

### Critical Success Factors

1. **Signature Verification:** Must correctly verify Linear signatures
2. **Event Parsing:** Must handle all relevant Linear event types
3. **Trigger Logic:** Must correctly identify when to trigger runs
4. **Command Parsing:** Must parse @adw run commands accurately

### Common Pitfalls to Avoid

- Don't store secrets in code or config files
- Don't assume payload structure - validate with Pydantic
- Don't ignore signature verification errors
- Don't forget to handle missing optional fields

### Linear-Specific Considerations

- Label names are case-sensitive
- Comment bodies may contain markdown formatting
- Issue descriptions may be null
- Webhook delivery is not guaranteed (implement idempotency)

### References

- [Source: _bmad-output/epics/epic-13-webhook-infrastructure.md#Story-13.3]
- [Source: Linear API Documentation - Webhooks]
- [Source: _bmad-output/architecture.md#Task-Manager-Integration]

---

## Dev Agent Record

### Context Reference

Story context created by create-epic workflow (Epic 13 generation)

### Agent Model Used

Claude Opus 4.5 (create-epic autonomous orchestrator)

### Debug Log References

### Completion Notes List

### File List

---

## Dependencies

- **Depends On:** Story 13.2 (Webhook Provider Protocol)
- **Blocks:** Story 13.4 (Event-to-Workflow Mapping)
- **Can Parallel With:** Story 13.6 (Signature Verification), Story 13.7 (GitHub Provider)

### Dependency Rationale
- Story 13.2 provides the WebhookProvider Protocol this implements
- Story 13.4 needs a concrete provider to test event mapping
- Story 13.6 shares signature verification patterns
- Story 13.7 follows similar implementation patterns
