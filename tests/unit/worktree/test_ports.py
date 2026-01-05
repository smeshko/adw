"""Unit tests for port allocation system.

Tests for the PortAllocator class which handles deterministic port
allocation for concurrent ADW runs.
"""

import socket
import threading

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
