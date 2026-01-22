"""Webhook security utilities for signature verification.

This module provides security utilities for verifying webhook signatures
from various providers. It implements HMAC-based signature verification
with support for multiple hash algorithms.

Key features:
- Timing-safe signature comparison to prevent timing attacks
- Support for SHA-256 and SHA-1 algorithms
- Provider-specific verification functions for Linear and GitHub
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from fastapi import Request

logger = logging.getLogger(__name__)


def verify_hmac_signature(
    payload: bytes,
    signature: str,
    secret: str,
    algorithm: Literal["sha256", "sha1"] = "sha256",
) -> bool:
    """Verify HMAC signature using timing-safe comparison.

    Uses constant-time comparison via hmac.compare_digest() to prevent
    timing attacks that could leak information about the expected signature.

    Args:
        payload: Raw request body bytes.
        signature: Expected signature (hex encoded).
        secret: HMAC secret key.
        algorithm: Hash algorithm to use ("sha256" or "sha1").

    Returns:
        True if signature is valid, False otherwise.

    Raises:
        ValueError: If algorithm is not supported.

    Example:
        >>> import hmac, hashlib
        >>> secret = "my-secret"
        >>> payload = b'{"action": "create"}'
        >>> sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        >>> verify_hmac_signature(payload, sig, secret, "sha256")
        True
    """
    if algorithm == "sha256":
        hash_func = hashlib.sha256
    elif algorithm == "sha1":
        hash_func = hashlib.sha1
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    expected = hmac.new(
        secret.encode("utf-8"),
        payload,
        hash_func,
    ).hexdigest()

    # Use timing-safe comparison to prevent timing attacks
    return hmac.compare_digest(expected, signature)


# Environment variable names for webhook secrets
ENV_LINEAR_WEBHOOK_SECRET = "LINEAR_WEBHOOK_SECRET"
ENV_GITHUB_WEBHOOK_SECRET = "GITHUB_WEBHOOK_SECRET"

# Header names for webhook signatures
HEADER_LINEAR_SIGNATURE = "x-linear-signature"
HEADER_GITHUB_SIGNATURE_256 = "x-hub-signature-256"


class SignatureVerificationError(Exception):
    """Raised when webhook signature verification fails.

    Attributes:
        provider: The provider that failed verification.
        reason: The reason for failure.
    """

    def __init__(self, provider: str, reason: str) -> None:
        self.provider = provider
        self.reason = reason
        super().__init__(f"Signature verification failed for {provider}: {reason}")


def verify_linear_signature(request: Request, body: bytes) -> bool:
    """Verify Linear webhook signature.

    Linear uses HMAC-SHA256 with the signature provided in the
    X-Linear-Signature header as a hex-encoded string.

    Args:
        request: FastAPI request object.
        body: Raw request body bytes.

    Returns:
        True if signature is valid or verification is skipped.

    Raises:
        SignatureVerificationError: If signature verification fails.

    Note:
        If LINEAR_WEBHOOK_SECRET environment variable is not set,
        verification is skipped with a warning logged.
    """
    secret = os.environ.get(ENV_LINEAR_WEBHOOK_SECRET)

    if not secret:
        logger.warning(
            "Linear webhook secret not configured - skipping verification",
            extra={"env_var": ENV_LINEAR_WEBHOOK_SECRET, "provider": "linear"},
        )
        return True  # Skip verification when secret not configured

    signature = request.headers.get(HEADER_LINEAR_SIGNATURE)

    if not signature:
        logger.error(
            "Missing signature header for Linear webhook - request rejected",
            extra={
                "provider": "linear",
                "header": HEADER_LINEAR_SIGNATURE,
                "source_ip": _get_client_ip(request),
            },
        )
        raise SignatureVerificationError("linear", "Missing signature header")

    if not verify_hmac_signature(body, signature, secret, "sha256"):
        logger.error(
            "Invalid Linear webhook signature - request rejected",
            extra={"provider": "linear", "source_ip": _get_client_ip(request)},
        )
        raise SignatureVerificationError("linear", "Invalid signature")

    return True


def verify_github_signature(request: Request, body: bytes) -> bool:
    """Verify GitHub webhook signature.

    GitHub uses HMAC-SHA256 with the signature provided in the
    X-Hub-Signature-256 header in the format "sha256=<hex_signature>".

    Args:
        request: FastAPI request object.
        body: Raw request body bytes.

    Returns:
        True if signature is valid or verification is skipped.

    Raises:
        SignatureVerificationError: If signature verification fails.

    Note:
        If GITHUB_WEBHOOK_SECRET environment variable is not set,
        verification is skipped with a warning logged.
    """
    secret = os.environ.get(ENV_GITHUB_WEBHOOK_SECRET)

    if not secret:
        logger.warning(
            "GitHub webhook secret not configured - skipping verification",
            extra={"env_var": ENV_GITHUB_WEBHOOK_SECRET, "provider": "github"},
        )
        return True  # Skip verification when secret not configured

    header = request.headers.get(HEADER_GITHUB_SIGNATURE_256)

    if not header:
        logger.error(
            "Missing signature header for GitHub webhook - request rejected",
            extra={
                "provider": "github",
                "header": HEADER_GITHUB_SIGNATURE_256,
                "source_ip": _get_client_ip(request),
            },
        )
        raise SignatureVerificationError("github", "Missing signature header")

    # GitHub format: "sha256=<hex_signature>"
    if not header.startswith("sha256="):
        logger.error(
            "Invalid GitHub signature format - request rejected",
            extra={
                "provider": "github",
                "expected_prefix": "sha256=",
                "source_ip": _get_client_ip(request),
            },
        )
        raise SignatureVerificationError("github", "Invalid signature format")

    signature = header[7:]  # Remove "sha256=" prefix

    if not verify_hmac_signature(body, signature, secret, "sha256"):
        logger.error(
            "Invalid GitHub webhook signature - request rejected",
            extra={"provider": "github", "source_ip": _get_client_ip(request)},
        )
        raise SignatureVerificationError("github", "Invalid signature")

    return True


def _get_client_ip(request: Request) -> str:
    """Get client IP address from request for logging.

    Args:
        request: FastAPI request object.

    Returns:
        Client IP address or "unknown" if not available.
    """
    if request.client:
        return request.client.host
    return "unknown"
