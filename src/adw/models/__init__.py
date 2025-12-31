"""ADW data models - Pydantic models for validation and serialization.

This package contains all Pydantic models used throughout ADW:
- command: ResolvedCommand, LoadedCommand
- context: RunContext, SessionContext, ProjectContext, StateSnapshot
- phase: PhaseStatus, PhaseResult, Artifact, ArtifactType
- config: ProjectConfig, LLMConfig, PhaseConfig, HookConfig
- llm: LLMResult, ToolCall
"""

from adw.models.command import LoadedCommand, ResolvedCommand
from adw.models.config import (
    HookConfig,
    LLMConfig,
    PhaseConfig,
    ProjectConfig,
)
from adw.models.context import (
    ProjectContext,
    RunContext,
    SessionContext,
    StateSnapshot,
)
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

__all__: list[str] = [
    # Command models
    "LoadedCommand",
    "ResolvedCommand",
    # Config models
    "HookConfig",
    "LLMConfig",
    "PhaseConfig",
    "ProjectConfig",
    # Context models
    "ProjectContext",
    "RunContext",
    "SessionContext",
    "StateSnapshot",
    # LLM models
    "LLMResult",
    "ToolCall",
    # Phase models
    "Artifact",
    "ArtifactType",
    "PhaseResult",
    "PhaseStatus",
]
