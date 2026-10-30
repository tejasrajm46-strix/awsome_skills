#!/usr/bin/env python3
"""Content-hash skill cache: metadata reuse with inherent invalidation.

    from skill_cache import SkillCache
    cache = SkillCache(workspace)            # or SkillCache() for a temp dir
    entry, from_cache = cache.get(path)      # {sha256, bytes, tokens_est, cached_at}

The cache never returns file *content* - content is always read fresh and
hashed on every call, so a modified skill can never be served stale. What is
cached is the parsed metadata keyed by the content hash: when the hash changes,
the old entry is simply unreachable (a new key), which is invalidation by
construction rather than by bookkeeping. Explicit `invalidate`/`prune` exist
for hygiene. Hit/miss counters feed the orchestrator's measured context stats.

The cache is deliberately separate from task state (task_state.py) and holds
nothing user-provided or confidential - only hashes, sizes and estimates of
repository skill files.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SCHEMA = "skill-cache-entry"


def token_estimate(text):
    return max(1, round(len(text) / 4))


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


class SkillCache:
    def __init__(self, directory=None):
        self.directory = directory or os.path.join(tempfile.gettempdir(), "awesome-skills-cache")
        os.makedirs(self.directory, exist_ok=True)
        # Counters persist with the cache directory, so a task reports the hit
        # rate of its own workspace rather than of a process instance.
        self._stats_path = os.path.join(self.directory, "stats.json")
        try:
            with open(self._stats_path, encoding="utf-8") as handle:
                stored = json.load(handle)
        except (OSError, json.JSONDecodeError):
            stored = {}
        self.hits = int(stored.get("hits", 0))
        self.misses = int(stored.get("misses", 0))

    def _record(self, hit):
        if hit:
            self.hits += 1
        else:
            self.misses += 1
        tmp = self._stats_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump({"hits": self.hits, "misses": self.misses}, handle)
        os.replace(tmp, self._stats_path)

    def _entry_path(self, sha):
        return os.path.join(self.directory, "%s.json" % sha)

    def get(self, path):
        """Read the file fresh, hash it, and serve parsed metadata from the cache."""
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        sha = sha256_of(path)
        entry_path = self._entry_path(sha)
        if os.path.isfile(entry_path):
            with open(entry_path, encoding="utf-8") as handle:
                entry = json.load(handle)
            if entry.get("schema") == SCHEMA and entry.get("sha256") == sha:
                self._record(True)
                return dict(entry, content=text), True
        entry = {"schema": SCHEMA, "sha256": sha, "path": os.path.abspath(path),
                 "bytes": os.path.getsize(path), "tokens_est": token_estimate(text),
                 "cached_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        with open(entry_path, "w", encoding="utf-8") as handle:
            json.dump(entry, handle, indent=2)
        self._record(False)
        return dict(entry, content=text), False

    def invalidate(self, path):
        """Drop the cached entry for a path's current content, if any."""
        if not os.path.isfile(path):
            return False
        entry_path = self._entry_path(sha256_of(path))
        if os.path.isfile(entry_path):
            os.unlink(entry_path)
            return True
        return False

    def prune(self):
        """Remove entries whose files are gone or whose hashes no longer exist on disk."""
        removed = 0
        for name in os.listdir(self.directory):
            entry_path = os.path.join(self.directory, name)
            if not name.endswith(".json") or name == "stats.json":
                continue
            try:
                with open(entry_path, encoding="utf-8") as handle:
                    entry = json.load(handle)
            except (OSError, json.JSONDecodeError):
                os.unlink(entry_path)
                removed += 1
                continue
            source = entry.get("path", "")
            if not source or not os.path.isfile(source) or sha256_of(source) != entry.get("sha256"):
                os.unlink(entry_path)
                removed += 1
        return removed

    def stats(self):
        total = self.hits + self.misses
        return {"hits": self.hits, "misses": self.misses,
                "hit_rate": round(self.hits / total, 3) if total else 0.0}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", help="cache directory (default: system temp)")
    ap.add_argument("paths", nargs="+", help="files to cache-check")
    args = ap.parse_args(argv)
    cache = SkillCache(args.dir)
    for path in args.paths:
        entry, from_cache = cache.get(path)
        print("%-60s %s  %5d tok  sha=%s…"
              % (os.path.relpath(path), "cached" if from_cache else "fresh",
                 entry["tokens_est"], entry["sha256"][:12]))
    print(json.dumps(cache.stats()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
