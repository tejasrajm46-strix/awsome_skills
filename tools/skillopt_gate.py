#!/usr/bin/env python3
"""Validation gate for the published skill documents.

Adapts the optimisation loop of Microsoft's SkillOpt
(https://github.com/microsoft/SkillOpt) to this collection. SkillOpt treats a
skill document as the *trainable state* of a frozen agent: an optimiser proposes
bounded add/delete/replace edits, and a candidate document replaces the current
one only when it strictly improves a score measured against a held-out split.
Two machine-managed regions -- a slow update and an appendix -- are protected
from ordinary edits.

This module implements the parts that are decidable offline, with no model call
and no dependency beyond the standard library:

    check     validate the skill-document contract for every catalog skill
    optimize  apply a bounded edit patch, accept it only on strict improvement
    report    write report.md / report.json, including rejected edits

The contract is derived from ``skills.json``, so it follows the catalog instead
of hard-coding a version. A document that fails any check is a hard failure: the
gate refuses it no matter how much its numeric score improves.

Every document is read through a :class:`TreeSource`, so the working tree and a
published git ref are scored by exactly the same rules. A baseline whose
auxiliary files were resolved from the working tree would score higher than it
deserves, which is the one failure mode this tool exists to prevent.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SLOW_START = "<!-- SLOW_UPDATE_START -->"
SLOW_END = "<!-- SLOW_UPDATE_END -->"
APPENDIX_START = "<!-- APPENDIX_START -->"
APPENDIX_END = "<!-- APPENDIX_END -->"
PROTECTED = (SLOW_START, SLOW_END, APPENDIX_START, APPENDIX_END)

EVOLUTION_DOC = "references/skill-evolution.md"

# SkillOpt's deployed artifact is kept compact, because SKILL.md is loaded on
# every task while the references are read on demand. One band applies to every
# skill: 400-2,400 estimated tokens, i.e. SkillOpt's 300-2,000 token target plus
# headroom for a skill that has to carry a format schema. Above the ceiling the
# fix is to move depth into `references/`, never to raise this number.
TOKEN_BUDGET = (400, 2400)

# Sections each skill must keep: a gate is only meaningful if the document still
# contains the workflow it is gating.
REQUIRED_SECTIONS = {
    "ppt": ("## Workflow", "## No slide transitions", "## Rules that are not negotiable"),
    "word": ("## Workflow", "## Existing documents and review features", "## Ownership and checks"),
    "pdf": ("## Workflow", "## Common operations", "## Supporting files"),
    "xlsm": ("## Workflow", "## Security and QA", "## Checks"),
    "poster": ("## Choose the workflow", "## QA and delivery rules", "## Image use and rights"),
    "scrape": ("## Workflow", "## Safety and limits", "## Checks and provenance"),
}

FRONTMATTER_KEYS = ("name", "description", "license", "compatibility", "version")
PLACEHOLDER = re.compile(r"\b(TODO|TBD|FIXME|XXX|LOREM IPSUM)\b", re.I)
VERSION_LITERAL = re.compile(r"\bv\d+\.\d+\.\d+\b")
EDIT_OPS = ("add", "replace", "delete")


class TreeSource:
    """Read skill files from a checkout or from a git ref, uniformly.

    ``text`` returns file contents with LF line endings, or None when the file is
    absent. ``exists`` answers the same question without reading the whole file.
    """

    def __init__(self, root=None, ref=None, repo=REPO):
        if (root is None) == (ref is None):
            raise ValueError("give exactly one of root or ref")
        self.root = root
        self.ref = ref
        self.repo = repo

    @property
    def label(self):
        return self.ref if self.ref else os.path.relpath(self.root, REPO)

    def text(self, relpath):
        relpath = relpath.replace(os.sep, "/")
        if self.root is not None:
            path = os.path.join(self.root, relpath)
            if not os.path.isfile(path):
                return None
            with open(path, encoding="utf-8") as handle:
                return handle.read().replace("\r\n", "\n")
        try:
            result = subprocess.run(["git", "-C", self.repo, "show", "%s:%s" % (self.ref, relpath)],
                                    capture_output=True, text=True, check=True)
        except (OSError, subprocess.SubprocessError):
            return None
        return result.stdout.replace("\r\n", "\n")

    def exists(self, relpath):
        return self.text(relpath) is not None


def working_tree():
    return TreeSource(root=REPO)


def load_catalog():
    with open(os.path.join(REPO, "skills.json"), encoding="utf-8") as handle:
        return json.load(handle)


def estimate_tokens(text):
    """Cheap, stable token estimate; the trend matters, not the last digit."""
    return (len(text) + 3) // 4


def parse_frontmatter(text):
    """Return the frontmatter mapping, or None when the block is malformed."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 3)
    if end == -1:
        return None
    fields = {}
    for line in text[4:end].splitlines():
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if match:
            fields[match.group(1)] = match.group(2).strip().strip('"')
    return fields


