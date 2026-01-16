"""Tests for Linear-specific webhook models.

Following ADR-001: Tests focus on business logic, validation, and error paths.
Avoid trivial attribute tests.
"""

from __future__ import annotations


class TestLinearEvent:
    """Tests for LinearEvent model."""

    def test_from_payload_parses_issue_event(self) -> None:
        """Should parse an issue event payload into LinearEvent."""
        from adw.models.webhook import LinearEvent

        payload = {
            "action": "create",
            "type": "Issue",
            "data": {
                "id": "issue-uuid",
                "identifier": "ENG-42",
                "title": "Add dark mode",
                "description": "Implement dark mode toggle",
                "labels": [{"id": "label-1", "name": "adw:auto"}],
            },
            "webhookTimestamp": 1705312800,
            "webhookId": "webhook-123",
        }

        event = LinearEvent.from_payload(payload)

        assert event.action == "create"
        assert event.type == "Issue"
        assert event.data["identifier"] == "ENG-42"
        assert event.webhook_timestamp == 1705312800
        assert event.webhook_id == "webhook-123"

    def test_from_payload_handles_missing_fields(self) -> None:
        """Should handle missing optional fields gracefully."""
        from adw.models.webhook import LinearEvent

        payload = {"action": "create"}

        event = LinearEvent.from_payload(payload)

        assert event.action == "create"
        assert event.type == "unknown"
        assert event.data == {}
        assert event.webhook_timestamp is None

    def test_get_issue_extracts_from_issue_event(self) -> None:
        """Should extract LinearIssue from Issue event data."""
        from adw.models.webhook import LinearEvent

        payload = {
            "action": "create",
            "type": "Issue",
            "data": {
                "id": "issue-uuid",
                "identifier": "ENG-42",
                "title": "Add dark mode",
                "description": "Implement dark mode toggle",
                "labels": [{"id": "label-1", "name": "adw:auto", "color": "#ff0000"}],
                "state": {"id": "state-1", "name": "Todo", "type": "unstarted"},
                "assignee": {"id": "user-1", "name": "John Doe", "email": "john@example.com"},
                "url": "https://linear.app/team/issue/ENG-42",
            },
        }

        event = LinearEvent.from_payload(payload)
        issue = event.get_issue()

        assert issue is not None
        assert issue.id == "issue-uuid"
        assert issue.identifier == "ENG-42"
        assert issue.title == "Add dark mode"
        assert issue.description == "Implement dark mode toggle"
        assert len(issue.labels) == 1
        assert issue.labels[0].name == "adw:auto"
        assert issue.state is not None
        assert issue.state.name == "Todo"
        assert issue.assignee is not None
        assert issue.assignee.name == "John Doe"
        assert issue.url == "https://linear.app/team/issue/ENG-42"

    def test_get_issue_extracts_from_comment_event(self) -> None:
        """Should extract nested issue from Comment event data."""
        from adw.models.webhook import LinearEvent

        payload = {
            "action": "create",
            "type": "Comment",
            "data": {
                "id": "comment-uuid",
                "body": "@adw run",
                "issue": {
                    "id": "issue-uuid",
                    "identifier": "ENG-42",
                    "title": "Add dark mode",
                    "labels": [],
                },
            },
        }

        event = LinearEvent.from_payload(payload)
        issue = event.get_issue()

        assert issue is not None
        assert issue.identifier == "ENG-42"
        assert issue.title == "Add dark mode"

    def test_get_issue_returns_none_for_unknown_type(self) -> None:
        """Should return None for event types without issue data."""
        from adw.models.webhook import LinearEvent

        payload = {"action": "create", "type": "Project", "data": {}}

        event = LinearEvent.from_payload(payload)
        issue = event.get_issue()

        assert issue is None

    def test_get_comment_extracts_from_comment_event(self) -> None:
        """Should extract LinearComment from Comment event."""
        from adw.models.webhook import LinearEvent

        payload = {
            "action": "create",
            "type": "Comment",
            "data": {
                "id": "comment-uuid",
                "body": "@adw run --phase build",
                "issue": {
                    "id": "issue-uuid",
                    "identifier": "ENG-42",
                    "title": "Feature",
                    "labels": [],
                },
            },
        }

        event = LinearEvent.from_payload(payload)
        comment = event.get_comment()

        assert comment is not None
        assert comment.id == "comment-uuid"
        assert comment.body == "@adw run --phase build"
        assert comment.issue is not None
        assert comment.issue.identifier == "ENG-42"

    def test_get_comment_returns_none_for_non_comment_event(self) -> None:
        """Should return None for non-Comment events."""
        from adw.models.webhook import LinearEvent

        payload = {"action": "create", "type": "Issue", "data": {}}

        event = LinearEvent.from_payload(payload)
        comment = event.get_comment()

        assert comment is None


class TestLinearIssue:
    """Tests for LinearIssue model."""

    def test_linear_issue_with_all_fields(self) -> None:
        """Should create LinearIssue with all fields populated."""
        from adw.models.webhook import (
            LinearAssignee,
            LinearIssue,
            LinearLabel,
            LinearState,
        )

        issue = LinearIssue(
            id="uuid",
            identifier="ENG-42",
            title="Add dark mode",
            description="Implement toggle",
            state=LinearState(id="s1", name="Todo", type="unstarted"),
            labels=[LinearLabel(id="l1", name="adw:auto", color="#ff0000")],
            assignee=LinearAssignee(id="u1", name="John"),
            url="https://linear.app/team/issue/ENG-42",
        )

        assert issue.identifier == "ENG-42"
        assert issue.state is not None
        assert issue.state.name == "Todo"
        assert len(issue.labels) == 1
        assert issue.assignee is not None

    def test_linear_issue_with_minimal_fields(self) -> None:
        """Should create LinearIssue with only required fields."""
        from adw.models.webhook import LinearIssue

        issue = LinearIssue(
            id="uuid",
            identifier="ENG-42",
            title="Feature",
        )

        assert issue.identifier == "ENG-42"
        assert issue.description is None
        assert issue.state is None
        assert issue.labels == []
        assert issue.assignee is None


class TestLinearComment:
    """Tests for LinearComment model."""

    def test_linear_comment_with_issue(self) -> None:
        """Should create LinearComment with associated issue."""
        from adw.models.webhook import LinearComment, LinearIssue

        comment = LinearComment(
            id="comment-uuid",
            body="@adw run",
            issue=LinearIssue(id="i1", identifier="ENG-42", title="Feature"),
        )

        assert comment.id == "comment-uuid"
        assert comment.body == "@adw run"
        assert comment.issue is not None
        assert comment.issue.identifier == "ENG-42"

    def test_linear_comment_without_issue(self) -> None:
        """Should create LinearComment without issue (edge case)."""
        from adw.models.webhook import LinearComment

        comment = LinearComment(
            id="comment-uuid",
            body="Just a comment",
        )

        assert comment.body == "Just a comment"
        assert comment.issue is None
