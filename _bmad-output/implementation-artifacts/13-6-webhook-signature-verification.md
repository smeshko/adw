# Story 13.6: Webhook Signature Verification

Status: ready-for-dev
Linear Issue: not-configured
Epic: 13 - Webhook Infrastructure
Created: 2026-01-09

---

## Story

As a developer,
I want webhook signatures verified,
so that only legitimate events trigger runs and unauthorized requests are rejected.

## Acceptance Criteria

**Given** Linear webhook
**When** received
**Then** `X-Linear-Signature` header is verified against secret

**Given** GitHub webhook
**When** received
**Then** `X-Hub-Signature-256` header is verified against secret

**Given** signature verification fails
**When** invalid signature
**Then** 401 returned, event logged as rejected

**Given** secret not configured
**When** webhook received
**Then** verification skipped with warning log

## Tasks / Subtasks

### Task 1: Create Signature Verification Module
- [ ] Create `src/adw/webhook/security.py` for security utilities
- [ ] Implement generic HMAC signature verification
- [ ] Support multiple hash algorithms (SHA-256, SHA-1)
- [ ] Handle timing-safe comparison

### Task 2: Implement Linear Signature Verification
- [ ] Create `verify_linear_signature()` function
- [ ] Parse `X-Linear-Signature` header
- [ ] Use HMAC-SHA256 algorithm
- [ ] Read secret from `LINEAR_WEBHOOK_SECRET` env var

### Task 3: Implement GitHub Signature Verification
- [ ] Create `verify_github_signature()` function
- [ ] Parse `X-Hub-Signature-256` header (format: `sha256=<hex>`)
- [ ] Use HMAC-SHA256 algorithm
- [ ] Read secret from `GITHUB_WEBHOOK_SECRET` env var

### Task 4: Add Configuration Support
- [ ] Add `secret_env` field to provider configuration
- [ ] Support environment variable references
- [ ] Log warning when secret not configured
- [ ] Make verification optional (but default to enabled)

### Task 5: Integrate with Route Handler
- [ ] Add signature verification middleware or route decorator
- [ ] Return 401 Unauthorized on verification failure
- [ ] Include error message in response (without leaking secret)
- [ ] Log all verification failures with source IP

### Task 6: Update Provider Protocol
- [ ] Ensure `verify_signature()` method is called in route
- [ ] Pass request headers and body to verification
- [ ] Handle verification exceptions gracefully

### Task 7: Write Tests
- [ ] Create `tests/unit/webhook/test_security.py`
- [ ] Test HMAC verification with known values
- [ ] Test Linear signature verification
- [ ] Test GitHub signature verification
- [ ] Test missing secret handling
- [ ] Test invalid signature response

---

## Developer Context

### Technical Requirements

**From Architecture Document:**
- Signature verification is critical for security
- Use timing-safe comparison to prevent timing attacks
- Log all verification failures for security auditing
- Support graceful degradation when secret not configured

**Security Requirements:**
- Never expose secrets in logs or responses
- Use cryptographically secure comparison
- Handle malformed headers gracefully
- Rate limit on verification failures (future enhancement)

### Architecture Compliance

**File Locations:**
```
src/adw/webhook/
├── security.py                 # New: Security utilities
├── routes.py                  # Modified: Add verification
└── providers/
    ├── base.py               # Existing: verify_signature method
    └── linear.py             # Modified: Implement verification
```

### Library & Framework Requirements

**Generic HMAC Verification:**
```python
import hmac
import hashlib
from typing import Literal

def verify_hmac_signature(
    payload: bytes,
    signature: str,
    secret: str,
    algorithm: Literal["sha256", "sha1"] = "sha256",
) -> bool:
    """Verify HMAC signature.

    Uses timing-safe comparison to prevent timing attacks.

    Args:
        payload: Raw request body bytes
        signature: Expected signature (hex encoded)
        secret: HMAC secret key
        algorithm: Hash algorithm to use

    Returns:
        True if signature is valid
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

    return hmac.compare_digest(expected, signature)
```

