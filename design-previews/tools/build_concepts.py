"""Generate the three animated hero concepts (SVG source + motion spec).

Run: python design-previews/tools/build_concepts.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "design-previews"

W, H = 1200, 440
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',PingFang SC,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Consolas,monospace"

BLUE = "#60A5FA"
CYAN = "#22D3EE"
VIOLET = "#8B5CF6"
SUCCESS = "#34D399"
WHITE = "#F1F5F9"
MUTED = "#94A3B8"
DIM = "#64748B"

DEFS = f"""
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#090D1A"/>
      <stop offset="0.55" stop-color="#0D1526"/>
      <stop offset="1" stop-color="#111A2E"/>
    </linearGradient>
    <radialGradient id="halo" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="{BLUE}" stop-opacity="0.30"/>
      <stop offset="0.55" stop-color="{BLUE}" stop-opacity="0.08"/>
      <stop offset="1" stop-color="{BLUE}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="violetHalo" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="{VIOLET}" stop-opacity="0.38"/>
      <stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="vignette" cx="0.5" cy="0.42" r="0.78">
      <stop offset="0" stop-color="#000000" stop-opacity="0"/>
      <stop offset="0.62" stop-color="#000000" stop-opacity="0.12"/>
      <stop offset="1" stop-color="#000000" stop-opacity="0.40"/>
    </radialGradient>
    <linearGradient id="coreGrad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{BLUE}"/>
      <stop offset="0.55" stop-color="#8B5CF6"/>
      <stop offset="1" stop-color="{CYAN}"/>
    </linearGradient>
    <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{BLUE}" stop-opacity="0"/>
      <stop offset="0.5" stop-color="{CYAN}" stop-opacity="0.85"/>
      <stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/>
    </linearGradient>
  </defs>"""


def text(x, y, body, size, fill, weight="400", anchor="start", ls=None, family=SANS, extra=""):
    attrs = [f'x="{x}"', f'y="{y}"', f'font-size="{size}"', f'fill="{fill}"', f'font-weight="{weight}"']
    if anchor != "start":
        attrs.append(f'text-anchor="{anchor}"')
    if ls:
        attrs.append(f'letter-spacing="{ls}"')
    if extra:
        attrs.append(extra)
    return f'<text {" ".join(attrs)} font-family="{family}">{body}</text>'


def rect(x, y, w, h, rx=0, fill="none", stroke=None, sw=1, extra=""):
    attrs = [f'x="{x}"', f'y="{y}"', f'width="{w}"', f'height="{h}"']
    if rx:
        attrs.append(f'rx="{rx}"')
    attrs.append(f'fill="{fill}"')
    if stroke:
        attrs.append(f'stroke="{stroke}" stroke-width="{sw}"')
    if extra:
        attrs.append(extra)
    return f'<rect {" ".join(attrs)}/>'


def circle(cx, cy, r, fill="none", stroke=None, sw=1, extra=""):
    attrs = [f'cx="{cx}"', f'cy="{cy}"', f'r="{r}"', f'fill="{fill}"']
    if stroke:
        attrs.append(f'stroke="{stroke}" stroke-width="{sw}"')
    if extra:
        attrs.append(extra)
    return f'<circle {" ".join(attrs)}/>'


def line(x1, y1, x2, y2, stroke, sw=1.5, extra=""):
    return f'<path d="M{x1} {y1}L{x2} {y2}" fill="none" stroke="{stroke}" stroke-width="{sw}" {extra}/>'


def frame(title_id, desc_id, title, desc, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'role="img" aria-labelledby="{title_id} {desc_id}">\n'
        f'  <title id="{title_id}">{title}</title>\n'
        f'  <desc id="{desc_id}">{desc}</desc>\n'
        f"{DEFS}\n"
        f'  <rect width="{W}" height="{H}" fill="url(#bg)"/>\n'
        f"{body}\n"
        f'  <rect width="{W}" height="{H}" fill="url(#vignette)"/>\n'
        f"</svg>\n"
    )


def title_block(eyebrow, name, sub, meta):
    return "\n".join(
        [
            f'  <g id="title-block">',
            f"    {text(64, 120, eyebrow, 18, CYAN, weight='600', ls='4')}",
            f"    {text(64, 184, name, 54, WHITE, weight='700', ls='0.5')}",
            f'    <path d="M64 210H214" stroke="url(#edge)" stroke-width="2"/>',
            f"    {text(64, 250, sub, 23, MUTED)}",
            f"    {text(64, 330, meta, 19, DIM, family=MONO)}",
            f"  </g>",
        ]
    )


def badge(x, y, label, colour):
    return (
        f'<g><rect x="{x}" y="{y}" width="104" height="30" rx="15" fill="{colour}" fill-opacity="0.12" '
        f'stroke="{colour}" stroke-opacity="0.45"/>{text(x + 52, y + 20, label, 16, colour, weight="600", anchor="middle", ls="1")}</g>'
    )


# --------------------------------------------------------------------------------------
# A · AI orchestration: core, orbiting modules, convergence, output
# --------------------------------------------------------------------------------------

CORE = (876, 208)
ORBIT_R = 138
MODULES = [
    ("PPTX", -90, BLUE),
    ("DOCX", -30, CYAN),
    ("PDF", 30, VIOLET),
    ("XLSX", 90, BLUE),
    ("POSTER", 150, CYAN),
    ("RESEARCH", 210, VIOLET),
]


def module_positions():
    import math

    out = []
    for label, angle, colour in MODULES:
        rad = math.radians(angle)
        out.append((label, CORE[0] + ORBIT_R * math.cos(rad), CORE[1] + ORBIT_R * math.sin(rad), colour))
    return out


def module_node(x, y, label, colour):
    parts = [
        circle(x, y, 25, "#111A2E", stroke=colour, sw=1.4, extra='stroke-opacity="0.55"'),
        circle(x, y, 4, colour, extra='opacity="0.9"'),
        text(x, y + 46, label, 17, "#94A3B8", weight="600", anchor="middle", ls="1.2"),
    ]
    return "\n".join(parts)


def concept_a():
    nodes = module_positions()
    body = [title_block("AI EXECUTION ECOSYSTEM", "AWESOME SKILLS", "Six skills. One pipeline.", "v3.2.0  /  MIT  /  validated delivery")]
    body.append(f'  <ellipse cx="{CORE[0]}" cy="{CORE[1]}" rx="300" ry="200" fill="url(#halo)"/>')
    body.append(f'  <ellipse cx="1120" cy="70" rx="210" ry="130" fill="url(#violetHalo)"/>')
    # static chassis: the orbit survives every phase, so no frame reads as empty
    body.append(circle(CORE[0], CORE[1], 112, "none", stroke="#243253", sw=1, extra='stroke-opacity="0.7"'))
    body.append(circle(CORE[0], CORE[1], 150, "none", stroke="#1B2740", sw=1, extra='stroke-opacity="0.55" stroke-dasharray="2 9"'))
    for _, sx, sy, _ in module_positions():
        body.append(circle(sx, sy, 7, "#111A2E", stroke="#243253", sw=1))

    links = [
        line(
            round(CORE[0] + 78 * (x - CORE[0]) / ORBIT_R, 1),
            round(CORE[1] + 78 * (y - CORE[1]) / ORBIT_R, 1),
            round(x - 27 * (x - CORE[0]) / ORBIT_R, 1),
            round(y - 27 * (y - CORE[1]) / ORBIT_R, 1),
            "#22D3EE",
            1.2,
            'stroke-opacity="0.55"',
        )
        for _, x, y, _ in nodes
    ]
    body.append('  <g id="links">' + "".join(links) + "</g>")

    core = [
        circle(CORE[0], CORE[1], 74, "none", stroke="#33456B", sw=1.2, extra='stroke-opacity="0.75"'),
        circle(CORE[0], CORE[1], 50, "url(#coreGrad)"),
        f'<g transform="translate({CORE[0] - 24} {CORE[1] - 24}) scale(0.19)"><path fill="#090D1A" fill-opacity="0.82" d="M80 32H224V80H80V104H176L224 152V176L176 224H32V176H176V152H80L32 104V80Z"/></g>',
    ]
    body.append('  <g id="core">' + "".join(core) + "</g>")

    for index, (label, x, y, colour) in enumerate(nodes):
        body.append(f'  <g id="module-{index + 1}">{module_node(x, y, label, colour)}</g>')

    chips = []
    chip_w, chip_gap = 86, 12
    total = len(nodes) * chip_w + (len(nodes) - 1) * chip_gap
    start = CORE[0] - total / 2
    for index, (label, _, _, colour) in enumerate(nodes):
        x = start + index * (chip_w + chip_gap)
        chips.append(rect(x, 366, chip_w, 38, 10, "#111A2E", stroke="#33456B", sw=1))
        chips.append(circle(x + 16, 385, 3.5, colour))
        chips.append(text(x + 30, 391, label, 15, "#F1F5F9", weight="600"))
    body.append('  <g id="pipeline">' + "".join(chips) + "</g>")

    output = [
        rect(772, 156, 168, 104, 16, "#111A2E", stroke="#33456B", sw=1.2),
        rect(772, 156, 168, 6, 3, BLUE),
        text(796, 196, "DELIVERABLE", 14, "#22D3EE", weight="700", ls="2.4"),
        rect(796, 210, 118, 7, 3.5, "#22304D"),
        rect(796, 224, 84, 7, 3.5, "#1B2740"),
        circle(898, 240, 12, "#0B2A24", stroke=CYAN, sw=1.6),
        '<path d="M892 240L896 245L904 234" fill="none" stroke="#34D399" stroke-width="2"/>',
    ]
    body.append('  <g id="output">' + "".join(output) + "</g>")

    spec = {
        "width": W,
        "fps": 30,
        "duration": 5.0,
        "colors": 160,
        "dither": "none",
        "clip_to_base_alpha": True,
        "max_size_mb": 2.0,
        "reveals": [
            {"id": "links", "axis": "x", "start": 1.15, "end": 1.95, "exit": {"start": 2.4, "end": 2.76}},
        ],
        "layers": [
            {"id": "core", "enter": {"start": 0.05, "end": 1.0, "from": [0, 16]}, "exit": {"start": 2.45, "end": 2.85, "to": [0, -22]}},
            {"id": "module-1", "enter": {"start": 0.6, "end": 1.35, "from": [0, 12]}, "exit": {"start": 2.4, "end": 2.78, "to": [0, -18]}},
            {"id": "module-2", "enter": {"start": 0.75, "end": 1.5, "from": [0, 12]}, "exit": {"start": 2.4, "end": 2.78, "to": [0, -18]}},
            {"id": "module-3", "enter": {"start": 0.9, "end": 1.65, "from": [0, 12]}, "exit": {"start": 2.4, "end": 2.78, "to": [0, -18]}},
            {"id": "module-4", "enter": {"start": 1.05, "end": 1.8, "from": [0, 12]}, "exit": {"start": 2.4, "end": 2.78, "to": [0, -18]}},
            {"id": "module-5", "enter": {"start": 1.2, "end": 1.95, "from": [0, 12]}, "exit": {"start": 2.4, "end": 2.78, "to": [0, -18]}},
            {"id": "module-6", "enter": {"start": 1.35, "end": 2.1, "from": [0, 12]}, "exit": {"start": 2.4, "end": 2.78, "to": [0, -18]}},
            {"id": "pipeline", "enter": {"start": 2.6, "end": 3.3, "from": [0, 22]}, "exit": {"start": 4.45, "end": 4.95, "to": [0, 22]}},
            {"id": "output", "enter": {"start": 3.3, "end": 4.0, "from": [0, 16]}, "exit": {"start": 4.5, "end": 4.96, "to": [0, -16]}},
        ],
    }
    svg = frame(
        "title-a",
        "desc-a",
        "Awesome Skills — AI orchestration",
        "A central orchestrator core lights up, six skill modules appear around it, links activate, the modules converge into a pipeline and a validated deliverable appears.",
        "\n".join(body),
    )
    return svg, spec


# --------------------------------------------------------------------------------------
# B · Intelligence engine: stacked processing deck
# --------------------------------------------------------------------------------------

DECK_X, DECK_W = 620, 516
SLABS = [
    (78, "REGISTRY", "skills.json · six entries"),
    (144, "PLANNER", "dependency DAG · allowlisted"),
    (210, "EXECUTOR", "scripts · real exit codes"),
]


def concept_b():
    body = [title_block("INTELLIGENCE ENGINE", "AWESOME SKILLS", "Discover. Plan. Execute. Validate.", "v3.2.0  /  MIT  /  six packages")]
    body.append(f'  <ellipse cx="880" cy="180" rx="320" ry="220" fill="url(#halo)" opacity="0.8"/>')
    body.append(f'  <ellipse cx="1150" cy="60" rx="200" ry="120" fill="url(#violetHalo)" opacity="0.7"/>')

    deck = []
    for y, label, detail in SLABS:
        deck.append(rect(DECK_X, y, DECK_W, 58, 14, "#111A2E", stroke="#243253", sw=1))
        deck.append(rect(DECK_X, y, 3, 58, 2, CYAN, extra='opacity="0.7"'))
        deck.append(text(DECK_X + 24, y + 36, label, 18, "#F1F5F9", weight="700", ls="2"))
        deck.append(text(DECK_X + 176, y + 36, detail, 17, DIM, family=MONO))
    # the engine deck is the chassis: static, so no frame reads as an empty panel
    body.extend(deck)

    body.append(f'  <g id="packet">{rect(560, 104, 44, 22, 11, "#111A2E", stroke=CYAN, sw=1.2)}'
                f'{circle(572, 115, 3.4, CYAN)}{circle(586, 115, 3.4, CYAN)}</g>')

    ping = circle(DECK_X + 12, 115, 26, "none", stroke=CYAN, sw=1.4, extra='stroke-opacity="0.5"')
    ping += circle(DECK_X + 12, 115, 10, "none", stroke=CYAN, sw=1.2, extra='stroke-opacity="0.8"')
    body.append('  <g id="registry-ping">' + ping + "</g>")

    nodes = []
    for index in range(4):
        x = 668 + index * 96
        node = circle(x, 302, 13, "#111A2E", stroke=CYAN, sw=1.3, extra='stroke-opacity="0.85"')
        node += circle(x, 302, 4, CYAN)
        nodes.append(f'  <g id="node-{index + 1}">' + node + "</g>")
    body.extend(nodes)

    flow = [line(668, 302, 956, 302, "#2A3E66", 1.4, 'stroke-opacity="0.7"')]
    for x in (668, 764, 860, 956):
        flow.append(line(x, 268, x, 289, "#2A3E66", 1.2, 'stroke-opacity="0.6"'))
    body.append('  <g id="flow">' + "".join(flow) + "</g>")

    validated = [
        badge(1012, 288, "VALIDATED", SUCCESS),
    ]
    body.append('  <g id="validated">' + "".join(validated) + "</g>")

    tiles = []
    for index, label in enumerate(("PPTX", "DOCX", "PDF")):
        x = 640 + index * 168
        tiles.append(rect(x, 356, 152, 56, 12, "#111A2E", stroke="#33456B", sw=1))
        tiles.append(text(x + 18, 384, label, 16, "#94A3B8", weight="700", ls="1.6", family=MONO))
        tiles.append(rect(x + 18, 394, 84, 6, 3, "#22304D"))
        tiles.append(circle(x + 132, 386, 7, "#0B2A24", stroke=SUCCESS, sw=1.2))
        tiles.append(f'<path d="M{ x + 128 } 386L{x + 131} 389L{x + 136} 382" fill="none" stroke="{SUCCESS}" stroke-width="1.4"/>')
    body.append('  <g id="deliverables">' + "".join(tiles) + "</g>")

    spec = {
        "width": W,
        "fps": 30,
        "duration": 5.0,
        "colors": 192,
        "dither": "none",
        "clip_to_base_alpha": True,
        "max_size_mb": 2.0,
        "reveals": [
            {"id": "flow", "axis": "x", "start": 2.45, "end": 3.2, "exit": {"start": 4.4, "end": 4.85}},
        ],
        "layers": [
            {"id": "packet", "enter": {"start": 0.5, "end": 1.25, "from": [-90, 0]}, "exit": {"start": 1.5, "end": 1.95, "to": [40, 0]}},
            {"id": "registry-ping", "enter": {"start": 1.2, "end": 1.6, "from": [0, 0]}, "exit": {"start": 1.9, "end": 2.2, "to": [0, 0]}},
            {"id": "node-1", "enter": {"start": 1.95, "end": 2.3, "from": [0, 6]}, "exit": {"start": 4.4, "end": 4.8, "to": [0, -8]}},
            {"id": "node-2", "enter": {"start": 2.15, "end": 2.5, "from": [0, 6]}, "exit": {"start": 4.4, "end": 4.8, "to": [0, -8]}},
            {"id": "node-3", "enter": {"start": 2.35, "end": 2.7, "from": [0, 6]}, "exit": {"start": 4.4, "end": 4.8, "to": [0, -8]}},
            {"id": "node-4", "enter": {"start": 2.55, "end": 2.9, "from": [0, 6]}, "exit": {"start": 4.4, "end": 4.8, "to": [0, -8]}},
            {"id": "validated", "enter": {"start": 3.2, "end": 3.7, "from": [0, 10]}, "exit": {"start": 4.45, "end": 4.85, "to": [0, -10]}},
            {"id": "deliverables", "enter": {"start": 3.55, "end": 4.25, "from": [0, 20]}, "exit": {"start": 4.55, "end": 4.97, "to": [0, 20]}},
        ],
    }
    svg = frame(
        "title-b",
        "desc-b",
        "Awesome Skills — intelligence engine",
        "A data packet enters a three-layer engine: registry, planner and executor. Four processing nodes activate in sequence, paths connect, validation completes and three deliverables emerge.",
        "\n".join(body),
    )
    return svg, spec


# --------------------------------------------------------------------------------------
# C · Creative automation: workspace of modules, research stream, deliverables
# --------------------------------------------------------------------------------------

CARDS = [
    ("PowerPoint", "Deck JSON → PPTX", BLUE),
    ("Word", "Doc JSON → DOCX", CYAN),
    ("PDF", "Extract · fill", VIOLET),
    ("Excel", "Template → XLSM", CYAN),
    ("Poster", "HTML → print PNG", BLUE),
    ("Research", "Shared pipeline", VIOLET),
]


def concept_c():
    body = [title_block("CREATIVE AUTOMATION", "AWESOME SKILLS", "One ecosystem. Multiple capabilities.", "v3.2.0  /  MIT  /  six skills")]
    body.append(f'  <ellipse cx="900" cy="210" rx="330" ry="210" fill="url(#halo)" opacity="0.55"/>')
    body.append(rect(608, 76, 552, 252, 20, "#0D1526", stroke="#1B2740", sw=1))
    body.append(rect(608, 76, 552, 6, 3, VIOLET, extra='opacity="0.5"'))

    stream = line(596, 340, 1148, 340, "#2A3E66", 1.4, 'stroke-dasharray="6 9" stroke-opacity="0.75"')
    for marker in (700, 820, 940, 1060):
        stream += circle(marker, 340, 2.6, CYAN)
    body.append('  <g id="stream">' + stream + "</g>")

    for index, (label, detail, colour) in enumerate(CARDS):
        col = index % 3
        row = index // 3
        x = 632 + col * 172
        y = 100 + row * 108
        card = [
            rect(x, y, 152, 88, 14, "#111A2E", stroke="#22304D", sw=1),
            rect(x, y, 152, 3, 1.5, colour, extra='opacity="0.8"'),
            text(x + 18, y + 38, label, 19, "#F1F5F9", weight="700"),
            text(x + 18, y + 60, detail, 14, DIM, family=MONO),
            circle(x + 18, y + 74, 2.6, colour),
        ]
        body.append(f'  <g id="card-{index + 1}">' + "".join(card) + "</g>")

    for index, label in enumerate(("PPTX", "DOCX", "PDF")):
        x = 640 + index * 168
        tile = [
            rect(x, 356, 152, 54, 12, "#111A2E", stroke="#33456B", sw=1),
            text(x + 18, 380, label, 16, "#94A3B8", weight="700", ls="1.6", family=MONO),
            rect(x + 18, 390, 78, 6, 3, "#22304D"),
            circle(x + 130, 384, 7, "#0B2A24", stroke=SUCCESS, sw=1.2),
            f'<path d="M{x + 126} 384L{x + 129} 387L{x + 134} 380" fill="none" stroke="{SUCCESS}" stroke-width="1.3"/>',
        ]
        body.append(f'  <g id="deliverable-{index + 1}">' + "".join(tile) + "</g>")

    spec = {
        "width": W,
        "fps": 30,
        "duration": 5.0,
        "colors": 192,
        "dither": "none",
        "clip_to_base_alpha": True,
        "max_size_mb": 2.0,
        "reveals": [
            {"id": "stream", "axis": "x", "start": 0.35, "end": 1.15, "exit": {"start": 4.4, "end": 4.85}},
        ],
        "layers": [
            {"id": f"card-{i + 1}", "enter": {"start": 0.55 + i * 0.16, "end": 1.25 + i * 0.16, "from": [0, 14]},
             "exit": {"start": 4.45, "end": 4.9, "to": [0, 14]}}
            for i in range(6)
        ]
        + [
            {"id": "deliverable-1", "enter": {"start": 2.75, "end": 3.35, "from": [0, 18]}, "exit": {"start": 4.5, "end": 4.95, "to": [0, 18]}},
            {"id": "deliverable-2", "enter": {"start": 2.95, "end": 3.55, "from": [0, 18]}, "exit": {"start": 4.5, "end": 4.95, "to": [0, 18]}},
            {"id": "deliverable-3", "enter": {"start": 3.15, "end": 3.75, "from": [0, 18]}, "exit": {"start": 4.5, "end": 4.95, "to": [0, 18]}},
        ],
    }
    svg = frame(
        "title-c",
        "desc-c",
        "Awesome Skills — creative automation",
        "A workspace panel holds six skill modules: PowerPoint, Word, PDF, Excel, Poster and Research. A research stream feeds them and three checked deliverables assemble below.",
        "\n".join(body),
    )
    return svg, spec


CONCEPTS = {
    "concept-a-ai-orchestration": concept_a,
    "concept-b-intelligence-engine": concept_b,
    "concept-c-creative-automation": concept_c,
}


def main() -> None:
    for name, builder in CONCEPTS.items():
        svg, spec = builder()
        folder = OUT / name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "hero.svg").write_text(svg, encoding="utf-8")
        (folder / "hero-motion.json").write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {folder.relative_to(ROOT)}/hero.svg + hero-motion.json")


if __name__ == "__main__":
    main()
