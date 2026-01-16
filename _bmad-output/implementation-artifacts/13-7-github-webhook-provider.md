# Story 13.7: GitHub Webhook Provider (Future)

Status: ready-for-dev
Linear Issue: not-configured
Epic: 13 - Webhook Infrastructure
Created: 2026-01-09

---

## Story

As a user,
I want GitHub issue events to trigger ADW runs,
so that I can automate feature development from GitHub Issues.

## Acceptance Criteria

**Given** GitHub webhook configured
**When** issue opened with label `adw`
**Then** ADW run starts with issue as feature description

**Given** GitHub issue comment containing `/adw run`
**When** comment is posted
**Then** ADW run starts for that issue

**Given** GitHub PR review comment
**When** contains `/adw fix`
**Then** ADW resumes with focus on the review feedback

## Tasks / Subtasks

### Task 1: Create GitHub Provider Package
- [x] Create `src/adw/webhook/providers/github.py`
- [x] Implement `GitHubProvider` class conforming to `WebhookProvider` Protocol
- [x] Register provider if enabled in configuration

### Task 2: Implement Signature Verification
- [x] Use `verify_github_signature()` from security module
- [x] Handle `X-Hub-Signature-256` header
- [x] Support legacy `X-Hub-Signature` (SHA-1) as fallback

### Task 3: Implement Event Parsing
- [x] Create `GitHubEvent` model for GitHub-specific payload
- [x] Map event types: issues, issue_comment, pull_request_review_comment
- [x] Extract issue data: number, title, body, labels, user
- [x] Extract PR data when applicable

### Task 4: Implement Run Trigger Logic
- [x] Check for `adw` label on issue opened events
- [x] Check for `/adw run` pattern in comment text
- [x] Check for `/adw fix` pattern in PR review comments
- [x] Respect event mapping configuration from project.yaml

### Task 5: Implement Run Parameter Extraction
- [x] Build feature_request from issue title + body
- [x] Include issue URL and number in source_info
- [x] Parse command flags from comments
- [x] Handle PR context for fix commands

### Task 6: Add GitHub-Specific Models
- [x] Add `GitHubEvent` model to `src/adw/models/webhook.py`
- [x] Add `GitHubIssue` model for issue data
- [x] Add `GitHubComment` model for comment data
- [x] Add `GitHubPullRequest` model for PR context

### Task 7: Add Configuration Support
- [x] Support GitHub configuration in project.yaml
- [x] Configuration options: enabled, secret_env, command_prefix
- [x] Default values matching GitHub conventions

### Task 8: Write Tests
- [ ] Create `tests/unit/webhook/providers/test_github.py`
- [ ] Test event parsing for each event type
- [ ] Test trigger logic for various scenarios
- [ ] Test parameter extraction
- [ ] Create test fixtures for GitHub webhook payloads

---

## Developer Context

### Technical Requirements

**From GitHub Webhook Documentation:**
- Events sent as POST with JSON bodies
- `X-Hub-Signature-256` contains HMAC-SHA256 signature
- `X-GitHub-Event` header indicates event type
- `X-GitHub-Delivery` header contains unique delivery ID

**Integration Requirements:**
- Handle issue events: opened, labeled
- Handle issue_comment events: created
- Handle pull_request_review_comment events: created
- Support command pattern `/adw <command> [flags]`

### Architecture Compliance

**File Locations:**
```
src/adw/webhook/providers/
├── __init__.py                # Modified: export GitHubProvider
├── base.py                    # Existing: Protocol definition
├── linear.py                  # Existing: Reference implementation
└── github.py                  # New: GitHubProvider implementation
```

**Model Additions:**
```
src/adw/models/
└── webhook.py                 # Add: GitHubEvent, GitHubIssue, GitHubComment, GitHubPullRequest
```

### Library & Framework Requirements

**GitHub Event Headers:**
```python
HEADER_GITHUB_EVENT = "X-GitHub-Event"
HEADER_GITHUB_DELIVERY = "X-GitHub-Delivery"
HEADER_GITHUB_SIGNATURE = "X-Hub-Signature-256"
```

**GitHub Event Types:**
```python
class GitHubEventType(str, Enum):
    ISSUES = "issues"
    ISSUE_COMMENT = "issue_comment"
    PULL_REQUEST_REVIEW_COMMENT = "pull_request_review_comment"
    PULL_REQUEST = "pull_request"
```

