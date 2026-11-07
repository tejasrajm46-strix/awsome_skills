#!/usr/bin/env python3
"""Task state machine and execution ledger.

    state = TaskState.create(workspace, objective, mode)
    state.transition("SKILL_DISCOVERY", reason="registry index built")
    state.record_step("s3", status="command_completed", outputs=["deck.pptx"], seconds=1.2)
    state.transition("VALIDATION"); state.record_validation({...})
    state.transition("DELIVERY");  print(state.report())

States: CREATED -> UNDERSTANDING -> SKILL_DISCOVERY -> SKILL_LOADING ->
PLANNING -> EXECUTION -> VALIDATION -> DELIVERY, with REPAIR reachable from
EXECUTION (a build failed mid-run) or VALIDATION (a check failed) and always
returning to VALIDATION, plus FAILED and CANCELLED from any non-terminal state. Every transition is checked against this table and
recorded with a reason and timestamp - an orchestration run that cannot say how
it got here is not debuggable.

Step statuses are the completion protocol, and they are deliberately not
interchangeable:

- ``command_completed`` - a controlled command actually ran and returned 0.
  Only the executor sets it; the host LLM cannot self-report it.
- ``manual_pending``    - a manual step (research, render review, a PDF/Excel
  library operation) the host LLM still owes.
- ``manual_completed``  - the host supplied evidence of completion through
  `orchestrator.py done --evidence <file>`. It is work finished, *not* an
  independent validation: a PDF merged by hand-read code is not thereby
  validated.
- ``validated``         - the required independent check actually passed.
  Set only by the validation pass over a validator step that itself ran as a
  controlled command.
- plus ``not_run``, ``failed`` and ``stale``.

Resumption is guarded by `freshen()`: the ledger stores the plan's hash, each
command step's script hash, and each loaded guide's hash. On resume, a plan
that changed after execution began refuses to continue, and any step whose
script or skill guide changed on disk is demoted to ``stale`` so it re-runs
instead of being skipped. Persisted state therefore cannot silently skip work
whose inputs or instructions moved underneath it.
"""
from __future__ import annotations

import json
import os
import sys
import time

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import skill_cache

SCHEMA = "task-state"
SCHEMA_VERSION = 1
STATES = ("CREATED", "UNDERSTANDING", "SKILL_DISCOVERY", "SKILL_LOADING", "PLANNING",
          "EXECUTION", "VALIDATION", "REPAIR", "DELIVERY", "FAILED", "CANCELLED")
TERMINAL = ("DELIVERY", "FAILED", "CANCELLED")
TRANSITIONS = {
    "CREATED": {"UNDERSTANDING", "CANCELLED"},
    "UNDERSTANDING": {"SKILL_DISCOVERY", "FAILED", "CANCELLED"},
    "SKILL_DISCOVERY": {"SKILL_LOADING", "FAILED", "CANCELLED"},
    "SKILL_LOADING": {"PLANNING", "FAILED", "CANCELLED"},
    "PLANNING": {"EXECUTION", "FAILED", "CANCELLED"},
    # A build that fails mid-run may enter REPAIR directly: forcing the host to
    # detour through VALIDATION first left the retry gate closed at the moment
    # it was needed. The budget still bounds how many cycles can open.
    "EXECUTION": {"VALIDATION", "REPAIR", "FAILED", "CANCELLED"},
    "VALIDATION": {"REPAIR", "DELIVERY", "FAILED", "CANCELLED"},
    "REPAIR": {"VALIDATION", "FAILED", "CANCELLED"},
    "DELIVERY": set(), "FAILED": set(), "CANCELLED": set(),
}
REPAIR_LIMITS = {"fast": 1, "balanced": 2, "deep": 3}
STEP_STATUSES = ("command_completed", "manual_pending", "manual_completed",
                 "validated", "not_run", "failed", "stale")
# Work that has actually finished - by controlled command or evidenced manual
# completion. `validated` is strictly stronger and only ever earned by an
# independent check that ran.
DONE_STATUSES = ("command_completed", "manual_completed", "validated")


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


class IllegalTransition(ValueError):
    pass


class StaleTask(RuntimeError):
    """The ledger's plan no longer matches the plan on disk; refuse to resume."""


