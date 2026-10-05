#!/usr/bin/env python3
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from inspect_xlsm import inspect

WORKBOOK = '''<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheets><sheet name="Data" sheetId="1"/></sheets></workbook>'''
SHEET = '''<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row><c r="A1"><f>SUM(1,2)</f><v>3</v></c><c r="A2" t="e"><v>#REF!</v></c></row></sheetData></worksheet>'''


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        path = root / "source.xlsm"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("xl/workbook.xml", WORKBOOK)
            archive.writestr("xl/worksheets/sheet1.xml", SHEET)
            archive.writestr("xl/vbaProject.bin", b"fixture only")
            archive.writestr("xl/vbaProjectSignature.bin", b"signature fixture")
            archive.writestr("xl/activeX/activeX1.bin", b"control fixture")
        report = inspect(path)
        assert report["ok"] and report["is_xlsm"]
        assert report["vba_present"] and report["vba_signature_present"]
        assert len(report["vba_sha256"]) == 64
        assert report["formula_count"] == 1
        assert report["formula_error_cells"][0]["value"] == "#REF!"
        assert "xl/activeX/activeX1.bin" in report["special_parts"]
        bad = root / "broken.xlsm"
        bad.write_bytes(b"not a package")
        assert not inspect(bad)["ok"]
    print("PASS: XLSM VBA/signature/control inventory and formula error census")


if __name__ == "__main__":
    main()
