#!/usr/bin/env python3
"""Regression tests for the controlled executor: gates, timeouts, real runs."""
from __future__ import annotations

import os
import stat
import sys
import tempfile
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import task_executor
import task_planner
import task_state


INTERP = {"objective": "Research storage costs; build an editable deck and a PDF report",
          "deliverables": [{"format": "pptx", "path": "outputs/deck.pptx"},
                           {"format": "pdf", "path": "outputs/report.pdf"}],
          "research": {"needed": True}, "mode": "balanced"}


def test_allowlist_gate():
    # Paths outside the repository, non-allowlisted binaries, shell chaining
    # and nonexistent scripts are all refused before anything executes.
    gate = task_executor.check_command({"id": "x", "command": ["python", "../../evil.py"]}, ".")
    assert gate and "escapes" in str(gate), gate
    gate = task_executor.check_command(
        {"id": "x", "command": ["python", "ultimate-scrape-skill/scripts/route.py",
                                "research; rm -rf /"]}, ".")
    assert gate and "metacharacters" in str(gate), gate
    gate = task_executor.check_command(
        {"id": "x", "command": ["bash", "ppt_skill/scripts/build_deck.py"]}, ".")
    assert gate and "not allowlisted" in str(gate), gate
    gate = task_executor.check_command(
        {"id": "x", "command": ["python", "ppt_skill/scripts/missing.py"]}, ".")
    assert gate and "does not exist" in str(gate), gate
    gate = task_executor.check_command(
        {"id": "x", "command": ["python", "tools/check_release.py", "&&", "echo pwned"]}, ".")
    assert gate and "metacharacters" in str(gate), gate
    ok = task_executor.check_command(
        {"id": "x", "command": ["python", "ultimate-scrape-skill/scripts/route.py", "--help"]}, ".")
    assert ok is None, ok
    # Manual steps bypass the command gate by construction.
    assert task_executor.check_command({"id": "x", "manual": True}, ".") is None


def test_symlink_containment():
    """A symlink inside a skill root that points outside must be refused."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        (root / "tools").mkdir(parents=True)
        outside = Path(tmp) / "outside.py"
        outside.write_text("print('smuggled')\n", encoding="utf-8", newline="\n")
        link = root / "tools" / "smuggled.py"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            print("     (symlinks unavailable on this host; containment untested here)")
            return
        gate = task_executor.check_command(
            {"id": "x", "command": ["python", "tools/smuggled.py"]}, str(root))
        assert gate and "symlink" in str(gate), gate
        # A file genuinely inside the tree still passes.
        (root / "tools" / "real.py").write_text("print('ok')\n", encoding="utf-8", newline="\n")
        ok = task_executor.check_command({"id": "x", "command": ["python", "tools/real.py"]},
                                         str(root))
        assert ok is None, ok


def test_subprocess_handling_and_timeout():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        (root / "tools").mkdir(parents=True)
        # A real allowlisted subprocess runs and its actual output is returned.
        (root / "tools" / "hello.py").write_text("print('hello from subprocess')\n",
                                                 encoding="utf-8", newline="\n")
        runner = task_executor.SubprocessRunner(timeout=30)
        result = runner.run({"id": "x", "command": ["python", "tools/hello.py"]}, str(root))
        assert result.ok and result.returncode == 0, result.summary()
        assert "hello from subprocess" in result.stdout

        # A failing command is a recorded failure, never a success.
        (root / "tools" / "boom.py").write_text("import sys; sys.exit(3)\n",
                                                encoding="utf-8", newline="\n")
        result = runner.run({"id": "x", "command": ["python", "tools/boom.py"]}, str(root))
        assert not result.ok and result.returncode == 3

        # Timeout: the child is killed and the step fails with a timeout reason.
        (root / "tools" / "slow.py").write_text("import time; time.sleep(30)\n",
                                                encoding="utf-8", newline="\n")
        result = task_executor.SubprocessRunner(timeout=1).run(
            {"id": "x", "command": ["python", "tools/slow.py"]}, str(root))
        assert not result.ok and "timed out" in (result.reason or ""), result.summary()
        assert result.seconds < 10, result.seconds


def test_execution_records_protocol_statuses():
    index = __import__("skill_registry").build_index()
    local = {"objective": "x", "mode": "fast",
             "deliverables": [{"format": "pptx", "path": "outputs/deck.pptx"}],
             "research": {"needed": False}}
    plan = task_planner.build_plan(local, index, "fast")
    with tempfile.TemporaryDirectory() as tmp:
        state = task_state.TaskState.create(tmp, "x", "fast")
        for target in ("UNDERSTANDING", "SKILL_DISCOVERY", "SKILL_LOADING", "PLANNING"):
            state.transition(target)
        state.transition("EXECUTION")
        runner = task_executor.MockRunner(fail_first={"b1-validate": 1})
        state.record_step("s1-inspect-inputs", "manual_completed", detail="no inputs")
        executed = task_executor.execute_ready(state, plan, runner, ".")
        assert executed >= 2, executed
        build = state.step("b1-build")
        assert build["status"] == "command_completed" and build["script_sha256"], build
        failed = [s for s in state.data["steps"] if s["status"] == "failed"]
        assert any("b1-validate" == s["id"] for s in failed), failed
        # Completed work is not repeated; failed deps block dependents.
        runner2 = task_executor.MockRunner()
        executed2 = task_executor.execute_ready(state, plan, runner2, ".")
        assert "b1-build" not in runner2.calls
        assert executed2 == 0, "outside a repair cycle, failed steps are not retried"
        # Entering a REPAIR cycle makes the retry deliberate and bounded by design.
        state.transition("VALIDATION", reason="steps complete")
        state.transition("REPAIR", reason="b1-validate failed once")
        executed3 = task_executor.execute_ready(state, plan, runner2, ".")
        assert "b1-validate" in runner2.calls and executed3 >= 1, (executed3, runner2.calls)
        assert state.step("b1-validate")["status"] == "command_completed"


def main():
    test_allowlist_gate()
    test_symlink_containment()
    test_subprocess_handling_and_timeout()
    test_execution_records_protocol_statuses()
    print("PASS: executor gates paths, symlinks, chaining and binaries; subprocess "
          "results and timeouts are honest; protocol statuses recorded with script hashes")


if __name__ == "__main__":
    main()
