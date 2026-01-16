"""Tests for GitHubProvider webhook implementation."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from adw.models.webhook import ProviderConfig, WebhookConfig, WebhookEvent
from adw.webhook.providers.github import GitHubProvider

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def github_provider() -> GitHubProvider:
    """Create a GitHubProvider with no configuration."""
    return GitHubProvider()


@pytest.fixture
def github_provider_with_secret() -> GitHubProvider:
    """Create a GitHubProvider with a configured secret."""
    config = WebhookConfig(
        providers={
            "github": ProviderConfig(
                enabled=True,
                secret_env="GITHUB_WEBHOOK_SECRET",
            )
        }
    )
    # Mock the secret retrieval
    provider = GitHubProvider(config)
    provider._secret = "test-secret"
    return provider


@pytest.fixture
def github_provider_custom_config() -> GitHubProvider:
    """Create a GitHubProvider with custom configuration."""
    config = WebhookConfig(
        providers={
            "github": ProviderConfig(
                enabled=True,
                command_prefix="/feature",
                trigger_label="automation",
            )
        }
    )
    return GitHubProvider(config)


@pytest.fixture
def issue_opened_payload() -> dict:
    """Sample GitHub issue opened webhook payload."""
    return {
        "action": "opened",
        "issue": {
            "id": 123456,
            "number": 42,
            "title": "Add dark mode feature",
            "body": "We need dark mode for accessibility",
            "state": "open",
            "labels": [{"name": "adw", "color": "0075ca"}],
            "user": {"id": 1, "login": "testuser", "type": "User"},
            "html_url": "https://github.com/org/repo/issues/42",
        },
        "repository": {
            "id": 789,
            "name": "repo",
            "full_name": "org/repo",
            "html_url": "https://github.com/org/repo",
        },
        "sender": {"id": 1, "login": "testuser", "type": "User"},
    }


@pytest.fixture
def issue_comment_payload() -> dict:
    """Sample GitHub issue comment webhook payload."""
    return {
        "action": "created",
        "issue": {
            "id": 123456,
            "number": 42,
            "title": "Feature request",
            "body": "Original description",
            "state": "open",
            "labels": [],
            "user": {"id": 1, "login": "testuser", "type": "User"},
            "html_url": "https://github.com/org/repo/issues/42",
        },
        "comment": {
            "id": 999,
            "body": "Let's do this! /adw run --phase build",
            "user": {"id": 2, "login": "reviewer", "type": "User"},
            "html_url": "https://github.com/org/repo/issues/42#issuecomment-999",
            "created_at": "2026-01-16T10:00:00Z",
        },
        "repository": {
            "id": 789,
            "name": "repo",
            "full_name": "org/repo",
            "html_url": "https://github.com/org/repo",
        },
        "sender": {"id": 2, "login": "reviewer", "type": "User"},
    }


@pytest.fixture
def pr_review_comment_payload() -> dict:
    """Sample GitHub PR review comment webhook payload."""
    return {
        "action": "created",
        "pull_request": {
            "id": 456,
            "number": 15,
            "title": "Fix authentication",
            "body": "This fixes the auth issue",
            "head": {"ref": "fix-auth", "sha": "abc123"},
            "base": {"ref": "main", "sha": "def456"},
            "html_url": "https://github.com/org/repo/pull/15",
        },
        "comment": {
            "id": 888,
            "body": "/adw fix",
            "user": {"id": 3, "login": "codereviewer", "type": "User"},
            "html_url": "https://github.com/org/repo/pull/15#discussion_r888",
            "created_at": "2026-01-16T11:00:00Z",
        },
        "repository": {
            "id": 789,
            "name": "repo",
            "full_name": "org/repo",
            "html_url": "https://github.com/org/repo",
        },
        "sender": {"id": 3, "login": "codereviewer", "type": "User"},
    }


def _create_mock_request(
    headers: dict | None = None,
    body: bytes | None = None,
) -> MagicMock:
    """Create a mock FastAPI Request object."""
    request = MagicMock()
    request.headers = headers or {}
    return request


# =============================================================================
# Provider Protocol Tests
# =============================================================================


class TestGitHubProviderProtocol:
    """Test that GitHubProvider conforms to WebhookProvider protocol."""

    def test_provider_has_name_property(self, github_provider: GitHubProvider) -> None:
        """Provider has name property returning 'github'."""
        assert github_provider.name == "github"

    def test_provider_has_verify_signature_method(
        self, github_provider: GitHubProvider
    ) -> None:
        """Provider has verify_signature method."""
        assert hasattr(github_provider, "verify_signature")
        assert callable(github_provider.verify_signature)

    def test_provider_has_parse_event_method(
        self, github_provider: GitHubProvider
    ) -> None:
        """Provider has parse_event method."""
        assert hasattr(github_provider, "parse_event")
        assert callable(github_provider.parse_event)

    def test_provider_has_should_trigger_run_method(
        self, github_provider: GitHubProvider
    ) -> None:
        """Provider has should_trigger_run method."""
        assert hasattr(github_provider, "should_trigger_run")
        assert callable(github_provider.should_trigger_run)

    def test_provider_has_extract_run_params_method(
        self, github_provider: GitHubProvider
    ) -> None:
        """Provider has extract_run_params method."""
        assert hasattr(github_provider, "extract_run_params")
        assert callable(github_provider.extract_run_params)


# =============================================================================
# Signature Verification Tests
# =============================================================================


class TestSignatureVerification:
    """Test signature verification for GitHub webhooks."""

    def test_verify_returns_false_when_no_secret_configured(
        self, github_provider: GitHubProvider
    ) -> None:
        """Without configured secret, verification fails closed (returns False)."""
        request = _create_mock_request()
        assert github_provider.verify_signature(request, b"test body") is False

    def test_verify_sha256_signature_valid(
        self, github_provider_with_secret: GitHubProvider
    ) -> None:
        """Valid SHA-256 signature returns True."""
        import hashlib
        import hmac

        body = b'{"test": "data"}'
        secret = "test-secret"
        signature = hmac.new(
            secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()

        request = _create_mock_request(
            headers={"x-hub-signature-256": f"sha256={signature}"}
        )
        assert github_provider_with_secret.verify_signature(request, body) is True

    def test_verify_sha256_signature_invalid(
        self, github_provider_with_secret: GitHubProvider
    ) -> None:
        """Invalid SHA-256 signature returns False."""
        request = _create_mock_request(
            headers={"x-hub-signature-256": "sha256=invalidsignature"}
        )
        assert (
            github_provider_with_secret.verify_signature(request, b"test body")
            is False
        )

    def test_verify_sha1_fallback_valid(
        self, github_provider_with_secret: GitHubProvider
    ) -> None:
        """Valid SHA-1 fallback signature returns True."""
        import hashlib
        import hmac

        body = b'{"test": "data"}'
        secret = "test-secret"
        signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha1).hexdigest()

        request = _create_mock_request(headers={"x-hub-signature": f"sha1={signature}"})
        assert github_provider_with_secret.verify_signature(request, body) is True

    def test_verify_returns_false_when_no_signature_header(
        self, github_provider_with_secret: GitHubProvider
    ) -> None:
        """When secret configured but no signature header, returns False."""
        request = _create_mock_request(headers={})
        assert (
            github_provider_with_secret.verify_signature(request, b"test") is False
        )


# =============================================================================
# Event Parsing Tests
# =============================================================================


class TestEventParsing:
    """Test event parsing for different GitHub webhook event types."""

    def test_parse_issue_opened_event(
        self,
        github_provider: GitHubProvider,
        issue_opened_payload: dict,
    ) -> None:
        """Parse issue opened webhook into WebhookEvent."""
        import json

        request = _create_mock_request(
            headers={
                "x-github-event": "issues",
                "x-github-delivery": "delivery-123",
            }
        )
        body = json.dumps(issue_opened_payload).encode("utf-8")

        event = github_provider.parse_event(request, body)

        assert event.event_type == "issues_opened"
        assert event.provider == "github"
        assert event.payload["issue"]["number"] == 42
        assert event.headers["x-github-event"] == "issues"
        assert event.headers["x-github-delivery"] == "delivery-123"

    def test_parse_issue_comment_event(
        self,
        github_provider: GitHubProvider,
        issue_comment_payload: dict,
    ) -> None:
        """Parse issue comment webhook into WebhookEvent."""
        import json

        request = _create_mock_request(
            headers={
                "x-github-event": "issue_comment",
                "x-github-delivery": "delivery-456",
            }
        )
        body = json.dumps(issue_comment_payload).encode("utf-8")

        event = github_provider.parse_event(request, body)

        assert event.event_type == "issue_comment_created"
        assert event.provider == "github"
        assert "/adw run" in event.payload["comment"]["body"]

    def test_parse_pr_review_comment_event(
        self,
        github_provider: GitHubProvider,
        pr_review_comment_payload: dict,
    ) -> None:
        """Parse PR review comment webhook into WebhookEvent."""
        import json

        request = _create_mock_request(
            headers={
                "x-github-event": "pull_request_review_comment",
                "x-github-delivery": "delivery-789",
            }
        )
        body = json.dumps(pr_review_comment_payload).encode("utf-8")

        event = github_provider.parse_event(request, body)

        assert event.event_type == "pull_request_review_comment_created"
        assert event.provider == "github"

    def test_parse_event_missing_github_event_header_raises(
        self, github_provider: GitHubProvider
    ) -> None:
        """Missing X-GitHub-Event header raises ValueError."""
        request = _create_mock_request(headers={})
        with pytest.raises(ValueError, match="Missing X-GitHub-Event header"):
            github_provider.parse_event(request, b'{"action": "opened"}')

    def test_parse_event_invalid_json_raises(
        self, github_provider: GitHubProvider
    ) -> None:
        """Invalid JSON body raises ValueError."""
        request = _create_mock_request(headers={"x-github-event": "issues"})
        with pytest.raises(ValueError, match="Invalid JSON body"):
            github_provider.parse_event(request, b"not json")


# =============================================================================
# Trigger Logic Tests
# =============================================================================


class TestTriggerLogic:
    """Test run trigger logic for various scenarios."""

    def test_trigger_on_issue_opened_with_adw_label(
        self, github_provider: GitHubProvider
    ) -> None:
        """Issue opened with 'adw' label triggers run."""
        event = WebhookEvent(
            event_type="issues_opened",
            provider="github",
            payload={
                "action": "opened",
                "issue": {
                    "labels": [{"name": "adw"}],
                },
            },
        )
        assert github_provider.should_trigger_run(event) is True

    def test_no_trigger_on_issue_opened_without_label(
        self, github_provider: GitHubProvider
    ) -> None:
        """Issue opened without 'adw' label does not trigger run."""
        event = WebhookEvent(
            event_type="issues_opened",
            provider="github",
            payload={
                "action": "opened",
                "issue": {
                    "labels": [{"name": "bug"}, {"name": "enhancement"}],
                },
            },
        )
        assert github_provider.should_trigger_run(event) is False

    def test_trigger_on_issue_labeled_with_adw(
        self, github_provider: GitHubProvider
    ) -> None:
        """Issue labeled with 'adw' triggers run."""
        event = WebhookEvent(
            event_type="issues_labeled",
            provider="github",
            payload={
                "action": "labeled",
                "issue": {
                    "labels": [{"name": "adw"}],
                },
            },
        )
        assert github_provider.should_trigger_run(event) is True

    def test_trigger_on_comment_with_adw_run_command(
        self, github_provider: GitHubProvider
    ) -> None:
        """Comment with '/adw run' command triggers run."""
        event = WebhookEvent(
            event_type="issue_comment_created",
            provider="github",
            payload={
                "action": "created",
                "comment": {
                    "body": "Let's implement this. /adw run",
                },
            },
        )
        assert github_provider.should_trigger_run(event) is True

    def test_trigger_on_comment_with_adw_fix_command(
        self, github_provider: GitHubProvider
    ) -> None:
        """Comment with '/adw fix' command triggers run."""
        event = WebhookEvent(
            event_type="issue_comment_created",
            provider="github",
            payload={
                "action": "created",
                "comment": {
                    "body": "/adw fix this issue",
                },
            },
        )
        assert github_provider.should_trigger_run(event) is True

    def test_no_trigger_on_comment_without_adw_command(
        self, github_provider: GitHubProvider
    ) -> None:
        """Comment without '/adw' command does not trigger run."""
        event = WebhookEvent(
            event_type="issue_comment_created",
            provider="github",
            payload={
                "action": "created",
                "comment": {
                    "body": "This looks good, let's proceed.",
                },
            },
        )
        assert github_provider.should_trigger_run(event) is False

    def test_trigger_on_pr_review_comment_with_adw_command(
        self, github_provider: GitHubProvider
    ) -> None:
        """PR review comment with '/adw fix' triggers run."""
        event = WebhookEvent(
            event_type="pull_request_review_comment_created",
            provider="github",
            payload={
                "action": "created",
                "comment": {
                    "body": "/adw fix this code issue",
                },
            },
        )
        assert github_provider.should_trigger_run(event) is True

    def test_no_trigger_on_unknown_event_type(
        self, github_provider: GitHubProvider
    ) -> None:
        """Unknown event types do not trigger run."""
        event = WebhookEvent(
            event_type="push",
            provider="github",
            payload={},
        )
        assert github_provider.should_trigger_run(event) is False

    def test_trigger_with_custom_label_config(
        self, github_provider_custom_config: GitHubProvider
    ) -> None:
        """Custom trigger label from config is respected."""
        event = WebhookEvent(
            event_type="issues_opened",
            provider="github",
            payload={
                "action": "opened",
                "issue": {
                    "labels": [{"name": "automation"}],
                },
            },
        )
        assert github_provider_custom_config.should_trigger_run(event) is True

        # Default label should not trigger
        event_adw = WebhookEvent(
            event_type="issues_opened",
            provider="github",
            payload={
                "action": "opened",
                "issue": {
                    "labels": [{"name": "adw"}],
                },
            },
        )
        assert github_provider_custom_config.should_trigger_run(event_adw) is False

    def test_trigger_with_custom_command_prefix(
        self, github_provider_custom_config: GitHubProvider
    ) -> None:
        """Custom command prefix from config is respected."""
        event = WebhookEvent(
            event_type="issue_comment_created",
            provider="github",
            payload={
                "action": "created",
                "comment": {
                    "body": "/feature run this",
                },
            },
        )
        assert github_provider_custom_config.should_trigger_run(event) is True

        # Default command should not trigger
        event_adw = WebhookEvent(
            event_type="issue_comment_created",
            provider="github",
            payload={
                "action": "created",
                "comment": {
                    "body": "/adw run this",
                },
            },
        )
        assert github_provider_custom_config.should_trigger_run(event_adw) is False


# =============================================================================
# Parameter Extraction Tests
# =============================================================================


class TestParameterExtraction:
    """Test run parameter extraction from events."""

    def test_extract_params_from_issue_opened(
        self, github_provider: GitHubProvider
    ) -> None:
        """Extract run parameters from issue opened event."""
        event = WebhookEvent(
            event_type="issues_opened",
            provider="github",
            payload={
                "action": "opened",
                "issue": {
                    "number": 42,
                    "title": "Add dark mode feature",
                    "body": "We need dark mode for accessibility.",
                    "html_url": "https://github.com/org/repo/issues/42",
                },
                "repository": {
                    "full_name": "org/repo",
                },
            },
            headers={"x-github-delivery": "delivery-abc"},
        )

        params = github_provider.extract_run_params(event)

        assert "Add dark mode feature" in params.feature_request
        assert "We need dark mode" in params.feature_request
        assert params.source_info["provider"] == "github"
        assert params.source_info["repo"] == "org/repo"
        assert params.source_info["issue_number"] == 42
        assert params.source_info["issue_url"] == "https://github.com/org/repo/issues/42"
        assert params.metadata["delivery_id"] == "delivery-abc"
        assert params.phases is None

    def test_extract_params_from_comment_with_phase_flag(
        self, github_provider: GitHubProvider
    ) -> None:
        """Extract run parameters from comment with --phase flag.

        Issue comments should use issue title+body as feature_request
        (the run starts 'for that issue'), not the comment text.
        """
        event = WebhookEvent(
            event_type="issue_comment_created",
            provider="github",
            payload={
                "action": "created",
                "issue": {
                    "number": 42,
                    "title": "Add payment processing",
                    "body": "We need to integrate Stripe for payments.",
                    "html_url": "https://github.com/org/repo/issues/42",
                },
                "comment": {
                    "body": "Let's run this /adw run --phase build",
                    "html_url": "https://github.com/org/repo/issues/42#comment-123",
                },
                "repository": {
                    "full_name": "org/repo",
                },
            },
            headers={"x-github-delivery": "delivery-def"},
        )

        params = github_provider.extract_run_params(event)

        # Feature request should be from issue, not comment
        assert "Add payment processing" in params.feature_request
        assert "Stripe" in params.feature_request
        # Phase flag should still be parsed from comment
        assert params.phases == ["build"]
        assert params.metadata["command"] == "run"
        assert (
            params.source_info["comment_url"]
            == "https://github.com/org/repo/issues/42#comment-123"
        )

    def test_extract_params_from_fix_command(
        self, github_provider: GitHubProvider
    ) -> None:
        """Extract run parameters from /adw fix command in PR review comment."""
        event = WebhookEvent(
            event_type="pull_request_review_comment_created",
            provider="github",
            payload={
                "action": "created",
                "pull_request": {
                    "number": 15,
                    "html_url": "https://github.com/org/repo/pull/15",
                },
                "comment": {
                    "body": "/adw fix",
                    "html_url": "https://github.com/org/repo/pull/15#comment-456",
                },
                "repository": {
                    "full_name": "org/repo",
                },
            },
            headers={"x-github-delivery": "delivery-ghi"},
        )

        params = github_provider.extract_run_params(event)

        assert params.feature_request == "/adw fix"
        assert params.metadata["command"] == "fix"
        # PR context should be extracted for review comments
        assert params.source_info["pr_number"] == 15
        assert params.source_info["pr_url"] == "https://github.com/org/repo/pull/15"
        assert (
            params.source_info["comment_url"]
            == "https://github.com/org/repo/pull/15#comment-456"
        )

    def test_extract_params_handles_null_issue_body(
        self, github_provider: GitHubProvider
    ) -> None:
        """Handle null issue body gracefully."""
        event = WebhookEvent(
            event_type="issues_opened",
            provider="github",
            payload={
                "action": "opened",
                "issue": {
                    "number": 42,
                    "title": "Quick fix",
                    "body": None,
                    "html_url": "https://github.com/org/repo/issues/42",
                },
                "repository": {
                    "full_name": "org/repo",
                },
            },
            headers={},
        )

        params = github_provider.extract_run_params(event)

        assert params.feature_request == "Quick fix"


# =============================================================================
# Command Parsing Tests
# =============================================================================


class TestCommandParsing:
    """Test /adw command parsing from text."""

    def test_parse_run_command(self, github_provider: GitHubProvider) -> None:
        """Parse /adw run command."""
        result = github_provider._parse_command("/adw run")
        assert result["command"] == "run"

    def test_parse_fix_command(self, github_provider: GitHubProvider) -> None:
        """Parse /adw fix command."""
        result = github_provider._parse_command("/adw fix")
        assert result["command"] == "fix"

    def test_parse_command_with_phase_flag(
        self, github_provider: GitHubProvider
    ) -> None:
        """Parse command with --phase flag."""
        result = github_provider._parse_command("/adw run --phase build")
        assert result["command"] == "run"
        assert result["from_phase"] == "build"

    def test_parse_command_case_insensitive(
        self, github_provider: GitHubProvider
    ) -> None:
        """Command parsing is case-insensitive."""
        result = github_provider._parse_command("/ADW RUN --PHASE BUILD")
        assert result["command"] == "run"
        assert result["from_phase"] == "build"

    def test_parse_command_in_text(self, github_provider: GitHubProvider) -> None:
        """Parse command embedded in text."""
        result = github_provider._parse_command(
            "Great idea! Let's do it. /adw run --phase validate"
        )
        assert result["command"] == "run"
        assert result["from_phase"] == "validate"

    def test_parse_no_command_returns_empty(
        self, github_provider: GitHubProvider
    ) -> None:
        """Text without command returns empty dict."""
        result = github_provider._parse_command("Just a regular comment")
        assert result == {}

    def test_parse_custom_command_prefix(
        self, github_provider_custom_config: GitHubProvider
    ) -> None:
        """Custom command prefix is correctly parsed."""
        result = github_provider_custom_config._parse_command("/feature run")
        assert result["command"] == "run"

        # Default prefix should not match
        result_adw = github_provider_custom_config._parse_command("/adw run")
        assert result_adw == {}
