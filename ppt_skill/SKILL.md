---
name: pptx-generator
description: Build polished, editable PowerPoint (.pptx) decks with Python and python-pptx - title, section, hero and giant-statement slides, bullets, two-column comparisons, stat callouts, timelines, quotes, tables, native editable charts, layered cutaways, flow and sequence diagrams, ocean cross-sections, network maps, and real embedded slide transitions, on one consistent colour and type system. Use this skill whenever the user wants to make, generate, build, design, or restyle slides, a slide deck, a PowerPoint, a PPT, a .pptx file, a presentation, a pitch deck, or slide notes - even if they only say "deck" or "slides" and never mention PowerPoint or Python. Also use it to turn a report, document, notes, research, or an outline into a presentation, to fix a deck whose text overflows or whose styling is inconsistent, and when asked for real PowerPoint transitions between slides. Check this before hand-rolling python-pptx code, since it already encodes the layout, fit, transition and validation work.
license: MIT
compatibility: Requires Python 3.8+ with python-pptx and lxml (both pulled in automatically). Charts are native PPTX charts, so matplotlib is not needed. LibreOffice is optional and only used to render a PDF preview.
---

# PPTX Generator

Turn content into a real, editable `.pptx`. The output is a normal PowerPoint
file - the recipient can retype a number, restyle a colour, or swap a chart
type. Text, charts and diagrams stay editable; imported images remain images.

## Why the workflow is shaped like this

The failure modes of generated decks are, in order: **text that overflows the
slide**, **inconsistent geometry between slides**, and **transitions that were
written in the notes but never actually embedded**. The measured grid, text-fit
estimates, real `<p:transition>` elements and saved-package checks reduce these
failures; they do not replace rendering in PowerPoint or LibreOffice. Font metrics
are heuristic, and imported images are checked for bounds/collisions, not their
internal label legibility.

Respect the order below. In particular, never report a deck as finished without
running the validator - it is the only thing that has actually looked at the
bytes.

## Workflow

1. **Check dependencies.** `python -c "import pptx, lxml"` - if that fails, run
   `python -m pip install python-pptx`. lxml arrives with python-pptx.
   `soffice --version` tells you whether a PDF preview is possible; its absence
   is not an error.

2. **Draft the content as an outline first**, in prose or bullets, before
   touching JSON. Set audience, purpose and a coherent visual system. Decide the
   single takeaway of each slide. For research, read authoritative sources and
   keep numbered source IDs with URLs and claim coverage. Share this register
   and original image assets with `word-generator` when delivering both formats.
   A deck is an argument, not a document with page breaks.

3. **Write a deck spec JSON** (schema below), choosing a layout per slide from
   the table further down. Write the `title` as a claim, not a label.

4. **Build it:**
   ```bash
   python <skill-path>/scripts/build_deck.py deck.json -o deck.pptx
   ```
   Add `--base their-template.pptx` to start from a template the user supplied.

5. **Add real transitions** (if the deck wants them - see below):
   ```bash
   python <skill-path>/scripts/transitions.py deck.pptx --config transitions.json
   ```

6. **Validate, and read the warnings:**
   ```bash
   python <skill-path>/scripts/validate_deck.py deck.pptx --expect <n> --strict
   ```
   Errors are hard failures: a shape off the slide, overlapping text, a table
   that grows past the bottom of the slide, malformed transition XML. Warnings
   mean it will open but probably looks wrong - text likely overflowing its box,
   a table that will auto-grow, type below 10pt, no transitions at all. Overflow
   warnings mean the slide is carrying too much text. Fix it by splitting the
   slide or cutting words - **not** by lowering the font size. Tables are
   measured, not skipped, so a cramped table is reported like any other slide.

7. **Render and inspect** every slide with installed PowerPoint or LibreOffice,
   when available. Check actual wrapping, figure-label size, contrast, clipping,
   whitespace and narrative rhythm. Fix the spec and rebuild; no validator can
   certify visual perfection. Do not modify the user template in place.

8. **Report** the output path, slide count, theme, embedded transition count,
   structural result and whether rendering/visual review actually occurred.
   Do not paste the deck's contents back into chat or call unrendered output flawless.

