#!/usr/bin/env python3
"""Package installable skill folders into deterministic, skill-only ZIP files.

    python tools/package_skill.py --skill ppt --version v1.2.0
    python tools/package_skill.py --skill pdf --version v1.0.0

Archives are written to releases/skills/ by default; pass -o to choose another path.

Each archive has one top-level directory matching its SKILL.md frontmatter name.
No generated outputs, evaluation workspaces, dependencies, or unrelated project
files are included. The archive is deterministic for a fixed source tree.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import zipfile
import json

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(REPO, "skills.json"), encoding="utf-8") as catalog_file:
    CATALOG = json.load(catalog_file)
SOURCES = {s["key"]: (os.path.join(REPO, s["folder"]), s["name"])
           for s in CATALOG["skills"]}
HELPER_SOURCE, HELPER_NAME = SOURCES["scrape"]
INCLUDE_DIRS = ("scripts", "references", "evals", "tests", "assets")
INCLUDE_FILES = ("SKILL.md",)
OPTIONAL_FILES = ("LICENSE", "requirements.txt", "README.md")
SHARED_SCRIPTS = {"word-generator": (os.path.join(REPO, "ppt_skill", "scripts", "extract_office_assets.py"),
                                     "scripts/extract_office_assets.py")}
EXCLUDE_DIRS = {"__pycache__", "node_modules", ".git", "workspace", "workspaces"}
EXCLUDE_PARTS = {".DS_Store", "Thumbs.db"}


def guess_version():
    """Newest vX.Y.Z tag, or v0.0.0 when no tags are available."""
    import subprocess

    try:
        out = subprocess.run(["git", "tag", "--list", "v*"], cwd=REPO, timeout=10,
                             capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return "v0.0.0"
    versions = []
    for tag in out.split():
        if re.fullmatch(r"v\d+\.\d+\.\d+", tag):
            versions.append((tuple(int(p) for p in tag[1:].split(".")), tag))
    return max(versions)[1] if versions else "v0.0.0"


def collect(source=None, zip_root=None):
    """Return (absolute_path, archive_path) entries allowed in the skill zip."""
    if source is None or zip_root is None:
        source, zip_root = SOURCES["ppt"]
    if not os.path.isdir(source):
        raise SystemExit("no skill folder at %s" % source)
    members = []
    for name in INCLUDE_FILES:
        path = os.path.join(source, name)
        if not os.path.isfile(path):
            raise SystemExit("skill is missing %s - refusing to ship a partial skill" % name)
        members.append((path, "%s/%s" % (zip_root, name)))
    for name in OPTIONAL_FILES:
        path = os.path.join(source, name)
        if os.path.isfile(path):
            members.append((path, "%s/%s" % (zip_root, name)))
    for top in INCLUDE_DIRS:
        base = os.path.join(source, top)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith("."))
            for filename in sorted(filenames):
                if filename.startswith(".") or filename.endswith((".pyc", ".pyo", ".zip", ".pptx", ".docx", ".xlsm", ".xlsx", ".pdf")) or filename in EXCLUDE_PARTS:
                    continue
                path = os.path.join(dirpath, filename)
                rel = os.path.relpath(path, source).replace(os.sep, "/")
                members.append((path, "%s/%s" % (zip_root, rel)))
    shared = SHARED_SCRIPTS.get(zip_root)
    if shared:
        path, rel = shared
        if not os.path.isfile(path):
            raise SystemExit("shared skill helper is missing: %s" % path)
        destination = "%s/%s" % (zip_root, rel)
        if not any(arcname == destination for _, arcname in members):
            members.append((path, destination))
    if os.path.abspath(source) != os.path.abspath(HELPER_SOURCE):
        # Each format ZIP works alone, with a canonical generated helper copy.
        members.extend(collect(HELPER_SOURCE, zip_root + "/shared/" + HELPER_NAME))
    # Word references this shared helper from its portable skill directory; PPT
    # already owns the canonical copy in scripts/.
    paths = [archive_path for _, archive_path in members]
    if len(paths) != len(set(paths)):
        raise SystemExit("duplicate archive path while collecting %s" % zip_root)
    return sorted(members, key=lambda m: m[1])


def build(version, out=None, source=None, zip_root=None):
    if source is None or zip_root is None:
        source, zip_root = SOURCES["ppt"]
    out = out or os.path.join(REPO, "releases", "skills", "%s-%s.zip" % (zip_root, version))
    members = collect(source, zip_root)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, arcname in members:
            info = zipfile.ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(path, "rb") as fh:
                zf.writestr(info, fh.read())
    with zipfile.ZipFile(out) as zf:
        bad = zf.testzip()
        if bad:
            raise SystemExit("archive is corrupt at %s" % bad)
        names = zf.namelist()
        outside = [n for n in names if not n.startswith(zip_root + "/")]
        if outside:
            raise SystemExit("archive contains files outside its skill root: %s" % outside)
    return out, members


def main(argv=None):
    ap = argparse.ArgumentParser(description="Package one installable skill.")
    ap.add_argument("--skill", choices=tuple(SOURCES) + ("all",), default="ppt")
    ap.add_argument("--version", help="version tag, e.g. v1.0.0 (default: newest git tag)")
    ap.add_argument("-o", "--out", help="output zip path")
    args = ap.parse_args(argv)
    version = args.version or guess_version()
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", version):
        ap.error("version must be a vX.Y.Z tag (optional prerelease suffix)")
    if args.skill == "all" and args.out:
        ap.error("--out is only supported for a single skill")
    keys = tuple(SOURCES) if args.skill == "all" else (args.skill,)
    for key in keys:
        source, zip_root = SOURCES[key]
        out, members = build(version, args.out, source, zip_root)
        print("packaged %d files -> %s (%.1f KB)"
              % (len(members), os.path.relpath(out, REPO), os.path.getsize(out) / 1024.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