**GitHub Models:**
```python
class GitHubUser(BaseModel):
    """GitHub user data."""
    id: int
    login: str
    type: str  # "User", "Bot"

class GitHubIssue(BaseModel):
    """GitHub issue data."""
    id: int
    number: int
    title: str
    body: str | None
    state: str  # "open", "closed"
    labels: list[dict]  # [{name, color}]
    user: GitHubUser
    html_url: str

class GitHubComment(BaseModel):
    """GitHub comment data."""
    id: int
    body: str
    user: GitHubUser
    html_url: str
    created_at: datetime

class GitHubPullRequest(BaseModel):
    """GitHub pull request data."""
    id: int
    number: int
    title: str
    body: str | None
    head: dict  # {ref, sha}
    base: dict  # {ref, sha}
    html_url: str

class GitHubEvent(BaseModel):
    """Parsed GitHub webhook event."""
    event_type: str  # From X-GitHub-Event header
    action: str  # "opened", "created", etc.
    delivery_id: str  # From X-GitHub-Delivery
    issue: GitHubIssue | None = None
    comment: GitHubComment | None = None
    pull_request: GitHubPullRequest | None = None
    sender: GitHubUser
    repository: dict
```

**Provider Implementation:**
```python
class GitHubProvider:
    """Webhook provider for GitHub events."""

    name = "github"

    def __init__(self, config: ProviderConfig | None = None):
        self.config = config or ProviderConfig()

    def verify_signature(self, request: Request) -> bool:
        """Verify GitHub webhook signature."""
        from adw.webhook.security import verify_github_signature
        return await verify_github_signature(request)

    def parse_event(self, request: Request) -> WebhookEvent:
        """Parse GitHub webhook into WebhookEvent."""
        event_type = request.headers.get(HEADER_GITHUB_EVENT)
        delivery_id = request.headers.get(HEADER_GITHUB_DELIVERY)
        payload = await request.json()

        return WebhookEvent(
            event_type=f"{event_type}_{payload.get('action', '')}",
            provider="github",
            payload=payload,
            headers=dict(request.headers),
            timestamp=datetime.utcnow(),
            metadata={"delivery_id": delivery_id},
        )

    def should_trigger_run(self, event: WebhookEvent) -> bool:
        """Check if event should trigger ADW run."""
        # Check for adw label on issue opened
        if event.event_type == "issues_opened":
            labels = event.payload.get("issue", {}).get("labels", [])
            if any(l.get("name") == "adw" for l in labels):
                return True

        # Check for /adw command in comments
        if event.event_type in ("issue_comment_created", "pull_request_review_comment_created"):
            body = event.payload.get("comment", {}).get("body", "")
            if "/adw " in body:
                return True

        return False

    def extract_run_params(self, event: WebhookEvent) -> RunParams:
        """Extract ADW run parameters from event."""
        issue = event.payload.get("issue", {})
        comment = event.payload.get("comment", {})

        # Build feature request
        if event.event_type.startswith("issue"):
            feature_request = f"{issue.get('title', '')}\n\n{issue.get('body', '')}"
        else:
            feature_request = comment.get("body", "")

        # Parse command from comment if present
        command_args = self._parse_command(comment.get("body", ""))

        return RunParams(
            feature_request=feature_request,
            phases=command_args.get("phases"),
            source_info={
                "provider": "github",
                "repo": event.payload.get("repository", {}).get("full_name"),
                "issue_number": issue.get("number"),
                "issue_url": issue.get("html_url"),
            },
        )

    def _parse_command(self, text: str) -> dict:
        """Parse /adw command from text."""
        import re
        match = re.search(r'/adw\s+(\w+)(?:\s+(.*))?', text)
        if not match:
            return {}

        command = match.group(1)
        args = match.group(2) or ""

        result = {"command": command}

        # Parse --phase flag
        phase_match = re.search(r'--phase\s+(\w+)', args)
        if phase_match:
            result["from_phase"] = phase_match.group(1)

        return result
```

### File Structure Requirements

**New Files to Create:**
1. `src/adw/webhook/providers/github.py` - GitHub provider implementation
2. `tests/unit/webhook/providers/test_github.py` - GitHub provider tests
3. `tests/fixtures/webhook/github/` - Test fixture directory
4. `tests/fixtures/webhook/github/issue_opened.json` - Sample payload
5. `tests/fixtures/webhook/github/issue_comment_created.json` - Sample payload

**Files to Modify:**
1. `src/adw/webhook/providers/__init__.py` - Export GitHubProvider
2. `src/adw/models/webhook.py` - Add GitHub-specific models
3. `src/adw/webhook/server.py` - Auto-register GitHubProvider if enabled

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/webhook/providers/test_github.py
import pytest
from adw.webhook.providers.github import GitHubProvider
from adw.models.webhook import WebhookEvent

