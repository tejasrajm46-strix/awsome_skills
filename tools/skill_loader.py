#!/usr/bin/env python3
"""Progressive skill loading: three stages, measured context, no silent omissions.

    from skill_registry import build_index
    from skill_loader import SkillLoader
    loader = SkillLoader(index, cache)
    stage_a = loader.metadata("ppt")            # identity + cost, before committing
    stage_b = loader.skill("ppt")               # the authoritative SKILL.md
    stage_c = loader.reference("ppt", "references/deck-schema.md")

Stage A returns only what discovery needs (identity, description, formats,
dependencies, token cost). Stage B returns the skill's full guide text - the
guide is the authoritative instruction, and the loader never substitutes a
summary for it. Stage C loads a single reference by its index-listed name and
refuses anything the skill does not actually contain, so a hallucinated
reference path cannot be loaded.

Every load is recorded: path, content hash, cache provenance and token cost.
`loaded_context()` returns what actually entered the task, which is what the
orchestrator reports and what tests use to prove irrelevant skills were never
loaded. Reference links whose anchor text marks them as required reading
("read ... before", "first") are surfaced as `required_references` - a
heuristic aid, reported honestly as such; the guide itself stays authoritative.
"""
from __future__ import annotations

import os
import re
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import skill_registry

LINK = re.compile(r"\[[^\]]*\]\(([^)]+\.md)\)", re.I)
REQUIRED_TEXT = re.compile(r"\[[^\]]*\]\(([^)]+\.md)\)[^.]*(?:\bread\b.*\bbefore\b|before\b.*\bread\b|\bread\b|\bfirst\b)", re.I)


class SkillLoader:
    def __init__(self, index, cache=None):
        self.index = index
        self.cache = cache
        self.loaded = []

    def _skill(self, key):
        for skill in self.index["skills"]:
            if skill["key"] == key:
                return skill
        raise KeyError("no skill %r in the registry" % key)

    def _record(self, path, entry, from_cache, stage, skill_key):
        record = {"path": os.path.relpath(path, self.index["root"]).replace(os.sep, "/"),
                  "sha256": entry["sha256"], "tokens_est": entry["tokens_est"],
                  "from_cache": from_cache, "stage": stage, "skill": skill_key}
        self.loaded.append(record)
        return record

    def metadata(self, key):
        """Stage A: what discovery and planning need, before any guide is loaded."""
        skill = self._skill(key)
        # Stage A loads the index entry, not the guide: only the description and
        # identity fields are billed as context, and the record says so.
        record = {"path": "%s/SKILL.md" % skill["folder"], "sha256": "",
                  "tokens_est": skill_registry.token_estimate(skill["description"]),
                  "from_cache": False, "stage": "A", "skill": key, "guide_loaded": False}
        self.loaded.append(record)
        return {"key": key, "name": skill["name"], "version": skill["version"],
                "description": skill["description"], "formats": skill["formats"],
                "shared_helper": skill["shared_helper"],
                "execution_surface": skill["execution_surface"],
                "scripts": skill["scripts"], "tokens_est": skill["token_estimate"],
                "load_record": record}

    def skill(self, key):
        """Stage B: the full, authoritative guide text for a selected skill."""
        skill = self._skill(key)
        guide_path = os.path.join(self.index["root"], skill["folder"], "SKILL.md")
        if self.cache:
            entry, from_cache = self.cache.get(guide_path)
        else:
            content = skill_registry.read_text(guide_path)
            entry = {"sha256": "", "tokens_est": skill["token_estimate"], "content": content}
            from_cache = False
        record = self._record(guide_path, entry, from_cache, "B", key)
        content = entry["content"].replace("\r\n", "\n")
        linked = sorted({target for target in LINK.findall(content)
                         if not target.startswith(("http://", "https://", "#"))})
        required = sorted({target for target in REQUIRED_TEXT.findall(content)
                           if not target.startswith(("http://", "https://", "#"))})
        return {"key": key, "name": skill["name"], "content": content,
                "tokens_est": entry["tokens_est"], "sha256": entry["sha256"],
                "linked_references": linked, "required_references": required,
                "load_record": record}

    def resolve_reference(self, key, name):
        """Resolve a caller-supplied reference name to the skill's index entry.

        Accepts the exact index path, the same path with a leading ``./``, and a
        bare basename when exactly one reference matches it. Unknown and
        ambiguous names raise ValueError listing what the skill ships, so a
        hallucinated path is refused with an actionable message rather than a
        crash or a silent empty load.
        """
        skill = self._skill(key)
        normalized = name.replace(os.sep, "/").strip()
        while normalized.startswith("./"):
            normalized = normalized[2:]
        normalized = normalized.lstrip("/")
        if normalized in skill["references"]:
            return normalized
        matches = [ref for ref in skill["references"]
                   if ref.rsplit("/", 1)[-1] == normalized or ref.endswith("/" + normalized)]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError("%s has several references matching %r: %s; pass the full path"
                             % (key, name, ", ".join(matches)))
        raise ValueError("%s has no reference %r; available: %s"
                         % (key, name, ", ".join(skill["references"]) or "none"))

    def reference(self, key, name):
        """Stage C: one reference, by its index-listed name; unknown names are refused."""
        skill = self._skill(key)
        normalized = self.resolve_reference(key, name)
        path = os.path.join(self.index["root"], skill["folder"], normalized)
        if self.cache:
            entry, from_cache = self.cache.get(path)
        else:
            content = skill_registry.read_text(path)
            entry = {"sha256": "", "tokens_est": skill_registry.token_estimate(content),
                     "content": content}
            from_cache = False
        record = self._record(path, entry, from_cache, "C", key)
        return {"key": key, "reference": normalized, "content": entry["content"],
                "tokens_est": entry["tokens_est"], "sha256": entry["sha256"],
                "load_record": record}

    def loaded_context(self, stage=None, skill=None):
        records = self.loaded
        if stage:
            records = [r for r in records if r["stage"] == stage]
        if skill:
            records = [r for r in records if r["skill"] == skill]
        return {"files": len(records), "tokens_est": sum(r["tokens_est"] for r in records),
                "records": records}

    def loaded_skills(self):
        return sorted({record["skill"] for record in self.loaded})


def main(argv=None):
    import argparse
    import json
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    meta = sub.add_parser("metadata"); meta.add_argument("key")
    guide = sub.add_parser("skill"); guide.add_argument("key")
    ref = sub.add_parser("reference"); ref.add_argument("key"); ref.add_argument("name")
    args = ap.parse_args(argv)
    index = skill_registry.build_index()
    loader = SkillLoader(index)
    if args.command == "metadata":
        info = loader.metadata(args.key)
        info.pop("load_record", None)
        info.pop("scripts", None)
        print(json.dumps(info, indent=2))
    elif args.command == "skill":
        info = loader.skill(args.key)
        print(info["content"])
        print("\n<!-- linked: %s -->" % ", ".join(info["linked_references"]))
        print("<!-- required (heuristic): %s -->" % ", ".join(info["required_references"]))
    else:
        info = loader.reference(args.key, args.name)
        print(info["content"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
