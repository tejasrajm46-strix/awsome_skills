---
name: pdf-processor
description: "Use whenever a PDF is mentioned or is the input/output: read or extract text/tables/images, OCR scans, create/export, merge, split, reorder, rotate, watermark, fill forms, redact, compress, encrypt, or inspect PDF metadata. Inspect the PDF structure and distinguish searchable text from scanned pages. Do not treat a raster image of text as editable source or promise that redaction is secure unless underlying content was removed and verified."
license: MIT
compatibility: Python 3.8+; pypdf for structural operations; pdfplumber for layout/table extraction; reportlab for basic generation; Poppler or MuPDF tools for rendering/OCR workflows. The inspection script uses Python standard library only.
---

# PDF Processor

PDF workflows must preserve page order, geometry, text, and security expectations. First identify whether each page contains text, vectors, raster scans, or a mixture. Choose a method based on the task; verify the saved PDF, not only the intermediate objects.

## Shared research and assets

When external facts, images, tables or a website's visual style are needed, read
[`references/shared-scraping.md`](references/shared-scraping.md), which connects
this skill to `ultimate-scrape-skill`. Skip scraping for local-only PDF operations.

## Workflow

1. **Protect source material.** Never overwrite the only input. Treat PDFs and embedded links/attachments as untrusted. Do not execute scripts, open embedded files, submit forms, or follow links unless explicitly authorized.
2. **Inspect.** Run `python scripts/inspect_pdf.py file.pdf --json` to check ZIP-independent PDF header/trailer, page count, encryption flag when readable, and metadata basics. If tools are available, inspect text with `pdftotext -layout`, metadata with `pdfinfo`, and representative rendered pages. A scan with little/no text needs OCR.
3. **Clarify consequential choices.** Preserve original page order unless asked to change it. For form filling, identify fields and flattening expectations. For redaction, distinguish a visible black box (not redaction) from irreversible removal. For encryption, determine password/permissions and handle secrets without logging them.
4. **Choose an appropriate tool.** Use pypdf for page-level changes, pdfplumber for layout-aware extraction and tables, ReportLab for authored PDFs, and OCR/rendering tools for image-only pages. Preserve vector/text quality when feasible.
5. **Perform the task.** Write to a new output file. Keep page rotation, boxes, bookmarks, metadata, tags, links and encryption consistent with requirements. Be cautious with digitally signed PDFs: modification invalidates signatures. A redacted area must be removed from underlying content and, when needed, sanitized from metadata, OCR layers, attachments, annotations, and incremental revisions.
6. **Verify output.** Reopen it with an independent parser. Confirm page count/order, page dimensions/rotation, expected text/fields, metadata, encryption, and attachments as relevant. Render all pages or a representative full-page contact sheet for visual review. Search the output for supposedly removed text before claiming redaction. Check that OCR text is accurate against the image.
7. **Deliver.** State output path, operations, page count only when measured, and exact structural/visual/security checks performed. Do not claim a PDF is accessible/searchable, redacted, password-protected, or print-ready without validating that property.

## Common operations

### Extract text and page count

```python
from pypdf import PdfReader
reader = PdfReader("input.pdf")
print("pages", len(reader.pages))
for number, page in enumerate(reader.pages, 1):
    print(f"--- PAGE {number} ---")
    print(page.extract_text() or "[No extractable text; may require OCR]")
```

For reading order/tables, use `pdfplumber` and compare with rendered pages; PDF extraction order can differ from visual order.

### Merge and split

```python
from pypdf import PdfReader, PdfWriter
writer = PdfWriter()
for source in ["a.pdf", "b.pdf"]:
    for page in PdfReader(source).pages:
        writer.add_page(page)
with open("merged.pdf", "wb") as stream:
    writer.write(stream)
```

For splitting, create one writer per requested range and verify each output's page count. Preserve bookmarks only if the chosen library path supports them; otherwise report loss.

### Rotate and metadata

Use `page.rotate(90)` on selected pages and preserve the rest. Check page dimensions and orientation afterwards. Set document metadata only with accurate title/author/subject values; metadata changes can invalidate signatures.

### Generate

Use ReportLab for authored PDFs. For long reports, use Platypus flowables and real page templates rather than manually positioning every line. Embed an appropriate font for non-ASCII text. Avoid Unicode subscript/superscript glyphs with built-in ReportLab fonts; use Paragraph `<sub>`/`<super>` tags or a font with glyph support. For accessible PDFs, a visual PDF alone is not a guarantee of tagged reading order: use an authoring source/tool that supports tagging and validate with an accessibility checker.

### OCR scanned pages

Render pages at appropriate resolution and OCR with a verified local tool. Keep the original scan available. If creating a searchable PDF, place the OCR layer accurately over each page; verify page orientation, language, diacritics, tables, and representative extracted text. OCR is an estimate and must not be silently presented as authoritative transcription.

### Redaction and security

Do not overlay black rectangles and call it redaction. Use a true redaction implementation that removes text/graphics from page content, then sanitize metadata, attachments, annotations, hidden OCR layers and prior revisions where the threat model requires. Reopen and text-search the final file, render it, and inspect page content. Encryption tools and permission flags vary; test opening behavior without putting passwords in shell history or logs.

## Supporting files

- `python scripts/inspect_pdf.py file.pdf [--json]`: dependency-free PDF container sanity check. It is not a full parser or content safety scan.
- `python tests/test_inspect_pdf.py`: basic parser-inventory regression tests.
- Use `pypdf` for simple page operations; `pdfplumber` for layout extraction; `pdftotext -layout`, `pdfinfo`, `pdftoppm`, `qpdf`, or equivalent only when installed.
- See `references/operations-and-qa.md` for validation checklists.
