# Story 13.1: Generic Webhook Server Framework

Status: ready-for-dev
Linear Issue: not-configured
Epic: 13 - Webhook Infrastructure
Created: 2026-01-09

---

## Story

As a developer,
I want a webhook server that can receive events from multiple providers,
so that ADW can be triggered automatically by external events.

## Acceptance Criteria

**Given** command `adw webhook start`
**When** executed
**Then** FastAPI server starts on configured port (default: 8000)

**Given** webhook server
**When** running
**Then** health endpoint available at `GET /health`

**Given** incoming webhook
**When** received
**Then** request is logged with: timestamp, provider, event_type, payload_size

**Given** server configuration
**When** set in project.yaml
**Then** options include:
```yaml
webhook:
  port: 8000
  host: "0.0.0.0"
  providers:
    linear:
      enabled: true
      secret_env: LINEAR_WEBHOOK_SECRET
    github:
      enabled: false
      secret_env: GITHUB_WEBHOOK_SECRET
```

## Tasks / Subtasks

### Task 1: Add FastAPI Dependency
- [ ] Add `fastapi` and `uvicorn[standard]` to pyproject.toml dependencies
- [ ] Run `uv sync` to install dependencies
- [ ] Verify dependencies are correctly installed

### Task 2: Create Webhook Package Structure
- [ ] Create `src/adw/webhook/` package directory
- [ ] Create `src/adw/webhook/__init__.py`
- [ ] Create `src/adw/webhook/server.py` for FastAPI app
- [ ] Create `src/adw/webhook/config.py` for webhook configuration model
- [ ] Create `src/adw/webhook/routes.py` for route definitions

### Task 3: Implement Configuration Models
- [ ] Create `WebhookConfig` Pydantic model in `src/adw/models/webhook.py`
- [ ] Create `ProviderConfig` model for provider-specific settings
- [ ] Add webhook configuration to project config loading
- [ ] Support env variable references for secrets (e.g., `secret_env: LINEAR_WEBHOOK_SECRET`)

### Task 4: Implement FastAPI Server
- [ ] Create FastAPI app instance in `server.py`
- [ ] Implement `/health` endpoint returning `{"status": "healthy"}`
- [ ] Implement base `/webhook/{provider}` route skeleton
- [ ] Add request logging middleware for all webhook requests
- [ ] Add Rich console output for server startup/shutdown

### Task 5: Implement CLI Command
- [ ] Create `src/adw/cli/webhook.py` with Typer subcommand group
- [ ] Add `adw webhook start` command with options:
  - `--port` (default: 8000 or from config)
  - `--host` (default: 0.0.0.0 or from config)
  - `--reload` (development mode)
- [ ] Add `adw webhook status` command (placeholder)
- [ ] Register webhook commands in main app

### Task 6: Add Logging Integration
- [ ] Use ADW's structured logging for webhook events
- [ ] Log webhook requests with: timestamp, provider, event_type, payload_size
- [ ] Add request ID generation for tracing
- [ ] Integrate with existing LogManager

### Task 7: Write Tests
- [ ] Create `tests/unit/webhook/test_server.py`
- [ ] Test health endpoint returns 200
- [ ] Test webhook route returns 404 for unknown providers
- [ ] Test request logging captures expected fields
- [ ] Test configuration loading from project.yaml

---

## Developer Context

### Technical Requirements

**From Architecture Document:**
- Use FastAPI for webhook server (lightweight, async-native, modern)
- Use Uvicorn as ASGI server
- Follow existing CLI patterns (Typer + Rich)
- Use Pydantic for request/response models
- Integrate with existing logging infrastructure

**Performance Requirements:**
- Server startup should be fast (<5 seconds)
- Webhook responses should be under 200ms for simple acknowledgments
- Non-blocking event processing

### Architecture Compliance

**File Locations (new files):**
```
src/adw/
├── webhook/                    # New package
│   ├── __init__.py
│   ├── server.py              # FastAPI app
│   ├── config.py              # Configuration handling
│   └── routes.py              # Route definitions
├── models/
│   └── webhook.py             # New: WebhookConfig, ProviderConfig
└── cli/
    └── webhook.py             # New: CLI commands
```

**Integration Points:**
- CLI layer calls webhook server start via Uvicorn
- Webhook server uses ADW logging infrastructure
- Configuration loaded through existing config hierarchy
- Future stories will add provider implementations

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| FastAPI | 0.115+ | Webhook HTTP server |
| Uvicorn | 0.32+ | ASGI server |
| Pydantic | 2.12+ | Request/response validation |

