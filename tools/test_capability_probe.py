#!/usr/bin/env python3
"""Regression tests for the capability probe: statuses, honesty, no side effects."""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import capability_probe


def test_report_shape():
    report = capability_probe.probe()
    assert report["schema"] == "capability-report", report
    assert report["schema_version"] == 1
    names = [entry["name"] for entry in report["capabilities"]]
    assert sorted(names) == sorted(capability_probe.CAPABILITIES), names
    assert len(names) == len(set(names)), "each capability is probed once"
    for entry in report["capabilities"]:
        assert entry["status"] in capability_probe.STATUSES, entry
        assert isinstance(entry["detail"], str) and entry["detail"].strip(), entry
        assert isinstance(entry["skills"], list), entry
        assert set(entry) == {"name", "status", "detail", "evidence", "skills"}, entry
        # A status other than available must never carry a "verified" claim.
        if entry["status"] != "available":
            assert "verified" not in entry["detail"] or "unverified" in entry["detail"], entry
    for status in capability_probe.STATUSES:
        assert status in report["summary"], report["summary"]
    flattened = sum(report["summary"].values(), [])
    assert sorted(flattened) == sorted(capability_probe.CAPABILITIES), flattened
    json.dumps(report)


def test_repo_read_is_real_here():
    by_name = {entry["name"]: entry for entry in capability_probe.probe()["capabilities"]}
    assert by_name["repo_read"]["status"] == "available", by_name["repo_read"]
    assert by_name["repo_read"]["evidence"] == "skills.json"


def test_authorization_boundaries():
    by_name = {entry["name"]: entry for entry in capability_probe.probe()["capabilities"]}
    assert by_name["dependency_install"]["status"] == "permission_required"
    assert by_name["network_access"]["status"] == "permission_required"
    assert "no request" in by_name["network_access"]["detail"]
    # Without the flag no request may be attempted at all.
    def forbidden(*args, **kwargs):
        raise AssertionError("the network must not be touched without --allow-network")
    original = capability_probe.urllib.request.urlopen
    capability_probe.urllib.request.urlopen = forbidden
    try:
        capability_probe.probe()
    finally:
        capability_probe.urllib.request.urlopen = original


def test_missing_library_is_unavailable_not_unverified():
    original = capability_probe.module_available
    capability_probe.module_available = lambda name: False
    try:
        report = capability_probe.probe()
    finally:
        capability_probe.module_available = original
    by_name = {entry["name"]: entry for entry in report["capabilities"]}
    for name in ("document_generation", "spreadsheet_generation",
                 "presentation_generation", "image_inspection"):
        assert by_name[name]["status"] == "unavailable", by_name[name]
        assert "not importable" in by_name[name]["detail"], by_name[name]


def test_file_write_is_confined_and_cleaned_up():
    entry = capability_probe.probe_file_write()
    assert entry["status"] in ("available", "unavailable"), entry
    if entry["status"] == "available":
        assert "temporary" in entry["detail"] and "deleted" in entry["detail"], entry
        # Nothing named like the probe's file is left in the system temp root.
        leftovers = [name for name in os.listdir(tempfile.gettempdir())
                     if name == "probe.txt"]
        assert not leftovers, leftovers


def test_render_and_cli():
    report = capability_probe.probe()
    text = capability_probe.render(report)
    for name in capability_probe.CAPABILITIES:
        assert name in text, name
    for status in capability_probe.STATUSES:
        assert status.replace("_", "_") in text, status
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "report.json")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = capability_probe.main(["--json", "--out", out])
        assert code == 0, buffer.getvalue()
        stored = json.loads(Path(out).read_text(encoding="utf-8"))
        assert stored["schema"] == "capability-report"
        assert len(stored["capabilities"]) == len(capability_probe.CAPABILITIES)
        printed = json.loads(buffer.getvalue())
        assert printed["summary"] == stored["summary"]


def main():
    test_report_shape()
    test_repo_read_is_real_here()
    test_authorization_boundaries()
    test_missing_library_is_unavailable_not_unverified()
    test_file_write_is_confined_and_cleaned_up()
    test_render_and_cli()
    print("PASS: capability probe reports every capability once with an honest status, "
          "never touches the network unasked, and emits matching JSON and text reports")


if __name__ == "__main__":
    main()
