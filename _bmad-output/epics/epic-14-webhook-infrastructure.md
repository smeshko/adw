# Epic 14: Webhook Infrastructure

**Goal:** Enable ADW runs to be triggered by external events via webhooks, starting with Linear and expanding to GitHub.

**Priority:** Post-MVP
**Dependencies:** Epic 11 (Task Manager Integration), Epic 6 (Run Management)

---

## Story 14.1: Generic Webhook Server Framework

As a developer,
I want a webhook server that can receive events from multiple providers,
So that ADW can be triggered automatically.

**Acceptance Criteria:**

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

---

## Story 14.2: Webhook Provider Protocol

As a developer,
I want a pluggable provider interface,
So that new webhook sources can be added easily.

**Acceptance Criteria:**

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
**Then** 404 returned with available providers

**Given** new provider implementation
**When** registered
**Then** it's automatically routed at `/webhook/{provider_name}`

---

## Story 14.3: Linear Webhook Provider

As a user,
I want Linear issue events to trigger ADW runs,
So that I can automate feature development from Linear.

**Acceptance Criteria:**

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

---

## Story 14.4: Event-to-Workflow Mapping

As a developer,
I want to configure which events trigger which workflows,
So that I have fine-grained control over automation.

**Acceptance Criteria:**

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

---

## Story 14.5: Bot Loop Prevention

As a developer,
I want ADW to not trigger itself,
So that webhooks don't cause infinite loops.

**Acceptance Criteria:**

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

---

## Story 14.6: Webhook Signature Verification

As a developer,
I want webhook signatures verified,
So that only legitimate events trigger runs.

**Acceptance Criteria:**

**Given** Linear webhook
**When** received
**Then** `X-Linear-Signature` header is verified against secret

**Given** GitHub webhook
**When** received
**Then** `X-Hub-Signature-256` header is verified against secret

**Given** signature verification fails
**When** invalid signature
**Then** 401 returned, event logged as rejected

**Given** secret not configured
**When** webhook received
**Then** verification skipped with warning log

---

## Story 14.7: GitHub Webhook Provider (Future)

As a user,
I want GitHub issue events to trigger ADW runs,
So that I can automate feature development from GitHub Issues.

**Acceptance Criteria:**

**Given** GitHub webhook configured
**When** issue opened with label `adw`
**Then** ADW run starts with issue as feature description

**Given** GitHub issue comment containing `/adw run`
**When** comment is posted
**Then** ADW run starts for that issue

**Given** GitHub PR review comment
**When** contains `/adw fix`
**Then** ADW resumes with focus on the review feedback

---

## Configuration

```yaml
# .adw/project.yaml
webhook:
  enabled: true
  port: 8000
  host: "0.0.0.0"

  providers:
    linear:
      enabled: true
      secret_env: LINEAR_WEBHOOK_SECRET

    github:
      enabled: false
      secret_env: GITHUB_WEBHOOK_SECRET

  mappings:
    linear:
      issue_created:
        trigger: true
        require_label: "adw:auto"
      comment_created:
        trigger: true
        require_mention: "@adw"
        parse_command: true

    github:
      issues_opened:
        trigger: true
        require_label: "adw"
      issue_comment_created:
        trigger: true
        require_prefix: "/adw"

  # Bot loop prevention
  bot_markers:
    comment: "<!-- [ADW] -->"
    author_prefix: "[ADW]"

  # Async run handling
  run_async: true
  max_concurrent_webhook_runs: 5
```

---

## Architecture

```
                    ┌─────────────────────┐
                    │   Webhook Server    │
                    │   (FastAPI)         │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │ Linear Provider │ │ GitHub Provider │ │ Future Provider │
    └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
             │                   │                   │
             ▼                   ▼                   ▼
    ┌─────────────────────────────────────────────────────────┐
    │                    Event Router                          │
    │  - Verify signature                                      │
    │  - Check mapping rules                                   │
    │  - Bot loop prevention                                   │
    └────────────────────────────┬────────────────────────────┘
                                 │
                                 ▼
    ┌─────────────────────────────────────────────────────────┐
    │                    Run Trigger                           │
    │  - Extract run parameters                                │
    │  - Start async ADW run                                   │
    │  - Post acknowledgment comment                           │
    └─────────────────────────────────────────────────────────┘
```

---

## Dependency Flowchart

```
     Story 14.1 (Server Framework)
              │
              ▼
     Story 14.2 (Provider Protocol)
              │
     ┌────────┼────────┐
     ▼        ▼        ▼
  14.3     14.6     14.7
 Linear   Verify   GitHub
     │        │   (future)
     └────────┼────────┘
              ▼
     Story 14.4 (Event Mapping)
              │
              ▼
     Story 14.5 (Loop Prevention)
```

---
