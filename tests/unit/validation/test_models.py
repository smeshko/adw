"""Tests for validation models (Story 11.2).

Tests cover:
- IssueSource, IssueSeverity, FixResult enums
- ValidationIssue model with required fields
- Issue ID generation with VI- prefix
- IssueLocation and IssueContext models
- Fix tracking with FixAttempt
- Issue comparison and hashing
- Serialization methods
"""

from adw.validation.models import (
    FixAttempt,
    FixResult,
    IssueContext,
    IssueLocation,
    IssueSeverity,
    IssueSource,
    ValidationIssue,
)


class TestIssueEnums:
    """Tests for validation issue enums."""

    def test_issue_source_has_required_values(self) -> None:
        """IssueSource enum has TEST, REVIEW, EVIDENCE values."""
        assert IssueSource.TEST == "TEST"
        assert IssueSource.REVIEW == "REVIEW"
        assert IssueSource.EVIDENCE == "EVIDENCE"

    def test_issue_severity_has_required_values(self) -> None:
        """IssueSeverity enum has ERROR, WARNING, INFO values."""
        assert IssueSeverity.ERROR == "ERROR"
        assert IssueSeverity.WARNING == "WARNING"
        assert IssueSeverity.INFO == "INFO"

    def test_fix_result_has_required_values(self) -> None:
        """FixResult enum has RESOLVED, PARTIAL, FAILED, NOT_ATTEMPTED values."""
        assert FixResult.RESOLVED == "RESOLVED"
        assert FixResult.PARTIAL == "PARTIAL"
        assert FixResult.FAILED == "FAILED"
        assert FixResult.NOT_ATTEMPTED == "NOT_ATTEMPTED"


class TestValidationIssue:
    """Tests for ValidationIssue model core functionality."""

    def test_create_with_required_fields(self) -> None:
        """Issue created with id, source, severity, description."""
        issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed: test_login",
        )
        assert issue.source == IssueSource.TEST
        assert issue.severity == IssueSeverity.ERROR
        assert issue.description == "Test failed: test_login"
        assert issue.id.startswith("VI-")

    def test_id_auto_generated_with_ulid(self) -> None:
        """Issue ID is auto-generated with VI- prefix and ULID."""
        issue = ValidationIssue(
            source=IssueSource.REVIEW,
            severity=IssueSeverity.WARNING,
            description="Missing docstring",
        )
        assert issue.id.startswith("VI-")
        # ULID portion is 26 characters
        ulid_part = issue.id[3:]  # Remove "VI-"
        assert len(ulid_part) == 26
        assert ulid_part.isalnum()

    def test_id_is_unique_across_instances(self) -> None:
        """Each issue gets a unique ID."""
        issue1 = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Error 1",
        )
        issue2 = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Error 2",
        )
        assert issue1.id != issue2.id

    def test_id_stable_across_serialization(self) -> None:
        """ID remains stable through serialization/deserialization."""
        issue = ValidationIssue(
            source=IssueSource.EVIDENCE,
            severity=IssueSeverity.INFO,
            description="Screenshot mismatch",
        )
        original_id = issue.id

        data = issue.model_dump()
        restored = ValidationIssue.model_validate(data)

        assert restored.id == original_id


class TestIssueLocation:
    """Tests for IssueLocation model."""

    def test_create_with_all_fields(self) -> None:
        """IssueLocation can be created with all location fields."""
        location = IssueLocation(
            file_path="src/auth.py",
            line_start=42,
            line_end=45,
            function_name="login",
            test_name="test_login_validation",
        )
        assert location.file_path == "src/auth.py"
        assert location.line_start == 42
        assert location.line_end == 45
        assert location.function_name == "login"
        assert location.test_name == "test_login_validation"

    def test_create_with_minimal_fields(self) -> None:
        """IssueLocation works with only some fields."""
        location = IssueLocation(file_path="src/utils.py", line_start=10)
        assert location.file_path == "src/utils.py"
        assert location.line_start == 10
        assert location.line_end is None
        assert location.function_name is None

    def test_issue_with_location(self) -> None:
        """ValidationIssue can include location information."""
        location = IssueLocation(
            file_path="tests/test_api.py",
            line_start=100,
            function_name="test_endpoint",
        )
        issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Assertion failed",
            location=location,
        )
        assert issue.location is not None
        assert issue.location.file_path == "tests/test_api.py"

    def test_issue_with_multiple_locations(self) -> None:
        """ValidationIssue can have multiple affected locations."""
        locations = [
            IssueLocation(file_path="src/a.py", line_start=10),
            IssueLocation(file_path="src/b.py", line_start=20),
        ]
        issue = ValidationIssue(
            source=IssueSource.REVIEW,
            severity=IssueSeverity.WARNING,
            description="Duplicate code detected",
            locations=locations,
        )
        assert len(issue.locations) == 2
        assert issue.locations[0].file_path == "src/a.py"
        assert issue.locations[1].file_path == "src/b.py"


