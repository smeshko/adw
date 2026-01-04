"""Evidence-related models for ADW evidence gathering.

This module contains models for platform detection and evidence gathering
strategy selection during the Verify phase.

Includes:
- Platform detection models (PlatformType, Confidence, PlatformDetectionResult)
- Evidence strategy models (EvidenceStrategy)
- CLI evidence capture models (CommandConfig, CommandResult, CLIEvidenceSummary)
"""

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class PlatformType(str, Enum):
    """Type of project platform for evidence gathering.

    The platform type determines which evidence gathering strategy
    to use during the Verify phase:
    - CLI: Capture terminal output from CLI commands
    - WEB: Capture browser screenshots
    - MOBILE: Capture device/simulator screenshots
    - BACKEND: Capture API request/response pairs
    - UNKNOWN: Default to CLI strategy with warning
    """

    CLI = "cli"
    WEB = "web"
    MOBILE = "mobile"
    BACKEND = "backend"
    UNKNOWN = "unknown"


class Confidence(str, Enum):
    """Confidence level for platform detection.

    Confidence levels indicate how certain the detection is:
    - HIGH: Explicit config or multiple strong markers
    - MEDIUM: Multiple weak markers corroborating
    - LOW: Single weak marker or inference
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EvidenceStrategy(str, Enum):
    """Strategy for gathering evidence during Verify phase.

    Each strategy determines how evidence is captured:
    - TERMINAL_OUTPUT: Capture stdout/stderr from CLI commands
    - SCREENSHOT: Capture browser/device screenshots (WEB and MOBILE)
    - API_CAPTURE: Capture HTTP request/response pairs
    """

    TERMINAL_OUTPUT = "terminal_output"
    SCREENSHOT = "screenshot"
    API_CAPTURE = "api_capture"


class PlatformDetectionResult(BaseModel):
    """Result of platform detection.

    This model captures the outcome of detecting a project's platform type,
    including the confidence level and what markers were found.

    Attributes:
        platform: The detected platform type
        confidence: How confident the detection is
        source: Where the detection came from (config, markers, default)
        markers: List of markers found that informed the detection

    Example:
        >>> result = PlatformDetectionResult(
        ...     platform=PlatformType.WEB,
        ...     confidence=Confidence.HIGH,
        ...     source="markers",
        ...     markers=["package.json:react", "next.config.js"],
        ... )
        >>> result.platform
        <PlatformType.WEB: 'web'>
    """

    platform: PlatformType = Field(
        ..., description="The detected platform type"
    )
    confidence: Confidence = Field(
        ..., description="How confident the detection is"
    )
    source: str = Field(
        ..., description="Where the detection came from (config, markers, default)"
    )
    markers: list[str] = Field(
        default_factory=list,
        description="List of markers found that informed the detection",
    )

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "platform": "web",
                "confidence": "high",
                "source": "markers",
                "markers": ["package.json:react", "next.config.js"],
            }
        },
    }


# =============================================================================
# CLI Evidence Capture Models
# =============================================================================


class CommandConfig(BaseModel):
    """Configuration for a CLI command to execute during evidence gathering.

    This model represents a single command that will be executed to gather
    evidence during the Verify phase for CLI projects.

    Attributes:
        name: Unique identifier for the command (used in output filenames)
        cmd: The shell command to execute
        timeout: Maximum execution time in seconds (default: 30)

    Example:
        >>> config = CommandConfig(
        ...     name="version",
        ...     cmd="adw --version",
        ...     timeout=30,
        ... )
        >>> config.name
        'version'
    """

    name: str = Field(..., description="Unique name for this command")
    cmd: str = Field(..., description="The shell command to execute")
    timeout: int = Field(
        default=30,
        gt=0,
        description="Maximum execution time in seconds",
    )

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "name": "version",
                "cmd": "adw --version",
                "timeout": 30,
            }
        },
    }


class CommandResult(BaseModel):
    """Result of executing a CLI command.

    Captures the complete output and metadata from executing a command,
    including stdout, stderr, exit code, duration, and success status.

    Attributes:
        command: The command that was executed
        exit_code: Exit code from the command (-1 for timeout)
        stdout: Standard output captured from the command
        stderr: Standard error captured from the command
        duration_seconds: How long the command took to execute
        success: Whether the command succeeded (exit_code == 0)
        executed_at: When the command was executed (UTC)

    Example:
        >>> result = CommandResult(
        ...     command="adw --version",
        ...     exit_code=0,
        ...     stdout="adw version 1.0.0",
        ...     stderr="",
        ...     duration_seconds=0.125,
        ...     success=True,
        ... )
        >>> result.success
        True
    """

    command: str = Field(..., description="The command that was executed")
    exit_code: int = Field(..., description="Exit code from the command")
    stdout: str = Field(..., description="Standard output")
    stderr: str = Field(..., description="Standard error")
    duration_seconds: float = Field(
        ..., ge=0, description="Execution duration in seconds"
    )
    success: bool = Field(..., description="Whether the command succeeded")
    executed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the command was executed (UTC)",
    )

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "command": "adw --version",
                "exit_code": 0,
                "stdout": "adw version 1.0.0",
                "stderr": "",
                "duration_seconds": 0.125,
                "success": True,
                "executed_at": "2026-01-03T10:30:45Z",
            }
        },
    }


class CLIEvidenceSummary(BaseModel):
    """Summary of CLI evidence gathering results.

    Aggregates the results of executing multiple CLI commands during
    the Verify phase, providing counts and detailed results.

    Attributes:
        total_commands: Total number of commands executed
        passed: Number of commands that succeeded (exit_code == 0)
        failed: Number of commands that failed (exit_code != 0)
        results: List of individual command results
        platform: The platform type (always "cli" for this summary)
        captured_at: When the evidence was captured (UTC)

    Example:
        >>> summary = CLIEvidenceSummary(
        ...     total_commands=5,
        ...     passed=4,
        ...     failed=1,
        ...     results=[...],
        ... )
        >>> summary.passed
        4
    """

    total_commands: int = Field(
        ..., ge=0, description="Total number of commands executed"
    )
    passed: int = Field(
        ..., ge=0, description="Number of commands that succeeded"
    )
    failed: int = Field(
        ..., ge=0, description="Number of commands that failed"
    )
    results: list[CommandResult] = Field(
        default_factory=list, description="Individual command results"
    )
    platform: str = Field(
        default="cli", description="Platform type (always 'cli')"
    )
    captured_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When evidence was captured (UTC)",
    )

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "total_commands": 5,
                "passed": 4,
                "failed": 1,
                "platform": "cli",
                "captured_at": "2026-01-03T10:30:45Z",
                "results": [],
            }
        },
    }
