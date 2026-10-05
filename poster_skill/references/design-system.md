# Poster design system

Use this when no user template defines the design. With a supplied template, follow `template-reference-mode.md` first and let the source design's visual system take precedence.

## Establish a direction before styling

Write down the audience, purpose, venue/platform, information density, dominant message and one visual idea. Give the direction a short name and rationale. Every color, shape, image, type style and effect should support that direction; whitespace does not need to be filled.

Separate copy from visual tokens. Keep a content inventory (headline, supporting line, verified details, CTA, credit) apart from canvas/grid, palette, typography, image treatment and layout. This makes revisions controlled: changing date or palette should not accidentally alter composition.

For references, extract broad design cues (hierarchy, spacing, palette logic, image treatment and material), not a traced arrangement. Check reference rights and do not use third-party logos, characters or identifiable people as if they endorsed the work.

## Grid and composition

- Start with a 12-column grid, even when the final composition is asymmetric. Use consistent margins and gutters.
- A digital canvas should keep text inside safe margins. Print needs the printer's specified physical size, DPI, bleed and trim; do not guess them.
- Select a composition to serve the content: title-led, image-led, editorial split, asymmetric grid, information modules, or card grid. Avoid repeating one layout for every brief.
- Use asymmetry intentionally, align blocks to shared edges, keep related details together, and give the primary message a clear area of dominance.
- Preserve negative space. Remove a decorative object before adding a second accent or texture.

## Palette and contrast

Choose a small, topic-specific palette: one dominant field, supporting surface/text colors and one intentional accent. Check actual text against the surface behind it; body text generally needs at least 4.5:1 contrast, and large display text at least 3:1. Muted does not mean illegible. Never rely on color alone to convey a category or action.

If background texture/imagery varies beneath text, measure or visually check contrast across the complete text block. Move text, add a restrained scrim, or use a solid surface when the background is busy.

## Typography

Two type families are usually enough; use a third only for a specific purpose. A display face provides character while a familiar sans-serif carries details, or one family can establish hierarchy through scale and weight alone.

- Use size, weight, case, tracking and line spacing as a coherent type scale rather than independent guesses.
- Large display text often benefits from slightly negative tracking; small all-caps labels often need positive tracking.
- Use all caps sparingly; they are labels/headlines, not long paragraphs.
- Set deliberate line breaks. If the headline no longer fits, shorten or reflow it; do not squeeze readable supporting copy into tiny type.
- Confirm fonts are licensed, available, loaded, and consistent in the rendered output. State substitutions.

## Images and artwork

Prefer the user's image, then a downloaded image with a verified license, then original/generated art. Ask what an image contributes; do not add it just to occupy a blank panel. Preserve a source image's important focal subject. Download external images into the project for reproducible output and record attribution where required.

A generated texture or pattern should have a system (repetition, scale, rhythm) rather than looking like scattershot decoration. Keep artwork at native resolution or size it down; do not silently upscale a low-resolution asset for large-format print.

## Iteration and QA

Translate feedback into one controlled design change. If the user asks for more whitespace, adjust density and spacing rather than changing the image and palette as well. Keep the written rationale consistent with the actual design.

Review in dependency order:

1. Canvas, aspect, crop, bleed and safe region.
2. Content accuracy, containment, overlap, clipping and image load.
3. Primary-to-secondary hierarchy and type fit.
4. Contrast, image crops, spacing and alignment.
5. Export dimensions, file integrity, color and attribution.

Always look at the render. Automated geometry checks cannot assess whether the design is memorable, whether a background patch looks natural, or whether generated text appears visually balanced.
