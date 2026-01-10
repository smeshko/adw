"""Unit tests for the TemplateEngine class."""

from pathlib import Path

import pytest

from adw.commands import TemplateEngine
from adw.commands.template import ARTIFACT_REF_PATTERN, FILE_PATTERN, VARIABLE_PATTERN
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


class TestArtifactRefPattern:
    """Tests for ISS-017: ARTIFACT_REF_PATTERN consolidation."""

    def test_artifact_ref_pattern_importable_from_template(self) -> None:
        """ARTIFACT_REF_PATTERN should be importable from adw.commands.template."""
        from adw.commands.template import ARTIFACT_REF_PATTERN

        assert ARTIFACT_REF_PATTERN is not None

    def test_artifact_ref_pattern_matches_simple_reference(self) -> None:
        """ARTIFACT_REF_PATTERN should match {{artifacts.phase.name}}."""
        match = ARTIFACT_REF_PATTERN.search("Content: {{artifacts.plan.output}}")
        assert match is not None
        assert match.group(1) == "plan.output"

    def test_artifact_ref_pattern_matches_with_underscore(self) -> None:
        """ARTIFACT_REF_PATTERN should match snake_case names."""
        match = ARTIFACT_REF_PATTERN.search("{{artifacts.build.build_output}}")
        assert match is not None
        assert match.group(1) == "build.build_output"

    def test_artifact_ref_pattern_matches_wildcard(self) -> None:
        """ARTIFACT_REF_PATTERN should match wildcards like {{artifacts.phase.*}}."""
        match = ARTIFACT_REF_PATTERN.search("{{artifacts.plan.*}}")
        assert match is not None
        assert match.group(1) == "plan.*"

    def test_artifact_ref_pattern_does_not_match_root_wildcard(self) -> None:
        """ARTIFACT_REF_PATTERN requires at least one identifier before wildcard.

        Note: {{artifacts.*}} is intentionally NOT supported by the pattern.
        Valid wildcards are {{artifacts.plan.*}} (phase-level wildcard).
        """
        match = ARTIFACT_REF_PATTERN.search("{{artifacts.*}}")
        # Pattern requires at least one identifier segment
        assert match is None

    def test_artifact_ref_pattern_findall(self) -> None:
        """ARTIFACT_REF_PATTERN.findall should find all artifact references."""
        template = "{{artifacts.plan.output}} and {{artifacts.build.diff}}"
        matches = ARTIFACT_REF_PATTERN.findall(template)
        assert matches == ["plan.output", "build.diff"]


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


class TestBuildTaskContext:
    """Tests for Story 12.5: Task Context Building (build_task_context)."""

    def test_build_task_context_with_none_returns_empty_string_values(self) -> None:
        """build_task_context(None) returns dict with empty string values for graceful degradation."""
        from adw.commands.template import build_task_context

        result = build_task_context(None)

        # All standard fields should be empty strings
        assert result["id"] == ""
        assert result["identifier"] == ""
        assert result["title"] == ""
        assert result["description"] == ""
        assert result["status"] == ""
        assert result["priority"] == ""
        assert result["priority_label"] == ""
        assert result["labels"] == ""
        assert result["assignee"] == ""
        assert result["parent_id"] == ""
        assert result["parent_title"] == ""
        # Custom should be a GracefulDict (returns chainable GracefulDict for any key,
        # which converts to empty string when used as str)
        assert str(result["custom"]["any_missing_field"]) == ""
        assert str(result["custom"]["nested"]) == ""
        # Nested access should also work
        assert str(result["custom"]["any"]["deeply"]["nested"]["path"]) == ""

    def test_build_task_context_maps_all_fields(self) -> None:
        """build_task_context maps all TaskInfo fields correctly."""
        from adw.commands.template import build_task_context
        from adw.models.task import TaskInfo

        task = TaskInfo(
            id="uuid-123",
            identifier="RULE-456",
            title="Fix critical bug",
            description="Bug causes crash on login",
            status="In Progress",
            priority=1,
            labels=["bug", "critical"],
            assignee="john.doe",
            parent_id="RULE-100",
            parent_title="Authentication Epic",
            custom_fields={"sprint": "2024-Q1"},
        )

        result = build_task_context(task)

        assert result["id"] == "uuid-123"
        assert result["identifier"] == "RULE-456"
        assert result["title"] == "Fix critical bug"
        assert result["description"] == "Bug causes crash on login"
        assert result["status"] == "In Progress"
        assert result["priority"] == "1"
        assert result["priority_label"] == "Urgent"
        assert result["labels"] == "bug, critical"
        assert result["assignee"] == "john.doe"
        assert result["parent_id"] == "RULE-100"
        assert result["parent_title"] == "Authentication Epic"
        assert result["custom"] == {"sprint": "2024-Q1"}

    def test_build_task_context_priority_labels(self) -> None:
        """build_task_context maps priority numbers to correct labels."""
        from adw.commands.template import build_task_context
        from adw.models.task import TaskInfo

        priorities = {
            1: "Urgent",
            2: "High",
            3: "Medium",
            4: "Low",
        }

        for priority, expected_label in priorities.items():
            task = TaskInfo(
                id="test",
                identifier="TEST-1",
                title="Test",
                priority=priority,
            )
            result = build_task_context(task)
            assert result["priority_label"] == expected_label, f"Priority {priority} should map to {expected_label}"

    def test_build_task_context_handles_none_fields(self) -> None:
        """build_task_context handles None/missing optional fields as empty strings."""
        from adw.commands.template import build_task_context
        from adw.models.task import TaskInfo

        # Minimal task with only required fields
        task = TaskInfo(
            id="test-id",
            identifier="TEST-1",
            title="Test task",
        )

        result = build_task_context(task)

        assert result["id"] == "test-id"
        assert result["identifier"] == "TEST-1"
        assert result["title"] == "Test task"
        assert result["description"] == ""
        assert result["status"] == ""
        assert result["priority"] == ""
        assert result["priority_label"] == ""
        assert result["labels"] == ""
        assert result["assignee"] == ""
        assert result["parent_id"] == ""
        assert result["parent_title"] == ""
        assert result["custom"] == {}

    def test_build_task_context_labels_joined_with_comma(self) -> None:
        """build_task_context joins labels with comma and space."""
        from adw.commands.template import build_task_context
        from adw.models.task import TaskInfo

        task = TaskInfo(
            id="test",
            identifier="TEST-1",
            title="Test",
            labels=["bug", "urgent", "P1"],
        )

        result = build_task_context(task)
        assert result["labels"] == "bug, urgent, P1"


