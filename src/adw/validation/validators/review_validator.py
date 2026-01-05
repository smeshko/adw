"""ReviewValidator - LLM-based code review.

This validator uses an LLM executor to perform code review
and converts findings to ValidationIssues.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from adw.validation.config import ValidationConfig
from adw.validation.models import ValidationIssue, ValidationSource

if TYPE_CHECKING:
    from adw.executors.base import LLMExecutor
    from adw.models import RunContext

logger = logging.getLogger(__name__)


# Pattern to parse review issues from LLM output
ISSUE_PATTERN = re.compile(
    r"\*?\*?\[?(HIGH|MEDIUM|LOW|CRITICAL|INFO)\]?\*?\*?\s*[:\-]?\s*(.+?)(?=\n\n|\*?\*?\[|$)",
    re.MULTILINE | re.IGNORECASE | re.DOTALL,
)

# Alternative pattern for finding issues with file paths
FILE_ISSUE_PATTERN = re.compile(
    r"\*?\*?\[?(HIGH|MEDIUM|LOW|CRITICAL|INFO)\]?\*?\*?\s*[:\-]?\s*(?:(.+?)\s+in\s+)?([^\s:]+\.(?:py|js|ts|jsx|tsx)):?(\d+)?",
    re.MULTILINE | re.IGNORECASE,
)


class ReviewValidator:
    """Validator that performs LLM-based code review.

    Uses the configured LLM executor to analyze code changes
    and identify potential issues. Findings are converted to
    ValidationIssues with source=REVIEW.

    Attributes:
        executor: LLM executor for running review prompts.
        config: ValidationConfig with review settings.
    """

    def __init__(
        self,
        executor: LLMExecutor | None = None,
        config: ValidationConfig | None = None,
    ) -> None:
        """Initialize the review validator.

        Args:
            executor: LLM executor for running review prompts.
            config: Optional configuration with review settings.
        """
        self._executor = executor
        self._config = config or ValidationConfig()

    @property
    def name(self) -> str:
        """Return the validator's name."""
        return "review"

    def validate(self, context: RunContext) -> list[ValidationIssue]:
        """Perform code review and return any issues found.

        Args:
            context: Current run context with artifacts.

        Returns:
            List of ValidationIssues for each review finding.
        """
        if not self._executor:
            return [
                ValidationIssue(
                    source=ValidationSource.REVIEW,
                    message="No LLM executor configured for code review",
                    severity="critical",
                )
            ]

        # Build review prompt
        prompt = self._build_review_prompt(context)

        logger.info("Running LLM code review")
        logger.debug(f"Review focus areas: {self._config.review_focus}")

        try:
            result = self._executor.execute(
                prompt,
                phase="validation",
            )

            if not result.success:
                return [
                    ValidationIssue(
                        source=ValidationSource.REVIEW,
                        message=f"Code review execution failed: {result.content}",
                        severity="high",
                    )
                ]

            # Parse issues from response
            issues = self._parse_review_response(result.content)

            logger.info(f"Code review found {len(issues)} issues")
            return issues

        except Exception as e:
            logger.error(f"Code review failed: {e}")
            return [
                ValidationIssue(
                    source=ValidationSource.REVIEW,
                    message=f"Code review failed with error: {e}",
                    severity="high",
                )
            ]

    def _build_review_prompt(self, context: RunContext) -> str:
        """Build the code review prompt.

        Args:
            context: Current run context.

        Returns:
            Formatted review prompt string.
        """
        focus_areas = ", ".join(self._config.review_focus)

        prompt = f"""## Code Review Request

Please review the code changes for this feature and identify any issues.

**Feature Description:** {context.feature_description}

**Focus Areas:** {focus_areas}

### Review Guidelines

1. Look for potential bugs, security vulnerabilities, and edge cases
2. Check error handling and input validation
3. Identify any performance concerns
4. Note any code quality issues

### Output Format

For each issue found, use this format:

**[SEVERITY] Issue description**
- Location: file.py:line_number (if known)
- Suggestion: How to fix it

Where SEVERITY is one of: CRITICAL, HIGH, MEDIUM, LOW, INFO

If no issues are found, state "No issues found."
"""

        return prompt

    def _parse_review_response(self, content: str) -> list[ValidationIssue]:
        """Parse LLM review response to extract issues.

        Args:
            content: LLM response content.

        Returns:
            List of ValidationIssues extracted from response.
        """
        issues: list[ValidationIssue] = []

        # Check for "no issues" indicators
        no_issue_patterns = [
            "no issues found",
            "code looks good",
            "no problems",
            "all good",
            "lgtm",
        ]
        content_lower = content.lower()
        has_no_issue_pattern = any(
            pattern in content_lower for pattern in no_issue_patterns
        )
        has_severity = any(
            sev in content_lower for sev in ["high", "medium", "critical"]
        )
        if has_no_issue_pattern and not has_severity:
            return []

        # Try to find issues with file paths first
        file_matches = FILE_ISSUE_PATTERN.findall(content)
        for match in file_matches:
            severity = match[0].lower()
            description = match[1].strip() if match[1] else ""
            file_path = match[2] if len(match) > 2 else None
            line_num = int(match[3]) if len(match) > 3 and match[3] else None

            message = description if description else f"Issue in {file_path}"

            issues.append(
                ValidationIssue(
                    source=ValidationSource.REVIEW,
                    message=message,
                    severity=severity,
                    file_path=file_path,
                    line_number=line_num,
                )
            )

        # If no file-specific issues found, try general pattern
        if not issues:
            general_matches = ISSUE_PATTERN.findall(content)
            for match in general_matches:
                severity = match[0].lower()
                description = match[1].strip()

                # Skip if description is too short or looks like a header
                if len(description) < 10 or description.startswith("#"):
                    continue

                # Truncate very long descriptions
                if len(description) > 200:
                    description = description[:200] + "..."

                issues.append(
                    ValidationIssue(
                        source=ValidationSource.REVIEW,
                        message=description,
                        severity=severity,
                    )
                )

        return issues


__all__ = ["ReviewValidator"]