@pytest.fixture
def github_provider():
    return GitHubProvider()

@pytest.fixture
def issue_opened_payload():
    return {
        "action": "opened",
        "issue": {
            "number": 42,
            "title": "Add dark mode feature",
            "body": "We need dark mode for accessibility",
            "labels": [{"name": "adw"}],
            "html_url": "https://github.com/org/repo/issues/42",
        },
        "repository": {"full_name": "org/repo"},
    }

def test_parse_issue_opened_event(github_provider, issue_opened_payload):
    # Create mock request
    event = github_provider.parse_event_from_payload(
        "issues",
        issue_opened_payload,
    )
    assert event.event_type == "issues_opened"
    assert event.payload["issue"]["number"] == 42

def test_should_trigger_on_adw_label(github_provider, issue_opened_payload):
    event = WebhookEvent(
        event_type="issues_opened",
        provider="github",
        payload=issue_opened_payload,
    )
    assert github_provider.should_trigger_run(event) is True

def test_should_not_trigger_without_label(github_provider):
    payload = {
        "action": "opened",
        "issue": {"labels": []},
    }
    event = WebhookEvent(
        event_type="issues_opened",
        provider="github",
        payload=payload,
    )
    assert github_provider.should_trigger_run(event) is False

def test_parse_adw_command_from_comment():
    body = "Let's implement this. /adw run --phase build"
    result = github_provider._parse_command(body)
    assert result["command"] == "run"
    assert result["from_phase"] == "build"

def test_parse_adw_fix_command():
    body = "This needs fixing. /adw fix"
    result = github_provider._parse_command(body)
    assert result["command"] == "fix"
```

---

## Previous Story Intelligence

**From Story 13.3 (Linear Provider):**
- Similar implementation structure
- Same WebhookProvider Protocol
- Shared security utilities for signature verification

**Key Differences from Linear:**
- Different header names for event metadata
- Different command syntax (`/adw` vs `@adw`)
- PR review comments are unique to GitHub
- Label name is `adw` (no colon)

---

## Git Intelligence

**Recent Patterns:**
- Provider implementations follow consistent structure
- Models are comprehensive with all fields
- Test fixtures use real-world payload structure

**Recommended Commit Pattern:**
```
feat(webhook): implement GitHub webhook provider

- Add GitHubProvider implementing WebhookProvider Protocol
- Support issue, issue_comment, and PR review events
- Implement /adw command parsing
- Handle adw label trigger for issues
- Support /adw fix for PR review comments
- Include comprehensive test suite with fixtures
```

---

## Latest Technical Information

**GitHub Webhook Events (2025):**
- Event types in `X-GitHub-Event` header
- Action field indicates specific trigger
- Rich payload structure with nested objects

**GitHub Command Patterns:**
- Slash commands: `/command [args]`
- Common in CI/CD bots (dependabot, codecov)
- Case-insensitive matching recommended

**GitHub API Identifiers:**
- Issues use numbers (not UUIDs)
- URLs follow pattern: `https://github.com/{owner}/{repo}/issues/{number}`
- PR review comments include position/line info

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

1. **Event Parsing:** Must handle all relevant GitHub event types
2. **Command Parsing:** Must parse `/adw` commands correctly
3. **PR Context:** Must handle PR review comments properly
4. **Signature Verification:** Must use security module

### Common Pitfalls to Avoid

- Don't confuse issue_comment vs pull_request_review_comment
- Don't assume body field is always present
- Don't forget to check sender type (avoid bot loops)
- Don't use case-sensitive command matching

### GitHub-Specific Considerations

- Issue and PR share some events (labeled, commented)
- PR review comments have different structure than issue comments
- GitHub Apps vs OAuth Apps affect webhook payloads
- Rate limiting may affect high-volume repositories

### Future Enhancements

- Support for pull_request events (opened, synchronize)
- Support for check_suite events (CI integration)
- Support for release events (automated deployments)
- GitHub Actions workflow dispatch integration

### References

- [Source: _bmad-output/epics/epic-13-webhook-infrastructure.md#Story-13.7]
- [Source: GitHub Webhook Events Documentation]
- [Source: GitHub REST API Reference]

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
- **Blocks:** None
- **Can Parallel With:** Story 13.3 (Linear Provider), Story 13.6 (Signature Verification)

### Dependency Rationale
- Story 13.2 provides the WebhookProvider Protocol this implements
- Can be developed in parallel with Linear provider
- Shares security utilities from Story 13.6
