"""Tests for setup_logging: the adw logger's console and live.log handlers."""

import io
import logging
import os
import time
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from adw.cli.logs import _parse_log_line
from adw.dashboard.routes import _load_log_entries
from adw.logging import setup_logging
from adw.logging.console import ConsoleHandler, get_active_live, set_active_live
from adw.logging.live_stream import LiveStreamHandler
from adw.models.config import RedactionConfig
from adw.models.logging import Verbosity

RUN_ID = "01TESTRUNID0000000000000A"
SECRET = "sk-" + "a" * 24
LOGGER = logging.getLogger("adw.test.setup")


@pytest.fixture
def run_dir(tmp_path: Path) -> Path:
    return tmp_path / "runs" / RUN_ID


@pytest.fixture
def buf() -> io.StringIO:
    return io.StringIO()


@pytest.fixture
def console(buf: io.StringIO) -> Console:
    return Console(file=buf, width=200)


@pytest.fixture
def new_york_tz() -> Iterator[None]:
    """Run in a zone whose local time differs from UTC, even on a UTC box."""
    old = os.environ.get("TZ")
    os.environ["TZ"] = "America/New_York"
    time.tzset()
    yield
    if old is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = old
    time.tzset()


@pytest.mark.parametrize(
    ("verbosity", "shown"), [(Verbosity.VERBOSE, True), (Verbosity.NORMAL, False)]
)
def test_verbose_console_shows_debug(
    verbosity: Verbosity, shown: bool, console: Console, buf: io.StringIO
) -> None:
    """-v shows DEBUG records on the console; the default doesn't (B8)."""
    setup_logging(verbosity, console=console)

    LOGGER.debug("debug detail")

    assert ("[DEBUG] debug detail" in buf.getvalue()) is shown


def test_quiet_console_shows_only_errors(console: Console, buf: io.StringIO) -> None:
    setup_logging(Verbosity.QUIET, console=console)

    LOGGER.warning("a warning")
    LOGGER.error("an error")

    assert "a warning" not in buf.getvalue()
    assert "[ERROR] an error" in buf.getvalue()


@pytest.mark.parametrize(
    ("verbosity", "debug_written"),
    [
        (Verbosity.QUIET, False),
        (Verbosity.NORMAL, False),
        (Verbosity.VERBOSE, True),
        (Verbosity.TRACE, True),
    ],
)
def test_live_log_level_follows_verbosity(
    verbosity: Verbosity, debug_written: bool, run_dir: Path, console: Console
) -> None:
    """live.log records INFO always, and DEBUG at -v/--trace; -q is console-only."""
    setup_logging(verbosity, run_dir, console=console)

    LOGGER.debug("debug detail")
    LOGGER.info("info line")

    content = (run_dir / "live.log").read_text()
    assert "info line" in content
    assert ("debug detail" in content) is debug_written


def test_redacts_records_on_console_and_live_log(
    run_dir: Path, console: Console, buf: io.StringIO
) -> None:
    setup_logging(Verbosity.NORMAL, run_dir, console=console)

    LOGGER.warning("key %s", SECRET)

    for text in (buf.getvalue(), (run_dir / "live.log").read_text()):
        assert "[REDACTED]" in text
        assert "sk-aaaa" not in text


def test_llm_stream_is_redacted(run_dir: Path, console: Console) -> None:
    """LLM text, tool calls and errors go through the same redaction filter."""
    handler = setup_logging(Verbosity.NORMAL, run_dir, console=console)
    assert handler is not None

    handler.write_llm_token("token=abcdefgh1234")
    handler.write_tool_call("Bash", "curl -H 'Authorization: Bearer abc.def'")
    handler.write_error("password=hunter22")

    content = (run_dir / "live.log").read_text()
    for secret in ("abcdefgh1234", "abc.def", "hunter22"):
        assert secret not in content
    assert content.count("[REDACTED]") == 3
    # Redaction runs before colouring, so the error line keeps its reset code
    assert content.rstrip("\n").endswith("[REDACTED]\033[0m")


