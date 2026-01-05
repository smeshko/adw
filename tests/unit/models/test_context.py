"""Tests for context models - validation and behavior only.

AUDIT NOTE: This file was reduced from ~564 lines to ~75 lines.
Removed trivial tests:
- All "defaults_to" tests (Pydantic guarantees defaults work)
- All "can_be_set" tests (Pydantic guarantees field assignment works)
- All serialization tests (Pydantic guarantees serialization works)
- All trivial creation tests (redundant with validation tests)

Kept: validation logic and immutability behavior that represent actual code.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from adw.models import RunContext


class TestRunContext:
    """Tests for RunContext model - validation and behavior."""

    def test_invalid_ulid_length(self) -> None:
        """Invalid ULID length raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RunContext(
                run_id="short",
                feature_description="Test",
                current_phase="plan",
                started_at=datetime.now(),
            )
        assert "ULID must be 26 characters" in str(exc_info.value)

    def test_invalid_ulid_characters(self) -> None:
        """Invalid ULID characters raise ValidationError."""
        # U is not valid in Crockford Base32 (26 chars with invalid U)
        with pytest.raises(ValidationError) as exc_info:
            RunContext(
                run_id="01KDSG2VDHNK0W4HSCUUUUUUUU",  # 26 chars with U
                feature_description="Test",
                current_phase="plan",
                started_at=datetime.now(),
            )
        assert "Invalid ULID character" in str(exc_info.value)

    def test_required_fields_missing(self) -> None:
        """Missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RunContext(
                run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
                # Missing feature_description, current_phase, started_at
            )  # type: ignore
        errors = exc_info.value.errors()
        missing_fields = {e["loc"][0] for e in errors}
        assert "feature_description" in missing_fields
        assert "current_phase" in missing_fields
        assert "started_at" in missing_fields

    def test_status_rejects_invalid_value(self) -> None:
        """status rejects invalid values."""
        with pytest.raises(ValidationError):
            RunContext(
                run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
                feature_description="Test",
                current_phase="plan",
                started_at=datetime.now(),
                status="invalid_status",  # type: ignore[arg-type]
            )

    def test_immutability_with_model_copy(self) -> None:
        """model_copy creates new instance without modifying original."""
        original = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Test",
            current_phase="plan",
            started_at=datetime.now(),
        )
        original_phase = original.current_phase

        # Create updated copy
        updated = original.model_copy(update={"current_phase": "build"})

        # Original unchanged
        assert original.current_phase == original_phase
        assert original.current_phase == "plan"

        # Updated has new value
        assert updated.current_phase == "build"

        # They are different objects
        assert original is not updated
