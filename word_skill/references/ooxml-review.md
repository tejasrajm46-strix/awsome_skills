# DOCX package-aware editing

DOCX files are ZIP archives containing WordprocessingML, relationships, styles, numbering, document properties, media and optional features. A text-only extraction does not reveal all structure or revisions.

## Inspect before editing

- Inventory ZIP members and relationships before and after the change. Pay attention to `word/document.xml`, `styles.xml`, `numbering.xml`, headers/footers, footnotes/endnotes, comments, custom XML, embeddings, drawings, custom properties and relationships.
- Treat archive member paths as untrusted; reject traversal entries and remove symlink entries before extraction.
- Parse only required XML parts. Avoid pretty-printing or rewriting unrelated OOXML; namespace prefix changes, relationship IDs, and child ordering may make a valid document unreadable in Word.
- Preserve fields (`w:fldSimple`, `w:instrText`), bookmarks, hyperlinks, content controls and revision markup when they are outside scope.

## Tracked changes

Real redlining uses revision elements: `<w:ins>` and `<w:del>` with IDs, author and date metadata. Deleted text uses `<w:delText>`; inserted text uses `<w:t>`. Deleting a paragraph mark is separate from deleting its text and changes paragraph joining behavior. A strikethrough font alone is not a tracked deletion.

Validate a redlined document by checking each requested insertion/deletion is wrapped in actual revision markup, under the expected author, and that accepted/rejected views produce the intended text. If accepting revisions, confirm deleted paragraph marks do not leave empty list items or paragraphs. Keep an unchanged source copy.

## Comments

Comments require a comments part, document relationship, content-type declaration and start/end/reference markers around the target range. A comments part with no anchor is not a visible comment. Check the document in Word's review view and ensure comments are attached to the intended text.

## Fields and templates

- TOCs, page numbers, cross-references and citations may be fields that need recalculation in Word. Field codes existing in XML do not prove displayed values are current.
- Preserve section properties, styles, numbering relationships, headers and footers. When copying content across templates, map styles and numbering rather than carrying conflicting definitions blindly.
- `python-docx` is useful for ordinary document creation, but is not a complete OOXML round-trip engine. For complex tracked changes, comments, SmartArt, controls, embedded OLE or signatures, use Microsoft Word automation or avoid the edit if it cannot be kept safely.
- Modifying a signed document generally invalidates its digital signature. Preserve the original and disclose signature invalidation; do not claim the edited copy remains signed.

## Inventory helper

Run `python scripts/inspect_docx.py input.docx --json` to confirm a DOCX package and inspect document paragraph/table counts, text preview, media, links, comments, footnotes, and headers/footers. This does not validate all schema constraints or visual appearance.
