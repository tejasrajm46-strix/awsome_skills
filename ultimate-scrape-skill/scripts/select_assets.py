#!/usr/bin/env python3
"""Review gate between downloaded image candidates and the format builders.

    python select_assets.py review work/research/manifest.json
    python select_assets.py approve work/research/manifest.json \
        --asset work/research/assets/image-01.png \
        --use "hero image, slide 3" --license "CC BY 4.0" --attribution "© 2026 A. Okonkwo"
    python select_assets.py reject work/research/manifest.json \
        --asset work/research/assets/image-02.png --reason "watermarked"
    python select_assets.py validate work/research/manifest.json --json

A download is not a decision. Every file the extraction manifest records must
end up either approved (with the intended use and the license/attribution
recorded) or rejected (with a reason) before a builder consumes it; `validate`
refuses an incomplete review. Approvals re-hash the file on disk and compare it
against the manifest record, so a renamed, replaced or stale candidate cannot
sail through on an old decision.

The manifest is the one `extract_parts.py` writes (`downloads`) or the PPT/Word
asset extractor writes (`assets`). Decisions land in `selection.json` beside
the manifest, and `handoff.py` ships them with the research bundle.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import date

SCHEMA = "asset-selection"
SCHEMA_VERSION = 1
RECORD_KEYS = ("downloads", "assets")


def manifest_path_of(selection_path):
    return os.path.join(os.path.dirname(os.path.abspath(selection_path)), "manifest.json")


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def manifest_records(manifest):
    """The downloadable/extracted asset records, from either manifest convention."""
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be a JSON object")
    for key in RECORD_KEYS:
        records = manifest.get(key)
        if isinstance(records, list):
            return records
    raise ValueError("manifest has no %s list; nothing to review" % " or ".join(RECORD_KEYS))


def resolve(base, path):
    """Resolve a record's `file` against the manifest directory."""
    return path if os.path.isabs(path) else os.path.join(base, path)


def file_hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_record(records, asset):
    matches = [record for record in records
               if os.path.normpath(str(record.get("file", ""))) == os.path.normpath(asset)]
    return matches[0] if len(matches) == 1 else None


def load_decisions(manifest_file):
    selection = os.path.join(os.path.dirname(os.path.abspath(manifest_file)), "selection.json")
    if os.path.isfile(selection):
        data = load_json(selection)
        if data.get("schema") != SCHEMA or data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("%s is not a v%d selection file" % (selection, SCHEMA_VERSION))
        return selection, data.setdefault("decisions", [])
    return selection, []


def decide(args, decision):
    try:
        manifest = load_json(args.manifest)
        records = manifest_records(manifest)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        ap_exit("cannot read manifest: %s" % exc)
    base = os.path.dirname(os.path.abspath(args.manifest))
    record = find_record(records, args.asset)
    if record is None:
        ap_exit("%r is not a candidate in this manifest; run review to list them" % args.asset)
    on_disk = resolve(base, args.asset)
    if not os.path.isfile(on_disk):
        ap_exit("candidate file %s does not exist" % on_disk)
    recorded = record.get("sha256")
    if recorded and recorded != file_hash(on_disk):
        ap_exit("%s changed since extraction (sha256 mismatch); re-extract before deciding" % args.asset)
    if args.command == "approve":
        if not args.use:
            ap_exit("approving requires --use describing where and how the asset is used")
        if not (args.license or "").strip():
            ap_exit("approving requires --license (use 'unknown - verify before "
                    "public distribution' when the license is genuinely unclear)")
        entry = {"file": os.path.normpath(args.asset).replace(os.sep, "/"),
                 "sha256": recorded or file_hash(on_disk),
                 "decision": "approved", "use": args.use, "license": args.license,
                 "decided": date.today().isoformat()}
        if args.attribution:
            entry["attribution"] = args.attribution
        if args.source_page:
            entry["source_page"] = args.source_page
    else:
        if not (args.reason or "").strip():
            ap_exit("rejecting requires --reason")
        entry = {"file": os.path.normpath(args.asset).replace(os.sep, "/"),
                 "sha256": recorded or file_hash(on_disk),
                 "decision": "rejected", "reason": args.reason,
                 "decided": date.today().isoformat()}
    selection, decisions = load_decisions(args.manifest)
    decisions[:] = [d for d in decisions if d.get("file") != entry["file"]]
    decisions.append(entry)
    save_json(selection, {"schema": SCHEMA, "schema_version": SCHEMA_VERSION,
                          "decisions": decisions})
    print("%s %s (%d/%d reviewed)" % (decision, entry["file"],
                                      len(decisions), len(records)))
    return 0


