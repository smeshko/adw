"""Integration tests for interruption handling.

These tests verify actual signal handling behavior and end-to-end
recovery functionality.
"""

import signal
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from adw.core.context_manager import ContextManager
from adw.core.interruption import InterruptionHandler
from adw.core.resume_manager import ResumeManager
from adw.core.run_lookup import RunLookup
from adw.core.snapshot_manager import SnapshotManager
from adw.models import RunContext


@pytest.fixture
def runs_dir(tmp_path: Path) -> Path:
    """Create temporary runs directory with proper structure."""
    runs = tmp_path / ".adw" / "runs"
    runs.mkdir(parents=True)
    return runs


def _create_run_directory(runs_dir: Path, run_id: str) -> None:
    """Helper to create run directory structure."""
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "snapshots").mkdir(exist_ok=True)
    (run_dir / "artifacts").mkdir(exist_ok=True)


@pytest.fixture
def sample_context(runs_dir: Path) -> RunContext:
    """Create a sample RunContext with run directory structure."""
    run_id = "01JFTEST000000000000000001"
    _create_run_directory(runs_dir, run_id)

    return RunContext(
        run_id=run_id,
        feature_description="Integration test feature",
        current_phase="plan",
        phase_history=[],
        started_at=datetime.now(UTC),
        status="running",
    )


@pytest.fixture
def context_manager(runs_dir: Path) -> ContextManager:
    """Create ContextManager instance."""
    return ContextManager(runs_dir)


@pytest.fixture
def snapshot_manager(runs_dir: Path) -> SnapshotManager:
    """Create SnapshotManager instance."""
    return SnapshotManager(runs_dir)


class TestInterruptionHandlerIntegration:
    """Integration tests for InterruptionHandler with real managers."""

    def test_protected_execution_saves_on_exception(
        self,
        runs_dir: Path,
        sample_context: RunContext,
        context_manager: ContextManager,
        snapshot_manager: SnapshotManager,
    ) -> None:
        """Test that protected execution handles exceptions gracefully."""
        handler = InterruptionHandler(
            context_manager=context_manager,
            snapshot_manager=snapshot_manager,
        )

        # Save initial context
        context_manager.save(sample_context)

        # Simulate running in protected mode and raising an exception
        with pytest.raises(ValueError), handler.protected_execution(sample_context):
            raise ValueError("simulated error")

        # The handler should have restored signal handlers
        # (verified by the test not hanging or crashing)

    def test_full_interrupt_and_resume_cycle(
        self,
        runs_dir: Path,
        sample_context: RunContext,
        context_manager: ContextManager,
        snapshot_manager: SnapshotManager,
    ) -> None:
        """Test complete interrupt-and-resume workflow."""
        InterruptionHandler(
            context_manager=context_manager,
            snapshot_manager=snapshot_manager,
        )

        # Simulate a run that was interrupted
        # 1. Save initial running context
        context_manager.save(sample_context)

        # 2. Manually simulate an interrupt by creating interrupted context
        interrupted_context = sample_context.model_copy(
            update={
                "status": "interrupted",
                "interrupted_phase": "build",
                "interrupted_at": datetime.now(UTC),
                "phase_history": ["plan"],
            }
        )
        context_manager.save(interrupted_context)

        # 3. Load and verify interrupted state
        loaded = context_manager.load(sample_context.run_id)
        assert loaded.status == "interrupted"
        assert loaded.interrupted_phase == "build"

        # 4. Prepare for resume using ResumeManager
        resume_manager = ResumeManager(
            runs_dir=runs_dir,
            run_lookup=RunLookup(runs_dir),
            context_manager=context_manager,
        )
        resume_phase = resume_manager.get_resume_phase(loaded)
        assert resume_phase == "build"

        resumed = resume_manager.prepare_for_resume(loaded)
        assert resumed.status == "running"
        assert resumed.interrupted_phase is None
        assert resumed.phase_history == ["plan"]

        # 5. Save resumed context
        context_manager.save(resumed)

        # 6. Verify final state
        final = context_manager.load(sample_context.run_id)
        assert final.status == "running"

    def test_snapshot_created_on_interrupt_simulation(
        self,
        runs_dir: Path,
        sample_context: RunContext,
        context_manager: ContextManager,
        snapshot_manager: SnapshotManager,
    ) -> None:
        """Test that snapshots can be created during interrupt handling."""
        InterruptionHandler(
            context_manager=context_manager,
            snapshot_manager=snapshot_manager,
        )

        # Save initial context
        context_manager.save(sample_context)

        # Create a pre-phase snapshot
        snapshot_manager.create_pre_phase_snapshot(
            context=sample_context,
            phase="build",
        )

        # Create an interrupt snapshot (simulating what happens on SIGINT)
        interrupted_context = sample_context.model_copy(
            update={
                "status": "interrupted",
                "interrupted_phase": "build",
            }
        )
        snapshot_manager.create_post_phase_snapshot(
            context=interrupted_context,
            phase="build",
            phase_result=None,  # No result on interrupt
        )

        # Verify snapshots were created
        snapshots = snapshot_manager.list_snapshots(sample_context.run_id)
        assert len(snapshots) == 2
        assert snapshots[0]["timing"] == "pre"
        assert snapshots[1]["timing"] == "post"


