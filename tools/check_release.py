#!/usr/bin/env python3
"""Deterministic release-consistency checks; reports drift, never fixes it.

    python tools/check_release.py
    python tools/check_release.py --skip-rebuild

One catalog version, one set of packages. This tool compares every place a
release version lives -- `skills.json`, each `SKILL.md` frontmatter, each
`evals/evals.json`, the README download links, the CHANGELOG section, the
committed archives in `releases/skills/` and the release workflow -- and fails
with the exact file and location when they disagree.

It is a report, not a repair tool: stale or missing packages are listed for an
explicit release update, never overwritten or deleted here. The SkillOpt gate
owns the SKILL.md content contract; this tool owns the release metadata around
it, so the two checks stay independently runnable.

`--skip-rebuild` checks metadata and archive names only. By default each
committed archive is also byte-compared against a fresh deterministic rebuild
of the current tree, which is what catches a package that no longer matches
the sources it claims to ship.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_RE = re.compile(r"\bv\d+\.\d+\.\d+\b")
FRONTMATTER_VERSION = re.compile(r"^version: (\S+)$", re.M)


def catalog(root):
    with open(os.path.join(root, "skills.json"), encoding="utf-8") as handle:
        data = json.load(handle)
    version = data["version"]
    if not VERSION_RE.fullmatch(version):
        raise ValueError("skills.json version %r is not a vX.Y.Z tag" % version)
    return data, version


def read(root, *parts):
    with open(os.path.join(root, *parts), encoding="utf-8") as handle:
        return handle.read()


def check_versions(root, version, problems):
    """Frontmatter, eval manifests and CHANGELOG must carry the catalog version."""
    for spec in json.loads(read(root, "skills.json"))["skills"]:
        folder = spec["folder"]
        guide = read(root, folder, "SKILL.md")
        match = FRONTMATTER_VERSION.search(guide)
        if not match or match.group(1) != version:
            problems.append("%s/SKILL.md frontmatter version is %s, catalog says %s"
                            % (folder, match.group(1) if match else "missing", version))
        evals = json.loads(read(root, folder, "evals", "evals.json"))
        if evals.get("skill_version") != version:
            problems.append("%s/evals/evals.json skill_version is %s, catalog says %s"
                            % (folder, evals.get("skill_version"), version))
    sys.path.insert(0, os.path.join(root, "tools"))
    try:
        import changelog_notes
        changelog_notes.REPO = root
        changelog_notes.notes_for(version)
    except KeyError:
        problems.append("CHANGELOG.md has no nonempty section for %s" % version)
    finally:
        sys.path.pop(0)


def check_readme_links(root, version, problems):
    """README package links must name the current version and exist on disk."""
    text = read(root, "README.md")
    links = re.findall(r"releases/skills/([A-Za-z0-9._-]+\.zip)", text)
    if not links:
        problems.append("README.md references no package under releases/skills/")
    for name in sorted(set(links)):
        if not name.endswith("-%s.zip" % version):
            problems.append("README.md links %s, which is not a %s package" % (name, version))
        if not os.path.isfile(os.path.join(root, "releases", "skills", name)):
            problems.append("README.md links releases/skills/%s, which does not exist" % name)
    stale = sorted({m.group(0) for m in VERSION_RE.finditer(text)
                    if m.group(0) != version and "-%s.zip" % m.group(0) in text})
    if stale:
        problems.append("README.md still links stale package versions: %s" % ", ".join(stale))


def check_workflow(root, version, problems):
    """The release workflow must derive its version, not hardcode one."""
    workflow = read(root, ".github", "workflows", "release.yml")
    for match in VERSION_RE.finditer(workflow):
        problems.append(".github/workflows/release.yml hardcodes %s; derive the version "
                        "from skills.json instead" % match.group(0))


def expected_packages(root, version):
    catalog_data, _ = catalog(root)
    return ["%s-%s.zip" % (spec["name"], version) for spec in catalog_data["skills"]]


def check_package_manifests(root, version, problems):
    """Each committed package's own SKILL.md must carry the catalog version."""
    directory = os.path.join(root, "releases", "skills")
    catalog_data, _ = catalog(root)
    for spec in catalog_data["skills"]:
        name = "%s-%s.zip" % (spec["name"], version)
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            continue
        with zipfile.ZipFile(path) as archive:
            guide = archive.read("%s/SKILL.md" % spec["name"]).decode("utf-8").replace("\r\n", "\n")
        match = FRONTMATTER_VERSION.search(guide)
        if not match or match.group(1) != version:
            problems.append("%s packages SKILL.md version %s, catalog says %s"
                            % (name, match.group(1) if match else "missing", version))


def check_archives(root, version, problems, rebuild=True):
    """Committed archives: right names, nothing stale, contents match the tree."""
    directory = os.path.join(root, "releases", "skills")
    if not os.path.isdir(directory):
        problems.append("releases/skills/ does not exist; expected %d packages"
                        % len(expected_packages(root, version)))
        return
    committed = sorted(name for name in os.listdir(directory) if name.endswith(".zip"))
    expected = sorted(expected_packages(root, version))
    for name in committed:
        if name not in expected:
            if VERSION_RE.search(name):
                problems.append("stale package releases/skills/%s (catalog version is %s); "
                                "remove it in an explicit release update" % (name, version))
            else:
                problems.append("unexpected file releases/skills/%s" % name)
    for name in expected:
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            problems.append("missing package releases/skills/%s; build it with "
                            "tools/package_skill.py before tagging" % name)
    if problems or not rebuild:
        return
    sys.path.insert(0, os.path.join(root, "tools"))
    try:
        import package_skill
    finally:
        sys.path.pop(0)
    with tempfile.TemporaryDirectory() as tmp:
        for spec in json.loads(read(root, "skills.json"))["skills"]:
            name = "%s-%s.zip" % (spec["name"], version)
            path = os.path.join(directory, name)
            if not os.path.isfile(path):
                continue
            fresh = os.path.join(tmp, name)
            source = os.path.join(root, spec["folder"])
            package_skill.build(version, fresh, source, spec["name"])
            with open(path, "rb") as committed_file, open(fresh, "rb") as rebuilt:
                if committed_file.read() != rebuilt.read():
                    problems.append("releases/skills/%s does not match a fresh build of the "
                                    "current tree; rebuild the packages before tagging" % name)


def main(argv=None, root=None):
    ap = argparse.ArgumentParser(description="Check release-metadata consistency; reports, never repairs.")
    ap.add_argument("--skip-rebuild", action="store_true",
                    help="skip byte-comparing committed archives against fresh rebuilds")
    args = ap.parse_args(argv)
    root = root or REPO
    problems = []
    try:
        _, version = catalog(root)
    except (OSError, ValueError, KeyError) as exc:
        print("FAIL: skills.json: %s" % exc)
        return 1
    for check in (check_versions, check_readme_links, check_workflow, check_package_manifests):
        check(root, version, problems)
    check_archives(root, version, problems, rebuild=not args.skip_rebuild)
    if problems:
        for problem in problems:
            print("FAIL: %s" % problem)
        print("Release metadata is inconsistent with %s; fix the files above, "
              "do not publish until this passes." % version)
        return 1
    print("PASS: release metadata consistent with %s across skills.json, %d SKILL.md "
          "frontmatters, %d eval manifests, README links, CHANGELOG.md, release.yml "
          "and %d committed packages%s"
          % (version, len(json.loads(read(root, "skills.json"))["skills"]),
             len(json.loads(read(root, "skills.json"))["skills"]),
             len(expected_packages(root, version)),
             "" if args.skip_rebuild else " (byte-matched against fresh builds)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
