#!/usr/bin/env python3
"""Safely shortlist raster images embedded in a PowerPoint or Word package.

    python scripts/extract_office_assets.py source.pptx --out work/assets --max-assets 12
    python scripts/extract_office_assets.py source.docx --out work/assets --spec work/brief.json

Only images referenced by document parts are considered. Output is bounded,
deduplicated by SHA-256, and accompanied by a JSON manifest with source-part
usage and dimensions. Semantic relevance and image rights still require review.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import posixpath
import struct
import sys
import zipfile
from collections import defaultdict
from pathlib import Path, PurePosixPath
from urllib.parse import unquote
from xml.etree import ElementTree as ET

R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}
MAX_PACKAGE_PARTS = 20_000
MAX_XML_PART_BYTES = 5 * 1024 * 1024
MAX_IMAGE_BYTES = 30 * 1024 * 1024
MAX_SCAN_BYTES = 128 * 1024 * 1024
MAX_CANDIDATES = 500
MAX_SELECTED_BYTES = 48 * 1024 * 1024
MAX_PACKAGE_UNCOMPRESSED_BYTES = 512 * 1024 * 1024


def _safe_package_path(value: str) -> str | None:
    """Normalize an OPC package path and reject targets escaping its package root."""
    value = unquote(value.replace("\\", "/"))
    if value.startswith("/"):
        value = value[1:]
        if not value or ".." in PurePosixPath(value).parts:
            return None
        return value
    normalized = posixpath.normpath(value)
    if normalized in {"", ".", ".."} or normalized.startswith("../"):
        return None
    return normalized


def _source_parts(names: list[str], kind: str) -> list[str]:
    if kind == "pptx":
        return sorted(n for n in names if n.startswith("ppt/slides/slide") and
                       n.endswith(".xml") and "/_rels/" not in n)
    return sorted(n for n in names if n == "word/document.xml" or
                  (n.startswith(("word/header", "word/footer", "word/footnotes", "word/endnotes"))
                   and n.endswith(".xml") and "/_rels/" not in n))


def _rels_path(source_part: str) -> str:
    return posixpath.join(posixpath.dirname(source_part), "_rels",
                          posixpath.basename(source_part) + ".rels")


def _parse_xml(data: bytes):
    """Reject DTD/entity declarations before parsing untrusted package XML."""
    upper_data = data.upper()
    if b"<!DOCTYPE" in upper_data or b"<!ENTITY" in upper_data:
        raise ValueError("DTD/entity declarations are not allowed in Office package XML")
    return ET.fromstring(data)


def _referenced_images(archive: zipfile.ZipFile, names: set[str], source_parts: list[str],
                       media_prefix: str) -> tuple[dict[str, set[str]], list[dict[str, str]]]:
    occurrences: dict[str, set[str]] = defaultdict(set)
    skipped: list[dict[str, str]] = []
    visited_xml_bytes = 0
    for part in source_parts[:MAX_PACKAGE_PARTS]:
        try:
            info = archive.getinfo(part)
            if info.file_size > MAX_XML_PART_BYTES:
                skipped.append({"part": part, "reason": "source XML exceeds size limit"})
                continue
            visited_xml_bytes += info.file_size
            if visited_xml_bytes > MAX_SCAN_BYTES:
                skipped.append({"part": part, "reason": "source XML scan budget reached"})
                break
            root = _parse_xml(archive.read(part))
            rels_name = _rels_path(part)
            if rels_name not in names:
                continue
            rels_info = archive.getinfo(rels_name)
            if rels_info.file_size > MAX_XML_PART_BYTES:
                skipped.append({"part": rels_name, "reason": "relationships XML exceeds size limit"})
                continue
            visited_xml_bytes += rels_info.file_size
            if visited_xml_bytes > MAX_SCAN_BYTES:
                skipped.append({"part": rels_name, "reason": "relationships XML scan budget reached"})
                break
            rels_root = _parse_xml(archive.read(rels_name))
            relationships: dict[str, str] = {}
            for rel in rels_root:
                rel_id = rel.attrib.get("Id", "")
                target = rel.attrib.get("Target", "")
                rel_type = rel.attrib.get("Type", "")
                mode = rel.attrib.get("TargetMode", "")
                if rel_id and rel_type.endswith("/image") and mode.lower() != "external":
                    if target.startswith("/"):
                        resolved = _safe_package_path(target)
                    else:
                        resolved = _safe_package_path(posixpath.join(posixpath.dirname(part), target))
                    if resolved:
                        relationships[rel_id] = resolved
                    else:
                        skipped.append({"part": part, "reason": "unsafe image relationship target"})
            for node in root.iter():
                for attr, rel_id in node.attrib.items():
                    if attr.startswith("{%s}" % R_NS) and attr.rsplit("}", 1)[-1] in {"embed", "link", "id"}:
                        target = relationships.get(rel_id)
                        if target:
                            if target.startswith(media_prefix) and target in names:
                                occurrences[target].add(part)
                            elif target.startswith(media_prefix):
                                skipped.append({"part": part, "member": target,
                                                "reason": "referenced media member is missing"})
        except (KeyError, ET.ParseError, OSError, RuntimeError, ValueError, zipfile.BadZipFile) as exc:
            skipped.append({"part": part, "reason": "could not inspect package part: %s" % exc})
    if len(source_parts) > MAX_PACKAGE_PARTS:
        skipped.append({"reason": "source-part scan capped at %d" % MAX_PACKAGE_PARTS})
    return occurrences, skipped


def image_dimensions(data: bytes) -> tuple[int, int] | None:
    """Read dimensions for common raster formats without image libraries."""
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return struct.unpack(">II", data[16:24])
    if data[:6] in (b"GIF87a", b"GIF89a") and len(data) >= 10:
        return struct.unpack("<HH", data[6:10])
    if data.startswith(b"BM") and len(data) >= 26:
        width, height = struct.unpack_from("<ii", data, 18)
        return abs(width), abs(height)
    if data.startswith(b"\xff\xd8"):
        i = 2
        sof = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
               0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
        while i + 4 <= len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            while i < len(data) and data[i] == 0xFF:
                i += 1
            if i >= len(data):
                break
            marker = data[i]
            i += 1
            if marker in {0xD8, 0xD9, 0x01} or 0xD0 <= marker <= 0xD7:
                continue
            if i + 2 > len(data):
                break
            length = struct.unpack_from(">H", data, i)[0]
            if length < 2 or i + length > len(data):
                break
            if marker in sof and length >= 7:
                height, width = struct.unpack_from(">HH", data, i + 3)
                return width, height
            i += length
    return None


def _rank(width: int, height: int, uses: int) -> float:
    """Technical shortlist score only; it cannot judge semantic relevance."""
    pixels = max(width, 0) * max(height, 0)
    resolution = min(50.0, 10.0 * math.log2(max(1.0, pixels / 150_000.0) + 1.0))
    ratio = width / height if height else 0.0
    aspect = 15.0 if 0.75 <= ratio <= 1.9 else max(0.0, 15.0 - 12.0 * abs(math.log(max(ratio, 0.01) / 1.3)))
    reuse = min(max(uses, 1), 3) * 2.0
    return round(resolution + aspect + reuse, 2)


def _write_contact_sheet(items: list[dict], out_path: Path, force: bool) -> str:
    """Write a dependency-free, local HTML contact sheet for rapid visual triage."""
    sheet_path = out_path / "contact-sheet.html"
    if sheet_path.exists() and not force:
        raise FileExistsError("%s already exists; pass --force to overwrite it" % sheet_path)
    tiles = []
    for item in items:
        media_type = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                      ".gif": "image/gif", ".bmp": "image/bmp"}.get(Path(item["file"]).suffix.lower(), "application/octet-stream")
        details = "%s × %s px · %s KB · score %s" % (
            item["width"], item["height"], round(item["bytes"] / 1024), item["score"])
        members = ", ".join(item["source_members"])
        safe_file = html.escape(item["file"], quote=True)
        tiles.append(
            '<article><a download="%s" href="%s"><img src="%s" alt="%s"></a>'
            '<h2>%s</h2><p>%s</p><small>Embedded in: %s</small></article>' % (
                safe_file, safe_file, safe_file, safe_file, html.escape(item["file"]),
                html.escape(details), html.escape(members)))
    document = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Office image shortlist</title><style>
:root{color-scheme:light dark;font:15px/1.45 system-ui,sans-serif}body{max-width:1400px;margin:2rem auto;padding:0 1rem;background:#f5f7f8;color:#18252a}h1{font-size:1.7rem}header{margin-bottom:1.5rem;color:#42545a}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:1rem}article{padding:1rem;background:white;border:1px solid #d7e0e4;border-radius:12px;box-shadow:0 2px 8px #10203012;min-width:0}img{display:block;width:100%;height:190px;object-fit:contain;background:#edf1f3;border-radius:7px}h2{font-size:1rem;overflow-wrap:anywhere;margin:.8rem 0 .3rem}p{margin:.2rem 0;color:#41545a}small{display:block;margin-top:.5rem;color:#687a80;overflow-wrap:anywhere}@media(prefers-color-scheme:dark){body{background:#101719;color:#eff5f5}article{background:#1b2528;border-color:#344246}img{background:#263236}p,small,header{color:#b4c2c5}}
</style><body><h1>Embedded image shortlist</h1><header>Curated by resolution, aspect ratio and reuse—not semantic relevance. Review each image and its rights before use. Download an image by clicking it.</header><main class="grid">%%TILES%%</main></body></html>""".replace("%%TILES%%", "\n".join(tiles))
    sheet_path.write_text(document, encoding="utf-8")
    return sheet_path.name