def protected_regions(text):
    """Validate the machine-managed regions and return (ok, detail)."""
    for marker, label in ((SLOW_START, "slow-update start"), (SLOW_END, "slow-update end"),
                          (APPENDIX_START, "appendix start"), (APPENDIX_END, "appendix end")):
        if text.count(marker) != 1:
            return False, "%s marker must appear exactly once" % label
    slow_start, slow_end = text.index(SLOW_START), text.index(SLOW_END)
    appendix_start, appendix_end = text.index(APPENDIX_START), text.index(APPENDIX_END)
    if slow_start > slow_end or appendix_start > appendix_end:
        return False, "protected markers are out of order"
    if slow_start < appendix_start < slow_end or appendix_start < slow_start < appendix_end:
        return False, "protected regions must not overlap"
    slow_body = text[slow_start + len(SLOW_START):slow_end].strip()
    if len(slow_body) < 80:
        return False, "slow-update region carries no longitudinal guidance (%d chars)" % len(slow_body)
    appendix_body = text[appendix_start + len(APPENDIX_START):appendix_end].strip()
    return True, "slow update %d chars, appendix %d lines" % (
        len(slow_body), appendix_body.count("\n") + 1)


def load_evals(source, folder, name, version):
    """Contract for the held-out split the gate scores against."""
    raw = source.text("%s/evals/evals.json" % folder)
    if raw is None:
        return False, "no evals/evals.json"
    try:
        data = json.loads(raw)
    except ValueError as error:
        return False, "evals/evals.json is not valid JSON: %s" % error
    if data.get("skill_name") != name:
        return False, "evals skill_name is %r, expected %r" % (data.get("skill_name"), name)
    if data.get("skill_version") != version:
        return False, "evals skill_version is %r, expected %r" % (data.get("skill_version"), version)
    entries = data.get("evals") or []
    if not entries:
        return False, "no evals declared"
    ids = [entry.get("id") for entry in entries]
    if len(ids) != len(set(ids)) or None in ids:
        return False, "eval ids must be unique and non-null"
    splits = [entry.get("split") for entry in entries]
    unknown = sorted({s for s in splits if s not in ("selection", "test")})
    if unknown:
        return False, "unknown split(s): %s" % ", ".join(repr(s) for s in unknown)
    if "selection" not in splits:
        return False, "no selection-split eval to optimise against"
    if "test" not in splits:
        return False, "no held-out test-split eval"
    for entry in entries:
        if not entry.get("prompt") or not entry.get("expected_output"):
            return False, "eval %r lacks a prompt or expected_output" % entry.get("id")
        if not (entry.get("assertions") or entry.get("expectations")):
            return False, "eval %r declares no assertions" % entry.get("id")
    return True, "%d evals (%d selection, %d held-out test)" % (
        len(entries), splits.count("selection"), splits.count("test"))