class TaskState:
    def __init__(self, data, workspace):
        self.data = data
        self.workspace = workspace

    # -- lifecycle ---------------------------------------------------------
    @classmethod
    def create(cls, workspace, objective, mode="balanced", task_id=None):
        if mode not in REPAIR_LIMITS:
            raise ValueError("mode must be one of %s" % ", ".join(REPAIR_LIMITS))
        os.makedirs(workspace, exist_ok=True)
        data = {
            "schema": SCHEMA, "schema_version": SCHEMA_VERSION,
            "task_id": task_id or "task-%s" % time.strftime("%Y%m%d-%H%M%S"),
            "created": _now(), "objective": objective, "mode": mode,
            "state": "CREATED", "repair_limit": REPAIR_LIMITS[mode],
            "interpretation": None, "selected_skills": [], "loaded_context": [],
            "plan": None, "plan_sha256": None, "steps": [], "validation": None,
            "limitations": [], "history": [],
        }
        state = cls(data, workspace)
        state._save()
        return state

    @classmethod
    def load(cls, workspace):
        path = os.path.join(workspace, "task-state.json")
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        if data.get("schema") != SCHEMA:
            raise ValueError("%s is not a task-state ledger" % path)
        return cls(data, workspace)

    def _save(self):
        path = os.path.join(self.workspace, "task-state.json")
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(self.data, handle, indent=2, ensure_ascii=True)
            handle.write("\n")
        os.replace(tmp, path)

    @property
    def state(self):
        return self.data["state"]

    # -- transitions -------------------------------------------------------
    def transition(self, to_state, reason=""):
        if to_state not in STATES:
            raise IllegalTransition("unknown state %r" % to_state)
        if to_state == self.state:
            raise IllegalTransition("already in %s" % to_state)
        if to_state not in TRANSITIONS[self.state]:
            raise IllegalTransition("illegal transition %s -> %s" % (self.state, to_state))
        self.data["history"].append({"from": self.state, "to": to_state,
                                     "at": _now(), "reason": reason})
        self.data["state"] = to_state
        self._save()
        return self.state

    # -- records -----------------------------------------------------------
    def set_interpretation(self, interpretation, selected_skills):
        self.data["interpretation"] = interpretation
        self.data["selected_skills"] = selected_skills
        self._save()

    def add_loaded(self, records):
        self.data["loaded_context"].extend(records)
        self._save()

    def set_plan(self, plan):
        """Record the plan and the hash of plan.json as written to disk."""
        plan_path = os.path.join(self.workspace, "plan.json")
        self.data["plan"] = {"path": "plan.json", "steps": len(plan["steps"])}
        self.data["plan_sha256"] = (skill_cache.sha256_of(plan_path)
                                    if os.path.isfile(plan_path) else None)
        self._save()

    def record_step(self, step_id, status, outputs=None, seconds=None, detail=None,
                    script=None, script_sha256=None, skill=None, independent=False,
                    inputs=None):
        if status not in STEP_STATUSES:
            raise ValueError("unknown step status %r (known: %s)"
                             % (status, ", ".join(STEP_STATUSES)))
        if status == "validated" and not independent:
            raise ValueError("'validated' is only ever set by the independent "
                             "validation pass; manual completion is 'manual_completed'")
        steps = self.data["steps"]
        existing = next((s for s in steps if s["id"] == step_id), None)
        entry = existing or {"id": step_id, "attempts": 0}
        previous = entry.get("status")
        entry.update({"status": status, "at": _now()})
        if status in ("command_completed", "failed"):
            entry["attempts"] = entry.get("attempts", 0) + 1
        if status == "stale" and previous in DONE_STATUSES:
            self.data["history"].append({"step": step_id, "demoted": previous,
                                         "to": "stale", "at": _now()})
        if outputs:
            entry["outputs"] = outputs
        if seconds is not None:
            entry["seconds"] = round(seconds, 3)
        if detail:
            entry["detail"] = detail
        if script:
            entry["script"] = script
        if script_sha256:
            entry["script_sha256"] = script_sha256
        if inputs:
            entry["inputs"] = dict(sorted(inputs.items()))
        if skill and "skill" not in entry:
            entry["skill"] = skill
        if status != "stale" and "stale_reason" in entry and status in DONE_STATUSES:
            entry.pop("stale_reason", None)
        if existing is None:
            steps.append(entry)
        self._save()

    def step(self, step_id):
        return next((s for s in self.data["steps"] if s["id"] == step_id), None)

    def record_validation(self, validation):
        self.data["validation"] = validation
        self._save()

    def repair_count(self):
        return sum(1 for entry in self.data["history"] if entry.get("to") == "REPAIR")

    def add_limitation(self, text):
        if text not in self.data["limitations"]:
            self.data["limitations"].append(text)
            self._save()

    # -- resumption freshness ----------------------------------------------
    def freshen(self, root):
        """Re-verify persisted results against current files; return staleness notes.

        A plan.json that no longer matches its recorded hash is a hard refusal:
        the ledger's step results would describe a plan that no longer exists.
        A command step whose script changed, whose skill guide changed after the
        guide was loaded, or whose own input arguments changed on disk is demoted
        to ``stale`` so the executor re-runs it - resumption never skips work
        whose instructions or inputs moved.
        """
        notes = []
        plan_path = os.path.join(self.workspace, "plan.json")
        recorded = self.data.get("plan_sha256")
        if recorded and os.path.isfile(plan_path):
            current = skill_cache.sha256_of(plan_path)
            if current != recorded:
                raise StaleTask("plan.json changed since execution began; re-plan "
                                "before resuming - recorded results describe a "
                                "different plan")
        for step in self.data["steps"]:
            if step["status"] not in ("command_completed", "manual_completed"):
                continue
            reasons = []
            if step["status"] == "command_completed" and step.get("script"):
                script_path = os.path.join(root, *step["script"].split("/"))
                if os.path.isfile(script_path) and step.get("script_sha256") \
                        and skill_cache.sha256_of(script_path) != step["script_sha256"]:
                    reasons.append("script %s changed since it ran" % step["script"])
            if step.get("skill") and step["status"] == "command_completed":
                guide = next((r for r in reversed(self.data["loaded_context"])
                              if r.get("skill") == step["skill"] and r.get("stage") == "B"
                              and r.get("sha256")), None)
                if guide:
                    guide_path = os.path.join(root, *guide["path"].split("/"))
                    if os.path.isfile(guide_path) and \
                            skill_cache.sha256_of(guide_path) != guide["sha256"]:
                        reasons.append("skill guide %s changed after it was loaded"
                                       % guide["path"])
            if step["status"] == "command_completed":
                for recorded_path, recorded_sha in sorted((step.get("inputs") or {}).items()):
                    input_path = os.path.join(root, *recorded_path.replace("\\", "/").split("/"))
                    if not os.path.isfile(input_path):
                        reasons.append("input %s is gone" % recorded_path)
                    elif recorded_sha and skill_cache.sha256_of(input_path) != recorded_sha:
                        reasons.append("input %s changed since it ran" % recorded_path)
            if reasons:
                note = "%s: %s" % (step["id"], "; ".join(reasons))
                notes.append(note)
                self.record_step(step["id"], "stale", detail="; ".join(reasons))
        if notes:
            self.add_limitation("resumed after changes: %s" % " | ".join(notes))
        return notes

    # -- reporting ---------------------------------------------------------
    def report(self):
        data = self.data
        lines = ["task %s [%s] mode=%s" % (data["task_id"], data["state"], data["mode"]),
                 "objective: %s" % data["objective"]]
        if data["selected_skills"]:
            lines.append("skills: " + ", ".join(data["selected_skills"]))
        steps = data["steps"]
        if steps:
            counts = {}
            for step in steps:
                counts[step["status"]] = counts.get(step["status"], 0) + 1
            lines.append("steps: " + ", ".join("%d %s" % (n, s)
                                               for s, n in sorted(counts.items())))
        if data["validation"]:
            lines.append("validation: %s" % json.dumps(data["validation"])[:300])
        if data["limitations"]:
            lines.append("limitations:")
            lines.extend("  - %s" % item for item in data["limitations"])
        if self.state not in TERMINAL:
            lines.append("(task is not finished; state is %s)" % self.state)
        return "\n".join(lines)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    show = sub.add_parser("show"); show.add_argument("workspace")
    args = ap.parse_args(argv)
    print(TaskState.load(args.workspace).report())
    return 0


if __name__ == "__main__":
    sys.exit(main())
