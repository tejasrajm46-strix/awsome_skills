# When python-pptx is not available

Read this only when the build environment cannot install `python-pptx`.

## Say so plainly

Tell the user what is missing rather than producing a broken deck. Start by
asking them to install it:

```bash
python -m pip install python-pptx
```

## Last resort: write the package by hand

A `.pptx` is a ZIP of OOXML parts, so a minimal deck can be written with
`zipfile` and string templates and no third-party library. Be honest about what
this path costs: it supports almost none of the layouts in
[`deck-schema.md`](deck-schema.md). Text boxes and pictures are realistic; native
charts, measured tables, the dark layouts and the collision checks are not. If
the user wants any of those, they need the real library.

If you do take this path, validate what you can by reopening the ZIP and reading
the XML parts back, and say clearly that the normal validator did not run.

## Look at the result anyway

Whatever produced the file, try to render it:

```bash
soffice --headless --convert-to pdf deck.pptx
```

Installed PowerPoint exports PDF and PNG as well. Structural validation is not a
substitute for looking at rendered slides, so name the checks you ran.

## What `--strict` actually checks

`validate_deck.py --strict` fails on warnings as well as errors. It confirms that
missing alt text and picture/text collisions are caught, that bar axes start at
zero, and that theme backgrounds are explicit. Text that cannot fit at the 12pt
floor raises instead of quietly returning the smallest font - shorten the content
instead of shrinking it.

When a check cannot run because a dependency is missing, report it as a check
that did not run. "Unverified" is a correct answer; "looks fine" is not.
