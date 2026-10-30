#!/usr/bin/env python3
"""End-to-end handoff contract and cross-format reuse, offline.

One brief feeds two deliverables. The test builds a research workspace the way
an agent would - extract, review assets, register sources, bundle - then runs
two builder specs (a deck and a document) against the SAME register and assets,
proving the reuse path end to end:

    extract_parts manifest -> select_assets review -> handoff bundle
        -> source_register check-spec (deck) + check-spec (word)
        -> output_manifest per deliverable, both pointing at one register
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TOOLS = ROOT.parent / "tools"


def run(script, *argv):
    return subprocess.run([sys.executable, str(script), *argv],
                          capture_output=True, text=True)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "research"
        (work / "assets").mkdir(parents=True)

        # 1. Two candidates as the extractor would have downloaded them.
        image_a = work / "assets" / "image-01.png"
        image_b = work / "assets" / "image-02.jpg"
        image_a.write_bytes(b"\x89PNG\r\n\x1a\n" + b"a" * 500)
        image_b.write_bytes(b"\xff\xd8\xff" + b"b" * 500)
        import hashlib
        manifest = {"source": "https://example.com/brief", "parts": ["images"],
                    "downloads": [
                        {"file": str(image_a), "direct_url": "https://example.com/a.png",
                         "source_page": "https://example.com/brief", "bytes": image_a.stat().st_size,
                         "sha256": hashlib.sha256(image_a.read_bytes()).hexdigest()},
                        {"file": str(image_b), "direct_url": "https://example.com/b.jpg",
                         "source_page": "https://example.com/brief", "bytes": image_b.stat().st_size,
                         "sha256": hashlib.sha256(image_b.read_bytes()).hexdigest()}]}
        (work / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        # 2. Nothing is approved yet: validation refuses an unreviewed download.
        result = run(SCRIPTS / "select_assets.py", "validate", str(work / "manifest.json"))
        assert result.returncode == 1 and "has not been reviewed" in result.stdout, result.stdout

        # 3. The agent looks at both, approves one with its license, rejects the other.
        result = run(SCRIPTS / "select_assets.py", "approve", str(work / "manifest.json"),
                     "--asset", str(image_a), "--use", "hero image, slide 2 and figure 1",
                     "--license", "CC BY 4.0", "--attribution", "© 2026 Example Observatory")
        assert result.returncode == 0, result.stdout + result.stderr
        result = run(SCRIPTS / "select_assets.py", "reject", str(work / "manifest.json"),
                     "--asset", str(image_b), "--reason", "watermarked stock preview")
        assert result.returncode == 0, result.stdout + result.stderr
        result = run(SCRIPTS / "select_assets.py", "validate", str(work / "manifest.json"))
        assert result.returncode == 0 and "2/2 candidates reviewed, 1 approved" in result.stdout, result.stdout

        # 4. Register: two sources, claims mapped, one verified with evidence.
        result = run(SCRIPTS / "source_register.py", "new", "--out", str(work / "register.json"))
        assert result.returncode == 0, result.stderr
        result = run(SCRIPTS / "source_register.py", "add", str(work / "register.json"),
                     "--title", "Storage cost survey", "--url", "https://example.org/survey",
                     "--type", "research", "--claims", "C1,C2", "--evidence", "Table 3",
                     "--verification", "verified")
        assert result.returncode == 0, result.stdout + result.stderr
        result = run(SCRIPTS / "source_register.py", "add", str(work / "register.json"),
                     "--title", "Vendor spec sheet", "--url", "https://example.org/spec",
                     "--claims", "C3")
        assert result.returncode == 0, result.stdout + result.stderr

        # 5. The handoff bundle ties register, reviewed assets and limitations together.
        result = run(SCRIPTS / "handoff.py", "bundle", str(work),
                     "--brief", "storage-cost deck plus word brief",
                     "--limitation", "JavaScript-only pricing page not fetched; figures from the survey PDF")
        assert result.returncode == 0, result.stdout + result.stderr
        result = run(SCRIPTS / "handoff.py", "validate", str(work / "handoff.json"), "--json")
        assert result.returncode == 0, result.stdout
        bundle = json.loads(result.stdout)
        assert bundle["ok"] is True, bundle

        # A bundle without limitations, or with an unreviewed asset, is refused.
        broken = json.loads((work / "handoff.json").read_text(encoding="utf-8"))
        broken["limitations"] = []
        (work / "broken.json").write_text(json.dumps(broken), encoding="utf-8")
        result = run(SCRIPTS / "handoff.py", "validate", str(work / "broken.json"))
        assert result.returncode == 1 and "limitations must be a nonempty list" in result.stdout, result.stdout

        # 6. Two deliverable specs from the SAME brief cite the SAME register IDs.
        deck_spec = Path(tmp) / "deck.json"
        deck_spec.write_text(json.dumps({
            "title": "Storage costs", "slides": [{"layout": "title", "title": "Storage costs"}],
            "sources": [{"id": "S1", "title": "Storage cost survey", "url": "https://example.org/survey"}],
            "theme": {}, "images": [str(image_a)],
        }), encoding="utf-8")
        word_spec = Path(tmp) / "doc.json"
        word_spec.write_text(json.dumps({
            "title": "Storage costs brief",
            "sections": [{"heading": "Evidence", "blocks": [
                {"type": "paragraph", "text": "Costs fell [1]."},
                {"type": "references", "items": [
                    {"id": "S1", "title": "Storage cost survey", "url": "https://example.org/survey"}]}]}],
        }), encoding="utf-8")
        for spec, kind in ((deck_spec, "deck"), (word_spec, "word")):
            result = run(SCRIPTS / "source_register.py", "check-spec",
                         str(work / "register.json"), str(spec))
            assert result.returncode == 0 and ("%s spec cites 1 of 2" % kind) in result.stdout, result.stdout
        # A spec that invents its own ID scheme fails against the shared register.
        divergent = Path(tmp) / "divergent.json"
        divergent.write_text(json.dumps({
            "title": "Doc", "sections": [{"heading": "H", "blocks": [
                {"type": "references", "items": [{"id": "1", "title": "t", "url": "https://example.org/x"}]}]}],
        }), encoding="utf-8")
        result = run(SCRIPTS / "source_register.py", "check-spec",
                     str(work / "register.json"), str(divergent))
        assert result.returncode == 1 and "cites 1, which is not in the register" in result.stdout, result.stdout

        # 7. Both output manifests point at the same register file.
        outputs = Path(tmp) / "deliverables"
        outputs.mkdir()
        for name, output in (("deck", "deck.pptx"), ("doc", "brief.docx")):
            (outputs / output).write_bytes(b"PK\x03\x04 placeholder")
            manifest_out = outputs / ("%s-manifest.json" % name)
            result = run(TOOLS / "output_manifest.py", "new", "--task", "brief-%s" % name,
                         "--out", str(manifest_out), "--output", output,
                         "--register", str(work / "register.json"))
            assert result.returncode == 0, result.stdout + result.stderr
            result = run(TOOLS / "output_manifest.py", "validate", str(manifest_out))
            assert result.returncode == 0, result.stdout
            stored = json.loads(manifest_out.read_text(encoding="utf-8"))
            assert Path(stored["sources_register"]) == (work / "register.json"), stored

        # One register, one selection file, one handoff - two deliverables.
        assert (work / "register.json").is_file() and (work / "selection.json").is_file()
        assert (work / "handoff.json").is_file()
    print("PASS: one brief, one register, one reviewed asset set, two deliverables - "
          "handoff validates and both specs cite the shared register")


if __name__ == "__main__":
    main()
