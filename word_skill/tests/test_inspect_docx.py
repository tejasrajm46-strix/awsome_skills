#!/usr/bin/env python3
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from inspect_docx import inspect

XML = '''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body><w:p><w:r><w:t>Hello world</w:t></w:r></w:p><w:tbl/><w:hyperlink r:id="rId1"/></w:body></w:document>'''


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        good = root / "test.docx"
        with zipfile.ZipFile(good, "w") as zf:
            zf.writestr("word/document.xml", XML)
            zf.writestr("word/header1.xml", "<header/>")
            zf.writestr("word/comments.xml", "<comments/>")
        report = inspect(good)
        assert report["ok"] and report["paragraphs"] == 1 and report["tables"] == 1
        assert report["hyperlinks"] == 1 and "Hello world" in report["text_preview"]
        assert "word/comments.xml" in report["special_parts"]
        bad = root / "broken.docx"
        bad.write_bytes(b"invalid")
        assert not inspect(bad)["ok"]
    print("PASS: DOCX package, text/table/link inventory and malformed archive handling")


if __name__ == "__main__":
    main()