**Linear Signature Verification:**
```python
import os
from fastapi import Request, HTTPException
from adw.logging import logger

HEADER_LINEAR_SIGNATURE = "X-Linear-Signature"
ENV_LINEAR_SECRET = "LINEAR_WEBHOOK_SECRET"

async def verify_linear_signature(request: Request) -> bool:
    """Verify Linear webhook signature.

    Args:
        request: FastAPI request object

    Returns:
        True if signature is valid

    Raises:
        HTTPException: If verification fails
    """
    secret = os.environ.get(ENV_LINEAR_SECRET)
    if not secret:
        logger.warning(
            "Linear webhook secret not configured",
            env_var=ENV_LINEAR_SECRET,
        )
        return True  # Skip verification

    signature = request.headers.get(HEADER_LINEAR_SIGNATURE)
    if not signature:
        logger.warning(
            "Missing signature header",
            provider="linear",
            header=HEADER_LINEAR_SIGNATURE,
        )
        raise HTTPException(
            status_code=401,
            detail="Missing signature header",
        )

    payload = await request.body()
    if not verify_hmac_signature(payload, signature, secret, "sha256"):
        logger.warning(
            "Invalid signature",
            provider="linear",
            source_ip=request.client.host if request.client else "unknown",
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid signature",
        )

    return True
```

**GitHub Signature Verification:**
```python
HEADER_GITHUB_SIGNATURE = "X-Hub-Signature-256"
ENV_GITHUB_SECRET = "GITHUB_WEBHOOK_SECRET"

async def verify_github_signature(request: Request) -> bool:
    """Verify GitHub webhook signature.

    GitHub format: "sha256=<hex_signature>"

    Args:
        request: FastAPI request object

    Returns:
        True if signature is valid

    Raises:
        HTTPException: If verification fails
    """
    secret = os.environ.get(ENV_GITHUB_SECRET)
    if not secret:
        logger.warning(
            "GitHub webhook secret not configured",
            env_var=ENV_GITHUB_SECRET,
        )
        return True  # Skip verification

    header = request.headers.get(HEADER_GITHUB_SIGNATURE)
    if not header:
        raise HTTPException(status_code=401, detail="Missing signature header")

    # Parse "sha256=<hex>" format
    if not header.startswith("sha256="):
        raise HTTPException(status_code=401, detail="Invalid signature format")

    signature = header[7:]  # Remove "sha256=" prefix

    payload = await request.body()
    if not verify_hmac_signature(payload, signature, secret, "sha256"):
        logger.warning(
            "Invalid signature",
            provider="github",
            source_ip=request.client.host if request.client else "unknown",
        )
        raise HTTPException(status_code=401, detail="Invalid signature")

    return True
```

**Route Integration:**
```python
from fastapi import Depends

async def verify_provider_signature(
    provider: str,
    request: Request,
) -> None:
    """Verify webhook signature for the given provider."""
    if provider == "linear":
        await verify_linear_signature(request)
    elif provider == "github":
        await verify_github_signature(request)
    # Unknown providers skip verification (logged in route)

@app.post("/webhook/{provider}")
async def receive_webhook(
    provider: str,
    request: Request,
    _: None = Depends(verify_provider_signature),
):
    # Signature verified at this point
    ...
```

### File Structure Requirements

**New Files to Create:**
1. `src/adw/webhook/security.py` - Security verification utilities
2. `tests/unit/webhook/test_security.py` - Security tests

**Files to Modify:**
1. `src/adw/webhook/routes.py` - Add signature verification dependency
2. `src/adw/webhook/providers/linear.py` - Use security utilities
3. `src/adw/models/webhook.py` - Add secret_env to ProviderConfig

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/webhook/test_security.py
import pytest
import hmac
import hashlib
from adw.webhook.security import (
    verify_hmac_signature,
    verify_linear_signature,
    verify_github_signature,
)

def test_hmac_sha256_valid():
    payload = b'{"action": "create"}'
    secret = "test_secret"
    signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    assert verify_hmac_signature(payload, signature, secret, "sha256") is True

def test_hmac_sha256_invalid():
    payload = b'{"action": "create"}'
    assert verify_hmac_signature(payload, "invalid", "secret", "sha256") is False

def test_timing_safe_comparison():
    """Ensure we use timing-safe comparison."""
    # This is more of a code review check - verify hmac.compare_digest is used
    import inspect
    source = inspect.getsource(verify_hmac_signature)
    assert "compare_digest" in source
```

**Linear Tests:**
```python
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

@pytest.mark.asyncio
async def test_linear_verification_success(test_client):
    secret = "test_secret"
    payload = b'{"action":"create"}'
    signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    with patch.dict(os.environ, {"LINEAR_WEBHOOK_SECRET": secret}):
        response = test_client.post(
            "/webhook/linear",
            content=payload,
            headers={"X-Linear-Signature": signature},
        )
        assert response.status_code != 401

