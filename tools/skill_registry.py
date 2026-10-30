#!/usr/bin/env python3
"""Skill registry: build a validated, catalog-driven index of the collection.

    python tools/skill_registry.py index --json
    python tools/skill_registry.py discover --formats pptx,pdf --json

The index is derived from `skills.json` and each skill's own `SKILL.md`
frontmatter and file tree - the five current skills are not hardcoded anywhere
in this module. A new compatible skill becomes discoverable by adding a catalog
entry and following the repository's script conventions:

    build_*.py|compose*.mjs   builder      - creates the deliverable
    validate_*.py|qa*.mjs     validator    - reopens and checks the saved output
    inspect_*.py              inspector    - dependency-free file inventory
    route.py/extract_*.py/source_register.py/select_assets.py/handoff.py
                              research pipeline of the shared helper

Anything the registry cannot verify (a declared script that does not exist, a
missing frontmatter field) is a validation error, not a warning: orchestration
decisions are only as good as the metadata behind them.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)
FIELD = re.compile(r"^(name|description|version|compatibility|license): (.*)$", re.M)

BUILDER = re.compile(r"^(build_.*|compose.*|render.*)\.(py|mjs)$")
VALIDATOR = re.compile(r"^(validate_.*|qa.*)\.(py|mjs)$")
INSPECTOR = re.compile(r"^inspect_.*\.py$")
RESEARCH_SCRIPTS = ("route.py", "extract_parts.py", "source_register.py",
                    "select_assets.py", "handoff.py", "contact_sheet.py")


def read_text(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def parse_frontmatter(guide):
    match = FRONTMATTER.match(guide.replace("\r\n", "\n"))
    if not match:
        raise ValueError("SKILL.md has no frontmatter block")
    fields = {key: value.strip() for key, value in FIELD.findall(match.group(1))}
    missing = {"name", "description", "version"} - set(fields)
    if missing:
        raise ValueError("frontmatter is missing %s" % ", ".join(sorted(missing)))
    return fields


def token_estimate(text):
    """Rough deployment-cost estimate; the gate uses the same 4-chars-per-token."""
    return max(1, round(len(text) / 4))


def classify_scripts(folder):
    builders, validators, inspectors, research = [], [], [], []
    scripts_dir = os.path.join(folder, "scripts")
    if os.path.isdir(scripts_dir):
        for name in sorted(os.listdir(scripts_dir)):
            if BUILDER.match(name):
                builders.append("scripts/" + name)
            elif VALIDATOR.match(name):
                validators.append("scripts/" + name)
            elif INSPECTOR.match(name):
                inspectors.append("scripts/" + name)
            if name in RESEARCH_SCRIPTS:
                research.append("scripts/" + name)
    return {"builders": builders, "validators": validators,
            "inspectors": inspectors, "research": research}


def tree_listing(folder, sub):
    base = os.path.join(folder, sub)
    if not os.path.isdir(base):
        return []
    return sorted(sub + "/" + name for name in os.listdir(base)
                  if not name.startswith("."))


def build_entry(catalog_entry, root):
    folder = os.path.join(root, catalog_entry["folder"])
    if not os.path.isdir(folder):
        raise ValueError("catalog folder %s does not exist" % catalog_entry["folder"])
    guide_path = os.path.join(folder, "SKILL.md")
    if not os.path.isfile(guide_path):
        raise ValueError("skill %s has no SKILL.md" % catalog_entry["key"])
    guide = read_text(guide_path)
    fields = parse_frontmatter(guide)
    if fields["name"] != catalog_entry["name"]:
        raise ValueError("catalog name %r disagrees with frontmatter name %r"
                         % (catalog_entry["name"], fields["name"]))
    entry = {
        "key": catalog_entry["key"],
        "folder": catalog_entry["folder"],
        "name": fields["name"],
        "version": fields["version"],
        "description": fields["description"],
        "compatibility": fields.get("compatibility", ""),
        "formats": list(catalog_entry.get("formats", [])),
        "shared_helper": catalog_entry.get("shared_helper"),
        "token_estimate": token_estimate(guide),
        "scripts": classify_scripts(folder),
        "references": tree_listing(folder, "references"),
        "tests": [name for name in tree_listing(folder, "tests")],
        "evals": "evals/evals.json" if os.path.isfile(os.path.join(folder, "evals/evals.json")) else None,
    }
    # How the orchestrator can drive this skill: a script builder, the shared
    # research pipeline, or inspection + guidance (the host LLM writes library
    # code per the guide, as the PDF and Excel skills prescribe).
    if entry["scripts"]["builders"]:
        entry["execution_surface"] = "builder"
    elif entry["scripts"]["research"]:
        entry["execution_surface"] = "research"
    elif entry["scripts"]["inspectors"]:
        entry["execution_surface"] = "inspection"
    else:
        entry["execution_surface"] = "manual"
    if catalog_entry["key"] != "scrape" and not entry["shared_helper"]:
        raise ValueError("format skill %s declares no shared_helper" % entry["key"])
    if not entry["formats"]:
        raise ValueError("skill %s declares no formats" % entry["key"])
    if entry["execution_surface"] == "manual":
        raise ValueError("skill %s has no builder, research script or inspector; "
                         "the orchestrator could not drive it at all" % entry["key"])
    return entry


def build_index(root=REPO):
    catalog = json.loads(read_text(os.path.join(root, "skills.json")))
    skills = [build_entry(entry, root) for entry in catalog["skills"]]
    names = [skill["name"] for skill in skills]
    if len(names) != len(set(names)):
        raise ValueError("duplicate skill names in catalog")
    index = {"schema": "skill-index", "schema_version": 1,
             "catalog_version": catalog["version"], "root": os.path.abspath(root),
             "skills": skills}
    validate_index(index)
    return index


def validate_index(index):
    for skill in index["skills"]:
        folder = os.path.join(index["root"], skill["folder"])
        for group in ("builders", "validators", "inspectors", "research"):
            for script in skill["scripts"][group]:
                if not os.path.isfile(os.path.join(folder, script)):
                    raise ValueError("%s lists missing script %s" % (skill["key"], script))
        for reference in skill["references"]:
            if not os.path.isfile(os.path.join(folder, reference)):
                raise ValueError("%s lists missing reference %s" % (skill["key"], reference))
        if skill["shared_helper"]:
            helper = os.path.join(index["root"], skill["shared_helper"])
            if not os.path.isdir(helper):
                raise ValueError("%s declares missing shared helper %s"
                                 % (skill["key"], skill["shared_helper"]))
    return True


def skill_for_format(index, fmt):
    fmt = fmt.lower().lstrip(".")
    exact = [s for s in index["skills"] if fmt in [f.lower() for f in s["formats"]]]
    if exact:
        return exact[0]["key"]
    aliases = {"pptx": "pptx", "docx": "docx", "ppt": "pptx", "word": "docx",
               "excel": "xlsx", "xlsm": "xlsm", "presentation": "pptx"}
    if fmt in aliases:
        return skill_for_format(index, aliases[fmt])
    return None


def discover(index, formats=None, intent=None, research=None):
    """Rank candidate skills for a task; a deterministic discovery aid, not the selector."""
    wanted = []
    for fmt in formats or []:
        key = skill_for_format(index, fmt)
        if key and key not in wanted:
            wanted.append(key)
    scores = {}
    words = set(re.findall(r"[a-z]{3,}", (intent or "").lower()))
    for skill in index["skills"]:
        score = 0
        if skill["key"] in wanted:
            score += 10
        haystack = (skill["description"] + " " + " ".join(skill["formats"])).lower()
        overlap = sum(1 for word in words if word in haystack)
        score += min(overlap, 5)
        if research and skill["scripts"]["research"]:
            score += 3
        if score:
            scores[skill["key"]] = score
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return [{"key": key, "score": score,
             "skill": next(s for s in index["skills"] if s["key"] == key)}
            for key, score in ranked]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("index").add_argument("--json", action="store_true")
    find = sub.add_parser("discover")
    find.add_argument("--formats", help="comma-separated output formats")
    find.add_argument("--intent", help="free-text task intent (discovery aid only)")
    find.add_argument("--research", action="store_true")
    find.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    index = build_index()
    if args.command == "index":
        if args.json:
            print(json.dumps(index, indent=2))
        else:
            for skill in index["skills"]:
                print("%-24s %-28s %-7s %5d tok  builders=%s validators=%s"
                      % (skill["name"], skill["folder"], skill["version"],
                         skill["token_estimate"],
                         ",".join(skill["scripts"]["builders"]) or "-",
                         ",".join(skill["scripts"]["validators"]) or "-"))
        return 0
    results = discover(index, formats=(args.formats or "").split(",") if args.formats else None,
                       intent=args.intent, research=args.research)
    if args.json:
        print(json.dumps({"candidates": [{"key": c["key"], "name": c["skill"]["name"],
                                          "score": c["score"]} for c in results]}, indent=2))
    else:
        for candidate in results:
            print("%-24s score=%d  %s" % (candidate["skill"]["name"], candidate["score"],
                                          candidate["skill"]["description"][:80]))
        if not results:
            print("no candidate matched; clarify the requested formats")
    return 0


if __name__ == "__main__":
    sys.exit(main())
