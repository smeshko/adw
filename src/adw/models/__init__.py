"""ADW data models - Pydantic models for validation and serialization.

This package contains all Pydantic models used throughout ADW:
- artifacts: DiffStats
- command: ResolvedCommand, ValidateCommandConfig, ShipCommandConfig,
           ShipCommandsConfig, DocumentCommandConfig, DocMappingConfig
- context: RunContext, StateSnapshot
- phase: PhaseStatus, PhaseResult
- config: ProjectConfig, LLMConfig, PhaseConfig, HookConfig, GitConfig
- llm: LLMResult, ToolCall
- hook: HookResult
- logging: LogLevel, LogCategory, LogContext, LogEvent
- index: IndexEntry
- pr: PRDescription
- task: TaskInfo
- resume: ResumeInfo, ResumeStatus
- webhook: WebhookConfig, ProviderConfig
- wizard: WizardState
- registry: RegisteredProject, ProjectRegistry
- stats: TokenUsage, ProjectStatistics, GlobalStatistics
"""

from adw.models.artifacts import DiffStats
from adw.models.command import (
    DocMappingConfig,
    DocumentCommandConfig,
    ResolvedCommand,
    ShipCommandConfig,
    ShipCommandsConfig,
    ValidateCommandConfig,
)
from adw.models.config import (
    GitConfig,
    HookConfig,
    LLMConfig,
    PhaseConfig,
    PortRangeConfig,
    ProjectConfig,
    RetryConfig,
    TaskManagerConfig,
    TaskManagerLabelsConfig,
    WorktreeConfig,
)
from adw.models.context import (
    RunContext,
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
    PhaseResult,
    PhaseStatus,
)
from adw.models.pr import PRDescription
from adw.models.registry import ProjectRegistry, RegisteredProject
from adw.models.resume import ResumeInfo, ResumeStatus
from adw.models.stats import GlobalStatistics, ProjectStatistics, TokenUsage
from adw.models.task import TaskInfo
from adw.models.webhook import ProviderConfig, WebhookConfig
from adw.models.wizard import WizardState

# Rebuild models to resolve forward references
# This must happen after all models are imported
# - RunContext references TaskInfo
# - StateSnapshot references PhaseResult
RunContext.model_rebuild()
StateSnapshot.model_rebuild()

__all__: list[str] = [
    # Artifact models
    "DiffStats",
    # Command models
    "DocMappingConfig",
    "DocumentCommandConfig",
    "ResolvedCommand",
    "ShipCommandConfig",
    "ShipCommandsConfig",
    "ValidateCommandConfig",
    # Config models
    "GitConfig",
    "HookConfig",
    "LLMConfig",
    "PhaseConfig",
    "PortRangeConfig",
    "ProjectConfig",
    "RetryConfig",
    "TaskManagerConfig",
    "TaskManagerLabelsConfig",
    "WorktreeConfig",
    # Context models
    "RunContext",
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
    "PhaseResult",
    "PhaseStatus",
    # PR models
    "PRDescription",
    # Registry models
    "ProjectRegistry",
    "RegisteredProject",
    # Statistics models
    "GlobalStatistics",
    "ProjectStatistics",
    "TokenUsage",
    # Resume models
    "ResumeInfo",
    "ResumeStatus",
    # Task models
    "TaskInfo",
    # Webhook models
    "ProviderConfig",
    "WebhookConfig",
    # Wizard models
    "WizardState",
]
