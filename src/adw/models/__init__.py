"""ADW data models - Pydantic models for validation and serialization.

This package contains all Pydantic models used throughout ADW:
- artifacts: DiffStats
- command: ResolvedCommand, LoadedCommand
- context: RunContext, SessionContext, ProjectContext, StateSnapshot
- phase: PhaseStatus, PhaseResult, Artifact, ArtifactType
- config: ProjectConfig, LLMConfig, PhaseConfig, HookConfig, PipelineConfig, GitConfig
- llm: LLMResult, ToolCall
- hook: HookResult
- logging: LogLevel, LogCategory, LogContext, LogEvent
- index: IndexEntry
- security: BlockedPattern, SecurityConfig, ToolCallLog
- evidence: PlatformType, Confidence, EvidenceStrategy, PlatformDetectionResult,
            APIRequest, APIResponse, APIEvidenceResult, APIEvidenceSummary,
            EndpointConfig, AuthConfig, AuthType,
            CommandConfig, CommandResult, CLIEvidenceSummary,
            RouteConfig, ViewportConfig, ScreenshotResult, WebEvidenceSummary,
            MobileDeviceType, MobileScreenConfig, MobileScreenshotResult, MobileEvidenceSummary,
            EvidenceType, EvidenceStatus, EvidenceItem, PlanStepCoverage,
            CoverageSummary, EvidenceManifest,
            OptimizationConfig, FileOptimization, OptimizationReport
- pr: PRDescription
- validation: ValidationIssue, ValidationResult, IssueSource, IssueSeverity,
              IssueLocation, IssueContext, FixAttempt, FixResult
"""

from adw.models.artifacts import DiffStats
from adw.models.command import LoadedCommand, ResolvedCommand
from adw.models.config import (
    GitConfig,
    HookConfig,
    LLMConfig,
    PhaseConfig,
    PipelineConfig,
    PortRangeConfig,
    ProjectConfig,
    RetryConfig,
    WorktreeConfig,
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
    CoverageSummary,
    EndpointConfig,
    EvidenceItem,
    EvidenceManifest,
    EvidenceStatus,
    EvidenceStrategy,
    EvidenceType,
    FileOptimization,
    MobileDeviceType,
    MobileEvidenceSummary,
    MobileScreenConfig,
    MobileScreenshotResult,
    OptimizationConfig,
    OptimizationReport,
    PlanStepCoverage,
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
from adw.models.pr import PRDescription
from adw.models.security import (
    BlockedPattern,
    SecurityConfig,
    ToolCallLog,
)
from adw.models.worktree import PortAllocation
from adw.validation.models import (
    FixAttempt,
    FixResult,
    IssueContext,
    IssueLocation,
    IssueSeverity,
    IssueSource,
    ValidationIssue,
    ValidationResult,
)

# Rebuild StateSnapshot to resolve forward references to PhaseResult
# This must happen after all models are imported
StateSnapshot.model_rebuild()

__all__: list[str] = [
    # Artifact models
    "DiffStats",
    # Command models
    "LoadedCommand",
    "ResolvedCommand",
    # Config models
    "GitConfig",
    "HookConfig",
    "LLMConfig",
    "PhaseConfig",
    "PipelineConfig",
    "PortRangeConfig",
    "ProjectConfig",
    "RetryConfig",
    "WorktreeConfig",
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
    # Evidence models - Manifest
    "CoverageSummary",
    "EvidenceItem",
    "EvidenceManifest",
    "EvidenceStatus",
    "EvidenceType",
    "PlanStepCoverage",
    # Evidence models - Optimization
    "FileOptimization",
    "OptimizationConfig",
    "OptimizationReport",
    # Evidence models - Mobile
    "MobileDeviceType",
    "MobileEvidenceSummary",
    "MobileScreenConfig",
    "MobileScreenshotResult",
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
    # PR models
    "PRDescription",
    # Security models
    "BlockedPattern",
    "SecurityConfig",
    "ToolCallLog",
    # Worktree models
    "PortAllocation",
    # Validation models
    "FixAttempt",
    "FixResult",
    "IssueContext",
    "IssueLocation",
    "IssueSeverity",
    "IssueSource",
    "ValidationIssue",
    "ValidationResult",
]
