#!/usr/bin/env python3
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_doc import build
from validate_doc import validate
from docx import Document
from PIL import Image


def main():
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
        root = Path(tmp)
        Image.new("RGB", (600, 200), "white").save(root / "figure.png")
        spec = {"title": "Evidence brief", "sections": [{"heading": "Evidence", "blocks": [
            {"text": "A claim with **bold** emphasis."},
            {"type": "image", "path": "figure.png", "alt": "A labelled figure"},
            {"type": "table", "headers": ["A", "B"], "rows": [["one", "two"]]},
            {"type": "references", "items": [{"id": 1, "title": "Source", "url": "https://example.org"}]}]}]}
        path = root / "brief.docx"
        build(spec, path, root)
        report = validate(path)
        assert report["ok"] and not report["warnings"], report
        assert report["images"] == report["tables"] == 1
        doc = Document(path)
        assert any(r.bold for p in doc.paragraphs for r in p.runs)
        assert any(rel.is_external and rel.target_ref == "https://example.org"
                   for rel in doc.part.rels.values())
        doc.inline_shapes[0]._inline.docPr.set("descr", "")
        doc.save(path)
        assert not validate(path)["ok"]
        for block in [{"type": "unknown"}, {"type": "image", "path": "x"},
                      {"type": "table", "headers": ["A", "B"], "rows": [["one"]]}]:
            try:
                build({"title": "Invalid", "sections": [{"heading": "X", "blocks": [block]}]}, path)
            except ValueError:
                pass
            else:
                raise AssertionError("invalid block accepted: " + str(block))
    print("PASS: Word round-trip, styles, references, tables, alt text and invalid-input checks")


if __name__ == "__main__":
    main()
