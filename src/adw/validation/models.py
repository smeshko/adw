"""Validation models for the unified validation phase.

This module contains Pydantic models for validation results and issues.
Enhanced in Story 11.2 with structured issue tracking, fix history,
and triage support.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any, cast

import yaml
from pydantic import BaseModel, Field, field_validator

from adw.utils.ulid import generate_run_id


class IssueSource(str, Enum):
    """Source of a validation issue.

    Identifies which validator produced the issue:
    - TEST: From test execution (pytest, npm test, etc.)
    - REVIEW: From LLM code review
    - EVIDENCE: From evidence gathering comparison
    """

    TEST = "TEST"
    REVIEW = "REVIEW"
    EVIDENCE = "EVIDENCE"


# Backward compatibility alias
ValidationSource = IssueSource


class IssueSeverity(str, Enum):
    """Severity level of a validation issue.

    - ERROR: Must fix - blocks pipeline
    - WARNING: Should fix - can be deferred
    - INFO: Optional - can be dismissed
    """

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class FixResult(str, Enum):
    """Result of a fix attempt.

    - RESOLVED: Issue fully fixed
    - PARTIAL: Issue partially addressed
    - FAILED: Fix attempt did not work
    - NOT_ATTEMPTED: No fix has been tried yet
    """

    RESOLVED = "RESOLVED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    NOT_ATTEMPTED = "NOT_ATTEMPTED"


class IssueLocation(BaseModel):
    """Location information for a validation issue.

    Captures where in the codebase the issue was found.
    All fields are optional since not all issues have specific locations.

    Attributes:
        file_path: Path to the file containing the issue.
        line_start: Starting line number.
        line_end: Ending line number (for multi-line issues).
        function_name: Name of the function/method if applicable.
        test_name: Name of the test case if from test source.
    """

    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    function_name: str | None = None
    test_name: str | None = None

    model_config = {"frozen": False, "validate_assignment": True}


class IssueContext(BaseModel):
    """Context information for a validation issue.

    Provides additional details to help understand and fix the issue.
    Fields are truncated to prevent excessive storage.

    Attributes:
        code_snippet: Relevant code around the issue.
        error_message: Error or assertion message.
        stack_trace: Full or partial stack trace.
        related_files: Other files involved in the issue.
        suggestion: LLM or tool-generated fix suggestion.
    """

    code_snippet: str | None = Field(default=None, max_length=2000)
    error_message: str | None = Field(default=None, max_length=1000)
    stack_trace: str | None = Field(default=None, max_length=5000)
    related_files: list[str] = Field(default_factory=list)
    suggestion: str | None = Field(default=None, max_length=500)

    model_config = {"frozen": False, "validate_assignment": True}

    @field_validator("code_snippet", mode="before")
    @classmethod
    def truncate_code_snippet(cls, v: str | None) -> str | None:
        """Truncate code snippet to max length."""
        if v is not None and len(v) > 2000:
            return v[:2000]
        return v

    @field_validator("error_message", mode="before")
    @classmethod
    def truncate_error_message(cls, v: str | None) -> str | None:
        """Truncate error message to max length."""
        if v is not None and len(v) > 1000:
            return v[:1000]
        return v

    @field_validator("stack_trace", mode="before")
    @classmethod
    def truncate_stack_trace(cls, v: str | None) -> str | None:
        """Truncate stack trace to max length."""
        if v is not None and len(v) > 5000:
            return v[:5000]
        return v


class FixAttempt(BaseModel):
    """Record of a single fix attempt for an issue.

    Tracks when and how an issue fix was attempted, and what the outcome was.

    Attributes:
        timestamp: When the fix was attempted.
        result: Outcome of the fix attempt.
        notes: Human or LLM notes about the attempt.
        changes_made: List of files modified during the fix.
    """

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    result: FixResult
    notes: str | None = None
    changes_made: list[str] = Field(default_factory=list)

    model_config = {"frozen": False, "validate_assignment": True}


def _generate_issue_id() -> str:
    """Generate a unique issue ID with VI- prefix."""
    return f"VI-{generate_run_id()}"


def _normalize_severity(value: str | IssueSeverity) -> IssueSeverity:
    """Normalize severity value to IssueSeverity enum.

    Supports both new enum values (ERROR, WARNING, INFO) and legacy
    string values (critical, high, medium, low, info).
    """
    if isinstance(value, IssueSeverity):
        return value

    # Legacy mapping for backward compatibility
    legacy_mapping = {
        "critical": IssueSeverity.ERROR,
        "high": IssueSeverity.ERROR,
        "medium": IssueSeverity.WARNING,
        "low": IssueSeverity.WARNING,
        "info": IssueSeverity.INFO,
    }

    normalized = value.lower() if isinstance(value, str) else str(value).lower()
    if normalized in legacy_mapping:
        return legacy_mapping[normalized]

    # Try direct enum lookup (uppercase)
    try:
        return IssueSeverity(value.upper())
    except ValueError:
        return IssueSeverity.WARNING  # Default fallback


class ValidationIssue(BaseModel):
    """A single issue found during validation.

    Represents a problem discovered by one of the validators,
    including its source, severity, location, context, and fix tracking.

    Attributes:
        id: Unique issue ID (VI-{ulid} format).
        source: Which validator found this issue.
        severity: Issue severity level.
        description: Human-readable description of the issue.
        message: Alias for description (backward compatibility).
        location: Primary location of the issue.
        locations: Multiple affected locations (for cross-file issues).
        context: Additional context information.
        fix_attempted: Whether a fix has been tried.
        fix_attempt_count: Number of fix attempts made.
        last_fix_result: Result of the most recent fix attempt.
        fix_history: History of all fix attempts.
        triage_decision: Triage outcome (FIX, DISMISS, DEFER).
        triage_reason: Reason for triage decision.
        created_at: When the issue was first discovered.
        resolved_at: When the issue was marked resolved.
        file_path: Shorthand for single-file location (backward compat).
        line_number: Shorthand for single line location (backward compat).
        suggestion: Shorthand for context.suggestion (backward compat).
    """

    id: str = Field(default_factory=_generate_issue_id)
    source: IssueSource = Field(..., description="Which validator found this issue")
    severity: IssueSeverity = Field(..., description="Issue severity level")
    description: str = Field(..., description="Human-readable description of the issue")

    # Location information
    location: IssueLocation | None = None
    locations: list[IssueLocation] = Field(default_factory=list)

    # Context information
    context: IssueContext | None = None

    # Fix tracking
    fix_attempted: bool = False
    fix_attempt_count: int = 0
    last_fix_result: FixResult = FixResult.NOT_ATTEMPTED
    fix_history: list[FixAttempt] = Field(default_factory=list)

    # Triage fields (set in Story 11.3)
    triage_decision: str | None = None  # FIX, DISMISS, DEFER
    triage_reason: str | None = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = None

    # Backward compatibility fields
    file_path: str | None = Field(default=None, exclude=True)
    line_number: int | None = Field(default=None, exclude=True)
    suggestion: str | None = Field(default=None, exclude=True)

    def __init__(self, **data: object) -> None:
        """Initialize with backward compatibility for message and legacy severity."""
        # Handle 'message' as alias for 'description'
        if "message" in data and "description" not in data:
            data["description"] = data.pop("message")
        elif "message" in data:
            data.pop("message")  # Remove duplicate if both provided

        # Normalize severity (handle legacy string values)
        if "severity" in data:
            data["severity"] = _normalize_severity(
                cast("str | IssueSeverity", data["severity"])
            )

        super().__init__(**data)

        # Promote backward compat fields to proper structures
        if self.file_path and not self.location:
            object.__setattr__(
                self,
                "location",
                IssueLocation(
                    file_path=self.file_path,
                    line_start=self.line_number,
                ),
            )
        if self.suggestion and not self.context:
            object.__setattr__(
                self,
                "context",
                IssueContext(suggestion=self.suggestion),
            )

    @property
    def message(self) -> str:
        """Backward compatibility alias for description."""
        return self.description

    def _location_key(self) -> tuple[str | None, int | None]:
        """Extract location key for comparison.

        Returns a tuple of (file_path, line_start) from the primary location.
        """
        if self.location:
            return (self.location.file_path, self.location.line_start)
        return (None, None)

    def __eq__(self, other: object) -> bool:
        """Compare issues based on source, description, and location.

        Two issues are equal if they have the same source, description,
        and location (file_path and line_start).
        """
        if not isinstance(other, ValidationIssue):
            return NotImplemented
        return (
            self.source == other.source
            and self.description == other.description
            and self._location_key() == other._location_key()
        )

    def __hash__(self) -> int:
        """Hash based on immutable identifying characteristics.

        Uses source, truncated description (first 100 chars), and location key.
        """
        return hash(
            (
                self.source,
                self.description[:100],
                self._location_key(),
            )
        )

    def is_same_issue(self, other: "ValidationIssue") -> bool:
        """Fuzzy match to detect if two issues refer to the same problem.

        This is more lenient than __eq__ and is useful for detecting
        the same issue across different validation runs where descriptions
        may vary slightly.

        Args:
            other: Another ValidationIssue to compare against.

        Returns:
            True if the issues likely refer to the same underlying problem.
        """
        # Same source is required
        if self.source != other.source:
            return False

        # Same file required (if both have locations)
        if (
            self.location
            and other.location
            and self.location.file_path != other.location.file_path
        ):
            return False

        # Check description similarity (exact match or first 50 chars)
        return (
            self.description == other.description
            or self.description[:50] == other.description[:50]
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize issue to dictionary for JSON/persistence.

        Uses Pydantic's model_dump with JSON mode for proper serialization
        of enums and datetime objects.

        Returns:
            Dictionary representation suitable for JSON serialization.
        """
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValidationIssue":
        """Deserialize issue from dictionary.

        Creates a ValidationIssue instance from a dictionary, typically
        from JSON deserialization.

        Args:
            data: Dictionary containing issue data.

        Returns:
            New ValidationIssue instance.
        """
        return cls.model_validate(data)

    def to_markdown(self) -> str:
        """Render issue to human-readable markdown format.

        Produces a markdown representation suitable for reports or
        display in markdown-capable interfaces.

        Returns:
            Markdown-formatted string representing the issue.
        """
        lines = [
            f"## {self.severity.value}: {self.description}",
            f"- **ID:** `{self.id}`",
            f"- **Source:** {self.source.value}",
        ]

        if self.location:
            loc = f"- **Location:** `{self.location.file_path}`"
            if self.location.line_start:
                loc += f" (line {self.location.line_start})"
            lines.append(loc)

        if self.context and self.context.suggestion:
            lines.append(f"- **Suggestion:** {self.context.suggestion}")

        if self.fix_attempted:
            lines.append(
                f"- **Fix Status:** {self.last_fix_result.value} "
                f"({self.fix_attempt_count} attempts)"
            )

        return "\n".join(lines)

    def to_yaml(self) -> str:
        """Serialize issue to YAML format for persistence.

        Uses the dict representation and converts to YAML string
        with safe dumping for file storage.

        Returns:
            YAML-formatted string representation of the issue.
        """
        return yaml.safe_dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "ValidationIssue":
        """Deserialize issue from YAML string.

        Creates a ValidationIssue instance from a YAML string,
        typically from file storage.

        Args:
            yaml_str: YAML string containing issue data.

        Returns:
            New ValidationIssue instance.
        """
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "id": "VI-01HQ123456789ABCDEFGHJKMNP",
                "source": "TEST",
                "severity": "ERROR",
                "description": "Test failed: test_login_validation",
                "location": {
                    "file_path": "tests/test_auth.py",
                    "line_start": 42,
                },
                "fix_attempted": False,
                "fix_attempt_count": 0,
                "last_fix_result": "NOT_ATTEMPTED",
            }
        },
    }


