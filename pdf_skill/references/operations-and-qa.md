# PDF operations and quality checks

## Extraction

- Check page count and whether text exists per page before choosing extraction or OCR.
- `pdftotext -layout input.pdf output.txt` often preserves columns/tables better than simple text extraction, but always compare with the rendered page.
- `pdfplumber` exposes characters, words, bounding boxes and tables. Tune table strategies per page; a detected grid is not proof of correct row/column assignment.
- Preserve text in its original language and Unicode. Check hyphenation, multi-column ordering, headers/footers, ligatures and page labels.
- For scanned PDFs, keep an OCR transcript clearly identified as machine-generated until verified. Choose OCR language(s), deskew/rotate, and compare a sample with source pixels.

## Forms

- Inspect AcroForm field names, types, current values, choice options, required status and widget appearances before filling.
- Preserve field names and appearance streams if downstream users need editable fields. Flatten only on request; flattening makes values harder to edit and may affect accessibility.
- Validate values in the final file with a PDF parser and render filled pages. Confirm checkbox/radio appearance and long text fit.
- XFA forms may not be handled by pypdf; use compatible Adobe software or ask for a non-XFA copy. Do not claim a form is filled if fields were not verified.

## Creation and conversion

- Prefer the original editable source (DOCX, PPTX, HTML, source data) to convert to PDF rather than redrawing a PDF by hand.
- Set page size, margins, fonts, metadata, links and page numbers consistently. Embed fonts when licensing permits and reliable rendering requires it.
- Export to a new path. Then inspect dimensions, page count, text extraction and rendered pages. Conversion can change pagination, line wraps and vector details.
- A scanned/PDF/A/compressed output is a different target; do not assert conformance without a specific validator.

## Redaction and privacy

- A covering rectangle only obscures text visually. Searchable text, images, OCR layers, attachments, comments, bookmarks, metadata, or earlier incremental revisions can reveal it.
- Apply true redactions using a tool that removes the marked content; then sanitize according to the user's threat model. Rebuild/garbage-collect the file when removal of prior revisions is required.
- Search extracted text for target terms, inspect images and annotations, and render each changed page. A content search is not sufficient to prove no image or hidden layer retains the data.
- Do not upload a confidential PDF to an online OCR/conversion tool without permission.

## Quality checklist

- File opens with an independent PDF reader/parser; `qpdf --check` if available.
- Page count, dimensions, labels, rotation and requested order are correct.
- Expected text, tables, form values and links exist; removed text is absent if redaction was requested.
- Fonts, selectable/searchable text, bookmarks, attachments, tags, metadata, permissions and encryption match the request.
- Rendered pages show no clipping, blank pages, font substitution, overlapping text, incorrect crops, unintended rotation or missing annotations.
- If output is encrypted, test open behavior without exposing credentials. Note that encryption and permissions are not equivalent to DRM or guaranteed access control.
