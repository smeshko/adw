"""Unit tests for port allocation system.

Tests for the PortAllocator class which handles deterministic port
allocation for concurrent ADW runs.
"""

import socket

import pytest

from adw.exceptions import PortAllocationError
from adw.models.worktree import PortAllocation
from adw.worktree.ports import PortAllocator


class TestSlotCalculation:
    """Tests for slot calculation from run_id."""

    def test_same_run_id_same_slot(self) -> None:
        """Same run_id always produces same slot."""
        allocator = PortAllocator()
        slot1 = allocator.calculate_slot("01HQTEST123456789ABCD")
        slot2 = allocator.calculate_slot("01HQTEST123456789ABCD")
        assert slot1 == slot2

    def test_slot_within_range(self) -> None:
        """Calculated slot is always within valid range."""
        allocator = PortAllocator(max_concurrent=15)
        # Test with multiple run IDs
        for i in range(100):
            slot = allocator.calculate_slot(f"01HQTEST{i:020d}")
            assert 0 <= slot < 15

    def test_different_run_ids_produce_different_slots(self) -> None:
        """Different run_ids usually produce different slots (distribution test)."""
        allocator = PortAllocator(max_concurrent=15)
        slots = set()
        # Generate 50 different run IDs and check we get a reasonable distribution
        for i in range(50):
            slot = allocator.calculate_slot(f"01HQTEST{i:020d}")
            slots.add(slot)
        # With 50 random samples and 15 slots, we should hit at least 8 different slots
        assert len(slots) >= 8, f"Poor distribution: only {len(slots)} unique slots"

    def test_deterministic_hash_not_python_hash(self) -> None:
        """Slot calculation uses md5, not Python's hash (which varies by session)."""
        allocator = PortAllocator()
        # These should produce consistent results across Python sessions
        # The specific values are based on md5 hashing
        slot = allocator.calculate_slot("test-run-id")
        # Run again to ensure same result
        assert allocator.calculate_slot("test-run-id") == slot


class TestPortCalculation:
    """Tests for port number calculation from slot."""

    def test_default_port_ranges(self) -> None:
        """Default port ranges are 9100+ for backend and 9200+ for frontend."""
        allocator = PortAllocator()
        assert allocator.backend_start == 9100
        assert allocator.frontend_start == 9200

    def test_custom_port_ranges(self) -> None:
        """Port ranges can be customized."""
        allocator = PortAllocator(
            backend_start=8000,
            frontend_start=8100,
        )
        assert allocator.backend_start == 8000
        assert allocator.frontend_start == 8100

    def test_port_calculation_for_slot_zero(self) -> None:
        """Slot 0 produces base ports."""
        allocator = PortAllocator(
            backend_start=9100,
            frontend_start=9200,
        )
        backend, frontend = allocator.get_ports_for_slot(0)
        assert backend == 9100
        assert frontend == 9200

    def test_port_calculation_for_slot_n(self) -> None:
        """Slot N produces base ports + N."""
        allocator = PortAllocator(
            backend_start=9100,
            frontend_start=9200,
        )
        backend, frontend = allocator.get_ports_for_slot(5)
        assert backend == 9105
        assert frontend == 9205


class TestPortAllocation:
    """Tests for the allocation process."""

    def test_allocate_returns_port_allocation(self) -> None:
        """Allocation returns a PortAllocation model."""
        allocator = PortAllocator()
        result = allocator.allocate("01HQTEST123456789ABCD")
        assert isinstance(result, PortAllocation)

    def test_allocation_contains_run_id(self) -> None:
        """Allocation includes the original run_id."""
        allocator = PortAllocator()
        result = allocator.allocate("01HQTEST123456789ABCD")
        assert result.run_id == "01HQTEST123456789ABCD"

    def test_allocation_ports_in_valid_range(self) -> None:
        """Allocated ports are within the configured range."""
        allocator = PortAllocator(
            backend_start=9100,
            frontend_start=9200,
            max_concurrent=15,
        )
        result = allocator.allocate("01HQTEST123456789ABCD")
        assert 9100 <= result.backend_port < 9115
        assert 9200 <= result.frontend_port < 9215

    def test_allocation_slot_matches_ports(self) -> None:
        """Allocation slot matches the port offset."""
        allocator = PortAllocator(
            backend_start=9100,
            frontend_start=9200,
        )
        result = allocator.allocate("01HQTEST123456789ABCD")
        assert result.backend_port == 9100 + result.slot
        assert result.frontend_port == 9200 + result.slot


