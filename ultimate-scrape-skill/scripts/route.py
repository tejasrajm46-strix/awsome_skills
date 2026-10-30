#!/usr/bin/env python3
"""Offline keyword-level checklist for this repository's five deliverable skills."""
from __future__ import annotations

import argparse
import json
import re

RULES = (
    ("ppt_skill", "pptx-generator", r"\b(pptx?|powerpoint|slides?|deck|presentation)\b"),
    ("word_skill", "word-generator", r"\b(docx?|dotx|word|document|report|brief|letter)\b"),
    ("pdf_skill", "pdf-processor", r"\b(pdf|ocr|redact|redaction)\b"),
    ("xlsm_skill", "xlsm-processor", r"\b(xlsx|xlsm|xltx|xltm|excel|spreadsheet|workbook|csv|tsv)\b"),
    ("poster_skill", "smart-poster-designer", r"\b(poster|flyer|infographic|one-sheet)\b"),
)
GATHER = r"\b(research|scrape|extract|website|web|sources?|facts?|photos?|images?|data|style)\b|https?://"
EDIT = r"\b(edit|edits|editing|update|updating|modify|modifying|restyle|rebrand|revise|revising|rework|reworking|extend|extending|append|appending|reorder|rotate|redact|clean|cleaning)\b"
# Input files named by extension, mapped to the skill that owns the format.
INPUTS = (
    (r"\.pptx\b", "ppt_skill", "pptx-generator"),
    (r"\.(docx|dotx)\b", "word_skill", "word-generator"),
    (r"\.pdf\b", "pdf_skill", "pdf-processor"),
    (r"\.(xlsx|xlsm|xltx|xltm|csv|tsv)\b", "xlsm_skill", "xlsm-processor"),
    (r"\.(png|jpe?g)\b", "poster_skill", "smart-poster-designer"),
)


def route(request):
    selected = [{"folder": folder, "name": name, "guide": folder + "/SKILL.md"}
                for folder, name, pattern in RULES if re.search(pattern, request, re.I)]
    gather = bool(re.search(GATHER, request, re.I))
    editing = bool(re.search(EDIT, request, re.I))
    inputs = []
    for pattern, folder, name in INPUTS:
        for match in re.finditer(r"[A-Za-z0-9._-]+" + pattern, request, re.I):
            entry = {"file": match.group(0), "folder": folder, "name": name}
            if entry not in inputs:
                inputs.append(entry)
            if all(skill["folder"] != folder for skill in selected):
                selected.append({"folder": folder, "name": name, "guide": folder + "/SKILL.md"})
    mode = "edit_existing" if editing or inputs else "create_new"
    workflow = ["understand", "preserve source"]
    if mode == "edit_existing":
        workflow.append("inspect the existing file before choosing an editor")
    if gather:
        workflow.append("gather checked sources and selected assets once")
    workflow += ["build or edit", "reopen and validate", "render and inspect if available"]
    return {"skills": selected, "mode": mode, "inputs": inputs,
            "shared_helper": "ultimate-scrape-skill" if gather else None,
            "workflow": workflow,
            "needs_format_clarification": not selected,
            "caution": "Keyword checklist only; resolve overlap from the user's intended output."}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("request")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    result = route(args.request)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Skills: " + (", ".join(s["name"] for s in result["skills"]) or "clarify output format"))
        print("Mode: " + result["mode"] + (" (existing file: %s)"
              % ", ".join(i["file"] for i in result["inputs"]) if result["inputs"] else ""))
        print("Shared helper: " + (result["shared_helper"] or "not needed for local-only work"))
        print(" -> ".join(result["workflow"]))
        print(result["caution"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
