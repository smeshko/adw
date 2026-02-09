"""Tests for ConfigRegistry and SettingDefinition."""

from __future__ import annotations

import pytest

from adw.config.registry import ConfigRegistry, SettingDefinition


class TestSettingDefinition:
    """Tests for SettingDefinition dataclass."""

    def test_basic_creation(self) -> None:
        """Test creating a basic setting definition."""
        setting = SettingDefinition(
            name="timeout_seconds",
            type_hint="int",
            default=300,
            description="Maximum time for execution",
        )

        assert setting.name == "timeout_seconds"
        assert setting.type_hint == "int"
        assert setting.default == 300
        assert setting.description == "Maximum time for execution"
        assert setting.is_nested is False
        assert setting.is_required is False

    def test_required_setting(self) -> None:
        """Test required setting (no default)."""
        setting = SettingDefinition(
            name="name",
            type_hint="str",
            default=None,
            description="Project name",
            is_required=True,
        )

        assert setting.is_required is True
        assert setting.default is None

    def test_nested_setting(self) -> None:
        """Test nested setting definition."""
        setting = SettingDefinition(
            name="git",
            type_hint="GitConfig",
            default=None,
            description="Git configuration",
            is_nested=True,
        )

        assert setting.is_nested is True


class TestConfigRegistry:
    """Tests for ConfigRegistry."""

    @pytest.fixture
    def registry(self) -> ConfigRegistry:
        """Create a fresh registry instance."""
        return ConfigRegistry()

    def test_initialization(self, registry: ConfigRegistry) -> None:
        """Test registry initializes without errors."""
        assert registry is not None
        assert len(registry.list_sections()) > 0

    def test_project_section_has_required_fields(
        self, registry: ConfigRegistry
    ) -> None:
        """Test project section includes name and language as required."""
        settings = registry.get_all_settings("project")
        setting_names = {s.name for s in settings}

        assert "name" in setting_names
        assert "language" in setting_names

        # Check name is marked required
        name_setting = next(s for s in settings if s.name == "name")
        assert name_setting.is_required is True

    def test_git_section_has_expected_settings(self, registry: ConfigRegistry) -> None:
        """Test git section has expected settings with correct defaults."""
        settings = registry.get_all_settings("git")
        settings_dict = {s.name: s for s in settings}

        # Check expected fields exist
        assert "branch_prefix" in settings_dict
        assert "skip_hooks" in settings_dict

        # Check defaults
        assert settings_dict["branch_prefix"].default == "feature/"
        assert settings_dict["skip_hooks"].default is False

    def test_phase_settings(self, registry: ConfigRegistry) -> None:
        """Test phase settings are available."""
        settings = registry.get_phase_settings("plan")
        setting_names = {s.name for s in settings}

        assert "enabled" in setting_names
        assert "timeout_seconds" in setting_names

        # All phases should have same base settings
        build_settings = registry.get_phase_settings("build")
        assert {s.name for s in build_settings} == setting_names

    def test_llm_section_has_path_and_timeout(self, registry: ConfigRegistry) -> None:
        """Test LLM section has critical settings."""
        settings = registry.get_all_settings("llm")
        settings_dict = {s.name: s for s in settings}

        assert "path" in settings_dict
        assert "timeout_seconds" in settings_dict

        # Check defaults
        assert settings_dict["path"].default == "claude"
        assert settings_dict["timeout_seconds"].default == 300

    def test_unknown_section_raises_keyerror(self, registry: ConfigRegistry) -> None:
        """Test accessing unknown section raises KeyError."""
        with pytest.raises(KeyError, match="Unknown config section"):
            registry.get_all_settings("nonexistent")

    def test_has_section(self, registry: ConfigRegistry) -> None:
        """Test has_section method."""
        assert registry.has_section("git") is True
        assert registry.has_section("llm") is True
        assert registry.has_section("nonexistent") is False

    def test_section_order(self, registry: ConfigRegistry) -> None:
        """Test section order is defined."""
        order = registry.get_section_order()

        assert len(order) > 0
        assert "project" in order
        assert "git" in order

    def test_settings_have_descriptions(self, registry: ConfigRegistry) -> None:
        """Test all settings have non-empty descriptions."""
        for section in ["project", "git", "llm"]:
            settings = registry.get_all_settings(section)
            for setting in settings:
                assert setting.description, (
                    f"{section}.{setting.name} missing description"
                )

    def test_security_section_exists(self, registry: ConfigRegistry) -> None:
        """Test security section has expected settings."""
        settings = registry.get_all_settings("security")
        setting_names = {s.name for s in settings}

        assert "blocked_patterns" in setting_names
        assert "blocked_env_files" in setting_names

    def test_ship_section_exists(self, registry: ConfigRegistry) -> None:
        """Test ship section has expected settings."""
        settings = registry.get_all_settings("ship")
        setting_names = {s.name for s in settings}

        assert "enabled" in setting_names
        assert "post_publish" in setting_names

    def test_ports_section_has_defaults(self, registry: ConfigRegistry) -> None:
        """Test ports section has expected defaults."""
        settings = registry.get_all_settings("ports")
        settings_dict = {s.name: s for s in settings}

        assert "backend_start" in settings_dict
        assert "frontend_start" in settings_dict
        assert settings_dict["backend_start"].default == 9100
        assert settings_dict["frontend_start"].default == 9200