class TestIssueContext:
    """Tests for IssueContext model."""

    def test_create_with_all_context_fields(self) -> None:
        """IssueContext can store full context information."""
        context = IssueContext(
            code_snippet="def login():\n    pass",
            error_message="AssertionError: expected True",
            stack_trace="Traceback...\n  File...",
            related_files=["src/auth.py", "tests/test_auth.py"],
            suggestion="Add return statement",
        )
        assert context.code_snippet == "def login():\n    pass"
        assert context.error_message == "AssertionError: expected True"
        assert len(context.related_files) == 2
        assert context.suggestion == "Add return statement"

    def test_context_truncates_long_fields(self) -> None:
        """Context fields are truncated to prevent excessive storage."""
        long_snippet = "x" * 3000  # Exceeds 2000 char limit
        long_error = "e" * 1500   # Exceeds 1000 char limit
        long_trace = "t" * 6000  # Exceeds 5000 char limit

        context = IssueContext(
            code_snippet=long_snippet,
            error_message=long_error,
            stack_trace=long_trace,
        )

        assert len(context.code_snippet) <= 2000
        assert len(context.error_message) <= 1000
        assert len(context.stack_trace) <= 5000

    def test_issue_with_context(self) -> None:
        """ValidationIssue can include context information."""
        context = IssueContext(
            error_message="TypeError: expected int",
            suggestion="Cast value to int first",
        )
        issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Type error in calculation",
            context=context,
        )
        assert issue.context is not None
        assert issue.context.error_message == "TypeError: expected int"


class TestFixTracking:
    """Tests for fix attempt tracking."""

    def test_fix_attempt_creation(self) -> None:
        """FixAttempt records fix attempt details."""
        attempt = FixAttempt(
            result=FixResult.PARTIAL,
            notes="Fixed main issue, side effect remains",
            changes_made=["src/auth.py", "tests/test_auth.py"],
        )
        assert attempt.result == FixResult.PARTIAL
        assert "side effect" in attempt.notes
        assert len(attempt.changes_made) == 2
        assert attempt.timestamp is not None

    def test_issue_fix_tracking_defaults(self) -> None:
        """ValidationIssue has correct fix tracking defaults."""
        issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed",
        )
        assert issue.fix_attempted is False
        assert issue.fix_attempt_count == 0
        assert issue.last_fix_result == FixResult.NOT_ATTEMPTED
        assert issue.fix_history == []

    def test_issue_records_fix_attempts(self) -> None:
        """ValidationIssue can track multiple fix attempts."""
        issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed",
        )

        # Record first attempt
        attempt1 = FixAttempt(
            result=FixResult.FAILED,
            notes="First attempt failed",
        )
        issue.fix_history.append(attempt1)
        issue.fix_attempted = True
        issue.fix_attempt_count = 1
        issue.last_fix_result = FixResult.FAILED

        # Record second attempt
        attempt2 = FixAttempt(
            result=FixResult.RESOLVED,
            notes="Fixed by correcting assertion",
        )
        issue.fix_history.append(attempt2)
        issue.fix_attempt_count = 2
        issue.last_fix_result = FixResult.RESOLVED

        assert len(issue.fix_history) == 2
        assert issue.fix_attempt_count == 2
        assert issue.last_fix_result == FixResult.RESOLVED


