#!/usr/bin/env python3
"""Regression tests for deterministic skill-only packaging."""
from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import zipfile
import subprocess
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import package_skill


def main():
    with tempfile.TemporaryDirectory() as tmp:
        for key, (source, root) in package_skill.SOURCES.items():
            assert os.path.isfile(os.path.join(source, "SKILL.md")), key
            first = os.path.join(tmp, key + "-one.zip")
            second = os.path.join(tmp, key + "-two.zip")
            package_skill.build("v9.9.9", first, source, root)
            package_skill.build("v9.9.9", second, source, root)
            a, b = Path(first).read_bytes(), Path(second).read_bytes()
            assert hashlib.sha256(a).digest() == hashlib.sha256(b).digest(), key
            with zipfile.ZipFile(first) as archive:
                names = archive.namelist()
                assert names and all(n.startswith(root + "/") for n in names), key
                assert root + "/SKILL.md" in names, key
                if key in {"ppt", "word"}:
                    assert root + "/scripts/extract_office_assets.py" in names, key
                assert not any("__pycache__" in n or "node_modules" in n or "workspace" in n for n in names), key
                assert archive.testzip() is None, key
                assert not any(n.endswith((".pptx", ".docx", ".zip")) for n in names), key
                assert not any(n.endswith("/transitions.py") for n in names), key
                if key == "ppt":
                    assert root + "/assets/template-sheet.jpg" in names
                    assert root + "/assets/credits.json" in names
                helper = root if key == "scrape" else root + "/shared/ultimate-scrape-skill"
                assert helper + "/SKILL.md" in names, key
                assert helper + "/scripts/extract_parts.py" in names, key
                install = Path(tmp) / (key + "-installed")
                archive.extractall(install)
            # Exercise the interface from outside the repository, as an agent
            # would after installing just this ZIP.
            helper_path = install / helper
            out = Path(tmp) / (key + "-research")
            result = subprocess.run([sys.executable, str(helper_path / "scripts/extract_parts.py"),
                                     "--html-file", str(helper_path / "tests/fixture-product.html"),
                                     "--base-url", "https://example.com/product", "--parts", "data,template",
                                     "--out", str(out)], cwd=tmp, capture_output=True, text=True)
            assert result.returncode == 0, (key, result.stderr)
            assert json.loads((out / "data.json").read_text())["fields"]["sku"] == "EX-E61-01"
            if key in {"ppt", "word", "pdf", "xlsm"}:
                script = {"ppt": "extract_office_assets.py", "word": "extract_office_assets.py",
                          "pdf": "inspect_pdf.py", "xlsm": "inspect_workbook.py"}[key]
                subprocess.run([sys.executable, str(install / root / "scripts" / script), "--help"],
                               cwd=tmp, capture_output=True, text=True, check=True)
            if key == "poster":
                subprocess.run(["node", "--check", str(install / root / "scripts/compose.mjs")], check=True)
            print("PASS", key, len(names), "members")
    print("PASS: deterministic, isolated skill archives")


if __name__ == "__main__":
    main()
