"""Validation state persistence manager.

Simplified in Epic 16 (Story 16.4) - validation state is now minimal
since the LLM handles the entire validate-fix-re-validate cycle.

State is stored in .adw/runs/<run_id>/validation/ directory:
- result.json: Final validation result
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from adw.validation.models import ValidationResult

__all__ = ["ValidationStateManager"]

logger = logging.getLogger(__name__)


class ValidationStateManager:
    """Manages validation result persistence.

    Stores validation result in the run's validation directory:
    .adw/runs/<run_id>/validation/

    Files:
    - result.json: Final validation result

    Attributes:
        run_id: The run ID this manager is associated with.
        validation_dir: Path to the validation state directory.
    """

    def __init__(self, run_id: str, base_path: Path) -> None:
        """Initialize the ValidationStateManager.

        Args:
            run_id: The run ID for state association.
            base_path: Base path to the run directory (.adw/runs/<run_id>).
        """
        self.run_id = run_id
        self.validation_dir = base_path / "validation"
        # Create validation directory if it doesn't exist
        self.validation_dir.mkdir(parents=True, exist_ok=True)

    @property
    def result_file(self) -> Path:
        """Path to the result.json file."""
        return self.validation_dir / "result.json"

    def _atomic_write(self, path: Path, content: str) -> None:
        """Write file atomically using temp file + rename pattern.

        Args:
            path: Target file path.
            content: Content to write.
        """
        temp_path = path.with_suffix(".tmp")
        try:
            with open(temp_path, "w") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            temp_path.replace(path)
            logger.debug("Atomic write completed", extra={"path": str(path)})
        except OSError:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def save_result(self, result: ValidationResult) -> None:
        """Save validation result to result.json.

        Args:
            result: ValidationResult to persist.
        """
        content = result.model_dump_json(indent=2)
        self._atomic_write(self.result_file, content)
        logger.info(
            "Validation result saved",
            extra={"passed": result.passed, "path": str(self.result_file)},
        )

    def load_result(self) -> ValidationResult | None:
        """Load validation result from result.json.

        Returns:
            ValidationResult if found and valid, None otherwise.
        """
        if not self.result_file.exists():
            logger.debug("Result file not found")
            return None

        try:
            data = json.loads(self.result_file.read_text())
            result = ValidationResult.model_validate(data)
            logger.info(
                "Validation result loaded",
                extra={"passed": result.passed, "path": str(self.result_file)},
            )
            return result
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(
                "Failed to load validation result",
                extra={"error": str(e), "path": str(self.result_file)},
            )
            return None

    def clear(self) -> None:
        """Clear validation state files.

        Called on successful completion to clean up state.
        """
        if self.result_file.exists():
            self.result_file.unlink()
            logger.debug("Removed result file", extra={"path": str(self.result_file)})

        logger.info("Validation state cleared")