class TestIssueComparisonHashing:
    """Tests for issue comparison and hashing (Task 6)."""

    def test_equal_issues_same_source_description_location(self) -> None:
        """Issues with same source, description, and location are equal."""
        location = IssueLocation(file_path="src/auth.py", line_start=42)
        issue1 = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed",
            location=location,
        )
        issue2 = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed",
            location=IssueLocation(file_path="src/auth.py", line_start=42),
        )
        assert issue1 == issue2

    def test_different_issues_not_equal(self) -> None:
        """Issues with different source, description, or location are not equal."""
        issue1 = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed",
        )
        issue2 = ValidationIssue(
            source=IssueSource.REVIEW,
            severity=IssueSeverity.ERROR,
            description="Test failed",
        )
        assert issue1 != issue2

        issue3 = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Different error",
        )
        assert issue1 != issue3

    def test_hash_consistent_for_equal_issues(self) -> None:
        """Equal issues have the same hash value."""
        issue1 = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed",
            location=IssueLocation(file_path="src/auth.py", line_start=42),
        )
        issue2 = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed",
            location=IssueLocation(file_path="src/auth.py", line_start=42),
        )
        assert hash(issue1) == hash(issue2)

    def test_issues_usable_in_sets(self) -> None:
        """Issues can be added to sets and deduplicated."""
        issue1 = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed",
        )
        issue2 = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed",
        )
        issue3 = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Different error",
        )

        issue_set = {issue1, issue2, issue3}
        assert len(issue_set) == 2  # issue1 and issue2 are duplicates

    def test_is_same_issue_exact_match(self) -> None:
        """is_same_issue returns True for exact matches."""
        issue1 = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed: test_login_validation",
            location=IssueLocation(file_path="tests/test_auth.py"),
        )
        issue2 = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.WARNING,  # Different severity is OK
            description="Test failed: test_login_validation",
            location=IssueLocation(file_path="tests/test_auth.py"),
        )
        assert issue1.is_same_issue(issue2)

    def test_is_same_issue_fuzzy_match_description(self) -> None:
        """is_same_issue matches when first 50 chars are the same."""
        # Both descriptions share the same first 50+ characters
        issue1 = ValidationIssue(
            source=IssueSource.REVIEW,
            severity=IssueSeverity.WARNING,
            description="Missing docstring in function 'calculate_total_amount' - this is detailed extra info",
            location=IssueLocation(file_path="src/calc.py"),
        )
        issue2 = ValidationIssue(
            source=IssueSource.REVIEW,
            severity=IssueSeverity.WARNING,
            description="Missing docstring in function 'calculate_total_amount' - with different suffix",
            location=IssueLocation(file_path="src/calc.py"),
        )
        assert issue1.is_same_issue(issue2)

    def test_is_same_issue_different_source_no_match(self) -> None:
        """is_same_issue returns False for different sources."""
        issue1 = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Same description",
        )
        issue2 = ValidationIssue(
            source=IssueSource.REVIEW,
            severity=IssueSeverity.ERROR,
            description="Same description",
        )
        assert not issue1.is_same_issue(issue2)

    def test_is_same_issue_different_file_no_match(self) -> None:
        """is_same_issue returns False for different files."""
        issue1 = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed",
            location=IssueLocation(file_path="src/a.py"),
        )
        issue2 = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed",
            location=IssueLocation(file_path="src/b.py"),
        )
        assert not issue1.is_same_issue(issue2)

    def test_comparison_with_non_issue_type(self) -> None:
        """Comparison with non-ValidationIssue returns NotImplemented."""
        issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed",
        )
        # This should not raise, and should return False via NotImplemented
        assert issue != "not an issue"
        assert issue != 123
        assert issue != {"source": "TEST"}


