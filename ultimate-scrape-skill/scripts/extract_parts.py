#!/usr/bin/env python3
"""Original, bounded extraction of images, page data and style tokens from HTML.

Saved-page parsing is offline. Live HTML and explicit image downloads use public
HTTP(S) only; redirects to local/private addresses and access challenges fail.
"""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import ipaddress
import json
from pathlib import Path
import re
import socket
import urllib.error
import urllib.parse
import urllib.request

MAX_HTML_BYTES = 5 * 1024 * 1024
BLOCKED_IMAGES = re.compile(r"shutterstock|gettyimages|istockphoto|alamy|watermark|placeholder|spacer", re.I)


def public_url(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Use a public HTTP(S) URL without embedded credentials")
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("Local/private network URLs are not permitted")
    return url


class PublicRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_url(url):
    public_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": "AwesomeSkills/2.0 bounded-research"})
    return urllib.request.build_opener(PublicRedirect()).open(request, timeout=20)


def fetch_html(url):
    with open_url(url) as response:
        content = response.read(MAX_HTML_BYTES + 1)
        if len(content) > MAX_HTML_BYTES:
            raise ValueError("HTML exceeds the 5 MB limit")
        if "html" not in response.headers.get("Content-Type", "").lower():
            raise ValueError("Expected HTML; use a saved page for other inputs")
        return content.decode(response.headers.get_content_charset() or "utf-8", errors="replace")


class PageParser(HTMLParser):
    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base = base
        self.images = []
        self.meta = {}
        self.tables = []
        self.definitions = []
        self.jsonld = []
        self.css = []
        self.title = []
        self._capture = None
        self._chunks = []
        self._table = None
        self._row = None
        self._cell = None
        self._term = ""

    def add_image(self, url):
        url = urllib.parse.urljoin(self.base, url.strip())
        if urllib.parse.urlsplit(url).scheme in {"http", "https"} and not BLOCKED_IMAGES.search(url):
            if url not in self.images:
                self.images.append(url)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("style"):
            self.css.append(a["style"])
        if tag == "meta":
            key = a.get("property") or a.get("name")
            if key:
                self.meta[key.lower()] = a.get("content", "")
                if key.lower() in {"og:image", "twitter:image"}:
                    self.add_image(a.get("content", ""))
        if tag in {"img", "source"}:
            raw = a.get("srcset") or a.get("data-srcset")
            if raw:
                candidates = []
                for item in raw.split(","):
                    bits = item.strip().split()
                    if bits:
                        score = float(re.sub(r"[^0-9.]", "", bits[-1]) or 0) if len(bits) > 1 else 0
                        candidates.append((score, bits[0]))
                if candidates:
                    self.add_image(max(candidates)[1])
            for key in ("data-src", "data-original", "data-lazy-src", "src"):
                if a.get(key):
                    self.add_image(a[key])
        if tag in {"style", "title", "dt", "dd"} or (tag == "script" and a.get("type") == "application/ld+json"):
            self._capture = tag
            self._chunks = []
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, text):
        if self._cell is not None:
            self._cell.append(text)
        if self._capture:
            self._chunks.append(text)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self._cell is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None
        if tag == self._capture:
            value = " ".join("".join(self._chunks).split())
            if tag == "style":
                self.css.append(value)
            elif tag == "title":
                self.title.append(value)
            elif tag == "dt":
                self._term = value
            elif tag == "dd":
                self.definitions.append([self._term, value])
            elif tag == "script":
                try:
                    self.jsonld.append(json.loads(value))
                except json.JSONDecodeError:
                    pass  # Malformed page metadata is not authoritative data.
            self._capture = None


def parse_html(text, base=""):
    parser = PageParser(base)
    parser.feed(text)
    for url in re.findall(r"url\(\s*['\"]?([^)'\"]+)", " ".join(parser.css)):
        parser.add_image(url)
    return parser


def data_part(page, limit):
    fields = {}
    wanted = {"name", "sku", "model", "description", "price", "priceCurrency", "availability", "weight", "brand"}

    def walk(node, depth=0):
        if depth > 6:
            return
        if isinstance(node, dict):
            for key, value in node.items():
                if key in wanted and isinstance(value, (str, float, int)):
                    fields.setdefault(key.lower(), value)
                elif isinstance(value, (dict, list)):
                    walk(value, depth + 1)
        elif isinstance(node, list):
            for item in node[:limit]:
                walk(item, depth + 1)
    for node in page.jsonld[:limit]:
        walk(node)
    for key in ("og:title", "description", "og:description"):
        if page.meta.get(key):
            fields.setdefault(key, page.meta[key])
    specs = [row for table in page.tables for row in table if len(row) == 2]
    return {"source": page.base, "fields": dict(list(fields.items())[:limit]),
            "specs": specs[:limit], "dl": page.definitions[:limit],
            "tables": [[r[:limit] for r in table[:limit]] for table in page.tables[:min(3, limit)]]}


