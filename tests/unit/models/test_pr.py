"""Unit tests for PR description model (Story 9.4).

Tests PRDescription model validation, serialization, and markdown conversion.
"""

import pytest
from pydantic import ValidationError

from adw.models import PRDescription


class TestPRDescriptionModel:
    """Tests for PRDescription model validation."""

    def test_create_valid_pr_description(self):
        """Test creating a valid PR description."""
        pr = PRDescription(
            summary="Add user authentication with JWT tokens",
            changes=["Add login endpoint", "Add token refresh logic"],
            testing="Unit tests added, all integration tests pass",
            evidence="See screenshots in evidence/screenshots/",
        )

        assert pr.summary == "Add user authentication with JWT tokens"
        assert len(pr.changes) == 2
        assert pr.testing == "Unit tests added, all integration tests pass"
        assert pr.evidence == "See screenshots in evidence/screenshots/"

    def test_default_evidence(self):
        """Test that evidence field has correct default."""
        pr = PRDescription(
            summary="Fix a critical bug in the system",
            changes=["Fix null pointer exception"],
            testing="Tests pass",
        )

        assert pr.evidence == "No visual evidence captured"

    def test_summary_min_length_validation(self):
        """Test that summary requires minimum length."""
        with pytest.raises(ValidationError) as exc_info:
            PRDescription(
                summary="Short",  # Too short (< 10 chars)
                changes=["Change 1"],
                testing="Tests pass",
            )

        errors = exc_info.value.errors()
        assert any("summary" in str(e) for e in errors)

    def test_changes_min_items_validation(self):
        """Test that changes requires at least one item."""
        with pytest.raises(ValidationError) as exc_info:
            PRDescription(
                summary="Add user authentication feature",
                changes=[],  # Empty list
                testing="Tests pass",
            )

        errors = exc_info.value.errors()
        assert any("changes" in str(e) for e in errors)

    def test_testing_min_length_validation(self):
        """Test that testing requires minimum length."""
        with pytest.raises(ValidationError) as exc_info:
            PRDescription(
                summary="Add user authentication feature",
                changes=["Change 1"],
                testing="OK",  # Too short (< 5 chars)
            )

        errors = exc_info.value.errors()
        assert any("testing" in str(e) for e in errors)


class TestPRDescriptionToMarkdown:
    """Tests for to_markdown() method."""

    def test_basic_markdown_output(self):
        """Test basic markdown generation."""
        pr = PRDescription(
            summary="Fix login bug in authentication module",
            changes=["Update password validation", "Fix session handling"],
            testing="All unit tests pass",
        )

        md = pr.to_markdown()

        assert "## Summary" in md
        assert "Fix login bug in authentication module" in md
        assert "## Changes" in md
        assert "- Update password validation" in md
        assert "- Fix session handling" in md
        assert "## Testing" in md
        assert "All unit tests pass" in md
        assert "## Evidence" in md
        assert "No visual evidence captured" in md

    def test_markdown_with_evidence(self):
        """Test markdown generation with custom evidence."""
        pr = PRDescription(
            summary="Add feature with screenshots",
            changes=["Add new UI component"],
            testing="Manual testing done",
            evidence="See ![screenshot](evidence/screenshots/login.png)",
        )

        md = pr.to_markdown()

        assert "## Evidence" in md
        assert "![screenshot](evidence/screenshots/login.png)" in md


class TestPRDescriptionFromMarkdown:
    """Tests for from_markdown() class method."""

    def test_parse_valid_markdown(self):
        """Test parsing valid markdown PR description."""
        markdown = """## Summary

Fix the login bug that caused authentication failures.

## Changes

- Update auth logic
- Fix session timeout

## Testing

All tests pass, including integration tests.

## Evidence

No visual evidence captured
"""

        pr = PRDescription.from_markdown(markdown)

        assert "login bug" in pr.summary
        assert len(pr.changes) == 2
        assert "Update auth logic" in pr.changes
        assert "Fix session timeout" in pr.changes
        assert "All tests pass" in pr.testing
        assert pr.evidence == "No visual evidence captured"

    def test_parse_markdown_missing_summary(self):
        """Test that missing summary raises error."""
        markdown = """## Changes

- Change 1

## Testing

Tests pass
"""

        with pytest.raises(ValueError, match="Missing required section: Summary"):
            PRDescription.from_markdown(markdown)

    def test_parse_markdown_missing_changes(self):
        """Test that missing changes raises error."""
        markdown = """## Summary

Add feature

## Testing

Tests pass
"""

        with pytest.raises(ValueError, match="Missing required section: Changes"):
            PRDescription.from_markdown(markdown)

    def test_parse_markdown_missing_testing(self):
        """Test that missing testing raises error."""
        markdown = """## Summary

Add feature

## Changes

- Change 1
"""

        with pytest.raises(ValueError, match="Missing required section: Testing"):
            PRDescription.from_markdown(markdown)

    def test_parse_markdown_default_evidence(self):
        """Test that missing evidence section uses default."""
        markdown = """## Summary

Add feature to the system

## Changes

- Change 1

## Testing

Tests pass
"""

        pr = PRDescription.from_markdown(markdown)
        assert pr.evidence == "No visual evidence captured"

    def test_roundtrip_markdown(self):
        """Test that to_markdown and from_markdown are consistent."""
        original = PRDescription(
            summary="Add user authentication with JWT tokens",
            changes=["Add login endpoint", "Add token refresh"],
            testing="Unit tests added, all pass",
            evidence="See evidence/screenshots/",
        )

        md = original.to_markdown()
        parsed = PRDescription.from_markdown(md)

        assert parsed.summary == original.summary
        assert parsed.changes == original.changes
        assert parsed.testing == original.testing
        assert parsed.evidence == original.evidence


class TestPRDescriptionSchema:
    """Tests for JSON schema methods."""

    def test_get_json_schema(self):
        """Test getting JSON schema."""
        schema = PRDescription.get_json_schema()

        assert schema["title"] == "PRDescription"
        assert "summary" in schema["required"]
        assert "changes" in schema["required"]
        assert "testing" in schema["required"]

    def test_validate_json_with_dict(self):
        """Test validating JSON from dict."""
        data = {
            "summary": "Fix critical bug in system",
            "changes": ["Fix bug", "Add test"],
            "testing": "All tests pass",
        }

        pr = PRDescription.validate_json(data)

        assert pr.summary == "Fix critical bug in system"
        assert len(pr.changes) == 2

    def test_validate_json_with_string(self):
        """Test validating JSON from string."""
        json_str = '{"summary": "Fix critical bug", "changes": ["Fix bug"], "testing": "Tests pass"}'

        pr = PRDescription.validate_json(json_str)

        assert pr.summary == "Fix critical bug"

    def test_validate_json_invalid_data(self):
        """Test that invalid JSON data raises error."""
        data = {
            "summary": "OK",  # Too short
            "changes": [],  # Empty
            "testing": "OK",  # Too short
        }

        with pytest.raises(ValidationError):
            PRDescription.validate_json(data)
