"""Tests for InputResolver.

Tests cover:
- Basic resolution logic (task ID vs feature string)
- Force flags (--task-id, --no-task-manager)
- Edge cases (empty strings, whitespace, etc.)
- Logging behavior
"""

from unittest.mock import Mock

import pytest

from adw.task_managers.resolver import InputResolver, InputType, ResolvedInput


class TestInputResolver:
    """Test InputResolver.resolve method."""

    @pytest.fixture
    def mock_task_manager(self) -> Mock:
        """Create a mock TaskManager."""
        manager = Mock()
        manager.name = "mock"
        return manager

    @pytest.fixture
    def resolver(self, mock_task_manager: Mock) -> InputResolver:
        """Create an InputResolver with mock task manager."""
        return InputResolver(mock_task_manager)

    def test_resolve_task_id_match(
        self,
        resolver: InputResolver,
        mock_task_manager: Mock,
    ) -> None:
        """Returns TASK_ID when pattern matches."""
        mock_task_manager.resolve_task_id.return_value = "RULE-123"

        result = resolver.resolve("RULE-123")

        assert result.type == InputType.TASK_ID
        assert result.value == "RULE-123"
        assert result.task_id == "RULE-123"
        assert result.original == "RULE-123"
        mock_task_manager.resolve_task_id.assert_called_once_with("RULE-123")

    def test_resolve_feature_string(
        self,
        resolver: InputResolver,
        mock_task_manager: Mock,
    ) -> None:
        """Returns FEATURE_STRING when pattern doesn't match."""
        mock_task_manager.resolve_task_id.return_value = None

        result = resolver.resolve("Add user authentication")

        assert result.type == InputType.FEATURE_STRING
        assert result.value == "Add user authentication"
        assert result.task_id is None
        assert result.original == "Add user authentication"

    def test_resolve_force_task_id_success(
        self,
        resolver: InputResolver,
        mock_task_manager: Mock,
    ) -> None:
        """Force task ID succeeds when pattern matches."""
        mock_task_manager.resolve_task_id.return_value = "RULE-123"

        result = resolver.resolve("RULE-123", force_task_id=True)

        assert result.type == InputType.TASK_ID
        assert result.task_id == "RULE-123"

    def test_resolve_force_task_id_error(
        self,
        resolver: InputResolver,
        mock_task_manager: Mock,
    ) -> None:
        """Raises error when force_task_id=True and no match."""
        mock_task_manager.resolve_task_id.return_value = None

        with pytest.raises(ValueError, match="does not match task ID pattern"):
            resolver.resolve("Add user authentication", force_task_id=True)

    def test_resolve_force_feature(
        self,
        resolver: InputResolver,
        mock_task_manager: Mock,
    ) -> None:
        """Returns FEATURE_STRING regardless of pattern when force_feature=True."""
        # Even though this looks like a task ID, force_feature should skip resolution
        result = resolver.resolve("RULE-123", force_feature=True)

        assert result.type == InputType.FEATURE_STRING
        assert result.value == "RULE-123"
        assert result.task_id is None
        # Should NOT call resolve_task_id when force_feature is True
        mock_task_manager.resolve_task_id.assert_not_called()

    def test_resolve_preserves_original(
        self,
        resolver: InputResolver,
        mock_task_manager: Mock,
    ) -> None:
        """ResolvedInput includes original input string."""
        mock_task_manager.resolve_task_id.return_value = "RULE-123"

        result = resolver.resolve("  RULE-123  ")

        # Original should be preserved exactly as passed
        assert result.original == "  RULE-123  "


class TestInputResolverEdgeCases:
    """Test edge cases in input resolution."""

    @pytest.fixture
    def mock_task_manager(self) -> Mock:
        """Create a mock TaskManager."""
        manager = Mock()
        manager.name = "mock"
        return manager

    @pytest.fixture
    def resolver(self, mock_task_manager: Mock) -> InputResolver:
        """Create an InputResolver with mock task manager."""
        return InputResolver(mock_task_manager)

    def test_empty_string(
        self,
        resolver: InputResolver,
        mock_task_manager: Mock,
    ) -> None:
        """Empty string treated as feature."""
        mock_task_manager.resolve_task_id.return_value = None

        result = resolver.resolve("")

        assert result.type == InputType.FEATURE_STRING
        assert result.value == ""

    def test_whitespace_only(
        self,
        resolver: InputResolver,
        mock_task_manager: Mock,
    ) -> None:
        """Whitespace-only treated as feature."""
        mock_task_manager.resolve_task_id.return_value = None

        result = resolver.resolve("   ")

        assert result.type == InputType.FEATURE_STRING
        assert result.value == "   "

    def test_with_spaces(
        self,
        resolver: InputResolver,
        mock_task_manager: Mock,
    ) -> None:
        """Input with spaces treated as feature."""
        mock_task_manager.resolve_task_id.return_value = None

        result = resolver.resolve("Add user auth")

        assert result.type == InputType.FEATURE_STRING
        mock_task_manager.resolve_task_id.assert_called_once_with("Add user auth")

    def test_numeric_only(
        self,
        resolver: InputResolver,
        mock_task_manager: Mock,
    ) -> None:
        """Numeric-only input (e.g., '123') treated as feature."""
        mock_task_manager.resolve_task_id.return_value = None

        result = resolver.resolve("123")

        assert result.type == InputType.FEATURE_STRING

    def test_case_preserved(
        self,
        resolver: InputResolver,
        mock_task_manager: Mock,
    ) -> None:
        """Case is preserved in value and original."""
        mock_task_manager.resolve_task_id.return_value = "RULE-123"

        result = resolver.resolve("rule-123")

        # Task manager returns normalized, but original is preserved
        assert result.original == "rule-123"
        assert result.task_id == "RULE-123"  # Normalized by task manager


class TestResolvedInput:
    """Test ResolvedInput dataclass."""

    def test_task_id_resolved_input(self) -> None:
        """Create ResolvedInput for task ID."""
        result = ResolvedInput(
            type=InputType.TASK_ID,
            value="RULE-123",
            task_id="RULE-123",
            original="RULE-123",
        )

        assert result.type == InputType.TASK_ID
        assert result.value == "RULE-123"
        assert result.task_id == "RULE-123"
        assert result.original == "RULE-123"

    def test_feature_string_resolved_input(self) -> None:
        """Create ResolvedInput for feature string."""
        result = ResolvedInput(
            type=InputType.FEATURE_STRING,
            value="Add auth",
            original="Add auth",
        )

        assert result.type == InputType.FEATURE_STRING
        assert result.value == "Add auth"
        assert result.task_id is None
        assert result.original == "Add auth"


class TestInputType:
    """Test InputType enum."""

    def test_task_id_value(self) -> None:
        """TASK_ID has expected value."""
        assert InputType.TASK_ID.value == "task_id"

    def test_feature_string_value(self) -> None:
        """FEATURE_STRING has expected value."""
        assert InputType.FEATURE_STRING.value == "feature_string"
