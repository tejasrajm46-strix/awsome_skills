# pptx-generator

**Turn a plain JSON outline into a polished, fully editable PowerPoint deck - from a single prompt.**

No templates to download. No matplotlib. No flattened images. Every colour, chart,
table and transition is a real, native `.pptx` object, so the recipient can retype
a number or restyle a colour without leaving PowerPoint.

[![Python](https://img.shields.io/badge/python-3.8%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![python-pptx](https://img.shields.io/badge/built%20with-python--pptx-2E7D32)](https://python-pptx.readthedocs.io/)
[![License](https://img.shields.io/badge/license-MIT-2563EB)](LICENSE)
[![Layouts](https://img.shields.io/badge/layouts-24-A16207)](ppt_skill/SKILL.md)
[![Validated](https://img.shields.io/badge/decks-validated%20in%20CI-0E4C7A)](#the-validator)

---

## Why this exists

Generated decks usually fail in the same three ways:

| Failure | What this skill does about it |
|---|---|
| Text overflows the slide | Headlines and body text **size themselves down to fit** a measured grid. The builder refuses to go below 12pt - it tells you to split the slide instead. |
| Geometry drifts between slides | Every slide lays out on **one measured grid** with a shared type scale, so titles land on the same baseline throughout. |
| Transitions were written in the notes but never embedded | `transitions.py` writes **real `<p:transition>` elements** into the slide XML. What the validator reports is what PowerPoint plays. |

There is a fourth, quieter failure: a deck that *passes* validation and still looks
broken. That is why the validator here re-measures tables, detects colliding text
blocks as **errors**, and shares its measurement code with the builder so the two
can never disagree.

---

## Quick start

```bash
# 1. dependencies (lxml arrives with python-pptx)
python -m pip install python-pptx

# 2. build a deck from a JSON spec
python ppt_skill/scripts/build_deck.py examples/quick-start.json -o deck.pptx

# 3. add real slide transitions (optional)
python ppt_skill/scripts/transitions.py deck.pptx --preset fade --duration 700

# 4. gate it - always do this before you call a deck finished
python ppt_skill/scripts/validate_deck.py deck.pptx --expect 5
```

Prefer to start from a template the user supplied? Add `--base their-template.pptx`
and the theme is kept.

---

## A worked example

Here is the entire input for a five-slide deck - `examples/quick-start.json`:

```json
{
  "title": "Q3 Platform Review",
  "subtitle": "Three numbers that moved, and why",
  "theme": { "primary": "1E3A5F", "accent": "2563EB", "panel": "E9EEF5" },
  "slides": [
    { "layout": "title",  "kicker": "Platform Review",
      "title": "Q3 Platform Review", "subtitle": "Three numbers that moved, and why" },

    { "layout": "bullets", "title": "Latency fell further than volume grew",
      "bullets": [
        "Traffic grew **38%** while p95 latency fell **210ms**.",
        "The win came from the query cache, not from more hardware."
      ],
      "source": "Internal telemetry, 1 Jul - 30 Sep",
      "notes": "The cache change landed in week 3 - exclude week 1-2." },

    { "layout": "stats", "title": "Three numbers that moved",
      "items": [
        { "value": "38%",    "label": "quarter-on-quarter traffic growth" },
        { "value": "-210ms", "label": "p95 latency, after the cache" },
        { "value": "-41%",   "label": "cost per thousand requests" }
      ] },

    { "layout": "table", "title": "Where the latency actually went",
      "headers": ["Layer", "p95 before", "p95 after"],
      "rows": [["Edge", "180ms", "175ms"], ["API", "420ms", "260ms"],
               ["Database", "610ms", "290ms"]] }
  ]
}
```

Build it, and the validator's real output is:

```
$ python ppt_skill/scripts/validate_deck.py deck.pptx --expect 5
Deck: deck.pptx
Size: 13.33 x 7.50 in
Slides: 5

   1  Q3 Platform Review                     shapes=8   ok
   2  Latency fell further than volume grew  shapes=8   ok
   3  38%                                    shapes=16  ok
   4  Where the latency actually went        shapes=8   ok
   5  Thank you                              shapes=5   ok

Transitions: 5 embedded (fade x5)

Summary: 5 slides, 0 errors, 0 warnings
Result: PASS (editable, opens cleanly)
```

Four things worth noticing:

- `**38%**` renders as **bold** - inline emphasis works in any bullet or text field.
- The `table` slide came out with **rows sized to their tallest cell** and columns
  sized to their content, so the table cannot silently grow down over the footer.
- Every slide got **speaker notes** (`notes`) and a **right-aligned source line** (`source`).
- Slide 3 is a `stats` slide: three numeric cards, each auto-sized by value length.

The repo also ships two full-length examples you can run as-is:

| Example | What it shows |
|---|---|
| [`examples/blue-led-deck.json`](examples/blue-led-deck.json) | 15-slide editorial science deck: timelines, a native bar chart, a layered `stack` cutaway, tables, a quote, a stats slide. |
| [`examples/ocean-deck.json`](examples/ocean-deck.json) | 15-slide dark deck: hero, giant statement, ocean cross-sections, a node-graph `network`, a `cutaway` with leader lines, an animated-feeling `sequence`. Pair it with [`examples/ocean-transitions.json`](examples/ocean-transitions.json) - the transitions are mapped to the narrative. |

---

## Prompts to get started

Paste any of these into your agent. The skill triggers on "deck", "slides",
"PowerPoint", "pptx" or "presentation" even when you never name Python.

**The one-liner**

> Make me a 12-slide deck on the history of the transistor for a general audience.

**From a document**

> Turn `report.md` into a 10-slide presentation for our board, and put the detail in the speaker notes.

**A specific look**

> Build a dark, cinematic 8-slide pitch deck for a climate-tech startup. One big number per slide, native charts, no photos.

**Fixing a deck you already have**

> My deck's text overflows on slides 4 and 9 and the styling is inconsistent. Fix it without shrinking any font below 12pt.

**Real transitions**

> Add fade transitions throughout, with slower fades on the section dividers and a push on the two journey slides.

**Repurposing an existing file**

> Take my `old-deck.pptx` as the template and restyle the content of `notes.md` into it.

---

## How it works

The pipeline is four small programs rather than one, because each answers a
different question and each can be run and tested alone.

```
  outline.json
       |
       v
  +------------------+     +--------------------+     +---------------------+
  |  build_deck.py   | --> |  transitions.py    | --> |  validate_deck.py   |
  |  spec -> .pptx   |     |  real <p:transition>|     |  re-reads the bytes |
  +------------------+     +--------------------+     +---------------------+
       |                             |                          |
       +--------- both import ----> textmetrics.py <--- both import ---------+
                        (one owner of "how many lines
                         does this need, how tall is
                         that row, how wide is that
                         column")
```

| File | Owns |
|---|---|
| `scripts/textmetrics.py` | Text and table measurement. The single source of line counts, row heights and column widths. No `python-pptx` import, so it is testable alone. |
| `scripts/build_deck.py` | Spec JSON -> `.pptx`. The 24 layouts, theme tokens, freeform geometry, type auto-fit. |
| `scripts/transitions.py` | Post-processes a saved package to add real `<p:transition>` elements, which `python-pptx` has no API for. |
| `scripts/validate_deck.py` | Re-reads the saved package and gates it. Re-measures with the **same functions** as the builder. |
| `tests/test_layout_rules.py` | Assert-based regression checks for the layout rules. No framework, no fixtures. |

The one-way dependency is `textmetrics` <- `build_deck` / `validate_deck`. An
estimate that exists twice is how a deck passes validation and still looks broken,
so if you extend this, import the measurement instead of copying it.

### Design decisions worth knowing

- **Theme tokens, not templates.** A `theme` block of ~8 hex colours plus two font
  names drives the whole deck. Re-skinning is a five-line edit.
- **Native charts.** Charts are real PPTX chart objects (`bar`, `hbar`, `line`,
  `area`, `pie`, `doughnut`), so matplotlib is never needed and the chart stays editable.
- **Real transitions via OOXML.** `python-pptx` cannot write slide transitions, so a
  post-processing pass injects them, with the correct legacy `spd` attribute and the
  modern `p14:dur` duration, plus the `mc:Ignorable` declaration that keeps pre-2010
  readers happy.
- **No fabricated content.** The skill's rules forbid inventing a citation, statistic
  or quotation. Unverifiable numbers are left out, and diagrams that are not to scale
  say so.

---

## Layouts

24 layouts across a light editorial set and a dark cinematic set.

**Light - built for argument and evidence**

`title` · `section` · `bullets` · `two_column` · `stats` · `timeline` · `quote` ·
`table` · `chart` · `image` · `stack` · `closing`

**Dark - built for technical explanation**

`hero` · `split` · `statement` · `hero_stat` · `network` · `forces` · `cutaway` ·
`journey` · `flow` · `compare` · `trinity` · `sequence`

Each one takes its content as fields, and any slide accepts `notes` and `source`.
See [`ppt_skill/SKILL.md`](ppt_skill/SKILL.md) for the full schema and a per-layout
field reference.

---

## The validator

`validate_deck.py` is not a linter for style. It re-opens the saved `.pptx` and
answers one question: **will this actually read as intended?** It exits non-zero on
any error, so it works as a CI gate.

**Errors** - the deck is broken or unreadable as intended:

- shape extends past the slide edge
- two painted shapes collide (text over text, or a table/chart under text)
- a table grows past the bottom of the slide
- malformed, out-of-order or invalid transition XML
- unexpected slide count

**Warnings** - it will open fine but probably looks wrong:

- text likely overflows its box
- a table will auto-grow beyond where it was placed
- type below the 10pt legibility floor
- an empty slide, or a repeated title
- no transitions embedded at all

Tables are **measured, not skipped** - PowerPoint treats a row height as a minimum,
so a table can be taller than its declared box. Run the checks yourself:

```bash
python ppt_skill/tests/test_layout_rules.py
# ok   test_clean_deck_passes_the_gate
# ok   test_columns_follow_content_demand_with_a_floor
# ok   test_rows_get_the_height_of_their_worst_cell
# ok   test_stack_note_cannot_reach_the_marker_column
# ok   test_table_does_not_need_growing
# ok   test_table_too_dense_to_read_is_refused
# ok   test_validator_reports_collisions_as_errors
#
# 7/7 passed
```

---

## Install as an agent skill

A skill folder must be named after its `name:` field, which is `pptx-generator`.

**From the release zip (recommended)**

```bash
unzip pptx-generator-v1.0.0.zip -d ~/.agents/skills/
# -> ~/.agents/skills/pptx-generator/
```

The zip contains the skill only - no examples, no build outputs.

**From source**

```bash
git clone https://github.com/tejasrajm46-strix/skill_ppt_generator.git
cp -r skill_ppt_generator/ppt_skill ~/.agents/skills/pptx-generator
```

Once installed, just ask for a deck; the skill's description tells the agent when
to reach for it.

---

## Requirements

- **Python 3.8+**
- **python-pptx** (`pip install python-pptx`) - pulls in Pillow and lxml
- **Optional:** LibreOffice (`soffice`), only if you want a PDF preview. Its absence
  is not an error - but it is worth knowing that structural validation does not
  replace looking at the rendered slides.

Fonts must exist on the machine that opens the deck: `python-pptx` cannot embed
fonts, so a Google font named in the spec silently substitutes. Stick to
`Segoe UI`, `Calibri`, `Arial` or `Consolas`.

---

## Repository layout

```
README.md
LICENSE
ppt_skill/                 the skill - clone or copy this into your skills directory
  SKILL.md                 workflow, spec schema, layout reference, house rules
  scripts/
    build_deck.py          spec JSON -> .pptx (24 layouts)
    textmetrics.py         shared measurement: line counts, row heights, column widths
    transitions.py         real OOXML <p:transition> post-processor
    validate_deck.py       integrity, bounds, collisions, table growth, transitions
  references/
    design-rules.md        type scale, narrative arc, chart and table craft, anti-patterns
    free-assets.md         licence facts verified at source, and attribution duties
  evals/evals.json         evaluation cases
  tests/                   assert-based layout regression suite
examples/
  quick-start.json         the five-slide deck above
  blue-led-deck.json       15-slide light editorial deck
  ocean-deck.json          15-slide dark deck
  *-transitions.json       transition maps for the two full examples
```

---

## Releases

Releases are cut automatically. Push a tag and GitHub Actions builds
`pptx-generator-<tag>.zip` from `ppt_skill/` and attaches it to the release:

```bash
git tag v1.0.1
git push origin v1.0.1
```

Then install it with the `unzip` line above.

---

## License

MIT - see [LICENSE](LICENSE).
