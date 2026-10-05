#!/usr/bin/env python3
"""Regression tests for bounded Office image shortlisting."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path

from PIL import Image

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
import extract_office_assets as extractor

NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _pptx(path: Path, image_a: bytes, image_b: bytes | None = None):
    slide1 = f'''<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="{NS_R}"><p:cSld><p:spTree><p:pic><p:blipFill><a:blip r:embed="rId1"/></p:blipFill></p:pic></p:spTree></p:cSld></p:sld>'''
    slide2 = f'''<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="{NS_R}"><p:cSld><p:spTree><p:pic><p:blipFill><a:blip r:embed="rId1"/></p:blipFill></p:pic></p:spTree></p:cSld></p:sld>'''
    slide3 = f'''<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="{NS_R}"><p:cSld><p:spTree><p:pic><p:blipFill><a:blip r:embed="rId1"/></p:blipFill></p:pic></p:spTree></p:cSld></p:sld>'''
    rels_a = '''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image1.png"/></Relationships>'''
    rels_b = '''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image2.png"/></Relationships>'''
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("ppt/slides/slide1.xml", slide1)
        archive.writestr("ppt/slides/_rels/slide1.xml.rels", rels_a)
        archive.writestr("ppt/slides/slide2.xml", slide2)
        archive.writestr("ppt/slides/_rels/slide2.xml.rels", rels_a)
        archive.writestr("ppt/media/image1.png", image_a)
        if image_b:
            archive.writestr("ppt/slides/slide3.xml", slide3)
            archive.writestr("ppt/slides/_rels/slide3.xml.rels", rels_b)
            archive.writestr("ppt/media/image2.png", image_b)


def _docx(path: Path, image_data: bytes):
    document = f'''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="{NS_R}"><w:body><w:p><w:r><w:drawing><a:blip r:embed="rId1"/></w:drawing></w:r></w:p></w:body></w:document>'''
    rels = '''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.png"/></Relationships>'''
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document)
        archive.writestr("word/_rels/document.xml.rels", rels)
        archive.writestr("word/media/image1.png", image_data)


def _png(path: Path, color: str) -> bytes:
    Image.new("RGB", (800, 450), color).save(path, format="PNG")
    return path.read_bytes()


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        fixture = root / "input.pptx"
        img_path = root / "reference.png"
        image_a = _png(img_path, "#174f68")
        image_b = _png(root / "other.png", "#b56a32")
        _pptx(fixture, image_a, image_b)
        spec = root / "deck.json"
        spec.write_text(json.dumps({"slides": [{"layout": "image", "image": "reference.png"}]}), encoding="utf-8")
        output = root / "shortlist"
        report = extractor.extract(str(fixture), str(output), max_assets=5, spec_path=str(spec))
        assert len(report["assets"]) == 2, report
        by_hash = {item["sha256"]: item for item in report["assets"]}
        selected = by_hash[hashlib.sha256(image_a).hexdigest()]
        assert selected["width"] == 800 and selected["height"] == 450
        assert len(selected["used_by"]) == 2, selected
        assert selected["referenced_in_spec"] is True
        assert Path(report["contact_sheet"]).name == "contact-sheet.html"
        sheet = (output / report["contact_sheet"]).read_text(encoding="utf-8")
        assert "Embedded image shortlist" in sheet and selected["file"] in sheet
        cached = extractor.extract(str(fixture), str(output), max_assets=5, spec_path=str(spec))
        assert cached["cached"] is True
        assert cached["assets"][0]["referenced_in_spec"] or cached["assets"][1]["referenced_in_spec"]
        spec.write_text(json.dumps({"slides": [{"layout": "image", "image": "other.png"}]}), encoding="utf-8")
        refreshed = extractor.extract(str(fixture), str(output), max_assets=5, spec_path=str(spec))
        assert refreshed["cached"] is True
        assert next(item for item in refreshed["assets"] if item["sha256"] == hashlib.sha256(image_b).hexdigest())["referenced_in_spec"]
        assert next(item for item in refreshed["assets"] if item["sha256"] == hashlib.sha256(image_a).hexdigest())["referenced_in_spec"] is False
        word_file = root / "input.docx"
        _docx(word_file, image_a)
        word_report = extractor.extract(str(word_file), str(root / "word-shortlist"), max_assets=2)
        assert len(word_report["assets"]) == 1 and word_report["assets"][0]["used_by"] == ["word/document.xml"]
        try:
            extractor.extract(str(fixture), str(output), max_assets=1, spec_path=str(spec))
        except FileExistsError:
            pass
        else:
            raise AssertionError("stale cache should require --force or another output folder")
        assert extractor.image_dimensions(b"not an image") is None
        assert extractor._safe_package_path("../../outside.png") is None
        assert extractor._safe_package_path("ppt/slides/../../../outside.png") is None
        assert extractor._safe_package_path("ppt/slides/../media/image.png") == "ppt/media/image.png"
    print("PASS: PPTX/DOCX references, bounded dedup shortlist, contact sheet, cache and spec audit")


if __name__ == "__main__":
    main()
