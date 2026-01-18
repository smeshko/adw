# Data Models Documentation

## Project: ADW SDK (adw)

**Generated:** 2026-01-18
**Project Type:** Backend + CLI
**Validation Framework:** Pydantic v2

---

## Model Categories

The ADW SDK uses Pydantic models extensively organized into the following categories:

### 1. Configuration Models (`models/config.py`)

| Model | Description |
|-------|-------------|
| `RetryConfig` | Retry behavior with exponential backoff |
| `LLMConfig` | LLM execution settings |
| `PhaseConfig` | Phase-specific configuration |
| `HookConfig` | Git and shell hook settings |
| `PipelineConfig` | Phase pipeline configuration |
| `RedactionConfig` | Secret redaction settings |
| `LoggingConfig` | Logging behavior configuration |
| `PortRangeConfig` | Port allocation for worktrees |
| `WorktreeConfig` | Git worktree isolation settings |
| `TaskManagerLabelsConfig` | Label-based task filtering |
| `TaskManagerConfig` | External task manager integration |
| `GitConfig` | Git integration settings |
| `ProjectConfig` | Main project configuration |

### 2. Context Models (`models/context.py`)

| Model | Description |
|-------|-------------|
| `RunContext` | State for a single workflow run |
| `SessionContext` | Session-level context |
| `ProjectContext` | Project-wide context |
| `StateSnapshot` | Point-in-time state capture |

### 3. Webhook Models (`models/webhook.py`)

| Model | Description |
|-------|-------------|
| `ProviderConfig` | Webhook provider configuration |
| `WebhookConfig` | Main webhook configuration |
| `WebhookEvent` | Parsed webhook event |
| `RunParams` | Parameters for triggering a run |
| `EventTriggerConfig` | Event-to-run trigger rules |
| `ProviderEventMapping` | Provider-specific event mappings |
| `WebhookMappings` | All webhook mapping rules |
| `MappingEvaluationResult` | Result of event evaluation |
| `GitHubUser` | GitHub user model |
| `GitHubLabel` | GitHub label model |
| `GitHubIssue` | GitHub issue model |
| `GitHubComment` | GitHub comment model |
| `GitHubPullRequest` | GitHub PR model |
| `GitHubRepository` | GitHub repository model |
| `GitHubEvent` | GitHub webhook event |
| `LinearLabel` | Linear label model |
| `LinearState` | Linear state model |
| `LinearAssignee` | Linear assignee model |
| `LinearIssue` | Linear issue model |
| `LinearComment` | Linear comment model |
| `LinearEvent` | Linear webhook event |

### 4. Command Models (`models/command.py`)

| Model | Description |
|-------|-------------|
| `PhaseLLMConfig` | Per-phase LLM settings |
| `ArtifactConfig` | Artifact capture configuration |
| `CommandConfig` | Command definition from YAML |
| `ResolvedCommand` | Fully resolved command |
| `LoadedCommand` | Command with loaded templates |

### 5. Logging Models (`models/logging.py`)

| Model | Description |
|-------|-------------|
| `LogContext` | Contextual logging metadata |
| `LogEvent` | Structured log event |
| `LLMStats` | Token usage statistics |
| `LLMToolCall` | Captured tool call |
| `LLMToolResult` | Captured tool result |
| `LLMRequest` | LLM request capture |
| `LLMResponse` | LLM response capture |
| `LLMStreamEvent` | Streaming event capture |

### 6. Phase Models (`models/phase.py`)

| Model | Description |
|-------|-------------|
| `Artifact` | Generated artifact metadata |
| `PhaseResult` | Phase execution result |

### 7. Security Models (`models/security.py`)

| Model | Description |
|-------|-------------|
| `BlockedPattern` | Dangerous command pattern |
| `SecurityConfig` | Security settings |
| `ToolCallLog` | Security-audited tool call |

### 8. Other Models

| File | Model | Description |
|------|-------|-------------|
| `models/artifacts.py` | `DiffStats` | Git diff statistics |
| `models/worktree.py` | `PortAllocation` | Allocated port for worktree |
| `models/pr.py` | `PRDescription` | Pull request description |
| `models/llm.py` | `ToolCall`, `LLMResult` | LLM interaction models |
| `models/hook.py` | `HookResult` | Hook execution result |
| `models/task.py` | `TaskInfo` | External task metadata |
| `models/index.py` | `IndexEntry` | Run index entry |
| `models/resume.py` | Various | Resume-related models |

---

## Key Model Details

### ProjectConfig (Main Configuration)

```python
class ProjectConfig(BaseModel):
    name: str
    language: str
    framework: str | None
    platform: str | None
    test_command: str | None
    build_command: str | None
    llm: LLMConfig
    phases: dict[str, PhaseConfig]
    git: GitConfig
    worktree: WorktreeConfig
    task_manager: TaskManagerConfig
    validation: dict
    logging: LoggingConfig
    security: SecurityConfig
    webhook: WebhookConfig
```

### RunContext (Run State)

```python
class RunContext(BaseModel):
    run_id: str
    command_name: str
    feature_request: str
    current_phase: str
    phase_index: int
    completed_phases: list[str]
    artifacts: dict[str, Any]
    start_time: datetime
    status: str
```

### WebhookEvent (Webhook Payload)

```python
class WebhookEvent(BaseModel):
    provider: str
    event_type: str
    payload: dict[str, Any]
    headers: dict[str, str]
    received_at: datetime
```

---

## Model Relationships

```
ProjectConfig
├── LLMConfig
├── PhaseConfig (per phase)
├── GitConfig
├── WorktreeConfig
│   └── PortRangeConfig
├── TaskManagerConfig
│   └── TaskManagerLabelsConfig
├── LoggingConfig
│   └── RedactionConfig
├── SecurityConfig
└── WebhookConfig
    ├── ProviderConfig
    └── WebhookMappings
        └── ProviderEventMapping
            └── EventTriggerConfig

RunContext
├── StateSnapshot
├── PhaseResult
│   └── Artifact
└── SessionContext
```

---

## Validation Rules

All models use Pydantic v2 with strict validation:

- **Required fields**: Enforced at parse time
- **Type coercion**: Minimal, prefer explicit types
- **Field validators**: Custom validators for complex rules
- **Model validators**: Cross-field validation

---

## Serialization

Models support JSON serialization with:

- `model_dump()`: Convert to dict
- `model_dump_json()`: Convert to JSON string
- `model_validate()`: Parse from dict
- `model_validate_json()`: Parse from JSON string
