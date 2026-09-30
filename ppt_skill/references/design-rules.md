# Slide Design Rules

Read this when you are writing a spec and need to decide *what* goes on each
slide. The `build_deck.py` script enforces geometry and overflow for you; this
file is about the editorial decisions the script cannot make.

## The geometry you are designing against

```
  0.85in margin                                     0.85in margin
  +-------------------------------------------------------------+
  |                                                             |
  |  KICKER (running section, small caps, accent)      y=0.56   |
  |  Slide title, 30pt bold, navy                     y=0.90   |
  |  ==accent rule==                                  y=1.74   |
  |                                                             |
  |  content region  11.63in wide x 4.26in tall       y=2.10   |
  |                                                             |
  |  source line (optional, italic, right)            y=6.30   |
  |  ----------------------------- hairline --------- y=6.60  |
  |  deck title (footer)                     slide # y=6.70   |
  +-------------------------------------------------------------+
```

Every content slide reserves the kicker row even when there is no kicker, so
titles land on the same baseline throughout the deck. That consistency is the
cheapest way to make a deck look professionally made.

## Type scale

| Role | Size | Notes |
|------|------|-------|
| Slide title | 30pt bold | one line if possible, two maximum |
| Section number | 96pt | pure decoration on divider slides |
| Stat value | 26-46pt | auto-shrinks by value length |
| Quote | 18-30pt | auto-fits |
| Column / band heading | 16-17pt bold | |
| Body bullets | 12-20pt | auto-fits, never below 12pt |
| Card label, source, footer | 9-13pt | 10pt is the legibility floor |

The builder picks the largest body size that fits, so you should write the
content you mean and let it size. If a slide comes back at 12pt, that is a
signal the slide is carrying too much text - split it rather than shrink it.

## Structure

**A title is a claim, not a label.** "InGaN: The Missing Blue" beats
"Background". The title is the only element guaranteed to be read.

**One idea per slide.** If you cannot name the slide's single takeaway in a
sentence, it is two slides.

**Six bullets, six words.** Aim for <= 6 bullets and <= ~12 words per bullet.
The hard ceiling is what fits at 12pt; the quality ceiling is much lower.

**Do not put the same content in the kicker and the title.** The kicker is the
*running section* ("The Race for Blue"), the title is *this slide's point*.

**Narrative arc for a research or history deck:**
title -> why it matters -> the obstacle -> the breakthrough -> the mechanism
-> the evidence -> the aftermath -> sources.

## Choosing a layout

| You have | Use | Because |
|----------|-----|---------|
| A short, punchy sentence | `quote` | breaks the rhythm of bullet slides |
| 2-4 numbers worth remembering | `stats` | numbers need scale contrast to land |
| A sequence with dates | `timeline` | 2-6 items; split if more |
| Structure with layers | `stack` | the only text layout that shows containment |
| A measured trend | `chart` | native charts stay editable |
| Comparison of two options | `two_column` | side-by-side forces parallel phrasing |
| Data with more than one dimension | `table` | max ~5 columns; rows are sized to their tallest cell |
| A real photograph | `image` | one image, full attention, always captioned |

Vary the rhythm: a deck of eight identical bullet slides reads as a wall.
Alternate bullets, then a stat slide, then a chart, then a quote.

## Color

The default theme is the "Research Lab" palette: navy `#1E3A5F` for structure,
blue `#2563EB` for emphasis, amber `#A16207` for the third series, cool grey
`#E9EEF5` panels on white. It is deliberately restrained - colour carries
*hierarchy*, not decoration.

- Navy = structure (titles, headers, structure bands).
- Accent blue = the thing the eye should land on (the key number, the node,
  the highlight).
- Amber = the third data series only, so it stays remarkable.
- Never encode meaning in colour alone. "The blue one is worse" is invisible to
  a colour-blind reader and in a greyscale print-out - name it in the text too.

Contrast: body text `#0F172A` on white is ~17:1, and white on navy is ~11:1.
If you introduce a custom colour, keep body text at 4.5:1 or better.

