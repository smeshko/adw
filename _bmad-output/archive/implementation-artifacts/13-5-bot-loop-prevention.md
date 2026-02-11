# Story 13.5: Bot Loop Prevention

Status: ready-for-dev
Linear Issue: not-configured
Epic: 13 - Webhook Infrastructure
Created: 2026-01-09

---

## Story

As a developer,
I want ADW to not trigger itself,
so that webhooks don't cause infinite loops when ADW posts comments or creates issues.

## Acceptance Criteria

**Given** ADW posts a comment
**When** comment is posted
**Then** it includes marker: `<!-- [ADW] -->`

**Given** incoming comment event
**When** comment contains ADW marker
**Then** event is ignored (no run triggered)

**Given** ADW creates/updates an issue
**When** action is performed
**Then** it includes metadata identifying ADW as author

**Given** incoming issue event
**When** author is ADW bot
**Then** event is ignored

## Tasks / Subtasks

### Task 1: Define Bot Markers Configuration
- [ ] Add `bot_markers` section to webhook configuration
- [ ] Configure comment marker (default: `<!-- [ADW] -->`)
- [ ] Configure author prefix (default: `[ADW]` or user identifier)
- [ ] Make markers configurable via project.yaml

### Task 2: Implement Marker Injection
- [ ] Create `src/adw/webhook/markers.py` for marker utilities
- [ ] Implement `inject_comment_marker()` function
- [ ] Implement `inject_author_identifier()` function
- [ ] Ensure markers are added to all ADW-generated content

### Task 3: Implement Loop Detection
- [ ] Implement `is_adw_generated()` function in markers.py
- [ ] Check for comment marker in text content
- [ ] Check for author identifier in event metadata
- [ ] Support custom detection patterns

### Task 4: Integrate with Event Mapper
- [ ] Add loop detection check before trigger evaluation
- [ ] Log skipped events with reason "bot loop prevention"
- [ ] Add metrics for prevented loops (if metrics exist)
- [ ] Make loop prevention configurable (enabled by default)

### Task 5: Update Linear Provider
- [ ] Check for ADW markers in comment events
- [ ] Check author information in issue events
- [ ] Skip trigger for ADW-generated content
- [ ] Log detection of self-generated events

### Task 6: Create Output Integration
- [ ] Integrate marker injection with task manager integration
- [ ] Ensure all ADW-posted comments include marker
- [ ] Ensure all ADW-created issues include identifier
- [ ] Document marker format in comments

### Task 7: Write Tests
- [ ] Create `tests/unit/webhook/test_markers.py`
- [ ] Test marker injection functions
- [ ] Test marker detection functions
- [ ] Test integration with event mapper
- [ ] Test edge cases (partial markers, similar text)

---

## Developer Context

### Technical Requirements

**From Architecture Document:**
- Bot loop prevention is critical for production safety
- Markers must be invisible to users in rendered content
- Detection must be fast and not impact webhook response time
- Configuration allows customization per deployment

**Safety Requirements:**
- Must prevent infinite loops with 100% reliability
- Must handle edge cases (malformed content, missing metadata)
- Must work across all supported providers
- Must log all prevention actions for debugging

### Architecture Compliance

**File Locations:**
```
src/adw/webhook/
├── markers.py                  # New: Marker utilities
├── mapping.py                  # Modified: Add loop detection
└── providers/
    └── linear.py              # Modified: Check for markers
```

**Configuration in project.yaml:**
```yaml
webhook:
  bot_markers:
    comment: "<!-- [ADW] -->"
    author_prefix: "[ADW]"
    enabled: true  # Default: true
```

### Library & Framework Requirements