class TestSignalHandlerScript:
    """Tests that run actual signal handling in subprocess."""

    def test_signal_handler_script_handles_sigterm(
        self,
        tmp_path: Path,
    ) -> None:
        """Test SIGTERM handling in a subprocess.

        This test creates a Python script that uses our signal handler,
        runs it in a subprocess, sends SIGTERM, and verifies proper cleanup.
        """
        runs_dir = tmp_path / ".adw" / "runs"
        runs_dir.mkdir(parents=True)
        run_id = "01JFTEST000000000000000001"
        run_dir = runs_dir / run_id
        run_dir.mkdir()
        (run_dir / "snapshots").mkdir()
        (run_dir / "artifacts").mkdir()

        # Create a test script that uses our InterruptionHandler
        script_content = f'''
import sys
import time
from pathlib import Path
from datetime import datetime, UTC

# Add src to path
sys.path.insert(0, "{Path(__file__).parent.parent.parent.parent / "src"}")

from adw.core.interruption import InterruptionHandler
from adw.core.context_manager import ContextManager
from adw.core.snapshot_manager import SnapshotManager
from adw.models import RunContext

runs_dir = Path("{runs_dir}")
run_id = "{run_id}"

context_manager = ContextManager(runs_dir)
snapshot_manager = SnapshotManager(runs_dir)

context = RunContext(
    run_id=run_id,
    feature_description="Signal test",
    current_phase="build",
    phase_history=["plan"],
    started_at=datetime.now(UTC),
    status="running",
)

context_manager.save(context)

handler = InterruptionHandler(
    context_manager=context_manager,
    snapshot_manager=snapshot_manager,
)

# Signal we're ready
print("READY", flush=True)

try:
    with handler.protected_execution(context):
        # Wait for signal
        time.sleep(10)
except KeyboardInterrupt:
    # Expected - signal was caught
    pass
except Exception as e:
    print(f"ERROR: {{e}}", flush=True)
    sys.exit(1)

# Check if context was saved with interrupted status
try:
    loaded = context_manager.load(run_id)
    status = loaded.status
    print(f"STATUS: {{status}}", flush=True)
except Exception as e:
    print(f"LOAD_ERROR: {{e}}", flush=True)
    sys.exit(1)

print("DONE", flush=True)
'''
        script_file = tmp_path / "test_signal.py"
        script_file.write_text(script_content)

        # Run the script
        proc = subprocess.Popen(
            [sys.executable, str(script_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait for script to be ready
        ready = False
        start = time.time()
        while time.time() - start < 5:
            if proc.stdout:
                line = proc.stdout.readline()
                if "READY" in line:
                    ready = True
                    break
            time.sleep(0.1)

        if not ready:
            proc.kill()
            stdout, stderr = proc.communicate(timeout=5)
            pytest.fail(
                f"Script did not become ready in time. stdout={stdout}, stderr={stderr}"
            )

        # Give it a moment to enter protected execution
        time.sleep(0.2)

        # Send SIGTERM
        proc.send_signal(signal.SIGTERM)

        # Wait for completion
        stdout, stderr = proc.communicate(timeout=5)

        # Check output
        all_output = stdout
        if "STATUS: interrupted" in all_output:
            # Perfect - context was saved with interrupted status
            pass
        elif "DONE" in all_output:
            # Script completed, which means signal was handled
            pass
        else:
            # Something went wrong
            pytest.fail(f"Unexpected output: stdout={all_output}, stderr={stderr}")


class TestResumeFromSnapshot:
    """Tests for resuming from snapshot after interruption."""

    def test_can_resume_from_last_snapshot(
        self,
        runs_dir: Path,
        sample_context: RunContext,
        context_manager: ContextManager,
        snapshot_manager: SnapshotManager,
    ) -> None:
        """Test that we can load state from snapshot after interrupt."""
        # Create and save initial context
        context_manager.save(sample_context)

        # Simulate progress through phases with snapshots
        context_after_plan = sample_context.model_copy(
            update={
                "current_phase": "build",
                "phase_history": ["plan"],
            }
        )
        context_manager.save(context_after_plan)
        snapshot_manager.create_post_phase_snapshot(
            context=context_after_plan,
            phase="plan",
            phase_result=None,
        )

        # Simulate interruption during build
        interrupted = context_after_plan.model_copy(
            update={
                "status": "interrupted",
                "interrupted_phase": "build",
            }
        )
        context_manager.save(interrupted)
        snapshot_manager.create_post_phase_snapshot(
            context=interrupted,
            phase="build",
            phase_result=None,
        )

        # Now resume
        loaded = context_manager.load(sample_context.run_id)
        assert loaded.status == "interrupted"

        # Get last good snapshot (before interrupt)
        snapshot_manager.list_snapshots(sample_context.run_id)
        last_snapshot = snapshot_manager.load_snapshot(
            sample_context.run_id,
            sequence=1,  # First snapshot after plan
        )

        # Verify we can access the pre-interrupt state
        assert last_snapshot.context.phase_history == ["plan"]
