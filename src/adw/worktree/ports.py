"""Port allocation for concurrent ADW runs.

This module provides the PortAllocator class for deterministically
allocating ports to runs, preventing conflicts between concurrent
executions.
"""

import hashlib
import logging
import socket
from pathlib import Path

from adw.exceptions import PortAllocationError
from adw.models.worktree import PortAllocation

logger = logging.getLogger(__name__)

# Default port ranges
DEFAULT_BACKEND_START = 9100
DEFAULT_FRONTEND_START = 9200
DEFAULT_MAX_CONCURRENT = 15


class PortAllocator:
    """Allocates deterministic ports for concurrent ADW runs.

    Uses a hash of the run_id to calculate a slot number, which then
    determines the backend and frontend ports. If ports are in use,
    it can try alternative slots.

    Attributes:
        backend_start: Starting port number for backend services.
        frontend_start: Starting port number for frontend services.
        max_concurrent: Maximum number of concurrent runs (slot count).

    Example:
        >>> allocator = PortAllocator()
        >>> allocation = allocator.allocate("01HQTEST123456789ABCD")
        >>> allocation.backend_port
        9103
        >>> allocation.frontend_port
        9203
    """

    def __init__(
        self,
        backend_start: int = DEFAULT_BACKEND_START,
        frontend_start: int = DEFAULT_FRONTEND_START,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    ) -> None:
        """Initialize the PortAllocator.

        Args:
            backend_start: Starting port number for backend services.
                Defaults to 9100.
            frontend_start: Starting port number for frontend services.
                Defaults to 9200.
            max_concurrent: Maximum number of concurrent runs.
                Defaults to 15.
        """
        self.backend_start = backend_start
        self.frontend_start = frontend_start
        self.max_concurrent = max_concurrent

    def calculate_slot(self, run_id: str) -> int:
        """Deterministically calculate slot from run_id.

        Uses MD5 hashing to ensure consistent slot assignment across
        Python sessions (unlike Python's built-in hash function).

        Args:
            run_id: The ULID identifier for the run.

        Returns:
            A slot number between 0 and max_concurrent-1.
        """
        hash_int = int(hashlib.md5(run_id.encode()).hexdigest(), 16)
        return hash_int % self.max_concurrent

    def get_ports_for_slot(self, slot: int) -> tuple[int, int]:
        """Get the backend and frontend ports for a given slot.

        Args:
            slot: The slot number (0 to max_concurrent-1).

        Returns:
            A tuple of (backend_port, frontend_port).
        """
        return (self.backend_start + slot, self.frontend_start + slot)

    def is_port_available(self, port: int) -> bool:
        """Check if a port is available for use.

        Uses socket connection test to determine if a port is in use.

        Args:
            port: The port number to check.

        Returns:
            True if the port is available, False if in use.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.1)
            result = sock.connect_ex(("127.0.0.1", port))
            # Non-zero result means connection failed (port is free)
            return result != 0

    def allocate(
        self,
        run_id: str,
        max_attempts: int = 3,
    ) -> PortAllocation:
        """Allocate ports for a run, trying alternative slots if needed.

        Calculates the initial slot from the run_id, then checks if
        the ports are available. If not, tries subsequent slots up to
        max_attempts times.

        Args:
            run_id: The ULID identifier for the run.
            max_attempts: Maximum number of slots to try before failing.
                Defaults to 3.

        Returns:
            A PortAllocation with the assigned slot and ports.

        Raises:
            PortAllocationError: If no available ports found after max_attempts.
        """
        base_slot = self.calculate_slot(run_id)

        for attempt in range(max_attempts):
            slot = (base_slot + attempt) % self.max_concurrent
            backend_port, frontend_port = self.get_ports_for_slot(slot)

            if self.is_port_available(backend_port) and self.is_port_available(
                frontend_port
            ):
                logger.info(
                    "Port allocation successful",
                    extra={
                        "run_id": run_id,
                        "slot": slot,
                        "backend_port": backend_port,
                        "frontend_port": frontend_port,
                        "attempt": attempt + 1,
                    },
                )
                return PortAllocation(
                    slot=slot,
                    backend_port=backend_port,
                    frontend_port=frontend_port,
                    run_id=run_id,
                )

            logger.debug(
                "Slot unavailable, trying next",
                extra={
                    "run_id": run_id,
                    "slot": slot,
                    "backend_port": backend_port,
                    "frontend_port": frontend_port,
                    "attempt": attempt + 1,
                },
            )

        raise PortAllocationError(
            code="PORT_ALLOCATION_FAILED",
            message=f"Could not find available ports after {max_attempts} attempts",
            suggestion="Check for orphaned processes or increase max_concurrent",
            recoverable=False,
        )

    def write_ports_env(
        self,
        allocation: PortAllocation,
        worktree_path: Path,
    ) -> Path:
        """Write .ports.env file to worktree.

        Creates a shell-sourceable environment file containing the
        port allocation variables.

        Args:
            allocation: The port allocation to write.
            worktree_path: Path to the worktree directory.

        Returns:
            Path to the generated .ports.env file.
        """
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

        logger.info(
            "Port environment file written",
            extra={
                "path": str(ports_file),
                "run_id": allocation.run_id,
            },
        )

        return ports_file