def checks_for(spec, version, source, guide_text):
    """Return [(check_id, weight, passed, detail)] for one skill document."""
    results = []

    fields = parse_frontmatter(guide_text)
    if fields is None:
        results.append(("frontmatter", 3, False, "missing a YAML frontmatter block"))
    else:
        missing = [key for key in FRONTMATTER_KEYS if not fields.get(key)]
        if missing:
            results.append(("frontmatter", 3, False, "frontmatter lacks %s" % ", ".join(missing)))
        elif fields["name"] != spec["name"]:
            results.append(("frontmatter", 3, False,
                            "name is %r, catalog says %r" % (fields["name"], spec["name"])))
        else:
            results.append(("frontmatter", 3, True, "name, description, license, compatibility, version"))

    declared = fields.get("version") if fields else None
    results.append(("version", 2, declared == version,
                    "frontmatter version %r vs catalog %r" % (declared, version)))

    ok, detail = protected_regions(guide_text)
    results.append(("protected_regions", 3, ok, detail))

    floor, ceiling = TOKEN_BUDGET
    tokens = estimate_tokens(guide_text)
    results.append(("budget", 3, floor <= tokens <= ceiling,
                    "~%d tokens (band %d-%d)" % (tokens, floor, ceiling)))

    required = REQUIRED_SECTIONS.get(spec["key"], ())
    absent = [heading for heading in required if heading not in guide_text]
    results.append(("sections", 2, not absent,
                    "missing %s" % ", ".join(absent) if absent
                    else "%d required sections present" % len(required)))

    evolution = "%s/%s" % (spec["folder"], EVOLUTION_DOC)
    linked = EVOLUTION_DOC in guide_text
    results.append(("evolution_ref", 2, linked and source.exists(evolution),
                    "linked and present" if linked and source.exists(evolution)
                    else ("not linked" if not linked else "%s is missing" % evolution)))

    ok, detail = load_evals(source, spec["folder"], spec["name"], version)
    results.append(("evals_split", 3, ok, detail))

    placeholders = sorted({match.upper() for match in PLACEHOLDER.findall(guide_text)})
    results.append(("placeholders", 1, not placeholders,
                    "found %s" % ", ".join(placeholders) if placeholders else "none"))

    stale = sorted(set(VERSION_LITERAL.findall(guide_text)) - {version})
    results.append(("stale_version", 2, not stale,
                    "stale version literals %s" % ", ".join(stale) if stale
                    else "only %s" % version))
    return results


def score_document(spec, version, source, text):
    """Score one document against the contract.

    Line endings are normalised: how a checkout happened to materialise a file is
    not a quality signal, and a git-sourced baseline has to score the same as the
    working tree it is compared against.
    """
    text = text.replace("\r\n", "\n")
    checks = checks_for(spec, version, source, text)
    earned = sum(weight for _, weight, passed, _ in checks if passed)
    total = sum(weight for _, weight, _, _ in checks)
    return {
        "skill": spec["name"],
        "key": spec["key"],
        "score": round(100.0 * earned / total, 2),
        "hard_pass": all(passed for _, _, passed, _ in checks),
        "tokens": estimate_tokens(text),
        "checks": [{"id": cid, "weight": weight, "passed": passed, "detail": detail}
                   for cid, weight, passed, detail in checks],
    }


def score_skill(spec, version, source):
    """Score a skill's SKILL.md as it exists in a source."""
    text = source.text("%s/SKILL.md" % spec["folder"])
    if text is None:
        return {"skill": spec["name"], "key": spec["key"], "score": 0.0, "hard_pass": False,
                "tokens": 0, "checks": [{"id": "document", "weight": 1, "passed": False,
                                         "detail": "SKILL.md not found"}]}
    return score_document(spec, version, source, text)


def catalog_specs(keys=None):
    return [s for s in load_catalog()["skills"] if keys is None or s["key"] in keys]


def score_all(version, source, keys=None):
    return [score_skill(spec, version, source) for spec in catalog_specs(keys)]


# --------------------------------------------------------------------------- #
# Bounded edits (add / delete / replace) and the strict-improvement gate
# --------------------------------------------------------------------------- #

def apply_edits(text, edits, max_edits=8, lr_budget=4000):
    """Apply bounded edits to a skill document.

    Mirrors SkillOpt's edit discipline: a small number of add/delete/replace
    patches per step, a textual learning-rate budget on how much text a step may
    change, and a refusal to write inside a protected region.
    """
    if len(edits) > max_edits:
        raise ValueError("patch proposes %d edits, the step allows %d" % (len(edits), max_edits))
    for edit in edits:
        if edit.get("op") not in EDIT_OPS:
            raise ValueError("unknown op %r" % edit.get("op"))
        if edit["op"] != "delete" and not edit.get("text"):
            raise ValueError("op %r requires text" % edit["op"])
    candidate, changed = text, 0
    for index, edit in enumerate(edits, 1):
        for field in ("text", "find", "after", "before"):
            if any(marker in (edit.get(field) or "") for marker in PROTECTED):
                raise ValueError("edit %d may not write inside a protected region" % index)
        if edit["op"] == "add":
            anchor = edit.get("after") or edit.get("before")
            if not anchor:
                raise ValueError("edit %d: add needs an 'after' or 'before' anchor" % index)
            if candidate.count(anchor) != 1:
                raise ValueError("edit %d: anchor appears %d times" % (index, candidate.count(anchor)))
            insertion = edit["text"].rstrip("\n") + "\n"
            position = candidate.index(anchor) + (len(anchor) if edit.get("after") else 0)
            candidate = candidate[:position] + "\n" + insertion + candidate[position:]
            changed += len(insertion) + 1
        else:
            find = edit.get("find")
            if not find:
                raise ValueError("edit %d: %s needs a 'find' string" % (index, edit["op"]))
            if candidate.count(find) != 1:
                raise ValueError("edit %d: 'find' appears %d times" % (index, candidate.count(find)))
            replacement = edit.get("text", "") if edit["op"] == "replace" else ""
            candidate = candidate.replace(find, replacement)
            changed += max(len(find), len(replacement))
    if changed > lr_budget:
        raise ValueError("patch changes %d characters, over the %d budget" % (changed, lr_budget))
    return candidate, changed


