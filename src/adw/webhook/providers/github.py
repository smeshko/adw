"""GitHub webhook provider implementation.

This module implements the WebhookProvider protocol for GitHub webhooks,
handling signature verification, event parsing, and ADW run triggering
for GitHub issues, comments, and PR review comments.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
from typing import TYPE_CHECKING, Any

from adw.models.webhook import RunParams, WebhookEvent
from adw.webhook.providers.base import BaseWebhookProvider
from adw.webhook.providers.loader import register_provider_factory

if TYPE_CHECKING:
    from fastapi import Request

    from adw.models.webhook import WebhookConfig

logger = logging.getLogger(__name__)

# GitHub-specific header names
HEADER_GITHUB_EVENT = "x-github-event"
HEADER_GITHUB_DELIVERY = "x-github-delivery"
HEADER_GITHUB_SIGNATURE_256 = "x-hub-signature-256"
HEADER_GITHUB_SIGNATURE = "x-hub-signature"  # Legacy SHA-1 fallback

# ADW trigger label and command patterns
ADW_LABEL = "adw"
ADW_COMMAND_PATTERN = re.compile(r"/adw\s+(\w+)(?:\s+(.*))?", re.IGNORECASE)
ADW_PHASE_FLAG_PATTERN = re.compile(r"--phase\s+(\w+)", re.IGNORECASE)


class GitHubProvider:
    """Webhook provider for GitHub events.

    Implements the WebhookProvider protocol to handle GitHub webhook
    events including issues, issue comments, and pull request review
    comments.

    Trigger conditions:
    - Issue opened with 'adw' label
    - Comment containing '/adw run' command
    - PR review comment containing '/adw fix' command

    Example:
        >>> provider = GitHubProvider(config)
        >>> if provider.verify_signature(request, body):
        ...     event = provider.parse_event(request, body)
        ...     if provider.should_trigger_run(event):
        ...         params = provider.extract_run_params(event)
        ...         # Start ADW run with params
    """

    def __init__(self, config: WebhookConfig | None = None) -> None:
        """Initialize the GitHub provider.

        Args:
            config: Optional webhook configuration containing GitHub settings.
        """
        self._config = config
        self._secret: str | None = None
        if config:
            provider_config = config.get_provider("github")
            if provider_config:
                self._secret = provider_config.get_secret()

    @property
    def name(self) -> str:
        """Provider identifier.

        Returns:
            The string 'github'.
        """
        return "github"

    def verify_signature(self, request: Request, body: bytes) -> bool:
        """Verify GitHub webhook signature.

        GitHub signs webhooks using HMAC-SHA256 (preferred) or HMAC-SHA1
        (legacy). This method checks both signature headers for compatibility.

        Args:
            request: The incoming FastAPI Request object.
            body: The raw request body bytes for signature computation.

        Returns:
            True if signature is valid or no secret is configured,
            False if signature is invalid.

        Note:
            If no secret is configured, signature verification is skipped
            and True is returned. This allows testing without secrets but
            should be avoided in production.
        """
        if not self._secret:
            logger.warning("GitHub webhook secret not configured - skipping verification")
            return True

        # Try SHA-256 signature first (preferred)
        signature_256 = BaseWebhookProvider.get_header(request, HEADER_GITHUB_SIGNATURE_256)
        if signature_256:
            return self._verify_hmac_sha256(body, signature_256)

        # Fall back to SHA-1 signature (legacy)
        signature_sha1 = BaseWebhookProvider.get_header(request, HEADER_GITHUB_SIGNATURE)
        if signature_sha1:
            return self._verify_hmac_sha1(body, signature_sha1)

        logger.warning("No GitHub signature header found")
        return False

    def _verify_hmac_sha256(self, body: bytes, signature: str) -> bool:
        """Verify HMAC-SHA256 signature.

        Args:
            body: The raw request body bytes.
            signature: The signature header value (format: 'sha256=<hex>').

        Returns:
            True if signature matches, False otherwise.
        """
        if not signature.startswith("sha256="):
            return False

        expected_signature = signature[7:]  # Remove 'sha256=' prefix
        computed = hmac.new(
            self._secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(computed, expected_signature)

    def _verify_hmac_sha1(self, body: bytes, signature: str) -> bool:
        """Verify HMAC-SHA1 signature (legacy).

        Args:
            body: The raw request body bytes.
            signature: The signature header value (format: 'sha1=<hex>').

        Returns:
            True if signature matches, False otherwise.
        """
        if not signature.startswith("sha1="):
            return False

        expected_signature = signature[5:]  # Remove 'sha1=' prefix
        computed = hmac.new(
            self._secret.encode("utf-8"),
            body,
            hashlib.sha1,
        ).hexdigest()

        return hmac.compare_digest(computed, expected_signature)

    def parse_event(self, request: Request, body: bytes) -> WebhookEvent:
        """Parse GitHub webhook into WebhookEvent.

        Extracts event type from headers and parses the JSON payload
        into a structured WebhookEvent.

        Args:
            request: The incoming FastAPI Request object.
            body: The raw request body bytes.

        Returns:
            Parsed WebhookEvent with GitHub-specific details.

        Raises:
            ValueError: If the request cannot be parsed.
        """
        event_type = BaseWebhookProvider.get_header(request, HEADER_GITHUB_EVENT)
        delivery_id = BaseWebhookProvider.get_header(request, HEADER_GITHUB_DELIVERY)

        if not event_type:
            raise ValueError("Missing X-GitHub-Event header")

        payload = BaseWebhookProvider.parse_json_body(body)
        action = payload.get("action", "")

        # Combine event type and action for more specific event identification
        combined_event_type = f"{event_type}_{action}" if action else event_type

        return WebhookEvent(
            event_type=combined_event_type,
            provider=self.name,
            payload=payload,
            headers={
                HEADER_GITHUB_EVENT: event_type,
                HEADER_GITHUB_DELIVERY: delivery_id or "",
            },
            raw_body=body,
        )

    def should_trigger_run(self, event: WebhookEvent) -> bool:
        """Check if event should trigger an ADW run.

        Trigger conditions:
        1. Issue opened with 'adw' label
        2. Issue or PR labeled with 'adw' label
        3. Issue comment containing '/adw <command>'
        4. PR review comment containing '/adw <command>'

        Args:
            event: The parsed webhook event.

        Returns:
            True if run should be triggered, False otherwise.
        """
        event_type = event.event_type
        payload = event.payload

        # Check for 'adw' label on issue opened or labeled events
        if event_type in ("issues_opened", "issues_labeled"):
            return self._has_adw_label(payload)

        # Check for /adw command in issue comments
        if event_type == "issue_comment_created":
            body = payload.get("comment", {}).get("body", "")
            return self._has_adw_command(body)

        # Check for /adw command in PR review comments
        if event_type == "pull_request_review_comment_created":
            body = payload.get("comment", {}).get("body", "")
            return self._has_adw_command(body)

        return False

    def _has_adw_label(self, payload: dict[str, Any]) -> bool:
        """Check if issue/PR has the 'adw' label.

        Args:
            payload: The webhook payload.

        Returns:
            True if 'adw' label is present, False otherwise.
        """
        issue = payload.get("issue", {})
        labels = issue.get("labels", [])
        return any(
            label.get("name", "").lower() == ADW_LABEL
            for label in labels
        )

    def _has_adw_command(self, text: str) -> bool:
        """Check if text contains an /adw command.

        Args:
            text: The comment text to check.

        Returns:
            True if /adw command is present, False otherwise.
        """
        return bool(ADW_COMMAND_PATTERN.search(text))

    def extract_run_params(self, event: WebhookEvent) -> RunParams:
        """Extract ADW run parameters from event.

        Builds the feature request from issue title/body or comment text,
        and extracts any command arguments.

        Args:
            event: The parsed webhook event.

        Returns:
            RunParams with feature_request, phases, and metadata.
        """
        payload = event.payload
        issue = payload.get("issue", {})
        comment = payload.get("comment", {})
        repository = payload.get("repository", {})

        # Determine feature request content based on event type
        if event.event_type.startswith("issue_comment") or event.event_type.startswith(
            "pull_request_review_comment"
        ):
            # For comments, use the comment body as feature request
            feature_request = comment.get("body", "")
            # Also parse any command arguments
            command_args = self._parse_command(feature_request)
        else:
            # For issue events, use issue title + body
            title = issue.get("title", "")
            body = issue.get("body", "") or ""
            feature_request = f"{title}\n\n{body}".strip()
            command_args = {}

        # Extract phase from command if present
        phases = None
        if "from_phase" in command_args:
            phases = [command_args["from_phase"]]

        return RunParams(
            feature_request=feature_request,
            phases=phases,
            source_info={
                "provider": self.name,
                "repo": repository.get("full_name"),
                "issue_number": issue.get("number"),
                "issue_url": issue.get("html_url"),
                "comment_url": comment.get("html_url") if comment else None,
            },
            metadata={
                "delivery_id": event.headers.get(HEADER_GITHUB_DELIVERY),
                "event_type": event.event_type,
                "command": command_args.get("command"),
            },
        )

    def _parse_command(self, text: str) -> dict[str, Any]:
        """Parse /adw command from text.

        Extracts command name and flags like --phase from the command text.

        Args:
            text: The comment text containing the command.

        Returns:
            Dictionary with parsed command details:
            - command: The command name (e.g., 'run', 'fix')
            - from_phase: The phase to start from (if --phase flag present)
        """
        match = ADW_COMMAND_PATTERN.search(text)
        if not match:
            return {}

        command = match.group(1).lower()
        args = match.group(2) or ""

        result: dict[str, Any] = {"command": command}

        # Parse --phase flag
        phase_match = ADW_PHASE_FLAG_PATTERN.search(args)
        if phase_match:
            result["from_phase"] = phase_match.group(1).lower()

        return result


def _create_github_provider(config: WebhookConfig) -> GitHubProvider:
    """Factory function for creating GitHubProvider instances.

    Args:
        config: The webhook configuration.

    Returns:
        A configured GitHubProvider instance.
    """
    return GitHubProvider(config)


# Register the provider factory
register_provider_factory("github", _create_github_provider)