class ValidationResult(BaseModel):
    """Result of the unified validation phase.

    Aggregates results from all enabled validators (evidence, review, tests)
    into a single result with pass/fail status and collected issues.

    Attributes:
        passed: Whether all validators passed with no issues.
        issues: List of issues found by validators.
    """

    passed: bool = Field(..., description="Whether validation passed")
    issues: list[ValidationIssue] = Field(
        default_factory=list, description="Issues found during validation"
    )

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "passed": False,
                "issues": [
                    {
                        "id": "VI-01HQ123456789ABCDEFGHJKMNP",
                        "source": "TEST",
                        "severity": "ERROR",
                        "description": "Test failed",
                    }
                ],
            }
        },
    }


class LoopState(BaseModel):
    """State of the validation loop for tracking progress.

    Tracks issue counts and stall detection for the fix iteration loop.

    Attributes:
        issues_resolved: Number of issues successfully fixed.
        issues_dismissed: Number of issues triaged as dismiss.
        issues_deferred: Number of issues deferred for later.
        issues_remaining: Number of issues still to address.
        stall_count: Consecutive iterations with no progress.
    """

    issues_resolved: int = Field(default=0, ge=0)
    issues_dismissed: int = Field(default=0, ge=0)
    issues_deferred: int = Field(default=0, ge=0)
    issues_remaining: int = Field(default=0, ge=0)
    stall_count: int = Field(default=0, ge=0)

    model_config = {"frozen": False, "validate_assignment": True}

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON persistence."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LoopState":
        """Deserialize from dictionary."""
        return cls.model_validate(data)


