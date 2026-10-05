#!/usr/bin/env python3
"""Offline acceptance tests for the original shared extraction implementation."""
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import extract_parts as extractor
from route import route


def main():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "parts"
        command = [sys.executable, str(ROOT / "scripts/extract_parts.py"), "--html-file",
                   str(ROOT / "tests/fixture-product.html"), "--base-url", "https://example.com/product",
                   "--parts", "images,data,template", "--max-items", "3", "--out", str(out)]
        result = subprocess.run(command, cwd=tmp, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert {p.name for p in out.iterdir()} == {"urls.txt", "data.json", "theme.json", "manifest.json"}
        data = json.loads((out / "data.json").read_text())
        assert data["fields"]["sku"] == "EX-E61-01"
        assert len(data["fields"]) <= 3 and len(data["specs"]) <= 3
        urls = (out / "urls.txt").read_text().splitlines()
        assert len(urls) <= 3 and any("2400.webp" in u for u in urls)
        assert not any("shutterstock" in u for u in urls)
        assert json.loads((out / "theme.json").read_text())["theme"]["accent"] == "B45309"
        assert json.loads((out / "manifest.json").read_text())["downloads"] == []
        bad = subprocess.run(command + ["--max-items", "0"], capture_output=True, text=True)
        assert bad.returncode != 0 and "max-items" in bad.stderr
        assert extractor.theme_part(extractor.parse_html("<p>plain</p>"))["theme"]["text"] == "111827"
        page = extractor.parse_html('<img src="images/a.png">', "https://example.com/product/")
        assert page.images == ["https://example.com/product/images/a.png"]

        first = b"\x89PNG\r\n\x1a\n" + b"a" * 8992
        second = b"\xff\xd8\xff" + b"b" * 8997
        opener = lambda url: BytesIO(first if url.endswith("a") else second)
        downloaded, failures = extractor.download_images(["https://example.com/a", "https://example.com/b"],
                                                         Path(tmp) / "images", 19000, "source", opener)
        assert len(downloaded) == 2 and not failures
        assert sum(d["bytes"] for d in downloaded) == 18000
        assert downloaded[0]["file"].endswith(".png") and downloaded[1]["file"].endswith(".jpg")
        downloaded, failures = extractor.download_images(["https://example.com/a"], Path(tmp) / "capped",
                                                         8500, "source", opener)
        assert not downloaded and failures and not list((Path(tmp) / "capped").iterdir())
        downloaded, failures = extractor.download_images(["a", "a"], Path(tmp) / "dupes", 19000, "source", opener)
        assert len(downloaded) == 1 and not failures
        downloaded, failures = extractor.download_images(["a"], Path(tmp) / "not-image", 100, "source",
                                                         lambda u: BytesIO(b"<html>not an image</html>"))
        assert not downloaded and failures
    for url in ["file:///etc/passwd", "https://user:pass@example.com"]:
        try:
            extractor.public_url(url)
        except ValueError:
            pass
        else:
            raise AssertionError(url)
    with patch.object(extractor.socket, "getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 443))]):
        try:
            extractor.public_url("https://example.com")
        except ValueError:
            pass
        else:
            raise AssertionError("Private address must be rejected")
    for request, folder in [("slides", "ppt_skill"), ("Word", "word_skill"), ("PDF", "pdf_skill"),
                            ("XLSX", "xlsm_skill"), ("XLSM", "xlsm_skill"), ("poster", "poster_skill")]:
        assert folder in {s["folder"] for s in route(request)["skills"]}
    assert route("research photos for slides")["shared_helper"] == "ultimate-scrape-skill"
    print("PASS: original offline parser, bounds, raster types, deduplication, security and five-format routing")


if __name__ == "__main__":
    main()
