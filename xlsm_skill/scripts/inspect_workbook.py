#!/usr/bin/env python3
"""Inspect XLSX/XLSM package structure without executing workbook content.

Usage: python inspect_workbook.py path.xlsx [--json]
This is an inventory, not a formula evaluator, malware scanner, or Excel validator.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkg": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def inspect(path: Path) -> dict:
    result = {
        "file": str(path), "extension": path.suffix.lower(), "bytes": path.stat().st_size,
        "ok": False, "sheets": [], "formula_count": 0, "formula_errors": [],
        "external_links": [], "vba_present": False, "special_parts": [], "errors": [],
    }
    try:
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            if bad:
                result["errors"].append("Corrupt ZIP member: " + bad)
                return result
            names = set(archive.namelist())
            result["vba_present"] = "xl/vbaProject.bin" in names
            result["special_parts"] = sorted(
                name for name in names
                if name.startswith(("xl/activeX/", "xl/ctrlProps/", "xl/externalLinks/", "customUI/", "customXml/"))
                or name.endswith(("vbaProject.bin", "vbaProjectSignature.bin"))
            )
            if "xl/workbook.xml" not in names:
                result["errors"].append("Missing xl/workbook.xml")
                return result
            root = ET.fromstring(archive.read("xl/workbook.xml"))
            for sheet in root.findall("main:sheets/main:sheet", NS):
                result["sheets"].append({
                    "name": sheet.get("name"), "sheetId": sheet.get("sheetId"),
                    "state": sheet.get("state", "visible"),
                })
            for member in sorted(n for n in names if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)):
                sheet_root = ET.fromstring(archive.read(member))
                for cell in sheet_root.findall(".//main:c", NS):
                    formula = cell.find("main:f", NS)
                    value = cell.find("main:v", NS)
                    if formula is not None:
                        result["formula_count"] += 1
                    if cell.get("t") == "e" and value is not None:
                        result["formula_errors"].append({"part": member, "cell": cell.get("r"), "value": value.text})
            result["external_links"] = sorted(n for n in names if n.startswith("xl/externalLinks/") and n.endswith(".xml"))
            result["ok"] = True
    except (zipfile.BadZipFile, OSError, ET.ParseError) as exc:
        result["errors"].append("Inspection failed: %s" % exc)
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.workbook.is_file():
        parser.error("file not found: %s" % args.workbook)
    report = inspect(args.workbook)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("XLSX/XLSM package inspection (not Excel validation)")
        for key in ("file", "extension", "bytes", "sheets", "formula_count", "formula_errors", "external_links", "vba_present", "special_parts", "errors"):
            print("%s: %s" % (key, report[key]))
        print("package_ok: %s" % report["ok"])
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