def theme_part(page):
    css = " ".join(page.css)
    palette = []
    for match in re.finditer(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", css):
        color = match[1].upper()
        if len(color) == 3:
            color = "".join(c * 2 for c in color)
        if color not in palette:
            palette.append(color)
    def lightness(color):
        return sum(float(w) * int(color[i:i + 2], 16) for w, i in zip((.2126, .7152, .0722), (0, 2, 4)))
    dark = min(palette, key=lightness) if palette else "111827"
    light = max(palette, key=lightness) if palette else "FFFFFF"
    declared = {}
    for key, raw in re.findall(r"--(background|text|accent|primary)\s*:\s*#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", css):
        declared[key] = raw.upper() if len(raw) == 6 else "".join(c * 2 for c in raw.upper())
    fonts = []
    for raw in re.findall(r"font-family\s*:\s*([^;}]+)", css):
        name = raw.split(",")[0].strip().strip("'\"")
        if name not in fonts:
            fonts.append(name)
    return {"source": page.base, "palette": palette[:12], "fonts": fonts[:6],
            "theme": {"primary": declared.get("primary", dark), "bg": declared.get("background", light),
                      "text": declared.get("text", dark), "accent": declared.get("accent", dark),
                      "font_head": fonts[0] if fonts else "Arial", "font_body": fonts[0] if fonts else "Arial"}}


def raster_extension(head):
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if head.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if head.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        return ".webp"
    raise ValueError("Download is not a recognized raster image")


def download_images(urls, out, budget, source, opener=open_url):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    downloaded = []
    failures = []
    hashes = set()
    for index, url in enumerate(urls, 1):
        if budget <= 0:
            break
        temp = out / ("image-%02d.part" % index)
        try:
            digest = hashlib.sha256()
            total = 0
            head = b""
            with opener(url) as response, temp.open("wb") as stream:
                while True:
                    chunk = response.read(min(65536, budget + 1))
                    if not chunk:
                        break
                    if len(chunk) > budget:
                        budget = 0
                        raise ValueError("Image exceeds remaining total download budget")
                    budget -= len(chunk)
                    total += len(chunk)
                    head = (head + chunk)[:16]
                    digest.update(chunk)
                    stream.write(chunk)
            extension = raster_extension(head)
            sha = digest.hexdigest()
            if sha in hashes:
                continue
            hashes.add(sha)
            path = temp.with_suffix(extension)
            temp.replace(path)
            downloaded.append({"file": str(path), "direct_url": url, "source_page": source,
                               "bytes": total, "sha256": sha})
        except (OSError, ValueError, urllib.error.URLError) as exc:
            failures.append({"url": url, "error": str(exc)})
        finally:
            if temp.exists():
                temp.unlink()
    return downloaded, failures


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("url", nargs="?")
    ap.add_argument("--html-file")
    ap.add_argument("--base-url", default="")
    ap.add_argument("--parts", default="images")
    ap.add_argument("--out", default="parts")
    ap.add_argument("--max-items", type=int, default=20)
    ap.add_argument("--max-mb", type=float, default=25)
    ap.add_argument("--download", action="store_true")
    args = ap.parse_args(argv)
    parts = list(dict.fromkeys(p.strip() for p in args.parts.split(",") if p.strip()))
    if not (args.url or args.html_file) or not parts or set(parts) - {"images", "data", "template"}:
        ap.error("Supply URL or --html-file and valid nonempty parts: images,data,template")
    if args.max_items <= 0 or not 0 < args.max_mb <= 1024:
        ap.error("max-items must be positive; max-mb must be in (0,1024]")
    if args.download and "images" not in parts:
        ap.error("--download requires the images part")
    try:
        source = args.url or args.base_url
        if args.html_file:
            path = Path(args.html_file)
            if path.stat().st_size > MAX_HTML_BYTES:
                raise ValueError("HTML exceeds the 5 MB limit")
            text = path.read_text(encoding="utf-8", errors="replace")
        else:
            text = fetch_html(source)
        if not text.strip():
            raise ValueError("Empty HTML")
        page = parse_html(text, source)
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        files, downloads, failures = [], [], []
        def save(name, data):
            (out / name).write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
            files.append(name)
        if "images" in parts:
            urls = page.images[:args.max_items]
            (out / "urls.txt").write_text("\n".join(urls) + "\n", encoding="utf-8")
            files.append("urls.txt")
            if args.download:
                downloads, failures = download_images(urls, out / "assets", int(args.max_mb * 1048576), source)
        if "data" in parts:
            save("data.json", data_part(page, args.max_items))
        if "template" in parts:
            save("theme.json", theme_part(page))
        result = {"source": source, "parts": parts, "files": files,
                  "downloads": downloads, "download_failures": failures}
        save("manifest.json", result)
        print(json.dumps(result, indent=2))
        if args.download and not downloads:
            raise ValueError("No image downloads succeeded")
        return 0
    except (OSError, ValueError, urllib.error.URLError) as exc:
        ap.exit(1, "Extraction failed: %s\n" % exc)


if __name__ == "__main__":
    raise SystemExit(main())
