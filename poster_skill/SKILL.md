---
name: smart-poster-designer
description: "Design posters, flyers, infographics, event graphics, launch visuals, social graphics and print one-sheets as PNG/JPG/PDF. When the user supplies a design, template or reference image and wants its style, layout, background or look reused, use Template Reference Mode: study the source, rebuild its background and visual language, then swap in the new text and imagery while keeping the reference's hierarchy. Use it for template redesigns even when the user says 'copy this design' or 'same background, change the content'. Never overwrite the source template."
license: MIT
compatibility: Node 18+ for the bundled compose/render scripts; Chrome or Chromium for PNG/PDF; ImageMagick or macOS sips for JPG. Any image or layout tool you already have also works.
version: v3.0.0
---

# Smart Poster Designer

Give the poster a point of view instead of filling in a template. A supplied
template or reference means **Template Reference Mode**: match the background,
structure, palette, type character and image treatment the user chose, then
replace the content. A reference is a visual guide, not copy to reuse.

Keep the cues the user wants, and drop obsolete copy and stale logos. Call it a
pixel-perfect match only after editing the real source and comparing both at the
same rendered size.

## Shared research and assets

For outside facts, images, tables or a site's visual style, read
[`references/shared-scraping.md`](references/shared-scraping.md), which connects
this skill to `ultimate-scrape-skill`. User assets come first; skip searching for
local-only work.

## Choose the workflow

### Template Reference Mode (whenever a reference file is supplied)

1. **Keep the original and study it.** Record file type, canvas size, aspect
   ratio, resolution, bleed, output target and layers. Never edit the only source
   file: copy a native source (PSD, AI, SVG, PPTX, DOCX) with its layers intact.
   A flattened PNG/JPG/PDF is a background image, not editable source.
2. **Write the keep/replace map first.**
   - **Keep:** background and texture, palette, layout zones, rhythm, alignment,
     type hierarchy, frames, the template's own decoration.
   - **Replace:** title, body copy, names, dates, prices, CTA, logos, photos,
     subject art, QR code - whatever the brief changes.
   - **Flag:** unknown facts, brand marks, baked-in old text, and anything you
     cannot separate cleanly. Never invent a missing event detail.
3. **Read the design at full canvas.** Record aspect ratio, grid, margins,
   dominant and support colours, shapes, crops, focal points, text zones, type
   scale and case, contrast, and which marks are background versus content. View
   it full size, then zoom into small print. For PDFs, render pages and pull text
   separately; for rasters, use dimensions, colour sampling and OCR.
4. **Pick the cheapest preservation method that holds:** edit a layered source,
   place copy over a clean flattened background, reconstruct a background that
   has text baked into it, or keep the whole template as artwork underneath. Each
   path has a full procedure in
   [`references/template-reference-mode.md`](references/template-reference-mode.md) -
   read it before you composite. Never cover old copy with a flat box or a blur
   and call it gone, and say so if a clean reconstruction is impossible.
5. **Match the design, not the old wording.** Hold the visual roles and roughly
   the same geometry: title position, scale and line count, secondary-copy zones,
   detail grid, image bounds and crop, margins, palette, effects, texture,
   negative space. Fit new copy by editing words or reflowing inside that system.
   Never shrink type below comfortable legibility to force a paragraph into a
   headline; if the volume really changes, adapt the grid.
6. **Plan the replacement map:** old region, new content, target bounds,
   typography, treatment. Keep user copy accurate, and do not carry over claims,
   personal details, QR destinations or logos unless the user asks.
7. **Compose, render, compare.** Put source and render side by side at the same
   scale, and check background continuity, positions, colour, crop, hierarchy and
   the text swaps. Proof at review size, revise, then export the requested
   full-resolution PNG/JPG/PDF, with bleed and crop marks if the printer asked.
8. **Hand it over.** Report what you kept, what you replaced, any background you
   reconstructed, the export dimensions, and the visual QA you actually ran.

### Original Design Mode (no template supplied)

1. Read the brief and make sensible calls. Ask one focused question only when a
   missing name, date, venue, price or CTA would make the result wrong, and use a
   placeholder rather than an invented fact.
