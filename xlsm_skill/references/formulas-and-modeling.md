# Spreadsheet formulas and model QA

## Inputs, assumptions, and units

- Use professional fonts (Arial or Times New Roman) unless the existing workbook has a clear convention; the original workbook always wins during edits.
- Separate hardcoded assumptions from derived formulas. Label units in headers (`Revenue ($mm)`), document hardcoded numbers in visible notes/comments, and cite a real source or say that the user supplied the value.
- Use blue font for hardcoded inputs, black for formulas, green for same-workbook links, red for external links, and yellow fill for key assumptions in finance models unless the workbook's established palette says otherwise.
- Store percentages as fractions (`0.15` = 15%), zeros as `-` and negatives in parentheses for financial models where appropriate. Treat years as text labels when formatting may otherwise add thousands separators.
- Guard denominators and explicitly define blank input behavior. Keep formula patterns consistent across projection periods; repeated formulas should differ only by intentional references.

## Formula strategy

- Write formulas, not precomputed values, when users expect dynamic updates. Use absolute references for assumptions that should stay fixed when copied.
- Prefer broadly supported formulas when the workbook must recalculate outside current desktop Excel. `SUMIFS`, `INDEX`, `MATCH`, `IFERROR`, and `SUMPRODUCT` are widely portable.
- Do not assume a clean formula evaluation means the logic is correct. Test a few hand-calculated examples first, then audit ranges, signs, units, edge cases, and references.
- Excel calculation metadata can request automatic/full recalculation, but that does not produce cached values by itself. Use a real calculation engine and reopen the saved workbook to verify caches.
- Formulas that reference external workbooks (often `='[1]Other.xlsx'!A1`) need their linked files and existing cached values preserved. Do not save/recalculate blindly.

## Reading formulas and cached results safely

```python
from openpyxl import load_workbook

formulas = load_workbook("model.xlsx", data_only=False, read_only=False)
values = load_workbook("model.xlsx", data_only=True, read_only=True)
for ws_f, ws_v in zip(formulas.worksheets, values.worksheets):
    for row in ws_f.iter_rows():
        for cell in row:
            if cell.data_type == "f":
                cached = values[ws_f.title][cell.coordinate].value
                print(ws_f.title, cell.coordinate, cell.value, cached)
```

`data_only=True` reads the last calculated value and hides the formula. Never save that workbook object: formulas are not loaded and would be replaced by values.

## Recalculation

For a compatible `.xlsx`, Excel or LibreOffice can calculate formulas. Verify tool output/status **and** reopen using `data_only=True`; some formulas or functions may not be implemented. For `.xlsm`, signed files, links, controls, add-ins, or complex extensions, use Excel if possible. State clearly when cached results are unavailable.

## QA checklist

- Verify workbook opens, expected sheet names/order/visibility are retained, and the output extension matches the actual package.
- Compare formula counts and formula-error cells with the source; investigate every newly introduced error.
- Inspect cached values only after recalculation, with formulas in a separate load.
- Test formulas independently with a few hand-calculated cases; verify lookups, totals, and edge cases.
- Check number formats, units, dates, hidden rows/columns, merged cells, print areas, frozen panes, validations, named ranges, charts and conditional formatting as relevant.
- Render the edited sheets and check clipping, readable widths, page breaks, charts, and contrast when a compatible renderer exists.
- Confirm all required VBA/embedded parts are still present in macro-enabled files. A matching `vbaProject.bin` is necessary but does not prove macros work.
