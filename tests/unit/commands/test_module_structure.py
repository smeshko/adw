"""Tests for command module structure (Task 1).

Verifies that the commands module exports the correct classes.
"""


class TestCommandModuleStructure:
    """Test the commands module structure and exports."""

    def test_command_resolver_importable(self) -> None:
        """CommandResolver should be importable from adw.commands."""
        from adw.commands import CommandResolver

        assert CommandResolver is not None

    def test_command_loader_importable(self) -> None:
        """CommandLoader should be importable from adw.commands."""
        from adw.commands import CommandLoader

        assert CommandLoader is not None

    def test_command_resolver_is_class(self) -> None:
        """CommandResolver should be a class."""
        from adw.commands import CommandResolver

        assert isinstance(CommandResolver, type)

    def test_command_loader_is_class(self) -> None:
        """CommandLoader should be a class."""
        from adw.commands import CommandLoader

        assert isinstance(CommandLoader, type)