**FastAPI Pattern:**
```python
from fastapi import FastAPI, Request
from rich.console import Console

console = Console()
app = FastAPI(title="ADW Webhook Server")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/webhook/{provider}")
async def receive_webhook(provider: str, request: Request):
    # Log and route to provider handler
    ...
```

**CLI Pattern:**
```python
import typer
import uvicorn

webhook_app = typer.Typer(name="webhook", help="Webhook server commands")

@webhook_app.command("start")
def start_server(
    port: int = typer.Option(8000, "--port", "-p"),
    host: str = typer.Option("0.0.0.0", "--host", "-H"),
):
    console.print(f"[bold green]Starting webhook server on {host}:{port}[/]")
    uvicorn.run("adw.webhook.server:app", host=host, port=port)
```

### File Structure Requirements

**New Files to Create:**
1. `src/adw/webhook/__init__.py` - Package init
2. `src/adw/webhook/server.py` - FastAPI application
3. `src/adw/webhook/config.py` - Configuration utilities
4. `src/adw/webhook/routes.py` - Route handlers
5. `src/adw/models/webhook.py` - Webhook models
6. `src/adw/cli/webhook.py` - CLI commands
7. `tests/unit/webhook/test_server.py` - Server tests
8. `tests/unit/webhook/__init__.py` - Test package init

**Files to Modify:**
1. `pyproject.toml` - Add fastapi, uvicorn dependencies
2. `src/adw/cli/app.py` - Register webhook subcommand
3. `src/adw/models/__init__.py` - Export webhook models

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/webhook/test_server.py
from fastapi.testclient import TestClient
from adw.webhook.server import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_unknown_provider_returns_404():
    response = client.post("/webhook/unknown", json={})
    assert response.status_code == 404
```

**Test Coverage:**
- Health endpoint functionality
- Unknown provider handling
- Request logging middleware
- Configuration model validation

---

## Previous Story Intelligence

This is the first story in Epic 13. No previous story learnings available.

**Epic Context:**
- Epic 13 establishes webhook infrastructure for external integrations
- Story 13.1 provides the foundation server framework
- Stories 13.2-13.7 will build provider-specific implementations on top

---

## Git Intelligence

**Recent Patterns:**
- Typer CLI commands follow kebab-case naming
- Rich console used for all CLI output
- Pydantic models centralized in models/ directory
- New features added as separate packages under src/adw/

**Recommended Commit Pattern:**
```
feat(webhook): implement generic webhook server framework

- Add FastAPI/Uvicorn dependencies
- Create webhook package with server, config, routes
- Add /health and /webhook/{provider} endpoints
- Implement webhook CLI commands (start, status)
- Add request logging middleware
- Include comprehensive unit tests
```

---

## Latest Technical Information

**FastAPI 0.115+ (current stable):**
- Native Pydantic v2 support
- Automatic OpenAPI documentation at /docs
- Async request handling by default
- Built-in request validation

**Uvicorn 0.32+ (current stable):**
- High-performance ASGI server
- Hot reload support for development
- Graceful shutdown handling
- Configurable workers

**Integration Considerations:**
- FastAPI's TestClient for unit testing
- Uvicorn's programmatic API for CLI integration
- Middleware pattern for request logging

---

## Project Context Reference

See: _bmad-output/project-context.md

Key patterns and rules from project context:
- All CLI output must use Rich Console
- Exception hierarchy must be used for errors
- Type annotations required on all functions
- Models must be in src/adw/models/
- Structured logging with context fields

---

## Dev Notes

### Critical Success Factors

1. **FastAPI Integration:** Server must start cleanly via CLI
2. **Health Endpoint:** Must return 200 with correct payload
3. **Logging:** All requests must be logged with required fields
4. **Configuration:** Must support project.yaml webhook config

### Common Pitfalls to Avoid

- Don't block the event loop with sync operations
- Don't store secrets in config - use environment variable references
- Don't forget to register webhook commands in main CLI app
- Don't use print() - use Rich Console for CLI output

### References

- [Source: _bmad-output/epics/epic-13-webhook-infrastructure.md#Story-13.1]
- [Source: _bmad-output/architecture.md#Future-Enhancement-Webhook-Infrastructure]
- [Source: _bmad-output/project-context.md#Technology-Stack]

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

- **Depends On:** None (first story in epic)
- **Blocks:** Story 13.2 (Webhook Provider Protocol)
- **Can Parallel With:** None

### Dependency Rationale
- Story 13.2 requires the webhook server framework to register providers
- Story 13.3-13.7 all depend on the server being operational