## Deck spec schema

Only `title` and `slides` are required. Every layout accepts `notes` (speaker
notes) and `source` (citation line, right-aligned above the footer).

```json
{
  "title": "How the Blue LED Was Invented",
  "subtitle": "Three decades, three researchers, one stubborn crystal",
  "author": "Your Name",
  "theme": {
    "primary": "1E3A5F", "accent": "2563EB", "highlight": "A16207",
    "text": "0F172A", "muted": "475569", "panel": "E9EEF5", "border": "CBD5E1",
    "font_head": "Segoe UI", "font_body": "Segoe UI", "font_mono": "Consolas",
    "bg_dark": "04121F", "deep": "0A2540", "ocean": "0E4C7A",
    "cyan": "22D3EE", "cyan_soft": "7DD3FC", "warm": "F59E0B", "alarm": "EF4444"
  },
  "slides": [
    {"layout": "title", "kicker": "Materials Science", "title": "How the Blue LED Was Invented",
     "subtitle": "Three decades, three researchers, one stubborn crystal",
     "author": "Your Name", "date": "2026"},

    {"layout": "section", "number": "01", "title": "The Long Wait",
     "text": "Why red and green came first"},

    {"layout": "bullets", "title": "Blue was the last colour to fall",
     "bullets": ["**Red** (1962) and **green** (1968) were solved within a decade.",
                 "Blue needs a much wider band gap than any known material allowed."],
     "body_size": 16, "notes": "Detail that belongs in the talk, not on screen."},

    {"layout": "two_column", "title": "Two candidate materials",
     "left": {"heading": "ZnSe", "bullets": ["Direct band gap", "Short lifetime"]},
     "right": {"heading": "GaN", "bullets": ["Tougher crystal", "No p-type doping (yet)"]}},

    {"layout": "stats", "title": "The breakthrough in numbers",
     "items": [{"value": "1993", "label": "First practical blue LED"}]},

    {"layout": "timeline", "title": "Thirty years to a blue light",
     "items": [{"date": "1989", "label": "Amano", "text": "p-type GaN achieved"}]},

    {"layout": "table", "title": "Band gaps by colour", "headers": ["Colour", "Material", "Gap (eV)"],
     "rows": [["Blue", "InGaN", "3.4"]]},

    {"layout": "chart", "title": "Efficiency overtakes the filament lamp",
     "chart_type": "line", "unit": "lumens per watt",
     "categories": ["1970", "2010"], "series": [{"name": "White LED", "values": [1, 130]}]},

    {"layout": "stack", "title": "The InGaN junction", "items": [
        {"label": "p-type GaN", "note": "Hole supply", "marker": "+"},
        {"label": "InGaN active layer", "note": "Recombination emits light", "marker": "hv"}]},

    {"layout": "quote", "text": "The citation text.", "attribution": "Source, 2014"},
    {"layout": "image", "title": "A packaged LED", "image": "assets/led.png", "caption": "Caption."},
    {"layout": "closing", "title": "Thank you", "text": "Questions welcome.", "credit": "Sources: ..."}
  ]
}
```

### Layout reference

Light-background layouts use the standard header grid. Dark layouts
(`hero`, `statement`, `hero_stat`, `network`, `forces`, `cutaway`, and
`flow` with `"dark": true`) paint their own full-bleed background.

