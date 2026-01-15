# Story 13.2: Webhook Provider Protocol

Status: ready-for-dev
Linear Issue: not-configured
Epic: 13 - Webhook Infrastructure
Created: 2026-01-09

---

## Story

As a developer,
I want a pluggable provider interface,
so that new webhook sources can be added easily without modifying core server code.

## Acceptance Criteria

**Given** WebhookProvider protocol
**When** implemented
**Then** it requires:
```python
class WebhookProvider(Protocol):
    def verify_signature(self, request: Request) -> bool: ...
    def parse_event(self, request: Request) -> WebhookEvent: ...
    def should_trigger_run(self, event: WebhookEvent) -> bool: ...
    def extract_run_params(self, event: WebhookEvent) -> RunParams: ...
```

**Given** unknown provider in request path
**When** webhook received at `/webhook/unknown`
**Then** 404 returned with available providers listed

**Given** new provider implementation
**When** registered
**Then** it's automatically routed at `/webhook/{provider_name}`

## Tasks / Subtasks

### Task 1: Define Provider Protocol
- [x] Create `src/adw/webhook/providers/base.py` with `WebhookProvider` Protocol
- [x] Define `verify_signature()` method signature
- [x] Define `parse_event()` method signature
- [x] Define `should_trigger_run()` method signature
- [x] Define `extract_run_params()` method signature
- [x] Add comprehensive docstrings for each method

### Task 2: Create Event Models
- [ ] Create `WebhookEvent` model in `src/adw/models/webhook.py`
- [ ] Include fields: event_type, provider, payload, headers, timestamp
- [ ] Create `RunParams` model for extracted run parameters
- [ ] Include fields: feature_request, phases, source_info, metadata

### Task 3: Implement Provider Registry
- [ ] Create `src/adw/webhook/providers/registry.py`
- [ ] Implement `ProviderRegistry` class with register/get methods
- [ ] Support auto-discovery of enabled providers from config
- [ ] Implement `list_providers()` for showing available providers

### Task 4: Update Server Routes
- [ ] Modify `/webhook/{provider}` route to use provider registry
- [ ] Return 404 with available providers when provider not found
- [ ] Delegate signature verification to provider
- [ ] Delegate event parsing to provider
- [ ] Add error handling for provider method failures

### Task 5: Create Base Provider Implementation
- [ ] Create `src/adw/webhook/providers/__init__.py`
- [ ] Implement `BaseWebhookProvider` abstract class (optional helper)
- [ ] Add common utilities (header parsing, logging)
- [ ] Provide default implementations where sensible

### Task 6: Add Provider Loading
- [ ] Load enabled providers from project.yaml on server start
- [ ] Register providers in registry
- [ ] Log which providers are available
- [ ] Handle missing provider configuration gracefully

### Task 7: Write Tests
- [ ] Create `tests/unit/webhook/providers/test_base.py`
- [ ] Test protocol compliance checker
- [ ] Create `tests/unit/webhook/providers/test_registry.py`
- [ ] Test provider registration and retrieval
- [ ] Test unknown provider handling
- [ ] Test provider list endpoint

---

## Developer Context

### Technical Requirements

**From Architecture Document:**
- Use Python Protocol for provider interface (structural typing)
- Pydantic models for all data structures
- Provider instances must be stateless
- Registry pattern for dynamic provider lookup

**Design Principles:**
- Open/Closed Principle: Add new providers without modifying core
- Dependency Inversion: Core depends on abstractions, not implementations
- Single Responsibility: Each provider handles one external service

### Architecture Compliance

**File Locations:**
```
src/adw/webhook/
├── providers/                  # New package
│   ├── __init__.py            # Re-exports
│   ├── base.py                # WebhookProvider Protocol
│   └── registry.py            # ProviderRegistry
├── server.py                  # Modified: use registry
└── routes.py                  # Modified: provider routing
```

**Model Additions:**
```
src/adw/models/
└── webhook.py                 # Add: WebhookEvent, RunParams
```

### Library & Framework Requirements

**Protocol Pattern:**
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class WebhookProvider(Protocol):
    """Protocol for webhook provider implementations.

    Each provider handles webhooks from a specific external service
    (Linear, GitHub, etc.) and knows how to verify, parse, and
    process events from that service.
    """

    @property
    def name(self) -> str:
        """Unique provider identifier (e.g., 'linear', 'github')."""
        ...

    def verify_signature(self, request: Request) -> bool:
        """Verify the request came from the claimed provider.

        Args:
            request: The incoming FastAPI Request object

        Returns:
            True if signature is valid, False otherwise
        """
        ...

    def parse_event(self, request: Request) -> WebhookEvent:
        """Parse the raw request into a structured WebhookEvent.

        Args:
            request: The incoming FastAPI Request object

        Returns:
            Parsed WebhookEvent with provider-specific details

        Raises:
            ValueError: If request cannot be parsed
        """
        ...

    def should_trigger_run(self, event: WebhookEvent) -> bool:
        """Determine if this event should trigger an ADW run.

        Considers event type, labels, configuration rules, etc.

        Args:
            event: The parsed webhook event

        Returns:
            True if run should be triggered, False otherwise
        """
        ...

    def extract_run_params(self, event: WebhookEvent) -> RunParams:
        """Extract parameters needed to start an ADW run.

        Args:
            event: The parsed webhook event

        Returns:
            RunParams with feature_request, phases, and metadata
        """
        ...
```

**Registry Pattern:**
```python
class ProviderRegistry:
    """Registry for webhook provider implementations."""

    def __init__(self):
        self._providers: dict[str, WebhookProvider] = {}

    def register(self, provider: WebhookProvider) -> None:
        """Register a provider instance."""
        self._providers[provider.name] = provider

    def get(self, name: str) -> WebhookProvider | None:
        """Get a provider by name."""
        return self._providers.get(name)

    def list_providers(self) -> list[str]:
        """List all registered provider names."""
        return list(self._providers.keys())
