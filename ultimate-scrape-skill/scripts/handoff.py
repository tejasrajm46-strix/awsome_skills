#!/usr/bin/env python3
"""Assemble and validate the research handoff bundle for the format skills.

    python handoff.py bundle work/research --out work/research/handoff.json \
        --brief "storage-cost deck + word brief" \
        --limitation "JavaScript-only pricing page not fetched; figures from the PDF report"
    python handoff.py validate work/research/handoff.json --json

One brief, one bundle. `handoff.json` is the single predictable structure a
format skill reads at the start of a task: which register the claims live in,
which assets were approved for use (and which were rejected), where the page
data and theme tokens are, and which limitations the next skill must carry into
its delivery note. Every referenced file is validated in place - the register
against its schema, the asset review against the extraction manifest, the
approved files against their recorded hashes - so a bundle that validates is a
bundle the five format skills can consume without re-deciding anything.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

SCHEMA = "research-handoff"
SCHEMA_VERSION = 1
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import select_assets
import source_register


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def rel(base, path):
    return os.path.relpath(path, base).replace(os.sep, "/")


def build(args):
    """Assemble the bundle from the research directory's own artifacts."""
    research = os.path.abspath(args.research)
    if not os.path.isdir(research):
        ap_exit("no research directory at %s" % research)
    register_path = os.path.join(research, "register.json")
    manifest_path = os.path.join(research, "manifest.json")
    if not os.path.isfile(register_path):
        ap_exit("research directory has no register.json; create one with source_register.py")
    if not os.path.isfile(manifest_path):
        ap_exit("research directory has no manifest.json; extraction never ran here")
    register = load_json(register_path)
    errors = source_register.validate_register(register)
    if errors:
        for error in errors:
            print("FAIL: register.json: %s" % error)
        sys.exit(1)
    manifest = load_json(manifest_path)
    try:
        records = select_assets.manifest_records(manifest)
    except ValueError as exc:
        ap_exit(exc)
    bundle = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "created": date.today().isoformat(),
        "register": {"path": "register.json",
                     "sources": len(register.get("sources", [])),
                     "claims": sum(len(s.get("claims", [])) for s in register.get("sources", []))},
        "assets": {"manifest": "manifest.json", "candidates": len(records)},
        "limitations": list(args.limitation) or ["none identified"],
    }
    if args.brief:
        bundle["brief"] = args.brief
    selection_path = os.path.join(research, "selection.json")
    if os.path.isfile(selection_path):
        bundle["assets"]["selection"] = "selection.json"
    data_path = os.path.join(research, "data.json")
    if os.path.isfile(data_path):
        bundle["data"] = {"path": "data.json"}
    theme_path = os.path.join(research, "theme.json")
    if os.path.isfile(theme_path):
        bundle["theme"] = {"path": "theme.json"}
    return bundle


def validate(bundle, base):
    """Errors list; empty means the bundle is an honest, consumable handoff."""
    errors = []
    if not isinstance(bundle, dict) or bundle.get("schema") != SCHEMA:
        return ["this is not a %s bundle" % SCHEMA]
    if bundle.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version must be %d" % SCHEMA_VERSION)
    if not (isinstance(bundle.get("created"), str) and len(bundle["created"]) == 10):
        errors.append("created must be an ISO date")
    register = bundle.get("register")
    if not isinstance(register, dict) or not isinstance(register.get("path"), str):
        errors.append("register.path is required")
    else:
        register_file = os.path.join(base, register["path"])
        if not os.path.isfile(register_file):
            errors.append("register %s does not exist" % register["path"])
        else:
            for error in source_register.validate_register(load_json(register_file)):
                errors.append("register: %s" % error)
    assets = bundle.get("assets")
    if not isinstance(assets, dict) or not isinstance(assets.get("manifest"), str):
        errors.append("assets.manifest is required")
    else:
        manifest_file = os.path.join(base, assets["manifest"])
        if not os.path.isfile(manifest_file):
            errors.append("asset manifest %s does not exist" % assets["manifest"])
        else:
            try:
                records = select_assets.manifest_records(load_json(manifest_file))
            except ValueError as exc:
                errors.append(str(exc))
                records = []
            selection = assets.get("selection")
            if not isinstance(selection, str):
                errors.append("assets.selection is required; every candidate needs a "
                              "review decision before a builder consumes it")
            else:
                selection_file = os.path.join(base, selection)
                if not os.path.isfile(selection_file):
                    errors.append("selection file %s does not exist" % selection)
                else:
                    fake = argparse.Namespace()
                    fake.json = True
                    fake.manifest = manifest_file
                    result = json.loads(_capture(lambda: select_assets.validate(fake)))
                    for error in result["errors"]:
                        errors.append("asset review: %s" % error)
    limitations = bundle.get("limitations")
    if not isinstance(limitations, list) or not limitations \
            or not all(isinstance(item, str) and item.strip() for item in limitations):
        errors.append("limitations must be a nonempty list of strings; use "
                      "'none identified' when there genuinely are none")
    for part in ("data", "theme"):
        section = bundle.get(part)
        if section is not None:
            if not isinstance(section, dict) or not isinstance(section.get("path"), str):
                errors.append("%s must be {\"path\": ...}" % part)
            elif not os.path.isfile(os.path.join(base, section["path"])):
                errors.append("%s file %s does not exist" % (part, section["path"]))
    return errors


def _capture(call):
    import contextlib
    import io
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        code = call()
    return captured.getvalue()


def ap_exit(message):
    sys.stderr.write("FAIL: %s\n" % message)
    sys.exit(1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    bundle = sub.add_parser("bundle", help="assemble handoff.json from a research directory")
    bundle.add_argument("research")
    bundle.add_argument("--out", help="bundle path (default: <research>/handoff.json)")
    bundle.add_argument("--brief", help="one line naming the deliverables this feeds")
    bundle.add_argument("--limitation", action="append", default=[],
                        help="capability or coverage gap the next skill must disclose "
                             "(repeatable; default: 'none identified')")

    check = sub.add_parser("validate", help="validate a handoff bundle")
    check.add_argument("bundle")
    check.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.command == "bundle":
        assembled = build(args)
        out = args.out or os.path.join(os.path.abspath(args.research), "handoff.json")
        save_json(out, assembled)
        print("wrote %s (%d register sources, %d asset candidates, %d limitation(s))"
              % (out, assembled["register"]["sources"], assembled["assets"]["candidates"],
                 len(assembled["limitations"])))
        return 0

    try:
        stored = load_json(args.bundle)
    except (OSError, json.JSONDecodeError) as exc:
        ap_exit("cannot read %s: %s" % (args.bundle, exc))
    base = os.path.dirname(os.path.abspath(args.bundle))
    errors = validate(stored, base)
    if args.json:
        print(json.dumps({"ok": not errors, "errors": errors}, indent=2))
    elif errors:
        for error in errors:
            print("FAIL: %s" % error)
    else:
        print("PASS: register, asset review, data, theme and limitations all check out")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
