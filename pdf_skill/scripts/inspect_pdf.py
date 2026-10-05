#!/usr/bin/env python3
"""Check basic PDF container markers without parsing or executing PDF content.

Usage: python inspect_pdf.py file.pdf [--json]
This is not a full PDF parser, repair utility, OCR tool, or security scanner.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def inspect(path: Path) -> dict:
    result = {"file": str(path), "bytes": path.stat().st_size, "ok": False,
              "pdf_version": None, "page_markers": 0, "encrypted_marker": False,
              "startxref_present": False, "errors": []}
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            head = handle.read(1024)
            handle.seek(max(0, size - 65536))
            tail = handle.read()
            handle.seek(0)
            carry = b""
            page_pattern = re.compile(rb"/Type\s*/Page\b")
            encrypt_pattern = re.compile(rb"/Encrypt\b")
            page_count = 0
            encrypted = False
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                data = carry + chunk
                page_count += len(page_pattern.findall(data))
                encrypted = encrypted or bool(encrypt_pattern.search(data))
                carry = data[-32:]
        match = re.search(rb"%PDF-(\d\.\d)", head)
        result["pdf_version"] = match.group(1).decode("ascii") if match else None
        result["page_markers"] = page_count
        result["encrypted_marker"] = encrypted
        result["startxref_present"] = bool(re.search(rb"startxref\s+\d+", tail))
        if not result["pdf_version"]:
            result["errors"].append("PDF header not found near file start")
        if not result["page_markers"]:
            result["errors"].append("No /Type /Page markers found; file may be malformed or use an unsupported page-tree encoding")
        if not result["startxref_present"]:
            result["errors"].append("startxref marker not found in final 64 KiB")
        result["ok"] = not result["errors"]
    except OSError as exc:
        result["errors"].append(str(exc))
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.pdf.is_file():
        parser.error("file not found: %s" % args.pdf)
    result = inspect(args.pdf)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("PDF marker inspection (not a full parser)")
        for key, value in result.items():
            print("%s: %s" % (key, value))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