```

### File Structure Requirements

**New Files to Create:**
1. `src/adw/webhook/providers/__init__.py` - Package exports
2. `src/adw/webhook/providers/base.py` - Protocol definition
3. `src/adw/webhook/providers/registry.py` - Registry implementation
4. `tests/unit/webhook/providers/__init__.py` - Test package
5. `tests/unit/webhook/providers/test_base.py` - Protocol tests
6. `tests/unit/webhook/providers/test_registry.py` - Registry tests

**Files to Modify:**
1. `src/adw/models/webhook.py` - Add WebhookEvent, RunParams models
2. `src/adw/webhook/server.py` - Initialize registry
3. `src/adw/webhook/routes.py` - Use registry for routing

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/webhook/providers/test_registry.py
from adw.webhook.providers.registry import ProviderRegistry
from adw.webhook.providers.base import WebhookProvider

class MockProvider:
    """Mock provider for testing."""
    name = "mock"

    def verify_signature(self, request): return True
    def parse_event(self, request): return WebhookEvent(...)
    def should_trigger_run(self, event): return True
    def extract_run_params(self, event): return RunParams(...)

def test_register_and_get_provider():
    registry = ProviderRegistry()
    provider = MockProvider()
    registry.register(provider)
    assert registry.get("mock") is provider

def test_unknown_provider_returns_none():
    registry = ProviderRegistry()
    assert registry.get("unknown") is None

def test_list_providers():
    registry = ProviderRegistry()
    registry.register(MockProvider())
    assert "mock" in registry.list_providers()
```

**Protocol Compliance Tests:**
```python
# tests/unit/webhook/providers/test_base.py
from adw.webhook.providers.base import WebhookProvider

def test_mock_provider_implements_protocol():
    provider = MockProvider()
    assert isinstance(provider, WebhookProvider)
```

---

## Previous Story Intelligence

**From Story 13.1:**
- FastAPI server framework established
- `/webhook/{provider}` route skeleton exists
- Request logging middleware in place
- WebhookConfig model exists in models/webhook.py

**Key Files Created in 13.1:**
- `src/adw/webhook/server.py` - FastAPI app
- `src/adw/webhook/routes.py` - Route handlers
- `src/adw/models/webhook.py` - Configuration models

---

## Git Intelligence

**Recent Patterns:**
- Protocol-based abstractions for extensibility (see LLMExecutor)
- Registry pattern used for command resolution
- Comprehensive docstrings on public interfaces

**Recommended Commit Pattern:**
```
feat(webhook): implement provider protocol and registry

- Add WebhookProvider Protocol with full interface
- Create WebhookEvent and RunParams models
- Implement ProviderRegistry for dynamic lookup
- Update routes to use provider registry
- Add 404 response with available providers
- Include comprehensive unit tests
```

---

## Latest Technical Information

**Python Protocol (PEP 544):**
- Structural subtyping (duck typing with type hints)
- `@runtime_checkable` enables isinstance() checks
- No explicit inheritance required for conformance
- Works well with mypy for static type checking

**FastAPI Request Handling:**
- `Request.headers` for header access
- `await Request.body()` for raw payload
- `await Request.json()` for parsed JSON
- State can be attached to `request.state`

---

## Project Context Reference

See: _bmad-output/project-context.md

Key patterns and rules from project context:
- Use Protocol for extensible interfaces
- All models in src/adw/models/
- Type annotations on all public functions
- Structured logging for events

---

## Dev Notes

### Critical Success Factors

1. **Protocol Completeness:** All required methods defined
2. **Registry Works:** Providers can be registered and retrieved
3. **Routing Works:** Requests correctly routed to providers
4. **404 Response:** Shows available providers

### Common Pitfalls to Avoid

- Don't make providers stateful - they should be stateless
- Don't couple registry to specific providers
- Don't forget `@runtime_checkable` decorator on Protocol
- Don't modify core server code when adding providers

### References

- [Source: _bmad-output/epics/epic-13-webhook-infrastructure.md#Story-13.2]
- [Source: _bmad-output/architecture.md#Protocol-Based-Abstraction]
- [Source: Python PEP 544 - Structural Subtyping]

---

## Dev Agent Record

### Context Reference

Story context created by create-epic workflow (Epic 13 generation)

### Agent Model Used

Claude Opus 4.5 (create-epic autonomous orchestrator)

### Debug Log References

### Completion Notes List

**Task 1 (2026-01-15):** Implemented WebhookProvider Protocol following existing LLMExecutor pattern from executors/base.py. Added @runtime_checkable decorator for isinstance() checks. Also added WebhookEvent and RunParams models to src/adw/models/webhook.py as they are needed by the Protocol type hints. All 3 protocol compliance tests pass.

### File List

**New Files:**
- `src/adw/webhook/providers/__init__.py`
- `src/adw/webhook/providers/base.py`
- `tests/unit/webhook/providers/__init__.py`
- `tests/unit/webhook/providers/test_base.py`

**Modified Files:**
- `src/adw/models/webhook.py` (added WebhookEvent, RunParams)

---

## Dependencies

- **Depends On:** Story 13.1 (Generic Webhook Server Framework)
- **Blocks:** Story 13.3 (Linear Provider), Story 13.6 (Signature Verification), Story 13.7 (GitHub Provider)
- **Can Parallel With:** None

### Dependency Rationale
- Story 13.1 provides the server framework this story extends
- Story 13.3 implements a concrete provider using this protocol
- Story 13.6 uses the verify_signature method defined here
- Story 13.7 implements another provider using this protocol