class ValidationState(BaseModel):
    """Persistable state for the validation loop.

    Captures all information needed to resume validation after interruption.
    Stored at .adw/runs/<run_id>/validation/state.json.

    Attributes:
        run_id: The run ID this state belongs to.
        current_iteration: Current iteration number (1-based).
        total_iterations: Maximum iterations configured.
        loop_state: Detailed loop progress tracking.
        started_at: When validation phase started.
        last_updated: When state was last persisted.
    """

    run_id: str = Field(..., description="Run ID for state association")
    current_iteration: int = Field(default=1, ge=1)
    total_iterations: int = Field(default=5, ge=1)
    loop_state: LoopState = Field(default_factory=LoopState)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "run_id": "01HQ123456789ABCDEFGHJKMNP",
                "current_iteration": 3,
                "total_iterations": 5,
                "loop_state": {
                    "issues_resolved": 5,
                    "issues_dismissed": 2,
                    "issues_deferred": 1,
                    "issues_remaining": 3,
                    "stall_count": 0,
                },
                "started_at": "2026-01-05T10:00:00Z",
                "last_updated": "2026-01-05T10:15:00Z",
            }
        },
    }

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON persistence."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValidationState":
        """Deserialize from dictionary."""
        return cls.model_validate(data)


__all__ = [
    "FixAttempt",
    "FixResult",
    "IssueContext",
    "IssueLocation",
    "IssueSeverity",
    "IssueSource",
    "LoopState",
    "ValidationIssue",
    "ValidationResult",
    "ValidationSource",  # Backward compatibility
    "ValidationState",
]
