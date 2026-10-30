#!/usr/bin/env python3
"""Regression tests for the content-hash skill cache."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import skill_cache


def test_cache_invalidation():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "note.md"
        target.write_text("alpha\n", encoding="utf-8", newline="\n")
        cache = skill_cache.SkillCache(os.path.join(tmp, "cache"))
        first, hit1 = cache.get(str(target))
        assert hit1 is False
        second, hit2 = cache.get(str(target))
        assert hit2 is True and second["sha256"] == first["sha256"]
        # Content changes are served fresh: the new hash makes the old entry
        # unreachable by construction, so stale instructions cannot be served.
        target.write_text("alpha but different\n", encoding="utf-8", newline="\n")
        third, hit3 = cache.get(str(target))
        assert hit3 is False and third["sha256"] != first["sha256"]
        assert third["content"] == "alpha but different\n"
        stats = cache.stats()
        assert stats["hits"] == 1 and stats["misses"] == 2, stats
        # Prune removes entries whose source vanished or changed.
        removed = cache.prune()
        assert removed == 1, removed  # only the first (stale) entry
        try:
            cache.get(str(Path(tmp) / "missing.md"))
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("cache.get on a missing file must raise")


def test_stats_persist_per_directory():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "note.md"
        target.write_text("data\n", encoding="utf-8", newline="\n")
        directory = os.path.join(tmp, "cache")
        first = skill_cache.SkillCache(directory)
        first.get(str(target))
        first.get(str(target))
        assert first.stats()["hits"] == 1 and first.stats()["misses"] == 1
        # A new instance over the same directory continues the counters - a
        # task reports its own hit rate, not a process's.
        second = skill_cache.SkillCache(directory)
        assert second.stats()["hits"] == 1 and second.stats()["misses"] == 1
        second.get(str(target))
        assert second.stats()["hits"] == 2
        assert skill_cache.SkillCache(directory).stats()["hit_rate"] > 0.5


def main():
    test_cache_invalidation()
    test_stats_persist_per_directory()
    print("PASS: cache invalidates by content, prunes stale entries and "
          "persists hit/miss statistics per directory")


if __name__ == "__main__":
    main()
