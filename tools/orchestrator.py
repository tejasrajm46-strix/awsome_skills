#!/usr/bin/env python3
"""The skill-intelligence orchestrator: one CLI around registry, loader,
planner, executor and state.

    python tools/orchestrator.py new-task  work/tasks/t1 --objective "..." --mode deep
    python tools/orchestrator.py interpret work/tasks/t1 --interpretation interp.json
    python tools/orchestrator.py plan      work/tasks/t1
    python tools/orchestrator.py run       work/tasks/t1          # command steps
    python tools/orchestrator.py done      work/tasks/t1 --step s2-research
    python tools/orchestrator.py status    work/tasks/t1
    python tools/orchestrator.py report    work/tasks/t1

Division of labor - the part an LLM plays and the part this code plays:

- **The host LLM reasons.** It writes `interpretation.json` (objective,
  deliverables, research needs, constraints) and performs every `manual` step
  (research, spec writing, render review, the delivery note), recording each
  via `done`.
- **The registry discovers.** `interpret` resolves formats to catalog skills,
  validates the interpretation, adds the shared helper when research is needed,
  and loads Stage-A metadata - recording exactly what entered the task.
- **The planner plans.** A dependency-ordered DAG whose commands are
  allowlisted repository scripts; modes change depth, never safety.
- **The executor runs.** Allowlisted commands only, real return codes, bounded
  repair; a step that did not run is never reported as run.
- **The state machine remembers.** Every transition, load, attempt and
  validation lands in `task-state.json`; a crashed task resumes from disk.

The orchestrator is a tool the LLM uses - not a sixth skill, and not an
execution environment for arbitrary instructions. See docs in the README and
`references/handoff-contract.md` for the research half of the pipeline.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import skill_cache
import skill_loader
import skill_registry
import task_executor
import task_planner
import task_state


def load_or_create_state(workspace, mode=None):
    if os.path.isfile(os.path.join(workspace, "task-state.json")):
        return task_state.TaskState.load(workspace)
    raise SystemExit("no task at %s; run new-task first" % workspace)


def cmd_new_task(args):
    state = task_state.TaskState.create(args.workspace, args.objective, args.mode)
    state.transition("UNDERSTANDING", reason="task created")
    print("created %s in %s" % (state.data["task_id"], args.workspace))
    return 0


def cmd_interpret(args):
    state = load_or_create_state(args.workspace)
    with open(args.interpretation, encoding="utf-8") as handle:
        interpretation = json.load(handle)
    index = skill_registry.build_index()
    errors, selected = task_planner.validate_interpretation(interpretation, index)
    if errors:
        for error in errors:
            print("FAIL: %s" % error)
        return 1
    loader = skill_loader.SkillLoader(index, skill_cache.SkillCache(
        os.path.join(args.workspace, ".skill-cache")))
    if state.state == "UNDERSTANDING":
        state.transition("SKILL_DISCOVERY", reason="interpretation validated")
    for key in selected:
        info = loader.metadata(key)
        state.add_loaded([info["load_record"]])
    if state.state == "SKILL_DISCOVERY":
        state.transition("SKILL_LOADING", reason="metadata loaded for %s" % ", ".join(selected))
    state.set_interpretation(interpretation, selected)
    stats = loader.loaded_context()
    print("selected: %s (stage-A context: %d files, ~%d tokens, cache %s)"
          % (", ".join(selected), stats["files"], stats["tokens_est"],
             skill_cache.SkillCache(os.path.join(args.workspace, ".skill-cache")).stats()))
    return 0


def cmd_plan(args):
    state = load_or_create_state(args.workspace)
    interpretation = state.data["interpretation"]
    if not interpretation:
        print("FAIL: run interpret first")
        return 1
    index = skill_registry.build_index()
    plan = task_planner.build_plan(interpretation, index, args.mode or state.data["mode"])
    with open(os.path.join(args.workspace, "plan.json"), "w", encoding="utf-8",
              newline="\n") as handle:
        json.dump(plan, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
    state.set_plan(plan)
    # Manual steps start as explicit obligations in the ledger, not as blanks:
    # the validation pass reads them from here.
    for step in plan["steps"]:
        if step.get("manual"):
            state.record_step(step["id"], "manual_pending")
    if state.state == "SKILL_LOADING":
        state.transition("PLANNING", reason="plan built")
    manual = sum(1 for step in plan["steps"] if step.get("manual"))
    print("plan: %d steps (%d manual obligations), mode %s, repair limit %d"
          % (len(plan["steps"]), manual, plan["mode"], plan["repair_limit"]))
    return 0


def cmd_load(args):
    """Stage B/C: load the authoritative guide and on-demand references."""
    state = load_or_create_state(args.workspace)
    index = skill_registry.build_index()
    loader = skill_loader.SkillLoader(index, skill_cache.SkillCache(
        os.path.join(args.workspace, ".skill-cache")))
    records = []
    for key in args.skills:
        info = loader.skill(key)
        records.append(info["load_record"])
        print("loaded %s guide (~%d tokens, %s)"
              % (key, info["tokens_est"],
                 "cached" if info["load_record"]["from_cache"] else "fresh"))
        print("  required references (heuristic): %s"
              % (", ".join(info["required_references"]) or "none flagged"))
        for name in args.references or []:
            ref = loader.reference(key, name)
            records.append(ref["load_record"])
            print("  reference %s (~%d tokens)" % (name, ref["tokens_est"]))
    state.add_loaded(records)
    if state.state == "SKILL_LOADING":
        state.transition("PLANNING", reason="guides loaded for %s" % ", ".join(args.skills))
    stats = loader.loaded_context()
    print("context so far: %d files, ~%d tokens" % (stats["files"], stats["tokens_est"]))
    return 0


def cmd_run(args):
    state = load_or_create_state(args.workspace)
    plan_path = os.path.join(args.workspace, "plan.json")
    if not os.path.isfile(plan_path):
        print("FAIL: run plan first")
        return 1
    with open(plan_path, encoding="utf-8") as handle:
        plan = json.load(handle)
    ready = task_executor.ready_steps(plan, state.data)
    if args.dry_run:
        for step in ready:
            kind = "manual (host LLM)" if step.get("manual") else "command"
            print("%-16s %-8s %s" % (step["id"], kind, step["name"]))
        return 0
    if state.state == "PLANNING":
        state.transition("EXECUTION", reason="execution started")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        stale = state.freshen(root)
    except task_state.StaleTask as exc:
        print("FAIL: %s" % exc)
        return 1
    for note in stale:
        print("STALE: %s (re-running)" % note)
    executed = task_executor.execute_ready(state, plan, task_executor.SubprocessRunner(), root)
    pending_manual = [step["id"] for step in task_executor.ready_steps(plan, state.data)
                      if step.get("manual")]
    ready_auto = [step["id"] for step in task_executor.ready_steps(plan, state.data)
                  if not step.get("manual")]
    print("executed %d command step(s)" % executed)
    if pending_manual:
        print("awaiting the host LLM on manual steps: %s" % ", ".join(pending_manual))
    if ready_auto:
        print("not yet ready (dependencies unmet): %s" % ", ".join(ready_auto))
    return 0


def cmd_done(args):
    state = load_or_create_state(args.workspace)
    plan_path = os.path.join(args.workspace, "plan.json")
    with open(plan_path, encoding="utf-8") as handle:
        plan = json.load(handle)
    step = next((s for s in plan["steps"] if s["id"] == args.step), None)
    if not step:
        print("FAIL: plan has no step %s" % args.step)
        return 1
    if not step.get("manual"):
        print("FAIL: %s is a command step; run it through `run` - a command's "
              "outcome is recorded by the executor, never self-reported" % args.step)
        return 1
    if not args.evidence:
        print("FAIL: manual completion requires --evidence: a file on disk that "
              "shows the work (the handoff validation, the reviewed render, the "
              "notes of the operation). Completion without evidence is refused.")
        return 1
    evidence = os.path.abspath(args.evidence)
    if not os.path.isfile(evidence) and not os.path.isdir(evidence):
        print("FAIL: evidence %s does not exist" % args.evidence)
        return 1
    state.record_step(args.step, "manual_completed",
                      outputs=args.output or [os.path.relpath(evidence)],
                      detail=args.note)
    print("recorded %s as manual_completed (evidence: %s); independent "
          "validation, where the skill has one, still has to run"
          % (args.step, os.path.relpath(evidence)))
    return 0


def cmd_validate(args):
    state = load_or_create_state(args.workspace)
    plan_path = os.path.join(args.workspace, "plan.json")
    with open(plan_path, encoding="utf-8") as handle:
        plan = json.load(handle)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    stale = state.freshen(root)
    for note in stale:
        print("STALE: %s (re-runs on the next `run`)" % note)
    if state.state == "EXECUTION":
        state.transition("VALIDATION", reason="command steps complete")
    statuses = {s["id"]: s["status"] for s in state.data["steps"]}
    failed = [s["id"] for s in state.data["steps"] if s["status"] == "failed"]
    # A step blocks delivery until it is done (or failed) - except an optional
    # step recorded as `not_run`, which is a disclosed skip (host lacked the
    # capability), not pending work.
    pending = [s["id"] for s in plan["steps"]
               if statuses.get(s["id"]) not in task_state.DONE_STATUSES
               and s["id"] not in failed
               and not (s.get("optional") and statuses.get(s["id"]) == "not_run")]
    # Promotion to `validated` happens here and only here: a validation-kind
    # step that ran as a controlled command has passed an independent check.
    # Manual completions are never promoted - they are evidence of work, not
    # of verification.
    for s in plan["steps"]:
        if s.get("kind") == "validation" and statuses.get(s["id"]) == "command_completed":
            state.record_step(s["id"], "validated", independent=True)
    statuses = {s["id"]: s["status"] for s in state.data["steps"]}
    # The completion protocol made visible: command-validated vs manual-only.
    validation_steps = [s for s in plan["steps"] if s.get("kind") == "validation"]
    per_deliverable = [{"step": s["id"], "skill": s.get("skill"),
                        "state": ("validated" if statuses.get(s["id"]) in ("command_completed", "validated")
                                  else statuses.get(s["id"], "manual_pending")
                                  if s.get("manual") else statuses.get(s["id"], "not_run"))}
                       for s in validation_steps]
    fully_validated = all(entry["state"] == "validated" for entry in per_deliverable) \
        and bool(per_deliverable)
    summary = {"deliverable_checks": per_deliverable,
               "fully_validated": fully_validated,
               "failed_steps": failed,
               "pending_steps": pending,
               "repair_used": state.repair_count(),
               "repair_limit": state.data["repair_limit"],
               "stale": stale}
    state.record_validation(summary)
    if failed and state.repair_count() < state.data["repair_limit"]:
        # Stay in REPAIR: the host applies its fix and re-runs the failed steps
        # there; the next `validate` closes the cycle. Bouncing straight back to
        # VALIDATION would leave the retry gate closed and the cycle fiction.
        state.transition("REPAIR", reason="failed steps: %s" % ", ".join(failed))
        print("failed steps recorded; repair cycle %d/%d - fix and `run`, then "
              "`validate` again" % (state.repair_count() + 1, state.data["repair_limit"]))
        return 2
    if failed:
        state.transition("FAILED", reason="repair limit reached with failing steps")
        print("FAILED: %s" % ", ".join(failed))
        return 1
    if pending:
        if state.state == "REPAIR":
            state.transition("VALIDATION", reason="repair applied; revalidating")
        print("awaiting completion of: %s" % ", ".join(pending))
        if not fully_validated:
            print("deliverable checks not fully validated: %s"
                  % ", ".join("%s=%s" % (e["step"], e["state"]) for e in per_deliverable))
        return 0
    if state.state == "REPAIR":
        state.transition("VALIDATION", reason="repair cycle closed")
    if state.state == "VALIDATION":
        state.transition("DELIVERY", reason="all steps completed")
    print("all steps completed; %s" %
          ("every deliverable passed an independent validator"
           if fully_validated else
           "NOT fully validated - manual completions are recorded, not independently checked: %s"
           % ", ".join("%s=%s" % (e["step"], e["state"]) for e in per_deliverable
                       if e["state"] != "validated")))
    return 0


def cmd_status(args):
    print(task_state.TaskState.load(args.workspace).report())
    return 0


def cmd_report(args):
    state = task_state.TaskState.load(args.workspace)
    data = state.data
    print(state.report())
    loaded = data["loaded_context"]
    if loaded:
        print("context loaded: %d files, ~%d tokens" %
              (len(loaded), sum(r["tokens_est"] for r in loaded)))
    cache = skill_cache.SkillCache(os.path.join(args.workspace, ".skill-cache"))
    print("cache: %s" % json.dumps(cache.stats()))
    done_steps = [s for s in data["steps"] if s["status"] in task_state.DONE_STATUSES]
    print("steps done: %s" % (", ".join("%s=%s" % (s["id"], s["status"]) for s in done_steps) or "none"))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    new = sub.add_parser("new-task")
    new.add_argument("workspace")
    new.add_argument("--objective", required=True)
    new.add_argument("--mode", default="balanced", choices=task_state.REPAIR_LIMITS.keys())
    new.set_defaults(func=cmd_new_task)

    interp = sub.add_parser("interpret")
    interp.add_argument("workspace")
    interp.add_argument("--interpretation", required=True)
    interp.set_defaults(func=cmd_interpret)

    def plan_extra(parser):
        parser.add_argument("--mode", choices=task_planner.MODES,
                            help="override the task's execution mode for this plan")

    def run_extra(parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="list ready steps without executing")

    for name, func, extra in (("plan", cmd_plan, plan_extra), ("run", cmd_run, run_extra),
                              ("status", cmd_status, None), ("report", cmd_report, None),
                              ("validate", cmd_validate, None)):
        parser = sub.add_parser(name)
        parser.add_argument("workspace")
        if extra:
            extra(parser)
        parser.set_defaults(func=func)

    load = sub.add_parser("load")
    load.add_argument("workspace")
    load.add_argument("--skills", nargs="+", required=True)
    load.add_argument("--references", nargs="*", default=[])
    load.set_defaults(func=cmd_load)

    done = sub.add_parser("done")
    done.add_argument("workspace")
    done.add_argument("--step", required=True)
    done.add_argument("--evidence", required=True,
                      help="a file or directory on disk evidencing the manual work")
    done.add_argument("--output", action="append", default=[])
    done.add_argument("--note", default=None)
    done.set_defaults(func=cmd_done)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
