"""Evidence optimizer for ADW.

This module provides the EvidenceOptimizer class for compressing and
optimizing evidence files to reduce storage and transfer size.

Features:
- Image compression (PNG/JPEG) using Pillow (optional dependency)
- Text file truncation with head/tail preservation
- JSON minification
- Size monitoring with configurable warning thresholds
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from adw.logging import LogCategory, get_logger
from adw.models.evidence import (
    FileOptimization,
    OptimizationConfig,
    OptimizationReport,
)

# Check if Pillow is available
try:
    from PIL import Image

    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


class EvidenceOptimizer:
    """Optimizer for evidence files.

    Compresses and optimizes evidence files to reduce storage and transfer size.
    Handles different file types with appropriate strategies:
    - Images: Compress with Pillow (if available)
    - Text: Truncate large files preserving head/tail
    - JSON: Minify by removing whitespace

    Attributes:
        config: Optimization configuration settings

    Example:
        >>> optimizer = EvidenceOptimizer()
        >>> report = optimizer.optimize_directory(
        ...     Path(".adw/runs/01HQ/evidence"),
        ...     run_id="01HQ..."
        ... )
    """

    # File extensions by category
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
    TEXT_EXTENSIONS = {".txt", ".log", ".md"}
    JSON_EXTENSIONS = {".json"}

    # Default truncation settings
    DEFAULT_KEEP_HEAD_LINES = 500
    DEFAULT_KEEP_TAIL_LINES = 500

    def __init__(self, config: OptimizationConfig | None = None) -> None:
        """Initialize the evidence optimizer.

        Args:
            config: Optimization configuration. Uses defaults if not provided.
        """
        self.config = config or OptimizationConfig()
        self._logger = get_logger()

    def optimize_directory(
        self,
        directory: Path,
        run_id: str,
    ) -> OptimizationReport:
        """Optimize all evidence files in a directory.

        Processes all supported file types in the directory and subdirectories,
        applying appropriate optimization strategies.

        Args:
            directory: Path to the evidence directory
            run_id: Unique identifier for the run

        Returns:
            OptimizationReport with complete optimization results
        """
        if not self.config.enabled:
            self._logger.info(
                LogCategory.STATE,
                "Evidence optimization disabled",
            )
            # Return empty report when disabled
            total_files = sum(1 for _ in directory.rglob("*") if _.is_file())
            return OptimizationReport(
                run_id=run_id,
                total_files=total_files,
                files_optimized=0,
                files_skipped=total_files,
                original_total_bytes=self.calculate_directory_size(directory),
                optimized_total_bytes=self.calculate_directory_size(directory),
                total_savings_bytes=0,
                total_savings_percent=0.0,
            )

        self._logger.info(
            LogCategory.STATE,
            f"Starting evidence optimization for {directory}",
        )

        image_results: list[FileOptimization] = []
        text_results: list[FileOptimization] = []
        json_results: list[FileOptimization] = []

        original_total = 0
        optimized_total = 0

        # Process all files
        for file_path in directory.rglob("*"):
            if not file_path.is_file():
                continue

            suffix = file_path.suffix.lower()
            original_size = file_path.stat().st_size
            original_total += original_size

            if suffix in self.IMAGE_EXTENSIONS:
                result = self.compress_image(file_path)
                image_results.append(result)
            elif suffix in self.TEXT_EXTENSIONS:
                result = self.truncate_text(file_path)
                text_results.append(result)
            elif suffix in self.JSON_EXTENSIONS:
                result = self.minify_json(file_path)
                json_results.append(result)
            else:
                continue

            # Update optimized total
            if result.optimized and result.optimized_size is not None:
                optimized_total += result.optimized_size
            else:
                optimized_total += original_size

        # Calculate statistics
        all_results = image_results + text_results + json_results
        total_files = len(all_results)
        files_optimized = sum(1 for r in all_results if r.optimized)
        files_skipped = total_files - files_optimized
        total_savings = original_total - optimized_total
        savings_percent = (
            (total_savings / original_total * 100) if original_total > 0 else 0.0
        )

        # Check for size warning
        size_warning = False
        warning_threshold_mb = None
        if self.config.warn_total_size_mb > 0:
            threshold_bytes = self.config.warn_total_size_mb * 1024 * 1024
            if optimized_total > threshold_bytes:
                size_warning = True
                warning_threshold_mb = self.config.warn_total_size_mb
                self._logger.warn(
                    LogCategory.STATE,
                    f"Evidence directory size ({optimized_total / 1024 / 1024:.1f} MB) "
                    f"exceeds threshold ({self.config.warn_total_size_mb} MB)",
                )

        self._logger.info(
            LogCategory.STATE,
            f"Optimization complete: {files_optimized}/{total_files} files optimized, "
            f"saved {self._format_size(total_savings)} ({savings_percent:.1f}%)",
        )

        return OptimizationReport(
            run_id=run_id,
            optimized_at=datetime.now(UTC),
            total_files=total_files,
            files_optimized=files_optimized,
            files_skipped=files_skipped,
            original_total_bytes=original_total,
            optimized_total_bytes=optimized_total,
            total_savings_bytes=total_savings,
            total_savings_percent=round(savings_percent, 1),
            image_optimization=image_results,
            text_optimization=text_results,
            json_optimization=json_results,
            size_warning=size_warning,
            warning_threshold_mb=warning_threshold_mb,
        )

    def compress_image(
        self,
        path: Path,
        quality: int | None = None,
    ) -> FileOptimization:
        """Compress an image file.

        Uses Pillow to compress PNG/JPEG images with configurable quality.
        Iteratively reduces quality until max_image_size_kb is met.
        Falls back gracefully when Pillow is not installed.

        Args:
            path: Path to the image file
            quality: JPEG quality (1-100). Uses config default if not specified.

        Returns:
            FileOptimization with compression results
        """
        if not PILLOW_AVAILABLE:
            return FileOptimization(
                path=str(path),
                optimized=False,
                reason="Pillow not installed",
            )

        quality = quality or self.config.image_quality
        original_size = path.stat().st_size
        max_size_bytes = self.config.max_image_size_kb * 1024

        try:
            with Image.open(path) as img:
                # Convert RGBA to RGB for JPEG compression
                if img.mode == "RGBA" and path.suffix.lower() in {".jpg", ".jpeg"}:
                    img = img.convert("RGB")

                # Save with initial optimization
                img.save(path, optimize=True, quality=quality)

                # Iteratively reduce quality if still over max size (max 5 iterations)
                current_size = path.stat().st_size
                min_quality = 20  # Don't go below 20% quality
                iterations = 0
                max_iterations = 5

                while (
                    current_size > max_size_bytes
                    and quality > min_quality
                    and iterations < max_iterations
                ):
                    quality = max(min_quality, quality - 15)
                    img.save(path, optimize=True, quality=quality)
                    current_size = path.stat().st_size
                    iterations += 1

            optimized_size = path.stat().st_size
            savings = original_size - optimized_size

            # Only count as optimized if we actually saved space
            if savings > 0:
                return FileOptimization(
                    path=str(path),
                    optimized=True,
                    original_size=original_size,
                    optimized_size=optimized_size,
                    savings_bytes=savings,
                    savings_percent=round(savings / original_size * 100, 1),
                )
            else:
                return FileOptimization(
                    path=str(path),
                    optimized=False,
                    reason="No size reduction achieved",
                    original_size=original_size,
                )

        except Exception as e:
            self._logger.warn(
                LogCategory.STATE,
                f"Failed to compress image {path}: {e}",
            )
            return FileOptimization(
                path=str(path),
                optimized=False,
                reason=f"Compression error: {e}",
                original_size=original_size,
            )

    def truncate_text(
        self,
        path: Path,
        keep_head_lines: int | None = None,
        keep_tail_lines: int | None = None,
    ) -> FileOptimization:
        """Truncate a large text file.

        Preserves the first and last N lines, replacing middle content
        with a truncation marker that includes the original size.

        Args:
            path: Path to the text file
            keep_head_lines: Lines to keep from start (default: 500)
            keep_tail_lines: Lines to keep from end (default: 500)

        Returns:
            FileOptimization with truncation results
        """
        keep_head = keep_head_lines or self.DEFAULT_KEEP_HEAD_LINES
        keep_tail = keep_tail_lines or self.DEFAULT_KEEP_TAIL_LINES

        original_size = path.stat().st_size
        max_size_bytes = self.config.max_text_size_kb * 1024

        # Check if file is under threshold
        if original_size <= max_size_bytes:
            return FileOptimization(
                path=str(path),
                optimized=False,
                reason="Under size threshold",
                original_size=original_size,
            )

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            lines = content.split("\n")
            total_lines = len(lines)

            # Check if file has enough lines to truncate
            if total_lines <= keep_head + keep_tail:
                return FileOptimization(
                    path=str(path),
                    optimized=False,
                    reason="Not enough lines to truncate",
                    original_size=original_size,
                )

            # Build truncated content
            head = "\n".join(lines[:keep_head])
            tail = "\n".join(lines[-keep_tail:])
            truncated_count = total_lines - keep_head - keep_tail

            truncated_content = (
                f"{head}\n\n"
                f"... [{truncated_count:,} lines truncated - "
                f"original size: {original_size:,} bytes] ...\n\n"
                f"{tail}"
            )

            path.write_text(truncated_content, encoding="utf-8")
            optimized_size = path.stat().st_size
            savings = original_size - optimized_size

            return FileOptimization(
                path=str(path),
                optimized=True,
                original_size=original_size,
                optimized_size=optimized_size,
                savings_bytes=savings,
                savings_percent=round(savings / original_size * 100, 1),
                truncated_lines=truncated_count,
            )

        except Exception as e:
            self._logger.warn(
                LogCategory.STATE,
                f"Failed to truncate text file {path}: {e}",
            )
            return FileOptimization(
                path=str(path),
                optimized=False,
                reason=f"Truncation error: {e}",
                original_size=original_size,
            )

    def minify_json(self, path: Path) -> FileOptimization:
        """Minify a JSON file.

        Removes whitespace from JSON files to reduce size.
        Optionally preserves manifest.json in readable format.

        Args:
            path: Path to the JSON file

        Returns:
            FileOptimization with minification results
        """
        original_size = path.stat().st_size

        # Check if this is manifest.json and should be kept pretty
        if self.config.keep_manifest_pretty and path.name == "manifest.json":
            return FileOptimization(
                path=str(path),
                optimized=False,
                reason="Manifest kept pretty-printed",
                original_size=original_size,
            )

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            # Minify by removing whitespace
            minified = json.dumps(data, separators=(",", ":"))
            path.write_text(minified, encoding="utf-8")

            optimized_size = path.stat().st_size
            savings = original_size - optimized_size

            # Only count as optimized if we saved space
            if savings > 0:
                return FileOptimization(
                    path=str(path),
                    optimized=True,
                    original_size=original_size,
                    optimized_size=optimized_size,
                    savings_bytes=savings,
                    savings_percent=round(savings / original_size * 100, 1),
                )
            else:
                return FileOptimization(
                    path=str(path),
                    optimized=False,
                    reason="No size reduction achieved",
                    original_size=original_size,
                )

        except json.JSONDecodeError as e:
            self._logger.warn(
                LogCategory.STATE,
                f"Invalid JSON in {path}: {e}",
            )
            return FileOptimization(
                path=str(path),
                optimized=False,
                reason=f"Invalid JSON: {e}",
                original_size=original_size,
            )
        except Exception as e:
            self._logger.warn(
                LogCategory.STATE,
                f"Failed to minify JSON {path}: {e}",
            )
            return FileOptimization(
                path=str(path),
                optimized=False,
                reason=f"Minification error: {e}",
                original_size=original_size,
            )

    def calculate_directory_size(self, directory: Path) -> int:
        """Calculate total size of a directory.

        Recursively calculates the total size of all files in a directory.

        Args:
            directory: Path to the directory

        Returns:
            Total size in bytes
        """
        total_size = 0
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size

    def calculate_type_breakdown(
        self, directory: Path
    ) -> dict[str, int]:
        """Calculate size breakdown by file type.

        Groups files by extension and calculates total size for each type.

        Args:
            directory: Path to the directory

        Returns:
            Dictionary mapping file type to total size in bytes
        """
        breakdown: dict[str, int] = {}

        for file_path in directory.rglob("*"):
            if not file_path.is_file():
                continue

            suffix = file_path.suffix.lower()
            if not suffix:
                suffix = "no_extension"
            else:
                suffix = suffix.lstrip(".")

            size = file_path.stat().st_size
            breakdown[suffix] = breakdown.get(suffix, 0) + size

        return breakdown

    def _format_size(self, size_bytes: int) -> str:
        """Format bytes as human-readable string.

        Args:
            size_bytes: Size in bytes

        Returns:
            Human-readable size string (e.g., "1.5 MB")
        """
        for unit in ["B", "KB", "MB", "GB"]:
            if abs(size_bytes) < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
