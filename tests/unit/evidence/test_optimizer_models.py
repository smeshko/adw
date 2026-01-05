"""Tests for evidence optimization models.

This module tests the Pydantic models used for evidence optimization:
- OptimizationConfig: Configuration for evidence optimization
- FileOptimization: Result of optimizing a single file
- OptimizationReport: Complete optimization report for a run
"""

from datetime import datetime

from adw.models.evidence import (
    FileOptimization,
    OptimizationConfig,
    OptimizationReport,
)

# =============================================================================
# OptimizationConfig Tests
# =============================================================================


class TestOptimizationConfig:
    """Tests for OptimizationConfig model."""

    def test_default_values(self) -> None:
        """Test that OptimizationConfig has sensible defaults."""
        config = OptimizationConfig()

        assert config.enabled is True
        assert config.max_image_size_kb == 500
        assert config.max_text_size_kb == 100
        assert config.image_quality == 80
        assert config.compress_json is True
        assert config.keep_manifest_pretty is True
        assert config.warn_total_size_mb == 10

    def test_custom_values(self) -> None:
        """Test creating config with custom values."""
        config = OptimizationConfig(
            enabled=False,
            max_image_size_kb=1000,
            max_text_size_kb=200,
            image_quality=90,
            compress_json=False,
            keep_manifest_pretty=False,
            warn_total_size_mb=20,
        )

        assert config.enabled is False
        assert config.max_image_size_kb == 1000
        assert config.max_text_size_kb == 200
        assert config.image_quality == 90
        assert config.compress_json is False
        assert config.keep_manifest_pretty is False
        assert config.warn_total_size_mb == 20

    def test_json_serialization(self) -> None:
        """Test that config serializes to JSON correctly."""
        config = OptimizationConfig()
        json_data = config.model_dump_json()

        assert "enabled" in json_data
        assert "max_image_size_kb" in json_data
        assert "image_quality" in json_data


# =============================================================================
# FileOptimization Tests
# =============================================================================


class TestFileOptimization:
    """Tests for FileOptimization model."""

    def test_minimal_file_optimization(self) -> None:
        """Test creating a minimal file optimization result."""
        result = FileOptimization(
            path="screenshots/home.png",
            optimized=True,
        )

        assert result.path == "screenshots/home.png"
        assert result.optimized is True
        assert result.reason is None
        assert result.original_size is None
        assert result.optimized_size is None

    def test_full_file_optimization(self) -> None:
        """Test creating a full file optimization result."""
        result = FileOptimization(
            path="screenshots/home.png",
            optimized=True,
            original_size=1048576,
            optimized_size=262144,
            savings_bytes=786432,
            savings_percent=75.0,
        )

        assert result.path == "screenshots/home.png"
        assert result.optimized is True
        assert result.original_size == 1048576
        assert result.optimized_size == 262144
        assert result.savings_bytes == 786432
        assert result.savings_percent == 75.0

    def test_skipped_file_optimization(self) -> None:
        """Test creating a skipped file optimization result."""
        result = FileOptimization(
            path="cli/version.txt",
            optimized=False,
            reason="Under size threshold",
            original_size=1024,
        )

        assert result.optimized is False
        assert result.reason == "Under size threshold"
        assert result.original_size == 1024

    def test_truncation_file_optimization(self) -> None:
        """Test creating a truncation result with line count."""
        result = FileOptimization(
            path="cli/large_output.txt",
            optimized=True,
            original_size=524288,
            optimized_size=102400,
            savings_bytes=421888,
            truncated_lines=5000,
        )

        assert result.truncated_lines == 5000
        assert result.savings_bytes == 421888

    def test_pillow_not_available_optimization(self) -> None:
        """Test creating a result when Pillow is not installed."""
        result = FileOptimization(
            path="screenshots/home.png",
            optimized=False,
            reason="Pillow not installed",
        )

        assert result.optimized is False
        assert result.reason == "Pillow not installed"


# =============================================================================
# OptimizationReport Tests
# =============================================================================


class TestOptimizationReport:
    """Tests for OptimizationReport model."""

    def test_empty_report(self) -> None:
        """Test creating an empty optimization report."""
        report = OptimizationReport(
            run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
            total_files=0,
            files_optimized=0,
            files_skipped=0,
            original_total_bytes=0,
            optimized_total_bytes=0,
            total_savings_bytes=0,
            total_savings_percent=0.0,
        )

        assert report.run_id == "01HQXK5P3Z7V8R2M4N6T9W1Y3C"
        assert report.total_files == 0
        assert report.files_optimized == 0
        assert report.size_warning is False

    def test_full_report(self) -> None:
        """Test creating a full optimization report."""
        image_opt = FileOptimization(
            path="screenshots/home.png",
            optimized=True,
            original_size=1048576,
            optimized_size=262144,
            savings_bytes=786432,
            savings_percent=75.0,
        )

        text_opt = FileOptimization(
            path="cli/large_output.txt",
            optimized=True,
            original_size=524288,
            optimized_size=102400,
            savings_bytes=421888,
            truncated_lines=5000,
        )

        json_opt = FileOptimization(
            path="api/health.json",
            optimized=True,
            original_size=2048,
            optimized_size=512,
            savings_bytes=1536,
        )

        report = OptimizationReport(
            run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
            total_files=12,
            files_optimized=8,
            files_skipped=4,
            original_total_bytes=5242880,
            optimized_total_bytes=2097152,
            total_savings_bytes=3145728,
            total_savings_percent=60.0,
            image_optimization=[image_opt],
            text_optimization=[text_opt],
            json_optimization=[json_opt],
        )

        assert report.total_files == 12
        assert report.files_optimized == 8
        assert report.files_skipped == 4
        assert report.total_savings_percent == 60.0
        assert len(report.image_optimization) == 1
        assert len(report.text_optimization) == 1
        assert len(report.json_optimization) == 1

    def test_size_warning(self) -> None:
        """Test report with size warning enabled."""
        report = OptimizationReport(
            run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
            total_files=5,
            files_optimized=5,
            files_skipped=0,
            original_total_bytes=20971520,  # 20 MB
            optimized_total_bytes=15728640,  # 15 MB
            total_savings_bytes=5242880,
            total_savings_percent=25.0,
            size_warning=True,
            warning_threshold_mb=10,
        )

        assert report.size_warning is True
        assert report.warning_threshold_mb == 10

    def test_optimized_at_default(self) -> None:
        """Test that optimized_at has a default value."""
        report = OptimizationReport(
            run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
            total_files=0,
            files_optimized=0,
            files_skipped=0,
            original_total_bytes=0,
            optimized_total_bytes=0,
            total_savings_bytes=0,
            total_savings_percent=0.0,
        )

        assert report.optimized_at is not None
        assert isinstance(report.optimized_at, datetime)

    def test_json_serialization(self) -> None:
        """Test that report serializes to JSON correctly."""
        report = OptimizationReport(
            run_id="01HQXK5P3Z7V8R2M4N6T9W1Y3C",
            total_files=5,
            files_optimized=3,
            files_skipped=2,
            original_total_bytes=1000000,
            optimized_total_bytes=500000,
            total_savings_bytes=500000,
            total_savings_percent=50.0,
        )

        json_data = report.model_dump_json()

        assert "run_id" in json_data
        assert "total_files" in json_data
        assert "total_savings_percent" in json_data
        assert "image_optimization" in json_data
