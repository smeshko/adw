"""Tests for the display formatters in adw.format."""

from datetime import UTC, datetime, timedelta

import pytest

from adw.format import (
    STATUS_STYLES,
    UNKNOWN_STATUS_STYLE,
    format_cost,
    format_duration,
    format_relative_time,
    format_size,
    format_tokens,
    status_style,
)
from adw.models.context import RunStatus


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (None, "—"),
        (0, "0s"),
        (0.4, "0s"),
        (45.9, "45s"),
        (59, "59s"),
        (60, "1m 0s"),
        (332, "5m 32s"),
        (3599, "59m 59s"),
        (3600, "1h 0m"),
        (3930, "1h 5m"),
        (90000, "25h 0m"),
        (-5, "0s"),
    ],
)
def test_format_duration(seconds: float | None, expected: str) -> None:
    assert format_duration(seconds) == expected


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (0, "0"),
        (999, "999"),
        (1_000, "1K"),
        (1_234, "1.2K"),
        (9_999, "10K"),
        (12_345, "12K"),
        (340_000, "340K"),
        (999_499, "999K"),
        (999_999, "1M"),
        (1_234_567, "1.2M"),
        (2_000_000, "2M"),
        (12_300_000, "12.3M"),
        (-1_500, "-1.5K"),
    ],
)
def test_format_tokens(count: int, expected: str) -> None:
    assert format_tokens(count) == expected


NOW = datetime(2026, 9, 24, 12, 0, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("when", "expected"),
    [
        (None, "—"),
        (NOW + timedelta(seconds=10), "just now"),
        (NOW, "0s ago"),
        (NOW - timedelta(seconds=30), "30s ago"),
        (NOW - timedelta(minutes=5), "5m ago"),
        (NOW - timedelta(minutes=59, seconds=59), "59m ago"),
        (NOW - timedelta(hours=2), "2h ago"),
        (NOW - timedelta(days=3), "3d ago"),
        (NOW - timedelta(days=45), "45d ago"),
        # A naive time is read as UTC
        (datetime(2026, 9, 24, 11, 55, 0), "5m ago"),
    ],
)
def test_format_relative_time(when: datetime | None, expected: str) -> None:
    assert format_relative_time(when, now=NOW) == expected


def test_format_relative_time_defaults_to_now() -> None:
    assert format_relative_time(datetime.now(UTC) - timedelta(hours=1)) == "1h ago"


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (0, "$0.00"),
        (0.05, "$0.05"),
        (47.824, "$47.82"),
        (1234.56, "$1,234.56"),
        (-1, "-$1.00"),
    ],
)
def test_format_cost(amount: float, expected: str) -> None:
    assert format_cost(amount) == expected


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        (0, "0 B"),
        (512, "512 B"),
        (1024, "1.0 KB"),
        (1536, "1.5 KB"),
        (2_411_724, "2.3 MB"),
        (1024**3 + 1024**3 // 10, "1.1 GB"),
    ],
)
def test_format_size(size: int, expected: str) -> None:
    assert format_size(size) == expected


def test_status_style_covers_every_run_status() -> None:
    assert set(STATUS_STYLES) == set(RunStatus)
    for status in RunStatus:
        assert status_style(status.value) is STATUS_STYLES[status]
    assert status_style("paused") is UNKNOWN_STATUS_STYLE
