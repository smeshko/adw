# Story 12.7: Label Management

Status: ready-for-dev
Linear Issue: pending
Epic: 12 - Task Manager Integration
Created: 2026-01-05

---

## Story

As a user,
I want ADW to manage task labels based on run state,
So that my task board reflects current progress.

## Acceptance Criteria

**Given** a run starts
**When** orchestrator initializes
**Then** label `adw:running` is added to the task

**Given** a phase starts
**When** phase runner begins
**Then** label `adw:phase:{phase_name}` is added (e.g., `adw:phase:build`)

**Given** a phase completes
**When** moving to next phase
**Then** previous phase label is removed, new phase label is added

**Given** a run completes successfully
**When** all phases done
**Then** `adw:running` removed, `adw:completed` added

**Given** a run fails
**When** error occurs
**Then** `adw:running` removed, `adw:failed` added, phase label remains

**Given** label configuration
**When** `labels.enabled: false` in config
**Then** no label operations are performed

## Tasks / Subtasks

- [ ] **Task 1**: Add `update_labels` method to TaskManagerProtocol
  - [ ] Define `update_labels(task_id: str, add: list[str], remove: list[str]) -> None`
  - [ ] Mark as optional capability
  - [ ] Add no-op to NullTaskManager

- [ ] **Task 2**: Implement `update_labels` in LinearTaskManager
  - [ ] Query existing labels on issue
  - [ ] Calculate new label set (existing + add - remove)
  - [ ] Use Linear `issueUpdate` mutation with labelIds

- [ ] **Task 3**: Create label management service
  - [ ] Handle ADW label prefix (configurable, default: `adw:`)
  - [ ] Track current phase label for removal on transition
  - [ ] Manage lifecycle labels: running, completed, failed

- [ ] **Task 4**: Integrate with Orchestrator lifecycle
  - [ ] Add labels at run start: `adw:running`
  - [ ] Update phase label at each transition
  - [ ] Update lifecycle label at completion/failure

- [ ] **Task 5**: Ensure labels exist in Linear team
  - [ ] Check if ADW labels exist before using
  - [ ] Auto-create labels if missing (optional config)
  - [ ] Use consistent colors: green=running, blue=phase, red=failed, purple=completed

- [ ] **Task 6**: Write unit tests
  - [ ] Test label add/remove operations
  - [ ] Test phase transition label swapping
  - [ ] Test lifecycle label management
  - [ ] Test disabled label config

---

## Developer Context

### Technical Requirements

This story adds visual progress indicators on task boards through dynamic label management. Labels provide at-a-glance status without opening the task.

**Key Design Decisions:**
- Prefix isolation: All ADW labels use configurable prefix (default: `adw:`)
- Label lifecycle: running → phase:X → completed/failed
- Auto-create: Optionally create missing labels

### Architecture Compliance

**Modified Files:**
```
src/adw/task_managers/
├── protocol.py    # Add update_labels method
├── linear.py      # Implement update_labels
src/adw/core/
├── orchestrator.py # Add label management hooks
```

**New Files:**
```
src/adw/task_managers/
├── label_manager.py # Label management logic
```

### Library & Framework Requirements

No new dependencies.

### File Structure Requirements

**Modified Files:**
- `src/adw/task_managers/protocol.py` - Add update_labels
- `src/adw/task_managers/linear.py` - Implement update_labels
- `src/adw/core/orchestrator.py` - Add label hooks
- `src/adw/models/config.py` - Add labels config section

**New Files:**
- `src/adw/task_managers/label_manager.py`
- `tests/unit/task_managers/test_labels.py`

### Testing Requirements

```python
def test_add_running_label_on_start(mock_task_manager):
    """adw:running label added when run starts."""
    label_manager = LabelManager(
        task_manager=mock_task_manager,
        config=LabelConfig(enabled=True, prefix="adw:")
    )
    label_manager.on_run_start("RULE-123")

    mock_task_manager.update_labels.assert_called_with(
        "RULE-123",
        add=["adw:running"],
        remove=[]
    )

def test_phase_label_swap_on_transition(mock_task_manager):
    """Phase label swapped when transitioning phases."""
    label_manager = LabelManager(
        task_manager=mock_task_manager,
        config=LabelConfig(enabled=True, prefix="adw:")
    )
    label_manager.current_phase_label = "adw:phase:plan"
    label_manager.on_phase_start("RULE-123", "build")

    mock_task_manager.update_labels.assert_called_with(
        "RULE-123",
        add=["adw:phase:build"],
        remove=["adw:phase:plan"]
    )

def test_labels_disabled(mock_task_manager):
    """No label operations when labels.enabled is false."""
    label_manager = LabelManager(
        task_manager=mock_task_manager,
        config=LabelConfig(enabled=False)
    )
    label_manager.on_run_start("RULE-123")

    mock_task_manager.update_labels.assert_not_called()
```

---

## Previous Story Intelligence

**From Story 12.3:**
- Orchestrator has lifecycle hooks
- Non-blocking pattern for task manager calls

---

## Latest Technical Information

### Linear Label Management

Labels in Linear are team-specific and require label IDs. To update labels:

1. Query existing issue labels
2. Query team labels to get IDs
3. Calculate new label set
4. Update issue with label IDs

```graphql
# Get issue labels
query GetIssueLabels($id: String!) {
  issue(id: $id) {
    labels {
      nodes { id, name }
    }
  }
}

# Get team labels
query TeamLabels($teamId: String!) {
  team(id: $teamId) {
    labels {
      nodes { id, name }
    }
  }
}

# Create label if missing
mutation LabelCreate($input: IssueLabelCreateInput!) {
  issueLabelCreate(input: $input) {
    success
    issueLabel { id, name }
  }
}

# Update issue labels
mutation IssueUpdate($id: String!, $input: IssueUpdateInput!) {
  issueUpdate(id: $id, input: $input) {
    success
  }
}
```

Input for label update:
```json
{
  "id": "issue-id",
  "input": {
    "labelIds": ["label-id-1", "label-id-2"]
  }
}
```

### ADW Label Scheme

| Label | When Applied | When Removed | Color |
|-------|--------------|--------------|-------|
| `adw:running` | Run starts | Run completes/fails | 🟢 Green |
| `adw:phase:{name}` | Phase starts | Next phase starts | 🔵 Blue |
| `adw:completed` | Run succeeds | - | 🟣 Purple |
| `adw:failed` | Run fails | - | 🔴 Red |
| `adw:pr-ready` | PR created | PR merged | 🟡 Yellow |

---

## Project Context Reference

See: `_bmad-output/project-context.md`

---

## Dev Notes

### Configuration Example

```yaml
task_manager_config:
  labels:
    enabled: true          # Enable label management
    prefix: "adw:"         # Label prefix
    auto_create: true      # Create labels if missing
```

### References

- [Source: _bmad-output/epics/epic-12-task-manager-integration.md#Story 12.7]
- [Source: ~/.claude/skills/linear/references/graphql_reference.md]

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### File List

---

## Dependencies

- **Depends On:** Story 12.1, Story 12.2
- **Blocks:** Story 12.10
- **Can Parallel With:** Story 12.3, Story 12.5, Story 12.6, Story 12.8, Story 12.9

### Dependency Rationale
- Story 12.1: Requires TaskManagerProtocol with update_labels method
- Story 12.2: Requires LinearTaskManager to implement label API
- Story 12.10: GitHub Issues uses label patterns from this story

