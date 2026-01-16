# Story 13.4: Event-to-Workflow Mapping

Status: ready-for-dev
Linear Issue: not-configured
Epic: 13 - Webhook Infrastructure
Created: 2026-01-09

---

## Story

As a developer,
I want to configure which events trigger which workflows,
so that I have fine-grained control over webhook automation behavior.

## Acceptance Criteria

**Given** event mapping configuration
**When** defined
**Then** options include:
```yaml
webhook:
  mappings:
    linear:
      issue_created:
        trigger: true
        require_label: "adw:auto"
        phases: ["plan", "build", "validation", "document"]
      comment_created:
        trigger: true
        require_mention: "@adw"
        parse_command: true
      issue_updated:
        trigger: false
```

**Given** event matches mapping
**When** trigger conditions met
**Then** run is started asynchronously

**Given** event doesn't match mapping
**When** received
**Then** event is logged and ignored

## Tasks / Subtasks

### Task 1: Define Mapping Models
- [x] Create `EventMapping` model in `src/adw/models/webhook.py`
- [x] Create `EventTriggerConfig` model for trigger conditions
- [x] Support fields: trigger, require_label, require_mention, parse_command, phases
- [x] Add validation for configuration values

### Task 2: Implement Mapping Configuration Loading
- [x] Add mappings section to `WebhookConfig` model
- [x] Create `src/adw/webhook/mapping.py` for mapping logic
- [x] Implement `EventMapper` class to evaluate trigger conditions
- [x] Load mappings from project.yaml on server start

### Task 3: Implement Event Evaluation
- [x] Create `evaluate_event()` method in EventMapper
- [x] Check if event type has mapping configured
- [x] Evaluate require_label condition
- [x] Evaluate require_mention condition
- [x] Return whether event should trigger and with what parameters

### Task 4: Implement Async Run Triggering
- [x] Create `src/adw/webhook/runner.py` for run triggering logic
- [x] Implement `trigger_run_async()` function
- [x] Use asyncio/background task for non-blocking execution
- [x] Integrate with ADW orchestrator
- [x] Handle run initiation errors gracefully

### Task 5: Update Provider Logic
- [x] Modify provider's `should_trigger_run()` to use EventMapper
- [x] Pass mapping configuration to provider on initialization
- [x] Update `extract_run_params()` to respect configured phases

### Task 6: Add Logging and Monitoring
- [ ] Log all events received with evaluation result
- [ ] Log trigger decisions with reasoning
- [ ] Log run initiation with run_id
- [ ] Add metrics for event processing (if metrics system exists)

### Task 7: Write Tests
- [ ] Create `tests/unit/webhook/test_mapping.py`
- [ ] Test mapping configuration loading
- [ ] Test require_label condition evaluation
- [ ] Test require_mention condition evaluation
- [ ] Test disabled event type handling
- [ ] Test async run triggering (mock orchestrator)

---

## Developer Context

### Technical Requirements

**From Architecture Document:**
- Configuration-driven behavior for flexibility
- Async run triggering for non-blocking webhook responses
- Comprehensive logging for debugging and auditing
- Graceful handling of unknown event types

**Configuration Design:**
- Per-provider, per-event type configuration
- Multiple condition types (label, mention, custom)
- Phase specification for targeted runs
- Default fallback behavior when no mapping exists

### Architecture Compliance

**File Locations:**
```
src/adw/webhook/
├── mapping.py                  # New: EventMapper class
├── runner.py                   # New: Run triggering logic
├── providers/
│   └── linear.py              # Modified: Use EventMapper
└── server.py                  # Modified: Initialize mapper
```

**Model Additions:**
```
src/adw/models/
└── webhook.py                 # Add: EventMapping, EventTriggerConfig
```

### Library & Framework Requirements