def _spec_references(spec_path: str | None) -> list[str]:
    if not spec_path:
        return []
    data = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    found: set[str] = set()

    def walk(value, key=""):
        if isinstance(value, dict):
            for child_key, child in value.items():
                walk(child, child_key)
        elif isinstance(value, list):
            for child in value:
                walk(child, key)
        elif key in {"image", "path"} and isinstance(value, str):
            path = Path(value)
            if not path.is_absolute():
                path = Path(spec_path).resolve().parent / path
            found.add(str(path.resolve()))
    walk(data)
    return sorted(found)


def _cache_hit(manifest_path: Path, source_path: Path, max_assets: int,
               spec_path: str | None) -> dict | None:
    """Reuse a shortlist when source/spec metadata and all cached files still match."""
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        source_stat = source_path.stat()
        cache = manifest.get("cache", {})
        if (cache.get("source") != str(source_path) or cache.get("source_size") != source_stat.st_size
                or cache.get("source_mtime_ns") != source_stat.st_mtime_ns):
            return None
        if cache.get("max_assets") != max_assets:
            return None
        if spec_path:
            Path(spec_path).stat()  # fail closed for a missing spec
        elif cache.get("spec"):
            return None
        sheet_name = manifest.get("contact_sheet", "contact-sheet.html")
        if Path(sheet_name).name != sheet_name or not (manifest_path.parent / sheet_name).is_file():
            return None
        for item in manifest.get("assets", []):
            filename = Path(item["file"])
            if filename.name != str(filename) or filename.is_absolute():
                return None
            file_path = manifest_path.parent / filename
            if not file_path.is_file() or hashlib.sha256(file_path.read_bytes()).hexdigest() != item.get("sha256"):
                return None
        spec_refs = _spec_references(spec_path)
        referenced_paths = set(spec_refs)
        referenced_hashes = set()
        for ref in spec_refs:
            path = Path(ref)
            if path.is_file():
                referenced_hashes.add(hashlib.sha256(path.read_bytes()).hexdigest())
        for item in manifest.get("assets", []):
            item["referenced_in_spec"] = (item["path"] in referenced_paths or
                                          item["sha256"] in referenced_hashes) if spec_path else False
        manifest["spec_audit"] = {
            "spec": str(Path(spec_path).resolve()) if spec_path else None,
            "image_references_found": len(spec_refs) if spec_path else None,
            "unused_candidates": [item["file"] for item in manifest.get("assets", [])
                                  if not item["referenced_in_spec"]] if spec_path else None,
        }
        source_stat = source_path.stat()
        spec_stat = Path(spec_path).stat() if spec_path else None
        cache.update({"source": str(source_path), "source_size": source_stat.st_size,
                      "source_mtime_ns": source_stat.st_mtime_ns,
                      "max_assets": max_assets, "spec": str(Path(spec_path).resolve()) if spec_path else None,
                      "spec_size": spec_stat.st_size if spec_stat else None,
                      "spec_mtime_ns": spec_stat.st_mtime_ns if spec_stat else None})
        manifest["cached"] = True
        tmp_path = manifest_path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(manifest_path)
        return manifest
    except (OSError, ValueError, KeyError, TypeError):
        return None


