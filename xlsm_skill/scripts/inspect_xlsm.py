#!/usr/bin/env python3
"""Inventory an XLSM ZIP package without executing its macros.

Usage: python inspect_xlsm.py workbook.xlsm [--json]
This is not a VBA malware scanner or Excel functional test.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
SPECIAL_PREFIXES = ("xl/activeX/", "xl/ctrlProps/", "xl/ctrls/", "xl/externalLinks/", "xl/queryTables/", "customUI/", "customXml/", "xl/embeddings/")
SPECIAL_NAMES = {"xl/connections.xml"}


def inspect(path: Path) -> dict:
    report = {"file": str(path), "bytes": path.stat().st_size, "ok": False,
              "is_xlsm": path.suffix.lower() == ".xlsm", "vba_present": False,
              "vba_sha256": None, "vba_signature_present": False, "special_parts": [],
              "sheets": [], "formula_count": 0, "formula_error_cells": [], "errors": []}
    try:
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            if bad:
                report["errors"].append("Corrupt ZIP member: " + bad)
                return report
            names = set(archive.namelist())
            report["vba_present"] = "xl/vbaProject.bin" in names
            report["vba_signature_present"] = "xl/vbaProjectSignature.bin" in names
            report["special_parts"] = sorted(n for n in names if n.startswith(SPECIAL_PREFIXES) or n in SPECIAL_NAMES or "Signature" in n and "vba" in n.lower())
            if report["vba_present"]:
                report["vba_sha256"] = hashlib.sha256(archive.read("xl/vbaProject.bin")).hexdigest()
            if "xl/workbook.xml" not in names:
                report["errors"].append("Missing xl/workbook.xml")
                return report
            workbook = ET.fromstring(archive.read("xl/workbook.xml"))
            report["sheets"] = [{"name": s.get("name"), "sheetId": s.get("sheetId"), "state": s.get("state", "visible")} for s in workbook.findall("m:sheets/m:sheet", NS)]
            for part in sorted(n for n in names if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)):
                root = ET.fromstring(archive.read(part))
                for cell in root.findall(".//m:c", NS):
                    if cell.find("m:f", NS) is not None:
                        report["formula_count"] += 1
                    value = cell.find("m:v", NS)
                    if cell.get("t") == "e" and value is not None:
                        report["formula_error_cells"].append({"part": part, "cell": cell.get("r"), "value": value.text})
            report["ok"] = True
    except (OSError, zipfile.BadZipFile, ET.ParseError) as exc:
        report["errors"].append("Inspection failed: %s" % exc)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xlsm", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.xlsm.is_file():
        parser.error("file not found: %s" % args.xlsm)
    report = inspect(args.xlsm)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for key, value in report.items():
            print("%s: %s" % (key, value))
        print("package_ok: %s" % report["ok"])
    return 0 if report["ok"] and report["is_xlsm"] else 1


if __name__ == "__main__":
    sys.exit(main())