2. Classify category, audience, purpose, channel and text density (`minimal`,
   `standard`, `rich`). Decide whether an image is needed and what it proves.
3. Choose palette, type pairing, grid and composition that fit this content, and
   name the direction in a line. Use
   [`references/design-system.md`](references/design-system.md). Do not imitate a
   specific reference's composition without permission.
4. Keep content separate from visual tokens, so an iteration changes only the
   variable the user asked about.
5. Compose on a real grid with real margins. Whitespace is intentional; cut
   decoration that carries no message. Keep contrast strong, type readable,
   artwork properly sourced, images at a usable resolution.
6. Render, look at it, run the measured QA if you have it, fix blockers and major
   issues, then export.

## Bundled engine (optional, but reproducible)

```bash
node scripts/check_env.mjs
node scripts/compose.mjs --dna design/dna.json --content design/content.json --out out/poster.html
node scripts/render.mjs --html out/poster.html --out out/poster --preview --formats png
node scripts/qa.mjs --html out/poster.html --report out/qa-report.json
```

For a flattened template that is already a clean background, keep the pixels and
place replacement copy in measured percentage zones:

```bash
node scripts/compose.mjs --dna design/dna.json --content design/content.json --template assets/template-background.png --out out/replacement.html
```

Regions take `x`, `y`, `w`, `h` as percentages of the template, plus `text`,
`size` (percent of canvas height), `color`, `weight`, `align` and `role`.
`cover: true` hides obsolete content; `patchX`/`patchY` sample the background.
Without them, `cover` paints one flat colour that will not erase text from a busy
background. Inspect patches at full resolution.

```bash
node scripts/qa.mjs --html out/replacement.html --report out/qa-report.json
node scripts/render.mjs --html out/replacement.html --out out/poster --formats png,pdf
```

JPG needs ImageMagick or macOS `sips`; use system fonts offline. Without Chrome,
use another local renderer and say plainly that the render and pixel QA did not
run. See
[`references/template-reference-mode.md`](references/template-reference-mode.md).

## Image use and rights

1. User assets come first. Do not crop away a subject they care about.
2. Prefer assets with a clear license, and credit them the way it asks.
3. Generated illustration is fine where a photo adds nothing; do not pass it off
   as a photograph of a real thing or person.
4. Never imply a real person endorses something, invent a QR destination,
   reproduce a third party's logo without permission, or reuse a template's
   branding as the user's.
5. Download sourced images into the project so renders stay reproducible.

## QA and delivery rules

- Check content accuracy first, then canvas and crop, containment and overlap,
  hierarchy, contrast, spacing, asset loading, resolution, export integrity.
- Only rendered pixels prove that a patch hides baked-in text, that a background
  patch matches, or that the poster reads well.
- For print, confirm size, DPI, bleed, trim and safe area against the printer's
  spec rather than guessing.
- For a supplied template, compare the final render against the reference and
  confirm only the requested regions changed. Note any background you could not
  reconstruct, and any font substitution.
- Automated design scores are not a grade. Report concrete defects and the checks
  you actually ran.

Editing this guide? Read
[`references/skill-evolution.md`](references/skill-evolution.md) first.

<!-- SLOW_UPDATE_START -->
## Rules that survived every revision

Distilled across many posters. Ordinary edits do not rewrite these; only an
epoch-level slow update does.

- **Never edit the only source file.** Copy it and work on the copy.
- **A flattened reference is a picture, not editable source.** Match it, place
  new content over it, and say what you could not reconstruct.
- **No ghost text.** Sample the background and rebuild the patch; a flat box over
  old copy reads as a mistake at print size.
- **Never invent a fact to fill a slot.** Name, date, venue, price, CTA and QR
  destination come from the user or appear as visible placeholders.
- **Look at the render before you export.** Structural checks cannot see a
  smudged patch or a bad crop.
- **Report what you checked.** No renderer means no pixel QA, and the delivery
  note says so.
<!-- SLOW_UPDATE_END -->

<!-- APPENDIX_START -->
Read this file before compositing, not after: keep the reference untouched, keep
one replace map for the whole job, and finish by looking at the exported pixels.
<!-- APPENDIX_END -->
