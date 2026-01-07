"""Unit tests for the TemplateEngine class."""

from pathlib import Path

import pytest

from adw.commands import TemplateEngine
from adw.commands.template import FILE_PATTERN, VARIABLE_PATTERN
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


class TestFileInclusion:
    """Tests for Task 3: File Inclusion Pattern."""

    def test_file_pattern_matches_simple_path(self) -> None:
        """FILE_PATTERN should match {{file:path.txt}}."""
        match = FILE_PATTERN.search("Content: {{file:data.txt}}")
        assert match is not None
        assert match.group(1) == "data.txt"

    def test_file_pattern_matches_path_with_directory(self) -> None:
        """FILE_PATTERN should match {{file:dir/file.txt}}."""
        match = FILE_PATTERN.search("{{file:path/to/file.txt}}")
        assert match is not None
        assert match.group(1) == "path/to/file.txt"

    def test_file_inclusion_reads_content(self, tmp_path: Path) -> None:
        """Engine should read and include file content."""
        # Create test file
        test_file = tmp_path / "data.txt"
        test_file.write_text("file content here")

        engine = TemplateEngine(project_root=tmp_path)
        template = "Content: {{file:data.txt}}"
        result = engine.render(template, {})
        assert result == "Content: file content here"

    def test_file_inclusion_nested_path(self, tmp_path: Path) -> None:
        """Engine should handle nested file paths."""
        # Create nested directory and file
        nested_dir = tmp_path / "subdir"
        nested_dir.mkdir()
        test_file = nested_dir / "nested.txt"
        test_file.write_text("nested content")

        engine = TemplateEngine(project_root=tmp_path)
        template = "{{file:subdir/nested.txt}}"
        result = engine.render(template, {})
        assert result == "nested content"

    def test_file_not_found_raises_config_error(self, tmp_path: Path) -> None:
        """Engine should raise ConfigError for missing files."""
        engine = TemplateEngine(project_root=tmp_path)
        template = "{{file:nonexistent.txt}}"

        with pytest.raises(ConfigError) as exc:
            engine.render(template, {})

        assert exc.value.code == "TEMPLATE_FILE_NOT_FOUND"
        assert "nonexistent.txt" in exc.value.message

    def test_file_inclusion_with_variables(self, tmp_path: Path) -> None:
        """Engine should process both variables and file inclusions."""
        test_file = tmp_path / "data.txt"
        test_file.write_text("file data")

        engine = TemplateEngine(project_root=tmp_path)
        template = "Name: {{name}}, Data: {{file:data.txt}}"
        result = engine.render(template, {"name": "test"})
        assert result == "Name: test, Data: file data"

    def test_multiple_file_inclusions(self, tmp_path: Path) -> None:
        """Engine should handle multiple file inclusions."""
        file1 = tmp_path / "one.txt"
        file1.write_text("first")
        file2 = tmp_path / "two.txt"
        file2.write_text("second")

        engine = TemplateEngine(project_root=tmp_path)
        template = "{{file:one.txt}} and {{file:two.txt}}"
        result = engine.render(template, {})
        assert result == "first and second"

    def test_file_path_whitespace_stripped(self, tmp_path: Path) -> None:
        """Engine should strip whitespace from file paths."""
        test_file = tmp_path / "data.txt"
        test_file.write_text("content")

        engine = TemplateEngine(project_root=tmp_path)
        template = "{{file: data.txt }}"
        result = engine.render(template, {})
        assert result == "content"

    def test_path_traversal_blocked(self, tmp_path: Path) -> None:
        """Engine should block path traversal attempts."""
        # Create a file outside the project root
        parent_file = tmp_path.parent / "secret.txt"
        parent_file.write_text("secret data")

        engine = TemplateEngine(project_root=tmp_path)
        template = "{{file:../secret.txt}}"

        with pytest.raises(ConfigError) as exc:
            engine.render(template, {})

        assert exc.value.code == "TEMPLATE_PATH_TRAVERSAL"

    def test_path_traversal_absolute_blocked(self, tmp_path: Path) -> None:
        """Engine should block absolute path attempts."""
        engine = TemplateEngine(project_root=tmp_path)
        template = "{{file:/etc/passwd}}"

        with pytest.raises(ConfigError) as exc:
            engine.render(template, {})

        # Could be NOT_FOUND or PATH_TRAVERSAL depending on resolution
        assert exc.value.code in ("TEMPLATE_PATH_TRAVERSAL", "TEMPLATE_FILE_NOT_FOUND")

    def test_directory_path_raises_error(self, tmp_path: Path) -> None:
        """Engine should raise ConfigError for directory paths."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        engine = TemplateEngine(project_root=tmp_path)
        template = "{{file:subdir}}"

        with pytest.raises(ConfigError) as exc:
            engine.render(template, {})

        assert exc.value.code == "TEMPLATE_FILE_IS_DIRECTORY"


class TestStrictVsLenientMode:
    """Tests for Task 4: Strict vs Lenient Mode."""

    def test_strict_mode_is_default(self) -> None:
        """strict=True should be the default."""
        engine = TemplateEngine()
        template = "{{unknown_var}}"
        with pytest.raises(ConfigError):
            engine.render(template, {})

    def test_strict_mode_raises_for_unknown_variable(self) -> None:
        """strict=True should raise ConfigError for unknown variables."""
        engine = TemplateEngine()
        template = "Hello, {{unknown_var}}!"

        with pytest.raises(ConfigError) as exc:
            engine.render(template, {}, strict=True)

        assert exc.value.code == "UNKNOWN_VARIABLE"
        assert "unknown_var" in exc.value.message

    def test_strict_mode_reports_all_unknown_variables(self) -> None:
        """strict=True should report all unknown variables in error."""
        engine = TemplateEngine()
        template = "{{var1}} and {{var2}} and {{var3}}"

        with pytest.raises(ConfigError) as exc:
            engine.render(template, {}, strict=True)

        assert exc.value.code == "UNKNOWN_VARIABLE"
        assert "var1" in exc.value.message
        assert "var2" in exc.value.message
        assert "var3" in exc.value.message

    def test_lenient_mode_preserves_unknown_variable(self) -> None:
        """strict=False should leave unknown variables as-is."""
        engine = TemplateEngine()
        template = "Hello, {{unknown_var}}!"
        result = engine.render(template, {}, strict=False)
        assert result == "Hello, {{unknown_var}}!"

    def test_lenient_mode_substitutes_known_variables(self) -> None:
        """strict=False should still substitute known variables."""
        engine = TemplateEngine()
        template = "{{known}} and {{unknown}}"
        result = engine.render(template, {"known": "value"}, strict=False)
        assert result == "value and {{unknown}}"

    def test_lenient_mode_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """strict=False should log a warning for unknown variables."""
        import logging

        engine = TemplateEngine()
        template = "{{missing}}"

        with caplog.at_level(logging.WARNING):
            engine.render(template, {}, strict=False)

        assert "missing" in caplog.text or any(
            "missing" in record.getMessage()
            or record.__dict__.get("variable") == "missing"
            for record in caplog.records
        )

    def test_strict_mode_with_nested_unknown(self) -> None:
        """strict=True should report unknown nested paths."""
        engine = TemplateEngine()
        template = "{{context.missing.field}}"

        with pytest.raises(ConfigError) as exc:
            engine.render(template, {"context": {}}, strict=True)

        assert exc.value.code == "UNKNOWN_VARIABLE"


class TestSingleLevelSubstitution:
    """Tests for Task 5: Single-Level Substitution Guard."""

    def test_no_recursive_expansion(self) -> None:
        """Engine should NOT recursively expand variables in values."""
        engine = TemplateEngine()
        # Context value contains template syntax
        context = {"value": "{{nested}}"}
        template = "{{value}}"
        result = engine.render(template, context, strict=False)
        # Should output the literal string, not try to expand {{nested}}
        assert result == "{{nested}}"

    def test_no_recursive_expansion_with_nested_variables(self) -> None:
        """Nested template syntax in values should remain literal."""
        engine = TemplateEngine()
        context = {"outer": "{{inner}}", "inner": "should not appear"}
        template = "{{outer}}"
        result = engine.render(template, context, strict=False)
        assert result == "{{inner}}"
        assert "should not appear" not in result

    def test_single_pass_processing(self) -> None:
        """Variables should be processed in a single pass."""
        engine = TemplateEngine()
        # If recursive, this would fail or loop
        context = {"a": "{{b}}", "b": "{{a}}"}
        template = "{{a}} and {{b}}"
        result = engine.render(template, context, strict=False)
        assert result == "{{b}} and {{a}}"

    def test_file_content_not_expanded(self, tmp_path: Path) -> None:
        """File content containing template syntax should remain literal."""
        # Create file with template syntax
        test_file = tmp_path / "config.txt"
        test_file.write_text("Value is {{some_var}}")

        engine = TemplateEngine(project_root=tmp_path)
        template = "{{file:config.txt}}"
        result = engine.render(template, {"some_var": "REPLACED"}, strict=False)
        # File content should NOT have its variables expanded
        assert result == "Value is {{some_var}}"
        assert "REPLACED" not in result

    def test_variables_processed_before_files(self, tmp_path: Path) -> None:
        """Variables are substituted before file inclusions."""
        test_file = tmp_path / "data.txt"
        test_file.write_text("file data")

        engine = TemplateEngine(project_root=tmp_path)
        # Variable substitution happens first, file inclusion second
        template = "{{name}} says: {{file:data.txt}}"
        result = engine.render(template, {"name": "Alice"})
        assert result == "Alice says: file data"


class TestContextObjectRendering:
    """Tests for Task 6: Context Object Rendering."""

    def test_pydantic_model_as_context(self) -> None:
        """Engine should accept Pydantic models as context."""
        from datetime import datetime

        from adw.models import RunContext

        engine = TemplateEngine()
        context = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="Add login",
            current_phase="plan",
            started_at=datetime.now(),
        )

        template = "Feature: {{feature_description}}"
        result = engine.render(template, context)
        assert result == "Feature: Add login"

    def test_pydantic_model_nested_access(self) -> None:
        """Engine should access nested fields in Pydantic models."""
        from pydantic import BaseModel

        class Inner(BaseModel):
            value: str = "nested_value"

        class Outer(BaseModel):
            inner: Inner = Inner()

        engine = TemplateEngine()
        context = Outer()
        template = "Value: {{inner.value}}"
        result = engine.render(template, context)
        assert result == "Value: nested_value"

    def test_model_dump_is_used(self) -> None:
        """Engine should use model_dump() for Pydantic models."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            name: str = "test_name"
            count: int = 42

        engine = TemplateEngine()
        model = TestModel()
        template = "{{name}} - {{count}}"
        result = engine.render(template, model)
        assert result == "test_name - 42"

    def test_run_context_multiple_fields(self) -> None:
        """Engine should render multiple RunContext fields."""
        from datetime import datetime

        from adw.models import RunContext

        engine = TemplateEngine()
        context = RunContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            feature_description="User auth",
            current_phase="build",
            started_at=datetime.now(),
            status="running",
        )

        template = "Run {{run_id}} in {{current_phase}} phase: {{feature_description}}"
        result = engine.render(template, context)
        assert "01KDSG2VDHNK0W4HSCZWJZXWSQ" in result
        assert "build" in result
        assert "User auth" in result

    def test_session_context_as_context(self) -> None:
        """Engine should accept SessionContext as context."""
        from adw.models.context import SessionContext

        engine = TemplateEngine()
        context = SessionContext(
            run_id="01KDSG2VDHNK0W4HSCZWJZXWSQ",
            current_phase="validate",
            is_resuming=True,
        )

        template = "Phase: {{current_phase}}, Resuming: {{is_resuming}}"
        result = engine.render(template, context)
        assert result == "Phase: validate, Resuming: True"

    def test_dict_and_model_produce_same_result(self) -> None:
        """Dict and Pydantic model should render identically."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            name: str
            value: int

        engine = TemplateEngine()
        template = "{{name}}: {{value}}"

        model = TestModel(name="test", value=123)
        dict_context = {"name": "test", "value": 123}

        result_model = engine.render(template, model)
        result_dict = engine.render(template, dict_context)

        assert result_model == result_dict == "test: 123"

    def test_object_attribute_access_in_nested_dict(self) -> None:
        """Engine should access object attributes for nested non-dict values."""

        class CustomObject:
            def __init__(self) -> None:
                self.inner_value = "accessed"

        engine = TemplateEngine()
        context = {"outer": CustomObject()}
        template = "{{outer.inner_value}}"
        result = engine.render(template, context)
        assert result == "accessed"

    def test_object_attribute_access_missing_raises(self) -> None:
        """Missing attribute on object should raise ConfigError."""

        class CustomObject:
            pass

        engine = TemplateEngine()
        context = {"outer": CustomObject()}
        template = "{{outer.nonexistent}}"
        with pytest.raises(ConfigError) as exc:
            engine.render(template, context, strict=True)
        assert exc.value.code == "UNKNOWN_VARIABLE"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_template(self) -> None:
        """Engine should handle empty template string."""
        engine = TemplateEngine()
        result = engine.render("", {})
        assert result == ""

    def test_whitespace_only_template(self) -> None:
        """Engine should preserve whitespace-only templates."""
        engine = TemplateEngine()
        result = engine.render("   \n\t  ", {})
        assert result == "   \n\t  "

    def test_no_variables_in_template(self) -> None:
        """Engine should return template unchanged if no variables."""
        engine = TemplateEngine()
        template = "Plain text without any variables"
        result = engine.render(template, {})
        assert result == template

    def test_empty_context(self) -> None:
        """Engine should work with empty context for templates without variables."""
        engine = TemplateEngine()
        template = "Static content"
        result = engine.render(template, {})
        assert result == "Static content"

    def test_boolean_value_conversion(self) -> None:
        """Engine should convert boolean values to string."""
        engine = TemplateEngine()
        template = "Active: {{active}}, Enabled: {{enabled}}"
        context = {"active": True, "enabled": False}
        result = engine.render(template, context)
        assert result == "Active: True, Enabled: False"

    def test_list_value_conversion(self) -> None:
        """Engine should convert list values to string."""
        engine = TemplateEngine()
        template = "Items: {{items}}"
        context = {"items": [1, 2, 3]}
        result = engine.render(template, context)
        assert result == "Items: [1, 2, 3]"
