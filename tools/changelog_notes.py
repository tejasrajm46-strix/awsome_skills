#!/usr/bin/env python3
"""Print the release notes for one version, read from CHANGELOG.md.

    python tools/changelog_notes.py v3.0.0 > release-notes.md

Publishing a release with notes nobody reviewed is worse than publishing with
generated ones, so this exits non-zero rather than inventing a body when the
changelog has no section for the requested version. The release workflow uses it
so the GitHub release matches the reviewed changelog entry.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def notes_for(version, path=None):
    """Return the changelog body for a version tag, or raise KeyError."""
    path = path or os.path.join(REPO, "CHANGELOG.md")
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    pattern = re.compile(r"^## \[%s\][^\n]*\n(.*?)(?=^## \[|\Z)" % re.escape(version),
                         re.S | re.M)
    match = pattern.search(text)
    if not match:
        raise KeyError(version)
    body = match.group(1).strip()
    if not body:
        raise KeyError(version)
    return body + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Print one version's release notes from CHANGELOG.md.")
    ap.add_argument("version", help="version tag, e.g. v3.0.0")
    args = ap.parse_args(argv)
    try:
        sys.stdout.write(notes_for(args.version))
    except KeyError:
        sys.stderr.write("CHANGELOG.md has no section for %s; refusing to publish un-reviewed notes\n"
                         % args.version)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
