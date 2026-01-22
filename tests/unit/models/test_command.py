# Test Reduction Notes per ADR-001:
# Only testing validation logic, boundary conditions, and error handling.
# NOT testing: default values, simple attribute assignment, Pydantic serialization.

"""Tests for command models (CommandConfig, PhaseLLMConfig, ArtifactConfig, DocumentCommandConfig)."""

import pytest
from pydantic import ValidationError

from adw.models.command import (
    ArtifactConfig,
    CommandConfig,
    DocMappingConfig,
    DocumentCommandConfig,
    PhaseLLMConfig,
)


class TestPhaseLLMConfig:
    """Tests for PhaseLLMConfig validation rules."""

    def test_temperature_boundary_zero(self) -> None:
        """Temperature accepts minimum value 0.0."""
        config = PhaseLLMConfig(temperature=0.0)
        assert config.temperature == 0.0

    def test_temperature_boundary_one(self) -> None:
        """Temperature accepts maximum value 1.0."""
        config = PhaseLLMConfig(temperature=1.0)
        assert config.temperature == 1.0

    def test_temperature_below_zero_rejected(self) -> None:
        """Temperature rejects values below 0.0."""
        with pytest.raises(ValidationError) as exc_info:
            PhaseLLMConfig(temperature=-0.1)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_temperature_above_one_rejected(self) -> None:
        """Temperature rejects values above 1.0."""
        with pytest.raises(ValidationError) as exc_info:
            PhaseLLMConfig(temperature=1.1)
        assert "less than or equal to 1" in str(exc_info.value)

    def test_extra_fields_rejected(self) -> None:
        """PhaseLLMConfig rejects unknown fields (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            PhaseLLMConfig(model="opus", unknown_field="value")  # type: ignore[call-arg]
        assert "extra" in str(exc_info.value).lower()


class TestArtifactConfig:
    """Tests for ArtifactConfig validation rules."""

    def test_name_required(self) -> None:
        """ArtifactConfig requires name field."""
        with pytest.raises(ValidationError) as exc_info:
            ArtifactConfig(pattern="output/*.md")  # type: ignore[call-arg]
        assert "name" in str(exc_info.value).lower()

    def test_pattern_required(self) -> None:
        """ArtifactConfig requires pattern field."""
        with pytest.raises(ValidationError) as exc_info:
            ArtifactConfig(name="plan")  # type: ignore[call-arg]
        assert "pattern" in str(exc_info.value).lower()

    def test_name_empty_string_rejected(self) -> None:
        """ArtifactConfig rejects empty name string."""
        with pytest.raises(ValidationError) as exc_info:
            ArtifactConfig(name="", pattern="output/*.md")
        assert (
            "min_length" in str(exc_info.value).lower()
            or "string_too_short" in str(exc_info.value).lower()
        )

    def test_pattern_empty_string_rejected(self) -> None:
        """ArtifactConfig rejects empty pattern string."""
        with pytest.raises(ValidationError) as exc_info:
            ArtifactConfig(name="plan", pattern="")
        assert (
            "min_length" in str(exc_info.value).lower()
            or "string_too_short" in str(exc_info.value).lower()
        )

    def test_extra_fields_rejected(self) -> None:
        """ArtifactConfig rejects unknown fields (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ArtifactConfig(name="plan", pattern="*.md", unknown="value")  # type: ignore[call-arg]
        assert "extra" in str(exc_info.value).lower()


class TestCommandConfig:
    """Tests for CommandConfig validation rules."""

    def test_timeout_must_be_positive(self) -> None:
        """CommandConfig timeout_seconds must be > 0."""
        with pytest.raises(ValidationError) as exc_info:
            CommandConfig(timeout_seconds=0)
        assert "greater than 0" in str(exc_info.value)

    def test_timeout_negative_rejected(self) -> None:
        """CommandConfig timeout_seconds rejects negative values."""
        with pytest.raises(ValidationError) as exc_info:
            CommandConfig(timeout_seconds=-1)
        assert "greater than 0" in str(exc_info.value)

    def test_artifact_names_must_be_unique(self) -> None:
        """CommandConfig rejects duplicate artifact names."""
        with pytest.raises(ValidationError) as exc_info:
            CommandConfig(
                artifacts=[
                    ArtifactConfig(name="plan", pattern="a.md"),
                    ArtifactConfig(name="plan", pattern="b.md"),  # duplicate
                ]
            )
        assert "Duplicate artifact names found: plan" in str(exc_info.value)

    def test_multiple_duplicate_artifact_names_reported(self) -> None:
        """CommandConfig reports all duplicate artifact names."""
        with pytest.raises(ValidationError) as exc_info:
            CommandConfig(
                artifacts=[
                    ArtifactConfig(name="plan", pattern="a.md"),
                    ArtifactConfig(name="plan", pattern="b.md"),
                    ArtifactConfig(name="code", pattern="c.md"),
                    ArtifactConfig(name="code", pattern="d.md"),
                ]
            )
        error_msg = str(exc_info.value)
        assert "code" in error_msg
        assert "plan" in error_msg

    def test_unique_artifact_names_accepted(self) -> None:
        """CommandConfig accepts unique artifact names."""
        config = CommandConfig(
            artifacts=[
                ArtifactConfig(name="plan", pattern="plan.md"),
                ArtifactConfig(name="code", pattern="code/*.py"),
            ]
        )
        assert len(config.artifacts) == 2

    def test_extra_fields_rejected(self) -> None:
        """CommandConfig rejects unknown fields (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            CommandConfig(unknown_field="value")  # type: ignore[call-arg]
        assert "extra" in str(exc_info.value).lower()

    def test_nested_llm_config_validated(self) -> None:
        """CommandConfig validates nested PhaseLLMConfig."""
        with pytest.raises(ValidationError) as exc_info:
            CommandConfig(llm=PhaseLLMConfig(temperature=2.0))  # invalid
        assert "less than or equal to 1" in str(exc_info.value)

    def test_valid_complete_config(self) -> None:
        """CommandConfig accepts valid complete configuration."""
        config = CommandConfig(
            timeout_seconds=600,
            input_files={"prd": "docs/prd.md"},
            llm=PhaseLLMConfig(model="claude-3-opus", temperature=0.7),
            artifacts=[
                ArtifactConfig(
                    name="plan",
                    pattern="output/plan.md",
                    required=True,
                    description="Implementation plan",
                )
            ],
            pre_hook="echo 'start'",
            post_hook="echo 'done'",
        )
        assert config.timeout_seconds == 600
        assert config.input_files == {"prd": "docs/prd.md"}
        assert config.llm.model == "claude-3-opus"
        assert config.llm.temperature == 0.7
        assert len(config.artifacts) == 1
        assert config.artifacts[0].name == "plan"


class TestDocMappingConfig:
    """Tests for DocMappingConfig validation rules."""

    def test_source_pattern_required(self) -> None:
        """DocMappingConfig requires source_pattern field."""
        with pytest.raises(ValidationError) as exc_info:
            DocMappingConfig(docs_dir="docs/architecture")  # type: ignore[call-arg]
        assert "source_pattern" in str(exc_info.value).lower()

    def test_docs_dir_required(self) -> None:
        """DocMappingConfig requires docs_dir field."""
        with pytest.raises(ValidationError) as exc_info:
            DocMappingConfig(source_pattern="src/**/*.py")  # type: ignore[call-arg]
        assert "docs_dir" in str(exc_info.value).lower()

    def test_source_pattern_empty_string_rejected(self) -> None:
        """DocMappingConfig rejects empty source_pattern string."""
        with pytest.raises(ValidationError) as exc_info:
            DocMappingConfig(source_pattern="", docs_dir="docs/arch")
        assert (
            "min_length" in str(exc_info.value).lower()
            or "string_too_short" in str(exc_info.value).lower()
        )

    def test_docs_dir_empty_string_rejected(self) -> None:
        """DocMappingConfig rejects empty docs_dir string."""
        with pytest.raises(ValidationError) as exc_info:
            DocMappingConfig(source_pattern="src/**/*.py", docs_dir="")
        assert (
            "min_length" in str(exc_info.value).lower()
            or "string_too_short" in str(exc_info.value).lower()
        )

    def test_extra_fields_rejected(self) -> None:
        """DocMappingConfig rejects unknown fields (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            DocMappingConfig(
                source_pattern="src/**/*.py",
                docs_dir="docs/arch",
                unknown="value",  # type: ignore[call-arg]
            )
        assert "extra" in str(exc_info.value).lower()

    def test_valid_mapping(self) -> None:
        """DocMappingConfig accepts valid mapping."""
        mapping = DocMappingConfig(
            source_pattern="src/adw/core/**/*.py",
            docs_dir="docs/architecture/deep-dive",
        )
        assert mapping.source_pattern == "src/adw/core/**/*.py"
        assert mapping.docs_dir == "docs/architecture/deep-dive"


class TestDocumentCommandConfig:
    """Tests for DocumentCommandConfig validation rules."""

    def test_inherits_from_command_config(self) -> None:
        """DocumentCommandConfig inherits from CommandConfig."""
        config = DocumentCommandConfig(timeout_seconds=600)
        assert config.timeout_seconds == 600
        assert config.enabled is True  # inherited default

    def test_doc_mappings_defaults_to_none(self) -> None:
        """DocumentCommandConfig doc_mappings defaults to None."""
        config = DocumentCommandConfig()
        assert config.doc_mappings is None

    def test_accepts_valid_doc_mappings(self) -> None:
        """DocumentCommandConfig accepts valid doc_mappings list."""
        config = DocumentCommandConfig(
            doc_mappings=[
                DocMappingConfig(
                    source_pattern="src/core/**/*.py",
                    docs_dir="docs/architecture",
                ),
                DocMappingConfig(
                    source_pattern="src/cli/**/*.py",
                    docs_dir="docs/cli",
                ),
            ]
        )
        assert config.doc_mappings is not None
        assert len(config.doc_mappings) == 2
        assert config.doc_mappings[0].source_pattern == "src/core/**/*.py"
        assert config.doc_mappings[1].docs_dir == "docs/cli"

    def test_extra_fields_rejected(self) -> None:
        """DocumentCommandConfig rejects unknown fields (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            DocumentCommandConfig(unknown_field="value")  # type: ignore[call-arg]
        assert "extra" in str(exc_info.value).lower()

    def test_nested_mapping_validation(self) -> None:
        """DocumentCommandConfig validates nested DocMappingConfig."""
        with pytest.raises(ValidationError) as exc_info:
            DocumentCommandConfig(
                doc_mappings=[
                    DocMappingConfig(
                        source_pattern="",  # invalid empty
                        docs_dir="docs/arch",
                    )
                ]
            )
        assert (
            "min_length" in str(exc_info.value).lower()
            or "string_too_short" in str(exc_info.value).lower()
        )

    def test_valid_complete_document_config(self) -> None:
        """DocumentCommandConfig accepts valid complete configuration."""
        config = DocumentCommandConfig(
            timeout_seconds=600,
            enabled=True,
            doc_mappings=[
                DocMappingConfig(
                    source_pattern="src/adw/core/**/*.py",
                    docs_dir="docs/architecture/deep-dive",
                )
            ],
            artifacts=[
                ArtifactConfig(
                    name="document_output",
                    pattern="document_output.md",
                    required=True,
                )
            ],
        )
        assert config.timeout_seconds == 600
        assert config.doc_mappings is not None
        assert len(config.doc_mappings) == 1
        assert config.artifacts is not None
        assert len(config.artifacts) == 1
