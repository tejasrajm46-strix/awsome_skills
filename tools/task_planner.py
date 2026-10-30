#!/usr/bin/env python3
"""Task planner: validate an interpretation, then emit an explicit DAG plan.

    python tools/task_planner.py validate interpretation.json
    python tools/task_planner.py plan interpretation.json --out plan.json --mode deep

The interpretation is authored by the reasoning LLM; this module is the
deterministic contract it must satisfy. Validation refuses:

- deliverables whose format no registered skill supports,
- a task that needs research without the shared helper among the skills,
- interpretations that omit the constraint fields the skills require to be
  asked about (objective and per-deliverable path),
- unknown execution modes.

The generated plan is a dependency graph of steps, each carrying either a
command (allowlisted from the registry's own scripts) or `manual: true` (the
host LLM performs it and reports back through the orchestrator). Ordering
rules: inspection precedes builds, research precedes any build that consumes
it, validation follows its build, delivery comes last; independent builds share
a `parallel_group` so an executor may overlap them.

Modes adjust depth, never safety. fast/balanced/deep change whether render
review, cross-format consistency and extra repair cycles are planned; every
mode plans validation for every deliverable - a plan without validators is
invalid by construction, and the planner re-checks that before returning.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import skill_registry

MODES = ("fast", "balanced", "deep")
MODE_REPAIR = {"fast": 1, "balanced": 2, "deep": 3}


def validate_interpretation(interpretation, index, mode=None):
    """Return errors (empty means valid) plus the resolved skill set."""
    errors = []
    if not isinstance(interpretation, dict):
        return ["interpretation must be a JSON object"], []
    if not (isinstance(interpretation.get("objective"), str) and interpretation["objective"].strip()):
        errors.append("objective is required")
    mode = mode or interpretation.get("mode", "balanced")
    if mode not in MODES:
        errors.append("mode must be one of %s" % ", ".join(MODES))
    deliverables = interpretation.get("deliverables")
    if not isinstance(deliverables, list) or not deliverables:
        errors.append("deliverables must be a nonempty list")
        return errors, []
    selected = []
    for number, deliverable in enumerate(deliverables, 1):
        label = "deliverable %d" % number
        fmt = deliverable.get("format")
        skill_key = skill_registry.skill_for_format(index, fmt or "")
        if not skill_key:
            errors.append("%s: no registered skill supports format %r" % (label, fmt))
            continue
        deliverable["skill"] = skill_key
        if skill_key not in selected:
            selected.append(skill_key)
        if not (isinstance(deliverable.get("path"), str) and deliverable["path"].strip()):
            errors.append("%s: output path is required" % label)
        if os.path.isabs(deliverable.get("path", "")):
            errors.append("%s: output path must be relative to the task workspace" % label)
    research = interpretation.get("research") or {}
    needs_research = bool(research.get("needed"))
    if needs_research:
        helper = next((s["key"] for s in index["skills"] if s["scripts"]["research"]), None)
        if helper and helper not in selected:
            selected.insert(0, helper)
    for source in interpretation.get("inputs", []) or []:
        if not isinstance(source.get("path"), str) or not source["path"].strip():
            errors.append("inputs: each entry needs a path")
    return errors, selected


def _step(step_id, name, skill=None, command=None, depends=(), group=None,
          manual=False, optional=False, kind="work"):
    return {"id": step_id, "name": name, "skill": skill, "kind": kind,
            "command": command, "depends_on": list(depends),
            "parallel_group": group, "manual": manual, "optional": optional}


def build_plan(interpretation, index, mode=None):
    errors, selected = validate_interpretation(interpretation, index, mode)
    if errors:
        raise ValueError("invalid interpretation: %s" % "; ".join(errors))
    mode = mode or interpretation.get("mode", "balanced")
    skills = {s["key"]: s for s in index["skills"]}
    research_needed = bool((interpretation.get("research") or {}).get("needed"))
    helper_key = next((s["key"] for s in index["skills"] if s["scripts"]["research"]), None)
    deliverables = interpretation["deliverables"]

    steps = []
    inspect_id = "s1-inspect-inputs"
    has_inputs = bool(interpretation.get("inputs"))
    steps.append(_step(inspect_id, "Inspect supplied inputs; preserve originals",
                       manual=True))

    research_id, handoff_id = None, None
    if research_needed:
        research_id = "s2-research"
        steps.append(_step(research_id, "Research: bounded extraction, claims to register",
                           skill=helper_key, manual=True))
        handoff_id = "s3-handoff"
        helper_scripts = skills[helper_key]["scripts"]["research"]
        handoff_cmd = None
        for script in helper_scripts:
            if script.endswith("handoff.py"):
                handoff_cmd = ["python", os.path.join(skills[helper_key]["folder"], script),
                               "validate", "<research-dir>/handoff.json"]
        steps.append(_step(handoff_id, "Validate the research handoff bundle",
                           skill=helper_key, command=handoff_cmd, depends=[research_id],
                           optional=handoff_cmd is None, manual=handoff_cmd is None,
                           kind="validation"))

    build_ids = {}
    for number, deliverable in enumerate(deliverables, 1):
        skill = skills[deliverable["skill"]]
        build_id = "b%d-build" % number
        validate_id = "b%d-validate" % number
        depends = []
        if research_needed:
            depends.append(handoff_id or research_id)
        if has_inputs:
            depends.append(inspect_id)
        command = None
        manual = True
        if skill["scripts"]["builders"]:
            builder = skill["scripts"]["builders"][0]
            suffix = ".mjs" if builder.endswith(".mjs") else ".py"
            command = ["node" if suffix == ".mjs" else "python",
                       os.path.join(skill["folder"], builder)] + \
                      (["--dna", "<dna>", "--content", "<content>", "--out",
                        deliverable["path"]] if suffix == ".mjs" else
                       ["<spec>", "-o", deliverable["path"]])
            manual = False
        steps.append(_step(build_id, "Build %s (%s)" % (deliverable["path"], skill["name"]),
                           skill=skill["key"], command=command, depends=depends,
                           group="build-%d" % number, manual=manual, kind="build"))
        build_ids[deliverable["path"]] = build_id
        validator = skill["scripts"]["validators"][0] if skill["scripts"]["validators"] else None
        validate_cmd = None
        validate_manual = True
        if validator:
            suffix = ".mjs" if validator.endswith(".mjs") else ".py"
            validate_cmd = ["node" if suffix == ".mjs" else "python",
                            os.path.join(skill["folder"], validator), deliverable["path"]]
            validate_manual = False
        steps.append(_step(validate_id, "Validate the saved %s" % deliverable["format"],
                           skill=skill["key"], command=validate_cmd, depends=[build_id],
                           manual=validate_manual, optional=validate_cmd is None,
                           kind="validation"))
        if mode in ("balanced", "deep"):
            steps.append(_step("b%d-render-review" % number,
                               "Render (if the host can) and visually review the output",
                               skill=skill["key"], depends=[validate_id], manual=True,
                               optional=True))

    if mode == "deep" and len(deliverables) > 1:
        consistency_deps = ["b%d-validate" % number for number in range(1, len(deliverables) + 1)]
        steps.append(_step("s-consistency",
                           "Cross-format consistency: same register IDs and shared assets",
                           skill=helper_key, depends=consistency_deps, manual=True))
    steps.append(_step("s-manifest", "Write the output manifest for every deliverable",
                       command=["python", os.path.join("tools", "output_manifest.py"),
                                "validate", "<task>/manifest.json"],
                       depends=["b%d-validate" % number for number in
                                range(1, len(deliverables) + 1)],
                       optional=True, manual=True))
    steps.append(_step("s-deliver", "Deliver outputs with an honest validation report",
                       manual=True,
                       depends=["b%d-validate" % number for number in
                                range(1, len(deliverables) + 1)]))
    _check_plan(steps, mode)
    return {"schema": "task-plan", "schema_version": 1, "mode": mode,
            "repair_limit": MODE_REPAIR[mode], "selected_skills": selected,
            "objective": interpretation["objective"], "steps": steps}


def _check_plan(steps, mode):
    """Safety invariants that hold in every mode."""
    known = {step["id"] for step in steps}
    for step in steps:
        for dep in step["depends_on"]:
            if dep not in known:
                raise ValueError("plan step %s depends on missing %s" % (step["id"], dep))
    for step in steps:
        if step["command"]:
            binary, script = step["command"][0], step["command"][1]
            if binary not in {"python", "node"}:
                raise ValueError("step %s may only run python or node" % step["id"])
            if not script.replace(os.sep, "/").startswith(
                    ("ppt_skill/", "word_skill/", "pdf_skill/", "xlsm_skill/",
                     "poster_skill/", "ultimate-scrape-skill/", "tools/")):
                raise ValueError("step %s command %r is outside the repository's "
                                 "allowlisted script roots" % (step["id"], script))
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    check = sub.add_parser("validate")
    check.add_argument("interpretation")
    plan = sub.add_parser("plan")
    plan.add_argument("interpretation")
    plan.add_argument("--out", required=True)
    plan.add_argument("--mode", choices=MODES)
    args = ap.parse_args(argv)
    index = skill_registry.build_index()
    with open(args.interpretation, encoding="utf-8") as handle:
        interpretation = json.load(handle)
    if args.command == "validate":
        errors, selected = validate_interpretation(interpretation, index)
        if errors:
            for error in errors:
                print("FAIL: %s" % error)
            return 1
        print("PASS: skills selected: %s" % ", ".join(selected))
        return 0
    result = build_plan(interpretation, index, args.mode)
    with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
    print("planned %d steps (mode %s, skills: %s) -> %s"
          % (len(result["steps"]), result["mode"], ", ".join(result["selected_skills"]), args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
