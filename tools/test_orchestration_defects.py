#!/usr/bin/env python3
"""Regression tests for the six defects found by the v3.1.0 release test.

Each test names the defect it pins down and asserts the behaviour that was
missing, not merely that the code stopped raising:

- E.1 `load --references` across skills: per-skill resolution, clear refusals.
- E.2 REPAIR from EXECUTION: a failed build opens a bounded cycle directly.
- E.3 `freshen()` input hashing: a changed specification demotes the build.
- E.4 `validate` in DELIVERY: an illegal transition is reported, not raised.
- E.5 manifest paths: resolved against the manifest, never the caller's cwd.
- E.6 repair counter and the planner/executor `{{name}}` placeholder contract.
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
import output_manifest
import skill_cache
import skill_registry
import task_executor
import task_planner
import task_state

REPO_ROOT = str(Path(__file__).resolve().parents[1])


def call(func, **kwargs):
    """Run a CLI command function, returning (code, combined output)."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = func(argparse.Namespace(**kwargs))
    return code, buffer.getvalue()


def run_json(*argv):
    """Run the manifest CLI and parse its --json report from a clean buffer."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = output_manifest.main(list(argv))
    return code, json.loads(buffer.getvalue().strip())


def advance(state, *targets):
    for target in targets:
        state.transition(target, reason="test")


def walk_to_execution(workspace, plan, mode="fast"):
    state = task_state.TaskState.create(workspace, "defect regression", mode)
    advance(state, "UNDERSTANDING", "SKILL_DISCOVERY", "SKILL_LOADING", "PLANNING")
    (Path(workspace) / "plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8",
                                               newline="\n")
    state.set_plan(plan)
    advance(state, "EXECUTION")
    return task_state.TaskState.load(workspace)


def failing_plan(workspace):
    """A real allowlisted command that fails deterministically, for REPAIR tests."""
    return {"schema": "task-plan", "schema_version": 1, "mode": "fast", "repair_limit": 1,
            "selected_skills": ["ppt"], "objective": "defect regression",
            "steps": [{"id": "b1-build", "name": "Build the deck", "skill": "ppt",
                       "kind": "build",
                       "command": ["python", "tools/orchestrator.py", "status",
                                   os.path.join(workspace, "does-not-exist")],
                       "depends_on": [], "parallel_group": "build-1", "manual": False,
                       "optional": False, "placeholders": []}]}


# -- E.1 ---------------------------------------------------------------------
def test_references_load_for_every_catalog_skill():
    index = skill_registry.build_index()
    with tempfile.TemporaryDirectory() as tmp:
        task_state.TaskState.create(tmp, "references", "fast")
        for skill in index["skills"]:
            if not skill["references"]:
                continue
            code, output = call(orchestrator.cmd_load, workspace=tmp, skills=[skill["key"]],
                                references=[skill["references"][0]])
            assert code == 0, (skill["key"], output)
            assert "reference" in output, output

        # A basename is enough when it is unambiguous.
        code, output = call(orchestrator.cmd_load, workspace=tmp, skills=["ppt"],
                            references=["deck-schema.md"])
        assert code == 0 and "references/deck-schema.md" in output, output

        # One task-level reference shared by two skills loads from each of them.
        code, output = call(orchestrator.cmd_load, workspace=tmp, skills=["ppt", "word"],
                            references=["references/shared-scraping.md"])
        assert code == 0, output
        assert output.count("references/shared-scraping.md") >= 2, output

        loaded_before = len(task_state.TaskState.load(tmp).data["loaded_context"])

        # A name no requested skill ships is refused with the available list,
        # before anything is recorded - and without a traceback.
        code, output = call(orchestrator.cmd_load, workspace=tmp, skills=["ppt"],
                            references=["references/invented.md"])
        assert code == 1, output
        assert "no requested skill has reference" in output, output
        assert "references/deck-schema.md" in output, output
        assert len(task_state.TaskState.load(tmp).data["loaded_context"]) == loaded_before

        # An unknown catalog key is equally clear.
        code, output = call(orchestrator.cmd_load, workspace=tmp, skills=["nope"],
                            references=[])
        assert code == 1 and "unknown skill" in output, output


# -- E.2 ---------------------------------------------------------------------
def test_failed_build_enters_repair_from_execution():
    with tempfile.TemporaryDirectory() as tmp:
        workspace = os.path.join(tmp, "task")
        plan = failing_plan(workspace)
        walk_to_execution(workspace, plan)
        code, output = call(orchestrator.cmd_run, workspace=workspace, dry_run=False)
        state = task_state.TaskState.load(workspace)
        assert code == 2, output
        assert state.state == "REPAIR", (state.state, output)
        assert state.repair_count() == 1
        assert state.step("b1-build")["status"] == "failed"
        assert "repair cycle 1/1" in output, output

        # Inside the cycle the failed step is retried for real; success lands as
        # a controlled completion, not as a manual claim.
        executed = task_executor.execute_ready(state, plan, task_executor.MockRunner(), REPO_ROOT)
        assert executed == 1, executed
        state = task_state.TaskState.load(workspace)
        assert state.step("b1-build")["status"] == "command_completed"

        # Terminal states stay terminal and invalid transitions are rejected.
        advance(state, "VALIDATION")
        state.transition("DELIVERY", reason="done")
        for target in ("REPAIR", "EXECUTION", "VALIDATION"):
            try:
                state.transition(target)
            except task_state.IllegalTransition:
                continue
            raise AssertionError("DELIVERY -> %s must be illegal" % target)

    # The budget is a hard boundary: with fast (limit 1) the second failure is
    # FAILED, never an endless repair loop.
    with tempfile.TemporaryDirectory() as tmp:
        workspace = os.path.join(tmp, "task")
        plan = failing_plan(workspace)
        state = walk_to_execution(workspace, plan)
        state.record_step("b1-build", "failed", detail="build failed")
        state.transition("VALIDATION", reason="steps complete")
        state.transition("REPAIR", reason="first failure")
        code, output = call(orchestrator.cmd_validate, workspace=workspace)
        state = task_state.TaskState.load(workspace)
        assert code == 1, output
        assert state.state == "FAILED", (state.state, output)
        assert state.repair_count() == state.data["repair_limit"] == 1


# -- E.3 ---------------------------------------------------------------------
def test_freshen_demotes_when_an_input_spec_changes():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "tools").mkdir()
        (root / "specs").mkdir()
        (root / "out").mkdir()
        (root / "tools" / "build_thing.py").write_text("print('built')\n",
                                                       encoding="utf-8", newline="\n")
        spec = root / "specs" / "spec.json"
        spec.write_text('{"title": "v1"}\n', encoding="utf-8", newline="\n")
        workspace = root / "task"
        plan = {"schema": "task-plan", "schema_version": 1, "mode": "fast", "repair_limit": 1,
                "selected_skills": ["ppt"], "objective": "inputs",
                "steps": [{"id": "b1-build", "name": "Build", "skill": "ppt", "kind": "build",
                           "command": ["python", "tools/build_thing.py", "specs/spec.json",
                                       "-o", "out/deck.pptx"],
                           "depends_on": [], "parallel_group": None, "manual": False,
                           "optional": False, "placeholders": []}]}
        state = walk_to_execution(str(workspace), plan)
        task_executor.execute_ready(state, plan, task_executor.MockRunner(), str(root))
        state = task_state.TaskState.load(str(workspace))
        step = state.step("b1-build")
        assert step["status"] == "command_completed"
        assert list(step["inputs"]) == ["specs/spec.json"], step.get("inputs")

        # Unchanged inputs: nothing to do.
        assert state.freshen(str(root)) == []

        # A changed specification demotes the build instead of trusting its output.
        spec.write_text('{"title": "v2"}\n', encoding="utf-8", newline="\n")
        notes = state.freshen(str(root))
        assert notes and "specs/spec.json" in notes[0], notes
        assert "changed" in notes[0], notes
        assert state.step("b1-build")["status"] == "stale"

        # A file the step never named cannot invalidate it: unrelated edits stay
        # unrelated, and the re-run's clean record survives them.
        state.record_step("b1-build", "command_completed", script="tools/build_thing.py",
                          script_sha256=skill_cache.sha256_of(str(root / "tools" / "build_thing.py")),
                          skill="ppt", inputs=task_executor.input_hashes(plan["steps"][0], str(root)))
        (root / "specs" / "unrelated.json").write_text("{}\n", encoding="utf-8", newline="\n")
        assert state.freshen(str(root)) == []

        # A deleted input is reported too, not skipped because the hash is gone.
        task_executor.execute_ready(state, plan, task_executor.MockRunner(), str(root))
        spec.unlink()
        notes = task_executor.input_hashes(plan["steps"][0], str(root))
        assert notes == {}, notes
        state = task_state.TaskState.load(str(workspace))
        notes = state.freshen(str(root))
        assert notes and "is gone" in notes[0], notes


# -- E.4 ---------------------------------------------------------------------
def test_validate_reports_illegal_transition_at_delivery():
    with tempfile.TemporaryDirectory() as tmp:
        workspace = os.path.join(tmp, "task")
        plan = {"schema": "task-plan", "schema_version": 1, "mode": "fast", "repair_limit": 1,
                "selected_skills": [], "objective": "delivery", "steps": []}
        (Path(workspace)).mkdir(parents=True)
        state = task_state.TaskState.create(workspace, "delivery", "fast")
        advance(state, "UNDERSTANDING", "SKILL_DISCOVERY", "SKILL_LOADING", "PLANNING")
        (Path(workspace) / "plan.json").write_text(json.dumps(plan, indent=2),
                                                   encoding="utf-8", newline="\n")
        state.set_plan(plan)
        advance(state, "EXECUTION")
        code, output = call(orchestrator.cmd_validate, workspace=workspace)
        assert code == 0, output
        state = task_state.TaskState.load(workspace)
        assert state.state == "DELIVERY"

        # A failure recorded after delivery used to raise IllegalTransition and
        # take the CLI down. It must be a report that names both states.
        state.record_step("b1-validate", "failed", detail="late failure")
        code, output = call(orchestrator.cmd_validate, workspace=workspace)
        assert code == 1, output
        assert "illegal transition DELIVERY -> REPAIR" in output, output
        assert "the task is DELIVERY" in output, output
        assert task_state.TaskState.load(workspace).state == "DELIVERY"


# -- E.5 ---------------------------------------------------------------------
def test_manifest_paths_resolve_against_the_manifest():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "task"
        (base / "evidence").mkdir(parents=True)
        (base / "evidence" / "structure.json").write_text("{}\n", encoding="utf-8")
        (base / "deck.pptx").write_bytes(b"PK\x03\x04 deck bytes")
        manifest = str(base / "manifest.json")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            assert output_manifest.main(["new", "--task", "t", "--out", manifest,
                                         "--output", "deck.pptx"]) == 0
            assert output_manifest.main(["mark", manifest, "--output", "deck.pptx",
                                         "--check", "structure", "--status", "passed",
                                         "--evidence", "evidence/structure.json"]) == 0
            assert output_manifest.main(["mark", manifest, "--output", "deck.pptx",
                                         "--check", "content", "--status", "passed",
                                         "--evidence", "evidence/structure.json"]) == 0
        # Invoked from an unrelated cwd, the manifest still finds its own files.
        previous = os.getcwd()
        try:
            os.chdir(tmp)
            code, report = run_json("validate", manifest, "--json")
        finally:
            os.chdir(previous)
        assert code == 0, report
        assert report["outputs"][0]["exists"] is True, report
        assert report["outputs"][0]["state"] == "validated", report

        # A file of the same name in the caller's directory is not the output.
        decoy = Path(tmp) / "deck.pptx"
        decoy.write_bytes(b"decoy")
        (base / "deck.pptx").unlink()
        code, report = run_json("validate", manifest, "--json")
        assert report["outputs"][0]["exists"] is False, report
        assert report["outputs"][0]["state"] == "missing", report

        # Absolute paths are used exactly as given.
        decoy_manifest = str(Path(tmp) / "absolute.json")
        with contextlib.redirect_stdout(io.StringIO()):
            assert output_manifest.main(["new", "--task", "abs", "--out", decoy_manifest,
                                         "--output", str(decoy)]) == 0
        code, report = run_json("validate", decoy_manifest, "--json")
        assert code == 0 and report["outputs"][0]["exists"] is True, report


# -- E.6 ---------------------------------------------------------------------
def test_repair_counter_and_placeholder_contract():
    with tempfile.TemporaryDirectory() as tmp:
        workspace = os.path.join(tmp, "task")
        plan = failing_plan(workspace)
        state = walk_to_execution(workspace, plan, "balanced")
        state = task_state.TaskState.load(workspace)
        state.record_step("b1-build", "failed", detail="build failed")
        state.transition("VALIDATION", reason="steps complete")
        code, output = call(orchestrator.cmd_validate, workspace=workspace)
        assert code == 2, output
        # The cycle just opened is cycle 1 of 2, not 2 of 2.
        assert "repair cycle 1/2" in output, output
        assert "repair cycle 2/2" not in output, output
        assert task_state.TaskState.load(workspace).repair_count() == 1

    # The planner emits `{{name}}` placeholders and declares them.
    index = skill_registry.build_index()
    local = {"objective": "x", "mode": "fast",
             "deliverables": [{"format": "pptx", "path": "out/deck.pptx"}],
             "research": {"needed": False}}
    plan = task_planner.build_plan(local, index, "fast")
    build = next(step for step in plan["steps"] if step["id"] == "b1-build")
    assert "{{spec}}" in build["command"], build["command"]
    assert build["placeholders"] == ["spec"], build

    # The executor refuses an unfilled placeholder with an actionable message,
    # not a shell-metacharacter refusal.
    gate = task_executor.check_command(build, REPO_ROOT)
    assert gate is not None, "an unfilled placeholder must not run"
    assert "placeholder {{spec}}" in str(gate), gate
    assert "concrete path" in str(gate), gate
    assert "metacharacters" not in str(gate), gate

    # Boundary cases: the contract is enforced both ways at plan time.
    def step_with(command, placeholders):
        return {"id": "x", "name": "x", "kind": "work", "command": command,
                "depends_on": [], "manual": False, "optional": False,
                "parallel_group": None, "placeholders": placeholders}

    for command, placeholders, fragment in (
            (["python", "tools/orchestrator.py", "<spec>"], [], "angle-bracket"),
            (["python", "tools/orchestrator.py", "{{spec}}"], [], "not declared"),
            (["python", "tools/orchestrator.py", "--flag"], ["spec"], "appear in no argument"),
            (["python", "tools/orchestrator.py", 7], [], "must be strings")):
        try:
            task_planner._check_plan([step_with(command, placeholders)], "fast")
        except ValueError as exc:
            assert fragment in str(exc), (fragment, exc)
        else:
            raise AssertionError("%r must be refused" % (command,))


def main():
    test_references_load_for_every_catalog_skill()
    test_failed_build_enters_repair_from_execution()
    test_freshen_demotes_when_an_input_spec_changes()
    test_validate_reports_illegal_transition_at_delivery()
    test_manifest_paths_resolve_against_the_manifest()
    test_repair_counter_and_placeholder_contract()
    print("PASS: E.1-E.6 - per-skill references, REPAIR from EXECUTION, input-hash "
          "freshness, reported illegal transitions, manifest-relative paths, accurate "
          "repair counting and the {{name}} placeholder contract")


if __name__ == "__main__":
    main()