| `layout` | Key fields | Notes |
|----------|-----------|-------|
| `title` | `title`, `kicker`, `subtitle`, `author`, `date` | Full-bleed navy opening. |
| `section` | `number`, `title`, `text` | Divider. Its `title` becomes the running `kicker` on later slides. |
| `bullets` | `title`, `bullets`, `body_size` | Auto-sizes 20pt down to 12pt. Use `body_size` for reference lists. |
| `two_column` | `title`, `left`, `right` (`{heading, bullets}`) | For genuine comparisons only. |
| `stats` | `title`, `items` (`{value, label}`) | 2-4 cards. Value shrinks with length. |
| `timeline` | `title`, `items` (`{date, label, text}`) | **2-6 items.** More raises an error - split the slide. |
| `quote` | `text`, `attribution` | Breaks a run of bullet slides. |
| `table` | `title`, `headers`, `rows` | Keep to <= 5 columns. Rows are sized to their tallest cell and columns to their content, so the table cannot grow over the footer; a table that would need under 12pt raises instead. |
| `chart` | `title`, `chart_type`, `categories`, `series`, `unit`, `bullets` | `bar`, `hbar`, `line`, `area`, `pie`, `doughnut`. Native and editable. |
| `stack` | `title`, `items` (`{label, note, marker}`) | Layered structure bands. Max 8. Label, note and marker occupy measured columns with a reserved gutter, so a long note cannot run into its marker. |
| `image` | `title`, `image`, `caption`, `alt` | Local PNG/JPEG path relative to spec JSON (API uses caller paths). Contained, never distorted. `alt` describes the message; caption is the fallback. |
| `closing` | `title`, `text`, `credit` | `credit` is where template/attribution lines go. |
| `hero` | `kicker`, `title`, `subtitle`, `meta` | Cinematic opening: ocean floor, grid, glowing cable. |
| `statement` | `kicker`, `title`, `text` | Giant typography on a dark ambient background. |
| `hero_stat` | `kicker`, `value`, `unit`, `text` | One enormous number. Sets the case up to 120pt. |
| `split` | `title`, `left`, `right`, `text` | Two illustrative panels joined by a cyan route. |
| `flow` | `title`, `steps`, `chips`, `vessel`, `dark` | Vertical chain plus an ocean cross-section strip. |
| `journey` | `title`, `stations`, `zones` | Cross-section with labelled stations above and below. |
| `cutaway` | `title`, `layers`, `note` | Vertical cutaway with leader lines to callouts. Dark. |
| `network` | `title`, `nodes` (`{name, x, y}`), `links` (`[[i,j]]`), `note` | Conceptual node graph. Normalised 0-1 coords. |
| `forces` | `title`, `items`, `note` | Warning callouts above a seabed. Dark. |
| `compare` | `title`, `left`, `right` (`{heading, bullets, motif}`) | `motif` is `signal` or `light`; drawn, not emoji. |
| `trinity` | `title`, `items`, `text` | Three stacked statement bands with arrows. |
| `sequence` | `title`, `steps`, `highlight`, `network`, `note` | Horizontal chain; `highlight` marks the failure in red. |

Inline `**bold**` works inside any bullet or text field.

## How the scripts fit together

The workflow is a pipeline of small parts, not one program, because each part
answers a different question and each can be run and tested alone:

| File | Owns |
|------|------|
| `scripts/textmetrics.py` | Text and table measurement. The single owner of "how many lines does this need, how tall is that row, how wide is that column". No python-pptx import, so it is testable alone. |
| `scripts/build_deck.py` | Spec JSON -> `.pptx`. Layout, theme tokens, freeform geometry. Imports its measurements from `textmetrics` and never re-derives them. |
| `scripts/transitions.py` | Post-processes a saved package to add real `<p:transition>` elements, which `python-pptx` cannot express. |
| `scripts/validate_deck.py` | Re-reads the saved package and gates it. Re-measures with the *same* functions as the builder, so the two can never disagree. |
| `tests/test_layout_rules.py` | Assert-based regression checks for the layout rules, including the two bugs that once shipped (a table sized for its shortest cell; a stack note box reaching into the marker column). |

The one-way dependency is `textmetrics` <- `build_deck` / `validate_deck`. If you
find yourself copying a line-count or width estimate into a new script, stop and
import it instead: an estimate that exists twice is how a deck passes validation
and still looks broken.

Run the checks with:

```bash
python <skill-path>/tests/test_layout_rules.py
```

## Slide transitions

`python-pptx` has no transition API. The bundled `transitions.py` post-processes
the saved package and writes real `<p:transition>` elements into each slide
part, which is what PowerPoint reads and actually plays.

```bash
python <skill-path>/scripts/transitions.py deck.pptx --config transitions.json
python <skill-path>/scripts/transitions.py deck.pptx --preset fade --duration 700
```

