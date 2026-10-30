#!/usr/bin/env python3
"""Create, update and validate the output manifest for a deliverable task.

    python output_manifest.py new --task artifact-001 --out manifest.json \
        --input brief.json --output deck.pptx
    python output_manifest.py mark manifest.json --output deck.pptx \
        --check structure --status passed --evidence evidence/structure.json
    python output_manifest.py validate manifest.json --json

One manifest per task, shipping beside the outputs. It records which checks
actually ran for each output, and it derives - never accepts - the per-output
state ladder:

    generated -> validated -> rendered -> visually_inspected

`generated` only means the file exists. `validated` means structure and content
checks passed with evidence on disk. `rendered` adds layout and render checks;
`visually_inspected` adds the visual pass. Two exceptional states exist: an
output that is gone is `missing`, and one with a failed check is
`needs_repair`. A check you did not run stays `not_run`, and the state says so.
A deck that merely built is `generated`, and the manifest is what stops it being
reported as anything more.

Standard library only. The manifest is a report, not a repair tool: it never
writes output files, only records what exists.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date

SCHEMA = "output-manifest"
SCHEMA_VERSION = 1
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}$")
CHECKS = ("structure", "content", "layout", "render", "visual_review")
STATUSES = ("passed", "failed", "not_run")
FORMATS = ("pptx", "docx", "pdf", "xlsx", "xlsm", "csv", "tsv", "png", "jpg", "html", "other")
EXTENSIONS = {"pptx": "pptx", "docx": "docx", "pdf": "pdf", "xlsx": "xlsx", "xlsm": "xlsm",
              "xltx": "xlsx", "xltm": "xlsm", "csv": "csv", "tsv": "tsv",
              "png": "png", "jpg": "jpg", "jpeg": "jpg", "html": "html"}
# The rungs of the ladder and the checks each one adds.
RUNGS = (("validated", ("structure", "content")),
         ("rendered", ("layout", "render")),
         ("visually_inspected", ("visual_review",)))


def load_manifest(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save_manifest(path, manifest):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def guess_format(path):
    extension = os.path.splitext(path)[1].lstrip(".").lower()
    return EXTENSIONS.get(extension, "other")


def find_output(manifest, output_path):
    for output in manifest.get("outputs", []):
        if output.get("path") == output_path:
            return output
    return None


def derived_state(output, exists):
    """Recompute the state ladder from the checks; never trust a stored one."""
    checks = output.get("checks", {})
    if not exists:
        return "missing"
    if any(check.get("status") == "failed" for check in checks.values()):
        return "needs_repair"
    state = "generated"
    for rung, required in RUNGS:
        if all(checks.get(name, {}).get("status") == "passed" for name in required):
            state = rung
        else:
            break
    return state


def validate_manifest(manifest, base):
    """Return (errors, report); errors nonempty means the manifest is not honest."""
    errors = []
    if not isinstance(manifest, dict):
        return ["manifest must be a JSON object"], {}
    if manifest.get("schema") != SCHEMA:
        errors.append("schema must be %r" % SCHEMA)
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version must be %d" % SCHEMA_VERSION)
    if not isinstance(manifest.get("task_id"), str) or not manifest["task_id"].strip():
        errors.append("task_id is required")
    if "created" in manifest and not (isinstance(manifest["created"], str) and DATE_RE.match(manifest["created"])):
        errors.append("created must be an ISO date (YYYY-MM-DD)")
    skill = manifest.get("skill")
    if skill is not None and (not isinstance(skill, dict)
                              or not isinstance(skill.get("name"), str)
                              or not isinstance(skill.get("version"), str)):
        errors.append("skill must be {\"name\": ..., \"version\": ...}")
    register = manifest.get("sources_register")
    if register is not None:
        if not isinstance(register, str) or not register.strip():
            errors.append("sources_register must be a path")
        elif not os.path.isfile(os.path.join(base, register)):
            errors.append("sources_register %s does not exist" % register)
    if not isinstance(manifest.get("inputs", []), list):
        errors.append("inputs must be a list of paths")
    outputs = manifest.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        errors.append("outputs must be a nonempty list")
        return errors, {}

    report_outputs = []
    for output in outputs:
        path = output.get("path")
        label = "output %s" % (path or "?")
        if not isinstance(path, str) or not path.strip():
            errors.append("%s: path is required" % label)
            continue
        if output.get("format") not in FORMATS:
            errors.append("%s: format must be one of %s" % (label, ", ".join(FORMATS)))
        exists = os.path.isfile(os.path.join(base, path)) or os.path.isdir(os.path.join(base, path))
        checks = output.get("checks", {})
        if not isinstance(checks, dict):
            errors.append("%s: checks must be an object" % label)
            continue
        for name, check in checks.items():
            if name not in CHECKS:
                errors.append("%s: unknown check %r (known: %s)"
                              % (label, name, ", ".join(CHECKS)))
                continue
            if not isinstance(check, dict):
                errors.append("%s: check %s must be an object" % (label, name))
                continue
            status = check.get("status")
            if status not in STATUSES:
                errors.append("%s: check %s status must be one of %s"
                              % (label, name, ", ".join(STATUSES)))
                continue
            evidence = check.get("evidence")
            if status in ("passed", "failed"):
                if not isinstance(evidence, str) or not evidence.strip():
                    errors.append("%s: check %s is %s but records no evidence"
                                  % (label, name, status))
                elif not (os.path.isfile(os.path.join(base, evidence))
                          or os.path.isdir(os.path.join(base, evidence))):
                    errors.append("%s: check %s evidence %s does not exist"
                                  % (label, name, evidence))
            elif evidence:
                errors.append("%s: check %s is not_run but records evidence" % (label, name))
            if status == "failed" and not isinstance(check.get("detail"), str):
                errors.append("%s: failed check %s needs a detail describing the defect"
                              % (label, name))
        state = derived_state(output, exists)
        if "state" in output and output["state"] != state:
            errors.append("%s: state %r is not the derived state %r; the state field is "
                          "computed, never hand-written" % (label, output["state"], state))
        report_outputs.append({"path": path, "format": output.get("format"),
                               "exists": exists, "state": state,
                               "checks": {name: check.get("status") for name, check in checks.items()}})
    report = {"outputs": report_outputs,
              "states": sorted({entry["state"] for entry in report_outputs})}
    return errors, report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new", help="start a manifest for one task")
    new.add_argument("--task", required=True, help="task identifier, e.g. artifact-001")
    new.add_argument("--out", required=True)
    new.add_argument("--input", dest="inputs", action="append", default=[],
                     help="input file (repeatable)")
    new.add_argument("--output", dest="outputs", action="append", default=[],
                     help="output file (repeatable)")
    new.add_argument("--format", action="append", default=[],
                     help="format for the preceding --output (else guessed)")
    new.add_argument("--skill-name", help="producing skill, e.g. pptx-generator")
    new.add_argument("--skill-version", help="producing skill version, e.g. v3.1.0")
    new.add_argument("--register", help="path to the source register the outputs cite "
                                        "(relative paths resolve against the manifest)")

    mark = sub.add_parser("mark", help="record one check result for one output")
    mark.add_argument("manifest")
    mark.add_argument("--output", required=True)
    mark.add_argument("--check", required=True, choices=CHECKS)
    mark.add_argument("--status", required=True, choices=STATUSES)
    mark.add_argument("--evidence", help="file or directory proving the result")
    mark.add_argument("--detail", help="for failures: what is wrong")

    check = sub.add_parser("validate", help="validate a manifest and recompute states")
    check.add_argument("manifest")
    check.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.command == "new":
        outputs = []
        for index, path in enumerate(args.outputs):
            fmt = args.format[index] if index < len(args.format) else guess_format(path)
            if fmt not in FORMATS:
                ap.error("format %r must be one of %s" % (fmt, ", ".join(FORMATS)))
            outputs.append({"path": path, "format": fmt, "checks": {}})
        if not outputs:
            ap.error("record at least one --output")
        manifest = {"schema": SCHEMA, "schema_version": SCHEMA_VERSION,
                    "task_id": args.task, "created": date.today().isoformat(),
                    "inputs": args.inputs, "outputs": outputs}
        if args.skill_name or args.skill_version:
            manifest["skill"] = {"name": args.skill_name or "", "version": args.skill_version or ""}
        if args.register:
            manifest["sources_register"] = args.register.replace(os.sep, "/")
        save_manifest(args.out, manifest)
        print("wrote manifest for %s to %s" % (args.task, args.out))
        return 0

    try:
        manifest = load_manifest(args.manifest)
    except (OSError, json.JSONDecodeError) as exc:
        ap.exit(1, "FAIL: cannot read %s: %s\n" % (args.manifest, exc))
    base = os.path.dirname(os.path.abspath(args.manifest))

    if args.command == "mark":
        output = find_output(manifest, args.output)
        if output is None:
            ap.exit(1, "FAIL: %s lists no output %r\n" % (args.manifest, args.output))
        entry = {"status": args.status}
        if args.evidence:
            entry["evidence"] = args.evidence
        if args.detail:
            entry["detail"] = args.detail
        output.setdefault("checks", {})[args.check] = entry
        exists = os.path.isfile(os.path.join(base, args.output))
        output["state"] = derived_state(output, exists)
        save_manifest(args.manifest, manifest)
        print("marked %s: %s = %s (state: %s)"
              % (args.output, args.check, args.status, output["state"]))
        return 0

    errors, report = validate_manifest(manifest, base)
    if args.json:
        print(json.dumps({"ok": not errors, "errors": errors, **report}, indent=2))
    elif errors:
        for error in errors:
            print("FAIL: %s" % error)
    else:
        for entry in report["outputs"]:
            print("%s [%s]: %s" % (entry["path"], entry["format"], entry["state"]))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
