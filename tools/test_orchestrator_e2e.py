#!/usr/bin/env python3
"""End-to-end orchestration test: one task, two skills, mock execution.

Runs the full lifecycle the way a host LLM would drive it - new-task,
interpret, load, plan, manual steps through the completion protocol, command
steps via the executor, validation with promotion to `validated`, bounded
repair recovery and delivery - then asserts the properties the system exists
for:

- irrelevant skills are never loaded and staged context is measured,
- manual completion without evidence is refused, and a manual completion is
  recorded as `manual_completed`, never as `validated`,
- `validated` is earned only by an independent validator that actually ran,
- a failed step is recorded, blocks its dependents, and is retried only
  inside a REPAIR cycle without repeating completed work,
- resume freshness runs against the real tree and finds nothing stale,
- the final report distinguishes what ran from what did not.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import orchestrator
import skill_cache
import skill_loader
import skill_registry
import task_executor
import task_planner
import task_state

INTERPRETATION = {
    "objective": "Research storage costs and deliver an editable deck plus a PDF report",
    "deliverables": [{"format": "pptx", "path": "outputs/deck.pptx"},
                     {"format": "pdf", "path": "outputs/report.pdf"}],
    "research": {"needed": True, "topics": ["grid storage cost per kWh"]},
    "constraints": {"audience": "executive", "editable": True},
    "mode": "balanced",
}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def advance(state, *targets):
    for target in targets:
        state.transition(target, reason="test drive")


def main():
    index = skill_registry.build_index()
    with tempfile.TemporaryDirectory() as tmp:
        workspace = os.path.join(tmp, "task")
        state = task_state.TaskState.create(workspace, INTERPRETATION["objective"],
                                            "balanced", "e2e-1")
        advance(state, "UNDERSTANDING")

        # -- interpret: validation + selection + stage-A metadata only ---------
        cache_dir = os.path.join(workspace, ".skill-cache")
        errors, selected = task_planner.validate_interpretation(INTERPRETATION, index)
        assert not errors, errors
        assert selected == ["scrape", "ppt", "pdf"], selected
        loader = skill_loader.SkillLoader(index, skill_cache.SkillCache(cache_dir))
        state.transition("SKILL_DISCOVERY", reason="interpretation validated")
        for key in selected:
            state.add_loaded([loader.metadata(key)["load_record"]])
        state.transition("SKILL_LOADING", reason="metadata loaded")
        state.set_interpretation(INTERPRETATION, selected)

        # Discovery loaded only descriptions: no full guide yet, no poster/xlsm.
        stage_a = loader.loaded_context(stage="A")
        full_guides = sum(s["token_estimate"] for s in index["skills"])
        assert stage_a["tokens_est"] * 10 < full_guides, (stage_a, full_guides)
        assert "poster" not in loader.loaded_skills() and "xlsm" not in loader.loaded_skills()

        # -- load: stage B for the two working skills, stage C for one reference
        deck_guide = loader.skill("ppt")
        pdf_guide = loader.skill("pdf")
        ref = loader.reference("ppt", "references/deck-schema.md")
        state.add_loaded([deck_guide["load_record"], pdf_guide["load_record"],
                          ref["load_record"]])
        assert deck_guide["load_record"]["from_cache"] is False

        # -- plan: DAG with research feeding both builds -----------------------
        plan = task_planner.build_plan(INTERPRETATION, index)
        by_id = {s["id"]: s for s in plan["steps"]}
        assert by_id["b1-build"]["depends_on"] == ["s3-handoff"]
        assert by_id["b2-build"]["depends_on"] == ["s3-handoff"]
        with open(os.path.join(workspace, "plan.json"), "w", encoding="utf-8",
                  newline="\n") as handle:
            json.dump(plan, handle, indent=2)
        state.set_plan(plan)
        for step in plan["steps"]:
            if step.get("manual"):
                state.record_step(step["id"], "manual_pending")
        advance(state, "PLANNING", "EXECUTION")

        # -- execute: manual research via the protocol, commands via the runner -
        state.record_step("s1-inspect-inputs", "manual_completed", detail="no inputs supplied")
        state.record_step("s2-research", "manual_completed",
                          outputs=["research/handoff.json"],
                          detail="register: 3 sources, 2 approved assets")
        runner = task_executor.MockRunner(fail_first={"b1-validate": 1})
        executed = task_executor.execute_ready(state, plan, runner, REPO_ROOT)
        assert executed >= 3, executed  # handoff validate, b1-build, b1-validate(fail)
        failed = {s["id"] for s in state.data["steps"] if s["status"] == "failed"}
        assert "b1-validate" in failed, state.data["steps"]
        assert "b1-build" in {s["id"] for s in state.data["steps"]
                              if s["status"] == "command_completed"}

        # -- validation, bounded repair, evidence protocol ---------------------
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            code = orchestrator.cmd_validate(argparse.Namespace(workspace=workspace))
        assert code == 2, "a failed step with repair budget left enters REPAIR"
        # CLI commands load their own ledger instance; reload to see their writes.
        state = task_state.TaskState.load(workspace)
        assert state.state == "REPAIR"
        # The retry runs inside the repair cycle; the next `validate` closes it.
        executed = task_executor.execute_ready(state, plan, runner, REPO_ROOT)
        assert executed >= 1 and "b1-validate" in runner.calls
        state = task_state.TaskState.load(workspace)
        assert state.step("b1-validate")["status"] == "command_completed"

        # The PDF deliverable has no builder script either: its build is manual
        # work, completed with evidence like any other manual obligation.
        build_evidence = Path(workspace) / "pdf-build-notes.md"
        build_evidence.write_text("pypdf merge executed on a copy; source untouched\n",
                                  encoding="utf-8", newline="\n")
        with contextlib.redirect_stdout(captured):
            code = orchestrator.cmd_done(argparse.Namespace(
                workspace=workspace, step="b2-build", output=["outputs/report.pdf"],
                evidence=str(build_evidence), note="report built with pypdf"))
        assert code == 0, captured.getvalue()
        state = task_state.TaskState.load(workspace)

        # The PDF deliverable's validation has no validator script: the host
        # completes it manually. Evidence makes it manual_completed - and the
        # promotion pass must NOT upgrade that to validated.
        pdf_evidence = Path(workspace) / "pdf-checks.md"
        pdf_evidence.write_text("pdftotext output checked; page count measured\n",
                                encoding="utf-8", newline="\n")
        with contextlib.redirect_stdout(captured):
            code = orchestrator.cmd_done(argparse.Namespace(
                workspace=workspace, step="b2-validate", output=[],
                evidence=str(pdf_evidence), note="manual PDF verification"))
        assert code == 0, captured.getvalue()
        state = task_state.TaskState.load(workspace)
        assert state.step("b2-validate")["status"] == "manual_completed"

        # Manual completion without evidence is refused by the protocol.
        with contextlib.redirect_stdout(captured):
            code = orchestrator.cmd_done(argparse.Namespace(
                workspace=workspace, step="b2-render-review", output=[],
                evidence=None, note="reviewed in my head"))
        assert code == 1 and "--evidence" in captured.getvalue(), captured.getvalue()
        state = task_state.TaskState.load(workspace)
        assert state.step("b2-render-review")["status"] == "manual_pending"

        # Evidenced manual completion lands as manual_completed - work done,
        # verification not implied.
        evidence = Path(workspace) / "review-notes.md"
        evidence.write_text("11 slides reviewed; contrast fixed on slide 3\n",
                            encoding="utf-8", newline="\n")
        with contextlib.redirect_stdout(captured):
            code = orchestrator.cmd_done(argparse.Namespace(
                workspace=workspace, step="b1-render-review", output=[],
                evidence=str(evidence), note="slides reviewed"))
        assert code == 0 and "manual_completed" in captured.getvalue(), captured.getvalue()
        state = task_state.TaskState.load(workspace)
        assert state.step("b1-render-review")["status"] == "manual_completed"

        state.record_step("b2-render-review", "not_run",
                          detail="host has no renderer; disclosed in limitations")
        state.add_limitation("rendering unavailable for the PDF: pagination unverified")
        # The remaining manual obligations: manifest written, delivery reported.
        state.record_step("s-manifest", "manual_completed",
                          outputs=["manifest.json"],
                          detail="output manifest validated: deck validated, docx generated")
        state.record_step("s-deliver", "manual_completed",
                          detail="delivered with limitations disclosed")

        # Resume freshness runs against the real tree before the delivery gate.
        assert state.freshen(REPO_ROOT) == [], "real tree must be unchanged here"
        advance(state, "VALIDATION")
        state = task_state.TaskState.load(workspace)
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            code = orchestrator.cmd_validate(argparse.Namespace(workspace=workspace))
        assert code == 0, captured.getvalue()
        state = task_state.TaskState.load(workspace)
        assert state.state == "DELIVERY"
        # The deck's validator ran as a command: it is `validated`. The DOCX's
        # validation was manual: recorded, and reported as NOT independently
        # validated.
        summary = state.data["validation"]
        states = {entry["step"]: entry["state"] for entry in summary["deliverable_checks"]}
        assert states["b1-validate"] == "validated", states
        assert states["b2-validate"] == "manual_completed", states
        assert summary["fully_validated"] is False
        assert state.step("b1-validate")["status"] == "validated"
        assert state.step("b2-validate")["status"] == "manual_completed"
        assert "NOT fully validated" in captured.getvalue(), captured.getvalue()

        # -- the ledger shows exactly what the LLM consumed --------------------
        loaded = state.data["loaded_context"]
        loaded_skills = {record["skill"] for record in loaded}
        assert loaded_skills == {"ppt", "pdf", "scrape"}, loaded_skills
        total = sum(record["tokens_est"] for record in loaded)
        assert total < full_guides, (total, full_guides)
        cache_stats = skill_cache.SkillCache(cache_dir).stats()
        assert cache_stats["misses"] >= 2, cache_stats
    print("PASS: multi-skill task ends in DELIVERY with measured context, evidence-gated "
          "manual completion, command-earned validation, one bounded repair and honest limitations")


if __name__ == "__main__":
    main()