class TestTaskContextTemplateRendering:
    """Tests for Story 12.5: Task Variables in Template Rendering."""

    def test_task_variables_render_correctly(self) -> None:
        """Task variables should be accessible in templates via {{task.*}} syntax."""
        from adw.commands.template import build_task_context
        from adw.models.task import TaskInfo

        engine = TemplateEngine()
        task = TaskInfo(
            id="uuid-123",
            identifier="RULE-456",
            title="Fix bug",
            priority=2,
        )

        variables = {"task": build_task_context(task)}
        template = "Task: {{task.identifier}} - {{task.title}} ({{task.priority_label}})"

        result = engine.render(template, variables)
        assert result == "Task: RULE-456 - Fix bug (High)"

    def test_task_custom_fields_render_correctly(self) -> None:
        """Custom task fields should be accessible via {{task.custom.<field>}} syntax."""
        from adw.commands.template import build_task_context
        from adw.models.task import TaskInfo

        engine = TemplateEngine()
        task = TaskInfo(
            id="test",
            identifier="TEST-1",
            title="Test",
            custom_fields={
                "sprint": "2024-Q1",
                "team": "backend",
            },
        )

        variables = {"task": build_task_context(task)}
        template = "Sprint: {{task.custom.sprint}}, Team: {{task.custom.team}}"

        result = engine.render(template, variables)
        assert result == "Sprint: 2024-Q1, Team: backend"

    def test_task_nested_custom_fields_render_correctly(self) -> None:
        """Nested custom fields should be accessible with dot notation."""
        from adw.commands.template import build_task_context
        from adw.models.task import TaskInfo

        engine = TemplateEngine()
        task = TaskInfo(
            id="test",
            identifier="TEST-1",
            title="Test",
            custom_fields={
                "metadata": {
                    "category": "infrastructure",
                    "details": {
                        "component": "auth",
                    },
                },
            },
        )

        variables = {"task": build_task_context(task)}
        template = "Category: {{task.custom.metadata.category}}, Component: {{task.custom.metadata.details.component}}"

        result = engine.render(template, variables)
        assert result == "Category: infrastructure, Component: auth"

    def test_graceful_degradation_with_no_task_context(self) -> None:
        """Task variables should render as empty strings when task_info is None."""
        from adw.commands.template import build_task_context

        engine = TemplateEngine()
        variables = {"task": build_task_context(None)}
        template = "Task: {{task.identifier}} - {{task.title}}"

        result = engine.render(template, variables)
        assert result == "Task:  - "

    def test_graceful_degradation_custom_fields_with_no_task_context(self) -> None:
        """Custom task fields should render as empty strings when task_info is None."""
        from adw.commands.template import build_task_context

        engine = TemplateEngine()
        variables = {"task": build_task_context(None)}
        template = "Sprint: {{task.custom.sprint}}, Team: {{task.custom.team}}"

        result = engine.render(template, variables)
        assert result == "Sprint: , Team: "

    def test_graceful_degradation_nested_custom_fields_with_no_task_context(self) -> None:
        """Nested custom task fields should render as empty strings when task_info is None."""
        from adw.commands.template import build_task_context

        engine = TemplateEngine()
        variables = {"task": build_task_context(None)}
        # Test deeply nested custom field access
        template = "Category: {{task.custom.metadata.category}}, Component: {{task.custom.metadata.details.component}}"

        result = engine.render(template, variables)
        assert result == "Category: , Component: "


