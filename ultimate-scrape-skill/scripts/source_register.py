#!/usr/bin/env python3
"""Create, extend and validate the shared source register.

    python source_register.py new --out register.json
    python source_register.py add register.json --title "Cost of storage" \
        --url https://example.org/report --type research --claims C1,C2
    python source_register.py validate register.json --json

The register is the one machine-readable handoff between research and the five
format skills: every claim in a deliverable traces to one numbered source, and
every source records where it was seen and whether it was verified. The schema
deliberately has no place for guessed metadata - a field you cannot fill from
the source stays empty, and "verified" is refused without recorded evidence.

Standard library only; works offline alongside `extract_parts.py`.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from urllib.parse import urlsplit

SCHEMA = "source-register"
SCHEMA_VERSION = 1
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}$")
SOURCE_TYPES = ("documentation", "research", "government", "academic", "standard",
                "filing", "dataset", "secondary", "website", "other")
VERIFICATIONS = ("unverified", "verified", "contradicted")
CLAIM_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


def load_register(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save_register(path, register):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(register, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def validate_register(register):
    """Return a list of schema and consistency errors; empty means valid."""
    errors = []
    if not isinstance(register, dict):
        return ["register must be a JSON object"]
    if register.get("schema") != SCHEMA:
        errors.append("schema must be %r" % SCHEMA)
    if register.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version must be %d" % SCHEMA_VERSION)
    sources = register.get("sources")
    if not isinstance(sources, list):
        errors.append("sources must be a list")
        return errors

    known_fields = {"id", "title", "url", "source_type", "author", "publisher",
                    "published", "accessed", "claims", "evidence", "verification", "notes"}
    seen_ids, claim_owner = set(), {}
    for index, source in enumerate(sources, 1):
        label = "source %d" % index
        if not isinstance(source, dict):
            errors.append("%s: must be an object" % label)
            continue
        unknown = sorted(set(source) - known_fields)
        if unknown:
            errors.append("%s: unknown field(s) %s; a field you cannot fill from the "
                          "source stays absent" % (label, ", ".join(unknown)))
        label = "source %s" % (source.get("id") or index)
        source_id = source.get("id")
        if not isinstance(source_id, str) or not source_id.strip():
            errors.append("%s: id is required" % label)
        elif source_id in seen_ids:
            errors.append("%s: duplicate id %r" % (label, source_id))
        else:
            seen_ids.add(source_id)
        title = source.get("title")
        if not isinstance(title, str) or not title.strip():
            errors.append("%s: title is required" % label)
        url = source.get("url")
        if not isinstance(url, str) or urlsplit(url).scheme not in {"http", "https"} \
                or not urlsplit(url).hostname:
            errors.append("%s: url must be an absolute http(s) URL" % label)
        if "source_type" in source and source["source_type"] not in SOURCE_TYPES:
            errors.append("%s: source_type must be one of %s"
                          % (label, ", ".join(SOURCE_TYPES)))
        for field in ("accessed", "published"):
            if field in source and not (isinstance(source[field], str) and DATE_RE.match(source[field])):
                errors.append("%s: %s must be an ISO date (YYYY-MM-DD)" % (label, field))
        verification = source.get("verification", "unverified")
        if verification not in VERIFICATIONS:
            errors.append("%s: verification must be one of %s"
                          % (label, ", ".join(VERIFICATIONS)))
        elif verification == "verified" and not (
                isinstance(source.get("evidence"), str) and source["evidence"].strip()):
            errors.append("%s: verified requires evidence naming where in the source "
                          "the claim is supported" % label)
        claims = source.get("claims", [])
        if not isinstance(claims, list) or any(
                not isinstance(claim, str) or not CLAIM_RE.match(claim) for claim in claims):
            errors.append("%s: claims must be IDs like C1, price-trend" % label)
            continue
        for claim in claims:
            if claim in claim_owner:
                errors.append("claim %r maps to both %s and %s; a claim traces to one source"
                              % (claim, claim_owner[claim], source_id))
            else:
                claim_owner[claim] = source_id
    return errors


def next_id(sources):
    highest = 0
    for source in sources:
        match = re.fullmatch(r"S(\d+)", str(source.get("id", "")))
        if match:
            highest = max(highest, int(match.group(1)))
    return "S%d" % (highest + 1)


def split_claims(raw):
    return [claim.strip() for claim in raw.split(",") if claim.strip()]


def build_entry(args, sources):
    entry = {
        "id": args.id or next_id(sources),
        "title": args.title,
        "url": args.url,
        "accessed": args.accessed or date.today().isoformat(),
        "verification": args.verification,
    }
    if args.type:
        entry["source_type"] = args.type
    if args.author:
        entry["author"] = args.author
    if args.publisher:
        entry["publisher"] = args.publisher
    if args.published:
        entry["published"] = args.published
    if args.claims:
        entry["claims"] = split_claims(args.claims)
    if args.evidence:
        entry["evidence"] = args.evidence
    if args.notes:
        entry["notes"] = args.notes
    return entry


CITATION_KEYS = ("sources", "citations", "references")


def extract_citations(spec):
    """Collect the source IDs a builder spec cites, wherever the convention puts them.

    Word specs cite through `references` blocks (`items[].id`); deck and paired
    specs carry a top-level `sources` list, and slides may name `sources` or
    `citations`. IDs are compared as strings, so a numeric `1` and a register ID
    `1` match - and a spec citing `1` against a register of `S1` IDs does not,
    which is exactly the drift this check exists to catch.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a JSON object")
    if isinstance(spec.get("slides"), list):
        kind = "deck"
    elif isinstance(spec.get("sections"), list):
        kind = "word"
    else:
        raise ValueError("spec must contain a slides or sections list")
    cited = []

    def add(value):
        if isinstance(value, bool):
            return
        if isinstance(value, int):
            value = str(value)
        if isinstance(value, str) and value.strip() and value not in cited:
            cited.append(value)

    def scan(node):
        if isinstance(node, dict):
            if node.get("type") == "references" and isinstance(node.get("items"), list):
                for item in node["items"]:
                    if isinstance(item, dict):
                        add(item.get("id"))
                    else:
                        add(item)
            for key, value in node.items():
                if key in CITATION_KEYS and isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            add(item.get("id"))
                        else:
                            add(item)
                elif isinstance(value, (dict, list)):
                    scan(value)
        elif isinstance(node, list):
            for item in node:
                scan(item)

    scan(spec)
    return kind, cited


