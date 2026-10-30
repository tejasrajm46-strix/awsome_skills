#!/usr/bin/env python3
"""Regression tests for the task planner: interpretation contract and plan DAG."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import skill_registry
import task_planner


INTERP = {"objective": "Research storage costs; build an editable deck and a PDF report",
          "deliverables": [{"format": "pptx", "path": "outputs/deck.pptx"},
                           {"format": "pdf", "path": "outputs/report.pdf"}],
          "research": {"needed": True}, "mode": "balanced"}


def test_interpretation_validation():
    index = skill_registry.build_index()
    errors, selected = task_planner.validate_interpretation(INTERP, index)
    assert not errors, errors
    assert selected[0] == "scrape", "research tasks include the shared helper"
    assert {"ppt", "pdf"} <= set(selected), selected

    missing_format = {"objective": "x", "deliverables": [{"format": "m4a", "path": "a"}]}
    errors, _ = task_planner.validate_interpretation(missing_format, index)
    assert any("no registered skill" in e for e in errors), errors

    no_path = {"objective": "x", "deliverables": [{"format": "pptx"}]}
    errors, _ = task_planner.validate_interpretation(no_path, index)
    assert any("path is required" in e for e in errors), errors

    absolute = {"objective": "x", "deliverables": [{"format": "pptx", "path": "C:/x.pptx"}]}
    errors, _ = task_planner.validate_interpretation(absolute, index)
    assert any("relative" in e for e in errors), errors

    no_objective = {"deliverables": [{"format": "pptx", "path": "a.pptx"}]}
    errors, _ = task_planner.validate_interpretation(no_objective, index)
    assert any("objective" in e for e in errors), errors

    bad_mode = dict(INTERP, mode="turbo")
    errors, _ = task_planner.validate_interpretation(bad_mode, index)
    assert any("mode" in e for e in errors), errors


def order_ok(steps):
    position = {step["id"]: i for i, step in enumerate(steps)}
    for step in steps:
        for dep in step["depends_on"]:
            if position[dep] > position[step["id"]]:
                return False
    return True


def test_plan_structure_and_modes():
    index = skill_registry.build_index()
    plan = task_planner.build_plan(INTERP, index)
    assert order_ok(plan["steps"]), "plan respects its own dependency order"
    by_id = {s["id"]: s for s in plan["steps"]}
    assert by_id["b1-build"]["depends_on"] == ["s3-handoff"]
    assert by_id["b1-validate"]["depends_on"] == ["b1-build"]
    assert by_id["b1-validate"]["kind"] == "validation", "validator steps are identifiable"
    assert by_id["s-deliver"]["depends_on"] == ["b1-validate", "b2-validate"]
    # Independent builds are separately grouped so an executor may overlap them.
    assert by_id["b1-build"]["parallel_group"] != by_id["b2-build"]["parallel_group"]
    # Research precedes both builds; both builds consume the same handoff.
    assert by_id["b2-build"]["depends_on"] == ["s3-handoff"]
    # Every mode plans validation for every deliverable: safety is not optional.
    # A skill with a validator script gets a command step; one without (pdf)
    # gets an explicit manual step - never a silent omission.
    for mode in ("fast", "balanced", "deep"):
        variant = task_planner.build_plan(INTERP, index, mode)
        validators = [s for s in variant["steps"] if s.get("kind") == "validation"]
        # Two deliverable validators plus the research handoff validator.
        assert len(validators) == 3, (mode, validators)
        by_mode = {s["id"]: s for s in variant["steps"]}
        assert by_mode["b1-validate"]["command"], "ppt has a real validator"
        assert by_mode["b2-validate"]["manual"], "pdf validation is explicit manual work"
        assert by_mode["s3-handoff"]["command"], "the handoff bundle validator is real"
    # Deep adds cross-format consistency; fast omits render review.
    deep = task_planner.build_plan(INTERP, index, "deep")
    assert any(s["id"] == "s-consistency" for s in deep["steps"])
    fast = task_planner.build_plan(INTERP, index, "fast")
    assert not any("render-review" in s["id"] for s in fast["steps"])
    assert deep["repair_limit"] > fast["repair_limit"]
    # A local-only task (no research) builds straight from inspection.
    local = dict(INTERP, research={"needed": False}, mode="fast")
    local_plan = task_planner.build_plan(local, index, "fast")
    assert not any("research" in s["id"] or "handoff" in s["id"]
                   for s in local_plan["steps"])
    # The allowlist: a hand-built step running something outside the roots fails.
    tampered = dict(local_plan)
    tampered["steps"] = local_plan["steps"] + [
        {"id": "evil", "name": "x", "kind": "work",
         "command": ["python", "not_a_skill/evil.py"],
         "depends_on": [], "manual": False, "optional": False, "parallel_group": None}]
    try:
        task_planner._check_plan(tampered["steps"], "fast")
    except ValueError as exc:
        assert "allowlisted" in str(exc), exc
    else:
        raise AssertionError("a command outside the skill roots must be refused")


def main():
    test_interpretation_validation()
    test_plan_structure_and_modes()
    print("PASS: interpretation contract and dependency-ordered plans with mode "
          "depth, identifiable validation steps and a script allowlist")


if __name__ == "__main__":
    main()
