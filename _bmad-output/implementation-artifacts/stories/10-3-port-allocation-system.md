# Story 10.3: Port Allocation System

Status: ready-for-dev
Linear Issue: not-configured
Epic: 10 - Worktree Isolation
Created: 2026-01-05

---

## Story

As a developer,
I want deterministic port allocation per run,
so that concurrent runs don't have port conflicts.

## Acceptance Criteria

**Given** a run with slot number N (0-14)
**When** ports are allocated
**Then** backend port = 9100 + N, frontend port = 9200 + N

**Given** run starts
**When** slot is assigned
**Then** slot is determined by hashing run_id modulo 15

**Given** port allocation
**When** `.ports.env` is generated
**Then** it contains: `BACKEND_PORT=91XX`, `FRONTEND_PORT=92XX`

**Given** a phase needs ports
**When** environment is set up
**Then** `.ports.env` is sourced or variables are injected

**Given** port is already in use
**When** allocation occurs
**Then** next available slot is tried (up to 3 attempts)

## Tasks / Subtasks

### Task 1: Create PortAllocator Class
- [x] Create `src/adw/worktree/ports.py` with `PortAllocator` class
- [x] Implement slot calculation: `hash(run_id) % 15`
- [x] Implement port calculation: `backend = 9100 + slot`, `frontend = 9200 + slot`
- [x] Add method `allocate(run_id: str) -> PortAllocation`

### Task 2: Implement Port Availability Check
- [x] Add `is_port_available(port: int) -> bool` using socket connection test
- [x] Add `find_available_slot(run_id: str, max_attempts: int = 3) -> int`
- [x] Start from calculated slot, try next slots if occupied
- [x] Raise `PortAllocationError` if no slots available after max_attempts

### Task 3: Create PortAllocation Model
- [x] Add `PortAllocation` model to `src/adw/models/worktree.py`:
  ```python
  class PortAllocation(BaseModel):
      slot: int
      backend_port: int
      frontend_port: int
      run_id: str
  ```

### Task 4: Implement .ports.env Generation
- [x] Add `write_ports_env(allocation: PortAllocation, worktree_path: Path) -> Path`
- [x] Generate `.ports.env` file in worktree root:
  ```
  BACKEND_PORT=9100
  FRONTEND_PORT=9200
  ADW_SLOT=0
  ADW_RUN_ID=01HQXK5...
  ```
- [x] Return path to generated file

### Task 5: Add Port Configuration
- [x] Extend `WorktreeConfig` with port settings:
  ```python
  port_range:
      backend_start: int = 9100
      frontend_start: int = 9200
  max_concurrent: int = 15
  ```

### Task 6: Integrate with Hook Environment
- [ ] Modify `hooks/environment.py` to include port variables
- [ ] Source `.ports.env` in hook execution or inject directly
- [ ] Add `ADW_BACKEND_PORT`, `ADW_FRONTEND_PORT` to hook environment

### Task 7: Write Tests
- [ ] Test slot calculation is deterministic for same run_id
- [ ] Test port availability checking
- [ ] Test fallback to next slot when port in use
- [ ] Test .ports.env file generation
- [ ] Test integration with hook environment

---

## Dependencies

**Depends On:**
- 10-1: Worktree Creation and Lifecycle (needs worktree to write .ports.env)

**Blocks:**
- 10-4: Concurrent Run Management (needs port allocation to prevent conflicts)

**Can Parallel With:**
- 10-2: Worktree Directory Structure
- 10-6: Worktree Branch Management

---

## Developer Context

### Technical Requirements

1. **Port Checking**
   - Use socket to test if port is in use
   - Handle both TCP and UDP if needed (TCP sufficient for most cases)
   - Quick timeout to avoid blocking

