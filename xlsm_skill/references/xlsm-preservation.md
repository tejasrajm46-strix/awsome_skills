# Editing macro-enabled Excel workbooks (.xlsm)

An `.xlsm` is an Office Open XML ZIP package plus VBA and potentially other executable or embedded components. It is not safe to treat an arbitrary `.xlsm` as an ordinary `.xlsx`.

## Before editing

1. Preserve the source unchanged and create a separate output copy.
2. Ask whether VBA, signatures, buttons, form controls, ActiveX, data connections, queries, and external links must be retained if that is not clear from the request.
3. Inspect ZIP member names and hashes for items such as `xl/vbaProject.bin`, `xl/activeX/`, `xl/ctrlProps/`, `customUI/`, `xl/externalLinks/`, and custom XML. This is package inventory, not a safety scan.
4. Never enable macros, execute embedded code, or allow untrusted connections/DDE merely to inspect a file. Treat VBA as untrusted code; do not print secrets from it into logs.
5. If digital signing is present, editing typically invalidates the signature. Obtain approval for the loss or use an authorized signing workflow after editing.

## Editing with openpyxl

```python
from openpyxl import load_workbook

wb = load_workbook("source.xlsm", keep_vba=True, data_only=False)
# Make only requested changes; do not delete unrelated sheets/features.
wb.save("edited.xlsm")  # Keep the .xlsm extension.
```

`keep_vba=True` retains the VBA project stream where supported; it does not make openpyxl a full-fidelity editor for Excel features. It may discard unsupported extensions, controls, signatures, connections, slicers, pivots, or other package parts. If any critical item cannot be preserved confidently, do not use this path; use Excel automation or make no edit to the source.

Never load the workbook with `data_only=True` for editing: formula text is not loaded. If formula caches matter, record values separately before editing, then use Excel to recalculate and verify. Avoid LibreOffice conversion/round-trip for a macro-enabled workbook unless the user explicitly accepts the compatibility risk.

## Post-edit verification

- Confirm the output is still an XLSM package and contains `xl/vbaProject.bin` when the input did.
- Compare before/after package inventories for lost VBA, controls, relationships, connections, external links, custom XML, and media. Review unexpected removals.
- Reopen in Excel with macros disabled; inspect edited cells and representative formulas. Confirm buttons/controls still point to valid macros, but do not run the macros unless the user separately authorizes an execution test.
- Verify recalculated values with Excel when needed. Formula text presence alone is not calculation QA.
- Report signature invalidation, dropped unsupported features, or missing calculation caches explicitly. Never claim the macro project works solely because its binary is present.