def gate(candidate, baseline):
    """SkillOpt's acceptance rule: strict improvement, and no hard failure."""
    return bool(candidate["hard_pass"] and candidate["score"] > baseline["score"])


def optimize(spec, version, source, patch_path, workspace):
    """Apply one bounded edit step; accept it only on strict improvement.

    A rejected candidate is not discarded silently: it is written to the
    workspace and its edits are listed in the run report.
    """
    os.makedirs(workspace, exist_ok=True)
    with open(patch_path, encoding="utf-8") as handle:
        patch = json.load(handle)
    if patch.get("skill") not in (None, spec["name"]):
        raise SystemExit("patch targets %r, not %r" % (patch.get("skill"), spec["name"]))
    text = source.text("%s/SKILL.md" % spec["folder"])
    if text is None:
        raise SystemExit("no SKILL.md for %s" % spec["name"])
    candidate_text, changed = apply_edits(text, patch.get("edits") or [],
                                          max_edits=patch.get("max_edits", 8),
                                          lr_budget=patch.get("lr_budget", 4000))
    candidate_path = os.path.join(workspace, "%s-candidate.md" % spec["name"])
    with open(candidate_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(candidate_text)
    baseline = score_document(spec, version, source, text)
    candidate = score_document(spec, version, source, candidate_text)
    accepted = gate(candidate, baseline)
    if accepted:
        reason = None
    elif not candidate["hard_pass"]:
        reason = "candidate fails the skill-document contract"
    elif baseline["score"] >= 100.0:
        # The contract score saturates by design. Beyond full compliance the
        # acceptance signal has to come from real rollouts, as in SkillOpt's own
        # training loop; this offline gate cannot invent one.
        reason = "baseline already scores 100; use the SkillOpt training loop for further gains"
    else:
        reason = "candidate did not strictly improve the score"
    return {"skill": spec["name"], "changed_chars": changed, "accepted": accepted, "reason": reason,
            "baseline_score": baseline["score"], "candidate_score": candidate["score"],
            "baseline_tokens": baseline["tokens"], "candidate_tokens": candidate["tokens"],
            "candidate_path": candidate_path,
            "rejected_edits": [] if accepted else (patch.get("edits") or [])}


def make_source(baseline):
    """A checkout path, or anything else treated as a git ref."""
    if os.path.isdir(baseline):
        return TreeSource(root=os.path.abspath(baseline))
    return TreeSource(ref=baseline)


def compare_baseline(version, source, baseline, keys=None):
    """Gate the working tree against a published tree or git ref."""
    baseline_source = make_source(baseline)
    rows = []
    for current in score_all(version, source, keys):
        spec = next(s for s in load_catalog()["skills"] if s["key"] == current["key"])
        if baseline_source.text("%s/SKILL.md" % spec["folder"]) is None:
            rows.append({"skill": spec["name"], "key": spec["key"], "baseline": None,
                         "baseline_source": "no %s/SKILL.md in %s" % (spec["folder"], baseline_source.label),
                         "current": current, "accepted": False})
            continue
        scored = score_skill(spec, version, baseline_source)
        rows.append({"skill": spec["name"], "key": spec["key"], "baseline": scored,
                     "baseline_source": baseline_source.label, "current": current,
                     "accepted": gate(current, scored)})
    return rows


def render_report(version, rows, path):
    sources = {row["baseline_source"] for row in rows if row["baseline"]}
    lines = ["# SkillOpt gate report", "",
             "Skill document contract and strict-improvement gate for `%s`." % version, "",
             "SkillOpt treats each skill document as trainable text: a candidate edit is",
             "accepted only when it strictly improves a held-out score, and a document that",
             "fails any contract check is rejected regardless of its numeric score.", "",
             "Baseline: %s" % (", ".join(sorted(sources)) if sources else "none matched"), "",
             "| Skill | Baseline | Current | Delta | Accepted | Tokens (before -> after) |",
             "|---|---|---|---|---|---|"]
    for row in rows:
        baseline, current = row["baseline"], row["current"]
        lines.append("| `%s` | %s | %.2f | %s | %s | %s -> %d |" % (
            row["skill"], "missing" if baseline is None else "%.2f" % baseline["score"],
            current["score"],
            "--" if baseline is None else "%+.2f" % round(current["score"] - baseline["score"], 2),
            "yes" if row["accepted"] else "no",
            "n/a" if baseline is None else str(baseline["tokens"]), current["tokens"]))
    lines += ["", "## Per-check evidence", ""]
    for row in rows:
        lines += ["### %s" % row["skill"], ""]
        for check in row["current"]["checks"]:
            lines.append("- `%s`: %s - %s" % (check["id"], "pass" if check["passed"] else "FAIL",
                                             check["detail"]))
        lines.append("")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    return path


def main(argv=None):
    catalog = load_catalog()
    version = catalog["version"]
    workspace = os.path.join(REPO, "skill-review-workspace", "skillopt")
    ap = argparse.ArgumentParser(description="SkillOpt-style gate for the published skill documents.")
    ap.add_argument("command", choices=("check", "optimize", "report"))
    ap.add_argument("--skill", default="all",
                    choices=tuple(s["key"] for s in catalog["skills"]) + ("all",))
    ap.add_argument("--root", help="checkout to score instead of this repository")
    ap.add_argument("--baseline", help="published tree or git ref to gate against, e.g. v2.0.0")
    ap.add_argument("--patch", help="bounded edit patch JSON (optimize)")
    ap.add_argument("--out", help="report path (report)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)
    keys = None if args.skill == "all" else (args.skill,)
    source = TreeSource(root=os.path.abspath(args.root)) if args.root else working_tree()

    if args.command == "optimize":
        if not args.patch:
            ap.error("optimize needs --patch")
        spec = next(s for s in catalog["skills"] if s["key"] == args.skill)
        result = optimize(spec, version, source, args.patch, workspace)
        print(json.dumps(result, indent=2) if args.json else
              "%s: %s (%.2f -> %.2f, %d chars changed, ~%d -> ~%d tokens)%s" % (
                  result["skill"], "ACCEPTED" if result["accepted"] else "REJECTED",
                  result["baseline_score"], result["candidate_score"], result["changed_chars"],
                  result["baseline_tokens"], result["candidate_tokens"],
                  "" if result["accepted"] else "\nrejected: %s\ncandidate kept at %s" % (
                      result["reason"], os.path.relpath(result["candidate_path"], REPO))))
        return 0 if result["accepted"] else 1

    if args.command == "report":
        if not args.baseline:
            ap.error("report needs --baseline")
        rows = compare_baseline(version, source, args.baseline, keys)
        os.makedirs(workspace, exist_ok=True)
        with open(os.path.join(workspace, "report.json"), "w", encoding="utf-8", newline="\n") as handle:
            json.dump({"version": version, "baseline": args.baseline, "rows": rows}, handle, indent=2)
        out = render_report(version, rows, args.out or os.path.join(workspace, "report.md"))
        print("wrote %s" % os.path.relpath(out, REPO))
        return 0

    if args.baseline:
        rows = compare_baseline(version, source, args.baseline, keys)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            for row in rows:
                baseline = row["baseline"]
                print("%-24s baseline %6s -> current %6.2f  %s%s" % (
                    row["skill"], "n/a" if baseline is None else "%.2f" % baseline["score"],
                    row["current"]["score"], "ACCEPTED" if row["accepted"] else "REJECTED",
                    "" if baseline else "  (%s)" % row["baseline_source"]))
        return 0 if all(row["accepted"] for row in rows) else 1

    results = score_all(version, source, keys)
    failed = False
    for result in results:
        if args.json:
            print(json.dumps(result, indent=2))
            continue
        print("%-24s %6.2f %s (~%d tokens)" % (result["skill"], result["score"],
                                               "PASS" if result["hard_pass"] else "FAIL", result["tokens"]))
        for check in result["checks"]:
            if not check["passed"]:
                print("    FAIL %-18s %s" % (check["id"], check["detail"]))
        failed = failed or not result["hard_pass"]
    if not args.json:
        print("%s: %d skill documents checked against %s" % (
            "FAIL" if failed else "PASS", len(results), version))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
