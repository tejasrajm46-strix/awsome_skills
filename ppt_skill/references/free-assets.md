# Free Templates, Images and Icons

## The default is: build from scratch

`build_deck.py` theming a blank presentation is the right answer most of the
time, and it is the only option that is offline, deterministic, and free of any
attribution duty. Reach for an external template when the user explicitly hands
you one, or when they ask for a look you cannot get from the theme tokens.

If the user gives you a `.pptx` to match, pass it as `--base`:

```bash
python scripts/build_deck.py spec.json -o deck.pptx --base brand-template.pptx
```

The deck is forced to 16:9 either way, and the builder draws on the base's blank
layout, so the base contributes its theme fonts and colours.

Do not scrape, script-login, or bypass paywalls to obtain a template. Download
the file by hand from the site's own download link, or ask the user for it.

## Licence facts worth getting right

Verified against each source's own terms, but **re-check at the source before
you ship anything commercial** - these change.

| Source | Licence | Attribution? |
|--------|---------|--------------|
| [SlidesCarnival](https://www.slidescarnival.com/terms-of-use) | Creative Commons Attribution 4.0 International (CC BY 4.0) | **Required.** Personal and commercial use both OK, but you must keep the credit. |
| [SlidesGo](https://slidesgo.com/) | Free tier is free for use; premium templates are not | Check per template. Free tier is generally used with a link-back. |
| [FPPT](https://www.free-power-point-templates.com/) | Site states templates are free for commercial and education use | None stated |
| [Google Slides template gallery](https://docs.google.com/presentation/u/0/?ftv=1) | Free to Google Workspace users under Google's terms | None |
| [Microsoft Create / Office templates](https://create.microsoft.com/) | Free under Microsoft's terms | None |
| [Pexels](https://www.pexels.com/license/) | Pexels licence - free for personal and commercial use | Not required (appreciated) |
| [Unsplash](https://unsplash.com/license) | Unsplash licence - free for commercial and non-commercial use | Not required. Note Unsplash+ images have a separate licence. |
| [The Noun Project](https://thenounproject.com/) | Per-icon: public domain or CC BY | **CC BY icons require crediting the creator.** Paid licence removes it. |

Two practical consequences:

1. **SlidesCarnival forces a credit.** If you use one, add it. The `closing`
   and `bullets` layouts both take a free-text field you can use:
   `"credit": "Slides template by SlidesCarnival.com (CC BY 4.0)"` or
   `"source": "Template: SlidesCarnival.com (CC BY 4.0)"`.
2. **Images of real people need care** even under a permissive licence. A model
   release covers the photographer, not your use of someone's face next to a
   claim they never made.

## When a deck cites real evidence

For anything research-flavoured, cite the sources rather than the assets:

- Put the citation on the slide that uses it via `"source"` - it renders
  right-aligned above the footer rule, where it is legible but not competing
  with the content.
- Put the primary URLs on the final slide as `bullets`.
- Prefer the primary source (paper, patent, manufacturer datasheet) over a
  news article about it. If the deck says "the 2014 Nobel Prize in Physics",
  the citation is nobelprize.org, not a blog.
- Do not round, extrapolate, or sharpen a number to make it punchier. If a
  figure is contested or approximate, say so in the text.

## Icons and imagery

`build_deck.py` does not fetch stock photos or icons. That is deliberate: an
automatic fetch can create licensing and reliability issues, and shape-drawn
diagrams often communicate structure better than clip art.

If an input PPTX/DOCX contains reusable pictures, the bundled
`scripts/extract_office_assets.py` can create a small, deduplicated local
shortlist and HTML contact sheet. It records source-slide usage and audits
whether selected candidates are referenced in the supplied spec. Run it only
on files the user provided or authorized you to inspect; select assets by actual
relevance and visual quality, not resolution alone. The ranking is technical
triage, not semantic understanding or rights clearance. Raster assets (PNG,
JPEG, GIF, BMP) are supported; vector media remain in the source package and
are reported as unsupported rather than silently converted.

For web research, use a structured search interface with user authorization or
a reputable image API, small query-specific result limits, preview/thumbnail
triage, and full-resolution download only for selected results. Keep title,
creator, source page, direct media URL, licence and attribution with the asset.
Do not scrape Google Images result pages, evade access controls, or assume a
search result itself grants reuse rights. Cache only by a stable content/source
identity with freshness/rights metadata, and refresh when the task or licence
requires it. Use the `image` layout for selected photos and caption them.
