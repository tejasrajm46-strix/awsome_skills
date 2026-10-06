---
name: pptx-generator
description: "Build, design, inspect or restyle editable PowerPoint (.pptx) decks, slides, pitch decks and speaker notes from outlines, reports, research or an existing template. Measured layouts, native charts, diagrams, visual reference assets and saved-file validation. Decks ship with no slide transitions. Read this before hand-writing python-pptx code or rebuilding a deck someone gave you."
license: MIT
compatibility: Python 3.8+ with python-pptx and lxml (they install together). Charts are native PPTX charts, so matplotlib is not needed. LibreOffice is optional and only used to render a PDF preview.
version: v3.0.0
---

# PPTX Generator

Turn content into a real, editable `.pptx`. The recipient can retype a number,
restyle a colour or swap a chart type: text, charts and diagrams stay editable,
while imported pictures stay pictures.

Two things break decks here: **text that overflows its shape** and **geometry that
drifts between slides**. The measured grid, the fit estimates and the
saved-package checks catch both, though they do not replace looking at a rendered
slide - font metrics are estimates, and a figure is checked for bounds, not for
whether its labels are readable. Do not call a deck finished without running the
validator: it is the one step that has read the saved bytes.

## Shared research and reference assets

For outside facts, images or a site's look, read
[`references/shared-scraping.md`](references/shared-scraping.md), which wires this
skill to `ultimate-scrape-skill`. Local-only work needs none of it.

Before choosing a visual direction, read [`assets/README.md`](assets/README.md)
and open [`assets/template-sheet.jpg`](assets/template-sheet.jpg) or
[`assets/preview-sheet.jpg`](assets/preview-sheet.jpg), then take hierarchy, grid,
typography and image treatment from what fits. Do not copy unrelated content or
treat a preview as an editable template;
[`assets/credits.json`](assets/credits.json) records where each one came from.

## Workflow

1. **Check the dependencies.** `python -c "import pptx, lxml"` should pass; if not,
   `python -m pip install python-pptx`. `soffice --version` only tells you whether
   a PDF preview is possible.

2. **Working from an existing deck or template? Read
   [`references/template-editing.md`](references/template-editing.md) before you
   pick a build path.** Keep the source, inspect its slides and rendered look, and
   say what can be reused faithfully. `--base` appends slides; it does not replace
   or restyle the ones already there.

3. **Write the argument before the JSON.** Settle the audience, purpose and one
   visual system, then give each slide a single takeaway. A deck is an argument,
   not a document with page breaks. Keep numbered source IDs, and share that
   register plus the chosen images with `word-generator` when you deliver both.

4. **Research enough to be right.** Use the effort policy in
   [`references/shared-scraping.md`](references/shared-scraping.md): a few focused
   questions, primary sources, one register holding title, URL, access date and the
   claims each source supports. Never trade claim checking for speed. Reach for
   supplied and local figures first; for authorised web images, search small
   (about 10 candidates per query) and preview, deduplicate and record creator,
   source page, direct URL and licence before a full download. The step-6
   extractor handles user-supplied PPTX/DOCX files and does not judge relevance,
   so cache this work and a paired Word deliverable will not repeat it.

5. **Write the spec JSON**, one layout per slide, each `title` a claim rather than
   a label. The spec format, every layout and its fields, and the script map are in
   [`references/deck-schema.md`](references/deck-schema.md).

6. **Build it, using the visuals you chose.** Reuse the user's figures, then the
   images from any paired DOCX. For pictures already inside a PPTX or DOCX, run
   the bounded local shortlist tool first: it writes a contact sheet with
   dimensions, SHA-256 deduplication and where each asset is used.
   ```bash
   python scripts/extract_office_assets.py source.pptx --out work/assets --max-assets 12 --spec deck.json
   python <skill-path>/scripts/build_deck.py deck.json -o deck.pptx
   ```
   Open its contact sheet, pick what is relevant, cite what needs citing, and put
   the chosen paths in the spec. It inventories local embedded images only: it
   does not scrape or decide what you may reuse. Add `--base their-template.pptx`
   only for an append-only base.

7. **Keep it transition-free.** No fades, wipes, automatic advances or transition
   notes. With `--base`, the builder strips inherited transitions from the output
   copy and leaves the source alone.

