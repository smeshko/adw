"""Fix Engine for automated issue resolution.

This module provides the FixEngine class which coordinates:
- LLM-based fix generation for validation issues
- Atomic file modification with backup/rollback
- Selective re-validation after fixes
- Fix attempt tracking and auto-defer logic

Story: 11.4 - Fix Iteration Loop
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from adw.validation.config import ValidationConfig
from adw.validation.models import (
    FixAttempt,
    FixResult,
    IssueSource,
    ValidationIssue,
)

if TYPE_CHECKING:
    from adw.executors.base import LLMExecutor
    from adw.models import RunContext
    from adw.validation.validators.base import Validator

logger = logging.getLogger(__name__)


@runtime_checkable
class ValidatorProtocol(Protocol):
    """Protocol for validators that can be re-run after fixes."""

    @property
    def name(self) -> str:
        """Return the validator's unique name."""
        ...

    def validate(self, context: RunContext) -> list[ValidationIssue]:
        """Execute validation and return issues found."""
        ...


class FixIterationResult(BaseModel):
    """Result of a single fix iteration.

    Tracks which issues were fixed, which remain, which were deferred,
    and what files were modified during the fix attempt.

    Attributes:
        issues_fixed: List of issue IDs that were successfully resolved.
        issues_remaining: List of issue IDs still needing fixes.
        issues_deferred: List of issue IDs auto-deferred after max attempts.
        files_modified: List of file paths modified during fixes.
        validation_rerun: Whether validators were re-run after fixes.
        iteration_number: Which iteration this result represents.
    """

    issues_fixed: list[str] = Field(default_factory=list)
    issues_remaining: list[str] = Field(default_factory=list)
    issues_deferred: list[str] = Field(default_factory=list)
    files_modified: list[str] = Field(default_factory=list)
    validation_rerun: bool = False
    iteration_number: int = 0

    model_config = {
        "frozen": False,
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "issues_fixed": ["VI-01HQ123"],
                "issues_remaining": ["VI-01HQ456"],
                "issues_deferred": [],
                "files_modified": ["src/auth.py"],
                "validation_rerun": True,
                "iteration_number": 1,
            }
        },
    }


@dataclass
class FileChange:
    """Represents a file modification to apply.

    Attributes:
        file_path: Path to the file to modify.
        original_content: Original file content (for rollback).
        new_content: New content to write.
        line_start: Optional starting line for partial change.
        line_end: Optional ending line for partial change.
    """

    file_path: Path
    original_content: str
    new_content: str
    line_start: int | None = None
    line_end: int | None = None


# Mapping from IssueSource to validator name
_SOURCE_TO_VALIDATOR: dict[IssueSource, str] = {
    IssueSource.TEST: "test",
    IssueSource.REVIEW: "review",
    IssueSource.EVIDENCE: "evidence",
}


