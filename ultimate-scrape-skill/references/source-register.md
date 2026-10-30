# The shared source register

Every research-driven deliverable in this collection is supposed to satisfy one
rule: **no fact without a source ID**. The register is where that rule becomes a
checkable artifact instead of a promise in prose. One register per brief, read
by every format skill the brief feeds, next to the asset manifest that
`extract_parts.py` writes.

## The file

```json
{
  "schema": "source-register",
  "schema_version": 1,
  "sources": [
    {
      "id": "S1",
      "title": "Grid-scale storage cost survey",
      "url": "https://example.org/reports/storage-2026",
      "source_type": "research",
      "author": "A. Okonkwo",
      "publisher": "Example Energy Institute",
      "published": "2026-03-14",
      "accessed": "2026-10-30",
      "claims": ["C1", "C2"],
      "evidence": "Table 3, cost-per-kWh series 2021-2026",
      "verification": "verified",
      "notes": "Figures cross-checked against the underlying dataset"
    }
  ]
}
```

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Stable source ID; this is what slides, docs and posters cite. |
| `title` | yes | The source's own title, not your summary of it. |
| `url` | yes | Absolute http(s) URL. |
| `source_type` | no | `documentation`, `research`, `government`, `academic`, `standard`, `filing`, `dataset`, `secondary`, `website`, `other`. |
| `author`, `publisher` | no | Only when the source names them. Never guessed. |
| `published` | no | Publication date, YYYY-MM-DD, only when the source states one. |
| `accessed` | yes | The date you read it, YYYY-MM-DD. `add` fills today's date. |
| `claims` | no | Claim IDs (e.g. `C1`, `lithium-price`) this source supports. |
| `evidence` | no | Where in the source the support lives - a section, table, figure. |
| `verification` | yes | `unverified` (default), `verified` or `contradicted`. |
| `notes` | no | Anything the next skill needs to know before relying on it. |

## Rules the validator enforces

- **No unknown fields.** If a fact is not in the schema, it does not get
  invented into it; put it in `notes`.
- **`verified` requires `evidence`.** You cannot mark a source verified without
  naming where in it the claim is supported.
- **One claim, one source.** A claim ID mapped to two sources is an error - the
  register cannot tell the format skills which one to cite.
- **Unique IDs, absolute URLs, ISO dates.**

A discovered URL is not a verified source. Add it with the default
`unverified`, read the page, then re-check and upgrade it only with evidence.

## Usage

```bash
python <helper-path>/scripts/source_register.py new --out work/research/register.json
python <helper-path>/scripts/source_register.py add work/research/register.json \
  --title "Grid-scale storage cost survey" --url https://example.org/reports/storage-2026 \
  --type research --claims C1,C2 --evidence "Table 3"
python <helper-path>/scripts/source_register.py validate work/research/register.json
```

`validate --json` prints `{"ok": ..., "errors": [...], "sources": n}` for
agents that want the result structurally. Exit code is non-zero on any error.

## Cross-referencing a builder spec

`check-spec` compares what a deliverable cites against the register, so the
IDs on slides and in documents are the register's IDs - not a parallel scheme
that drifted on the way into a spec:

```bash
python <helper-path>/scripts/source_register.py check-spec work/research/register.json deck.json
python <helper-path>/scripts/source_register.py check-spec work/research/register.json doc.json --strict
```

It reads citations wherever the builders put them: a Word spec's `references`
blocks (`items[].id`), a deck spec's top-level `sources`, and any slide-level
`sources`/`citations` lists. The rules:

- A cited ID that is not in the register is an error - that is the one-ID-per-
  source contract failing, and it fails the check, not the reader.
- A register entry marked `contradicted` cannot be cited.
- A cited entry still marked `unverified` is a warning by default and an error
  under `--strict`.
- Numeric IDs in a spec match string register IDs (`7` cites `7`), so nothing
  needs to be rewritten just to satisfy a type; the ID itself must match.

The summary also reports how many register claims the deliverable actually
carries, and which register sources went uncited - a register is shared across
deliverables, so uncited sources are information, not a failure.

## Handoff

When a deliverable is built, the format skill cites `id`s from this register
and the register ships beside the outputs, so a reviewer can trace any claim.
A claim with no entry is a claim you cut. The register, the reviewed assets and
the limitations travel together as one
[handoff bundle](handoff-contract.md). Tests live in
`tests/test_source_register.py`, `tests/test_handoff.py` and
`tests/test_security.py`, and run offline.
