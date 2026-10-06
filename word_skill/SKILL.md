---
name: word-generator
description: "Write, read and edit Microsoft Word documents (.docx, .dotx): reports, briefs, proposals, letters, handouts and document reviews, built from notes, research, an outline or a JSON spec. Use it to create a new Word file or to inspect and carefully edit an existing one. Editing a DOCX or template needs package-aware preservation; the bundled builder creates new documents and is not a lossless template round-trip."
license: MIT
compatibility: Python 3.8+ with python-docx. Word or LibreOffice is optional and only used to review rendered pagination; structural checks cannot certify how a page looks.
version: v3.0.0
---

# Word Generator

Ship a real, editable DOCX, not Markdown renamed to `.docx`. Text, headings and
tables stay editable; embed images only where the content needs a visual.

The builder writes new documents from a content spec. Given an existing DOCX or
DOTX, run `scripts/inspect_docx.py` and read
[`references/ooxml-review.md`](references/ooxml-review.md). Keep the source, its
revisions, comments and anything you do not fully understand. Prefer targeted
OOXML edits over rebuilding: regenerating a document to change one paragraph
discards everything else the author put into it.

## Shared research and assets

For outside facts, images, tables or a website's style, read
[`references/shared-scraping.md`](references/shared-scraping.md), which wires this
skill to `ultimate-scrape-skill`. Local-only work needs none of it.

## Workflow

1. Read what you were given. Settle audience, purpose, length and exact output
   path, and note whether an existing source file must come back untouched. For a
   thin brief, default a science explainer to a general audience, A4, installed
   fonts and short sections.
2. Check dependencies, ask before installing or running scripts if the host
   expects that, and prefer a project-local install.
3. **Research enough to be right.** Write 3-6 questions, search them in parallel,
   read up to five authoritative pages, and keep only the facts the brief uses in
   one register: title, URL, access date and supported claims. Stop once every
   claim has support; high-stakes claims deserve wider coverage.
4. Reach for the user's own figures first. For images inside a companion PPTX or
   DOCX, `scripts/extract_office_assets.py` builds a deduplicated shortlist and
   contact sheet offline; pick from it, then name the paths in the spec. For web
   images, preview before downloading, deduplicate, and keep creator, source,
   license and attribution beside each kept file.
5. Decide the argument, then one restrained design system: semantic headings, 11pt
   body, ~1.15 line spacing, strong contrast, generous margins, captions and alt
   text describing the message. Never let colour carry meaning alone.
   `references/design-rules.md` covers editorial QA.
6. Write a JSON spec and run:
   ```bash
   python <skill-path>/scripts/build_doc.py report.json -o report.docx
   python <skill-path>/scripts/validate_doc.py report.docx --strict --json
   ```
7. Render the saved DOCX if Word or LibreOffice is available. Read every page for
   clipped text, orphan headings, widows, blank spillover pages, split tables,
   small type and dead whitespace, then fix and render again. If nothing can
   render it, say pagination and appearance are unverified.
8. Reopen the file and validate its structure. Report a page count only when you
   rendered it, list the checks you ran, and say how much of the source you covered.

## JSON spec

Image paths are relative to the JSON file. API callers pass `asset_root` explicitly.
Unknown block types and malformed tables fail rather than silently disappearing.

```json
{
  "title": "Human Evolution",
  "subtitle": "Evidence, diversity and shared origins",
  "author": "",
  "meta": "Science brief | Sources checked 1 October 2026",
  "running_title": "Human evolution | Evidence brief",
  "footer": "General-audience science brief",
  "theme": {"primary": "163D38", "accent": "176B60", "font": "Calibri"},
  "sections": [
    {"heading": "The central idea", "blocks": [
      {"type": "paragraph", "text": "A sourced claim [1] with **inline bold**."},
      {"type": "bullets", "items": ["First point", "Second point"]},
      {"type": "callout", "text": "**Remember:** evolution is not a ladder."}
    ]},
    {"heading": "Evidence", "page_break": true, "blocks": [
      {"type": "image", "path": "assets/figure.png", "width": 6.7,
       "alt": "Describe the message and relationships, not just 'diagram'.",
       "caption": "Figure 1. Conceptual illustration; not to scale. Source [1]."},
      {"type": "table", "headers": ["Evidence", "Limit"],
       "rows": [["Fossils", "Incomplete record"]]}
    ]},
    {"heading": "Sources", "blocks": [
      {"type": "references", "items": [
        {"id": "1", "title": "Verified source title", "url": "https://example.org",
         "note": "Accessed 1 October 2026; supports the central claim."}
      ]}
    ]}
  ]
}
```

Supported blocks: `paragraph` (default), `bullets`, `callout`, `image`, `table`,
`references`. Sections have `heading`, `blocks`, optional `page_break`.
Theme keys: `primary`, `accent`, `text`, `muted`, `panel`, `font`.
Tables repeat their header and stop rows splitting, but a huge row can still
outgrow a page: shorten it or split the table and render again. Image width is
capped to the text region; height and pagination need a render. Links accept
HTTP(S) only, and a well-formed link can still point at nothing.

## Existing documents and review features

- `python-docx` cannot faithfully edit every Word feature and has no standard API
  for tracked changes or anchored comments. Do not fake redlining with styled text
  or leave orphaned comment parts.
- Real insertions and deletions use `<w:ins>` / `<w:del>` with author, date and
  IDs; deleted text uses `<w:delText>`. Comments need their parts plus range and
  reference markers. When revisions matter, check the accepted and rejected views.
- Preserve what is out of scope: styles, numbering, headers and footers, bookmarks,
  hyperlinks, fields, section breaks, images, relationships, comments, revisions.
  Editing usually invalidates a digital signature; keep the source and say so.
- For a dependency-free package inventory, run
  `python scripts/inspect_docx.py input.docx --json`. It is not an OOXML
  validator and it does not render pages.
- Follow [`references/design-rules.md`](references/design-rules.md) for pagination,
  accessibility, source, table and image QA.

## Ownership and checks

- `scripts/build_doc.py`: spec validation and document formatting.
- `scripts/validate_doc.py`: reopens the saved package independently.
- `tests/test_doc_rules.py`: assert-based regression checks; run them with Python.
- `evals/evals.json`: realistic tasks split into a selection set that tunes this
  guide and a held-out set that stays untouched.
- [`references/skill-evolution.md`](references/skill-evolution.md): how to change
  this guide. `SKILL.md` is trained text here; edits are scored against the
  contract and land only on strict improvement.

Pair with `pptx-generator` from one source register and the same image files,
adjusting depth per medium instead of pasting the report onto slides. Never edit
the user's template or source file in place.

<!-- SLOW_UPDATE_START -->
## Rules that survived every revision

Each earned its place by breaking a real document when missing. Edit patches may
not rewrite them.

- **Render before claiming a page count.** It comes from Word or LibreOffice, never from an estimate; "pagination unverified" is a correct answer.
- **Rebuilding is not editing.** A regenerated DOCX loses tracked changes, comments, numbering, fields and section breaks.
- **Never invent a source, owner, metric or date.** Leave it out or ask; a confident table of made-up numbers is the worst thing this skill can produce.
- **Alt text describes the message.** "Chart" is not alt text, and neither is the caption with "Figure 1" removed.
- **One source register per deliverable.** A report and its deck read the same sources and files.
<!-- SLOW_UPDATE_END -->

<!-- APPENDIX_START -->
- Name the checks that actually ran; never imply a render you did not perform.
- Keep the user's source file, and never save over it.
- A DOCX claim needs a DOCX: validate the saved package, not the spec.
<!-- APPENDIX_END -->