class FixEngine:
    """Engine for automatically fixing validation issues.

    The FixEngine coordinates the fix-validation loop:
    1. Filter issues to those triaged as FIX
    2. Build fix prompt with issue details
    3. Call LLM to generate fixes
    4. Apply fixes atomically with backup
    5. Re-run affected validators
    6. Track fix attempts and auto-defer

    Attributes:
        llm: LLM executor for generating fixes.
        config: Validation configuration.
        validators: Mapping of validator names to instances.

    Example:
        >>> engine = FixEngine(llm, config, validators)
        >>> result = engine.attempt_fixes(issues, context)
        >>> print(f"Fixed: {len(result.issues_fixed)}")
    """

    def __init__(
        self,
        llm_executor: LLMExecutor,
        config: ValidationConfig,
        validators: list[ValidatorProtocol],
    ) -> None:
        """Initialize the fix engine.

        Args:
            llm_executor: LLM executor for fix generation.
            config: Validation configuration with settings.
            validators: List of validators that can be re-run.
        """
        self.llm = llm_executor
        self.config = config
        self.validators: dict[str, ValidatorProtocol] = {v.name: v for v in validators}
        self._file_backups: dict[Path, str] = {}
        self._files_created: set[Path] = set()  # Track newly created files for rollback
        self._iteration = 0

    def attempt_fixes(
        self,
        issues: list[ValidationIssue],
        context: RunContext,
    ) -> FixIterationResult:
        """Attempt to fix all FIX-triaged issues.

        Filters issues to only those with triage_decision="FIX",
        generates fixes via LLM, applies them, and re-validates.

        Args:
            issues: List of validation issues to process.
            context: Current run context.

        Returns:
            FixIterationResult with fix outcomes and modified files.
        """
        self._iteration += 1

        # Filter to FIX issues only
        fix_issues = [i for i in issues if i.triage_decision == "FIX"]

        if not fix_issues:
            logger.debug("No FIX-triaged issues to process")
            return FixIterationResult(
                issues_fixed=[],
                issues_remaining=[i.id for i in issues if i.triage_decision != "DEFER"],
                issues_deferred=[i.id for i in issues if i.triage_decision == "DEFER"],
                files_modified=[],
                validation_rerun=False,
                iteration_number=self._iteration,
            )

        logger.info(
            "Attempting fixes",
            extra={
                "fix_count": len(fix_issues),
                "iteration": self._iteration,
            },
        )

        # Build and execute fix prompt
        prompt = self._build_fix_prompt(fix_issues, context)
        response = self.llm.execute(prompt)

        # Parse and apply fixes
        changes = self._parse_fix_response(response.content)

        if changes:
            try:
                self._backup_files(changes)
                self._apply_changes(changes)
            except Exception as e:
                logger.error(f"Failed to apply fixes: {e}")
                self._rollback()
                # All issues remain unfixed
                return FixIterationResult(
                    issues_fixed=[],
                    issues_remaining=[i.id for i in fix_issues],
                    issues_deferred=[],
                    files_modified=[],
                    validation_rerun=False,
                    iteration_number=self._iteration,
                )

        # Re-validate affected validators
        affected_validators = self._get_affected_validators(fix_issues)
        new_issues = self._revalidate(affected_validators, context)

        # Check which issues are resolved
        resolved, remaining = self._check_resolution(fix_issues, new_issues)

        # Update fix tracking on remaining issues
        deferred_ids: list[str] = []
        for issue in remaining:
            issue.fix_attempt_count += 1
            issue.fix_attempted = True
            issue.last_fix_result = FixResult.FAILED
            issue.fix_history.append(
                FixAttempt(
                    result=FixResult.FAILED,
                    notes=f"Attempt {issue.fix_attempt_count} failed",
                    changes_made=[str(c.file_path) for c in changes],
                )
            )

            # Auto-defer if max attempts reached
            if issue.fix_attempt_count >= self.config.max_fix_attempts_per_issue:
                issue.triage_decision = "DEFER"
                issue.triage_reason = (
                    f"Max fix attempts reached ({issue.fix_attempt_count})"
                )
                deferred_ids.append(issue.id)
                logger.info(
                    "Auto-deferring issue after max attempts",
                    extra={"issue_id": issue.id, "attempts": issue.fix_attempt_count},
                )

        # Update resolved issues
        for issue in resolved:
            issue.last_fix_result = FixResult.RESOLVED
            issue.fix_history.append(
                FixAttempt(
                    result=FixResult.RESOLVED,
                    notes="Fix verified by re-validation",
                    changes_made=[str(c.file_path) for c in changes],
                )
            )

        return FixIterationResult(
            issues_fixed=[i.id for i in resolved],
            issues_remaining=[
                i.id for i in remaining if i.triage_decision != "DEFER"
            ],
            issues_deferred=deferred_ids,
            files_modified=[str(c.file_path) for c in changes],
            validation_rerun=True,
            iteration_number=self._iteration,
        )

    def _build_fix_prompt(
        self,
        issues: list[ValidationIssue],
        context: RunContext,
    ) -> str:
        """Build LLM prompt for fixing issues.

        Creates a structured prompt with issue details and
        requests JSON-formatted fixes.

        Args:
            issues: List of issues to fix.
            context: Run context for additional info.

        Returns:
            Prompt string for the LLM.
        """
        issue_descriptions = []
        for issue in issues:
            desc = f"- ID: {issue.id}\n"
            desc += f"  Source: {issue.source.value}\n"
            desc += f"  Description: {issue.description}\n"
            if issue.location:
                desc += f"  File: {issue.location.file_path}\n"
                if issue.location.line_start:
                    desc += f"  Line: {issue.location.line_start}\n"
            if issue.context and issue.context.code_snippet:
                desc += f"  Code:\n{issue.context.code_snippet}\n"
            issue_descriptions.append(desc)

        return f"""You are fixing validation issues in code. For each issue below,
provide the fix as a file modification.

Issues to fix:
{"".join(issue_descriptions)}

Respond with JSON:
{{
  "fixes": [
    {{
      "issue_id": "VI-...",
      "file_path": "src/...",
      "line_start": 10,
      "line_end": 15,
      "replacement": "new code here"
    }}
  ]
}}

Only include fixes you are confident will resolve the issue.
If unsure, set replacement to null and explain in notes.
"""

    def _parse_fix_response(self, content: str) -> list[FileChange]:
        """Parse LLM fix response into FileChange objects.

        Extracts JSON from response and converts to FileChange list.

        Args:
            content: Raw LLM response content.

        Returns:
            List of FileChange objects to apply.
        """
        import json

        changes: list[FileChange] = []

        try:
            # Try to extract JSON from response
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(content[start:end])
                fixes = data.get("fixes", [])

                for fix in fixes:
                    if fix.get("replacement") is None:
                        continue  # Skip uncertain fixes

                    file_path = Path(fix["file_path"])
                    if file_path.exists():
                        original = file_path.read_text()
                    else:
                        original = ""

                    changes.append(
                        FileChange(
                            file_path=file_path,
                            original_content=original,
                            new_content=fix["replacement"],
                            line_start=fix.get("line_start"),
                            line_end=fix.get("line_end"),
                        )
                    )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse fix response: {e}")

        return changes

    def _backup_files(self, changes: list[FileChange]) -> None:
        """Backup files before modification.

        Stores original content in memory for rollback. Also tracks
        files that will be newly created so they can be deleted on rollback.

        Args:
            changes: List of changes to backup.
        """
        self._file_backups.clear()
        self._files_created.clear()
        for change in changes:
            if change.file_path.exists():
                self._file_backups[change.file_path] = change.file_path.read_text()
            else:
                # Track files that will be newly created
                self._files_created.add(change.file_path)

    def _apply_changes(self, changes: list[FileChange]) -> None:
        """Apply file changes atomically.

        Writes new content to files. If any write fails,
        should be followed by rollback.

        Groups changes by file to handle multiple changes to the same file
        correctly, ensuring cumulative edits are preserved.

        Args:
            changes: List of changes to apply.

        Raises:
            IOError: If file write fails.
        """
        # Group changes by file path to handle multiple changes to same file
        changes_by_file: dict[Path, list[FileChange]] = {}
        for change in changes:
            if change.file_path not in changes_by_file:
                changes_by_file[change.file_path] = []
            changes_by_file[change.file_path].append(change)

        for file_path, file_changes in changes_by_file.items():
            # Read current file content (may have been modified by earlier changes)
            if file_path.exists():
                current_content = file_path.read_text()
            else:
                current_content = ""

            # Sort changes by line_start in reverse order to apply from bottom to top
            # This prevents line number shifts from affecting later changes
            partial_changes = [
                c for c in file_changes
                if c.line_start is not None and c.line_end is not None
            ]
            full_replacement = [
                c for c in file_changes
                if c.line_start is None or c.line_end is None
            ]

            # If there's a full replacement, it takes precedence
            if full_replacement:
                # Use the last full replacement
                file_path.write_text(full_replacement[-1].new_content)
            elif partial_changes:
                # Sort by line_start descending to apply from bottom to top
                partial_changes.sort(key=lambda c: c.line_start or 0, reverse=True)
                lines = current_content.splitlines(keepends=True)

                for change in partial_changes:
                    # Apply each change to the current lines
                    new_lines = (
                        lines[: change.line_start - 1]
                        + [change.new_content + "\n"]
                        + lines[change.line_end :]
                    )
                    lines = new_lines

                file_path.write_text("".join(lines))

    def _rollback(self) -> None:
        """Restore files from backup.

        Reverts all changes made during the current fix attempt.
        Also deletes any newly created files to ensure atomic rollback.
        """
        # Restore existing files from backup
        for path, content in self._file_backups.items():
            try:
                path.write_text(content)
            except Exception as e:
                logger.error(f"Failed to rollback {path}: {e}")
        self._file_backups.clear()

        # Delete newly created files
        for path in self._files_created:
            try:
                if path.exists():
                    path.unlink()
            except Exception as e:
                logger.error(f"Failed to delete newly created file {path}: {e}")
        self._files_created.clear()

    def _get_affected_validators(
        self,
        issues: list[ValidationIssue],
    ) -> list[ValidatorProtocol]:
        """Get validators affected by the given issues.

        Maps issue sources to their corresponding validators.

        Args:
            issues: List of issues that were fixed.

        Returns:
            List of validators that should be re-run.
        """
        affected_names: set[str] = set()

        for issue in issues:
            validator_name = _SOURCE_TO_VALIDATOR.get(issue.source)
            if validator_name and validator_name in self.validators:
                affected_names.add(validator_name)

        return [self.validators[name] for name in affected_names]

    def _revalidate(
        self,
        validators: list[ValidatorProtocol],
        context: RunContext,
    ) -> list[ValidationIssue]:
        """Re-run validators after fixes are applied.

        Executes each affected validator and collects new issues.

        Args:
            validators: List of validators to run.
            context: Run context.

        Returns:
            List of issues found during re-validation.
        """
        all_issues: list[ValidationIssue] = []

        for validator in validators:
            try:
                logger.debug(f"Re-validating with {validator.name}")
                issues = validator.validate(context)
                all_issues.extend(issues)
            except Exception as e:
                logger.warning(f"Validator {validator.name} failed: {e}")

        return all_issues

    def _check_resolution(
        self,
        original_issues: list[ValidationIssue],
        new_issues: list[ValidationIssue],
    ) -> tuple[list[ValidationIssue], list[ValidationIssue]]:
        """Check which original issues are resolved.

        Compares original issues against new issues found
        to determine which are resolved.

        Args:
            original_issues: Issues we tried to fix.
            new_issues: Issues found during re-validation.

        Returns:
            Tuple of (resolved_issues, remaining_issues).
        """
        resolved: list[ValidationIssue] = []
        remaining: list[ValidationIssue] = []

        for original in original_issues:
            # Check if this issue still appears in new issues
            still_exists = any(
                original.is_same_issue(new) for new in new_issues
            )

            if still_exists:
                remaining.append(original)
            else:
                resolved.append(original)

        return resolved, remaining


__all__ = ["FileChange", "FixEngine", "FixIterationResult"]
