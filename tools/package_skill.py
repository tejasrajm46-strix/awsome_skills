#!/usr/bin/env python3
"""Package the skill into the release zip - and nothing else.

    python tools/package_skill.py --version v1.0.0

Produces `pptx-generator-<version>.zip` whose single top-level entry is
`pptx-generator/`, the folder name a skill must have to match its frontmatter.
That means the archive installs with one command:

    unzip pptx-generator-v1.0.0.zip -d ~/.agents/skills/

Only the skill goes in: not the examples, not build outputs, not caches. This
script is the single owner of that rule so the CI release and a local build
cannot drift apart.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(REPO, "ppt_skill")
ZIP_ROOT = "pptx-generator"
# Everything the archive may contain, relative to the skill folder.
INCLUDE_DIRS = ("scripts", "references", "evals", "tests")
INCLUDE_FILES = ("SKILL.md",)
EXCLUDE_DIRS = {"__pycache__"}


def guess_version():
    """Newest vX.Y.Z tag, or v0.0.0 when the repo has no tags yet."""
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


def collect(source=SOURCE, zip_root=ZIP_ROOT):
    """[(absolute_path, path_inside_the_zip)] for the files that ship."""
    if not os.path.isdir(source):
        raise SystemExit("no skill folder at %s" % source)
    members = []
    for name in INCLUDE_FILES:
        path = os.path.join(source, name)
        if not os.path.isfile(path):
            raise SystemExit("skill is missing %s - refusing to ship a partial skill" % name)
        members.append((path, "%s/%s" % (zip_root, name)))
    for top in INCLUDE_DIRS:
        base = os.path.join(source, top)
        if not os.path.isdir(base):
            raise SystemExit("skill is missing the %s/ directory" % top)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for filename in sorted(filenames):
                if filename.endswith(".pyc"):
                    continue
                path = os.path.join(dirpath, filename)
                rel = os.path.relpath(path, source).replace(os.sep, "/")
                members.append((path, "%s/%s" % (zip_root, rel)))
    return sorted(members, key=lambda m: m[1])


def build(version, out=None, source=SOURCE, zip_root=ZIP_ROOT):
    out = out or os.path.join(REPO, "%s-%s.zip" % (zip_root, version))
    members = collect(source, zip_root)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    # Deterministic archive: sorted entries, fixed timestamps, no OS metadata.
    # Two builds of the same tree then produce byte-identical zips.
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
    return out, members


def main(argv=None):
    ap = argparse.ArgumentParser(description="Zip the skill for a release.")
    ap.add_argument("--skill", choices=("ppt", "word"), default="ppt")
    ap.add_argument("--version", help="version tag, e.g. v1.0.0 (default: newest git tag)")
    ap.add_argument("-o", "--out", help="output zip path")
    args = ap.parse_args(argv)
    version = args.version or guess_version()
    source, zip_root = ((SOURCE, ZIP_ROOT) if args.skill == "ppt" else
                        (os.path.join(REPO, "word_skill"), "word-generator"))
    out, members = build(version, args.out, source, zip_root)
    print("packaged %d files -> %s (%.1f KB)"
          % (len(members), os.path.basename(out), os.path.getsize(out) / 1024.0))
    for _, arcname in members:
        print("  %s" % arcname)
    return 0


if __name__ == "__main__":
    sys.exit(main())
