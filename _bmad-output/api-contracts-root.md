# API Contracts Documentation

## Project: ADW SDK (adw)

**Generated:** 2026-01-18
**Project Type:** Backend + CLI
**Framework:** FastAPI

---

## API Overview

The ADW SDK exposes a webhook server built with FastAPI for receiving external events that trigger development workflow runs.

### Base Configuration

| Setting | Value |
|---------|-------|
| Default Port | 8000 |
| Default Host | 0.0.0.0 |
| Server Framework | FastAPI + Uvicorn |

---

## Webhook Endpoints

### Health Check

```
GET /health
```

**Description:** Health check endpoint for monitoring and load balancers.

**Response:**
```json
{
  "status": "healthy"
}
```

**Status Codes:**
- `200 OK`: Server is healthy

---

### Receive Webhook

```
POST /webhook/{provider}
```

**Description:** Receive and process webhooks from external providers (GitHub, Linear, etc.).

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `provider` | string | Provider name (e.g., `github`, `linear`, `gitlab`, `stripe`) |

**Request Headers (Provider-Specific):**
| Provider | Header | Description |
|----------|--------|-------------|
| Linear | `x-linear-event` | Event type |
| GitHub | `x-github-event` | Event type |
| GitLab | `x-gitlab-event` | Event type |
| Stripe | `stripe-event-type` | Event type |

**Authentication:**
- Signature verification via provider-specific mechanisms
- Returns `401 Unauthorized` for invalid signatures

**Response (Success):**
```json
{
  "status": "received",
  "request_id": "uuid",
  "trigger_evaluation": true,
  "run_triggered": true,
  "run_id": "ulid"
}
```

**Status Codes:**
- `202 Accepted`: Webhook received and processed
- `400 Bad Request`: Invalid webhook payload
- `401 Unauthorized`: Invalid webhook signature
- `404 Not Found`: Provider not configured or not found

---

## Supported Providers

### GitHub Provider
- Signature verification: HMAC-SHA256
- Event types: `issues`, `issue_comment`, `pull_request`, etc.
- Extracts: issue/PR title, body, labels, assignees

### Linear Provider
- Signature verification: Webhook secret
- Event types: `Issue`, `Comment`, etc.
- Extracts: issue title, description, state, labels

---

## CLI Commands

The ADW SDK also provides a comprehensive CLI interface via Typer.

### Main Commands

| Command | Description |
|---------|-------------|
| `adw run` | Start a new development workflow run |
| `adw resume` | Resume a failed or interrupted run |
| `adw status` | Check run status |
| `adw list` | List recent runs |
| `adw abort` | Abort a running execution |
| `adw init` | Initialize a new project |
| `adw logs` | View run logs |
| `adw pr` | Create/manage pull requests |
| `adw webhook` | Start webhook server |
| `adw cleanup` | Clean up worktrees |

### Entry Point

Defined in `pyproject.toml`:
```toml
[project.scripts]
adw = "adw.cli:app"
```

---

## Internal APIs

### LLM Executor Protocol

The SDK defines an executor protocol for LLM interactions:

```python
class LLMResult(BaseModel):
    success: bool
    output: str
    tool_calls: list[ToolCall]
    tokens: TokenUsage
```

### Phase Result Model

```python
class PhaseResult(BaseModel):
    phase: str
    success: bool
    artifacts: list[Artifact]
    duration: float
```

---

## Configuration

API behavior is configured via `.adw/project.yaml`:

```yaml
webhook:
  port: 8000
  host: "0.0.0.0"

llm:
  path: claude
  timeout_seconds: 300
  max_retries: 3
```
