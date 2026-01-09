"""Comment formatting for task management systems.

This module provides utilities for formatting status update comments
that are posted to task management systems (Linear, etc.).
"""


class CommentFormatter:
    """Formatter for task status update comments.

    Produces markdown-formatted comments for posting to task management
    systems at various stages of an ADW run.

    Example:
        >>> formatter = CommentFormatter()
        >>> comment = formatter.format_phase_complete("plan", 45.2, 3)
        >>> print(comment)
        **✓ Phase Complete: plan**

        | Metric | Value |
        |--------|-------|
        | Duration | 45.20s |
        | Artifacts | 3 |
    """

    def format_phase_complete(
        self,
        phase: str,
        duration: float,
        artifacts: int,
    ) -> str:
        """Format a phase completion comment.

        Args:
            phase: The phase name (e.g., "plan", "build").
            duration: The phase duration in seconds.
            artifacts: The number of artifacts produced.

        Returns:
            Markdown-formatted comment string.
        """
        return f"""**✓ Phase Complete: {phase}**

| Metric | Value |
|--------|-------|
| Duration | {duration:.2f}s |
| Artifacts | {artifacts} |
"""

    def format_phase_failed(
        self,
        phase: str,
        error: str,
        run_id: str,
    ) -> str:
        """Format a phase failure comment.

        Args:
            phase: The phase name that failed.
            error: The error message.
            run_id: The ADW run identifier.

        Returns:
            Markdown-formatted comment string.
        """
        return f"""**✗ Phase Failed: {phase}**

| Detail | Value |
|--------|-------|
| Run ID | `{run_id}` |
| Error | {error} |

See run logs for details.
"""

    def format_run_complete(
        self,
        run_id: str,
        pr_url: str | None,
        summary: str,
    ) -> str:
        """Format a run completion comment.

        Args:
            run_id: The ADW run identifier.
            pr_url: The pull request URL, if a PR was created.
            summary: A summary of the run.

        Returns:
            Markdown-formatted comment string.
        """
        pr_section = ""
        if pr_url:
            pr_section = f"\n**Pull Request:** {pr_url}\n"

        return f"""**✓ ADW Run Complete**

| Detail | Value |
|--------|-------|
| Run ID | `{run_id}` |
| Status | Completed |
{pr_section}
**Summary:** {summary}
"""
