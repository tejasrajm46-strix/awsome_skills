#!/usr/bin/env python3
"""Dependency-free repository acceptance checks; fails on stale links or syntax."""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def main():
    repo_root = ROOT.resolve()
    catalog = json.loads((ROOT / "skills.json").read_text(encoding="utf-8"))
    skills = catalog["skills"]
    assert len(skills) == 6
    assert {s["folder"] for s in skills} == {
        "ppt_skill", "word_skill", "pdf_skill", "xlsm_skill", "poster_skill", "ultimate-scrape-skill"}
    assert len({s["name"] for s in skills}) == 6
    shared = ROOT / "ultimate-scrape-skill/references/shared-scraping.md"
    for spec in skills:
        folder = ROOT / spec["folder"]
        guide = (folder / "SKILL.md").read_text(encoding="utf-8")
        assert guide.startswith("---\n") and "\n---\n" in guide
        assert re.search(r"^name: " + re.escape(spec["name"]) + r"$", guide, re.M), spec
        assert re.search(r"^description: .+", guide, re.M), spec
        if spec["key"] != "scrape":
            assert "references/shared-scraping.md" in guide
            assert (folder / "references/shared-scraping.md").read_bytes() == shared.read_bytes()
        for script in folder.rglob("*.py"):
            compile(script.read_text(encoding="utf-8"), str(script), "exec")
        for script in folder.rglob("*.mjs"):
            subprocess.run(["node", "--check", str(script)], check=True)
        assert not list(folder.rglob("*.zip")), folder
    assert not (ROOT / "xlsx_skill").exists()
    assert not (ROOT / "ppt_skill/scripts/transitions.py").exists()
    assert (ROOT / "word_skill/scripts/extract_office_assets.py").read_bytes() == (
        ROOT / "ppt_skill/scripts/extract_office_assets.py").read_bytes()
    credits = json.loads((ROOT / "ppt_skill/assets/credits.json").read_text(encoding="utf-8"))
    assert credits
    for credit in credits:
        assert credit["source"] and credit["file"], credit
        assert (ROOT / "ppt_skill/assets" / credit["file"]).is_file(), credit
    assert (ROOT / "ppt_skill/assets/template-sheet.jpg").is_file()
    assert (ROOT / "ppt_skill/assets/preview-sheet.jpg").is_file()
    assert not list((ROOT / "ppt_skill/assets").rglob("*.pptx"))

    # Validate all explicit local Markdown links in published text; raw web links
    # and code examples are not interpreted as repository paths.
    documents = [ROOT / "README.md", ROOT / "AGENTS.md", ROOT / "docs/organization-report.md"]
    for spec in skills:
        documents.extend((ROOT / spec["folder"]).rglob("*.md"))
    checked = 0
    for document in documents:
        text = document.read_text(encoding="utf-8")
        for target in re.findall(r"!?\[[^\]]*\]\(([^\s)]+)\)", text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = unquote(target.split("#", 1)[0])
            if not target:
                continue
            resolved = (document.parent / target).resolve()
            assert (repo_root == resolved or repo_root in resolved.parents) and resolved.exists(), (document, target)
            checked += 1
    for script in (ROOT / "tools").glob("*.py"):
        compile(script.read_text(encoding="utf-8"), str(script), "exec")
    print("PASS: six catalog entries, synchronized helpers, PPT references, script syntax and %d local links" % checked)


if __name__ == "__main__":
    main()
