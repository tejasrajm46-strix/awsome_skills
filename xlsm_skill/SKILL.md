---
name: xlsm-processor
description: "Create, read, clean, edit and audit Excel workbooks (.xlsx, .xlsm, .xltx, .xltm), CSV and TSV data, formulas, charts and financial models. Use it for ordinary and macro-enabled spreadsheets. Keep formulas, formatting, VBA and embedded controls intact, and never run a macro or refresh a connection just to look at a file."
license: MIT
compatibility: Python 3.8+ for the package inspectors; openpyxl for everyday editing; pandas is optional for flat tabular data. Excel or LibreOffice is needed to recalculate formulas. Complex macros and controls need Microsoft Excel.
version: v3.0.0
---

# Excel — XLSX and XLSM

One skill covers every spreadsheet. Ordinary `.xlsx` and macro-enabled `.xlsm`
files follow the same workflow; macros add checks, not a licence to run code. A
CSV is flat data, not a workbook with styles and formulas.

## Shared research and assets

When you need outside facts, images, tables or a website's visual style, read
[`references/shared-scraping.md`](references/shared-scraping.md). It connects this
skill to `ultimate-scrape-skill`. Skip it for local edits, and reuse one source
register and asset set across formats.

## Workflow

1. Confirm format, output path, sheets and ranges, units and date conventions.
   Keep the original. List the formulas, external links, connections, pivots,
   controls, signatures and macros that have to survive.
2. Inventory the file with
   `python <skill-path>/scripts/inspect_workbook.py input.xlsx --json`. For VBA or
   `.xlsm`/`.xltm`, also run
   `python <skill-path>/scripts/inspect_xlsm.py input.xlsm --json`. Both read the
   package; neither calculates formulas or scans for malware.
3. Pick the least destructive editor. `openpyxl` handles ordinary cells, styles
   and formulas; `pandas` is only for flat transformations where Excel features
   do not matter. For ActiveX, Power Query, slicers, signatures, complex pivots or
   XML that openpyxl cannot model, use Excel automation or leave that part alone.
4. Read formulas and cached values separately (`data_only=False` / `True`). Match
   the source's conventions and leave everything out of scope untouched: cells,
   formulas, names, validations, protection, sheet visibility and order, frozen
   panes, print areas. For a new model, label the inputs, assumptions, units and
   sources.
5. Edit a copy. Keep derived values as formulas, quote sheet names that contain
   spaces, handle missing inputs and divide-by-zero, and check compatibility with
   the engine that will open the result. **Never save a `data_only=True` load** -
   that writes cached values over your formulas.
6. For macro-enabled edits, read
   [`references/macro-preservation.md`](references/macro-preservation.md) and
   [`references/xlsm-preservation.md`](references/xlsm-preservation.md). Load with
   `keep_vba=True, data_only=False`, save as `.xlsm`, and compare package parts.
   Renaming an `.xlsx` to `.xlsm` does not create macros.
7. Recalculate in an engine that actually does. `openpyxl` writes formulas but
   never calculates the cached values. Use Excel for macro-enabled or complex
   workbooks; a LibreOffice round-trip can quietly change features it does not
   support. Do not reach for macros or a connection refresh as a way to calculate.
8. Reopen what you saved. Compare sheet names, formula and error counts, links and
   package parts, then check representative calculations against known inputs.
9. Report the file, the checks you ran, whether recalculation happened, what was
   preserved, whether signatures are now invalid, and what you could not verify.
   Only claim macro behaviour was tested if you ran it and were allowed to.

## Basic macro-preserving edit

```python
from openpyxl import load_workbook
wb = load_workbook("source.xlsm", keep_vba=True, data_only=False)
# Change only requested cells.
wb.save("edited.xlsm")
```

`keep_vba=True` keeps the VBA stream in the cases openpyxl supports - not every
control, relationship, custom XML part or signature. Hash `xl/vbaProject.bin`
when the code should come out unchanged, and inventory the signature, ActiveX,
control, connection and relationship parts too. Editing usually invalidates digital
signatures, and an identical VBA binary still does not prove the macro works.

## Security and QA

- Treat macros, DDE, add-ins, links and connections as untrusted. Do not click
  Enable Content on a file you were only asked to read, and do not upload a
  confidential workbook to an online converter.
- Never swap formulas for values, drop links or caches, or let an unsupported
  feature disappear. When preservation and the requested edit collide, ask.
- Do not add a formula error. Say which errors were already there and which one
  your edit introduced.
- Confirm the file opens in the target Excel version with macros disabled.
- [`references/formulas-and-modeling.md`](references/formulas-and-modeling.md)
  covers modeling and formula QA.

## Checks

```bash
python <skill-path>/tests/test_inspect_workbook.py
python <skill-path>/tests/test_inspect_xlsm.py
```

Both inspectors and their tests use only the standard library. CSV and TSV work
needs row/column, encoding, delimiter and value checks instead of ZIP checks.

## Evolving this skill

An edit to this guide lands only when it improves a measured score, so read
[`references/skill-evolution.md`](references/skill-evolution.md) first.

<!-- SLOW_UPDATE_START -->
## Carried-forward rules

These survived real work; only an explicit, gate-passing slow update changes them.

- **A workbook edit is a package edit.** Compare the parts, not just the cells.
- **Never load `data_only=True` and save.** openpyxl writes the cached values over
  your formulas with no error and no warning.
- **`keep_vba=True` is a preservation claim, not a guarantee.** Hash
  `xl/vbaProject.bin`, then inventory signature, ActiveX, control, connection and
  relationship parts; a file that opens is not a file that works.
- **Do not recalculate by running the file.** No macros and no connection refresh:
  recalculate in Excel, or say plainly that the cached values are stale.
- **Preservation and behaviour are separate results.** "Macros preserved" and
  "macro behaviour tested" are different sentences, and only the first is usually
  true.
<!-- SLOW_UPDATE_END -->

<!-- APPENDIX_START -->
Keep the source and write to a new path. When a library rather than Excel does the
saving, say what it does not model, and if the host has no Excel, name the checks
that stopped there.
<!-- APPENDIX_END -->
