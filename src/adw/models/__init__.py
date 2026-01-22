"""ADW data models - Pydantic models for validation and serialization.

This package contains all Pydantic models used throughout ADW:
- artifacts: DiffStats
- command: ResolvedCommand, LoadedCommand, ValidateCommandConfig, ShipCommandConfig,
           ShipCommandsConfig, ShipPRConfig, DocumentCommandConfig, DocMappingConfig
- context: RunContext, SessionContext, ProjectContext, StateSnapshot
- phase: PhaseStatus, PhaseResult, Artifact, ArtifactType
- config: ProjectConfig, LLMConfig, PhaseConfig, HookConfig, PipelineConfig, GitConfig
- llm: LLMResult, ToolCall
- hook: HookResult
- logging: LogLevel, LogCategory, LogContext, LogEvent
- index: IndexEntry
- security: BlockedPattern, SecurityConfig, ToolCallLog
- pr: PRDescription
- validation: ValidationResult
- task: TaskInfo
- resume: ResumeInfo, ResumeStatus
- webhook: WebhookConfig, ProviderConfig
- wizard: WizardState
"""

from adw.models.artifacts import DiffStats
from adw.models.command import (
    DocMappingConfig,
    DocumentCommandConfig,
    LoadedCommand,
    ResolvedCommand,
    ShipCommandConfig,
    ShipCommandsConfig,
    ShipPRConfig,
    ValidateCommandConfig,
)
from adw.models.config import (
    GitConfig,
    HookConfig,
    LLMConfig,
    PhaseConfig,
    PipelineConfig,
    PortRangeConfig,
    ProjectConfig,
    RetryConfig,
    TaskManagerConfig,
    TaskManagerLabelsConfig,
    WorktreeConfig,
)
from adw.models.context import (
    ProjectContext,
    RunContext,
    SessionContext,
    StateSnapshot,
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
from adw.models.resume import ResumeInfo, ResumeStatus
from adw.models.security import (
    BlockedPattern,
    SecurityConfig,
    ToolCallLog,
)
from adw.models.task import TaskInfo
from adw.models.webhook import ProviderConfig, WebhookConfig
from adw.models.wizard import WizardState
from adw.models.worktree import PortAllocation
from adw.validation.models import ValidationResult

# Rebuild models to resolve forward references
# This must happen after all models are imported
# - RunContext references TaskInfo (Story 12.3)
# - StateSnapshot references PhaseResult
RunContext.model_rebuild()
StateSnapshot.model_rebuild()

__all__: list[str] = [
    # Artifact models
    "DiffStats",
    # Command models
    "DocMappingConfig",
    "DocumentCommandConfig",
    "LoadedCommand",
    "ResolvedCommand",
    "ShipCommandConfig",
    "ShipCommandsConfig",
    "ShipPRConfig",
    "ValidateCommandConfig",
    # Config models
    "GitConfig",
    "HookConfig",
    "LLMConfig",
    "PhaseConfig",
    "PipelineConfig",
    "PortRangeConfig",
    "ProjectConfig",
    "RetryConfig",
    "TaskManagerConfig",
    "TaskManagerLabelsConfig",
    "WorktreeConfig",
    # Context models
    "ProjectContext",
    "RunContext",
    "SessionContext",
    "StateSnapshot",
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
    # Resume models
    "ResumeInfo",
    "ResumeStatus",
    # Security models
    "BlockedPattern",
    "SecurityConfig",
    "ToolCallLog",
    # Task models
    "TaskInfo",
    # Webhook models
    "ProviderConfig",
    "WebhookConfig",
    # Wizard models
    "WizardState",
    # Worktree models
    "PortAllocation",
    # Validation models
    "ValidationResult",
]