class TestTaskContextIntegration:
    """Integration tests for Story 12.5: End-to-End Task Context in Templates."""

    def test_run_context_with_task_info_renders_in_template(self) -> None:
        """RunContext with task_info should provide task variables in templates."""
        from datetime import datetime, UTC
        from adw.commands.template import build_task_context
        from adw.models.context import RunContext
        from adw.models.task import TaskInfo

        engine = TemplateEngine()

        task = TaskInfo(
            id="uuid-123",
            identifier="RULE-789",
            title="Implement feature",
            priority=3,
            labels=["feature", "backend"],
        )

        context = RunContext(
            run_id="01KEF734DWWB1JVAHSEEPX5EKC",  # Valid 26-char ULID
            feature_description="Add new API endpoint",
            current_phase="plan",
            started_at=datetime.now(UTC),
            status="running",
            task_info=task,
        )

        # Build variables like PhaseRunner does
        variables = {
            "context": context,
            "run_id": context.run_id,
            "feature": context.feature_description,
            "task": build_task_context(context.task_info),
        }

        template = """Run: {{run_id}}
Feature: {{feature}}
Task: {{task.identifier}} - {{task.title}}
Priority: {{task.priority_label}}
Labels: {{task.labels}}"""

        result = engine.render(template, variables)

        assert "Run: 01KEF734DWWB1JVAHSEEPX5EKC" in result
        assert "Feature: Add new API endpoint" in result
        assert "Task: RULE-789 - Implement feature" in result
        assert "Priority: Medium" in result
        assert "Labels: feature, backend" in result

    def test_run_context_without_task_info_renders_gracefully(self) -> None:
        """RunContext without task_info should render task variables as empty strings."""
        from datetime import datetime, UTC
        from adw.commands.template import build_task_context
        from adw.models.context import RunContext

        engine = TemplateEngine()

        context = RunContext(
            run_id="01KEF734DWWB2JVAHSEEPX6FKD",  # Valid 26-char ULID
            feature_description="Quick fix for login",
            current_phase="build",
            started_at=datetime.now(UTC),
            status="running",
            # task_info is None by default
        )

        variables = {
            "context": context,
            "run_id": context.run_id,
            "feature": context.feature_description,
            "task": build_task_context(context.task_info),
        }

        template = """Run: {{run_id}}
Feature: {{feature}}
Task: {{task.identifier}}
Title: {{task.title}}"""

        result = engine.render(template, variables)

        assert "Run: 01KEF734DWWB2JVAHSEEPX6FKD" in result
        assert "Feature: Quick fix for login" in result
        assert "Task: \n" in result  # Empty identifier
        assert "Title: " in result  # Empty title


class TestRenderWithRootParameters:
    """Tests for ISS-017: render() method with command_root and shared_root parameters."""

    def test_render_accepts_command_root_parameter(self, tmp_path: Path) -> None:
        """render() should accept command_root parameter for include resolution."""
        # Create a test include file
        command_dir = tmp_path / "commands" / "plan"
        command_dir.mkdir(parents=True)
        include_file = command_dir / "header.txt"
        include_file.write_text("Plan Header Content")

        engine = TemplateEngine(project_root=tmp_path)
        template = "Header: {{include:header.txt}}"

        # Pass command_root as parameter instead of setting instance attribute
        result = engine.render(template, {}, command_root=command_dir)

        assert result == "Header: Plan Header Content"

    def test_render_accepts_shared_root_parameter(self, tmp_path: Path) -> None:
        """render() should accept shared_root parameter for shared file resolution."""
        # Create a shared file
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir(parents=True)
        shared_file = commands_dir / "common.txt"
        shared_file.write_text("Shared Content")

        engine = TemplateEngine(project_root=tmp_path)
        template = "Common: {{shared:common.txt}}"

        # Pass shared_root as parameter instead of setting instance attribute
        result = engine.render(template, {}, shared_root=commands_dir)

        assert result == "Common: Shared Content"

    def test_render_parameters_override_instance_attributes(self, tmp_path: Path) -> None:
        """render() parameters should override instance command_root/shared_root."""
        # Create two different command directories with different content
        default_dir = tmp_path / "default"
        default_dir.mkdir()
        (default_dir / "file.txt").write_text("Default Content")

        override_dir = tmp_path / "override"
        override_dir.mkdir()
        (override_dir / "file.txt").write_text("Override Content")

        # Engine with default command_root
        engine = TemplateEngine(project_root=tmp_path, command_root=default_dir)
        template = "{{include:file.txt}}"

        # Without parameter, uses instance attribute
        result_default = engine.render(template, {})
        assert result_default == "Default Content"

        # With parameter, overrides instance attribute
        result_override = engine.render(template, {}, command_root=override_dir)
        assert result_override == "Override Content"


