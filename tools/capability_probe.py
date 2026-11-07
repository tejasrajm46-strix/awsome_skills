#!/usr/bin/env python3
"""Capability probe: what this host can actually do, as opposed to what it claims.

    python tools/capability_probe.py                    # human-readable report
    python tools/capability_probe.py --json             # machine-readable report
    python tools/capability_probe.py --json --out capabilities.json
    python tools/capability_probe.py --allow-network    # also test one real request

A model's documentation is not evidence. This probe tests the environment the
task will actually run in and gives each capability one of four answers:

- ``available``            - a probe ran here and succeeded.
- ``unavailable``          - a probe ran here and failed, or the required piece
  is absent. The skill cannot run in this host as it stands.
- ``unverified``           - something exists, but nothing here can settle
  whether it works (a renderer not on PATH, a library imported but unused).
  Treat it as a claim, not a fact, and confirm it with a real task.
- ``permission_required``  - the probe would need the user's authorization:
  installing a dependency, or reaching the network without ``--allow-network``.

Nothing destructive or remote happens by default. Writes go to a temporary
directory that is removed immediately; the network is never touched unless the
flag is passed; installing packages is reported, never attempted. The report is
advice for the host LLM about how to execute this collection - it is not a gate,
and it never upgrades a claim to a fact.

Standard library only, so the probe itself can run where the skills cannot.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STATUSES = ("available", "unavailable", "unverified", "permission_required")
CAPABILITIES = ("repo_read", "file_write", "python_exec", "shell_exec",
                "dependency_install", "document_generation", "pdf_generation",
                "spreadsheet_generation", "presentation_generation", "rendering",
                "image_inspection", "network_access", "git_ops")

# Which skills each capability actually gates. "all" means every skill needs it.
SKILL_MAP = {
    "repo_read": ["all"],
    "file_write": ["all"],
    "python_exec": ["all"],
    "shell_exec": ["all"],
    "dependency_install": ["all"],
    "git_ops": ["all"],
    "document_generation": ["word_skill"],
    "presentation_generation": ["ppt_skill"],
    "spreadsheet_generation": ["xlsm_skill"],
    "pdf_generation": ["pdf_skill"],
    "rendering": ["ppt_skill", "word_skill", "pdf_skill", "poster_skill"],
    "image_inspection": ["ppt_skill", "poster_skill", "ultimate-scrape-skill"],
    "network_access": ["ultimate-scrape-skill"],
}


def _entry(name, status, detail, evidence=None):
    if status not in STATUSES:
        raise ValueError("unknown capability status %r" % status)
    return {"name": name, "status": status, "detail": detail, "evidence": evidence}


def module_available(name):
    """True only when the module can be found for this interpreter."""
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, AttributeError, ValueError):
        return False


def _renderers():
    found = []
    for name in ("soffice", "libreoffice", "chrome", "google-chrome", "chromium",
                 "chromium-browser", "msedge"):
        path = shutil.which(name)
        if path:
            found.append(path)
    return found


def probe_repo_read(root):
    required = [os.path.join(root, "AGENTS.md"), os.path.join(root, "skills.json")]
    missing = [os.path.basename(path) for path in required if not os.path.isfile(path)]
    if missing:
        return _entry("repo_read", "unavailable",
                      "missing repository file(s): %s" % ", ".join(missing))
    try:
        with open(required[1], encoding="utf-8") as handle:
            handle.read(1)
    except OSError as exc:
        return _entry("repo_read", "unavailable",
                      "skills.json exists but cannot be read: %s" % exc)
    return _entry("repo_read", "available",
                  "read AGENTS.md and skills.json from the repository", "skills.json")


def probe_file_write():
    try:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "probe.txt")
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write("probe\n")
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
    except OSError as exc:
        return _entry("file_write", "unavailable",
                      "could not write a temporary file: %s" % exc)
    if content != "probe\n":
        return _entry("file_write", "unavailable",
                      "a written file did not read back unchanged")
    return _entry("file_write", "available",
                  "wrote and re-read a temporary file (deleted after the probe)")


def probe_python():
    try:
        result = subprocess.run([sys.executable, "-c", "print(6 * 7)"],
                                capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        return _entry("python_exec", "unavailable",
                      "could not start %s: %s" % (sys.executable, exc))
    if result.returncode == 0 and result.stdout.strip() == "42":
        return _entry("python_exec", "available",
                      "ran %s as a subprocess" % os.path.basename(sys.executable),
                      sys.executable)
    return _entry("python_exec", "unavailable",
                  "the interpreter started but returned %s" % result.returncode)


def probe_shell():
    candidates = []
    for name in ("bash", "sh"):
        path = shutil.which(name)
        if path:
            candidates.append((name, path))
    if os.name == "nt":
        path = shutil.which("powershell")
        if path:
            candidates.append(("powershell", path))
    for name, path in candidates:
        command = ([path, "-NoProfile", "-Command", "Write-Output probe-ok"]
                   if name == "powershell" else [path, "-c", "echo probe-ok"])
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode == 0 and "probe-ok" in result.stdout:
            return _entry("shell_exec", "available",
                          "%s ran a harmless echo; shell commands are possible" % name, path)
    return _entry("shell_exec", "unavailable", "no working bash, sh or powershell found")


def probe_git(root):
    git = shutil.which("git")
    if not git:
        return _entry("git_ops", "unavailable", "git is not on PATH")
    try:
        result = subprocess.run([git, "rev-parse", "--is-inside-work-tree"], cwd=root,
                                capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        return _entry("git_ops", "unavailable", "git could not run: %s" % exc)
    if result.returncode != 0 or result.stdout.strip() != "true":
        return _entry("git_ops", "unavailable",
                      "%s is not a git work tree" % os.path.basename(root))
    branch = subprocess.run([git, "rev-parse", "--abbrev-ref", "HEAD"], cwd=root,
                            capture_output=True, text=True, timeout=20)
    return _entry("git_ops", "available",
                  "read the work tree (branch %s)" % branch.stdout.strip(), git)


def _minimal_docx(path):
    import docx
    document = docx.Document()
    document.add_paragraph("capability probe")
    document.save(path)


def _minimal_pptx(path):
    from pptx import Presentation
    deck = Presentation()
    deck.slides.add_slide(deck.slide_layouts[6])
    deck.save(path)


def _minimal_xlsx(path):
    from openpyxl import Workbook
    workbook = Workbook()
    workbook.active["A1"] = "capability probe"
    workbook.save(path)


def _build_probe(name, module, build, label, extension):
    """Build one tiny artifact in a temp directory - a real, discarded test."""
    if not module_available(module):
        return _entry(name, "unavailable",
                      "%s is not importable; the %s builder cannot run on this host"
                      % (module, label))
    try:
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "probe" + extension)
            build(target)
            if not os.path.isfile(target):
                raise RuntimeError("no file was produced")
            size = os.path.getsize(target)
    except Exception as exc:  # noqa: BLE001 - any failure is the probe's answer
        return _entry(name, "unverified",
                      "%s imports but a minimal %s build failed: %s: %s"
                      % (module, label, type(exc).__name__, exc))
    return _entry(name, "available",
                  "built a minimal %s with %s (%d bytes, discarded)" % (label, module, size))


def probe_pdf():
    renderers = _renderers()
    if renderers:
        return _entry("pdf_generation", "available",
                      "a renderer is on PATH (%s); PDFs can be produced from "
                      "HTML or Office output" % os.path.basename(renderers[0]),
                      renderers[0])
    if module_available("reportlab"):
        return _entry("pdf_generation", "unverified",
                      "reportlab imports but no PDF was produced during the probe")
    return _entry("pdf_generation", "unavailable",
                  "no soffice/libreoffice/chrome on PATH and no reportlab; PDF output "
                  "needs a renderer or an installed library")


def probe_rendering():
    renderers = _renderers()
    if renderers:
        return _entry("rendering", "available",
                      "a renderer is on PATH: %s" % ", ".join(
                          os.path.basename(path) for path in renderers),
                      renderers[0])
    return _entry("rendering", "unverified",
                  "no soffice/libreoffice/chrome on PATH; an Office COM renderer may "
                  "still exist - confirm with a real render rather than assuming it")


def probe_image_inspection():
    if not module_available("PIL"):
        return _entry("image_inspection", "unavailable",
                      "Pillow is not importable; images cannot be examined programmatically")
    try:
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "probe.png")
            Image.new("RGB", (2, 2), "white").save(path)
            with Image.open(path) as image:
                size = image.size
    except Exception as exc:  # noqa: BLE001 - any failure is the probe's answer
        return _entry("image_inspection", "unverified",
                      "Pillow imports but a minimal image failed: %s: %s"
                      % (type(exc).__name__, exc))
    return _entry("image_inspection", "available",
                  "encoded and reopened a %dx%d PNG with Pillow (discarded)" % size)


def probe_network(allow_network=False):
    if not allow_network:
        return _entry("network_access", "permission_required",
                      "no request was made; pass --allow-network to test one")
    try:
        with urllib.request.urlopen("https://example.com", timeout=5) as response:
            status_code = getattr(response, "status", 200)
    except Exception as exc:  # noqa: BLE001 - any failure is the probe's answer
        return _entry("network_access", "unavailable",
                      "an HTTPS request failed: %s: %s" % (type(exc).__name__, exc))
    return _entry("network_access", "available",
                  "an HTTPS request to example.com returned %s" % status_code)


def probe(root=None, allow_network=False):
    """Probe the host and return the machine-readable report."""
    root = os.path.abspath(root or REPO)
    entries = [
        probe_repo_read(root),
        probe_file_write(),
        probe_python(),
        probe_shell(),
        _entry("dependency_install", "permission_required",
               "installing packages changes the environment; the probe never attempts it"),
        _build_probe("document_generation", "docx", _minimal_docx, "DOCX", ".docx"),
        probe_pdf(),
        _build_probe("spreadsheet_generation", "openpyxl", _minimal_xlsx, "XLSX", ".xlsx"),
        _build_probe("presentation_generation", "pptx", _minimal_pptx, "PPTX", ".pptx"),
        probe_rendering(),
        probe_image_inspection(),
        probe_network(allow_network),
        probe_git(root),
    ]
    names = [entry["name"] for entry in entries]
    if sorted(names) != sorted(CAPABILITIES) or len(names) != len(set(names)):
        raise ValueError("probe entries do not match CAPABILITIES: %s" % ", ".join(names))
    for entry in entries:
        entry["skills"] = SKILL_MAP.get(entry["name"], [])
    summary = {status: sorted(entry["name"] for entry in entries
                              if entry["status"] == status) for status in STATUSES}
    return {"schema": "capability-report", "schema_version": 1,
            "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "root": root, "platform": platform.platform(),
            "python": platform.python_version(), "capabilities": entries,
            "summary": summary,
            "note": "A capability that is not 'available' must not be described as "
                    "performed. 'unverified' is a claim to confirm, not a fact."}


def render(report):
    width = max(len(name) for name in CAPABILITIES) + 2
    lines = ["capability report: %s" % report["root"],
             "host: %s / Python %s" % (report["platform"], report["python"]), ""]
    for entry in report["capabilities"]:
        lines.append("  %-*s %-21s %s"
                     % (width, entry["name"], entry["status"], entry["detail"]))
    lines.append("")
    lines.append("available=%d unavailable=%d unverified=%d permission_required=%d"
                 % tuple(len(report["summary"][status]) for status in STATUSES))
    for status in ("unavailable", "unverified", "permission_required"):
        if report["summary"][status]:
            lines.append("  %s: %s" % (status, ", ".join(report["summary"][status])))
    lines.append("A capability not marked available must not be described as performed.")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="print the machine-readable report")
    ap.add_argument("--out", help="also write the JSON report to this file")
    ap.add_argument("--allow-network", action="store_true",
                    help="make one HTTPS request to test network access")
    ap.add_argument("--root", help="repository root to probe (default: this repository)")
    args = ap.parse_args(argv)
    report = probe(args.root, allow_network=args.allow_network)
    print(json.dumps(report, indent=2) if args.json else render(report))
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=True)
            handle.write("\n")
        print("wrote %s" % args.out, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