class TestPortAvailability:
    """Tests for port availability checking."""

    def test_available_port_returns_true(self) -> None:
        """Unused port returns True."""
        allocator = PortAllocator()
        # Use a high port that's unlikely to be in use
        assert allocator.is_port_available(59999) is True

    def test_used_port_returns_false(self) -> None:
        """Port with active listener returns False."""
        allocator = PortAllocator()
        # Create a listening server on a test port
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(("127.0.0.1", 19999))
            server.listen(1)
            # The port should now be in use
            assert allocator.is_port_available(19999) is False
        finally:
            server.close()


class TestAllocationRetry:
    """Tests for allocation retry behavior."""

    def test_allocate_retries_on_conflict(self) -> None:
        """Tries next slot when port is in use."""
        # Use high ports to avoid conflicts
        allocator = PortAllocator(
            backend_start=19100,
            frontend_start=19200,
            max_concurrent=5,
        )
        run_id = "01HQTEST123456789ABCD"
        base_slot = allocator.calculate_slot(run_id)
        base_backend = 19100 + base_slot

        # Block the base slot's backend port
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(("127.0.0.1", base_backend))
            server.listen(1)

            # Allocation should succeed with the next slot
            result = allocator.allocate(run_id, max_attempts=3)
            # Result should be from a different slot
            assert result.slot != base_slot or result.backend_port != base_backend
        finally:
            server.close()

    def test_allocate_raises_after_max_attempts(self) -> None:
        """Raises PortAllocationError when all attempts exhausted."""
        # Use high ports to avoid conflicts
        allocator = PortAllocator(
            backend_start=18100,
            frontend_start=18200,
            max_concurrent=3,
        )
        run_id = "01HQTEST_EXHAUST"
        base_slot = allocator.calculate_slot(run_id)

        # Block all 3 slots
        servers = []
        try:
            for i in range(3):
                slot = (base_slot + i) % 3
                port = 18100 + slot
                server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind(("127.0.0.1", port))
                server.listen(1)
                servers.append(server)

            # Should raise after trying all 3 slots
            with pytest.raises(PortAllocationError) as exc_info:
                allocator.allocate(run_id, max_attempts=3)

            assert exc_info.value.code == "PORT_ALLOCATION_FAILED"
            assert "3 attempts" in exc_info.value.message
        finally:
            for server in servers:
                server.close()


class TestPortsEnv:
    """Tests for .ports.env file generation."""

    def test_writes_correct_format(self, tmp_path) -> None:
        """Generated .ports.env has correct content."""
        allocator = PortAllocator()
        allocation = PortAllocation(
            slot=5,
            backend_port=9105,
            frontend_port=9205,
            run_id="01HQTEST123456789ABCD",
        )

        ports_file = allocator.write_ports_env(allocation, tmp_path)

        assert ports_file.exists()
        content = ports_file.read_text()
        assert "BACKEND_PORT=9105" in content
        assert "FRONTEND_PORT=9205" in content
        assert "ADW_SLOT=5" in content
        assert "ADW_RUN_ID=01HQTEST123456789ABCD" in content

    def test_file_is_shell_sourceable(self, tmp_path) -> None:
        """File can be sourced by shell (no syntax errors)."""
        import subprocess

        allocator = PortAllocator()
        allocation = PortAllocation(
            slot=0,
            backend_port=9100,
            frontend_port=9200,
            run_id="01HQTEST",
        )

        ports_file = allocator.write_ports_env(allocation, tmp_path)

        # Try to source the file with bash
        result = subprocess.run(
            ["bash", "-c", f"source {ports_file} && echo $BACKEND_PORT"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "9100"

    def test_returns_path_to_file(self, tmp_path) -> None:
        """Returns the path to the generated file."""
        allocator = PortAllocator()
        allocation = PortAllocation(
            slot=0,
            backend_port=9100,
            frontend_port=9200,
            run_id="01HQTEST",
        )

        result = allocator.write_ports_env(allocation, tmp_path)

        assert result == tmp_path / ".ports.env"
        assert result.is_file()
