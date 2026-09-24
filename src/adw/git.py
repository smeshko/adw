"""Every git and gh subprocess in ADW goes through this module.

git() and gh() behave like subprocess.run(capture_output=True, text=True), plus
a timeout on every call. A command that overruns its timeout is stopped with
SIGTERM, so git can remove its lockfiles, then SIGKILL after a grace period,
and the caller gets a recoverable ADWError instead of a hang.

git stays in the terminal's process group: a Ctrl+C reaches it directly, and
credential or SSH prompts can still use the terminal.
"""

import subprocess
from pathlib import Path

from adw.exceptions import ADWError

# Timeout tiers, in seconds
DEFAULT_TIMEOUT = 60.0  # local plumbing
NETWORK_TIMEOUT = 300.0  # fetch, gh pr view
CHECKOUT_TIMEOUT = 300.0  # worktree remove, add -A
# Commands that run git hooks: commit, checkout, pull, push, worktree add
HOOK_TIMEOUT = 600.0

# Seconds between SIGTERM and SIGKILL
KILL_GRACE = 5.0

_SUGGESTIONS = {
    "git": (
        "A slow remote, a waiting credential or SSH prompt, or a slow hook can "
        "hold git up: check `git remote -v`, your credentials or ssh-agent and "
        "the network, remove a stale .git/index.lock if one is left, then retry"
    ),
    "gh": "Check network access and `gh auth status`, then retry",
}


def git(
    *args: str,
    cwd: Path | None = None,
    check: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
) -> subprocess.CompletedProcess[str]:
    """Run git with a timeout.

    Raises:
        ADWError: GIT_TIMEOUT (recoverable) when git overruns ``timeout``.
        subprocess.CalledProcessError: On a non-zero exit when ``check`` is set.
        FileNotFoundError: When git is not installed.
    """
    return _run("git", args, cwd=cwd, check=check, timeout=timeout)


def gh(
    *args: str,
    cwd: Path | None = None,
    check: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
) -> subprocess.CompletedProcess[str]:
    """Run the GitHub CLI with a timeout.

    Raises:
        ADWError: GH_TIMEOUT (recoverable) when gh overruns ``timeout``.
        subprocess.CalledProcessError: On a non-zero exit when ``check`` is set.
        FileNotFoundError: When gh is not installed.
    """
    return _run("gh", args, cwd=cwd, check=check, timeout=timeout)


def _run(
    tool: str,
    args: tuple[str, ...],
    *,
    cwd: Path | None,
    check: bool,
    timeout: float,
) -> subprocess.CompletedProcess[str]:
    cmd = [tool, *args]
    with subprocess.Popen(
        cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    ) as proc:
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            _stop(proc)
            raise ADWError(
                f"{tool.upper()}_TIMEOUT",
                f"`{_label(tool, args)}` timed out after {timeout:g}s",
                suggestion=_SUGGESTIONS[tool],
                recoverable=True,
            ) from exc
        except BaseException:
            # KeyboardInterrupt or SystemExit from ADW's signal handlers
            _stop(proc)
            raise

    if check and proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd, stdout, stderr)
    return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)


def _stop(proc: subprocess.Popen[str]) -> None:
    """Stop the process with SIGTERM, then SIGKILL after the grace period.

    Never reads the pipes afterwards: a descendant that inherited them could
    keep them open forever.
    """
    proc.terminate()
    try:
        proc.wait(timeout=KILL_GRACE)
    except subprocess.TimeoutExpired:
        pass
    finally:
        # Also reached when a second interrupt lands during the grace wait
        if proc.poll() is None:
            proc.kill()
            proc.wait()


def _label(tool: str, args: tuple[str, ...]) -> str:
    """Return the tool plus up to two leading arguments before the first flag."""
    leading: list[str] = []
    for arg in args[:2]:
        if arg.startswith("-"):
            break
        leading.append(arg)
    return " ".join([tool, *leading])
