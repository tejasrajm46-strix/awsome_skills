#!/usr/bin/env python3
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from inspect_workbook import inspect

WORKBOOK = '''<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<sheets><sheet name="Inputs" sheetId="1"/><sheet name="Hidden" sheetId="2" state="hidden"/></sheets>
</workbook>'''
SHEET = '''<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<sheetData><row r="1"><c r="A1"><f>1+1</f><v>2</v></c><c r="A2" t="e"><v>#DIV/0!</v></c></row></sheetData>
</worksheet>'''


def make_book(path, *, macro=False):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("xl/workbook.xml", WORKBOOK)
        zf.writestr("xl/worksheets/sheet1.xml", SHEET)
        if macro:
            zf.writestr("xl/vbaProject.bin", b"test fixture, not executable")
        zf.writestr("xl/externalLinks/externalLink1.xml", "<externalLink/>")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        book = root / "sample.xlsm"
        make_book(book, macro=True)
        report = inspect(book)
        assert report["ok"], report
        assert report["vba_present"]
        assert report["formula_count"] == 1
        assert report["formula_errors"] == [{"part": "xl/worksheets/sheet1.xml", "cell": "A2", "value": "#DIV/0!"}]
        assert report["external_links"] == ["xl/externalLinks/externalLink1.xml"]
        assert report["sheets"][1]["state"] == "hidden"
        corrupt = root / "broken.xlsx"
        corrupt.write_bytes(b"not a zip")
        assert not inspect(corrupt)["ok"]
    print("PASS: XLSX/XLSM package inventory, formula/error census, links, VBA marker, corrupt-package handling")


if __name__ == "__main__":
    main()
