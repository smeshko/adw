# Test Reduction Notes per ADR-001:
# Only testing validation logic, boundary conditions, and error handling.
# NOT testing: default values, simple attribute assignment, Pydantic serialization.

"""Tests for command models (CommandConfig, PhaseLLMConfig, DocumentCommandConfig)."""

import pytest
from pydantic import ValidationError

from adw.models.command import (
    CommandConfig,
    DocMappingConfig,
    DocumentCommandConfig,
    PhaseLLMConfig,
)


class TestPhaseLLMConfig:
    """Tests for PhaseLLMConfig validation rules."""

    def test_extra_fields_rejected(self) -> None:
        """PhaseLLMConfig rejects unknown fields (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            PhaseLLMConfig(model="opus", unknown_field="value")  # type: ignore[call-arg]
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

    def test_extra_fields_rejected(self) -> None:
        """CommandConfig rejects unknown fields (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            CommandConfig(unknown_field="value")  # type: ignore[call-arg]
        assert "extra" in str(exc_info.value).lower()

    def test_valid_complete_config(self) -> None:
        """CommandConfig accepts valid complete configuration."""
        config = CommandConfig(
            timeout_seconds=600,
            input_files={"prd": "docs/prd.md"},
            llm=PhaseLLMConfig(model="claude-3-opus"),
        )
        assert config.timeout_seconds == 600
        assert config.input_files == {"prd": "docs/prd.md"}
        assert config.llm.model == "claude-3-opus"


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
        )
        assert config.timeout_seconds == 600
        assert config.doc_mappings is not None
        assert len(config.doc_mappings) == 1