**Marker Utilities:**
```python
import re

DEFAULT_COMMENT_MARKER = "<!-- [ADW] -->"
DEFAULT_AUTHOR_PREFIX = "[ADW]"

def inject_comment_marker(
    text: str,
    marker: str = DEFAULT_COMMENT_MARKER,
) -> str:
    """Add ADW marker to comment text.

    The marker is added at the end of the comment and is invisible
    when rendered as HTML/Markdown.

    Args:
        text: Original comment text
        marker: Marker string (default: HTML comment)

    Returns:
        Text with marker appended
    """
    return f"{text}\n\n{marker}"

def contains_adw_marker(
    text: str,
    marker: str = DEFAULT_COMMENT_MARKER,
) -> bool:
    """Check if text contains ADW marker.

    Args:
        text: Text to check
        marker: Marker string to look for

    Returns:
        True if marker is present
    """
    return marker in text

def is_adw_author(
    author_name: str | None,
    prefix: str = DEFAULT_AUTHOR_PREFIX,
) -> bool:
    """Check if author name indicates ADW bot.

    Args:
        author_name: Author name or identifier
        prefix: Prefix that identifies ADW

    Returns:
        True if author is ADW bot
    """
    if not author_name:
        return False
    return author_name.startswith(prefix)
```

**Event Filtering:**
```python
class LoopDetector:
    """Detects and prevents ADW triggering itself."""

    def __init__(self, config: BotMarkersConfig):
        self.comment_marker = config.comment
        self.author_prefix = config.author_prefix
        self.enabled = config.enabled

    def should_skip_event(self, event: WebhookEvent) -> tuple[bool, str]:
        """Check if event should be skipped to prevent loop.

        Args:
            event: The webhook event to check

        Returns:
            Tuple of (should_skip, reason)
        """
        if not self.enabled:
            return False, ""

        # Check comment content for marker
        if event.event_type == "comment_created":
            body = event.payload.get("body", "")
            if contains_adw_marker(body, self.comment_marker):
                return True, "ADW marker detected in comment"

        # Check author for all events
        author = event.payload.get("author", {})
        author_name = author.get("name") or author.get("displayName")
        if is_adw_author(author_name, self.author_prefix):
            return True, "ADW author detected"

        return False, ""
```

**Integration with EventMapper:**
```python
class EventMapper:
    def __init__(self, mappings: WebhookMappings, loop_detector: LoopDetector):
        self.mappings = mappings
        self.loop_detector = loop_detector

    def evaluate(
        self,
        provider: str,
        event_type: str,
        event: WebhookEvent,
    ) -> tuple[bool, dict | None]:
        # Check for loop prevention first
        skip, reason = self.loop_detector.should_skip_event(event)
        if skip:
            logger.info(
                "Event skipped (loop prevention)",
                provider=provider,
                event_type=event_type,
                reason=reason,
            )
            return False, None

        # Continue with normal evaluation
        ...
```

### File Structure Requirements

**New Files to Create:**
1. `src/adw/webhook/markers.py` - Marker utilities and LoopDetector
2. `tests/unit/webhook/test_markers.py` - Marker and detection tests

**Files to Modify:**
1. `src/adw/models/webhook.py` - Add BotMarkersConfig model
2. `src/adw/webhook/mapping.py` - Add LoopDetector integration
3. `src/adw/webhook/providers/linear.py` - Use LoopDetector
4. `src/adw/webhook/server.py` - Initialize LoopDetector

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/webhook/test_markers.py
import pytest
from adw.webhook.markers import (
    inject_comment_marker,
    contains_adw_marker,
    is_adw_author,
    LoopDetector,
)

def test_inject_marker():
    text = "Hello world"
    result = inject_comment_marker(text)
    assert result == "Hello world\n\n<!-- [ADW] -->"

def test_contains_marker_positive():
    text = "Some text\n\n<!-- [ADW] -->"
    assert contains_adw_marker(text) is True

def test_contains_marker_negative():
    text = "Some text without marker"
    assert contains_adw_marker(text) is False

def test_is_adw_author_positive():
    assert is_adw_author("[ADW] Build Bot") is True

def test_is_adw_author_negative():
    assert is_adw_author("John Developer") is False

def test_is_adw_author_none():
    assert is_adw_author(None) is False
```

**LoopDetector Tests:**
```python
@pytest.fixture
def detector():
    config = BotMarkersConfig(
        comment="<!-- [ADW] -->",
        author_prefix="[ADW]",
        enabled=True,
    )
    return LoopDetector(config)