A config maps a default plus per-slide overrides; slide numbers are 1-based and
a transition on slide N is the transition **into** slide N, so slide 1 is
normally `null`:

```json
{
  "default": {"type": "fade", "duration": 700},
  "slides": {
    "3": {"type": "push", "dir": "l", "duration": 700},
    "9": {"type": "split", "dir": "l", "duration": 700},
    "12": null
  }
}
```

Types: `fade`, `dissolve`, `cut`, `push`, `wipe`, `cover`, `split`. `dir` is
`l`, `r`, `u` or `d`. Durations are milliseconds.

House style, learned from how these read on a projector:

- `fade` is the default for anything informational. Use it for section changes
  at slightly longer duration to mark the narrative shift.
- `push`/`wipe` only where the content genuinely moves in a direction - a
  journey, a sequence, a progression.
- `split` for a comparison or a reveal.
- Never use random bars, checkerboard, airplane or rotating effects.
- Keep everything within 0.5-1.2s. Anything slower reads as a stall.
- Object animations are a different system and are not needed for a deck like
  this. Prefer transitions; do not overload both.

## Themes and design tokens

Every colour is a token in the spec's `theme` block, so re-skinning a deck is a
five-line edit and never a hunt through literals. `build_deck.py` ships a
"Research Lab" light palette and the deep-ocean tokens (`bg_dark`, `deep`,
`ocean`, `cyan`, `cyan_soft`, `warm`, `alarm`) used by the dark layouts.

Two hard constraints:

- **Fonts must exist on the machine that opens the deck.** python-pptx cannot
  embed fonts, so a Google font named in the spec silently substitutes and the
  deck renders in something you never chose. Prefer `Segoe UI`, `Calibri`,
  `Arial` or `Consolas`, all of which are present on Windows. If the user wants
  a display face, say so rather than shipping a deck that looks different on
  their machine than it did on yours.
- **The validator flags anything below 10pt**, except the deliberately small
  footer and citation shapes, which are marked `chrome:` precisely so they do
  not generate noise.

Set `"dark": true` on `flow` to place it on the dark background. The dark
layouts paint their own canvas, so they do not use the standard header grid.

## Choosing content, not just layout

Read `references/design-rules.md` before writing a spec of any size: the type
scale, the six-bullets-six-words guideline, narrative arcs, chart conventions
(always label the unit; never truncate a bar axis), and the anti-patterns. The
script estimates fit and creates a normal package; that file guides editorial quality.

For anything with real evidence in it, read `references/free-assets.md` - it has
licence facts verified at source, and the attribution duties that follow.

## Rules that are not negotiable

- **Never lower a font below 12pt** to make text fit. Split the slide.
- **Never state a licence or attribution claim you have not checked** at the
  source. SlidesCarnival templates are CC BY 4.0 - a credit is mandatory.
- **Never fabricate a citation, statistic, quotation or number.** If the deck
  needs a figure you do not have, research it or leave it out. Label
  conceptual maps and diagrams as conceptual rather than implying they are
  authoritative.
- **Never scrape or script-download** templates from sites that require an
  account, and never bypass a paywall. Ask the user for the file.
- **Never claim a transition, chart or feature is present** without the
  validator confirming it.
- **Always run the validator** before telling the user the deck is ready.

## Fallback when python-pptx cannot be installed

If there is no package manager and no network, say so plainly rather than
producing a broken deck. A `.pptx` is a ZIP of OOXML parts, so a minimal deck
can be written with `zipfile` and string templates, but that path supports
almost none of the layouts above. Prefer asking the user to install
`python-pptx`.

If LibreOffice is present, `soffice --headless --convert-to pdf deck.pptx`
produces a PDF you can look at. Installed PowerPoint can also export PDF and PNG
slides. Structural validation does not replace looking at rendered slides; say
which checks you actually performed. `--strict` fails on warnings too. Missing
alt text and picture/text collisions are checked, bar axes start at zero, theme
backgrounds are explicit, and text that cannot fit at the floor raises rather
than silently returning the smallest font. Shorten content instead of hiding it.