def check_spec(register, spec):
    """Cross-reference a builder spec against the register; returns (errors, warnings, summary)."""
    errors = validate_register(register)
    if errors:
        return errors, [], {}
    try:
        kind, cited = extract_citations(spec)
    except ValueError as exc:
        return [str(exc)], [], {}
    warnings = []
    sources = {str(source.get("id")): source for source in register.get("sources", [])}
    for source_id in cited:
        if source_id not in sources:
            errors.append("spec cites %s, which is not in the register; citation IDs and "
                          "register IDs must match exactly" % source_id)
            continue
        verification = sources[source_id].get("verification", "unverified")
        if verification == "contradicted":
            errors.append("spec cites %s, which the register marks contradicted" % source_id)
        elif verification == "unverified":
            warnings.append("spec cites %s, which is still unverified in the register"
                            % source_id)
    claims = {source_id: sources[source_id].get("claims", []) for source_id in cited
              if source_id in sources}
    summary = {"kind": kind, "cited": cited,
               "register_sources": len(sources),
               "register_claims": sum(len(s.get("claims", [])) for s in sources.values()),
               "claims_carried": sum(len(v) for v in claims.values()),
               "uncited_sources": sorted(set(sources) - set(cited))}
    return errors, warnings, summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new", help="write an empty register")
    new.add_argument("--out", required=True)

    add = sub.add_parser("add", help="validate the register, then append one source")
    add.add_argument("register")
    add.add_argument("--id", help="source ID (default: next S<number>)")
    add.add_argument("--title", required=True)
    add.add_argument("--url", required=True)
    add.add_argument("--type", choices=SOURCE_TYPES, help="source type")
    add.add_argument("--author")
    add.add_argument("--publisher")
    add.add_argument("--published", help="publication date, YYYY-MM-DD, only if known")
    add.add_argument("--accessed", help="access date, YYYY-MM-DD (default: today)")
    add.add_argument("--claims", help="comma-separated claim IDs this source supports")
    add.add_argument("--evidence", help="where in the source the claim is supported")
    add.add_argument("--verification", choices=VERIFICATIONS, default="unverified")
    add.add_argument("--notes")

    check = sub.add_parser("validate", help="validate a register")
    check.add_argument("register")
    check.add_argument("--json", action="store_true")

    cross = sub.add_parser("check-spec",
                           help="cross-reference a builder spec's citations against the register")
    cross.add_argument("register")
    cross.add_argument("spec")
    cross.add_argument("--strict", action="store_true",
                       help="citing an unverified source is an error, not a warning")
    cross.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.command == "new":
        save_register(args.out, {"schema": SCHEMA, "schema_version": SCHEMA_VERSION,
                                 "sources": []})
        print("wrote empty register to %s" % args.out)
        return 0

    if args.command == "add":
        try:
            register = load_register(args.register)
        except (OSError, json.JSONDecodeError) as exc:
            ap.exit(1, "FAIL: cannot read %s: %s\n" % (args.register, exc))
        errors = validate_register(register)
        entry = build_entry(args, register.get("sources", []))
        errors.extend(validate_register({"schema": SCHEMA, "schema_version": SCHEMA_VERSION,
                                         "sources": register.get("sources", []) + [entry]}))
        if errors:
            for error in errors:
                print("FAIL: %s" % error)
            return 1
        register.setdefault("sources", []).append(entry)
        save_register(args.register, register)
        print("added %s to %s" % (entry["id"], args.register))
        return 0

    try:
        register = load_register(args.register)
    except (OSError, json.JSONDecodeError) as exc:
        ap.exit(1, "FAIL: cannot read %s: %s\n" % (args.register, exc))
    if args.command == "check-spec":
        try:
            spec = json.loads(open(args.spec, encoding="utf-8").read())
        except (OSError, json.JSONDecodeError) as exc:
            ap.exit(1, "FAIL: cannot read %s: %s\n" % (args.spec, exc))
        errors, warnings, summary = check_spec(register, spec)
        if args.strict:
            errors.extend(warnings)
            warnings = []
        if args.json:
            print(json.dumps({"ok": not errors, "errors": errors,
                              "warnings": warnings, **summary}, indent=2))
        else:
            for problem in errors:
                print("FAIL: %s" % problem)
            for problem in warnings:
                print("WARN: %s" % problem)
            if not errors and not warnings:
                print("PASS: %s spec cites %d of %d register sources (%d of %d claims carried); "
                      "uncited: %s" % (summary["kind"], len(summary["cited"]),
                                       summary["register_sources"], summary["claims_carried"],
                                       summary["register_claims"],
                                       ", ".join(summary["uncited_sources"]) or "none"))
        return 1 if errors else 0

    errors = validate_register(register)
    if args.json:
        print(json.dumps({"ok": not errors, "errors": errors,
                          "sources": len(register.get("sources", [])) if isinstance(register, dict) else 0},
                         indent=2))
    elif errors:
        for error in errors:
            print("FAIL: %s" % error)
    else:
        sources = register.get("sources", [])
        verified = sum(1 for s in sources if s.get("verification") == "verified")
        print("PASS: %d sources, %d verified, %d claims mapped"
              % (len(sources), verified,
                 sum(len(s.get("claims", [])) for s in sources)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
