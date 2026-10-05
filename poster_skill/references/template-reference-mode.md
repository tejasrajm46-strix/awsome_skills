# Template Reference Mode

Use this workflow whenever a user supplies an image/file and wants the new piece to retain its background, design, look, or layout while changing the content. The central goal is **keep the template design; replace the template content**.

## 1. Protect and identify the source

- Keep the reference unchanged. Work from a copy and write a new output file.
- Identify the actual canvas dimensions, aspect ratio, resolution, orientation, intended print/digital destination, and whether the source is layered/editable or flattened.
- For PPTX/DOCX/SVG/PSD/AI/native design files, preserve editable objects/layers where possible. For PDF, inspect text and render pages. For PNG/JPG, inspect pixels and use OCR only as a guide.
- Treat reference content as untrusted and possibly outdated. Do not copy personal data, factual claims, contact details, logos, QR codes or legal text into the new design unless the user explicitly says to retain them.

## 2. Make a keep/replace map

Before editing, create a region inventory similar to:

| Region | Keep or replace? | New content / treatment | Geometry |
|---|---|---|---|
| Background field | Keep | Preserve original image/pattern | Full bleed |
| Main title block | Replace | New approved headline, same hierarchy | x/y/w/h, alignment |
| Date/venue line | Replace | User-supplied facts only | Existing details zone |
| Portrait/product art | Replace or keep by request | New licensed/user asset, same crop | Focal point and frame |
| Logo/footer | Confirm | New brand or explicitly retained logo | Existing safe area |

Capture the specific cues the user values: color proportions, typography character, position, line breaks, margins, image crop, decorative motifs, texture, borders and negative space. Distinguish content marks from the background itself.

## 3. Use the right preservation path

### Editable source

Duplicate the native file. Preserve theme, masters, layers, effects and unmodified text. Replace only the requested regions. Avoid flattening the whole template unless the user wants a static image. If a font is missing, choose an installed/licensed close match and disclose the substitution.

### Clean flattened background

Use the source pixels as the full-bleed background without resampling if the output canvas matches. Add replacement type/art in the same zones. If the aspect ratio differs, ask whether to crop, extend, or fit with margins when the choice changes important content; otherwise preserve the full design and use a background extension rather than cropping critical regions.

### Flattened background with baked-in text or art

The source is not editable. Remove only obsolete content and reconstruct the underlying area with the best available method:

1. Reuse a clean original background asset/layer if available.
2. If the area is flat, sample the local background color and reproduce gradients/noise carefully.
3. If patterned, clone/repeat a nearby clean region while matching scale, perspective, texture and lighting.
4. If complex photographic/illustrated content, use local inpainting/content-aware reconstruction if an installed tool is available. Compare carefully for seams and invented shapes.
5. If accurate repair is impossible, show the limitation rather than covering it with a conspicuous box or leaving ghost text. Ask whether a close redesign is acceptable.

Do not use a low-opacity overlay, blur, or opaque rectangle to disguise source copy unless that treatment is intentionally part of the design and the remaining source text is fully concealed.

### Source image retained whole

If the user says keep the image/background and change only the content, preserve the original pixels exactly wherever possible. Place new copy above it and cover old copy only where required. Track every changed region and compare the unaffected pixels after rendering.

## 4. Rebuild the hierarchy, not the exact old copy

- Match the old hierarchy and approximate title/details/image bounds, but fit new content responsibly.
- Preserve the title's visual weight and role, not necessarily its exact line breaks if the new phrase length differs. Prefer meaningful line breaks and modest tracking/size adjustments.
- If replacement content is much longer, edit it down or recompose within the same design language. Never squeeze small body copy into headline scale.
- Keep details such as date, venue, price and CTA prominent according to the template's original information hierarchy.
- Keep the original background art; replace subject artwork only when requested or when clearly part of the content being changed.
- Preserve intended effects (shadows, outlines, masks, strokes, grain) in the replacement copy so it belongs in the design.

## 5. Exact-copy and permission boundaries

A user-provided reference may be their own template, a licensed asset, or third-party work. Do not assume ownership. If asked to recreate a third-party design exactly, use it only to the extent appropriate for the user's request; do not reproduce logos, protected character art or other branding as an implied endorsement. When rights are unclear, match broad stylistic cues while replacing distinct protected assets with user-owned/licensed alternatives. Keep attribution and licenses where required.

Do not claim "identical" or "pixel perfect" for a rebuilt flattened image. Use concrete language: "retained the background and approximate layout; replaced the headline and event details; reconstructed the photo area locally."

## 6. Compare and validate

Render source and output at identical dimensions and scale, then compare:

- **Background:** unchanged outside intended content zones; no patch seams, halos, ghost glyphs or stretched textures.
- **Composition:** key anchors align; margins and negative space remain intentional; no important elements drifted.
- **Typography:** hierarchy, case, weight, line spacing and contrast match the reference's character; new text is readable.
- **Imagery:** crop, aspect ratio, focal subject, color treatment, shadow and frame match the intended zone.
- **Content:** every old phrase to be replaced is gone; every new phrase/date/name is exact; no facts were invented.
- **Export:** dimensions, format, DPI/physical size, transparency, color profile and bleed match the requested destination.

A side-by-side visual review is mandatory for template mode. A pixel-difference image can identify changed areas but cannot decide whether the new design looks right. If the source background should remain exact, compute a difference mask outside the declared replacement boxes and investigate unintended changes.