@pytest.mark.asyncio
async def test_linear_verification_failure():
    with patch.dict(os.environ, {"LINEAR_WEBHOOK_SECRET": "secret"}):
        response = test_client.post(
            "/webhook/linear",
            content=b'{"action":"create"}',
            headers={"X-Linear-Signature": "invalid"},
        )
        assert response.status_code == 401

@pytest.mark.asyncio
async def test_linear_missing_header():
    with patch.dict(os.environ, {"LINEAR_WEBHOOK_SECRET": "secret"}):
        response = test_client.post(
            "/webhook/linear",
            content=b'{"action":"create"}',
        )
        assert response.status_code == 401
```

**GitHub Tests:**
```python
@pytest.mark.asyncio
async def test_github_sha256_format():
    secret = "test_secret"
    payload = b'{"action":"opened"}'
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    with patch.dict(os.environ, {"GITHUB_WEBHOOK_SECRET": secret}):
        response = test_client.post(
            "/webhook/github",
            content=payload,
            headers={"X-Hub-Signature-256": f"sha256={sig}"},
        )
        assert response.status_code != 401
```

---

## Previous Story Intelligence

**From Story 13.2:**
- `WebhookProvider` Protocol includes `verify_signature()` method
- Provider implementations call this method early in processing
- Returns bool for verification result

**From Story 13.3:**
- Linear provider has basic signature verification structure
- Uses environment variable for secret
- This story enhances with proper security utilities

---

## Git Intelligence

**Recent Patterns:**
- Security-critical code has extensive test coverage
- Environment variables for secrets
- Logging without exposing sensitive data

**Recommended Commit Pattern:**
```
feat(webhook): implement robust signature verification

- Add security.py with HMAC verification utilities
- Implement Linear signature verification
- Implement GitHub signature verification (sha256= format)
- Add FastAPI dependency for route integration
- Log verification failures with source IP
- Handle missing secrets gracefully with warning
- Include comprehensive security test suite
```

---

## Latest Technical Information

**Linear Webhook Signatures:**
- Header: `X-Linear-Signature`
- Algorithm: HMAC-SHA256
- Format: Raw hex string

**GitHub Webhook Signatures:**
- Header: `X-Hub-Signature-256`
- Algorithm: HMAC-SHA256
- Format: `sha256=<hex_string>`
- Legacy: `X-Hub-Signature` (SHA-1, deprecated)

**Security Best Practices:**
- Always use `hmac.compare_digest()` for timing-safe comparison
- Never log secrets or full signatures
- Return generic error messages to clients
- Log source IP for security auditing

---

## Project Context Reference

See: _bmad-output/project-context.md

Key patterns and rules from project context:
- Environment variables for secrets (never in code)
- Structured logging with context
- Security-critical code needs comprehensive testing
- Graceful degradation with warnings

---

## Dev Notes

### Critical Success Factors

1. **Timing-Safe Comparison:** Must use `hmac.compare_digest()`
2. **401 Response:** Invalid signatures must return 401
3. **No Secret Leakage:** Never log or expose secrets
4. **Graceful Degradation:** Work without secret (with warning)

### Common Pitfalls to Avoid

- Don't use `==` for signature comparison (timing attack vulnerable)
- Don't log the actual signature values
- Don't expose detailed error messages to clients
- Don't forget to handle missing headers

### Security Considerations

- Consider rate limiting on verification failures
- Log client IP for all failures (audit trail)
- Consider alerting on repeated failures
- Document secret rotation procedure

### References

- [Source: _bmad-output/epics/epic-13-webhook-infrastructure.md#Story-13.6]
- [Source: Linear API Documentation - Webhook Security]
- [Source: GitHub Webhook Documentation - Validating Payloads]
- [Source: OWASP Cryptographic Practices]

---

## Dev Agent Record

### Context Reference

Story context created by create-epic workflow (Epic 13 generation)

### Agent Model Used

Claude Opus 4.5 (create-epic autonomous orchestrator)

### Debug Log References

### Completion Notes List

### File List

---

## Dependencies

- **Depends On:** Story 13.2 (Webhook Provider Protocol)
- **Blocks:** None
- **Can Parallel With:** Story 13.3 (Linear Provider), Story 13.7 (GitHub Provider)

### Dependency Rationale
- Story 13.2 defines the verify_signature() method in Protocol
- Can be developed in parallel with provider implementations
- Security utilities can be shared across all providers