2. **Slot Calculation**
   - Use consistent hash function (Python's hash is session-specific!)
   - Recommend: `int(hashlib.md5(run_id.encode()).hexdigest(), 16) % max_slots`
   - This ensures same run_id always gets same initial slot

3. **Environment File Format**
   - Use shell-compatible format (KEY=VALUE, no spaces)
   - One variable per line
   - Include comments for clarity

### Architecture Compliance

**New Files:**
```
src/adw/
├── worktree/
│   ├── __init__.py
│   ├── manager.py      # From Story 10-1
│   └── ports.py        # NEW: PortAllocator class
└── models/
    └── worktree.py     # NEW: PortAllocation model
```

**PortAllocator Implementation:**
```python
# src/adw/worktree/ports.py
import hashlib
import socket
from pathlib import Path

from adw.models.worktree import PortAllocation
from adw.models.config import WorktreeConfig
from adw.exceptions import PortAllocationError


class PortAllocator:
    def __init__(self, config: WorktreeConfig):
        self.config = config
        self.backend_start = config.port_range.backend_start
        self.frontend_start = config.port_range.frontend_start
        self.max_slots = config.max_concurrent

    def calculate_slot(self, run_id: str) -> int:
        """Deterministically calculate slot from run_id."""
        hash_int = int(hashlib.md5(run_id.encode()).hexdigest(), 16)
        return hash_int % self.max_slots

    def is_port_available(self, port: int) -> bool:
        """Check if a port is available for use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.1)
            result = sock.connect_ex(("127.0.0.1", port))
            return result != 0  # Non-zero means connection failed (port free)

    def allocate(self, run_id: str, max_attempts: int = 3) -> PortAllocation:
        """Allocate ports for a run, trying alternative slots if needed."""
        base_slot = self.calculate_slot(run_id)

        for attempt in range(max_attempts):
            slot = (base_slot + attempt) % self.max_slots
            backend_port = self.backend_start + slot
            frontend_port = self.frontend_start + slot

            if self.is_port_available(backend_port) and self.is_port_available(frontend_port):
                return PortAllocation(
                    slot=slot,
                    backend_port=backend_port,
                    frontend_port=frontend_port,
                    run_id=run_id,
                )

        raise PortAllocationError(
            code="PORT_ALLOCATION_FAILED",
            message=f"Could not find available ports after {max_attempts} attempts",
            suggestion="Check for orphaned processes or increase max_concurrent",
            recoverable=False,
        )

    def write_ports_env(self, allocation: PortAllocation, worktree_path: Path) -> Path:
        """Write .ports.env file to worktree."""
        ports_file = worktree_path / ".ports.env"
        content = f"""\
# ADW Port Allocation
# Generated for run: {allocation.run_id}
BACKEND_PORT={allocation.backend_port}
FRONTEND_PORT={allocation.frontend_port}
ADW_SLOT={allocation.slot}
ADW_RUN_ID={allocation.run_id}
"""
        ports_file.write_text(content)
        return ports_file
```

### Library & Framework Requirements

| Library | Version | Purpose |
|---------|---------|---------|
| socket | stdlib | Port availability checking |
| hashlib | stdlib | Deterministic slot calculation |
| pathlib | stdlib | File operations |

### File Structure Requirements

**New Files:**
- `src/adw/worktree/ports.py` - PortAllocator class
- `src/adw/models/worktree.py` - PortAllocation model

**Modified Files:**
- `src/adw/models/config.py` - Add PortRangeConfig to WorktreeConfig
- `src/adw/hooks/environment.py` - Add port variables to hook env
- `src/adw/worktree/__init__.py` - Export PortAllocator

**Test Files:**
- `tests/unit/worktree/test_ports.py`

### Testing Requirements

**Unit Tests:**
```python
# tests/unit/worktree/test_ports.py
class TestSlotCalculation:
    def test_same_run_id_same_slot(self):
        """Same run_id always produces same slot."""
        allocator = PortAllocator(default_config)
        slot1 = allocator.calculate_slot("01HQTEST")
        slot2 = allocator.calculate_slot("01HQTEST")
        assert slot1 == slot2

    def test_different_run_ids_different_slots_usually(self):
        """Different run_ids usually produce different slots."""
        # Test with 100 different run_ids, expect reasonable distribution


class TestPortAvailability:
    def test_available_port_returns_true(self):
        """Unused port returns True."""

    def test_used_port_returns_false(self, listening_server):
        """Port with active listener returns False."""


class TestAllocation:
    def test_allocate_returns_valid_ports(self):
        """Allocation returns ports in valid range."""

    def test_allocate_retries_on_conflict(self, mock_used_ports):
        """Tries next slot when port is in use."""

    def test_allocate_raises_after_max_attempts(self, mock_all_ports_used):
        """Raises PortAllocationError when all attempts exhausted."""


class TestPortsEnv:
    def test_writes_correct_format(self, tmp_path):
        """Generated .ports.env has correct content."""

    def test_file_is_shell_sourceable(self, tmp_path):
        """File can be sourced by shell."""
```

**Test Fixtures:**
```python
@pytest.fixture
def listening_server():
    """Create a server listening on a known port for testing."""
    import threading
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 19999))
    server.listen(1)
    yield 19999
    server.close()
```

---

## Previous Story Intelligence

**From Story 10-1:**
- WorktreeManager class provides worktree paths
- Worktree creation happens before port allocation needed

---

## Git Intelligence

**Relevant Patterns:**
- Environment variable handling from `hooks/environment.py`
- Configuration patterns from `models/config.py`

---

## Latest Technical Information

**Port Checking Best Practices:**
- `socket.connect_ex()` is more reliable than trying to bind
- Short timeout (0.1s) prevents blocking
- Check both backend and frontend ports before accepting slot

**Considerations:**
- Ports 9100-9114 and 9200-9214 should be above privileged range
- Some systems may have these ports in use (check common services)
- Consider making port ranges configurable per-project

---

## Project Context Reference

See: `_bmad-output/project-context.md`

Key patterns:
- **Exception hierarchy**: Create `PortAllocationError` extending `ADWError`
- **Pydantic models**: `PortAllocation` in `models/worktree.py`
- **Structured logging**: Log port allocation decisions

---

## Dev Notes

### Port Allocation Table

| Slot | Backend Port | Frontend Port |
|------|--------------|---------------|
| 0    | 9100         | 9200          |
| 1    | 9101         | 9201          |
| 2    | 9102         | 9202          |
| ...  | ...          | ...           |
| 14   | 9114         | 9214          |

### Exception to Add

```python
# src/adw/exceptions.py
class PortAllocationError(ADWError):
    """Raised when port allocation fails."""
    pass
```

### Integration Points

- Called from `WorktreeManager.create_worktree()` after worktree exists
- `.ports.env` written to worktree root
- Hook environment reads `.ports.env` or gets vars injected

### References

- [Source: _bmad-output/epics/epic-10-worktree-isolation.md#Story 10.3]
- [Source: _bmad-output/architecture.md#Hook Execution Environment]

---

## Dev Agent Record

### Context Reference

Epic 10: Worktree Isolation - Story 10.3

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

N/A

### Completion Notes List

- Tasks 1-4 implemented together as they are interdependent
- Created PortAllocator class in src/adw/worktree/ports.py
- Created PortAllocation Pydantic model in src/adw/models/worktree.py
- Added PortAllocationError exception to src/adw/exceptions.py
- Implemented MD5-based deterministic slot calculation (not Python hash)
- Implemented is_port_available() using socket.connect_ex() with 0.1s timeout
- Implemented allocate() with retry logic for occupied ports
- Implemented write_ports_env() for shell-sourceable environment files
- Added unit tests covering slot calculation, port calculation, and allocation
- Task 5: Added PortRangeConfig and extended WorktreeConfig with port_range and max_concurrent fields

### File List

**New Files:**
- src/adw/worktree/ports.py
- src/adw/models/worktree.py
- tests/unit/worktree/test_ports.py

**Modified Files:**
- src/adw/worktree/__init__.py
- src/adw/models/__init__.py
- src/adw/models/config.py
- src/adw/exceptions.py
- tests/unit/models/test_config.py
