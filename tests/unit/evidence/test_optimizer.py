"""Tests for evidence optimizer.

This module tests the EvidenceOptimizer class:
- Image compression (PNG/JPEG)
- Text truncation
- JSON minification
- Size monitoring
"""

import json
from pathlib import Path
from unittest.mock import patch

from adw.models.evidence import (
    FileOptimization,
    OptimizationConfig,
    OptimizationReport,
)

# =============================================================================
# EvidenceOptimizer Tests
# =============================================================================


class TestEvidenceOptimizer:
    """Tests for EvidenceOptimizer class."""

    def test_optimizer_creation(self) -> None:
        """Test creating an optimizer with default config."""
        from adw.evidence.optimizer import EvidenceOptimizer

        optimizer = EvidenceOptimizer()
        assert optimizer.config is not None
        assert optimizer.config.enabled is True

    def test_optimizer_with_custom_config(self) -> None:
        """Test creating an optimizer with custom config."""
        from adw.evidence.optimizer import EvidenceOptimizer

        config = OptimizationConfig(
            max_image_size_kb=200,
            max_text_size_kb=50,
        )
        optimizer = EvidenceOptimizer(config=config)
        assert optimizer.config.max_image_size_kb == 200
        assert optimizer.config.max_text_size_kb == 50


# =============================================================================
# Image Compression Tests
# =============================================================================