## Charts

Charts are native PPTX objects, so the recipient can retype a number or switch
the chart type. Keep them simple:

- One message per chart. Pick `line` for trends over time, `bar` for comparing
  categories, `hbar` when category names are long, `pie` only for 2-4 shares
  that add to 100.
- Always give the axis a unit via `"unit": "lumens per watt"`. An unlabelled
  axis is a chart nobody can quote.
- Put the takeaway in the slide *title*, not the chart title, and repeat it in
  a bullet beside the chart. The reader should get the point even if they skip
  the chart.
- Start a bar axis at zero. Truncated axes flatter your argument and destroy it
  the moment someone competent reads it.

## Tables

A table is a grid of text, and PowerPoint treats a declared row height as a
*minimum* - it grows the row until the text fits. That is how a table silently
grows down the slide and lands on the footer. `build_deck.py` measures every
cell before choosing the height, so the table you get is the table you saw in
the spec. Three consequences worth designing around:

- **A row is as tall as its worst-wrapping cell.** Do not balance row lengths by
  eye; write the real text and let the measurement set the height.
- **Columns get space in proportion to their content**, with a floor so a short
  "label" column still reads as a label instead of wrapping over three lines.
  Keep headers and cells short in the first column and let the prose columns be
  wide.
- **Beyond five columns the type would have to go below 12pt.** The builder
  raises rather than shrinking below the legibility floor, so six columns is a
  slide to split, not a table to squeeze.

## Speaker notes

Write `notes` for every substantive slide. This is where the detail goes - the
caveat, the number you could not fit, the transition to the next slide. A deck
that is a wall of text on screen is a deck nobody reads; a slide with tight text
and rich notes is a talk.

## Anti-patterns

- Text that fits only because it is 9pt.
- A title slide with no subtitle, so the audience does not know the angle.
- "Agenda" slides that list section names - the section dividers already do it.
- Claiming more precision than the source: "50%" when the source says "about half".
- Reusing one layout six times.
- Charts without units, tables without row meaning.

## Dark decks and diagram craft

Some subjects want a dark canvas: an ocean, a night sky, a machine interior.
The bundled dark layouts (`hero`, `statement`, `hero_stat`, `network`,
`forces`, `cutaway`, and `flow` with `"dark": true`) paint their own
background, so they do not use the light header grid.

- Alternate light and dark rather than stacking dark slides together. Three
  dark slides in a row read as one very long slide.
- On a dark background, a glow is made by stacking the same path several times
  with decreasing width and increasing brightness - not with transparency,
  which `python-pptx` cannot set without hand-writing DrawingML. `build_deck.py`
  exposes this as `_cable_glow()` plus the `mix()` colour blend; reuse them
  rather than inventing a per-slide effect.
- Grid lines and route arcs behind type must stay below roughly 15% luminance
  against the background, or they compete with the words instead of supporting
  them.
- Reserve one accent (here, cyan) to mean *look here*. A second colour for a
  warning state is fine, but a warning colour should appear exactly once in the
  deck - the moment it appears twice it stops signalling anything.

When a band carries more than one column of text (a label, a note, and a marker
on the right), the columns must be laid out from one set of measurements so they
cannot overlap. A note box sized as a percentage of the slide width will run into
the marker as soon as someone writes a long note; the fix is to give the note
exactly the space between the label column and a reserved gutter, which is what
`l_stack` now does. Any new multi-column band should do the same.

Diagrams beat clip art for anything structural. A cross-section, a cutaway with
callouts, a labelled chain, and a node graph between them cover almost every
technical explanation - and all four stay editable in PowerPoint. Two rules:
every diagram gets a scale-honesty note ("conceptual - not to scale") when it is
not to scale, and every node gets a text label rather than relying on colour to
distinguish it.

Sources belong on the chart, table or diagram that uses them, not only on a
final references slide. A reader who screenshots one slide should still be able
to see where its numbers came from.
