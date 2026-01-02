"""ADW data models - Pydantic models for validation and serialization.

This package contains all Pydantic models used throughout ADW:
- command: ResolvedCommand, LoadedCommand
- context: RunContext, SessionContext, ProjectContext, StateSnapshot
- phase: PhaseStatus, PhaseResult, Artifact, ArtifactType
- config: ProjectConfig, LLMConfig, PhaseConfig, HookConfig
- llm: LLMResult, ToolCall
- hook: HookResult
"""

from adw.models.command import LoadedCommand, ResolvedCommand
from adw.models.config import (
    HookConfig,
    LLMConfig,
    PhaseConfig,
    ProjectConfig,
    RetryConfig,
)
from adw.models.context import (
    ProjectContext,
    RunContext,
    SessionContext,
    StateSnapshot,
)
from adw.models.hook import HookResult
from adw.models.llm import (
    LLMResult,
    ToolCall,
)
from adw.models.phase import (
    Artifact,
    ArtifactType,
    PhaseResult,
    PhaseStatus,
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
    "ProjectConfig",
    "RetryConfig",
    # Context models
    "ProjectContext",
    "RunContext",
    "SessionContext",
    "StateSnapshot",
    # Hook models
    "HookResult",
    # LLM models
    "LLMResult",
    "ToolCall",
    # Phase models
    "Artifact",
    "ArtifactType",
    "PhaseResult",
    "PhaseStatus",
]
