# Story 14.9: Webhook Server Setup (Optional, Full)

Status: done
Linear Issue: pending
Epic: 14 - Interactive Init Wizard
Created: 2026-01-18

---

## Story

As a user in the wizard,
I want to configure webhook integrations,
so that external events can trigger ADW runs.

## Acceptance Criteria

- [ ] Prompts "Set up webhook server? [y/N]"
- [ ] If No, webhooks section uses defaults (disabled)
- [ ] If Yes:
  - [ ] "Webhook server port: 8000 [Enter or override]"
  - [ ] "Webhook server host: 0.0.0.0 [Enter or override]"
  - [ ] "Which providers to configure?" [multi-select: Linear, GitHub]
  - [ ] **For Linear** (if selected):
    - [ ] "Enable Linear webhooks? [Y/n]"
    - [ ] "Secret env variable: LINEAR_WEBHOOK_SECRET [Enter or override]"
    - [ ] "Command prefix: /adw [Enter or override]"
    - [ ] "Trigger label: adw [Enter or override]"
    - [ ] "Configure event mappings? [Y/n]"
    - [ ] If Yes:
      - [ ] "On issue created - trigger run? [Y/n]"
      - [ ] "  Require label? [none or label name]"
      - [ ] "On issue updated - trigger run? [y/N]"
      - [ ] "  Require label? [none or label name]"
      - [ ] "On comment created - trigger run? [Y/n]"
      - [ ] "  Require mention: @adw [Enter or override]"
      - [ ] "  Parse command from comment? [Y/n]"
  - [ ] **For GitHub** (if selected):
    - [ ] Same structure as Linear
    - [ ] "Secret env variable: GITHUB_WEBHOOK_SECRET [Enter or override]"
- [ ] All values stored in wizard state for final generation

## Tasks / Subtasks

### Task 1: Create Webhook Step Module
- [x] Create `src/adw/cli/wizard/webhooks.py`
- [x] Define `run_webhooks_step(state: WizardState) -> WizardState`
- [x] Import and register in flow controller

### Task 2: Implement Server Configuration Prompts
- [x] Prompt for webhook server enable/disable
- [x] If enabled:
  - Prompt for port (default 8000, validate 1-65535)
  - Prompt for host (default 0.0.0.0)

### Task 3: Implement Provider Selection
- [x] Create multi-select for providers (Linear, GitHub)
- [x] Return list of selected providers
- [x] Handle no providers selected (back to disabled)

### Task 4: Implement Linear Provider Configuration
- [x] Prompt for Linear enable
- [x] Prompt for secret env variable name
- [x] Prompt for command prefix
- [x] Prompt for trigger label
- [x] Implement event mapping configuration loop

### Task 5: Implement GitHub Provider Configuration
- [x] Same structure as Linear
- [x] Different default secret variable (GITHUB_WEBHOOK_SECRET)
- [x] May have different event types in future

### Task 6: Implement Event Mapping Configuration
- [x] For each event type (issue_created, issue_updated, comment_created):
  - Prompt for enable/disable
  - Conditional: label requirement
  - For comments: mention prefix, parse command option

### Task 7: Store Results in Wizard State
- [x] Update WizardState with full webhook config
- [x] Mark webhooks step as completed

### Task 8: Write Unit Tests
- [x] Test server config prompts
- [x] Test provider selection
- [x] Test Linear provider config flow
- [x] Test GitHub provider config flow
- [x] Test event mapping configuration
- [x] Test state update after step completion

---

## Dependencies

### Depends On
- 14.1 (Wizard Entry Point & Flow Control) - provides WizardState and flow controller
- 14.2 (Basics Configuration Step) - runs before this in wizard flow

### Blocks
- 14.10 (Summary) - displays webhook configuration

### Parallel With
- 14.7 (LLM Retry Configuration) - no dependencies
- 14.8 (Security Configuration) - no dependencies

---

## Developer Context

### Technical Requirements

**Default Webhook Configuration:**
```python
DEFAULT_WEBHOOK_CONFIG = {
    "enabled": False,
    "port": 8000,
    "host": "0.0.0.0",
    "providers": {
        "linear": {
            "enabled": False,
            "secret_env": "LINEAR_WEBHOOK_SECRET",
            "command_prefix": "/adw",
            "trigger_label": "adw",
            "event_mappings": {
                "issue_created": {
                    "enabled": True,
                    "require_label": None,
                },
                "issue_updated": {
                    "enabled": False,
                    "require_label": None,
                },
                "comment_created": {
                    "enabled": True,
                    "require_mention": "@adw",
                    "parse_command": True,
                },
            },
        },
        "github": {
            "enabled": False,
            "secret_env": "GITHUB_WEBHOOK_SECRET",
            # Similar structure
        },
    },
}
```

**Event Mapping Data Model:**
```python
@dataclass
class EventMapping:
    enabled: bool
    require_label: str | None = None
    require_mention: str | None = None  # For comments
    parse_command: bool = False  # For comments
```

### Architecture Compliance

**Layer Boundaries:**
- Wizard step in `src/adw/cli/wizard/webhooks.py`
- Webhook config models in `src/adw/models/webhook.py`
- Ensure compatibility with existing webhook infrastructure

**Existing Webhook Implementation:**
- Check `src/adw/webhook/` for server implementation
- Check `src/adw/webhook/providers/` for Linear, GitHub
- Check `src/adw/models/webhook.py` for config models

### Library & Framework Requirements

