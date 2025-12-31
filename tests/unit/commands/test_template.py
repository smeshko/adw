"""Unit tests for the TemplateEngine class."""

from pathlib import Path

import pytest

from adw.commands import TemplateEngine
from adw.commands.template import VARIABLE_PATTERN, FILE_PATTERN
from adw.exceptions import ConfigError


class TestTemplateEngineModuleStructure:
    """Tests for Task 1: Template Engine Module Structure."""

    def test_template_engine_importable_from_commands(self) -> None:
        """TemplateEngine should be importable from adw.commands."""
        from adw.commands import TemplateEngine

        assert TemplateEngine is not None

    def test_template_engine_has_render_method(self) -> None:
        """TemplateEngine should have a render method."""
        engine = TemplateEngine()
        assert hasattr(engine, "render")
        assert callable(engine.render)

    def test_template_engine_accepts_project_root(self) -> None:
        """TemplateEngine should accept a project_root parameter."""
        root = Path("/tmp/test")
        engine = TemplateEngine(project_root=root)
        assert engine.project_root == root

    def test_template_engine_defaults_to_cwd(self) -> None:
        """TemplateEngine should default project_root to cwd."""
        engine = TemplateEngine()
        assert engine.project_root == Path.cwd()
