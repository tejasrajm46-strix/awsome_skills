#!/usr/bin/env python3
"""Regression tests for the SkillOpt-style skill-document gate."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import skillopt_gate as gate


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def make_root(tmp, version="v3.0.0", slow_body=None, split=("selection", "test")):
    """Build a synthetic skill tree that satisfies every contract check."""
    root = Path(tmp) / "root"
    folder = root / "demo_skill"
    slow = slow_body if slow_body is not None else (
        "## Carried-forward rules (protected)\n\n"
        "- Never lower a font size to make text fit; split the content instead.\n"
        "- Always re-open the saved artifact before claiming it is finished.\n")
    guide = (
        "---\nname: demo-skill\ndescription: \"Demo skill for gate tests.\"\nlicense: MIT\n"
        "compatibility: Python 3.8+\nversion: %s\n---\n\n# Demo\n\nFiller sentence for the "
        "budget check. %s\n\n## Workflow\n\n1. Do the thing.\n\n"
        "Read [`references/skill-evolution.md`](references/skill-evolution.md) before editing this guide.\n\n"
        "<!-- SLOW_UPDATE_START -->\n%s<!-- SLOW_UPDATE_END -->\n\n"
        "<!-- APPENDIX_START -->\nRun the skill's own tests last.\n<!-- APPENDIX_END -->\n"
        % (version, "Padding sentence for the token band. " * 30, slow))
    write(folder / "SKILL.md", guide)
    write(folder / "references/skill-evolution.md", "# Skill evolution\n\nRun the gate.\n")
    evals = {"skill_name": "demo-skill", "skill_version": version,
             "evals": [{"id": 1, "split": split[0], "prompt": "A task", "expected_output": "An artifact",
                        "assertions": ["It works"]},
                       {"id": 2, "split": split[1], "prompt": "Held out", "expected_output": "An artifact",
                        "assertions": ["It works"]}]}
    write(folder / "evals/evals.json", json.dumps(evals, indent=2) + "\n")
    return root, {"key": "demo", "name": "demo-skill", "folder": "demo_skill"}, guide


def git(cwd, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME="gate", GIT_AUTHOR_EMAIL="gate@example.com",
               GIT_COMMITTER_NAME="gate", GIT_COMMITTER_EMAIL="gate@example.com")
    return subprocess.run(["git", "-c", "commit.gpgsign=false", *args], cwd=cwd,
                          capture_output=True, text=True, check=True, env=env)


def main():
    assert gate.estimate_tokens("") == 0
    assert gate.estimate_tokens("abcd" * 10) == 10
    print("ok   token estimate is stable")

    assert gate.parse_frontmatter("no frontmatter") is None
    assert gate.parse_frontmatter("---\nname: x\n") is None
    assert gate.parse_frontmatter('---\nname: demo-skill\ndescription: "A thing"\n---\nbody')["name"] == "demo-skill"
    assert gate.parse_frontmatter("---\nname: demo-skill\nversion: v9.9.9\n---\n")["version"] == "v9.9.9"
    print("ok   frontmatter parsing rejects malformed blocks")

    good = ("<!-- SLOW_UPDATE_START -->\n%s\n<!-- SLOW_UPDATE_END -->\n"
            "<!-- APPENDIX_START -->\nx\n<!-- APPENDIX_END -->" % ("guidance " * 20))
    assert gate.protected_regions(good)[0]
    assert not gate.protected_regions(good.replace(gate.SLOW_END, ""))[0]
    assert not gate.protected_regions(
        good.replace(gate.SLOW_START, gate.SLOW_START + "\n" + gate.SLOW_START))[0]
    short = ("<!-- SLOW_UPDATE_START -->\ntiny\n<!-- SLOW_UPDATE_END -->\n"
             "<!-- APPENDIX_START -->\nx\n<!-- APPENDIX_END -->")
    assert not gate.protected_regions(short)[0], "a short slow-update body must fail"
    overlapping = ("<!-- SLOW_UPDATE_START -->\n%s\n<!-- APPENDIX_START -->\nx\n"
                   "<!-- SLOW_UPDATE_END -->\n<!-- APPENDIX_END -->" % ("guidance " * 20))
    assert not gate.protected_regions(overlapping)[0], "overlapping regions must fail"
    print("ok   protected regions are balanced, ordered, non-overlapping and non-empty")

    with tempfile.TemporaryDirectory() as tmp:
        root, spec, guide = make_root(tmp)
        source = gate.TreeSource(root=str(root))
        result = gate.score_document(spec, "v3.0.0", source, guide)
        assert result["hard_pass"], [c for c in result["checks"] if not c["passed"]]
        assert result["score"] == 100.0, result["score"]
        print("ok   a complete document passes every contract check")

        for label, mutated in (
                ("protected region", guide.replace("<!-- APPENDIX_START -->", "")),
                ("stale version", guide.replace("# Demo", "# Demo (v2.0.0)")),
                ("placeholder", guide.replace("# Demo", "# Demo TODO")),
                ("missing evolution link", guide.replace("references/skill-evolution.md", "other.md"))):
            broken = gate.score_document(spec, "v3.0.0", source, mutated)
            assert not broken["hard_pass"], label
            assert broken["score"] < 100.0, label
        print("ok   degraded documents fail the gate instead of scoring partial credit")

        # The held-out split must exist before a score means anything.
        write(root / "demo_skill/evals/evals.json", json.dumps(
            {"skill_name": "demo-skill", "skill_version": "v3.0.0",
             "evals": [{"id": 1, "split": "selection", "prompt": "p", "expected_output": "o",
                        "assertions": ["a"]}]}) + "\n")
        assert not gate.load_evals(source, "demo_skill", "demo-skill", "v3.0.0")[0]
        write(root / "demo_skill/evals/evals.json", json.dumps(
            {"skill_name": "demo-skill", "skill_version": "v2.0.0",
             "evals": [{"id": 1, "split": "selection", "prompt": "p", "expected_output": "o",
                        "assertions": ["a"]},
                       {"id": 2, "split": "test", "prompt": "p", "expected_output": "o",
                        "assertions": ["a"]}]}) + "\n")
        assert not gate.load_evals(source, "demo_skill", "demo-skill", "v3.0.0")[0], \
            "an evals version that disagrees with the catalog must fail"
        print("ok   evals require a selection split, a held-out test split and the catalog version")

        # A git ref has to score exactly like the same tree on disk, including the
        # checks that read auxiliary files. Resolving those from the working tree
        # is how a baseline ends up scoring higher than it deserves.
        git(root, "init", "-q")
        git(root, "add", "-A")
        git(root, "commit", "-qm", "demo")
        git(root, "tag", "vX")
        on_disk = gate.score_skill(spec, "v3.0.0", gate.TreeSource(root=str(root)))
        from_ref = gate.score_skill(spec, "v3.0.0", gate.TreeSource(ref="vX", repo=str(root)))
        assert on_disk == from_ref, (on_disk, from_ref)
        # A ref that does not exist reports the missing document rather than a score.
        missing = gate.score_skill(spec, "v3.0.0", gate.TreeSource(ref="no-such-ref", repo=str(root)))
        assert missing["score"] == 0.0 and not missing["hard_pass"], missing
        print("ok   a git ref baseline scores identically to the same tree on disk")

    # Bounded edits: allowed ops work, and abuse is refused.
    text = "## Workflow\n\n1. Step one.\n\n## Notes\n\nKeep it short.\n"
    replacement = "Step one, carefully."
    edited, changed = gate.apply_edits(text, [{"op": "replace", "find": "Step one.", "text": replacement}])
    assert edited == text.replace("Step one.", replacement)
    assert changed == max(len("Step one."), len(replacement)), changed  # a step costs its larger side
    added, _ = gate.apply_edits(text, [{"op": "add", "after": "## Notes", "text": "Extra rule."}])
    assert "Extra rule." in added and added.index("## Notes") < added.index("Extra rule.")
    deleted, _ = gate.apply_edits(text, [{"op": "delete", "find": "\n## Notes\n\nKeep it short.\n"}])
    assert "Keep it short." not in deleted
    print("ok   add, replace and delete edits apply to a document copy")

    for label, edits in (
            ("too many edits", [{"op": "replace", "find": "Step one.", "text": str(i)} for i in range(9)]),
            ("ambiguous find", [{"op": "replace", "find": "o", "text": "0"}]),
            ("unknown op", [{"op": "rewrite", "find": "Step one.", "text": "x"}]),
            ("text with no target", [{"op": "replace", "text": "x"}]),
            ("missing anchor", [{"op": "add", "text": "x"}]),
            ("over the learning-rate budget", [{"op": "replace", "find": "Step one.", "text": "x" * 5000}]),
            ("protected region", [{"op": "add", "after": "## Notes",
                                   "text": gate.SLOW_START + " sabotage " + gate.SLOW_END}]),
            ("empty add", [{"op": "add", "after": "## Notes", "text": ""}])):
        try:
            gate.apply_edits(text, edits)
        except ValueError:
            continue
        raise AssertionError("expected %s to be refused" % label)
    print("ok   unbounded, ambiguous and protected-region edits are refused")

    # The gate itself: strict improvement, and never accept a hard failure.
    assert gate.gate({"score": 90.0, "hard_pass": True}, {"score": 89.99, "hard_pass": True})
    assert not gate.gate({"score": 90.0, "hard_pass": True}, {"score": 90.0, "hard_pass": True})
    assert not gate.gate({"score": 99.0, "hard_pass": True}, {"score": 99.0, "hard_pass": False})
    assert not gate.gate({"score": 99.0, "hard_pass": False}, {"score": 10.0, "hard_pass": False})
    print("ok   acceptance requires strict improvement and no hard failure")

    with tempfile.TemporaryDirectory() as tmp:
        root, spec, guide = make_root(tmp)
        source = gate.TreeSource(root=str(root))
        work = str(Path(tmp) / "work")

        # Start from a document missing its declared version, so the score can move.
        broken = guide.replace("compatibility: Python 3.8+\nversion: v3.0.0\n",
                               "compatibility: Python 3.8+\n")
        assert broken != guide
        write(root / "demo_skill/SKILL.md", broken)

        patch = Path(tmp) / "patch.json"
        patch.write_text(json.dumps({"skill": "demo-skill", "edits": [
            {"op": "replace", "find": "compatibility: Python 3.8+\n",
             "text": "compatibility: Python 3.8+\nversion: v3.0.0\n"}]}), encoding="utf-8")
        accepted = gate.optimize(spec, "v3.0.0", source, str(patch), work)
        assert accepted["accepted"] is True, accepted
        assert accepted["candidate_score"] > accepted["baseline_score"]
        print("ok   optimize accepts an edit that strictly improves the score")

        bad = Path(tmp) / "bad.json"
        bad.write_text(json.dumps({"skill": "demo-skill", "edits": [
            {"op": "replace", "find": "## Workflow", "text": "## Workflow TODO"}]}), encoding="utf-8")
        rejected = gate.optimize(spec, "v3.0.0", source, str(bad), work)
        assert rejected["accepted"] is False, rejected
        assert rejected["reason"] == "candidate fails the skill-document contract", rejected["reason"]
        assert rejected["rejected_edits"], "a rejected step must keep its edits"
        assert Path(rejected["candidate_path"]).is_file(), "a rejected candidate must be kept"
        print("ok   optimize rejects a hard failure and buffers its edits")

        # Once the document is fully compliant the score saturates, and the gate
        # says so instead of pretending a cosmetic edit is an improvement.
        write(root / "demo_skill/SKILL.md", guide)
        saturated = gate.optimize(spec, "v3.0.0", source, str(patch), work)
        assert saturated["accepted"] is False, saturated
        assert "scores 100" in saturated["reason"], saturated["reason"]
        print("ok   a saturated score is reported, not faked")

        # A candidate is never adopted in place: the live document is untouched.
        write(root / "demo_skill/SKILL.md", broken)
        assert (root / "demo_skill/SKILL.md").read_text(encoding="utf-8") == broken
        print("ok   optimization never rewrites the live skill document")

    # A baseline that cannot be read can never be accepted.
    version = gate.load_catalog()["version"]
    rows = gate.compare_baseline(version, gate.working_tree(), "definitely-not-a-ref")
    assert rows and all(row["baseline"] is None and not row["accepted"] for row in rows), rows
    assert "definitely-not-a-ref" in rows[0]["baseline_source"], rows[0]["baseline_source"]
    print("ok   an unreadable baseline is rejected rather than assumed")

    # The shipped catalog must satisfy its own contract.
    result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "tools/skillopt_gate.py"),
                             "check", "--json"], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    # The command emits one JSON object per skill rather than one array.
    decoder, reports, text = json.JSONDecoder(), [], result.stdout
    while text.strip():
        value, offset = decoder.raw_decode(text.lstrip())
        reports.append(value)
        text = text.lstrip()[offset:]
    assert len(reports) == 6, reports
    assert all(report["hard_pass"] for report in reports), [r for r in reports if not r["hard_pass"]]
    print("ok   every catalog skill document passes the shipped contract")

    print("PASS: SkillOpt gate contract, bounded edits, protected regions and acceptance rule")


if __name__ == "__main__":
    main()
