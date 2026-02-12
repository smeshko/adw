"""Dashboard dependency injection and CSRF protection.

All data-layer access in the dashboard goes through FastAPI ``Depends()``
so that route handlers never import managers directly. CSRF tokens are
generated per-request and validated on every POST endpoint.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request, status

if TYPE_CHECKING:
    from adw.core.index_manager import IndexManager
    from adw.core.project_registry import ProjectRegistryManager
    from adw.core.run_trigger import RunTrigger
    from adw.core.stats_aggregator import StatsAggregator

# ── CSRF ────────────────────────────────────────────────────────────────────

# A per-process secret used for CSRF token HMAC signing.
# Generated once at import time; rotates on server restart.
_CSRF_SECRET: str = secrets.token_hex(32)

CSRF_FIELD_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"


def generate_csrf_token(request: Request) -> str:
    """Generate a signed CSRF token tied to the current request.

    The token is an HMAC-SHA256 of a random nonce using the per-process
    secret. The nonce is stored in ``request.state`` so that validation
    can recompute the expected signature.

    Args:
        request: The current FastAPI request.

    Returns:
        A hex-encoded ``nonce:signature`` CSRF token string.
    """
    nonce = secrets.token_hex(16)
    signature = hmac.new(
        _CSRF_SECRET.encode(), nonce.encode(), hashlib.sha256
    ).hexdigest()
    token = f"{nonce}:{signature}"
    # Stash on request state so templates can render it
    request.state.csrf_token = token
    return token


def _verify_csrf_token(token: str) -> bool:
    """Verify that a CSRF token has a valid signature.

    Args:
        token: The ``nonce:signature`` token string.

    Returns:
        True if the signature is valid, False otherwise.
    """
    if ":" not in token:
        return False
    nonce, signature = token.split(":", 1)
    expected = hmac.new(
        _CSRF_SECRET.encode(), nonce.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)


async def validate_csrf(request: Request) -> None:
    """FastAPI dependency that validates the CSRF token on POST requests.

    Checks both the form field and the ``X-CSRF-Token`` header so that
    HTMX-based forms and programmatic clients are both covered.

    Args:
        request: The current FastAPI request.

    Raises:
        HTTPException: 403 if the CSRF token is missing or invalid.
    """
    # Try form body first, then header
    token: str | None = None

    content_type = request.headers.get("content-type", "")
    if (
        "application/x-www-form-urlencoded" in content_type
        or "multipart/form-data" in content_type
    ):
        form = await request.form()
        token = form.get(CSRF_FIELD_NAME)  # type: ignore[assignment]

    if not token:
        token = request.headers.get(CSRF_HEADER_NAME)

    if not token or not _verify_csrf_token(token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing or invalid",
        )


# ── Project filter resolution ────────────────────────────────────────────────


def resolve_project_filter(
    project_registry: ProjectRegistryManager,
    display_name: str | None,
) -> tuple[str | None, str | None]:
    """Resolve a project display name to its path string.

    The dropdown shows registered display names (e.g., "adw") but the index
    stores the directory name (e.g., "adw-final"). This helper bridges the gap.

    Args:
        project_registry: ProjectRegistry instance.
        display_name: The display name from the filter dropdown, or None.

    Returns:
        Tuple of (project_path_str, display_name). Both None if no filter.
    """
    if not display_name:
        return None, None
    all_projects = project_registry.get_all()
    for p in all_projects:
        if p.name == display_name:
            return str(p.path), display_name
    # Fallback: treat as literal name (backward compat)
    return None, display_name


# ── Data layer DI ───────────────────────────────────────────────────────────


def get_index_manager() -> IndexManager:
    """Provide an IndexManager instance via Depends()."""
    from adw.core.index_manager import IndexManager

    return IndexManager()


def get_stats_aggregator() -> StatsAggregator:
    """Provide a StatsAggregator instance via Depends()."""
    from adw.core.stats_aggregator import StatsAggregator

    return StatsAggregator()


def get_project_registry() -> ProjectRegistryManager:
    """Provide a ProjectRegistryManager instance via Depends()."""
    from adw.core.project_registry import ProjectRegistryManager

    return ProjectRegistryManager()


def get_run_trigger() -> RunTrigger:
    """Provide a RunTrigger instance via Depends()."""
    from adw.core.run_trigger import RunTrigger

    return RunTrigger()
