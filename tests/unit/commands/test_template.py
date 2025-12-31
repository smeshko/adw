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


class TestVariableSubstitution:
    """Tests for Task 2: Variable Substitution Pattern."""

    def test_variable_pattern_matches_simple_variable(self) -> None:
        """VARIABLE_PATTERN should match {{name}}."""
        match = VARIABLE_PATTERN.search("Hello, {{name}}!")
        assert match is not None
        assert match.group(1) == "name"

    def test_variable_pattern_matches_nested_path(self) -> None:
        """VARIABLE_PATTERN should match {{context.run_id}}."""
        match = VARIABLE_PATTERN.search("ID: {{context.run_id}}")
        assert match is not None
        assert match.group(1) == "context.run_id"

    def test_variable_pattern_matches_underscore_names(self) -> None:
        """VARIABLE_PATTERN should match snake_case names."""
        match = VARIABLE_PATTERN.search("{{feature_description}}")
        assert match is not None
        assert match.group(1) == "feature_description"

    def test_simple_variable_substitution(self) -> None:
        """Engine should substitute simple variables."""
        engine = TemplateEngine()
        template = "Hello, {{name}}!"
        context = {"name": "World"}
        result = engine.render(template, context)
        assert result == "Hello, World!"

    def test_multiple_variables(self) -> None:
        """Engine should substitute multiple variables."""
        engine = TemplateEngine()
        template = "{{greeting}}, {{name}}!"
        context = {"greeting": "Hi", "name": "World"}
        result = engine.render(template, context)
        assert result == "Hi, World!"

    def test_dot_notation_nested_access(self) -> None:
        """Engine should resolve dot notation paths."""
        engine = TemplateEngine()
        template = "Run ID: {{context.run_id}}"
        context = {"context": {"run_id": "abc123"}}
        result = engine.render(template, context)
        assert result == "Run ID: abc123"

    def test_deeply_nested_access(self) -> None:
        """Engine should resolve deeply nested paths."""
        engine = TemplateEngine()
        template = "Value: {{a.b.c.d}}"
        context = {"a": {"b": {"c": {"d": "deep_value"}}}}
        result = engine.render(template, context)
        assert result == "Value: deep_value"

    def test_none_value_becomes_empty_string(self) -> None:
        """Engine should convert None values to empty string."""
        engine = TemplateEngine()
        template = "Value: {{value}}"
        context = {"value": None}
        result = engine.render(template, context)
        assert result == "Value: "

    def test_numeric_values_converted_to_string(self) -> None:
        """Engine should convert numeric values to string."""
        engine = TemplateEngine()
        template = "Count: {{count}}, Price: {{price}}"
        context = {"count": 42, "price": 19.99}
        result = engine.render(template, context)
        assert result == "Count: 42, Price: 19.99"

    def test_render_method_signature(self) -> None:
        """render() should accept template and context."""
        engine = TemplateEngine()
        result = engine.render("text", {})
        assert isinstance(result, str)
