"""Tests for webhook security utilities.

Tests cover:
- HMAC signature verification with multiple algorithms
- Timing-safe comparison (verified via code inspection)
- Linear signature verification
- GitHub signature verification
- Missing secret handling (graceful degradation)
- Invalid signature handling
"""

from __future__ import annotations

import hashlib
import hmac
import inspect
from unittest.mock import MagicMock, patch

import pytest

from adw.webhook.security import (
    ENV_GITHUB_WEBHOOK_SECRET,
    ENV_LINEAR_WEBHOOK_SECRET,
    HEADER_GITHUB_SIGNATURE_256,
    HEADER_LINEAR_SIGNATURE,
    SignatureVerificationError,
    verify_github_signature,
    verify_hmac_signature,
    verify_linear_signature,
)


class TestVerifyHmacSignature:
    """Tests for verify_hmac_signature function."""

    def test_sha256_valid_signature(self) -> None:
        """Valid SHA-256 signature returns True."""
        payload = b'{"action": "create"}'
        secret = "test_secret"
        signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        result = verify_hmac_signature(payload, signature, secret, "sha256")

        assert result is True

    def test_sha256_invalid_signature(self) -> None:
        """Invalid SHA-256 signature returns False."""
        payload = b'{"action": "create"}'
        secret = "test_secret"

        result = verify_hmac_signature(payload, "invalid_signature", secret, "sha256")

        assert result is False

    def test_sha1_valid_signature(self) -> None:
        """Valid SHA-1 signature returns True."""
        payload = b'{"action": "create"}'
        secret = "test_secret"
        signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha1,
        ).hexdigest()

        result = verify_hmac_signature(payload, signature, secret, "sha1")

        assert result is True

    def test_sha1_invalid_signature(self) -> None:
        """Invalid SHA-1 signature returns False."""
        payload = b'{"action": "create"}'

        result = verify_hmac_signature(payload, "invalid", "secret", "sha1")

        assert result is False

    def test_unsupported_algorithm_raises(self) -> None:
        """Unsupported algorithm raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported algorithm: md5"):
            verify_hmac_signature(b"data", "sig", "secret", "md5")  # type: ignore[arg-type]

    def test_uses_timing_safe_comparison(self) -> None:
        """Verify implementation uses hmac.compare_digest for timing safety."""
        source = inspect.getsource(verify_hmac_signature)
        assert "compare_digest" in source, "Must use timing-safe comparison"


class TestVerifyLinearSignature:
    """Tests for verify_linear_signature function."""

    def _make_mock_request(
        self,
        signature: str | None = None,
        client_host: str = "127.0.0.1",
    ) -> MagicMock:
        """Create a mock FastAPI Request object."""
        request = MagicMock()
        headers = {}
        if signature is not None:
            headers[HEADER_LINEAR_SIGNATURE] = signature
        request.headers = headers
        request.client = MagicMock()
        request.client.host = client_host
        return request

    def test_valid_signature_returns_true(self) -> None:
        """Valid Linear signature returns True."""
        secret = "linear_secret"
        payload = b'{"action": "IssueCreate"}'
        signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        request = self._make_mock_request(signature=signature)

        with patch.dict("os.environ", {ENV_LINEAR_WEBHOOK_SECRET: secret}):
            result = verify_linear_signature(request, payload)

        assert result is True

    def test_invalid_signature_raises(self) -> None:
        """Invalid Linear signature raises SignatureVerificationError."""
        payload = b'{"action": "IssueCreate"}'
        request = self._make_mock_request(signature="invalid_signature")

        with patch.dict("os.environ", {ENV_LINEAR_WEBHOOK_SECRET: "secret"}):
            with pytest.raises(SignatureVerificationError) as exc_info:
                verify_linear_signature(request, payload)

        assert exc_info.value.provider == "linear"
        assert "Invalid signature" in exc_info.value.reason

    def test_missing_signature_header_raises(self) -> None:
        """Missing signature header raises SignatureVerificationError."""
        request = self._make_mock_request(signature=None)

        with patch.dict("os.environ", {ENV_LINEAR_WEBHOOK_SECRET: "secret"}):
            with pytest.raises(SignatureVerificationError) as exc_info:
                verify_linear_signature(request, b"payload")

        assert exc_info.value.provider == "linear"
        assert "Missing signature header" in exc_info.value.reason

    def test_missing_secret_skips_verification(self) -> None:
        """Missing secret skips verification with warning."""
        request = self._make_mock_request(signature="any")

        with patch.dict("os.environ", {}, clear=True):
            result = verify_linear_signature(request, b"payload")

        assert result is True  # Verification skipped


class TestVerifyGithubSignature:
    """Tests for verify_github_signature function."""

    def _make_mock_request(
        self,
        signature_header: str | None = None,
        client_host: str = "127.0.0.1",
    ) -> MagicMock:
        """Create a mock FastAPI Request object."""
        request = MagicMock()
        headers = {}
        if signature_header is not None:
            headers[HEADER_GITHUB_SIGNATURE_256] = signature_header
        request.headers = headers
        request.client = MagicMock()
        request.client.host = client_host
        return request

    def test_valid_sha256_signature_returns_true(self) -> None:
        """Valid GitHub sha256 signature returns True."""
        secret = "github_secret"
        payload = b'{"action": "opened"}'
        sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        header = f"sha256={sig}"

        request = self._make_mock_request(signature_header=header)

        with patch.dict("os.environ", {ENV_GITHUB_WEBHOOK_SECRET: secret}):
            result = verify_github_signature(request, payload)

        assert result is True

    def test_invalid_signature_raises(self) -> None:
        """Invalid GitHub signature raises SignatureVerificationError."""
        payload = b'{"action": "opened"}'
        request = self._make_mock_request(signature_header="sha256=invalid")

        with patch.dict("os.environ", {ENV_GITHUB_WEBHOOK_SECRET: "secret"}):
            with pytest.raises(SignatureVerificationError) as exc_info:
                verify_github_signature(request, payload)

        assert exc_info.value.provider == "github"
        assert "Invalid signature" in exc_info.value.reason

    def test_missing_signature_header_raises(self) -> None:
        """Missing signature header raises SignatureVerificationError."""
        request = self._make_mock_request(signature_header=None)

        with patch.dict("os.environ", {ENV_GITHUB_WEBHOOK_SECRET: "secret"}):
            with pytest.raises(SignatureVerificationError) as exc_info:
                verify_github_signature(request, b"payload")

        assert exc_info.value.provider == "github"
        assert "Missing signature header" in exc_info.value.reason

    def test_invalid_format_raises(self) -> None:
        """Invalid header format (missing sha256= prefix) raises error."""
        request = self._make_mock_request(signature_header="invalid_format")

        with patch.dict("os.environ", {ENV_GITHUB_WEBHOOK_SECRET: "secret"}):
            with pytest.raises(SignatureVerificationError) as exc_info:
                verify_github_signature(request, b"payload")

        assert exc_info.value.provider == "github"
        assert "Invalid signature format" in exc_info.value.reason

    def test_missing_secret_skips_verification(self) -> None:
        """Missing secret skips verification with warning."""
        request = self._make_mock_request(signature_header="sha256=any")

        with patch.dict("os.environ", {}, clear=True):
            result = verify_github_signature(request, b"payload")

        assert result is True  # Verification skipped


class TestSignatureVerificationError:
    """Tests for SignatureVerificationError exception."""

    def test_error_attributes(self) -> None:
        """Error captures provider and reason."""
        error = SignatureVerificationError("linear", "Invalid signature")

        assert error.provider == "linear"
        assert error.reason == "Invalid signature"

    def test_error_message(self) -> None:
        """Error message includes provider and reason."""
        error = SignatureVerificationError("github", "Missing header")

        assert "github" in str(error)
        assert "Missing header" in str(error)
