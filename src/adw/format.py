"""Display formatting shared by the CLI, Linear comments, live.log and the dashboard.

One formatter each for durations, token counts, relative times, costs and file
sizes, so every surface prints the same value the same way. The dashboard
registers them as Jinja filters.
"""

from datetime import UTC, datetime


def format_duration(seconds: float | None) -> str:
    """Format a duration: ``45s``, ``5m 32s`` or ``1h 2m``.

    Negative values clamp to 0; None gives ``—``.
    """
    if seconds is None:
        return "—"
    total = max(0, int(seconds))
    if total < 60:
        return f"{total}s"
    if total < 3600:
        minutes, secs = divmod(total, 60)
        return f"{minutes}m {secs}s"
    hours, rest = divmod(total, 3600)
    return f"{hours}h {rest // 60}m"


def format_tokens(count: int) -> str:
    """Format a token count: ``999``, ``1.2K``, ``340K``, ``1.2M`` or ``2M``.

    The unit is picked after rounding, so 9,999 is ``10K`` and 999,999 ``1M``.
    """
    if count < 0:
        return "-" + format_tokens(-count)
    if count < 1_000:
        return str(count)

    thousands = count / 1_000
    if round(thousands) < 1_000:
        text = f"{thousands:.1f}" if round(thousands, 1) < 10 else f"{thousands:.0f}"
        return text.removesuffix(".0") + "K"

    millions = count / 1_000_000
    return f"{millions:.1f}".removesuffix(".0") + "M"


def format_relative_time(when: datetime | None, *, now: datetime | None = None) -> str:
    """Format how long ago ``when`` was: ``30s ago``, ``5m ago``, ``2h ago``...

    A future time gives ``just now``, None gives ``—``, and a naive datetime
    is read as UTC.
    """
    if when is None:
        return "—"
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    seconds = int(((now or datetime.now(UTC)) - when).total_seconds())
    if seconds < 0:
        return "just now"
    if seconds < 60:
        return f"{seconds}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    return f"{hours // 24}d ago"


def format_cost(amount: float) -> str:
    """Format a USD amount: ``$47.82``, ``$1,234.56`` or ``-$1.00``."""
    if amount < 0:
        return f"-${-amount:,.2f}"
    return f"${amount:,.2f}"


def format_size(size_bytes: int) -> str:
    """Format a byte count, base 1024: ``512 B``, ``1.5 KB``, ``2.3 MB``, ``1.1 GB``."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    value = size_bytes / 1024
    for unit in ("KB", "MB"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"
