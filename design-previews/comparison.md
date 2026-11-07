# Three animated hero concepts — Arctic Graphite

Three GitHub-safe motion graphics for the Awesome Skills README, built with the
`beautify-github-readme` Skill: an editable static SVG source, a layer-timing
spec, and a GIF rendered at 30 FPS from that spec, all on one palette.

`README.md` is untouched. Nothing here is embedded.

## Palette — Arctic Graphite

| Colour | Hex | Role in the concepts |
| --- | --- | --- |
| Graphite Black | `#15191E` | Background base |
| Steel | `#252D35` | Cards, panels, sockets, engine deck |
| Arctic Teal | `#00B8A9` | Connections, execution rails, eyebrows, module dots |
| Ice Mint | `#83E6CE` | Pipeline row, highlights, success checks |
| Silver | `#C5D0D8` | Stage labels and secondary text |
| Cloud White | `#F4F7F8` | Titles and card labels |
| Amber | `#FFB454` | Emphasis: deliverable header, VALIDATED pill, workspace bar |

All seven appear in each of the three SVGs. The remaining values are graphite
hairlines and shading tints (`#2E3841`, `#2C353D`, `#3A4750`, `#38444E`), a silver
shade for metadata (`#7C8B96`), a dark teal well behind the checks (`#132B27`),
one background mid-stop (`#1A1F25`) and the black vignette stop.

## A · AI orchestration — "AI EXECUTION ECOSYSTEM"

![Concept A — AI orchestration](concept-a-ai-orchestration/preview.png)

<img src="concept-a-ai-orchestration/hero.gif" width="100%" alt="Animated hero: a teal orchestrator core lights up, six skill modules appear around it, links activate, the modules converge into a pipeline and an amber-accented deliverable appears">

The orchestrator core lights with the Relay S, six skill modules resolve around
it, the teal links activate, the modules collapse into a mint pipeline row, and
an amber-headed, mint-checked deliverable lands in the core. The orbit ring and
module sockets are static, so no frame reads as an empty panel.

- 1200 × 440 · 150 frames · 30 FPS · 5.00 s · **1.94 MB** · 144 colours
- Layers: 9 animated, 1 reveal · seam pixel-identical between last and first frame

## B · Intelligence engine — "DISCOVER. PLAN. EXECUTE. VALIDATE."

![Concept B — intelligence engine](concept-b-intelligence-engine/preview.png)

<img src="concept-b-intelligence-engine/hero.gif" width="100%" alt="Animated hero: a data packet enters a registry, planner and executor deck, four teal nodes activate, paths connect, an amber VALIDATED pill settles and three checked deliverables emerge">

A data packet enters, pings the registry, then four teal nodes light in sequence
on the executor bus. Paths connect, the amber VALIDATED pill settles, and three
mint-checked deliverables rise. The three-layer deck is static, so every frame
reads as a complete system and the file stays small.

- 1200 × 440 · 150 frames · 30 FPS · 5.00 s · **0.59 MB** · 192 colours
- Layers: 8 animated, 1 reveal · seam pixel-identical

## C · Creative automation — "ONE ECOSYSTEM. MULTIPLE CAPABILITIES."

![Concept C — creative automation](concept-c-creative-automation/preview.png)

<img src="concept-c-creative-automation/hero.gif" width="100%" alt="Animated hero: six module cards for PowerPoint, Word, PDF, Excel, Poster and Research enter a steel workspace panel under an amber bar, a teal research stream runs beneath them and three checked deliverables assemble">

Six real module cards — PowerPoint, Word, PDF, Excel, Poster, Research — enter the
steel workspace panel under an amber bar, the teal research stream runs beneath
them, and three mint-checked deliverables assemble.

- 1200 × 440 · 150 frames · 30 FPS · 5.00 s · **0.94 MB** · 192 colours
- Layers: 9 animated, 1 reveal · seam pixel-identical

## Comparison

| Criterion | A · Orchestration | B · Intelligence engine | C · Creative automation |
| --- | --- | --- | --- |
| Cinematic quality | Highest: glowing core, radial depth, converging modules | High: restrained, technical, less spectacle | Medium: tidy product board |
| Motion smoothness | Calm ease-outs; six staggered entrances | Calmest; four discrete node activations | Calm; six staggered card entrances |
| Project identity | Strong — Relay S in the core, six named skills | Strongest — registry, planner, executor are the real architecture | Strong — all six categories plus deliverables |
| Typography | 54 px title, 17–18 px labels | 54 px title, 17 px mono detail | 54 px title, 19 px cards, 14 px detail |
| Readability in motion | Labels legible at 900 px; captions small at 360 px | Best at 360 px: short labels, static deck | Good at 900 px; 14 px detail is metadata only |
| Animation file size | 1.94 MB | 0.59 MB | 0.94 MB |
| Palette fidelity | 7/7 colours | 7/7 | 7/7 |
| GitHub compatibility | GIF + static SVG fallback; no CSS, filters or remote refs | Same | Same |
| Mobile appearance | Orbit stays readable; captions become text-like | Deck stacks legibly; nodes stay clear | Cards stay legible; detail lines soften |
| Seamless looping | Verified identical first/last frame | Verified identical | Verified identical |

## Recommendation

**Ship A as the hero.** It is the only concept that states both halves of the
product — six skills and one orchestrated pipeline — inside a single loop, and
the Relay S in the core keeps the repository's identity rather than a generic AI
look. At 1.94 MB it fits the 2 MB budget with little headroom.

Keep **B** if a second, smaller visual is wanted further down the page: the most
technically honest architecture, the best mobile legibility, 0.59 MB. **C** is the
right choice only if the README is repositioned as a product page for the six
capabilities rather than the orchestration system.

## Production notes and limits

- **Rasterizer substitution.** The Skill's renderer shells out to `rsvg-convert`
  or macOS `sips`; neither exists on this Windows host. Only that step was
  replaced with headless Chrome (`--default-background-color=00000000` for
  transparency). Layer extraction, timing, easing, chroma flattening, palette
  generation and GIF encoding are the Skill's own `render_motion_gif.py`.
- **GitHub cannot animate SVG.** The GIF is the playable asset; each `hero.svg`
  is the editable source and static fallback. No `<style>`, `foreignObject`,
  script, filter or remote reference is used.
- **Colour budget.** Dither is off. A uses 144 colours because 160 colours landed
  at exactly 2.00 MB; B and C use 192. The backgrounds are gradients, so banding
  is possible on some displays.
- **Stills are real frames** extracted from each GIF (A at 2.1 s, B at 4.2 s,
  C at 3.9 s), not separately rendered.
- **Not yet watched end to end by a human.** Smoothness was checked by sampling
  frames at 0, 0.8, 2.0, 3.2, 4.0 and 5.0 s and by confirming the seam; the
  animation should be played once before publishing.