| Library | Usage | Import Pattern |
|---------|-------|----------------|
| Rich | Prompts | `from rich.prompt import Prompt, Confirm` |

**Provider Section Header:**
```python
from rich.console import Console
from rich.rule import Rule

console = Console()

console.print(Rule(f"[bold blue]Linear[/] Provider", style="blue"))
```

### File Structure Requirements

**New Files to Create:**
```
src/adw/cli/wizard/
└── webhooks.py           # Webhook configuration step
```

**Files to Modify:**
```
src/adw/cli/wizard/flow.py    # Register webhooks step
src/adw/models/wizard.py      # Add webhook fields to WizardState
```

### Testing Requirements

**Test Files:**
```
tests/unit/cli/wizard/
└── test_webhooks.py      # Webhook step tests
```

**Test Cases:**
```python
# Server config
def test_webhook_disabled(mocker):
    # Mock No response
    # Verify webhooks disabled in state

def test_webhook_server_config(mocker):
    # Mock custom port and host
    # Verify values in state

# Provider selection
def test_no_providers_selected(mocker):
    # Mock empty provider selection
    # Verify webhooks effectively disabled

def test_linear_provider_selected(mocker):
    # Mock Linear selection
    # Verify Linear config prompts shown

# Event mappings
def test_event_mapping_defaults(mocker):
    # Skip custom mapping
    # Verify default events

def test_event_mapping_custom(mocker):
    # Configure custom mappings
    # Verify custom events in state
```

**Mock Requirements:**
- Mock Rich prompts for all variations
- No external service calls to mock

---

## Previous Story Intelligence

**From Stories 14.1-14.8:**
- WizardState model structure
- Provider section patterns (similar to task manager)
- Multi-select patterns

**Expected State Structure:**
```python
# WizardState additions
webhook_enabled: bool = False
webhook_port: int = 8000
webhook_host: str = "0.0.0.0"
webhook_providers: dict[str, ProviderWizardConfig] = {}

@dataclass
class ProviderWizardConfig:
    enabled: bool = False
    secret_env: str = ""
    command_prefix: str = "/adw"
    trigger_label: str = "adw"
    event_mappings: dict[str, EventMapping] = field(default_factory=dict)
```

---

## Git Intelligence

**Existing Webhook Config:**
- Check `src/adw/webhook/server.py` for server config
- Check `src/adw/webhook/providers/linear.py` for Linear impl
- Check `src/adw/webhook/providers/github.py` for GitHub impl

**Search Commands:**
```bash
grep -r "WebhookConfig" src/
grep -r "LINEAR_WEBHOOK_SECRET" src/
grep -r "event_mapping" src/
```

---

## Latest Technical Information

**ADW Webhook Infrastructure:**
- FastAPI-based webhook server
- Provider pattern for extensibility
- Signature verification per provider
- Event-to-run mapping configurable

**Linear Webhook Events:**
| Event | Description |
|-------|-------------|
| `IssueCreate` | New issue created |
| `IssueUpdate` | Issue fields changed |
| `Comment` | Comment added to issue |

**GitHub Webhook Events:**
| Event | Description |
|-------|-------------|
| `issues` | Issue opened/edited/closed |
| `issue_comment` | Comment on issue |
| `pull_request` | PR events |

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns and rules from project context:
- Webhook server in `src/adw/webhook/`
- Provider implementations in `src/adw/webhook/providers/`
- Config models in `src/adw/models/`

---

## Dev Notes

- This is the most complex optional step
- Provider configuration is repetitive but necessary for full customization
- Event mappings allow fine-grained control over triggers
- Consider showing a summary of configured events before finishing

### Prompt Flow Diagram
```
Set up webhooks? [y/N]
├── No → webhooks disabled, DONE
└── Yes
    ├── Port: 8000
    ├── Host: 0.0.0.0
    └── Which providers? [multi-select]
        ├── Linear (if selected)
        │   ├── Enable Linear? [Y/n]
        │   ├── Secret env: LINEAR_WEBHOOK_SECRET
        │   ├── Command prefix: /adw
        │   ├── Trigger label: adw
        │   └── Configure events? [Y/n]
        │       └── For each event type...
        └── GitHub (if selected)
            └── Same structure...
```

### References

- [Source: _bmad-output/epics/epic-14-interactive-init-wizard.md#Story-14.9]
- [Source: _bmad-output/architecture-summary.md#Webhook-Trigger-Flow]
- [Source: src/adw/webhook/ - webhook implementation]

---

## Dev Agent Record

### Context Reference

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Implemented comprehensive webhook configuration wizard step
- Created `WebhooksStepHandler` and `run_webhooks_step` following existing wizard patterns
- Implemented server configuration (port with 1-65535 validation, host)
- Implemented multi-select provider selection (Linear, GitHub)
- Implemented provider configuration with secret env, command prefix, trigger label
- Implemented event mapping configuration for issue_created, issue_updated, comment_created
- Added comment-specific options (require_mention, parse_command)
- Registered handler in init.py flow
- Wrote 33 comprehensive unit tests covering all functionality
- All 259 wizard tests pass

### File List

- src/adw/cli/wizard/webhooks.py (new)
- src/adw/cli/wizard/__init__.py (modified - added exports)
- src/adw/cli/init.py (modified - registered handler)
- tests/unit/cli/wizard/test_webhooks.py (new)
- _bmad-output/implementation-artifacts/14-9-webhook-server-setup.md (modified)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified)