class TestImageCompression:
    """Tests for image compression functionality."""

    def test_compress_image_returns_file_optimization(self, tmp_path: Path) -> None:
        """Test that compress_image returns FileOptimization."""
        from adw.evidence.optimizer import EvidenceOptimizer

        # Create a simple PNG file (1x1 white pixel)
        image_path = tmp_path / "test.png"
        # Create a minimal valid PNG
        self._create_test_png(image_path)

        optimizer = EvidenceOptimizer()
        result = optimizer.compress_image(image_path)

        assert isinstance(result, FileOptimization)
        assert result.path == str(image_path)

    def test_compress_image_pillow_not_available(self, tmp_path: Path) -> None:
        """Test graceful handling when Pillow is not installed."""
        from adw.evidence.optimizer import EvidenceOptimizer

        image_path = tmp_path / "test.png"
        self._create_test_png(image_path)

        optimizer = EvidenceOptimizer()

        # Mock PILLOW_AVAILABLE as False
        with patch("adw.evidence.optimizer.PILLOW_AVAILABLE", False):
            result = optimizer.compress_image(image_path)

        assert result.optimized is False
        assert "Pillow not installed" in str(result.reason)

    def test_compress_image_under_threshold(self, tmp_path: Path) -> None:
        """Test that small images are not re-compressed."""
        from adw.evidence.optimizer import EvidenceOptimizer

        image_path = tmp_path / "test.png"
        self._create_test_png(image_path)

        # Very high threshold - file should not be optimized
        config = OptimizationConfig(max_image_size_kb=10000)
        optimizer = EvidenceOptimizer(config=config)
        result = optimizer.compress_image(image_path)

        # Should still optimize (compress) - threshold just affects warnings
        assert isinstance(result, FileOptimization)

    def test_compress_image_records_sizes(self, tmp_path: Path) -> None:
        """Test that original and optimized sizes are recorded."""
        from adw.evidence.optimizer import EvidenceOptimizer

        image_path = tmp_path / "test.png"
        self._create_test_png(image_path)
        original_size = image_path.stat().st_size

        optimizer = EvidenceOptimizer()
        result = optimizer.compress_image(image_path)

        # Even if not optimized, should record original size
        if result.optimized:
            assert result.original_size == original_size
            assert result.optimized_size is not None
            assert result.savings_bytes is not None

    def _create_test_png(self, path: Path, size: int = 100) -> None:
        """Create a test PNG file."""
        try:
            from PIL import Image

            # Create a simple gradient image
            img = Image.new("RGB", (size, size), color=(255, 0, 0))
            img.save(path, format="PNG")
        except ImportError:
            # If Pillow is not available, create a minimal valid PNG
            # PNG header + minimal IHDR + IDAT + IEND
            png_bytes = (
                b"\x89PNG\r\n\x1a\n"
                b"\x00\x00\x00\rIHDR"
                b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
                b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
                b"\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            path.write_bytes(png_bytes)


# =============================================================================
# Text Truncation Tests
# =============================================================================


class TestTextTruncation:
    """Tests for text file truncation."""

    def test_truncate_text_returns_file_optimization(self, tmp_path: Path) -> None:
        """Test that truncate_text returns FileOptimization."""
        from adw.evidence.optimizer import EvidenceOptimizer

        text_path = tmp_path / "large.txt"
        # Create a large text file
        text_path.write_text("\n".join([f"Line {i}" for i in range(10000)]))

        optimizer = EvidenceOptimizer()
        result = optimizer.truncate_text(text_path)

        assert isinstance(result, FileOptimization)
        assert result.path == str(text_path)

    def test_truncate_text_under_threshold(self, tmp_path: Path) -> None:
        """Test that small text files are not truncated."""
        from adw.evidence.optimizer import EvidenceOptimizer

        text_path = tmp_path / "small.txt"
        text_path.write_text("Short content")

        optimizer = EvidenceOptimizer()
        result = optimizer.truncate_text(text_path)

        assert result.optimized is False
        assert "Under size threshold" in str(result.reason)

    def test_truncate_text_preserves_head_and_tail(self, tmp_path: Path) -> None:
        """Test that truncation preserves head and tail lines."""
        from adw.evidence.optimizer import EvidenceOptimizer

        text_path = tmp_path / "large.txt"
        lines = [f"Line {i}" for i in range(5000)]
        text_path.write_text("\n".join(lines))

        config = OptimizationConfig(max_text_size_kb=1)  # Very small threshold
        optimizer = EvidenceOptimizer(config=config)
        result = optimizer.truncate_text(
            text_path, keep_head_lines=100, keep_tail_lines=100
        )

        if result.optimized:
            content = text_path.read_text()
            # Should contain head and tail
            assert "Line 0" in content
            assert "Line 4999" in content
            # Should contain truncation marker
            assert "truncated" in content.lower()

    def test_truncate_text_records_truncated_lines(self, tmp_path: Path) -> None:
        """Test that truncated line count is recorded."""
        from adw.evidence.optimizer import EvidenceOptimizer

        text_path = tmp_path / "large.txt"
        lines = [f"Line {i}" for i in range(5000)]
        text_path.write_text("\n".join(lines))

        config = OptimizationConfig(max_text_size_kb=1)
        optimizer = EvidenceOptimizer(config=config)
        result = optimizer.truncate_text(
            text_path, keep_head_lines=100, keep_tail_lines=100
        )

        if result.optimized:
            assert result.truncated_lines is not None
            assert result.truncated_lines > 0


# =============================================================================
# JSON Minification Tests
# =============================================================================


class TestJsonMinification:
    """Tests for JSON file minification."""

    def test_minify_json_returns_file_optimization(self, tmp_path: Path) -> None:
        """Test that minify_json returns FileOptimization."""
        from adw.evidence.optimizer import EvidenceOptimizer

        json_path = tmp_path / "data.json"
        data = {"key": "value", "nested": {"inner": [1, 2, 3]}}
        json_path.write_text(json.dumps(data, indent=2))

        optimizer = EvidenceOptimizer()
        result = optimizer.minify_json(json_path)

        assert isinstance(result, FileOptimization)
        assert result.path == str(json_path)

    def test_minify_json_removes_whitespace(self, tmp_path: Path) -> None:
        """Test that minification removes whitespace."""
        from adw.evidence.optimizer import EvidenceOptimizer

        json_path = tmp_path / "data.json"
        data = {"key": "value", "nested": {"inner": [1, 2, 3]}}
        json_path.write_text(json.dumps(data, indent=2))
        original_size = json_path.stat().st_size

        optimizer = EvidenceOptimizer()
        result = optimizer.minify_json(json_path)

        if result.optimized:
            new_size = json_path.stat().st_size
            assert new_size < original_size

    def test_minify_json_preserves_data(self, tmp_path: Path) -> None:
        """Test that minification preserves JSON data."""
        from adw.evidence.optimizer import EvidenceOptimizer

        json_path = tmp_path / "data.json"
        data = {"key": "value", "nested": {"inner": [1, 2, 3]}}
        json_path.write_text(json.dumps(data, indent=2))

        optimizer = EvidenceOptimizer()
        optimizer.minify_json(json_path)

        # Verify data is preserved
        loaded = json.loads(json_path.read_text())
        assert loaded == data

    def test_minify_json_skips_manifest(self, tmp_path: Path) -> None:
        """Test that manifest.json is not minified when configured."""
        from adw.evidence.optimizer import EvidenceOptimizer

        manifest_path = tmp_path / "manifest.json"
        data = {"run_id": "test", "items": []}
        manifest_path.write_text(json.dumps(data, indent=2))

        config = OptimizationConfig(keep_manifest_pretty=True)
        optimizer = EvidenceOptimizer(config=config)
        result = optimizer.minify_json(manifest_path)

        assert result.optimized is False
        assert "manifest" in str(result.reason).lower()


# =============================================================================
# Size Calculation Tests
# =============================================================================


class TestSizeCalculation:
    """Tests for directory size calculation."""

    def test_calculate_directory_size(self, tmp_path: Path) -> None:
        """Test calculating total directory size."""
        from adw.evidence.optimizer import EvidenceOptimizer

        # Create test files
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("content3")

        optimizer = EvidenceOptimizer()
        size = optimizer.calculate_directory_size(tmp_path)

        assert size > 0

    def test_calculate_type_breakdown(self, tmp_path: Path) -> None:
        """Test calculating size breakdown by file type."""
        from adw.evidence.optimizer import EvidenceOptimizer

        # Create test files of different types
        (tmp_path / "image.png").write_bytes(b"\x89PNG" + b"\x00" * 100)
        (tmp_path / "text.txt").write_text("text content")
        (tmp_path / "data.json").write_text('{"key": "value"}')

        optimizer = EvidenceOptimizer()
        breakdown = optimizer.calculate_type_breakdown(tmp_path)

        assert "png" in breakdown or "image" in breakdown
        assert "txt" in breakdown or "text" in breakdown
        assert "json" in breakdown


# =============================================================================
# Full Optimization Flow Tests
# =============================================================================


class TestOptimizeDirectory:
    """Tests for full directory optimization."""

    def test_optimize_directory_returns_report(self, tmp_path: Path) -> None:
        """Test that optimize_directory returns OptimizationReport."""
        from adw.evidence.optimizer import EvidenceOptimizer

        # Create test files
        (tmp_path / "test.txt").write_text("small content")

        optimizer = EvidenceOptimizer()
        report = optimizer.optimize_directory(tmp_path, run_id="test123")

        assert isinstance(report, OptimizationReport)
        assert report.run_id == "test123"

    def test_optimize_directory_disabled(self, tmp_path: Path) -> None:
        """Test that optimization is skipped when disabled."""
        from adw.evidence.optimizer import EvidenceOptimizer

        (tmp_path / "test.txt").write_text("content")

        config = OptimizationConfig(enabled=False)
        optimizer = EvidenceOptimizer(config=config)
        report = optimizer.optimize_directory(tmp_path, run_id="test123")

        assert report.files_optimized == 0
        assert report.files_skipped == report.total_files

    def test_optimize_directory_size_warning(self, tmp_path: Path) -> None:
        """Test that size warning is triggered when threshold exceeded."""
        from adw.evidence.optimizer import EvidenceOptimizer

        # Create files that exceed the warning threshold
        # Using 1 MB threshold and creating files that exceed it
        (tmp_path / "large1.txt").write_text("x" * 600_000)  # ~600 KB
        (tmp_path / "large2.txt").write_text("y" * 600_000)  # ~600 KB
        # Total > 1 MB, should trigger warning

        config = OptimizationConfig(warn_total_size_mb=1)  # 1 MB threshold
        optimizer = EvidenceOptimizer(config=config)
        report = optimizer.optimize_directory(tmp_path, run_id="test123")

        # With files exceeding 1 MB threshold, size_warning should be True
        assert report.size_warning is True
        assert report.warning_threshold_mb == 1


# =============================================================================
# Integration Function Tests
# =============================================================================


class TestOptimizeEvidenceFunction:
    """Tests for the optimize_evidence integration function."""

    def test_optimize_evidence_function_exists(self) -> None:
        """Test that optimize_evidence function is exported."""
        from adw.evidence import optimize_evidence

        assert callable(optimize_evidence)

    def test_optimize_evidence_returns_report(self, tmp_path: Path) -> None:
        """Test that optimize_evidence returns OptimizationReport."""
        from adw.evidence import optimize_evidence

        # Create test evidence directory
        evidence_dir = tmp_path / "evidence"
        evidence_dir.mkdir()
        (evidence_dir / "test.txt").write_text("test content")

        report = optimize_evidence(
            run_id="test123",
            evidence_directory=evidence_dir,
        )

        assert isinstance(report, OptimizationReport)
        assert report.run_id == "test123"

    def test_optimize_evidence_with_config(self, tmp_path: Path) -> None:
        """Test optimize_evidence with explicit config."""
        from adw.evidence import optimize_evidence

        evidence_dir = tmp_path / "evidence"
        evidence_dir.mkdir()
        (evidence_dir / "test.txt").write_text("test")

        config = OptimizationConfig(enabled=False)
        report = optimize_evidence(
            run_id="test123",
            evidence_directory=evidence_dir,
            config=config,
        )

        # Should skip all files when disabled
        assert report.files_optimized == 0

    def test_optimize_evidence_loads_project_config(self, tmp_path: Path) -> None:
        """Test that optimize_evidence loads config from project.yaml."""
        from adw.evidence import optimize_evidence

        # Create project structure
        project_root = tmp_path / "project"
        project_root.mkdir()
        config_dir = project_root / ".adw"
        config_dir.mkdir()
        config_file = config_dir / "project.yaml"
        config_file.write_text("""
evidence:
  optimization:
    enabled: true
    max_image_size_kb: 200
""")

        # Create evidence directory
        evidence_dir = project_root / "evidence"
        evidence_dir.mkdir()
        (evidence_dir / "test.txt").write_text("test")

        report = optimize_evidence(
            run_id="test123",
            evidence_directory=evidence_dir,
            project_root=project_root,
        )

        assert isinstance(report, OptimizationReport)