class TestIssueSerialization:
    """Tests for issue serialization methods (Task 7)."""

    def test_to_dict_returns_json_serializable_dict(self) -> None:
        """to_dict returns a JSON-serializable dictionary."""
        issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed",
            location=IssueLocation(file_path="src/auth.py", line_start=42),
        )
        data = issue.to_dict()

        assert isinstance(data, dict)
        assert data["source"] == "TEST"
        assert data["severity"] == "ERROR"
        assert data["description"] == "Test failed"
        assert data["location"]["file_path"] == "src/auth.py"
        assert data["location"]["line_start"] == 42

    def test_from_dict_creates_valid_issue(self) -> None:
        """from_dict creates a valid ValidationIssue from dictionary."""
        data = {
            "id": "VI-01HQ123456789ABCDEFGHJKMNP",
            "source": "REVIEW",
            "severity": "WARNING",
            "description": "Missing docstring",
            "location": {"file_path": "src/utils.py", "line_start": 10},
        }
        issue = ValidationIssue.from_dict(data)

        assert issue.id == "VI-01HQ123456789ABCDEFGHJKMNP"
        assert issue.source == IssueSource.REVIEW
        assert issue.severity == IssueSeverity.WARNING
        assert issue.description == "Missing docstring"
        assert issue.location.file_path == "src/utils.py"

    def test_round_trip_serialization(self) -> None:
        """Issue survives round-trip through to_dict/from_dict."""
        original = ValidationIssue(
            source=IssueSource.EVIDENCE,
            severity=IssueSeverity.INFO,
            description="Screenshot mismatch detected",
            location=IssueLocation(
                file_path="src/ui/button.py",
                line_start=100,
                function_name="render",
            ),
            context=IssueContext(
                error_message="Visual diff > threshold",
                suggestion="Update baseline screenshot",
            ),
            fix_attempted=True,
            fix_attempt_count=1,
            last_fix_result=FixResult.PARTIAL,
        )

        data = original.to_dict()
        restored = ValidationIssue.from_dict(data)

        assert restored.id == original.id
        assert restored.source == original.source
        assert restored.severity == original.severity
        assert restored.description == original.description
        assert restored.location.file_path == original.location.file_path
        assert restored.context.suggestion == original.context.suggestion
        assert restored.fix_attempted == original.fix_attempted

    def test_to_markdown_basic_issue(self) -> None:
        """to_markdown produces readable markdown for basic issue."""
        issue = ValidationIssue(
            id="VI-TEST123",
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed: test_login_validation",
        )
        md = issue.to_markdown()

        assert "## ERROR: Test failed: test_login_validation" in md
        assert "**ID:** `VI-TEST123`" in md
        assert "**Source:** TEST" in md

    def test_to_markdown_with_location(self) -> None:
        """to_markdown includes location information."""
        issue = ValidationIssue(
            id="VI-TEST456",
            source=IssueSource.REVIEW,
            severity=IssueSeverity.WARNING,
            description="Missing error handling",
            location=IssueLocation(file_path="src/api.py", line_start=42),
        )
        md = issue.to_markdown()

        assert "**Location:** `src/api.py` (line 42)" in md

    def test_to_markdown_with_suggestion(self) -> None:
        """to_markdown includes suggestion from context."""
        issue = ValidationIssue(
            id="VI-TEST789",
            source=IssueSource.REVIEW,
            severity=IssueSeverity.INFO,
            description="Could use list comprehension",
            context=IssueContext(suggestion="Replace for loop with list comprehension"),
        )
        md = issue.to_markdown()

        assert "**Suggestion:** Replace for loop with list comprehension" in md

    def test_to_markdown_with_fix_status(self) -> None:
        """to_markdown includes fix status when fix was attempted."""
        issue = ValidationIssue(
            id="VI-FIX001",
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed",
            fix_attempted=True,
            fix_attempt_count=2,
            last_fix_result=FixResult.PARTIAL,
        )
        md = issue.to_markdown()

        assert "**Fix Status:** PARTIAL (2 attempts)" in md

    def test_to_yaml_returns_valid_yaml_string(self) -> None:
        """to_yaml returns a valid YAML string."""
        issue = ValidationIssue(
            source=IssueSource.TEST,
            severity=IssueSeverity.ERROR,
            description="Test failed",
            location=IssueLocation(file_path="src/auth.py", line_start=42),
        )
        yaml_str = issue.to_yaml()

        assert isinstance(yaml_str, str)
        assert "source: TEST" in yaml_str
        assert "severity: ERROR" in yaml_str
        assert "description: Test failed" in yaml_str

    def test_from_yaml_creates_valid_issue(self) -> None:
        """from_yaml creates a valid ValidationIssue from YAML string."""
        yaml_str = """
id: VI-01HQ123456789ABCDEFGHJKMNP
source: REVIEW
severity: WARNING
description: Missing docstring
location:
  file_path: src/utils.py
  line_start: 10
"""
        issue = ValidationIssue.from_yaml(yaml_str)

        assert issue.id == "VI-01HQ123456789ABCDEFGHJKMNP"
        assert issue.source == IssueSource.REVIEW
        assert issue.severity == IssueSeverity.WARNING
        assert issue.description == "Missing docstring"
        assert issue.location.file_path == "src/utils.py"

    def test_yaml_round_trip_serialization(self) -> None:
        """Issue survives round-trip through to_yaml/from_yaml."""
        original = ValidationIssue(
            source=IssueSource.EVIDENCE,
            severity=IssueSeverity.INFO,
            description="Screenshot mismatch detected",
            location=IssueLocation(
                file_path="src/ui/button.py",
                line_start=100,
                function_name="render",
            ),
            context=IssueContext(
                error_message="Visual diff > threshold",
                suggestion="Update baseline screenshot",
            ),
            fix_attempted=True,
            fix_attempt_count=1,
            last_fix_result=FixResult.PARTIAL,
        )

        yaml_str = original.to_yaml()
        restored = ValidationIssue.from_yaml(yaml_str)

        assert restored.id == original.id
        assert restored.source == original.source
        assert restored.severity == original.severity
        assert restored.description == original.description
        assert restored.location.file_path == original.location.file_path
        assert restored.context.suggestion == original.context.suggestion
        assert restored.fix_attempted == original.fix_attempted
