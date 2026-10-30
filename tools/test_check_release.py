#!/usr/bin/env python3
"""Regression tests for the release-consistency checker, on hermetic fixtures."""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import check_release
import package_skill

NAME = "alpha-skill"
VERSION = "v3.1.0"


def write(root, *parts):
    """Write fixture text with LF endings so deterministic packaging is stable."""
    path = root.joinpath(*parts)
    return lambda text: path.write_text(text, encoding="utf-8", newline="\n")


def make_fixture(root, version=VERSION):
    """A minimal but structurally complete one-skill repository."""
    root = Path(root)
    (root / "alpha_skill" / "evals").mkdir(parents=True)
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / "releases" / "skills").mkdir(parents=True)
    write(root, "skills.json")(json.dumps({
        "schema_version": 1, "version": version,
        "skills": [{"key": "alpha", "folder": "alpha_skill", "name": NAME,
                    "formats": ["txt"], "shared_helper": "ultimate-scrape-skill"}]}))
    write(root, "alpha_skill", "SKILL.md")(
        "---\nname: %s\ndescription: Fixture skill.\nversion: %s\n---\n\n# Alpha\n" % (NAME, version))
    write(root, "alpha_skill", "evals", "evals.json")(
        json.dumps({"skill_name": NAME, "skill_version": version, "evals": []}))
    write(root, "CHANGELOG.md")("# Changelog\n\n## [%s]\n\nFixture release.\n" % version)
    write(root, "README.md")("Download: [alpha](releases/skills/%s-%s.zip)\n" % (NAME, version))
    write(root, ".github", "workflows", "release.yml")("on:\n  push:\n    tags:\n      - 'v*'\n")


def commit_package(root, version=VERSION):
    """Build the fixture package the same way check_release rebuilds it."""
    out = str(Path(root) / "releases" / "skills" / ("%s-%s.zip" % (NAME, version)))
    package_skill.build(version, out, str(Path(root) / "alpha_skill"), NAME)
    return out


def run(root, *argv):
    captured_out, captured_err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(captured_out), contextlib.redirect_stderr(captured_err):
            code = check_release.main(list(argv), root=str(root))
    except SystemExit as exc:  # argparse refusal paths
        code = exc.code
    return code, captured_out.getvalue() + captured_err.getvalue()


def expect_fail(label, root, *fragments, argv=()):
    code, output = run(root, *argv)
    assert code == 1, "%s: expected failure, got PASS:\n%s" % (label, output)
    for fragment in fragments:
        assert fragment in output, "%s: missing %r in:\n%s" % (label, fragment, output)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "consistent"
        make_fixture(root)
        commit_package(root)
        code, output = run(root)
        assert code == 0, output
        assert "byte-matched" in output, output

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "bad-evals"
        make_fixture(root)
        commit_package(root)
        path = root / "alpha_skill" / "evals" / "evals.json"
        path.write_text(path.read_text(encoding="utf-8").replace(VERSION, "v3.0.0"),
                        encoding="utf-8", newline="")
        expect_fail("stale eval manifest", root, "evals/evals.json skill_version is v3.0.0")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "bad-frontmatter"
        make_fixture(root)
        commit_package(root)
        path = root / "alpha_skill" / "SKILL.md"
        path.write_text(path.read_text(encoding="utf-8").replace(VERSION, "v2.0.0"),
                        encoding="utf-8", newline="")
        expect_fail("stale frontmatter", root, "frontmatter version is v2.0.0")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "no-changelog"
        make_fixture(root)
        commit_package(root)
        path = root / "CHANGELOG.md"
        path.write_text("# Changelog\n\n## [v2.0.0]\n\nOld entry.\n", encoding="utf-8", newline="")
        expect_fail("missing changelog section", root, "no nonempty section for %s" % VERSION)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "stale-package"
        make_fixture(root)
        commit_package(root)
        (root / "releases" / "skills" / ("%s-v3.0.0.zip" % NAME)).write_bytes(b"old package")
        expect_fail("stale package", root, "stale package releases/skills/%s-v3.0.0.zip" % NAME)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "missing-package"
        make_fixture(root)
        expect_fail("missing package", root, "missing package releases/skills/")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "drifted-package"
        make_fixture(root)
        commit_package(root)
        path = root / "releases" / "skills" / ("%s-%s.zip" % (NAME, VERSION))
        path.write_bytes(path.read_bytes()[:-1] + b"x")
        expect_fail("package drift", root, "does not match a fresh build")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "hardcoded-workflow"
        make_fixture(root)
        commit_package(root)
        path = root / ".github" / "workflows" / "release.yml"
        path.write_text("run: python tools/package_skill.py --skill all --version %s\n" % VERSION,
                        encoding="utf-8", newline="")
        expect_fail("hardcoded workflow version", root, "hardcodes %s" % VERSION)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "stale-readme"
        make_fixture(root)
        commit_package(root)
        path = root / "README.md"
        path.write_text("Download: [alpha](releases/skills/%s-v3.0.0.zip)\n" % NAME,
                        encoding="utf-8", newline="")
        expect_fail("stale README link", root,
                    "links %s-v3.0.0.zip, which is not a %s package" % (NAME, VERSION),
                    "does not exist")

    # --skip-rebuild still catches metadata drift without packaging anything.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "skip-rebuild"
        make_fixture(root)
        commit_package(root)
        code, output = run(root, "--skip-rebuild")
        assert code == 0, output
        assert "byte-matched" not in output, output

    # A package whose inner SKILL.md disagrees with the catalog is caught even
    # when the byte comparison would be skipped.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "stale-inner-version"
        make_fixture(root)
        stale = root / "releases" / "skills" / ("%s-%s.zip" % (NAME, VERSION))
        with zipfile.ZipFile(stale, "w") as archive:
            archive.writestr("%s/SKILL.md" % NAME,
                             "---\nname: %s\ndescription: Fixture.\nversion: v3.0.0\n---\n" % NAME)
        expect_fail("stale inner version", root,
                    "packages SKILL.md version v3.0.0, catalog says %s" % VERSION,
                    argv=("--skip-rebuild",))

    print("PASS: release checker catches stale evals, frontmatter, changelog, packages, "
          "README links, workflow literals and package manifests, and passes a consistent fixture")


if __name__ == "__main__":
    main()
