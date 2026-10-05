# Original PPT visual references

**Inspect these assets before choosing a slide direction.** They are original
repository-created layout studies, not third-party templates or editable PPTX files.

- [Contact sheet](template-sheet.jpg) · [alternate entry](preview-sheet.jpg)
- [Source and license register](credits.json)
- [Editorial](render/editorial.jpg): strong claim, split evidence region, shared grid.
- [Signal / dark](render/signal.jpg): restrained dark canvas and one dominant metric.
- [Comparison](render/evidence.jpg): equal measured panels, explicit before/after.
- [System / flow](render/diagram.jpg): native-object process stages and connectors.
- [Data hierarchy](render/data.jpg): zero-baseline bars, visible units and context.
- [Portfolio](render/gallery.jpg): subject/detail/context rhythm and generous margins.

Read the sheet, open relevant images, then use their hierarchy, alignment and
spacing traits with the actual user content. Recreate native editable objects
through the builder; never flatten a whole reference into an allegedly editable
slide. Metrics/text shown here are illustrative, not evidence about performance.

All six artworks were created by `tools/build_reference_assets.py` using original
geometry and installed fonts and are covered by the repository MIT license.
Original third-party previews and large native templates are preserved privately
in ignored `local-archive/`, not published or included in skill ZIPs.

**No slide transitions.** The builder removes inherited transitions from an output
copy; the validator rejects any remaining `p:transition`. Preserve the input source.
Render the final deck and inspect wrapping, contrast, crop and chart readability
when PowerPoint/LibreOffice is available. A layout study is not visual approval
of a generated deck.