class TestValidateArtifactReferences:
    """Tests for ISS-017: validate_artifact_references function."""

    def test_validate_artifact_references_importable(self) -> None:
        """validate_artifact_references should be importable from adw.commands.template."""
        from adw.commands.template import validate_artifact_references

        assert validate_artifact_references is not None

    def test_validate_no_references_passes(self) -> None:
        """Templates without artifact references should pass validation."""
        from adw.commands.template import validate_artifact_references

        template = "Hello {{name}}, welcome to {{project}}!"
        artifacts_map: dict[str, dict[str, str]] = {}

        # Should not raise
        validate_artifact_references(template, artifacts_map, strict=True)

    def test_validate_existing_artifact_passes(self) -> None:
        """Valid artifact references should pass validation."""
        from adw.commands.template import validate_artifact_references

        template = "Plan: {{artifacts.plan.output}}"
        artifacts_map = {"plan": {"output": "Plan content"}}

        # Should not raise
        validate_artifact_references(template, artifacts_map, strict=True)

    def test_validate_missing_phase_strict_raises(self) -> None:
        """Missing phase in strict mode should raise ConfigError."""
        from adw.commands.template import validate_artifact_references
        from adw.exceptions import ConfigError

        template = "Plan: {{artifacts.plan.output}}"
        artifacts_map: dict[str, dict[str, str]] = {}  # No plan phase

        with pytest.raises(ConfigError) as exc:
            validate_artifact_references(template, artifacts_map, strict=True)

        assert exc.value.code == "ARTIFACT_NOT_FOUND"
        assert "plan/output" in exc.value.message

    def test_validate_missing_artifact_strict_raises(self) -> None:
        """Missing artifact in strict mode should raise ConfigError."""
        from adw.commands.template import validate_artifact_references
        from adw.exceptions import ConfigError

        template = "Diff: {{artifacts.build.diff}}"
        artifacts_map = {"build": {"output": "Build output"}}  # Has output, not diff

        with pytest.raises(ConfigError) as exc:
            validate_artifact_references(template, artifacts_map, strict=True)

        assert exc.value.code == "ARTIFACT_NOT_FOUND"
        assert "build/diff" in exc.value.message

    def test_validate_missing_lenient_returns_list(self) -> None:
        """Missing artifacts in lenient mode should return list of missing refs."""
        from adw.commands.template import validate_artifact_references

        template = "{{artifacts.plan.output}} and {{artifacts.build.diff}}"
        artifacts_map: dict[str, dict[str, str]] = {}

        # Lenient mode should return missing list instead of raising
        missing = validate_artifact_references(template, artifacts_map, strict=False)
        assert missing == ["plan/output", "build/diff"]

    def test_validate_wildcard_skipped(self) -> None:
        """Wildcard patterns should be skipped in validation."""
        from adw.commands.template import validate_artifact_references

        template = "All artifacts: {{artifacts.plan.*}}"
        artifacts_map: dict[str, dict[str, str]] = {}  # Empty, but wildcard should be skipped

        # Should not raise even with empty artifacts
        missing = validate_artifact_references(template, artifacts_map, strict=True)
        assert missing == []

    def test_validate_multiple_missing_reports_all(self) -> None:
        """Validation should report all missing artifacts, not just the first."""
        from adw.commands.template import validate_artifact_references
        from adw.exceptions import ConfigError

        template = "{{artifacts.plan.output}} {{artifacts.build.diff}} {{artifacts.validate.report}}"
        artifacts_map: dict[str, dict[str, str]] = {}

        with pytest.raises(ConfigError) as exc:
            validate_artifact_references(template, artifacts_map, strict=True)

        assert "plan/output" in exc.value.message
        assert "build/diff" in exc.value.message
        assert "validate/report" in exc.value.message

    def test_validate_single_part_ref_skipped(self) -> None:
        """Single-part refs like {{artifacts.plan}} should be skipped."""
        from adw.commands.template import validate_artifact_references

        # This accesses the phase dict, not a specific artifact
        template = "Phase info: {{artifacts.plan}}"
        artifacts_map: dict[str, dict[str, str]] = {}

        # Should not raise - single-part refs don't require specific artifacts
        missing = validate_artifact_references(template, artifacts_map, strict=True)
        assert missing == []
