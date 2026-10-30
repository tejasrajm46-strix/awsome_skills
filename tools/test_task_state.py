#!/usr/bin/env python3
"""Regression tests for the task state machine: transitions, protocol, freshness."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import skill_cache
import task_state


def test_transitions_and_terminal_states():
    with tempfile.TemporaryDirectory() as tmp:
        state = task_state.TaskState.create(tmp, "objective", "balanced", "t-1")
        for target in ("UNDERSTANDING", "SKILL_DISCOVERY", "SKILL_LOADING", "PLANNING",
                       "EXECUTION", "VALIDATION"):
            state.transition(target, reason="test")
        assert state.state == "VALIDATION"
        # VALIDATION -> REPAIR -> VALIDATION is the only repair path.
        state.transition("REPAIR", reason="warning")
        state.transition("VALIDATION", reason="repaired")
        assert state.repair_count() == 1
        # An illegal jump is refused and changes nothing.
        try:
            state.transition("PLANNING")
        except task_state.IllegalTransition:
            pass
        else:
            raise AssertionError("VALIDATION -> PLANNING must be illegal")
        assert state.state == "VALIDATION"
        state.transition("DELIVERY", reason="done")
        again = task_state.TaskState.load(tmp)
        assert again.state == "DELIVERY"
        try:
            again.transition("FAILED")
        except task_state.IllegalTransition:
            pass
        else:
            raise AssertionError("DELIVERY is terminal")
        with tempfile.TemporaryDirectory() as tmp2:
            cancelled = task_state.TaskState.create(tmp2, "x", "fast")
            cancelled.transition("UNDERSTANDING")
            cancelled.transition("CANCELLED", reason="user")
            assert cancelled.state == "CANCELLED"


def test_completion_protocol():
    with tempfile.TemporaryDirectory() as tmp:
        state = task_state.TaskState.create(tmp, "objective", "balanced", "t-2")
        # Unknown statuses are refused: the protocol is closed.
        try:
            state.record_step("s1", "succeeded")
        except ValueError as exc:
            assert "unknown step status" in str(exc), exc
        else:
            raise AssertionError("'succeeded' is not a protocol status")
        state.record_step("cmd-1", "command_completed", script="ppt_skill/scripts/build_deck.py",
                          script_sha256="abc123", outputs=["outputs/deck.pptx"])
        state.record_step("man-1", "manual_pending")
        # A manual claim can only be recorded as manual_completed - distinct
        # from command_completed, and never from validated.
        state.record_step("man-1", "manual_completed", detail="evidence recorded")
        try:
            state.record_step("man-1", "validated")
        except ValueError:
            pass
        else:
            raise AssertionError("manual steps cannot self-assign validated")
        assert state.step("cmd-1")["attempts"] == 1
        assert state.step("man-1")["status"] == "manual_completed"
        assert state.step("cmd-1")["status"] in task_state.DONE_STATUSES
        assert "2 command_completed" not in state.report()  # distinct counts
        assert "1 manual_completed" in state.report()


def test_resume_freshness(tmp_root=None):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "tools").mkdir()
        script = root / "tools" / "slow.py"
        script.write_text("print('ok')\n", encoding="utf-8", newline="\n")
        guide = root / "ppt_skill"
        guide.mkdir()
        (guide / "SKILL.md").write_text("---\nname: x\nversion: v1\n---\n\nwork\n",
                                        encoding="utf-8", newline="\n")
        state = task_state.TaskState.create(str(root / "workspace"), "objective", "fast")
        plan = {"schema": "task-plan", "steps": [{"id": "b1"}]}
        (root / "workspace" / "plan.json").write_text("{}", encoding="utf-8", newline="\n")
        state.set_plan(plan)
        state.add_loaded([{"path": "ppt_skill/SKILL.md", "sha256": skill_cache.sha256_of(str(guide / "SKILL.md")),
                           "tokens_est": 5, "from_cache": False, "stage": "B", "skill": "ppt"}])
        state.record_step("b1", "command_completed", script="tools/slow.py",
                          script_sha256=skill_cache.sha256_of(str(script)),
                          skill="ppt")

        # Nothing changed: freshen is a no-op.
        assert state.freshen(str(root)) == []
        assert state.step("b1")["status"] == "command_completed"

        # The script changed on disk: the step is demoted to stale, so resumption
        # re-runs it instead of skipping it.
        script.write_text("print('changed')\n", encoding="utf-8", newline="\n")
        notes = state.freshen(str(root))
        assert notes and "b1" in notes[0], notes
        assert state.step("b1")["status"] == "stale"
        assert state.data["history"][-1]["demoted"] == "command_completed"
        assert "changed" in state.report()

        # Restore the script, change the guide: same protection for instructions.
        script.write_text("print('ok')\n", encoding="utf-8", newline="\n")
        state.record_step("b1", "command_completed", script="tools/slow.py",
                          script_sha256=skill_cache.sha256_of(str(script)), skill="ppt")
        (guide / "SKILL.md").write_text("---\nname: x\nversion: v2\n---\n\nnew rules\n",
                                        encoding="utf-8", newline="\n")
        notes = state.freshen(str(root))
        assert notes and "guide" in notes[0], notes
        assert state.step("b1")["status"] == "stale"

        # A plan that changed after execution began is a hard refusal.
        state.record_step("b1", "command_completed", script="tools/slow.py",
                          script_sha256=skill_cache.sha256_of(str(script)), skill="ppt")
        (root / "workspace" / "plan.json").write_text('{"tampered": true}', encoding="utf-8",
                                                      newline="\n")
        try:
            state.freshen(str(root))
        except task_state.StaleTask as exc:
            assert "re-plan" in str(exc), exc
        else:
            raise AssertionError("changed plan must refuse to resume")


def main():
    test_transitions_and_terminal_states()
    test_completion_protocol()
    test_resume_freshness()
    print("PASS: guarded transitions, the four-status completion protocol, and "
          "resume freshness that demotes steps whose script or guide changed")


if __name__ == "__main__":
    main()
