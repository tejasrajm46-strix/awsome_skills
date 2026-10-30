#!/usr/bin/env python3
"""Regression tests for the output manifest: ladder, evidence rule, tamper checks."""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import output_manifest


def run(*argv):
    captured_out, captured_err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(captured_out), contextlib.redirect_stderr(captured_err):
            code = output_manifest.main(list(argv))
    except SystemExit as exc:  # argparse refusal paths
        code = exc.code
    return code, captured_out.getvalue() + captured_err.getvalue()


def ladder(tmp):
    """Build a deck output through the full ladder and watch the state advance."""
    root = Path(tmp) / "ladder"
    (root / "evidence").mkdir(parents=True)
    (root / "evidence" / "structure.json").write_text("{}", encoding="utf-8")
    (root / "deck.pptx").write_bytes(b"PK\x03\x04 deck bytes")
    manifest = str(root / "manifest.json")
    code, output = run("new", "--task", "artifact-001", "--out", manifest,
                       "--input", "brief.json", "--output", "deck.pptx",
                       "--skill-name", "pptx-generator", "--skill-version", "v3.1.0")
    assert code == 0, output
    stored = json.loads(Path(manifest).read_text(encoding="utf-8"))
    assert stored["outputs"][0]["format"] == "pptx", stored
    assert "state" not in stored["outputs"][0], "state is derived, never written by new"

    code, output = run("validate", manifest, "--json")
    assert code == 0, output
    assert json.loads(output)["outputs"][0]["state"] == "generated", output

    run("mark", manifest, "--output", "deck.pptx", "--check", "structure",
        "--status", "passed", "--evidence", "evidence/structure.json")
    code, output = run("validate", manifest, "--json")
    assert code == 0, output
    assert json.loads(output)["outputs"][0]["state"] == "generated", \
        "content check still missing, so it cannot be validated yet"

    run("mark", manifest, "--output", "deck.pptx", "--check", "content",
        "--status", "passed", "--evidence", "evidence/structure.json")
    code, output = run("validate", manifest, "--json")
    assert code == 0 and json.loads(output)["outputs"][0]["state"] == "validated", output

    render_dir = root / "evidence" / "renders"
    render_dir.mkdir()
    run("mark", manifest, "--output", "deck.pptx", "--check", "layout",
        "--status", "passed", "--evidence", "evidence/renders")
    run("mark", manifest, "--output", "deck.pptx", "--check", "render",
        "--status", "passed", "--evidence", "evidence/renders")
    code, output = run("validate", manifest, "--json")
    assert code == 0 and json.loads(output)["outputs"][0]["state"] == "rendered", output

    run("mark", manifest, "--output", "deck.pptx", "--check", "visual_review",
        "--status", "passed", "--evidence", "evidence/renders")
    code, output = run("validate", manifest, "--json")
    assert code == 0 and json.loads(output)["outputs"][0]["state"] == "visually_inspected", output
    return root, manifest


def expect_fail(label, manifest, *fragments):
    code, output = run("validate", manifest, "--json")
    assert code == 1, "%s: expected failure, got:\n%s" % (label, output)
    for fragment in fragments:
        assert fragment in output, "%s: missing %r in:\n%s" % (label, fragment, output)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root, manifest = ladder(tmp)

        # A passed check without evidence is the failure mode this tool exists for.
        copy = str(root / "no-evidence.json")
        data = json.loads(Path(manifest).read_text(encoding="utf-8"))
        data["outputs"][0]["checks"]["structure"] = {"status": "passed"}
        Path(copy).write_text(json.dumps(data), encoding="utf-8")
        expect_fail("passed without evidence", copy, "records no evidence")

        # Evidence that does not exist is as bad as no evidence.
        copy = str(root / "ghost-evidence.json")
        data["outputs"][0]["checks"]["structure"] = {"status": "passed",
                                                     "evidence": "evidence/missing.json"}
        Path(copy).write_text(json.dumps(data), encoding="utf-8")
        expect_fail("missing evidence file", copy, "evidence/missing.json does not exist")

        # A hand-written state is overwritten knowledge: validate refuses it.
        copy = str(root / "hand-state.json")
        data["outputs"][0]["state"] = "visually_inspected"
        data["outputs"][0]["checks"]["visual_review"] = {"status": "not_run"}
        Path(copy).write_text(json.dumps(data), encoding="utf-8")
        expect_fail("hand-written state", copy, "never hand-written")

        # not_run plus evidence is contradictory.
        copy = str(root / "not-run-evidence.json")
        data["outputs"][0]["state"] = "visually_inspected"
        data["outputs"][0]["checks"]["visual_review"] = {"status": "not_run",
                                                         "evidence": "evidence/renders"}
        Path(copy).write_text(json.dumps(data), encoding="utf-8")
        expect_fail("not_run with evidence", copy, "not_run but records evidence")

        # A failed check must say what is wrong.
        copy = str(root / "silent-failure.json")
        data["outputs"][0]["checks"]["visual_review"] = {"status": "failed",
                                                         "evidence": "evidence/renders"}
        data["outputs"][0]["state"] = "needs_repair"
        Path(copy).write_text(json.dumps(data), encoding="utf-8")
        expect_fail("failure without detail", copy, "needs a detail")

        # Unknown check names are refused, not silently accepted.
        copy = str(root / "unknown-check.json")
        data["outputs"][0]["checks"]["vibes"] = {"status": "passed", "evidence": "evidence/renders"}
        del data["outputs"][0]["state"]
        Path(copy).write_text(json.dumps(data), encoding="utf-8")
        expect_fail("unknown check", copy, "unknown check 'vibes'")

        # A vanished output is reported as missing, not as its old state.
        gone = str(root / "gone.json")
        (root / "deck.pptx").unlink()
        Path(gone).write_text(Path(manifest).read_text(encoding="utf-8"), encoding="utf-8")
        expect_fail("missing output", gone, "state")
        code, output = run("validate", gone, "--json")
        states = json.loads(output)["outputs"][0]
        assert states["exists"] is False and states["state"] == "missing", output

        # mark refuses outputs the manifest does not list.
        code, output = run("mark", manifest, "--output", "other.pptx",
                           "--check", "structure", "--status", "passed")
        assert code == 1 and "lists no output" in output, output

        # Format guessing: an unknown extension stays honest as "other".
        other = str(root / "other.json")
        code, output = run("new", "--task", "t2", "--out", other, "--output", "asset.xyz")
        assert code == 0, output
        stored = json.loads(Path(other).read_text(encoding="utf-8"))
        assert stored["outputs"][0]["format"] == "other", stored

    print("PASS: output manifest ladder, evidence rule, derived-state tamper checks and refusal modes")


if __name__ == "__main__":
    main()
