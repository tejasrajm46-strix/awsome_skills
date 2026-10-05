---
name: word-generator
description: Create professional editable Microsoft Word documents (.docx) from notes, research, outlines or structured JSON; read, extract and inspect existing DOCX/DOTX documents and plan careful template edits. Use for Word reports, briefs, proposals, letters, handouts and document review. Existing-file edits require package-aware preservation; the bundled builder creates new documents, not lossless template round-trips.
license: MIT
compatibility: Python 3.8+ and python-docx. Word or LibreOffice is optional for rendered pagination review; structural checks alone cannot certify appearance.
---

# Word Generator

Deliver a genuine editable DOCX, not Markdown renamed as Word. Keep text, headings,
and tables editable; embed images only for visuals. Do not promise perfection.

The builder creates new documents from content specs. For existing DOCX/DOTX,
first run `scripts/inspect_docx.py` and read
[`references/ooxml-review.md`](references/ooxml-review.md). Preserve the source,
revisions, comments and unsupported parts; use Word automation or targeted OOXML
edits when needed. Do not rebuild an existing file merely to change one paragraph.
There is no separate document skill required by this repository.

## Shared research and assets

When external facts, images, tables or a website's visual style are needed, read
[`references/shared-scraping.md`](references/shared-scraping.md), which connects
this skill to `ultimate-scrape-skill`. Skip scraping for local-only work.

## Workflow

1. Read the supplied content. Determine audience, purpose, length, output path,
   and whether an existing source file should remain unchanged. Default a science
   explainer to a general audience, A4, installed fonts, and concise sections.
2. Inspect available dependencies. Obtain permission before installing anything
   or running scripts when the host requires it. Prefer a project-local install.
3. **Research efficiently.** For routine work, define 3–6 questions, search
   independent topics in parallel, read up to five authoritative pages, and
   capture only facts needed for the brief in one source register. Deduplicate
   URLs/facts and stop when key claims have support; use deeper source coverage
   for disputed/high-stakes topics. Never save time by skipping source checks.
   Record title, URL, access date and supported claims.
4. Reuse user-provided figures before sourcing new ones. For embedded images in
   a companion PPTX/DOCX, the bundled
   `scripts/extract_office_assets.py` creates a bounded, deduplicated shortlist
   and contact sheet without scraping. Select deliberately, then reference
   selected paths explicitly in this spec. For web images, search targeted
   queries, preview/filter thumbnails before full downloads, deduplicate, and
   retain creator/source/licence/attribution metadata for chosen images.
5. Plan the argument and one restrained design system. Use semantic headings,
   11pt body text, approximately 1.15 line spacing, high contrast, generous
   margins, captions and descriptive image alt text. Never encode meaning by
   colour alone. Read `references/design-rules.md` for editorial QA.
6. Write a JSON spec and run:
   ```bash
   python <skill-path>/scripts/build_doc.py report.json -o report.docx
   python <skill-path>/scripts/validate_doc.py report.docx --strict --json
   ```
7. Render the saved DOCX with installed Word or LibreOffice if available. Review
   every page for clipping, orphan headings, widows, blank spillover pages,
   table splits, legibility, and excessive whitespace. Fix and re-render. Otherwise
   say explicitly that pagination and appearance remain unverified.
8. Reopen and validate the generated structure; report page count only if rendered,
   source coverage, and exact checks performed.

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
Tables repeat their header and prevent individual rows from splitting. Large
rows may still exceed a page: shorten them or split the table and render again.
Image width is limited to the text region. Height/pagination needs rendered QA.
Links accept HTTP(S) only. Do not claim sources are verified merely because a
hyperlink is syntactically valid.

## Existing documents and review features

- `python-docx` cannot faithfully edit every Word feature and has no standard API
  for tracked changes or anchored comments. Do not simulate redlining with styled
  text or leave orphan comment parts.
- Actual insertions/deletions use `<w:ins>` / `<w:del>` with author/date/IDs;
  deleted text uses `<w:delText>`. Comments need the related parts and range/reference
  markers. Validate both accepted/rejected views where revisions matter.
- Preserve out-of-scope styles, numbering, headers/footers, bookmarks, hyperlinks,
  fields, section breaks, images, relationships, comments and revision markup. Editing
  may invalidate digital signatures; keep the source and disclose this.
- For careful package inventory without dependencies, run
  `python scripts/inspect_docx.py input.docx --json`. This is not an OOXML schema
  validator or visual page renderer.
- Follow [`references/design-rules.md`](references/design-rules.md) for rendered
  pagination, accessibility, source, table and image QA.

## Ownership and checks

- `scripts/build_doc.py`: spec validation and document formatting.
- `scripts/validate_doc.py`: independently reopens the saved package.
- `tests/test_doc_rules.py`: assert-based regression checks; run with Python.
- `evals/evals.json`: realistic skill-level tasks for human evaluation.

When pairing with `pptx-generator`, maintain one source register and common
visual assets. Adapt the detail to each medium; do not paste the entire report
onto slides. Do not modify the source template or user file in place.
