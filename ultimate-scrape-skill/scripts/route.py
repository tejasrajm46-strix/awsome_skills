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


def route(request):
    selected = [{"folder": folder, "name": name, "guide": folder + "/SKILL.md"}
                for folder, name, pattern in RULES if re.search(pattern, request, re.I)]
    gather = bool(re.search(GATHER, request, re.I))
    return {"skills": selected, "shared_helper": "ultimate-scrape-skill" if gather else None,
            "workflow": ["understand", "preserve source"] +
                        (["gather checked sources and selected assets once"] if gather else []) +
                        ["build or edit", "reopen and validate", "render and inspect if available"],
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
        print("Shared helper: " + (result["shared_helper"] or "not needed for local-only work"))
        print(" -> ".join(result["workflow"]))
        print(result["caution"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
