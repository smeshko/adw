"""ADW data models - Pydantic models for validation and serialization.

This package contains all Pydantic models used throughout ADW:
- command: ResolvedCommand, LoadedCommand
- context: RunContext, SessionContext, ProjectContext, StateSnapshot
- phase: PhaseStatus, PhaseResult, Artifact, ArtifactType
- config: ProjectConfig, LLMConfig, PhaseConfig, HookConfig, PipelineConfig
- llm: LLMResult, ToolCall
- hook: HookResult
- logging: LogLevel, LogCategory, LogContext, LogEvent
- index: IndexEntry
- security: BlockedPattern, SecurityConfig, ToolCallLog
- evidence: PlatformType, Confidence, EvidenceStrategy, PlatformDetectionResult,
            APIRequest, APIResponse, APIEvidenceResult, APIEvidenceSummary,
            EndpointConfig, AuthConfig, AuthType,
            RouteConfig, ViewportConfig, ScreenshotResult, WebEvidenceSummary,
            CommandConfig, CommandResult, CLIEvidenceSummary
"""

from adw.models.command import LoadedCommand, ResolvedCommand
from adw.models.config import (
    HookConfig,
    LLMConfig,
    PhaseConfig,
    PipelineConfig,
    ProjectConfig,
    RetryConfig,
)
from adw.models.context import (
    ProjectContext,
    RunContext,
    SessionContext,
    StateSnapshot,
)
from adw.models.evidence import (
    APIEvidenceResult,
    APIEvidenceSummary,
    APIRequest,
    APIResponse,
    AuthConfig,
    AuthType,
    CLIEvidenceSummary,
    CommandConfig,
    CommandResult,
    Confidence,
    EndpointConfig,
    EvidenceStrategy,
    PlatformDetectionResult,
    PlatformType,
    RouteConfig,
    ScreenshotResult,
    ViewportConfig,
    WebEvidenceSummary,
)
from adw.models.hook import HookResult
from adw.models.index import IndexEntry
from adw.models.llm import (
    LLMResult,
    ToolCall,
)
from adw.models.logging import (
    LogCategory,
    LogContext,
    LogEvent,
    LogLevel,
)
from adw.models.phase import (
    Artifact,
    ArtifactType,
    PhaseResult,
    PhaseStatus,
)
from adw.models.security import (
    BlockedPattern,
    SecurityConfig,
    ToolCallLog,
)

# Rebuild StateSnapshot to resolve forward references to PhaseResult
# This must happen after all models are imported
StateSnapshot.model_rebuild()

__all__: list[str] = [
    # Command models
    "LoadedCommand",
    "ResolvedCommand",
    # Config models
    "HookConfig",
    "LLMConfig",
    "PhaseConfig",
    "PipelineConfig",
    "ProjectConfig",
    "RetryConfig",
    # Context models
    "ProjectContext",
    "RunContext",
    "SessionContext",
    "StateSnapshot",
    # Evidence models - API
    "APIEvidenceResult",
    "APIEvidenceSummary",
    "APIRequest",
    "APIResponse",
    "AuthConfig",
    "AuthType",
    "EndpointConfig",
    # Evidence models - CLI
    "CLIEvidenceSummary",
    "CommandConfig",
    "CommandResult",
    # Evidence models - Web
    "RouteConfig",
    "ScreenshotResult",
    "ViewportConfig",
    "WebEvidenceSummary",
    # Evidence models - Common
    "Confidence",
    "EvidenceStrategy",
    "PlatformDetectionResult",
    "PlatformType",
    # Hook models
    "HookResult",
    # Index models
    "IndexEntry",
    # LLM models
    "LLMResult",
    "ToolCall",
    # Logging models
    "LogCategory",
    "LogContext",
    "LogEvent",
    "LogLevel",
    # Phase models
    "Artifact",
    "ArtifactType",
    "PhaseResult",
    "PhaseStatus",
    # Security models
    "BlockedPattern",
    "SecurityConfig",
    "ToolCallLog",
]