def test_skip_comment_with_marker(detector):
    event = WebhookEvent(
        event_type="comment_created",
        provider="linear",
        payload={"body": "Some comment\n\n<!-- [ADW] -->"},
    )
    skip, reason = detector.should_skip_event(event)
    assert skip is True
    assert "marker" in reason.lower()

def test_skip_adw_author(detector):
    event = WebhookEvent(
        event_type="issue_created",
        provider="linear",
        payload={"author": {"name": "[ADW] Build Bot"}},
    )
    skip, reason = detector.should_skip_event(event)
    assert skip is True
    assert "author" in reason.lower()

def test_allow_normal_event(detector):
    event = WebhookEvent(
        event_type="issue_created",
        provider="linear",
        payload={
            "author": {"name": "John Developer"},
            "body": "Please implement dark mode",
        },
    )
    skip, _ = detector.should_skip_event(event)
    assert skip is False

def test_disabled_detection(detector):
    detector.enabled = False
    event = WebhookEvent(
        event_type="comment_created",
        provider="linear",
        payload={"body": "<!-- [ADW] -->"},
    )
    skip, _ = detector.should_skip_event(event)
    assert skip is False
```

---

## Previous Story Intelligence

**From Story 13.4:**
- EventMapper evaluates events before triggering runs
- Integration point is before trigger condition evaluation
- Logging infrastructure in place for decision tracking

**Key Integration:**
- LoopDetector checks happen first in EventMapper.evaluate()
- Skip decision logged before returning False
- Normal evaluation continues if no loop detected

---

## Git Intelligence

**Recent Patterns:**
- Configuration via Pydantic models
- Utility functions with comprehensive type hints
- Logging at all decision points

**Recommended Commit Pattern:**
```
feat(webhook): implement bot loop prevention

- Add marker utilities for injection and detection
- Implement LoopDetector for self-triggering prevention
- Add BotMarkersConfig to webhook configuration
- Integrate with EventMapper for pre-evaluation check
- Log all skipped events with prevention reason
- Include comprehensive test suite
```

---

## Latest Technical Information

**HTML Comment Markers:**
- `<!-- text -->` is invisible when rendered as HTML/Markdown
- Supported by Linear, GitHub, and most platforms
- Must not contain nested comments

**Author Detection:**
- Bot accounts often have specific naming patterns
- Linear and GitHub support bot user identification
- Some platforms provide `is_bot` field in author data

---

## Project Context Reference

See: _bmad-output/project-context.md

Key patterns and rules from project context:
- Safety-critical features need comprehensive testing
- Logging at all decision points
- Configuration via Pydantic models
- Default values that are production-safe

---

## Dev Notes

### Critical Success Factors

1. **100% Loop Prevention:** Must never allow self-triggering
2. **Invisible Markers:** Markers must not affect user experience
3. **Fast Detection:** Must not slow down webhook processing
4. **Configurable:** Allow customization for different deployments

### Common Pitfalls to Avoid

- Don't use markers that might appear in normal content
- Don't assume author field is always present
- Don't forget to test edge cases (empty content, null author)
- Don't disable loop prevention in production

### Security Considerations

- Markers could theoretically be spoofed by malicious users
- Consider additional checks (API token identity, webhook source)
- Log all prevented loops for security auditing
- Don't expose internal marker format in public docs

### References

- [Source: _bmad-output/epics/epic-13-webhook-infrastructure.md#Story-13.5]
- [Source: _bmad-output/architecture.md#Bot-Loop-Prevention]
- [Source: Linear Webhook Documentation - Author Fields]

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

- **Depends On:** Story 13.4 (Event-to-Workflow Mapping)
- **Blocks:** None (end of main dependency chain)
- **Can Parallel With:** None

### Dependency Rationale
- Story 13.4 provides EventMapper where loop detection integrates
- This is the final story in the main sequential dependency chain
- Stories 13.6 and 13.7 can be done in parallel with 13.3
