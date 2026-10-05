# Macro-enabled workbook preservation

## Package parts to inventory

Besides workbook/sheet XML, inspect relevant parts such as:

- `xl/vbaProject.bin` and `xl/vbaProjectSignature.bin` (VBA and signature).
- `xl/activeX/`, `xl/ctrlProps/`, `xl/ctrls/`, `customUI/` (controls and ribbon customization).
- `xl/externalLinks/`, `xl/connections.xml`, query tables, pivot caches, slicers, and relationships.
- `customXml/`, `embeddings/`, media, workbook names, hidden/very-hidden sheets, and content types.

The exact layout varies. A part can be referenced through relationship files rather than obvious workbook XML. Compare complete inventories, not just filenames.

## Basic openpyxl case

Only consider openpyxl when the task is a limited cell/value/style/formula edit and the input contains no critical unsupported feature. Use `keep_vba=True`, preserve the `.xlsm` extension, and do not change unrelated workbook objects. Calculate a SHA-256 digest of `xl/vbaProject.bin` before and after when code should not change. The same hash means the binary stream survived, not that buttons still point to it or the macro works.

Do not rely on `keep_vba=True` for controls, signatures, custom XML, queries, external connections, complex pivots, or unsupported extensions. For these, edit via Excel automation or ask the user to accept the risk before proceeding.

## Signatures and trust

Editing a workbook invalidates its digital signature in common workflows. Preserve the original signed file. If the edited workbook must be signed, re-sign using the user's approved certificate/workflow and verify the resulting signature in Excel. Never state that a signature is valid because a signature part remains in the ZIP.

Do not extract or run macros from unknown workbooks. Package inspection, binary hashing and disabled-macro viewing are acceptable. Static macro review, if requested, should use an offline trusted parser and avoid copying confidential source into public services.

## Excel calculation

Openpyxl can write formula strings but does not evaluate them or populate the cached results. Set calculation mode only as a request to the spreadsheet application; it is not recalculation. Excel is the preferred calculation engine when macros/features must remain. Keep macros disabled during validation unless the user authorizes a test with controlled data and environment.

## Change disclosure

Report concrete differences: VBA stream retained/changed/missing; signature valid/invalid/unverified; controls/links/queries retained or not checked; calculation performed or pending; workbook opened/rendered or only package inspected. Never summarize all of these as merely "macro-safe."
