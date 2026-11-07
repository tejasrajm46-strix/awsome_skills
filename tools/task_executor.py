#!/usr/bin/env python3
"""Controlled plan execution: allowlisted commands, real results, bounded repair.

    from task_executor import SubprocessRunner, MockRunner, execute_ready
    result = execute_ready(state, plan, runner, cwd=workspace)

The executor runs only plan steps whose dependencies have succeeded. A step
carries either a command (executed here) or `manual: true` (the host LLM
performs it and records the outcome through the orchestrator). Both kinds end
in the ledger with their actual outcome - the executor has no code path that
can mark a step succeeded without an observed result.

Controls, in order:

- **Allowlist.** The plan's commands were already checked at plan time; the
  executor re-checks each before running: python/node only, script path inside
  the repository's skill/tool roots, no shell, no chained commands (`;`, `&&`,
  `|`), no output redirection. A command that an untrusted page talked the
  planner into carrying cannot pass this gate.
- **Timeouts.** Every subprocess gets a wall-clock timeout; a timeout is a
  failed attempt, not a hang.
- **Bounded repair.** A failed validation step may be retried after repair up
  to the plan's `repair_limit`; the executor never re-runs a step whose
  dependencies have not succeeded, never re-runs a succeeded step, and refuses
  to keep repairing past the limit - unresolved failures stay recorded as
  failed and the task moves to FAILED honestly.
- **Mockable.** `MockRunner` implements the same interface from a scripted
  table of outcomes, which is what the deterministic orchestration tests use;
  production uses `SubprocessRunner`.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import task_state
import skill_cache

ALLOWED_ROOTS = ("ppt_skill/", "word_skill/", "pdf_skill/", "xlsm_skill/",
                 "poster_skill/", "ultimate-scrape-skill/", "tools/")
CHAINED = re.compile(r"[;|&<>`]|\$\(")
# Plans carry `{{name}}` placeholders for values only the host can know (the
# builder spec, the research directory). The planner declares them, the executor
# refuses to run a step that still contains one, and both use this shape - the
# old `<spec>` form was rejected as shell redirection, which made the failure
# look like a security refusal instead of an unfinished plan.
PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z0-9_-]+)\s*\}\}")
OUTPUT_TAIL = 4000


class StepResult:
    def __init__(self, ok, returncode=None, stdout="", stderr="", seconds=0.0, reason=None):
        self.ok = ok
        self.returncode = returncode
        self.stdout = stdout[-OUTPUT_TAIL:]
        self.stderr = stderr[-OUTPUT_TAIL:]
        self.seconds = seconds
        self.reason = reason

    def summary(self):
        text = (self.stderr or self.stdout or "").strip().splitlines()
        detail = text[-1][:300] if text else (self.reason or "")
        return {"ok": self.ok, "returncode": self.returncode,
                "seconds": round(self.seconds, 3), "detail": detail}


def _contained(root, path):
    """True when path's real location stays inside root's real location.

    Symlinks and junctions are resolved before the containment check, so a
    link placed inside a skill folder cannot smuggle a script in from outside
    the repository.
    """
    real_root = os.path.realpath(root)
    real_path = os.path.realpath(path)
    return os.path.commonpath([real_root, real_path]) == real_root


def check_command(step, root):
    """The executor's own gate, independent of the planner's."""
    if step.get("manual"):
        return None
    command = step.get("command")
    if not command or not isinstance(command, list) or len(command) < 2:
        return ValueError("step %s has no executable command" % step["id"])
    binary, script = command[0], command[1]
    if binary not in {"python", "node"}:
        return ValueError("step %s: binary %r is not allowlisted" % (step["id"], binary))
    normalized = script.replace(os.sep, "/")
    if normalized.startswith("/") or ".." in normalized.split("/") or ":" in normalized:
        return ValueError("step %s: script path %r escapes the repository" % (step["id"], script))
    if not any(normalized.startswith(prefix) for prefix in ALLOWED_ROOTS):
        return ValueError("step %s: script %r is outside the allowlisted roots" % (step["id"], script))
    if root and os.path.isdir(root):
        absolute = os.path.join(root, normalized)
        if not os.path.isfile(absolute):
            return ValueError("step %s: script %s does not exist" % (step["id"], script))
        if not _contained(root, absolute):
            return ValueError("step %s: script %s resolves outside the repository "
                              "(symlink or junction)" % (step["id"], script))
    for argument in command[2:]:
        if not isinstance(argument, str):
            return ValueError("step %s: command arguments must be strings" % step["id"])
        placeholder = PLACEHOLDER.search(argument)
        if placeholder:
            return ValueError("step %s: argument %r still holds the placeholder %s; the "
                              "host must replace it with a concrete path in plan.json "
                              "before this step can run"
                              % (step["id"], argument, placeholder.group(0)))
        if CHAINED.search(argument):
            return ValueError("step %s: argument %r contains shell metacharacters; "
                              "commands run without a shell" % (step["id"], argument))
    return None


def input_hashes(step, root):
    """Content hashes of the files a step's own arguments name.

    Only arguments that resolve to an existing file inside the repository count:
    flags and output paths are not inputs, so an unrelated file changing never
    invalidates a step. `task_state.freshen()` compares these on resume, which
    is what stops a specification edited after a build from letting the stale
    output pass as current.
    """
    hashes = {}
    if not root or not os.path.isdir(root):
        return hashes
    for argument in (step.get("command") or [])[2:]:
        if not isinstance(argument, str) or argument.startswith("-"):
            continue
        normalized = argument.replace(os.sep, "/")
        candidate = (argument if os.path.isabs(argument)
                     else os.path.join(root, *normalized.split("/")))
        if os.path.isfile(candidate) and _contained(root, candidate):
            hashes[normalized] = skill_cache.sha256_of(candidate)
    return hashes


class SubprocessRunner:
    def __init__(self, timeout=600):
        self.timeout = timeout

    def run(self, step, root):
        error = check_command(step, root)
        if error:
            return StepResult(False, reason=str(error))
        command = list(step["command"])
        started = time.monotonic()
        try:
            completed = subprocess.run(command, cwd=root, capture_output=True,
                                       text=True, timeout=self.timeout, shell=False)
        except subprocess.TimeoutExpired:
            return StepResult(False, reason="timed out after %ss" % self.timeout,
                              seconds=time.monotonic() - started)
        except OSError as exc:
            return StepResult(False, reason=str(exc), seconds=time.monotonic() - started)
        return StepResult(completed.returncode == 0, completed.returncode,
                          completed.stdout, completed.stderr,
                          time.monotonic() - started)


class MockRunner:
    """Scripted outcomes: {step_id: (ok, stdout, stderr)} - missing ids succeed."""

    def __init__(self, outcomes=None, fail_first=None):
        self.outcomes = outcomes or {}
        self.fail_first = dict(fail_first or {})
        self.calls = []

    def run(self, step, root):
        self.calls.append(step["id"])
        if self.fail_first.get(step["id"], 0) > 0:
            self.fail_first[step["id"]] -= 1
            return StepResult(False, 1, "", "mock failure of %s" % step["id"])
        ok, out, err = self.outcomes.get(step["id"], (True, "mock ok", ""))
        return StepResult(ok, 0 if ok else 1, out, err)


def ready_steps(plan, state_data):
    """Steps whose dependencies are done and that are not done yet.

    A step is done only in the DONE_STATUSES sense (command_completed,
    manual_completed, validated). Failed dependencies block their dependents;
    stale ones simply no longer count as done, so their dependents re-run too.
    """
    done = {s["id"] for s in state_data.get("steps", []) if s["status"] in task_state.DONE_STATUSES}
    failed = {s["id"] for s in state_data.get("steps", []) if s["status"] == "failed"}
    ready = []
    for step in plan["steps"]:
        if step["id"] in done:
            continue
        if all(dep in done for dep in step["depends_on"]):
            if any(dep in failed for dep in step["depends_on"]):
                continue
            ready.append(step)
    return ready


def execute_ready(state, plan, runner, root, max_steps=100):
    """Run every ready command step in dependency order; returns the count run.

    Success is only ever recorded as ``command_completed`` with the script and
    its content hash at execution time - the evidence `freshen()` uses on
    resume. The environment is inherited unchanged from the host (PATH and
    friends are required to find python/node); no environment variable is set
    or modified here. A timed-out subprocess is killed by `subprocess.run`
    before TimeoutExpired propagates, so no orphan keeps running.
    """
    executed = 0
    while executed < max_steps:
        ready = ready_steps(plan, state.data)
        failed_ids = {s["id"] for s in state.data.get("steps", []) if s["status"] == "failed"}
        # A failed step is retried only inside a REPAIR cycle - blind retries
        # outside one would be an unbounded loop wearing a workflow's clothes.
        runnable = [step for step in ready
                    if not step.get("manual")
                    and (step["id"] not in failed_ids or state.state == "REPAIR")]
        if not runnable:
            break
        step = runnable[0]
        if state.state not in ("EXECUTION", "REPAIR"):
            break
        script = step["command"][1].replace(os.sep, "/")
        script_sha = None
        script_path = os.path.join(root, *script.split("/"))
        if os.path.isfile(script_path):
            script_sha = skill_cache.sha256_of(script_path)
        result = runner.run(step, root)
        if result.ok:
            state.record_step(step["id"], "command_completed",
                              seconds=result.seconds,
                              detail=result.summary()["detail"] or None,
                              script=script, script_sha256=script_sha,
                              skill=step.get("skill"),
                              inputs=input_hashes(step, root))
        else:
            state.record_step(step["id"], "failed",
                              seconds=result.seconds,
                              detail=result.summary()["detail"] or None,
                              skill=step.get("skill"))
        executed += 1
        if not result.ok:
            break
    return executed


def main(argv=None):
    import argparse
    import json
    import task_state
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workspace", help="task workspace with task-state.json and plan.json")
    ap.add_argument("--dry-run", action="store_true", help="list ready steps, run nothing")
    args = ap.parse_args(argv)
    state = task_state.TaskState.load(args.workspace)
    with open(os.path.join(args.workspace, "plan.json"), encoding="utf-8") as handle:
        plan = json.load(handle)
    ready = ready_steps(plan, state.data)
    if not ready:
        print("no ready steps; state=%s" % state.state)
        return 0
    for step in ready:
        gate = check_command(step, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        status = "manual (host LLM)" if step.get("manual") else \
                 ("refused: %s" % gate if gate else "runnable: %s" % " ".join(step["command"]))
        print("%-16s %s" % (step["id"], status))
    if args.dry_run:
        return 0
    executed = execute_ready(state, plan, SubprocessRunner(), os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
    print("executed %d command step(s)" % executed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