**Configuration Models:**
```python
class EventTriggerConfig(BaseModel):
    """Configuration for a single event type trigger."""
    trigger: bool = True
    require_label: str | None = None
    require_mention: str | None = None
    parse_command: bool = False
    phases: list[str] | None = None  # None = all phases

class ProviderMapping(BaseModel):
    """Event mappings for a specific provider."""
    issue_created: EventTriggerConfig | None = None
    issue_updated: EventTriggerConfig | None = None
    comment_created: EventTriggerConfig | None = None
    # Add more event types as needed

class WebhookMappings(BaseModel):
    """All webhook event mappings."""
    linear: ProviderMapping | None = None
    github: ProviderMapping | None = None
```

**EventMapper Implementation:**
```python
class EventMapper:
    """Evaluates webhook events against configured mappings."""

    def __init__(self, mappings: WebhookMappings):
        self.mappings = mappings

    def evaluate(
        self,
        provider: str,
        event_type: str,
        event: WebhookEvent,
    ) -> tuple[bool, dict | None]:
        """Evaluate if event should trigger a run.

        Args:
            provider: Provider name (e.g., "linear")
            event_type: Event type (e.g., "issue_created")
            event: The parsed webhook event

        Returns:
            Tuple of (should_trigger, run_params or None)
        """
        mapping = self._get_mapping(provider, event_type)
        if not mapping or not mapping.trigger:
            return False, None

        if not self._check_conditions(mapping, event):
            return False, None

        params = self._build_run_params(mapping, event)
        return True, params

    def _check_conditions(
        self,
        config: EventTriggerConfig,
        event: WebhookEvent,
    ) -> bool:
        """Check if all required conditions are met."""
        if config.require_label:
            if not self._has_label(event, config.require_label):
                return False

        if config.require_mention:
            if not self._has_mention(event, config.require_mention):
                return False

        return True
```

**Async Run Triggering:**
```python
import asyncio
from adw.core.orchestrator import Orchestrator

async def trigger_run_async(
    feature_request: str,
    phases: list[str] | None = None,
    source_info: dict | None = None,
) -> str:
    """Trigger an ADW run asynchronously.

    Args:
        feature_request: The feature to implement
        phases: Optional list of phases to run
        source_info: Metadata about the trigger source

    Returns:
        The run_id of the started run
    """
    # Create background task for run execution
    orchestrator = Orchestrator()
    run_id = await asyncio.to_thread(
        orchestrator.start_run,
        feature_request=feature_request,
        phases=phases,
        metadata=source_info,
    )
    return run_id
```

### File Structure Requirements

**New Files to Create:**
1. `src/adw/webhook/mapping.py` - EventMapper class
2. `src/adw/webhook/runner.py` - Async run triggering
3. `tests/unit/webhook/test_mapping.py` - Mapping tests
4. `tests/unit/webhook/test_runner.py` - Runner tests

**Files to Modify:**
1. `src/adw/models/webhook.py` - Add mapping models
2. `src/adw/webhook/providers/linear.py` - Use EventMapper
3. `src/adw/webhook/server.py` - Initialize EventMapper
4. `src/adw/webhook/routes.py` - Trigger runs via runner

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/webhook/test_mapping.py
import pytest
from adw.webhook.mapping import EventMapper
from adw.models.webhook import WebhookMappings, ProviderMapping, EventTriggerConfig

@pytest.fixture
def mapper():
    mappings = WebhookMappings(
        linear=ProviderMapping(
            issue_created=EventTriggerConfig(
                trigger=True,
                require_label="adw:auto",
                phases=["plan", "build"],
            ),
            issue_updated=EventTriggerConfig(trigger=False),
        )
    )
    return EventMapper(mappings)

def test_trigger_on_matching_label(mapper):
    event = WebhookEvent(
        event_type="issue_created",
        provider="linear",
        payload={"labels": [{"name": "adw:auto"}]},
    )
    should_trigger, params = mapper.evaluate("linear", "issue_created", event)
    assert should_trigger is True
    assert params["phases"] == ["plan", "build"]

