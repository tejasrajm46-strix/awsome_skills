---
name: xlsm-processor
description: "Create, read, clean, edit and audit Excel spreadsheets (.xlsx, .xlsm, .xltx, .xltm), CSV and TSV data, formulas, charts and financial models. Use for ordinary spreadsheets as well as macro-enabled workbooks. Preserve formulas, formatting, VBA and embedded controls; never execute macros or external connections merely to inspect a file."
license: MIT
compatibility: Python 3.8+ for package inspectors; openpyxl for ordinary editing; pandas is optional for flat tabular data. Excel or compatible LibreOffice is needed for formula recalculation. Complex macros and controls require Microsoft Excel.
---

# Excel — XLSX and XLSM

This is the single spreadsheet skill. Ordinary `.xlsx` and macro-enabled `.xlsm`
workbooks share a workflow, but **macro preservation adds checks, not permission
to execute code**. A CSV is flat data, not an Excel workbook with styles/formulas.

## Shared research and assets

When external facts, images, tables or a website's visual style are needed, read
[`references/shared-scraping.md`](references/shared-scraping.md). It connects this
skill to `ultimate-scrape-skill`. Skip scraping for local-only edits. Reuse one
source register and asset set when delivering multiple formats.

## Workflow

1. Confirm format, output path, sheets/ranges, units and date conventions. Preserve
   the original. Identify formulas, external links, connections, pivots, controls,
   signatures and macros that must survive.
2. Inventory with `python <skill-path>/scripts/inspect_workbook.py input.xlsx --json`.
   For VBA or `.xlsm`/`.xltm`, also run
   `python <skill-path>/scripts/inspect_xlsm.py input.xlsm --json`.
   These are package inventories, not formula engines or malware scans.
3. Choose the least destructive editor. Use `openpyxl` for ordinary cells/styles/
   formulas; `pandas` only for flat transformations when Excel features are not
   required. For ActiveX, Power Query, slicers, signatures, complex pivots or
   unsupported XML, use Excel automation or leave the feature untouched.
4. Read formulas and cached values separately (`data_only=False` / `True`). Match
   the source's design and preserve all out-of-scope cells, formulas, names,
   validations, protection, sheet visibility/order, frozen panes and print areas.
   For new models, label inputs, assumptions, units, sources and example values.
5. Edit a copy. Keep derived values as formulas; quote sheet names containing
   spaces, handle missing inputs and divide-by-zero, and check target-engine
   compatibility. **Never save a `data_only=True` load**: that discards formulas.
6. For macro-enabled edits, read
   [`references/macro-preservation.md`](references/macro-preservation.md) and
   [`references/xlsm-preservation.md`](references/xlsm-preservation.md). Load with
   `keep_vba=True, data_only=False`, save to `.xlsm`, and compare package parts.
   Do not create a plain XLSX and merely rename it `.xlsm`.
7. Recalculate in a compatible engine. `openpyxl` writes formulas but does not
   calculate caches. Use Excel for macro-enabled or complex workbooks; a
   LibreOffice round-trip can alter unsupported features and requires acceptance
   of that risk. Do not run macros or refresh connections to calculate by default.
8. Reopen the saved artifact. Compare sheet names, formula/error counts, links and
   package parts. Check representative calculations against known inputs and
   cached values after recalculation. Render/open changed sheets when possible.
9. Deliver the file with the exact checks, recalculation status, preservation
   result, signature invalidation and limitations. Do not claim macro behavior
   was tested unless execution testing was explicitly authorized and performed.

## Basic macro-preserving edit

```python
from openpyxl import load_workbook
wb = load_workbook("source.xlsm", keep_vba=True, data_only=False)
# Change only requested cells.
wb.save("edited.xlsm")
```

`keep_vba=True` preserves the VBA stream in supported cases, not every control,
relationship, custom XML part or signature. Compare `xl/vbaProject.bin` hashes
when code should be unchanged; also inventory signature, ActiveX, control,
connection, embedding and relationship parts. Editing usually invalidates digital
signatures. A matching VBA binary does not prove macro functionality.

## Security and QA

- Treat macros, DDE, add-ins, links and connections as untrusted. Never enable
  content or upload confidential workbooks to a service without authorization.
- Do not silently replace formulas with values, discard links/caches, or accept
  unsupported feature loss. Ask when preservation and the requested edit conflict.
- Never introduce new formula errors; distinguish pre-existing errors from edits.
- Confirm the file opens in the intended Excel version with macros disabled.
- Read [`references/formulas-and-modeling.md`](references/formulas-and-modeling.md)
  for modeling and formula QA.

## Checks

```bash
python <skill-path>/tests/test_inspect_workbook.py
python <skill-path>/tests/test_inspect_xlsm.py
```

Both inspectors and their tests use the standard library. CSV/TSV tasks need
separate row/column, encoding, delimiter and value checks rather than ZIP checks.
