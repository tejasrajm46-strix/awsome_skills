---
name: smart-poster-designer
description: "Create or redesign poster, flyer, infographic, event graphic, launch visual, social graphic, and print one-sheets as PNG/JPG/PDF. When the user provides a design/template/reference image or file and asks to reuse its style, layout, background, or look, enter Template Reference Mode: inspect the source, reproduce its background and visual design as closely as practical, then replace the source text and subject imagery with the new brief while preserving the reference's hierarchy and composition. Use for template-based redesigns even when the user says 'copy this design' or 'same background, change the content'. Never overwrite the source template."
license: MIT
compatibility: Node 18+ for the bundled HTML composition/render scripts; Chrome/Chromium for PNG/PDF rendering; ImageMagick or macOS sips for JPG conversion. The design and QA workflow can also be performed in an existing image/layout tool when the bundled engine is unavailable.
---

# Smart Poster Designer

Create a deliberate, finished poster—not a filled-in template. For an ordinary brief, define a design point of view and build an original composition. For a supplied template/reference, **follow Template Reference Mode below**: match the user's chosen background, visual structure, palette, typography character, and image treatment, while replacing all requested content. The source is a visual guide, not a content source to copy blindly.

Nothing appears without purpose. Preserve the hierarchy and distinctive visual cues the user wants; do not preserve obsolete copy, logos, or inaccurate details. Never claim a pixel-perfect copy unless the actual source design was edited and compared at rendered size.

## Shared research and assets

When external facts, images, tables or a website's visual style are needed, read
[`references/shared-scraping.md`](references/shared-scraping.md), which connects
this skill to `ultimate-scrape-skill`. User-supplied assets remain first choice.
Skip scraping when the task only uses local content.

## Choose the workflow

### Template Reference Mode (priority when a reference file is supplied)

1. **Preserve and inspect the original.** Identify its file type, page/canvas dimensions, aspect ratio, resolution, bleed, intended output and layers if available. Never edit the only source file. For a native editable source (PSD, AI, SVG, PPTX, DOCX, etc.), use a copy of the source and preserve its layers/elements whenever feasible. For a flattened PNG/JPG/PDF, treat it as a background/reference image, not editable source.
2. **Inventory what must remain versus change.** Create a concise map:
   - **Keep:** background artwork/texture, color palette, layout zones, visual rhythm, alignment, type hierarchy, borders/frames, decorative elements explicitly part of the template.
   - **Replace:** title, body copy, names, dates, prices, CTA, logos, photos/subject art, QR code and other content the brief changes.
   - **Ask/flag:** unknown facts, brand marks, a background containing old text, or an asset that cannot be cleanly separated. Do not invent missing event details.
3. **Analyze the design at full canvas.** Record the aspect ratio, grid/margins, dominant/background/support colors, large shapes, image crops/focal points, text zones, type scale/case/alignment, contrast, and which marks are background versus content. Inspect at least one full-size view and zoom into any embedded small print. For PDFs, render pages to images and extract text separately; for raster images, use dimensions/color sampling/OCR plus visual inspection.
4. **Choose the closest preservation method:**
   - **Editable layered/native source:** duplicate it, replace only requested text/images, retain the background/layers/effects/layout, and keep original objects editable.
   - **Flattened source with clean empty background:** use the image as the background verbatim; place replacement elements in the original zones. Match crop/fit exactly and cover old content only with a visually faithful background reconstruction (sample color/texture, clone or regenerate the missing patch) rather than an obvious solid rectangle.
   - **Flattened source with old text/art baked into a busy background:** reconstruct the background locally using a compatible patch, inpainting, carefully cropped nearby texture, or original assets. Do not leave ghost text or blur patches. If a high-fidelity clean replacement is impossible, state the limitation and ask whether the user accepts a close remake rather than pretending the text is editable.
   - **Template is the exact artwork to retain:** keep it untouched as a flattened background and place all replacement text/subject imagery above it. Confirm it contains no unwanted baked-in source copy.
