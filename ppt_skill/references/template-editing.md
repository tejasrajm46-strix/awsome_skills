# Working with supplied PowerPoint files

Use this reference whenever an existing `.pptx` / `.potx` is an input, or the user says to edit, restyle, repair, convert, reuse or copy a deck/template. Preserve the original and create a separate output.

## Route by task

| User goal | Safe starting point | Key limit |
|---|---|---|
| Extract text / audit a deck | Open with `python-pptx`; read slides, notes, tables and chart data; inspect package relationships | Extraction order/shape grouping may not mirror visual hierarchy. Render slides too. |
| Create new slides from a style/template | Inspect master/layouts, theme/fonts, image assets and representative slide renders. Use the existing builder with `--base` only when appending new slides is intended. | This builder appends; it is not a content-replacement or faithful theme-transfer engine. |
| Fix overflowing or inconsistent slides | Inventory every slide's content and intended hierarchy; rebuild affected slides or whole deck from the shared grid; preserve source copy | Do not simply lower all font sizes. Retain important notes/citations/data. |
| Replace wording/images in existing slides | Edit only in-scope shapes using PowerPoint/LibreOffice automation or a careful package-aware OOXML transformation | python-pptx may drop unsupported parts or change layout details on save. Verify preserved relationships and render. |
| Duplicate, reorder, or delete slides | Use PowerPoint automation or a package-aware tool with relationship/content-type bookkeeping | Do not copy slide XML files by hand; chart/media/notes/layout rels can be shared or orphaned. |
| Work with `.pptm` or signed decks | Prefer Microsoft Office automation and preserve VBA/signature policy | Editing may invalidate the signature; generic python-pptx round-tripping is not a macro-preservation guarantee. |

## Inspect a template before designing

1. Preserve the source and list slide count, dimensions, slide order, layouts, themes, fonts, notes, charts, media and package-specific features.
2. Extract all text and render representative slides (or all slides for a redesign). Make a map from each source slide to the intended role/content in the output.
3. Record reusable design properties: content grid, margins, title baseline, color tokens, fonts, image crop treatment, chart palette, footers, page numbers, and master decorations.
4. Distinguish editable slide objects from raster artwork. Avoid flattening editable tables/charts/diagrams when the user expects editing.
5. Document what's preserved, replaced, intentionally removed, and unsupported by the toolchain before modification.

## Edit rules

- Use a copy, not the user's only source. Never claim a template is preserved if it was replaced with a visually similar blank deck.
- Do all slide insertion/deletion/reordering work before editing content when using package-level tools, then update relationships and clean orphaned parts.
- Retain one paragraph per list item and use real bullet/numbering properties rather than literal bullet characters. Preserve text-run formatting where possible.
- Existing media and reused objects may be linked through relationships. Check every relationship target remains valid after edits.
- Preserve notes, source citations, alt text, charts and speaker notes unless the request explicitly removes them. Generated output must be transition-free: remove inherited slide transitions from the output copy and disclose this change; preserve the original.
- Where an exact native edit is too risky, create a rebuilt editable deck and identify which template characteristics were matched rather than claiming the original deck itself was edited.

## QA

- Compare slide count/order, page size, slide text, notes, chart series, image count and relationship targets before/after.
- Run the skill's structural validator; for template builds, verify the source deck remains unchanged.
- Render every output slide to images and inspect actual type fit, crop, hierarchy, contrast, margins, empty space, table/chart readability and any leftover placeholder text.
- Open the final deck in PowerPoint/LibreOffice when available. Confirm zero slide transitions; structural parsing alone cannot verify object animations, theme substitutions, or all embedded objects.
- Report precisely whether the output is a new deck, appended template, or edited source deck, and identify visual or functional features that were not verified.