def ap_exit(message):
    sys.stderr.write("FAIL: %s\n" % message)
    sys.exit(1)


def validate(args):
    """Every candidate has an honest decision; approvals still match the bytes."""
    errors = []
    try:
        manifest = load_json(args.manifest)
        records = manifest_records(manifest)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print("FAIL: %s" % exc)
        return 1
    base = os.path.dirname(os.path.abspath(args.manifest))
    selection = os.path.join(base, "selection.json")
    decisions = {}
    if os.path.isfile(selection):
        data = load_json(selection)
        if data.get("schema") != SCHEMA or data.get("schema_version") != SCHEMA_VERSION:
            print("FAIL: %s is not a v%d selection file" % (selection, SCHEMA_VERSION))
            return 1
        for decision in data.get("decisions", []):
            name = decision.get("file")
            if name in decisions:
                errors.append("duplicate decision for %s" % name)
            decisions[name] = decision
    reviewed = 0
    approved = []
    for record in records:
        name = os.path.normpath(str(record.get("file", ""))).replace(os.sep, "/")
        label = "candidate %s" % (name or "?")
        decision = decisions.get(name)
        if decision is None:
            errors.append("%s has not been reviewed; approve or reject it before a "
                          "builder consumes it" % label)
            continue
        reviewed += 1
        if decision.get("sha256") and record.get("sha256") \
                and decision["sha256"] != record["sha256"]:
            errors.append("%s decision was made against different bytes" % label)
        on_disk = resolve(base, name)
        if not os.path.isfile(on_disk):
            errors.append("%s no longer exists on disk" % label)
            continue
        if file_hash(on_disk) != decision.get("sha256"):
            errors.append("%s changed since its decision (sha256 mismatch)" % label)
            continue
        if decision.get("decision") == "approved":
            if not (decision.get("use") or "").strip():
                errors.append("%s approval does not say where it is used" % label)
            if not (decision.get("license") or "").strip():
                errors.append("%s approval does not record the license" % label)
            approved.append(name)
        elif decision.get("decision") == "rejected":
            if not (decision.get("reason") or "").strip():
                errors.append("%s rejection does not record a reason" % label)
        else:
            errors.append("%s has unknown decision %r" % (label, decision.get("decision")))
    if args.json:
        print(json.dumps({"ok": not errors, "errors": errors,
                          "candidates": len(records), "reviewed": reviewed,
                          "approved": approved}, indent=2))
    elif errors:
        for error in errors:
            print("FAIL: %s" % error)
    else:
        print("PASS: %d/%d candidates reviewed, %d approved: %s"
              % (reviewed, len(records), len(approved), ", ".join(approved) or "none"))
    return 1 if errors else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    show = sub.add_parser("review", help="list the candidates awaiting a decision")
    show.add_argument("manifest")

    for command, verb in (("approve", "approve"), ("reject", "reject")):
        parser = sub.add_parser(command, help="%s one candidate" % verb)
        parser.add_argument("manifest")
        parser.add_argument("--asset", required=True, help="candidate file from the manifest")
    sub.choices["approve"].add_argument("--use", help="where and how the asset is used")
    sub.choices["approve"].add_argument("--license", help="license as checked at the source")
    sub.choices["approve"].add_argument("--attribution", help="credit the license requires")
    sub.choices["approve"].add_argument("--source-page", help="page the asset came from")
    sub.choices["reject"].add_argument("--reason", help="why this candidate is out")

    check = sub.add_parser("validate", help="refuse an incomplete or stale review")
    check.add_argument("manifest")
    check.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.command == "review":
        try:
            records = manifest_records(load_json(args.manifest))
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            ap_exit(exc)
        base = os.path.dirname(os.path.abspath(args.manifest))
        _, decisions = load_decisions(args.manifest)
        done = {d.get("file") for d in decisions}
        for record in records:
            name = os.path.normpath(str(record.get("file", ""))).replace(os.sep, "/")
            state = "approved" if name in done else "pending"
            print("%-9s %-40s %8s bytes  from %s" % (
                state, name, record.get("bytes", "?"), record.get("source_page", "?")))
        pending = sum(1 for r in records
                      if os.path.normpath(str(r.get("file", ""))).replace(os.sep, "/") not in done)
        print("%d candidate(s), %d pending" % (len(records), pending))
        return 0
    if args.command == "validate":
        return validate(args)
    return decide(args, args.command)


if __name__ == "__main__":
    sys.exit(main())