def test_no_trigger_without_label(mapper):
    event = WebhookEvent(
        event_type="issue_created",
        provider="linear",
        payload={"labels": []},
    )
    should_trigger, _ = mapper.evaluate("linear", "issue_created", event)
    assert should_trigger is False

def test_no_trigger_when_disabled(mapper):
    event = WebhookEvent(
        event_type="issue_updated",
        provider="linear",
        payload={},
    )
    should_trigger, _ = mapper.evaluate("linear", "issue_updated", event)
    assert should_trigger is False

def test_unknown_event_type_returns_false(mapper):
    event = WebhookEvent(
        event_type="unknown_event",
        provider="linear",
        payload={},
    )
    should_trigger, _ = mapper.evaluate("linear", "unknown_event", event)
    assert should_trigger is False
```

**Async Run Tests:**
```python
# tests/unit/webhook/test_runner.py
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_trigger_run_async():
    with patch("adw.webhook.runner.Orchestrator") as mock_orch:
        mock_instance = mock_orch.return_value
        mock_instance.start_run.return_value = "run_123"

        run_id = await trigger_run_async(
            feature_request="Add dark mode",
            phases=["plan"],
            source_info={"provider": "linear", "issue": "ENG-42"},
        )

        assert run_id == "run_123"
        mock_instance.start_run.assert_called_once()
```

---

## Previous Story Intelligence

**From Story 13.3:**
- Linear provider parses events and extracts issue data
- Provider has `should_trigger_run()` method to override
- Labels and comments are available in parsed events

**Integration Point:**
- EventMapper will be called from provider's `should_trigger_run()`
- Provider passes event to mapper for evaluation
- Mapper returns decision and parameters

---

## Git Intelligence

**Recent Patterns:**
- Configuration-driven behavior via Pydantic models
- Separation of concerns (mapping vs triggering vs execution)
- Comprehensive logging at decision points

**Recommended Commit Pattern:**
```
feat(webhook): implement event-to-workflow mapping

- Add EventTriggerConfig and mapping models
- Implement EventMapper for trigger evaluation
- Add async run triggering via runner.py
- Support require_label and require_mention conditions
- Integrate with Linear provider
- Include comprehensive test coverage
```

---

## Latest Technical Information

**FastAPI Background Tasks:**
- `BackgroundTasks` class for fire-and-forget execution
- Tasks run after response is sent
- Good for webhook acknowledgment pattern

**Alternative: asyncio.create_task:**
- For longer-running operations
- Requires careful error handling
- Consider using task queue for production

---

## Project Context Reference

See: _bmad-output/project-context.md

Key patterns and rules from project context:
- Configuration via Pydantic models
- Structured logging for all decisions
- Type annotations on all functions
- Async patterns use asyncio

---

## Dev Notes

### Critical Success Factors

1. **Mapping Evaluation:** Correctly evaluate all condition types
2. **Async Triggering:** Non-blocking run initiation
3. **Configuration Loading:** Properly load and validate mappings
4. **Logging:** Clear logs for debugging trigger decisions

### Common Pitfalls to Avoid

- Don't block webhook response with run execution
- Don't ignore missing mapping configuration (use defaults)
- Don't forget to log why an event was not triggered
- Don't couple mapping logic to specific providers

### Design Decisions

- Mappings are optional - missing mapping means no trigger
- Conditions are AND logic (all must match)
- Unknown event types are silently ignored (logged at debug level)
- Run triggering is best-effort (errors logged, not propagated)

### References

- [Source: _bmad-output/epics/epic-13-webhook-infrastructure.md#Story-13.4]
- [Source: _bmad-output/architecture.md#Webhook-Event-Mapping]
- [Source: FastAPI Background Tasks Documentation]

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

- **Depends On:** Story 13.3 (Linear Webhook Provider)
- **Blocks:** Story 13.5 (Bot Loop Prevention)
- **Can Parallel With:** None

### Dependency Rationale
- Story 13.3 provides a concrete provider to test mapping with
- Story 13.5 needs event mapping to intercept and filter events
- Mapping configuration is used by loop prevention logic
