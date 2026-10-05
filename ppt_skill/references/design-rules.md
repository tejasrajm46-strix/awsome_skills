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

## Optional reference treatment: problem → solution → journey

The supplied reference is a **specific slide treatment**, not a replacement theme
or a new default. Use it only when the story genuinely compares a problem with
its proposed response and then explains a workflow. Keep the user's selected
PowerPoint theme and apply this composition only to the relevant slide; other
users and topics should retain their own visual language.

The PowerPoint theme-gallery reference also matters: theme is a user choice, not
an engine's permanent house style. If the user supplies a deck or names a theme,
follow that preference. If no style is specified and the choice would materially
change the result, offer a small set of styles (for example: clean light,
corporate, or dark editorial) rather than silently imposing this sample. Map the
chosen theme's colors and installed fonts into the spec tokens; do not claim
`--base` transfers every visual feature—the bundled builder appends slides and
its layouts draw explicit geometry/colors.

1. **Pair the story, not the paragraphs.** Use two equal-width rounded panels
   across the top: left = 2–3 short problem/impact statements; right = 2–3
   matched solution/capability statements. Pair each heading and sentence
   deliberately. Avoid one large wall of text per panel.
2. **Add one shared journey strip below.** Use 5–7 concise, equal-size stages
   with simple native icons or editable shapes, directional connectors and one
   clearly distinguished outcome. Every label stays inside its own card; stage
   names are short enough not to wrap awkwardly. If the deck contains no actual
   end-to-end journey, omit this strip rather than inventing steps.
3. **Keep visual hierarchy restrained.** Keep the reference's clear title,
   two-panel comparison and bottom flow. Preserve the user's chosen fonts,
   palette and slide dimensions; use a single accent for the outcome, high
   contrast, even margins and consistent gaps. Rounded cards and shadows are
   optional; use them only if they fit the rest of the deck.
4. **Fit before decorate.** Make the long content readable by editing for
   concise matched statements and checking actual box dimensions. Do not shrink
   type excessively to force the sample's amount of copy into the panel. Avoid
   orphan connector labels, clipped captions, collisions between headings and
   descriptions, and arrows that appear to enter the wrong card.
5. **Quality gate.** Check the two panels align at top and bottom, panel headings
   and copy have consistent spacing, journey cards share a baseline, arrows are
   centred, and the outcome is visibly the final stage. Run the saved-deck
   validator, then inspect a rendered slide at presentation size. The user's
   reference is a layout cue—not an asset to copy, and not permission to alter
   unrelated slides or the deck-wide style.

Suggested content model (adapt to the real narrative, not a required schema):

```text
[PROBLEM]                        [PROPOSED SOLUTION]
Access gap                       Capability 1
Quality uncertainty              Capability 2
Operational/productivity impact  Capability 3

[Stage 1] → [Stage 2] → [Stage 3] → [Outcome]
```

Use the built-in `two_column` for the paired comparison and `sequence` for a
short bottom journey when that is sufficient. Reuse of the visual treatment
doesn't require a new PPT builder layout; build one-off native shapes only when
the composition needs them.

## Quick style selection, not a forced style

- **Research/report:** restrained light palette, source line, evidence chart or
  figure; give notes the detail that would clutter the slide.
- **Pitch/problem-solution:** optionally use the reference treatment above for
  the comparison and journey—not as a deck-wide template.
- **Technical explainer:** editable labelled diagrams, a few carefully chosen
  photos only when they add evidence or context.
- **Photo-led/storytelling:** give a purposeful visual the room; do not add a
  flow diagram just to make a slide look busy.

A design reference answers *how to arrange this story*; the audience, subject,
and user-provided theme still decide which story and style to use.

## Fast research and asset triage

Normal requests should use a fast, bounded research path—not “collect everything
and summarize later.” First identify 3–6 questions the output must answer. Run
independent, focused searches concurrently; inspect at most five strong primary
or authoritative sources for routine factual work. Keep a compact evidence
register (source URL/title/date, extracted fact, claim/slide using it), deduplicate
repeated facts, and stop when each important claim has support. Widen the search
only for disputed, high-stakes, or explicitly deep-research work. Speed must not
come from skipping source checks.

For outside images, issue several purpose-labelled queries in parallel (hero,
component, process/diagram), cap each around 10 candidates, filter metadata and
thumbnails before downloading full files, remove URL/content duplicates, and
usually choose only the 1–5 visuals that improve comprehension. Store source,
creator, URL, rights/attribution, dimensions and retrieval date with the selected
file. Cache retrieved research/assets for the current project and reuse them
across paired PPT/DOCX outputs; check freshness and licence terms before reuse.
Do not crawl every result page or scrape a search-engine image-result page.

## Embedded assets: select and place, don't just extract

If media have been extracted, treat that as the start of selection—not the
finished result. Use the contact sheet to check relevance, legibility, crop and
visual quality; then explicitly place useful choices in the deck spec or leave
them out with a reason. Prefer a smaller, coherent set over a folder of unused
images. Never infer legal reuse permission from presence inside a file.
The local helper only shortlists raster images by resolution, broad aspect-ratio
suitability and reuse count; it is not a web crawler, semantic image model or
rights checker. See `references/free-assets.md` before introducing outside art.

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
