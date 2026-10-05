#!/usr/bin/env python3
"""Inspect basic DOCX package content without executing embedded objects.

Usage: python inspect_docx.py file.docx [--json]
Not a complete OOXML validator or visual page renderer.
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


def inspect(path: Path) -> dict:
    report = {"file": str(path), "bytes": path.stat().st_size, "ok": False,
              "paragraphs": 0, "tables": 0, "hyperlinks": 0, "text_preview": "",
              "special_parts": [], "errors": []}
    try:
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            if bad:
                report["errors"].append("Corrupt ZIP member: " + bad)
                return report
            names = set(archive.namelist())
            if "word/document.xml" not in names:
                report["errors"].append("Missing word/document.xml")
                return report
            root = ET.fromstring(archive.read("word/document.xml"))
            report["paragraphs"] = len(root.findall(".//w:p", NS))
            report["tables"] = len(root.findall(".//w:tbl", NS))
            report["hyperlinks"] = len(root.findall(".//w:hyperlink", NS))
            chunks = [node.text or "" for node in root.findall(".//w:t", NS)]
            report["text_preview"] = " ".join(chunks)[:1000]
            prefixes = ("word/media/", "word/header", "word/footer", "word/footnotes", "word/endnotes", "word/comments", "word/embeddings/", "customXml/")
            report["special_parts"] = sorted(n for n in names if n.startswith(prefixes))
            report["ok"] = True
    except (OSError, zipfile.BadZipFile, ET.ParseError) as exc:
        report["errors"].append("Inspection failed: %s" % exc)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("docx", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.docx.is_file():
        parser.error("file not found: %s" % args.docx)
    result = inspect(args.docx)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for key, value in result.items():
            print("%s: %s" % (key, value))
        print("package_ok: %s" % result["ok"])
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