def extract(source: str, out: str, *, max_assets: int = 12,
            spec_path: str | None = None, force: bool = False) -> dict:
    if not 1 <= max_assets <= 100:
        raise ValueError("--max-assets must be between 1 and 100")
    source_path, out_path = Path(source).resolve(), Path(out).resolve()
    suffix = source_path.suffix.lower()
    if suffix not in {".pptx", ".docx"}:
        raise ValueError("source must be a .pptx or .docx file")
    if not source_path.is_file():
        raise FileNotFoundError("source file does not exist: %s" % source_path)
    out_path.mkdir(parents=True, exist_ok=True)
    manifest_path = out_path / "assets.json"
    if manifest_path.exists() and not force:
        cached = _cache_hit(manifest_path, source_path, max_assets, spec_path)
        if cached is not None:
            return cached
        raise FileExistsError("%s contains a different or stale shortlist; choose another --out or pass --force" % manifest_path)
    if spec_path and not Path(spec_path).is_file():
        raise FileNotFoundError("spec file does not exist: %s" % spec_path)
    if (out_path / "contact-sheet.html").exists() and not force:
        raise FileExistsError("%s already exists; choose another --out or pass --force" % (out_path / "contact-sheet.html"))

    kind = suffix[1:]
    media_prefix = "ppt/media/" if kind == "pptx" else "word/media/"
    with zipfile.ZipFile(source_path) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_PACKAGE_PARTS * 10:
            raise ValueError("Office package has too many members; refusing to scan it")
        if sum(info.file_size for info in infos) > MAX_PACKAGE_UNCOMPRESSED_BYTES:
            raise ValueError("Office package exceeds the uncompressed size safety limit")
        names = {i.filename for i in infos}
        source_parts = _source_parts(sorted(names), kind)
        occurrences, skipped = _referenced_images(archive, names, source_parts, media_prefix)
        unique: dict[str, dict] = {}
        scanned_bytes, scanned_count = 0, 0
        for member in sorted(occurrences):
            info = archive.getinfo(member)
            if Path(member).suffix.lower() not in IMAGE_EXTENSIONS:
                skipped.append({"member": member, "reason": "non-raster or unsupported image format"})
                continue
            if info.file_size > MAX_IMAGE_BYTES:
                skipped.append({"member": member, "reason": "image exceeds per-file size limit"})
                continue
            if scanned_count >= MAX_CANDIDATES or scanned_bytes + info.file_size > MAX_SCAN_BYTES:
                skipped.append({"member": member, "reason": "candidate scan budget reached"})
                continue
            data = archive.read(member)
            scanned_count += 1
            scanned_bytes += len(data)
            dims = image_dimensions(data)
            if not dims or min(dims) <= 0:
                skipped.append({"member": member, "reason": "unrecognized or invalid raster image"})
                continue
            digest = hashlib.sha256(data).hexdigest()
            if digest in unique:
                unique[digest]["members"].append(member)
                unique[digest]["used_by"] = sorted(set(unique[digest]["used_by"]) | occurrences[member])
                unique[digest]["score"] = _rank(dims[0], dims[1], len(unique[digest]["used_by"]))
            else:
                unique[digest] = {
                    "sha256": digest, "members": [member], "used_by": sorted(occurrences[member]),
                    "width": dims[0], "height": dims[1], "bytes": len(data),
                    "score": _rank(dims[0], dims[1], len(occurrences[member])), "_data": data,
                }

    ranked = sorted(unique.values(), key=lambda item: (-item["score"], -item["width"] * item["height"], item["members"][0]))
    selected, not_selected = [], []
    selected_bytes = 0
    for item in ranked:
        if len(selected) < max_assets and item["bytes"] <= MAX_SELECTED_BYTES - selected_bytes:
            selected.append(item)
            selected_bytes += item["bytes"]
        else:
            not_selected.append(item)
    candidates = []
    for item in selected:
        digest = item["sha256"]
        ext = Path(item["members"][0]).suffix.lower()
        filename = "asset-%s%s" % (digest[:12], ext)
        path = out_path / filename
        if path.exists() and path.read_bytes() != item["_data"] and not force:
            raise FileExistsError("%s already exists; pass --force to overwrite it" % path)
        if not path.exists() or force:
            path.write_bytes(item["_data"])
        candidate = {k: v for k, v in item.items() if k != "_data"}
        candidate.update({"file": filename, "path": str(path), "source_members": item["members"],
                          "used_by": item["used_by"]})
        candidates.append(candidate)
    spec_refs = _spec_references(spec_path)
    referenced = set(spec_refs)
    referenced_hashes = set()
    for ref in spec_refs:
        path = Path(ref)
        if path.is_file():
            referenced_hashes.add(hashlib.sha256(path.read_bytes()).hexdigest())
    for item in candidates:
        item["referenced_in_spec"] = (item["path"] in referenced or
                                      item["sha256"] in referenced_hashes) if spec_path else False
    contact_sheet = _write_contact_sheet(candidates, out_path, force)
    source_stat = source_path.stat()
    spec_stat = Path(spec_path).stat() if spec_path else None
    manifest = {
        "source": source_path.name,
        "cached": False,
        "cache": {"source": str(source_path), "source_size": source_stat.st_size,
                  "source_mtime_ns": source_stat.st_mtime_ns,
                  "max_assets": max_assets, "spec": str(Path(spec_path).resolve()) if spec_path else None,
                  "spec_size": spec_stat.st_size if spec_stat else None,
                  "spec_mtime_ns": spec_stat.st_mtime_ns if spec_stat else None},
        "format": kind,
        "limits": {"max_assets": max_assets, "max_file_bytes": MAX_IMAGE_BYTES,
                   "max_scan_bytes": MAX_SCAN_BYTES, "max_candidates": MAX_CANDIDATES,
                   "max_selected_output_bytes": MAX_SELECTED_BYTES,
                   "max_package_uncompressed_bytes": MAX_PACKAGE_UNCOMPRESSED_BYTES},
        "selection_note": "Rank uses resolution, broad aspect-ratio suitability and reuse count only. Review semantic relevance, visual quality, rights and attribution before use.",
        "spec_audit": {"spec": str(Path(spec_path).resolve()) if spec_path else None,
                       "image_references_found": len(spec_refs) if spec_path else None,
                       "unused_candidates": [item["file"] for item in candidates if not item["referenced_in_spec"]] if spec_path else None},
        "assets": candidates,
        "contact_sheet": contact_sheet,
        "not_selected": [{k: v for k, v in item.items() if k != "_data"} for item in not_selected],
        "skipped": skipped,
    }
    temp_path = manifest_path.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(manifest_path)
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="input .pptx or .docx")
    parser.add_argument("--out", required=True, help="new or existing output directory")
    parser.add_argument("--max-assets", type=int, default=12, help="upper bound on extracted unique images (default: 12)")
    parser.add_argument("--spec", help="optional deck/document JSON spec; audit whether shortlisted images are referenced")
    parser.add_argument("--force", action="store_true", help="allow refreshing/overwriting the generated shortlist")
    args = parser.parse_args(argv)
    try:
        report = extract(args.source, args.out, max_assets=args.max_assets, spec_path=args.spec, force=args.force)
    except (OSError, ValueError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    action = "reused" if report.get("cached") else "extracted"
    print("%s %d unique raster candidate(s); skipped %d; manifest: %s"
          % (action, len(report["assets"]), len(report["skipped"]), Path(args.out) / "assets.json"))
    for item in report["assets"]:
        print("  %s  %dx%d  used in %d part(s)  score %.2f" %
              (item["file"], item["width"], item["height"], len(item["used_by"]), item["score"]))
    if args.spec:
        unused = report["spec_audit"]["unused_candidates"]
        print("  spec audit: %d shortlisted image(s) not referenced by the spec" % len(unused))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())