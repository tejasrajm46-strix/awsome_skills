# Shared visual production framework

## 1. Source

Define the audience, output format, canvas, claim coverage and image purpose.
Prefer supplied figures. Review PPT reference sheets before choosing its design.
Research only missing facts; share one numbered register across deliverables.

## 2. Filter

Collect a small candidate set; deduplicate URLs and downloaded bytes. Check real
image format, dimensions, relevance, watermarks, source context and reuse rights.
A file's extension or successful HTTP response does not prove it is an image.

## 3. Select

Open the contact sheet and inspect shortlisted images individually. Reject visual
clutter, misleading imagery, unreadable diagrams and mismatched styles. Keep a
selection manifest with source page, direct URL, creator, license and attribution.
The agent must not call unviewed images reviewed.

## 4. Place

Use explicit selected local paths in the destination specification. Crop rather
than stretch; preserve important subjects and label scientific/conceptual figures.
For PPT, use native editable shapes/charts and the supported measured layouts;
keep zero slide transitions. For Word, use semantic sections and captions. For
posters, preserve the reference's requested visual roles and accurate event copy.
For Excel, data provenance and units matter more than decorative imagery.

## 5. Harmonize

Use one palette, coherent type scale, alignment grid and spacing rhythm. Translate
website tokens to the actual builder schema, checking font availability and
contrast. Do not assume a site's raw palette is an accessible design system.
Keep source-specific restrictions and attributions close to chosen assets.

## 6. Verify

Run saved-artifact checks in the format skill, then render/open and inspect when
possible. PPT/Word structural validators cannot certify pixels or pagination;
Excel package inventory cannot calculate formulas or test macros; PDF inventory
cannot prove secure redaction; poster JSON/CSS checks cannot prove background
repair. Report structural, visual, calculation and security checks separately.

## Format owners

- `ppt_skill`: `build_deck.py`, `validate_deck.py`, local asset extractor and
  visual reference library. Installed name: `pptx-generator`.
- `word_skill`: `build_doc.py`, `validate_doc.py`, `inspect_docx.py` and package-
  aware editing notes. Installed name: `word-generator`.
- `pdf_skill`: PDF operation guidance and `inspect_pdf.py`. Installed name:
  `pdf-processor`.
- `xlsm_skill`: `inspect_workbook.py`, `inspect_xlsm.py`, formula and macro
  preservation guidance. Installed name: `xlsm-processor`.
- `poster_skill`: `compose.mjs`, `qa.mjs`, `render.mjs` and template-reference
  mode. Installed name: `smart-poster-designer`.

Resolve installed paths at runtime. PowerPoint, Word, Excel, LibreOffice,
Chrome/Chromium and other renderers are host capabilities, not bundled binaries.
No author's machine paths, missing auto-layout APIs or platform-specific render
helpers are prerequisites for the shared extraction workflow.
