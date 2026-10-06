# Deck spec and layout reference

Loaded on demand. [`SKILL.md`](../SKILL.md) carries the workflow; this file carries
the two tables you need while writing a spec, plus the map of which script owns
what.

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

For a process with explicit source/context → action → outcome, use the native
`sequence` or `flow` layout before reaching for unrelated photos. For a
comparison that must fit a single page, use `compare`; for substantive evidence
or a topic-specific hero, use a relevant image slide and a short caption. The
image extractor is an inventory/shortlist step—not an auto-insertion feature.
A selected asset must be explicitly referenced by an `image` slide or an image
block in a companion Word spec; otherwise it remains unused by design.

## How the scripts fit together

The workflow is a pipeline of small parts, not one program, because each part
answers a different question and each can be run and tested alone:

| File | Owns |
|------|------|
| `scripts/textmetrics.py` | Text and table measurement. The single owner of "how many lines does this need, how tall is that row, how wide is that column". No python-pptx import, so it is testable alone. |
| `scripts/build_deck.py` | Spec JSON -> `.pptx`. Layout, theme tokens, freeform geometry. Imports its measurements from `textmetrics` and never re-derives them. |
| `scripts/extract_office_assets.py` | Bounded PPTX/DOCX embedded-raster shortlist, SHA-256 deduplication, source-slide tracking, contact sheet and spec-use audit. No network or external dependencies. |
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
