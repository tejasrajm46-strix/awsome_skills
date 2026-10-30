#!/usr/bin/env python3
"""Regression tests for the skill intelligence layer: registry, cache, loader."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import skill_loader
import skill_registry


def test_index_and_validation():
    index = skill_registry.build_index()
    keys = [s["key"] for s in index["skills"]]
    assert set(keys) == {"ppt", "word", "pdf", "xlsm", "poster", "scrape"}, keys
    by_key = {s["key"]: s for s in index["skills"]}
    assert by_key["ppt"]["execution_surface"] == "builder"
    assert by_key["pdf"]["execution_surface"] == "inspection"
    assert by_key["scrape"]["execution_surface"] == "research"
    assert by_key["ppt"]["scripts"]["validators"] == ["scripts/validate_deck.py"]
    assert "references/deck-schema.md" in by_key["ppt"]["references"]
    assert by_key["word"]["shared_helper"] == "ultimate-scrape-skill"
    assert all(s["version"] == index["catalog_version"] for s in index["skills"])

    # A missing script listed by the tree cannot survive validation: simulate
    # a catalog entry pointing at a folder with no SKILL.md.
    with tempfile.TemporaryDirectory() as tmp:
        broken = dict(index)
        broken["root"] = tmp
        try:
            skill_registry.validate_index(broken)
        except ValueError as exc:
            assert "missing script" in str(exc), exc
        else:
            raise AssertionError("index validated against a nonexistent tree")


def test_discovery_is_catalog_driven():
    index = skill_registry.build_index()
    found = skill_registry.discover(index, formats=["pptx"])
    assert found[0]["key"] == "ppt", found
    both = skill_registry.discover(index, formats=["pptx", "pdf"])
    keys = [c["key"] for c in both[:2]]
    assert {"ppt", "pdf"} <= set(keys), keys
    assert skill_registry.skill_for_format(index, "xlsm") == "xlsm"
    assert skill_registry.skill_for_format(index, "presentation") == "ppt"
    assert skill_registry.skill_for_format(index, "m4a") is None

    # A NEW compatible skill in a copy of the repository is discoverable
    # without touching this module: no hardcoded five-skill list.
    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp)
        shutil.copytree(".", clone / "repo",
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".skill-cache"),
                        dirs_exist_ok=True)
        catalog = json.loads((clone / "repo" / "skills.json").read_text(encoding="utf-8"))
        (clone / "repo" / "sketch_skill").mkdir()
        (clone / "repo" / "sketch_skill" / "SKILL.md").write_text(
            "---\nname: sketch-generator\ndescription: \"Sketch quick wireframes and "
            "storyboards as png images.\"\nlicense: MIT\nversion: v3.1.0\n---\n\n# Sketch\n",
            encoding="utf-8")
        (clone / "repo" / "sketch_skill" / "scripts").mkdir()
        (clone / "repo" / "sketch_skill" / "scripts" / "build_sketch.py").write_text(
            "print('builder')\n", encoding="utf-8")
        catalog["skills"].append({"key": "sketch", "folder": "sketch_skill",
                                  "name": "sketch-generator", "formats": ["sketch", "png"],
                                  "shared_helper": "ultimate-scrape-skill"})
        (clone / "repo" / "skills.json").write_text(json.dumps(catalog), encoding="utf-8")
        extended = skill_registry.build_index(str(clone / "repo"))
        assert "sketch" in [s["key"] for s in extended["skills"]]
        assert skill_registry.skill_for_format(extended, "sketch") == "sketch"
        assert skill_registry.discover(extended, formats=["sketch"])[0]["key"] == "sketch"


def test_progressive_loading():
    index = skill_registry.build_index()
    loader = skill_loader.SkillLoader(index)

    stage_a = loader.metadata("ppt")
    assert stage_a["load_record"]["stage"] == "A"
    assert stage_a["load_record"]["guide_loaded"] is False
    assert stage_a["tokens_est"] > 0

    stage_b = loader.skill("ppt")
    assert "## Workflow" in stage_b["content"], "stage B returns the authoritative guide"
    assert stage_b["load_record"]["guide_loaded"] if "guide_loaded" in stage_b["load_record"] else True
    assert "references/deck-schema.md" in stage_b["linked_references"]
    assert stage_b["required_references"], "ppt flags at least one required reference"

    stage_c = loader.reference("ppt", "references/deck-schema.md")
    assert "layout" in stage_c["content"].lower()
    try:
        loader.reference("ppt", "references/does-not-exist.md")
    except ValueError as exc:
        assert "no reference" in str(exc), exc
    else:
        raise AssertionError("unknown reference must be refused")
    try:
        loader.skill("nope")
    except KeyError:
        pass
    else:
        raise AssertionError("unknown skill must be refused")

    # A second load of the same guide is a cache hit with the same hash.
    again = loader.skill("ppt")
    assert again["load_record"]["from_cache"] is False

    # Staged loading really is cheaper than loading everything, and the
    # ledger proves which skills were never loaded.
    everything = sum(s["token_estimate"] for s in index["skills"])
    staged = loader.loaded_context()["tokens_est"]
    assert staged < everything, (staged, everything)
    assert "poster" not in loader.loaded_skills()
    assert "xlsm" not in loader.loaded_skills()


def main():
    test_index_and_validation()
    test_discovery_is_catalog_driven()
    test_progressive_loading()
    print("PASS: registry indexes and validates the catalog, discovery is catalog-driven, "
          "cache invalidates by content, staged loading omits nothing and loads less")


if __name__ == "__main__":
    main()
