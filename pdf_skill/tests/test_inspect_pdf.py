#!/usr/bin/env python3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from inspect_pdf import inspect


MINIMAL = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >> endobj
startxref
0
%%EOF
"""


def main():
    with tempfile.TemporaryDirectory() as tmp:
        good = Path(tmp) / "one.pdf"
        good.write_bytes(MINIMAL)
        report = inspect(good)
        assert report["ok"] and report["pdf_version"] == "1.4", report
        assert report["page_markers"] == 1 and report["startxref_present"], report
        encrypted = Path(tmp) / "encrypted.pdf"
        encrypted.write_bytes(MINIMAL.replace(b"/Count 1", b"/Count 1 /Encrypt 8 0 R"))
        assert inspect(encrypted)["encrypted_marker"]
        bad = Path(tmp) / "bad.pdf"
        bad.write_bytes(b"no pdf")
        assert not inspect(bad)["ok"]
    print("PASS: PDF header, page marker, encryption marker, xref and invalid file checks")


if __name__ == "__main__":
    main()
