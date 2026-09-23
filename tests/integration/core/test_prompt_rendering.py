"""Render the bundled phase prompts through PhaseRunner's real render path.

These are the B5 regression tests: ADW's variables inside the files a prompt
includes are filled, and every other placeholder reaches the LLM verbatim.
The helper calls ``_load_and_render_prompt`` directly, so no hook, git
command or LLM call runs.
"""

import re
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from adw.commands.resolver import CommandResolver
from adw.commands.template import VARIABLE_PATTERN, TemplateEngine
from adw.core.artifact_manager import ArtifactManager
from adw.core.phase_runner import PhaseRunner
from adw.executors.mock import MockExecutor
from adw.models import RunContext
from adw.models.config import ProjectConfig

RUN_ID = "01KF636397JZC18V4K8MGS59G7"
DIFF_MARKER = "+DIFF-MARKER-7f3a"

_TOKEN = re.compile(r"\{\{([^}]+)\}\}")
_DIRECTIVE = re.compile(r"\{\{(include|shared|file):([^}]+)\}\}")


def _render(
    project_root: Path,
    phase: str,
    *,
    project_config: ProjectConfig | None = None,
) -> tuple[str, set[str]]:
    """Render a bundled phase prompt; return it and the variable keys ADW passed."""
    resolver = CommandResolver(project_root=project_root)
    engine = TemplateEngine(project_root=project_root)
    runner = PhaseRunner(
        command_resolver=resolver,
        template_engine=engine,
        hook_runner=MagicMock(),
        executor=MockExecutor(),
        artifact_manager=ArtifactManager(runs_dir=project_root / ".adw" / "runs"),
        project_config=project_config,
    )
    command = resolver.resolve(phase)
    assert command.tier == "bundled"
    ctx = RunContext(
        run_id=RUN_ID,
        feature_description="Add OAuth login",
        current_phase=phase,
        started_at=datetime.now(UTC),
    )
    with patch.object(engine, "render", wraps=engine.render) as spy:
        prompt = runner._load_and_render_prompt(
            phase,
            ctx,
            "",
            command,
            merged_config=runner._get_merged_config(phase, command),
        )
    return prompt, set(spy.call_args.args[1])


def _source_texts(phase: str, project_root: Path) -> list[str]:
    """Return prompt.md and every file its include/shared directives name."""
    command = CommandResolver(project_root=project_root).resolve(phase)
    prompt = (command.path / "prompt.md").read_text(encoding="utf-8")
    texts = [prompt]
    for kind, rel in _DIRECTIVE.findall(prompt):
        root = command.path if kind == "include" else command.path.parent
        texts.append((root / rel.strip()).read_text(encoding="utf-8"))
    return texts


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A project dir with earlier-phase artifacts and a document config."""
    artifacts = tmp_path / ".adw" / "runs" / RUN_ID / "artifacts"
    build = artifacts / "build"
    build.mkdir(parents=True)
    (build / "diff.txt").write_text(f"--- a/app.py\n{DIFF_MARKER}\n")
    (build / "diff_stats.json").write_text('{"files_changed": 1}')
    (build / "build_output.md").write_text("Built the login flow.")
    (artifacts / "plan").mkdir()
    (artifacts / "plan" / "plan_output.md").write_text("The plan.")
    (artifacts / "validate").mkdir()
    (artifacts / "validate" / "validate_output.md").write_text("All green.")

    document = tmp_path / ".adw" / "commands" / "document"
    document.mkdir(parents=True)
    (document / "config.yaml").write_text(
        'doc_mappings:\n  - source_pattern: "src/**"\n    docs_dir: "docs/features"\n'
    )
    return tmp_path


def test_document_prompt_fills_included_build_diff(project: Path) -> None:
    prompt, _ = _render(project, "document")

    instructions = prompt.split("### Instructions", 1)[1]
    assert "DIFF-MARKER-7f3a" in instructions
    assert "docs/features" in instructions
    for literal in (
        "{{artifacts.build.diff}}",
        "{{artifacts.build.diff_stats}}",
        "{{doc_mappings}}",
    ):
        assert literal not in prompt


def test_validate_prompt_fills_included_commands(project: Path) -> None:
    validate = project / ".adw" / "commands" / "validate"
    validate.mkdir(parents=True)
    (validate / "config.yaml").write_text('lint_command: "ruff check ."\n')
    config = ProjectConfig(name="t", language="python", test_command="uv run pytest")

    prompt, _ = _render(project, "validate", project_config=config)

    assert "`uv run pytest`" in prompt
    assert "`ruff check .`" in prompt
    assert "{{test_command}}" not in prompt
    assert "{{lint_command}}" not in prompt


def test_validate_prompt_without_commands_keeps_auto_detect(project: Path) -> None:
    prompt, _ = _render(project, "validate")

    assert re.search(r"Execute:\s*</action>", prompt) is None
    assert re.search(r'if="\s*is null"', prompt) is None


@pytest.mark.parametrize("phase", ["plan", "build", "validate", "document", "ship"])
def test_llm_facing_placeholders_survive(project: Path, phase: str) -> None:
    config = ProjectConfig(
        name="t",
        language="python",
        test_command="uv run pytest",
        build_command="uv build",
    )
    prompt, adw_keys = _render(project, phase, project_config=config)

    tokens = {
        tok
        for text in _source_texts(phase, project)
        for tok in _TOKEN.findall(text)
        if not _DIRECTIVE.fullmatch("{{" + tok + "}}")
    }
    llm_facing = {
        tok
        for tok in tokens
        if not (
            VARIABLE_PATTERN.fullmatch("{{" + tok + "}}")
            and tok.split(".", 1)[0] in adw_keys
        )
    }

    assert llm_facing, "scanner found no LLM-facing placeholders"
    missing = sorted(tok for tok in llm_facing if "{{" + tok + "}}" not in prompt)
    assert not missing, f"LLM-facing placeholders lost: {missing}"
