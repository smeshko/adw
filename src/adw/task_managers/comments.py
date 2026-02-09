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
        ...
    """

    @staticmethod
    def _format_duration(total_seconds: float) -> str:
        """Format seconds into a human-friendly duration string.

        Args:
            total_seconds: Duration in seconds.

        Returns:
            Formatted string like ``"28s"`` or ``"2m 18s"``.
        """
        total_seconds = max(0.0, total_seconds)
        minutes = int(total_seconds) // 60
        seconds = int(total_seconds) % 60
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"

    @staticmethod
    def _format_phase_timeline(
        phase_sequence: list[str],
        completed_phases: list[str],
        failed_phase: str | None = None,
    ) -> str:
        """Generate a visual phase timeline.

        Args:
            phase_sequence: Ordered list of all phases in the pipeline.
            completed_phases: Phases that completed successfully.
            failed_phase: The phase that failed, if any.

        Returns:
            String like ``"plan ✓ → build ✗ → validate ⊘ → document ⊘ → ship ⊘"``.
        """
        parts: list[str] = []
        failed_seen = False
        for phase in phase_sequence:
            if phase in completed_phases:
                parts.append(f"{phase} ✓")
            elif failed_phase and phase == failed_phase:
                parts.append(f"{phase} ✗")
                failed_seen = True
            elif failed_phase and not failed_seen:
                # Phase before the failed phase that wasn't completed
                parts.append(f"{phase} ⊘")
            else:
                parts.append(f"{phase} ⊘")
        return " → ".join(parts)

    def format_run_started(
        self,
        run_id: str,
        *,
        branch_name: str | None = None,
        phase_sequence: list[str] | None = None,
        assignee: str | None = None,
    ) -> str:
        """Format a run started comment.

        Args:
            run_id: The ADW run identifier.
            branch_name: Git branch for this run.
            phase_sequence: Ordered phases in the pipeline.
            assignee: Who triggered the run.

        Returns:
            Markdown-formatted comment string.
        """
        pipeline = ""
        if phase_sequence:
            pipeline = " → ".join(phase_sequence)

        rows = [f"| Run ID | `{run_id}` |"]
        if branch_name:
            rows.append(f"| Branch | `{branch_name}` |")
        if pipeline:
            rows.append(f"| Pipeline | {pipeline} |")
        if assignee:
            rows.append(f"| Triggered by | {assignee} |")

        table_rows = "\n".join(rows)

        return f"""**▶ ADW Run Started**

| Detail | Value |
|--------|-------|
{table_rows}
"""

    def format_phase_complete(
        self,
        phase: str,
        duration: float,
        artifacts: int,
        *,
        artifact_names: list[str] | None = None,
        tokens_used: int = 0,
        tool_calls_count: int = 0,
    ) -> str:
        """Format a phase completion comment.

        Args:
            phase: The phase name (e.g., "plan", "build").
            duration: The phase duration in seconds.
            artifacts: The number of artifacts produced.
            artifact_names: Names of produced artifacts.
            tokens_used: Tokens consumed during this phase.
            tool_calls_count: Number of tool calls made.

        Returns:
            Markdown-formatted comment string.
        """
        human_duration = self._format_duration(duration)

        rows = [
            f"| Duration | {human_duration} |",
            f"| Artifacts | {artifacts} |",
        ]

        if tokens_used > 0:
            rows.append(f"| Tokens | {tokens_used:,} |")
        if tool_calls_count > 0:
            rows.append(f"| Tool calls | {tool_calls_count:,} |")

        table_rows = "\n".join(rows)

        artifact_section = ""
        if artifact_names:
            items = "\n".join(f"- `{name}`" for name in artifact_names)
            artifact_section = f"\n**Artifacts:**\n{items}\n"

        return f"""**✓ Phase Complete: {phase}** ({human_duration})

