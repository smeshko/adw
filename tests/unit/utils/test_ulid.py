"""Unit tests for ULID generation utilities."""

from adw.utils.ulid import generate_run_id


class TestGenerateRunId:
    """Test the generate_run_id function."""

    def test_generate_run_id_returns_string(self) -> None:
        """Test that generate_run_id returns a string."""
        run_id = generate_run_id()
        assert isinstance(run_id, str)

    def test_generate_run_id_returns_26_characters(self) -> None:
        """Test that ULID is 26 characters long."""
        run_id = generate_run_id()
        assert len(run_id) == 26

    def test_generate_run_id_uses_valid_characters(self) -> None:
        """Test that ULID uses only valid Crockford Base32 characters."""
        run_id = generate_run_id()
        # Crockford's Base32 alphabet (excludes I, L, O, U)
        valid_chars = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
        for char in run_id.upper():
            assert char in valid_chars, f"Invalid character: {char}"

    def test_generate_run_id_is_unique(self) -> None:
        """Test that consecutive calls return unique IDs."""
        ids = [generate_run_id() for _ in range(100)]
        assert len(set(ids)) == 100, "Generated IDs should be unique"

    def test_generate_run_id_is_lexicographically_sortable(self) -> None:
        """Test that ULIDs are sortable by creation time."""
        import time

        ids = []
        for _ in range(5):
            ids.append(generate_run_id())
            time.sleep(0.002)  # Small delay to ensure different timestamps

        # ULIDs should already be in chronological order when sorted lexicographically
        sorted_ids = sorted(ids)
        assert ids == sorted_ids, "ULIDs should be lexicographically sortable"

    def test_generate_run_id_passes_model_validation(self) -> None:
        """Test that generated ULID passes RunContext validation."""
        from datetime import datetime

        from adw.models import RunContext

        run_id = generate_run_id()

        # Should not raise validation error
        context = RunContext(
            run_id=run_id,
            feature_description="Test feature",
            current_phase="plan",
            started_at=datetime.now(),
        )
        assert context.run_id == run_id