8. **Validate, and read the warnings.**
   ```bash
   python <skill-path>/scripts/validate_deck.py deck.pptx --expect <n> --strict
   ```
   Errors are hard failures: a shape off the slide, overlapping text, a table
   growing past the bottom, an embedded transition. Warnings mean it opens but
   probably looks wrong: text spilling out of its box, an auto-growing table, type
   below 10pt. Overflow means too much content - split the slide or cut words,
   never shrink the font.

9. **Render it and look at every slide**, with installed PowerPoint or
   LibreOffice. Check real wrapping, figure-label size, contrast, clipping,
   whitespace and rhythm, then fix the spec and rebuild. No validator can certify
   that a deck looks good, and you never edit the user's template in place.

10. **Report** the output path, slide count, theme, the zero-transition check, the
    structural result, and whether rendering and visual review actually happened.
    Do not paste the deck back into chat or call unrendered output flawless.

## No slide transitions

Transitions are deliberately unsupported here. The builder removes inherited
`<p:transition>` elements from an output copy, and validation fails if any remain.
Zero transitions is a requirement, not a warning. Never strip them from the user's
original template just to satisfy it.

## Themes and design tokens

Every colour is a token in the spec's `theme` block, so a re-skin is a five-line
edit rather than a hunt through literals; `build_deck.py` ships a light palette
and the deep-ocean tokens the dark layouts use.

- **The font has to exist on the machine that opens the deck.** python-pptx
  cannot embed fonts, so a Google font silently substitutes and the deck renders
  in something you never chose. Prefer `Segoe UI`, `Calibri`, `Arial` or
  `Consolas`, and warn the user before naming a display face.
- **The 12pt floor is real.** The validator flags anything under 10pt except the
  deliberately small footer and citation shapes, marked `chrome:` to stay quiet.

## Rules that are not negotiable

For an existing template or deck, [`references/template-editing.md`](references/template-editing.md)
applies too. Be specific about what you did: appended slides, rebuilt the deck in
the same visual style, or edited the supplied slides in place.

- **Never shrink type below 12pt to make something fit.** Split the slide.
- **Never state a licence or attribution you have not checked at the source.**
  SlidesCarnival templates are CC BY 4.0, so a credit is required.
- **Never invent a citation, statistic, quotation or number.** Research it or
  leave it out, and label a conceptual map as conceptual.
- **Never scrape or script-download** templates from sites that want an account,
  and never work around a paywall. Ask the user for the file.
- **Never claim a chart or feature is present** without the validator confirming it.
- **Always run the validator** before you tell the user the deck is ready.

## Editorial quality and no-library fallback

Read [`references/design-rules.md`](references/design-rules.md) first for the type
scale, the six-bullets-six-words guideline, narrative arcs and chart conventions:
the script gets the geometry right, that file gets the content right. For anything
with real evidence in it, [`references/free-assets.md`](references/free-assets.md)
has licence facts checked at the source and the attribution they require.

If `python-pptx` cannot be installed, read
[`references/fallback.md`](references/fallback.md) before promising an output.

Changing this guide? Read
[`references/skill-evolution.md`](references/skill-evolution.md) first: edits are
scored against a contract and land only on strict improvement.

<!-- SLOW_UPDATE_START -->
## Rules that survived every revision

Distilled across many decks. Ordinary edits do not rewrite these; only a
gate-passing slow update does.

- **The validator is the only thing that has read the file.** A deck that built is
  not a deck that is right.
- **Never shrink text to fit.** Overflow means too much content: split it or cut
  words. The 12pt floor holds in every layout.
- **Zero transitions, always.** The builder strips inherited ones from the output
  copy and the validator rejects survivors.
- **Never invent a number, a quote or a source.** A plausible fabricated statistic
  is the worst thing a deck can carry.
- **A preview is not a template and a download is not a licence.** Record what an
  asset allows before it goes on a slide.
- **Say which checks ran.** A render you did not perform is not a visual review.
<!-- SLOW_UPDATE_END -->

<!-- APPENDIX_START -->
Before you answer: the source is intact, the output is a new path, the validator
ran, the deck has no transitions, and every claim you report is one you verified.
<!-- APPENDIX_END -->