5. **Match the design—not the old wording.** Preserve the visual roles and approximate geometry: title position/scale/line count, secondary-copy zones, detail grid, image bounds/crop, margins, palette, effects, texture and negative space. Fit new copy by editing wording or reflowing inside the same design system; never shrink below comfortable legibility just to force a long paragraph into a headline slot. If content volume changes substantially, adapt the grid while keeping the recognizable design language.
6. **Create a replacement map** before composition (old region → new content → target bounds → typography/treatment). Keep all user-provided copy accurate. Do not copy factual claims, personal details, QR destinations or logos from a reference unless the user explicitly wants those carried over.
7. **Compose, render and compare.** Put the source and new render side-by-side at the same scale. Check the background continuity, element positions, colors, crop, hierarchy and text replacements. Render at a review scale first; revise; then export requested full-resolution PNG/JPG/PDF and print bleed/crop marks if required.
8. **Deliver clearly.** State which aspects were preserved, what content/assets were replaced, any baked-in source content/background reconstruction, export dimensions, and the visual QA actually performed. Keep the reference intact.

### Original Design Mode (no supplied template/reference)

1. Read the brief and infer sensible choices; ask one focused question only when a missing real fact (name/date/venue/price/CTA) would make the result wrong. Use placeholders rather than invented details.
2. Classify category, audience, purpose, channel and text density (`minimal`, `standard`, `rich`). Decide whether an image is necessary and what it should prove.
3. Write a short named direction and concise design rationale. Pick a content-specific palette, typographic pairing, grid and composition; use [`references/design-system.md`](references/design-system.md). Do not imitate a particular reference's exact composition without authorization.
4. Separate content from visual tokens so an iteration changes only the requested variable.
5. Compose with real margins and a coherent grid. Whitespace is intentional; remove decoration that carries no message. Keep text contrast strong, typography readable, artwork correctly licensed and images at sufficient resolution.
6. Render, visually inspect, run measured QA if available, repair blockers/major issues, and export only after review.

## Bundled engine (optional but reproducible)

Check prerequisites first:

```bash
node scripts/check_env.mjs
```

Compose a design and text separately:

```bash
node scripts/compose.mjs --dna design/dna.json --content design/content.json --out out/poster.html
node scripts/render.mjs --html out/poster.html --out out/poster --preview --formats png
node scripts/qa.mjs --html out/poster.html --report out/qa-report.json
```

For a flattened raster template that is already a clean background, retain the pixels and place replacement copy by measured percentage-based zones:

```bash
node scripts/compose.mjs --dna design/dna.json --content design/content.json --template assets/template-background.png --out out/replacement.html
```

Each replacement region can specify `x`, `y`, `w`, `h` as percentages of the template, plus `text`, `size` (percent of canvas height), `color`, `weight`, `align`, and a meaningful `role`. To cover obsolete content, specify `cover: true`. Use a pixel-sampled background patch where suitable via `patchX` and `patchY` source-position percentages (source dimensions are preserved). Without those coordinates, `cover` uses a solid patch color; it will not remove text invisibly from a complex background. Inspect every patch at full resolution and confirm the old copy is fully concealed.

Run static checks, then visually inspect the rendered output:

```bash
node scripts/qa.mjs --html out/replacement.html --report out/qa-report.json
```

After looking at the preview and repairing blockers/major issues, export full-size PNG/PDF; JPG requires ImageMagick or macOS `sips`:

```bash
node scripts/render.mjs --html out/replacement.html --out out/poster --formats png,pdf
```

Use system fonts when offline. If Chrome is unavailable, use the user's design application or another available local renderer; do not claim the full-resolution rendering or pixel QA ran when it did not. Read [`references/template-reference-mode.md`](references/template-reference-mode.md) for template reuse and [`references/design-system.md`](references/design-system.md) for original poster design.

## Image use and rights

1. User-supplied assets have priority; do not crop away important subjects or silently replace them.
2. Prefer assets with a verified license and record source/credit as required.
3. Generated illustration is useful where a literal photo adds nothing; do not present it as a photograph or real person.
4. Never imply a real person's endorsement, invent a QR target, reproduce a third-party logo without permission, or copy a template's original branding/content as though it were user's.
5. Download sourced images to the project for reproducible renders; avoid hot-linked final files.

## QA and delivery rules

- Check content accuracy first, then canvas and crop, containment/overlap, hierarchy, contrast, spacing, asset loading/resolution and export integrity.
- Rendered pixels matter: a JSON/CSS check cannot prove that baked-in text was erased, a background patch matches, or the final poster reads well.
- For print, confirm final physical size, DPI, bleed, trim and safe area against the printer's specification; do not infer exact print requirements.
- For an existing template, explicitly compare the final render to the reference. Confirm only requested regions changed; note any unreconstructable background or font substitution.
- Don't present automated design scores as an objective grade. Report concrete defects and actual verification.
