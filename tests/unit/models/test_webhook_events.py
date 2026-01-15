"""Tests for webhook event models.

Following ADR-001: Tests focus on validation, required fields, and
business logic - NOT trivial attribute access or serialization smoke tests.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from adw.models.webhook import RunParams, WebhookEvent


class TestWebhookEvent:
    """Tests for WebhookEvent model validation."""

    def test_required_fields_event_type_and_provider(self) -> None:
        """WebhookEvent requires event_type and provider."""
        # Should work with just required fields
        event = WebhookEvent(event_type="test", provider="mock")
        assert event.event_type == "test"
        assert event.provider == "mock"

    def test_missing_event_type_raises_validation_error(self) -> None:
        """Missing event_type should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            WebhookEvent(provider="mock")  # type: ignore[call-arg]
        assert "event_type" in str(exc_info.value)

    def test_missing_provider_raises_validation_error(self) -> None:
        """Missing provider should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            WebhookEvent(event_type="test")  # type: ignore[call-arg]
        assert "provider" in str(exc_info.value)

    def test_timestamp_defaults_to_utc_now(self) -> None:
        """Timestamp should default to current UTC time."""
        before = datetime.now(tz=timezone.utc)
        event = WebhookEvent(event_type="test", provider="mock")
        after = datetime.now(tz=timezone.utc)

        assert event.timestamp >= before
        assert event.timestamp <= after
        assert event.timestamp.tzinfo == timezone.utc

    def test_optional_raw_body_accepts_bytes(self) -> None:
        """raw_body should accept bytes for raw payload storage."""
        body = b'{"key": "value"}'
        event = WebhookEvent(
            event_type="test",
            provider="mock",
            raw_body=body,
        )
        assert event.raw_body == body


class TestRunParams:
    """Tests for RunParams model validation."""

    def test_required_field_feature_request(self) -> None:
        """RunParams requires feature_request."""
        params = RunParams(feature_request="Add new feature")
        assert params.feature_request == "Add new feature"

    def test_missing_feature_request_raises_validation_error(self) -> None:
        """Missing feature_request should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RunParams()  # type: ignore[call-arg]
        assert "feature_request" in str(exc_info.value)

    def test_phases_defaults_to_none_for_all_phases(self) -> None:
        """phases=None means run all phases."""
        params = RunParams(feature_request="test")
        assert params.phases is None

    def test_phases_accepts_list_of_strings(self) -> None:
        """phases can be set to specific phase list."""
        params = RunParams(
            feature_request="test",
            phases=["plan", "build"],
        )
        assert params.phases == ["plan", "build"]

    def test_source_info_and_metadata_default_to_empty_dict(self) -> None:
        """source_info and metadata should default to empty dicts."""
        params = RunParams(feature_request="test")
        assert params.source_info == {}
        assert params.metadata == {}
