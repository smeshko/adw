"""PR description models for ADW document phase.

This module provides Pydantic models for structured PR descriptions
generated during the document phase (Story 9.4).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PRDescription(BaseModel):
    """Structured PR description generated during document phase.

    Represents a GitHub-flavored Markdown PR description with
    standardized sections for summary, changes, testing, and evidence.

    Attributes:
        summary: 1-2 sentence summary of what the PR accomplishes
        changes: List of key changes made in this PR
        testing: Description of how changes were verified
        evidence: Links to evidence items or note about lack of evidence

    Example:
        >>> pr = PRDescription(
        ...     summary="Add user authentication with JWT tokens",
        ...     changes=["Add login endpoint", "Add token refresh"],
        ...     testing="Unit tests added, integration tests pass",
        ...     evidence="See screenshots in evidence/screenshots/",
        ... )
        >>> print(pr.to_markdown())
        ## Summary
        Add user authentication with JWT tokens
        ...
    """

    summary: str = Field(
        ...,
        description="1-2 sentence summary of what the PR accomplishes",
        min_length=10,
        max_length=500,
    )

    changes: list[str] = Field(
        ...,
        description="List of key changes made in this PR",
        min_length=1,
    )

    testing: str = Field(
        ...,
        description="Description of how the changes were verified",
        min_length=5,
    )

    evidence: str = Field(
        default="No visual evidence captured",
        description="Links to evidence items or note about lack of evidence",
    )

    def to_markdown(self) -> str:
        """Convert PR description to GitHub-flavored Markdown.

        Returns:
            Formatted markdown string suitable for GitHub PR body.

        Example:
            >>> pr = PRDescription(
            ...     summary="Fix login bug",
            ...     changes=["Update auth logic"],
            ...     testing="All tests pass",
            ... )
            >>> md = pr.to_markdown()
            >>> "## Summary" in md
            True
        """
        changes_list = "\n".join(f"- {change}" for change in self.changes)

        return f"""## Summary

{self.summary}

## Changes

{changes_list}

## Testing

{self.testing}

## Evidence

{self.evidence}
"""

    @classmethod
    def from_markdown(cls, markdown: str) -> PRDescription:
        """Parse a markdown PR description into a PRDescription model.

        Extracts sections based on ## headers and parses the content.

        Args:
            markdown: Markdown-formatted PR description text.

        Returns:
            PRDescription model with extracted fields.

        Raises:
            ValueError: If required sections are missing or invalid.

        Example:
            >>> md = '''## Summary
            ... Fix the login bug
            ...
            ... ## Changes
            ... - Update auth logic
            ...
            ... ## Testing
            ... All tests pass
            ... '''
            >>> pr = PRDescription.from_markdown(md)
            >>> pr.summary
            'Fix the login bug'
        """
        sections: dict[str, str] = {}
        current_section: str | None = None
        current_content: list[str] = []

        for line in markdown.split("\n"):
            # Check for section header
            if line.startswith("## "):
                # Save previous section
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = line[3:].strip().lower()
                current_content = []
            elif current_section:
                current_content.append(line)

        # Save last section
        if current_section:
            sections[current_section] = "\n".join(current_content).strip()

        # Extract required fields
        summary = sections.get("summary", "").strip()
        if not summary:
            raise ValueError("Missing required section: Summary")

        changes_text = sections.get("changes", "").strip()
        if not changes_text:
            raise ValueError("Missing required section: Changes")

        # Parse changes as bullet list
        changes: list[str] = []
        for line in changes_text.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                changes.append(line[2:].strip())
            elif line.startswith("* "):
                changes.append(line[2:].strip())
            elif line and not line.startswith("#"):
                # Non-bullet line, treat as single change
                changes.append(line)

        if not changes:
            raise ValueError("Changes section must contain at least one item")

        testing = sections.get("testing", "").strip()
        if not testing:
            raise ValueError("Missing required section: Testing")

        evidence = sections.get("evidence", "No visual evidence captured").strip()

        return cls(
            summary=summary,
            changes=changes,
            testing=testing,
            evidence=evidence,
        )


__all__ = ["PRDescription"]
