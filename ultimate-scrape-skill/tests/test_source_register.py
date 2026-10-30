#!/usr/bin/env python3
"""Offline tests for the shared source register: schema, evidence rule, claim map."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "source_register.py"

BASE_ENTRY = ["--title", "Cost survey", "--url", "https://example.org/survey",
              "--type", "research", "--accessed", "2026-10-30"]


def run(*argv):
    return subprocess.run([sys.executable, str(SCRIPT), *argv],
                          capture_output=True, text=True)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        register = str(Path(tmp) / "register.json")

        result = run("new", "--out", register)
        assert result.returncode == 0, result.stderr
        scaffold = json.loads(Path(register).read_text(encoding="utf-8"))
        assert scaffold["schema"] == "source-register" and scaffold["sources"] == []
        assert run("validate", register).returncode == 0

        # A verified source without evidence is refused.
        result = run("add", register, *BASE_ENTRY, "--id", "S1", "--claims", "C1",
                     "--verification", "verified")
        assert result.returncode == 1 and "verified requires evidence" in result.stdout, result.stdout
        assert json.loads(Path(register).read_text(encoding="utf-8"))["sources"] == [], \
            "a refused entry must not be written"

        # With evidence it lands; accessed defaults to today when omitted.
        result = run("add", register, *BASE_ENTRY, "--id", "S1", "--claims", "C1",
                     "--evidence", "Table 3", "--verification", "verified")
        assert result.returncode == 0, result.stdout
        result = run("add", register, "--title", "Spec page", "--url", "https://example.org/spec",
                     "--claims", "C2")
        assert result.returncode == 0, result.stdout
        sources = json.loads(Path(register).read_text(encoding="utf-8"))["sources"]
        assert sources[1]["id"] == "S2" and sources[1]["verification"] == "unverified"
        assert len(sources[1]["accessed"]) == 10, "accessed must default to an ISO date"
        assert "author" not in sources[1] and "published" not in sources[1], \
            "unknown metadata must stay absent, not invented"

        # The register's own validator rejects the failure modes that matter.
        validator = run("validate", register)
        assert validator.returncode == 0 and "2 claims mapped" in validator.stdout, validator.stdout

        def broken(mutate):
            data = json.loads(Path(register).read_text(encoding="utf-8"))
            mutate(data)
            path = Path(tmp) / "broken.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            return run("validate", str(path))

        def map_claim_twice(data):
            data["sources"][1]["claims"] = ["C1"]
        result = broken(map_claim_twice)
        assert result.returncode == 1 and "claim 'C1' maps to both" in result.stdout, result.stdout

        def duplicate_id(data):
            data["sources"][1]["id"] = "S1"
        result = broken(duplicate_id)
        assert result.returncode == 1 and "duplicate id" in result.stdout, result.stdout

        def invented_field(data):
            data["sources"][0]["impact"] = "high"
        result = broken(invented_field)
        assert result.returncode == 1 and "unknown field(s) impact" in result.stdout, result.stdout

        def guessed_date(data):
            data["sources"][0]["published"] = "spring 2026"
        result = broken(guessed_date)
        assert result.returncode == 1 and "ISO date" in result.stdout, result.stdout

        def bad_url(data):
            data["sources"][0]["url"] = "ftp://example.org/survey"
        result = broken(bad_url)
        assert result.returncode == 1 and "http(s)" in result.stdout, result.stdout

        def unknown_type(data):
            data["sources"][0]["source_type"] = "blog post"
        result = broken(unknown_type)
        assert result.returncode == 1 and "source_type must be one of" in result.stdout, result.stdout

        result = run("validate", register, "--json")
        assert result.returncode == 0
        report = json.loads(result.stdout)
        assert report["ok"] is True and report["sources"] == 2, report

        # check-spec: builder specs must cite register IDs exactly.
        deck_spec = Path(tmp) / "deck.json"
        deck_spec.write_text(json.dumps({
            "title": "Deck", "slides": [{"layout": "title", "title": "T"}],
            "sources": [{"id": "S1", "title": "Cost survey", "url": "https://example.org/survey"}],
        }), encoding="utf-8")
        result = run("check-spec", register, str(deck_spec))
        assert result.returncode == 0 and "deck spec cites 1 of 2" in result.stdout, result.stdout

        word_spec = Path(tmp) / "doc.json"
        word_spec.write_text(json.dumps({
            "title": "Doc",
            "sections": [{"heading": "H", "blocks": [
                {"type": "references", "items": [
                    {"id": "S1", "title": "Cost survey", "url": "https://example.org/survey"}]}]}],
        }), encoding="utf-8")
        result = run("check-spec", register, str(word_spec), "--json")
        assert result.returncode == 0, result.stdout
        cross = json.loads(result.stdout)
        assert cross["kind"] == "word" and cross["cited"] == ["S1"], cross
        assert cross["claims_carried"] == 1 and cross["uncited_sources"] == ["S2"], cross

        # Citing S2 (unverified) warns by default and is fatal under --strict.
        word_spec2 = Path(tmp) / "doc2.json"
        word_spec2.write_text(json.dumps({
            "title": "Doc2",
            "sections": [{"heading": "H", "blocks": [
                {"type": "references", "items": [{"id": "S2", "title": "Spec page",
                                                  "url": "https://example.org/spec"}]}]}],
        }), encoding="utf-8")
        result = run("check-spec", register, str(word_spec2))
        assert result.returncode == 0 and "WARN:" in result.stdout and "unverified" in result.stdout, result.stdout
        result = run("check-spec", register, str(word_spec2), "--strict")
        assert result.returncode == 1 and "unverified" in result.stdout, result.stdout

        # A citation the register does not know about is the ID drift this check exists for.
        stale = Path(tmp) / "stale.json"
        stale.write_text(json.dumps({"title": "T", "slides": [], "sources": [{"id": "1"}]}),
                         encoding="utf-8")
        result = run("check-spec", register, str(stale))
        assert result.returncode == 1 and "cites 1, which is not in the register" in result.stdout, result.stdout

        # A contradicted source cannot be cited at all.
        contradicted = Path(tmp) / "contradicted-register.json"
        data = json.loads(Path(register).read_text(encoding="utf-8"))
        data["sources"][1]["verification"] = "contradicted"
        contradicted.write_text(json.dumps(data), encoding="utf-8")
        result = run("check-spec", contradicted, str(word_spec2))
        assert result.returncode == 1 and "contradicted" in result.stdout, result.stdout

        # Numeric spec IDs match string register IDs: one canonical ID per source.
        numeric = Path(tmp) / "numeric-register.json"
        data["sources"][1]["id"] = "7"
        data["sources"][1]["verification"] = "unverified"
        numeric.write_text(json.dumps(data), encoding="utf-8")
        numeric_spec = Path(tmp) / "numeric-spec.json"
        numeric_spec.write_text(json.dumps({"title": "T", "slides": [], "sources": [{"id": 7}]}),
                                encoding="utf-8")
        result = run("check-spec", numeric, str(numeric_spec))
        assert result.returncode == 0 and "not in the register" not in result.stdout, result.stdout
        assert "cites 7, which is still unverified" in result.stdout, result.stdout

    print("PASS: source register schema, evidence rule, one-claim-one-source, "
          "no invented metadata and spec cross-reference")


if __name__ == "__main__":
    main()
