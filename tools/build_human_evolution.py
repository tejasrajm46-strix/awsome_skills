#!/usr/bin/env python3
"""Generate the human-evolution example; no source facts live in this script."""
import json
import sys
from html import escape
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ppt_skill/scripts"))
sys.path.insert(0, str(ROOT / "word_skill/scripts"))
from build_deck import build as build_deck
from build_doc import build as build_doc
from transitions import add_transitions as apply_transitions


def infographic(data, out):
    """Two independently labelled linear axes prevent compressed recent history."""
    width, height = 2200, 870
    bg, ink, muted, accent = "#FAF8F3", "#163D38", "#53615C", "#176B60"
    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img"><title>Overlapping human histories</title><desc>Selected approximate fossil ranges, not an ancestry tree. Deep-time and recent-time panels have separate linear scales.</desc><rect width="100%" height="100%" fill="{bg}"/>']
    fonts = Path("C:/Windows/Fonts")

    def text(x, y, value, size=30, colour=ink, bold=False):
        path = fonts / ("calibrib.ttf" if bold else "calibri.ttf")
        if not path.exists():
            raise RuntimeError("Calibri not available; choose a verified installed font")
        font = ImageFont.truetype(str(path), size)
        draw.text((x, y), value, font=font, fill=colour)
        svg.append(f'<text x="{x}" y="{y + size * .78}" fill="{colour}" font-family="Calibri, Arial, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}">{escape(value)}</text>')

    def line(x1, y1, x2, y2, colour, thickness=3):
        draw.line((x1, y1, x2, y2), fill=colour, width=thickness)
        svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{colour}" stroke-width="{thickness}"/>')

    def bar(x1, x2, y, colour):
        draw.rounded_rectangle((x1, y, x2, y + 18), radius=10, fill=colour)
        svg.append(f'<rect x="{x1}" y="{y}" width="{x2 - x1}" height="18" rx="10" fill="{colour}"/>')

    text(65, 40, "OVERLAPPING HUMAN HISTORIES", 56, bold=True)
    text(65, 103, "Selected ranges show coexistence—not a straight line of ancestry.", 40, muted)
    panels = [(65, 1020, 4.0, [4, 3, 2, 1, 0], "DEEP TIME / million years ago", data["ranges"]),
              (1200, 920, .5, [.5, .4, .3, .2, .1, 0], "ZOOM / thousand years ago", data["ranges"][1:])]
    for left, span, maximum, ticks, title, ranges in panels:
        text(left, 180, title, 42, bold=True)
        axis_y = 278
        line(left, axis_y, left + span, axis_y, "#B4C9BE")
        for tick in ticks:
            x = round(left + span * (1 - tick / maximum))
            line(x, axis_y - 8, x, 723, "#DEE6DF", 2)
            label = "NOW" if tick == 0 else str(int(tick * (1000 if maximum == .5 else 1)))
            text(x - (45 if tick == 0 else 22), 235, label, 40, muted)
        for i, item in enumerate(ranges):
            y = 320 + i * (115 if maximum == 4 else 150)
            text(left, y, item["name"], 44, bold=True)
            label = item["short_label"]
            text(left, y + 45, label + f'  [{item["source"]}]', 40, muted)
            start, end = min(item["start"], maximum), item["end"]
            x1 = round(left + span * (1 - start / maximum))
            x2 = round(left + span * (1 - end / maximum))
            bar(x1, max(x2, x1 + 6), y + 88, accent if item["end"] == 0 else "#9B5B28")
    line(1127, 184, 1127, 735, "#C7D7CE")
    text(65, 813, "Approximate ranges • Separate linear scales • Not an ancestry tree • Sources [2–5]", 40, muted)
    svg.append("</svg>")
    image.save(out / "human-evolution-infographic.png", dpi=(240, 240))
    (out / "human-evolution-infographic.svg").write_text("\n".join(svg), encoding="utf-8")


def main():
    data = json.loads((ROOT / "examples/human-evolution.json").read_text(encoding="utf-8"))
    out = ROOT / "outputs/human-evolution"
    out.mkdir(parents=True, exist_ok=True)
    infographic(data, out)
    sources = data["sources"]
    doc = {**data["word"], "title": data["title"], "subtitle": data["subtitle"], "theme": data["theme"]}
    for section in doc["sections"]:
        for block in section["blocks"]:
            if block.get("type") == "references":
                block["items"] = [{**source, "note": source["note"] + " Accessed " + data["accessed"] + "."} for source in sources]
    deck = {"title": data["title"], "subtitle": data["subtitle"], "theme": data["theme"], "slides": data["slides"]}
    register = "\n".join(f'[{s["id"]}] {s["title"]}\n{s["url"]}\n{s["note"]}' for s in sources)
    for slide in deck["slides"]:
        if slide.get("notes") == "SOURCE_REGISTER":
            slide["notes"] = register + "\nAccessed " + data["accessed"]
        if slide.get("image"):
            slide["image"] = str(out / slide["image"])
    (out / "word-spec.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "deck-spec.json").write_text(json.dumps(deck, ensure_ascii=False, indent=2), encoding="utf-8")
    build_doc(doc, out / "human-evolution.docx", out)
    build_deck(deck, str(out / "human-evolution.pptx"))
    apply_transitions(str(out / "human-evolution.pptx"), {"default": {"type": "fade", "duration": 600}, "slides": {"1": None}})
    print("Built Word, 12-slide PowerPoint and PNG/SVG infographic in " + str(out))


if __name__ == "__main__":
    main()
