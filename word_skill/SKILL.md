---
name: word-generator
description: Create, improve, or rebuild professional editable Microsoft Word documents (.docx), reports, research briefs, illustrated explainers, proposals, handouts, and documents derived from notes or presentations. Use whenever the user asks for a Word file, DOCX, polished report, or a document with headings, tables, citations, and images, even if they do not mention Python. Use the bundled builder before hand-writing document code. Do not use for slide-only tasks, spreadsheets, or plain chat answers.
license: MIT
compatibility: Python 3.8+ and python-docx. Word or LibreOffice is optional for rendered pagination review; structural checks alone cannot certify appearance.
---

# Word Generator

Deliver a genuine editable DOCX, not Markdown renamed as Word. Keep text, headings,
and tables editable; embed images only for visuals. Do not promise perfection.

## Workflow

1. Read the supplied material. Determine audience, purpose, length, output path,
   and whether an existing file/template must be preserved. Default a science
   explainer to a general audience, A4, installed fonts, and concise sections.
2. Inspect available dependencies. Obtain permission before installing anything
   or running scripts when the host requires it. Prefer a project-local install.
3. Establish a source register for factual work: numbered IDs, real titles,
   URLs, access date, and which claims each supports. Read the sources. Mark
   disputed relationships, estimates, and conceptual diagrams honestly.
4. Plan the argument and one restrained design system. Use semantic headings,
   11pt body text, approximately 1.15 line spacing, high contrast, generous
   margins, captions and descriptive image alt text. Never encode meaning by
   colour alone. Read `references/design-rules.md` for editorial QA.
5. Write a JSON spec and run:
   ```bash
   python <skill-path>/scripts/build_doc.py report.json -o report.docx
   python <skill-path>/scripts/validate_doc.py report.docx --strict --json
   ```
6. Render the saved DOCX with installed Word or LibreOffice if available. Review
   every page for clipped images, orphan headings, widows, blank spillover pages,
   table splits, legibility, and excessive whitespace. Fix the spec and rebuild.
   Otherwise say explicitly that pagination and appearance remain unverified.
7. Deliver the document link, page count only if rendered, source coverage, and
   exact checks performed. Include a PDF reading copy when requested or useful.

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

## Ownership and checks

- `scripts/build_doc.py`: spec validation and document formatting.
- `scripts/validate_doc.py`: independently reopens the saved package.
- `tests/test_doc_rules.py`: assert-based regression checks; run with Python.
- `evals/evals.json`: realistic skill-level tasks for human evaluation.

When pairing with `pptx-generator`, maintain one source register and common
visual assets. Adapt the detail to each medium; do not paste the entire report
onto slides. Do not modify the source template or user file in place.
