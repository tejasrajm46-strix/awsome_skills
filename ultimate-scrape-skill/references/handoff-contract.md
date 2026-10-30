# The research handoff contract

One brief, one workspace, one predictable bundle. When a research task feeds a
format skill, the handoff is a single `handoff.json` beside the artifacts it
names - not a chat summary the next skill has to re-decide from.

## The workspace layout

```text
work/research/
  register.json      source register (source_register.py) - claims and sources
  manifest.json      extraction manifest (extract_parts.py) - candidates and data
  selection.json     asset review (select_assets.py) - approved and rejected
  data.json          page data, when the data part ran
  theme.json         style tokens, when the template part ran
  handoff.json       the bundle (handoff.py) - the one file a format skill reads
```

## The bundle

```json
{
  "schema": "research-handoff",
  "schema_version": 1,
  "created": "2026-10-30",
  "brief": "storage-cost deck plus word brief",
  "register": {"path": "register.json", "sources": 2, "claims": 3},
  "assets": {"manifest": "manifest.json", "selection": "selection.json",
             "candidates": 2},
  "data": {"path": "data.json"},
  "theme": {"path": "theme.json"},
  "limitations": ["JavaScript-only pricing page not fetched; figures from the survey PDF"]
}
```

## What validation enforces

`python <helper-path>/scripts/handoff.py validate work/research/handoff.json`
fails - with the exact file - unless all of these hold:

- The register validates against its schema: every claim maps to one source,
  `verified` sources carry recorded evidence, no invented metadata.
- The asset manifest exists, and **every candidate has a review decision**:
  approved with its intended use and license, or rejected with a reason.
  Approved files must still hash to the bytes that were decided on.
- The theme and data paths, when declared, exist.
- `limitations` is a nonempty list. When there genuinely are none, say
  `"none identified"` - silence is not honesty.

A bundle that validates can be consumed without re-deciding anything. One that
does not is sent back to research rather than passed forward with gaps.

## Reuse across deliverables

Two deliverables from one brief validate against the same bundle. Both specs
are cross-referenced with `source_register.py check-spec` against the same
register, so slide citations and document citations use identical IDs, and
both output manifests can point at the same `sources_register` via
`tools/output_manifest.py new --register ...`. Nothing is researched or
downloaded twice; nothing is approved twice under different names.