| Metric | Value |
|--------|-------|
{table_rows}
{artifact_section}"""

    def format_phase_failed(
        self,
        phase: str,
        error: str,
        run_id: str,
        *,
        duration: float | None = None,
        phase_sequence: list[str] | None = None,
        completed_phases: list[str] | None = None,
        branch_name: str | None = None,
        artifacts_by_phase: dict[str, list[str]] | None = None,
    ) -> str:
        """Format a phase failure comment.

        Args:
            phase: The phase name that failed.
            error: The error message.
            run_id: The ADW run identifier.
            duration: Total run duration in seconds up to failure.
            phase_sequence: Ordered phases in the pipeline.
            completed_phases: Phases completed before failure.
            branch_name: Git branch name for the run.
            artifacts_by_phase: Mapping of phase names to artifact paths.

        Returns:
            Markdown-formatted comment string.
        """
        rows = [f"| Run ID | `{run_id}` |"]

        if duration is not None:
            rows.append(f"| Duration | {self._format_duration(duration)} |")

        if branch_name:
            rows.append(f"| Branch | `{branch_name}` |")

        rows.append(f"| Error | {error} |")

        table_rows = "\n".join(rows)

        timeline_section = ""
        if phase_sequence:
            timeline = self._format_phase_timeline(
                phase_sequence, completed_phases or [], failed_phase=phase
            )
            timeline_section = f"\n**Pipeline:** {timeline}\n"

        artifacts_section = ""
        if artifacts_by_phase:
            items: list[str] = []
            for p, names in artifacts_by_phase.items():
                if names:
                    items.append(f"- **{p}**: {', '.join(f'`{n}`' for n in names)}")
            if items:
                artifacts_section = (
                    "\n**Completed before failure:**\n" + "\n".join(items) + "\n"
                )

        branch_note = ""
        if branch_name:
            branch_note = (
                f"\nBranch `{branch_name}` has been preserved for debugging.\n"
            )

        return f"""**✗ Phase Failed: {phase}**

| Detail | Value |
|--------|-------|
{table_rows}
{timeline_section}{artifacts_section}{branch_note}
See run logs for details.
"""

    def format_run_complete(
        self,
        run_id: str,
        pr_url: str | None,
        summary: str,
        *,
        duration: float | None = None,
        phase_sequence: list[str] | None = None,
        completed_phases: list[str] | None = None,
        total_tokens: int = 0,
        commit_count: int = 0,
        artifacts_by_phase: dict[str, list[str]] | None = None,
    ) -> str:
        """Format a run completion comment.

        Args:
            run_id: The ADW run identifier.
            pr_url: The pull request URL, if a PR was created.
            summary: A summary of the run.
            duration: Total run duration in seconds.
            phase_sequence: Ordered phases in the pipeline.
            completed_phases: Phases completed successfully.
            total_tokens: Total tokens consumed across the run.
            commit_count: Number of commits created.
            artifacts_by_phase: Mapping of phase names to artifact paths.

        Returns:
            Markdown-formatted comment string.
        """
        rows = [
            f"| Run ID | `{run_id}` |",
            "| Status | Completed |",
        ]

        if duration is not None:
            rows.append(f"| Duration | {self._format_duration(duration)} |")
        if total_tokens > 0:
            rows.append(f"| Tokens | {total_tokens:,} |")
        if commit_count > 0:
            rows.append(f"| Commits | {commit_count} |")

        table_rows = "\n".join(rows)

        pr_section = ""
        if pr_url:
            pr_section = f"\n**Pull Request:** {pr_url}\n"

        timeline_section = ""
        if phase_sequence:
            timeline = self._format_phase_timeline(
                phase_sequence, completed_phases or []
            )
            timeline_section = f"\n**Pipeline:** {timeline}\n"

        artifacts_section = ""
        if artifacts_by_phase:
            items: list[str] = []
            for phase, names in artifacts_by_phase.items():
                if names:
                    items.append(f"- **{phase}**: {', '.join(f'`{n}`' for n in names)}")
            if items:
                artifacts_section = "\n**Artifacts:**\n" + "\n".join(items) + "\n"

        return f"""**✓ ADW Run Complete**

| Detail | Value |
|--------|-------|
{table_rows}
{pr_section}{timeline_section}{artifacts_section}
**Summary:** {summary}
"""