def test_live_log_timestamps_are_utc(tmp_path: Path, new_york_tz: None) -> None:
    """Record lines and LLM marker lines are both stamped in UTC."""
    epoch = 1_700_000_000.0  # 2023-11-14 22:13:20 UTC, 17:13:20 in New York
    handler = LiveStreamHandler(tmp_path / "live.log")
    try:
        handler.handle(
            logging.makeLogRecord(
                {
                    "msg": "record line",
                    "levelno": logging.INFO,
                    "levelname": "INFO",
                    "created": epoch,
                }
            )
        )
        with patch("adw.logging.live_stream.time.time", return_value=epoch):
            handler.write_llm_start("plan")
    finally:
        handler.close()

    lines = (tmp_path / "live.log").read_text().splitlines()
    assert len(lines) == 2
    assert all(line.startswith("[2023-11-14 22:13:20] ") for line in lines)


def test_record_lines_keep_the_parsed_shape(run_dir: Path, console: Console) -> None:
    """The dashboard and `adw logs follow` still parse record lines."""
    setup_logging(Verbosity.NORMAL, run_dir, console=console)

    LOGGER.info("phase started", extra={"phase": "build"})
    LOGGER.warning("slow hook")

    entries = _load_log_entries(run_dir.parent, RUN_ID)
    assert [e["level"] for e in entries] == ["INFO", "WARN"]
    assert "phase=build" in entries[0]["message"]
    assert _load_log_entries(run_dir.parent, RUN_ID, phase="build") == entries[:1]

    lines = (run_dir / "live.log").read_text().splitlines()
    parsed = [_parse_log_line(line) for line in lines]
    assert [p[1] if p else None for p in parsed] == ["INFO", "WARN"]


def test_second_call_replaces_handlers(run_dir: Path, console: Console) -> None:
    first = setup_logging(Verbosity.NORMAL, run_dir, console=console)
    assert first is not None
    LOGGER.info("opens the file")

    second = setup_logging(Verbosity.NORMAL, run_dir, console=console)

    handlers = logging.getLogger("adw").handlers
    assert sum(isinstance(h, ConsoleHandler) for h in handlers) == 1
    assert [h for h in handlers if isinstance(h, LiveStreamHandler)] == [second]
    assert first.stream is None


def test_disabled_redaction_warns_and_passes_secrets(
    run_dir: Path, console: Console, buf: io.StringIO
) -> None:
    setup_logging(
        Verbosity.NORMAL,
        run_dir,
        console=console,
        redaction=RedactionConfig(enabled=False),
    )

    LOGGER.info("key %s", SECRET)

    assert "redaction is DISABLED" in buf.getvalue()
    assert SECRET in (run_dir / "live.log").read_text()


def test_disabled_redaction_warns_once_across_calls(
    run_dir: Path, console: Console, buf: io.StringIO
) -> None:
    """adw run sets up logging twice; the DISABLED warning shows once."""
    disabled = RedactionConfig(enabled=False)
    setup_logging(Verbosity.NORMAL, console=console, redaction=disabled)
    setup_logging(Verbosity.NORMAL, run_dir, console=console, redaction=disabled)

    assert buf.getvalue().count("redaction is DISABLED") == 1


def test_live_log_needs_no_lock_file(run_dir: Path, console: Console) -> None:
    handler = setup_logging(Verbosity.NORMAL, run_dir, console=console)
    assert handler is not None

    LOGGER.info("a record")
    handler.write_llm_token("some LLM text")

    assert sorted(p.name for p in run_dir.iterdir()) == ["live.log"]


def test_console_handler_stops_active_spinner(console: Console) -> None:
    """A log line stops the running spinner so the two don't overlap."""
    spinner = MagicMock()
    set_active_live(spinner)
    try:
        setup_logging(Verbosity.NORMAL, console=console)
        LOGGER.info("hello")
    finally:
        live_after = get_active_live()
        set_active_live(None)

    spinner.stop.assert_called_once()
    assert live_after is None
