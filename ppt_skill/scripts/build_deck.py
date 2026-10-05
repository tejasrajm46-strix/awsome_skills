#!/usr/bin/env python3
"""Build an editable 16:9 PowerPoint deck from a JSON spec file.

    python build_deck.py deck.json -o deck.pptx [--base template.pptx]

Requires only `python-pptx` (which pulls in Pillow). Charts are *native* PPTX
charts, so they stay editable in PowerPoint and matplotlib is never needed.

The spec schema is documented in ../SKILL.md.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls
from pptx.util import Emu, Inches, Pt

from textmetrics import (  # noqa: E402  - sys.path above makes this importable
    column_widths,
    distribute_heights,
    est_lines,
    row_heights,
    table_grid,
)

# Freeform local coordinates are integers, and python-pptx derives the shape's
# extent from them. Passing inches directly therefore snaps every curve to a
# 1-inch grid and collapses anything smaller than an inch to zero extent.
# Working in hundredths of an inch keeps the error under 0.005in.
POLY_UNITS = 100
POLY_SCALE = Emu(9144)          # 0.01in per local unit

# ---------------------------------------------------------------- geometry --
SLIDE_W, SLIDE_H = 13.333, 7.5          # 16:9
MARGIN = 0.85
CONTENT_W = SLIDE_W - 2 * MARGIN        # 11.633
KICKER_Y, TITLE_Y = 0.56, 0.86
TITLE_H = 1.10            # tall enough for a two-line headline
RULE_Y, BODY_Y = 1.96, 2.30
FOOTER_RULE_Y, FOOTER_TEXT_Y = 6.60, 6.70
BODY_H = FOOTER_RULE_Y - 0.24 - BODY_Y

DEFAULT_THEME = {
    # "Research Lab" palette - institutional navy + a bright blue that nods to
    # the subject matter, on a near-white background.
    "primary": "1E3A5F",
    "accent": "2563EB",
    "highlight": "A16207",
    "text": "0F172A",
    "muted": "475569",
    "bg": "FFFFFF",
    "panel": "E9EEF5",
    "border": "CBD5E1",
    "font_head": "Segoe UI",
    "font_body": "Segoe UI",
    "font_mono": "Consolas",
    # secondary tokens used by the deep-ocean / dark layouts
    "bg_dark": "04121F",
    "deep": "0A2540",
    "ocean": "0E4C7A",
    "cyan": "22D3EE",
    "cyan_soft": "7DD3FC",
    "warm": "F59E0B",
    "alarm": "EF4444",
}

CHART_TYPES = {
    "bar": XL_CHART_TYPE.COLUMN_CLUSTERED,
    "hbar": XL_CHART_TYPE.BAR_CLUSTERED,
    "line": XL_CHART_TYPE.LINE_MARKERS,
    "area": XL_CHART_TYPE.AREA,
    "pie": XL_CHART_TYPE.PIE,
    "doughnut": XL_CHART_TYPE.DOUGHNUT,
}


# ------------------------------------------------------------------- utils --
def rgb(value: str) -> RGBColor:
    return RGBColor.from_string(value.lstrip("#").upper())


def textbox(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP, name=None):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        # the validator skips the legibility floor on "chrome:" shapes, so
        # footers and citations can sit at 9pt without adding warning noise
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    return tf


def add_runs(p, text, *, size, color, font, bold=False, italic=False, spacing=None):
    """Write `text` into paragraph `p`, honouring **bold** inline markup.

    A literal newline becomes a real DrawingML line break. A raw \\n inside
    <a:t> is *not* a line break in PowerPoint - it collapses as whitespace, so
    every deliberately broken headline would silently reflow.
    """
    # paragraph defaults, so the <a:br/> elements inherit the right size
    p.font.size = Pt(size)
    p.font.name = font
    for line_index, segment in enumerate(str(text).split("\n")):
        if line_index:
            p.add_line_break()
        for i, chunk in enumerate(re.split(r"\*\*(.+?)\*\*", segment)):
            if not chunk:
                continue
            run = p.add_run()
            run.text = chunk
            f = run.font
            f.size = Pt(size)
            f.name = font
            f.color.rgb = color
            f.bold = bold or (i % 2 == 1)
            f.italic = italic
            if spacing is not None:
                f._rPr.set("spc", str(int(spacing * 100)))
    return p


def line(tf, first, *, space_before=0, space_after=0, line_spacing=1.0):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    if space_before:
        p.space_before = Pt(space_before)
    if space_after:
        p.space_after = Pt(space_after)
    if line_spacing != 1.0:
        p.line_spacing = line_spacing
    return p


def set_bullet(p, char="\u2022", indent_in=0.28):
    """Give paragraph `p` a real hanging-indent bullet.

    Falls back to a literal bullet glyph (no hanging indent) if the XML insert
    is rejected - a cosmetic downgrade beats a crash.
    """
    pPr = p._p.get_or_add_pPr()
    pPr.set("marL", str(Inches(indent_in)))
    pPr.set("indent", str(-Inches(indent_in)))
    for xml in (
        '<a:buFont %s typeface="Arial"/>' % nsdecls("a"),
        '<a:buChar %s char="&#8226;"/>' % nsdecls("a"),
    ):
        pPr.insert_element_before(parse_xml(xml), "a:tabLst", "a:defRPr", "a:extLst")


def rect(slide, x, y, w, h, *, fill=None, line_color=None, shape=MSO_SHAPE.RECTANGLE,
         radius=None, weight=0.75):
    sh = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.shadow.inherit = False
    if fill is not None:
        sh.fill.solid()
        sh.fill.fore_color.rgb = fill
    else:
        sh.fill.background()
    if line_color is not None:
        sh.line.color.rgb = line_color
        sh.line.width = Pt(weight)
    else:
        sh.line.fill.background()
    if radius is not None:
        try:
            sh.adjustments[0] = radius
        except (IndexError, ValueError):
            pass
    sh.text_frame.word_wrap = True
    return sh


def connector(slide, x1, y1, x2, y2, *, color, weight=1.5):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1),
                                   Inches(x2), Inches(y2))
    c.shadow.inherit = False
    c.line.color.rgb = color
    c.line.width = Pt(weight)
    return c


# ------------------------------------------------------- text fitting maths --
def mix(fg_hex, bg_hex, t):
    """Blend `fg` over `bg` with weight `t` (0..1), returning hex.

    python-pptx cannot set fill/line transparency without hand-writing DrawingML,
    so "35% cyan on navy" is resolved here against the slide's known solid
    background. That keeps glow and grid effects dependency-free.
    """
    f, b = fg_hex.lstrip("#"), bg_hex.lstrip("#")
    return "".join(
        "%02X" % max(0, min(255, round(int(f[i:i + 2], 16) * t + int(b[i:i + 2], 16) * (1 - t))))
        for i in (0, 2, 4)
    )


def polyline(slide, pts, *, color, width=1.5, name=None):
    """Open freeform path through inch-coordinate points.

    Curves, contour lines and cable routes all need this; the DrawingML presets
    can't express an arbitrary path. Points are inches and are converted to
    hundredths-of-an-inch local units - see POLY_UNITS above for why passing
    inches straight through is wrong. Name a shape `bleed:...` when it is meant
    to run off the slide edge.
    """
    n = POLY_UNITS
    builder = slide.shapes.build_freeform(pts[0][0] * n, pts[0][1] * n, scale=POLY_SCALE)
    builder.add_line_segments([(x * n, y * n) for x, y in pts[1:]], close=False)
    sh = builder.convert_to_shape()
    if name:
        sh.name = name
    sh.shadow.inherit = False
    sh.fill.background()
    sh.line.color.rgb = color
    sh.line.width = Pt(width)
    return sh


def arc_points(p0, p1, bulge=0.5, n=26):
    """Quadratic curve from p0 to p1 bowing `bulge` inches along the normal.

    Negative bulge bows the other way. Used for cable routes and ocean contours.
    """
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    dist = math.hypot(dx, dy) or 1.0
    cx = (x0 + x1) / 2 + (-dy / dist) * bulge
    cy = (y0 + y1) / 2 + (dx / dist) * bulge
    return [((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1,
             (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1)
            for t in (i / (n - 1.0) for i in range(n))]


# Text measurement lives in textmetrics.py so the validator can re-measure a
# finished deck with exactly the maths that built it.


def fit_size(items, width_in, height_in, *, sizes=(20, 18, 17, 16, 15, 14, 13, 12),
             gap_pt=8, lead=1.25):
    """Largest body size from `sizes` whose text still fits the box."""
    for size in sizes:
        needed = sum(est_lines(t, width_in, size) * size * lead / 72.0 for t in items)
        needed += gap_pt / 72.0 * max(0, len(items) - 1)
        if needed <= height_in:
            return size
    raise ValueError("text cannot fit at %spt; shorten it or split the slide" % sizes[-1])


def fit_title(text, width_in, height_in=TITLE_H, sizes=(34, 30, 27, 26, 24, 22)):
    """Largest headline size that keeps the heading inside its zone.

    Headlines are unpredictable in length, so the size adapts rather than the
    title spilling into the content area - that spill is the single most common
    way a generated slide breaks.
    """
    for size in sizes:
        if est_lines(text, width_in, size) * size * 1.06 * 1.22 / 72.0 <= height_in:
            return size
    return sizes[-1]


# ------------------------------------------------------------------- deck --
class Deck:
    def __init__(self, spec, base=None):
        self.spec = spec
        self.theme = {**DEFAULT_THEME, **spec.get("theme", {})}
        self.prs = Presentation(base) if base else Presentation()
        self.prs.slide_width = Inches(SLIDE_W)
        self.prs.slide_height = Inches(SLIDE_H)
        self.blank = next(
            (l for l in self.prs.slide_layouts if "blank" in (l.name or "").lower()),
            self.prs.slide_layouts[-1],
        )
        self.footer = spec.get("title", "")
        self.section = None          # running section for automatic kickers
        self.n = 0

    def color(self, key):
        return rgb(self.theme[key])

    def new_slide(self):
        self.n += 1
        slide = self.prs.slides.add_slide(self.blank)
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = self.color("bg")
        return slide

    # -- shared chrome ------------------------------------------------------
    def chrome(self, slide, title, kicker=None, subtitle=None, source=None):
        accent, primary = self.color("accent"), self.color("primary")
        tf = textbox(slide, MARGIN, KICKER_Y, CONTENT_W, 0.3, name="chrome:kicker")
        add_runs(tf.paragraphs[0], (kicker or "").upper(), size=11, color=accent,
                 font=self.theme["font_head"], bold=True, spacing=1.2)
        tf = textbox(slide, MARGIN, TITLE_Y - 0.08, CONTENT_W, TITLE_H,
                     anchor=MSO_ANCHOR.MIDDLE)
        add_runs(line(tf, True, line_spacing=1.06), title,
                 size=fit_title(title, CONTENT_W), color=primary,
                 font=self.theme["font_head"], bold=True)
        rect(slide, MARGIN, RULE_Y, 1.15, 0.055, fill=accent)
        if subtitle:
            tf = textbox(slide, MARGIN, RULE_Y + 0.18, CONTENT_W, 0.4)
            add_runs(tf.paragraphs[0], subtitle, size=14, color=self.color("muted"),
                     font=self.theme["font_body"])
        self.footer_line(slide, source)

    def footer_line(self, slide, source=None):
        muted = self.color("muted")
        if source:
            tf = textbox(slide, MARGIN, FOOTER_RULE_Y - 0.30, CONTENT_W, 0.26,
                         name="chrome:source")
            p = line(tf, True)
            p.alignment = PP_ALIGN.RIGHT
            add_runs(p, source, size=9, color=muted, font=self.theme["font_body"], italic=True)
        rect(slide, MARGIN, FOOTER_RULE_Y, CONTENT_W, 0.012, fill=self.color("border"))
        tf = textbox(slide, MARGIN, FOOTER_TEXT_Y, CONTENT_W - 1.4, 0.28,
                     name="chrome:footer")
        add_runs(tf.paragraphs[0], self.footer, size=9, color=muted,
                 font=self.theme["font_body"])
        tf = textbox(slide, SLIDE_W - MARGIN - 1.2, FOOTER_TEXT_Y, 1.2, 0.28,
                     name="chrome:number")
        p = line(tf, True)
        p.alignment = PP_ALIGN.RIGHT
        add_runs(p, str(self.n), size=9, color=muted, font=self.theme["font_mono"])

    def notes(self, slide, text):
        if text:
            slide.notes_slide.notes_text_frame.text = text

    # -- layouts ------------------------------------------------------------
    def l_title(self, slide, s):
        if s.get("image"):
            self.l_photo_title(slide, s)
            return
        navy, accent = self.color("primary"), self.color("accent")
        rect(slide, 0, 0, SLIDE_W, SLIDE_H, fill=navy)
        # a small "emitting LED" motif: soft outer ring + bright core
        rect(slide, 10.35, 0.95, 2.35, 2.35, fill=rgb(mix(self.theme["accent"], self.theme["primary"], 0.45)), shape=MSO_SHAPE.OVAL)
        rect(slide, 10.80, 1.40, 1.45, 1.45, fill=accent, shape=MSO_SHAPE.OVAL)

        tf = textbox(slide, MARGIN, 3.30, 8.2, 0.34)
        add_runs(tf.paragraphs[0], (s.get("kicker") or "").upper(), size=12,
                 color=rgb("9DB8DC"), font=self.theme["font_head"], bold=True, spacing=1.6)
        tf = textbox(slide, MARGIN, 3.72, 8.6, 2.0)
        add_runs(line(tf, True, line_spacing=1.0), s["title"], size=40, color=rgb("FFFFFF"),
                 font=self.theme["font_head"], bold=True)
        rect(slide, MARGIN, 5.62, 1.4, 0.06, fill=accent)
        if s.get("subtitle"):
            tf = textbox(slide, MARGIN, 5.85, 8.4, 0.9)
            add_runs(line(tf, True, line_spacing=1.25), s["subtitle"], size=15,
                     color=rgb("C6D6EC"), font=self.theme["font_body"])
        meta = "  |  ".join(x for x in (s.get("author"), s.get("date")) if x)
        if meta:
            tf = textbox(slide, MARGIN, 6.72, 8.4, 0.3)
            add_runs(tf.paragraphs[0], meta, size=11, color=rgb("8FA8CC"),
                     font=self.theme["font_mono"])

    def l_photo_title(self, slide, s):
        """Automotive cover: full-bleed car photo with an editable dark text band."""
        from PIL import Image
        path = s["image"]
        with Image.open(path) as im:
            iw, ih = im.size
        scale = max(SLIDE_W / iw, SLIDE_H / ih)
        w, h = iw * scale, ih * scale
        pic = slide.shapes.add_picture(path, Inches((SLIDE_W - w) / 2), Inches((SLIDE_H - h) / 2),
                                       width=Inches(w), height=Inches(h))
        pic.name = "bleed:cover-image"
        pic._element.nvPicPr.cNvPr.set("descr", s.get("alt", "BMW M5 CS photographed at Goodwood Festival of Speed."))
        # The full-bleed image is already the backmost shape; the photograph is
        # intentionally exposed rather than covered with a canvas fill.
        # The bottom title band is deliberately dark and translucent-looking;
        # keeping it to a shallow band preserves the image as the main focus.
        rect(slide, 0, 5.00, SLIDE_W, 2.50, fill=rgb("0B0D0F"))
        rect(slide, MARGIN, 5.34, 0.08, 1.60, fill=self.color("accent"))
        tf = textbox(slide, MARGIN + 0.30, 5.26, 10.6, 0.30)
        add_runs(tf.paragraphs[0], (s.get("kicker") or "BMW M / CS EDITION").upper(), size=11,
                 color=self.color("accent"), font=self.theme["font_head"], bold=True, spacing=1.8)
        tf = textbox(slide, MARGIN + 0.30, 5.64, 11.0, 0.82)
        add_runs(line(tf, True, line_spacing=0.94), s["title"], size=44,
                 color=rgb("FFFFFF"), font=self.theme["font_head"], bold=True)
        if s.get("subtitle"):
            tf = textbox(slide, MARGIN + 0.30, 6.48, 10.8, 0.48)
            add_runs(line(tf, True, line_spacing=1.12), s["subtitle"], size=14,
                     color=rgb("D1D5D8"), font=self.theme["font_body"])
        if s.get("meta"):
            tf = textbox(slide, SLIDE_W - MARGIN - 2.1, 0.48, 2.1, 0.28, name="chrome:meta")
            p = line(tf, True)
            p.alignment = PP_ALIGN.RIGHT
            add_runs(p, s["meta"], size=10, color=rgb("FFFFFF"), font=self.theme["font_mono"])
        if s.get("image_credit"):
            tf = textbox(slide, MARGIN + 0.30, 7.28, 11.5, 0.16, name="chrome:credit")
            add_runs(tf.paragraphs[0], s["image_credit"], size=9,
                     color=rgb("C9CBCD"), font=self.theme["font_body"])

    def l_section(self, slide, s):
        navy, accent = self.color("primary"), self.color("accent")
        rect(slide, 0, 0, SLIDE_W, SLIDE_H, fill=navy)
        number = s.get("number")
        if number:
            tf = textbox(slide, MARGIN, 1.55, 6.0, 1.6)
            add_runs(tf.paragraphs[0], str(number), size=96, color=rgb("2C5185"),
                     font=self.theme["font_head"], bold=True)
        tf = textbox(slide, MARGIN, 3.45, 9.6, 1.5)
        add_runs(line(tf, True, line_spacing=1.05), s["title"], size=34, color=rgb("FFFFFF"),
                 font=self.theme["font_head"], bold=True)
        rect(slide, MARGIN, 4.72, 1.4, 0.06, fill=accent)
        if s.get("text"):
            tf = textbox(slide, MARGIN, 4.98, 8.6, 0.8)
            add_runs(line(tf, True, line_spacing=1.25), s["text"], size=15,
                     color=rgb("C6D6EC"), font=self.theme["font_body"])
        self.notes(slide, s.get("notes"))

    def l_bullets(self, slide, s):
        self.chrome(slide, s["title"], s.get("kicker", self.section), s.get("subtitle"),
                   s.get("source"))
        items = [str(b) for b in s.get("bullets", [])]
        if not items:
            return
        size = s.get("body_size") or fit_size(items, CONTENT_W - 0.4, BODY_H - 0.1)
        tf = textbox(slide, MARGIN, BODY_Y, CONTENT_W, BODY_H)
        for i, text in enumerate(items):
            p = line(tf, i == 0, space_after=size * 0.62, line_spacing=1.18)
            add_runs(p, text, size=size, color=self.color("text"),
                     font=self.theme["font_body"])
            for r in p.runs:
                if r.font.bold:
                    r.font.color.rgb = self.color("primary")
            try:
                set_bullet(p)
            except Exception:
                p.runs[0].text = "\u2022  " + p.runs[0].text

    def l_two_column(self, slide, s):
        self.chrome(slide, s["title"], s.get("kicker", self.section), s.get("subtitle"),
                   s.get("source"))
        gap = 0.55
        col_w = (CONTENT_W - gap) / 2
        blocks = [(MARGIN, s.get("left") or {}), (MARGIN + col_w + gap, s.get("right") or {})]
        connector(slide, MARGIN + col_w + gap / 2, BODY_Y, MARGIN + col_w + gap / 2,
                  FOOTER_RULE_Y - 0.30, color=self.color("border"), weight=1.0)
        for x, block in blocks:
            items = [str(b) for b in block.get("bullets", [])]
            head_h = 0.0
            if block.get("heading"):
                tf = textbox(slide, x, BODY_Y, col_w, 0.4)
                add_runs(tf.paragraphs[0], block["heading"], size=17,
                         color=self.color("primary"), font=self.theme["font_head"], bold=True)
                head_h = 0.52
            if not items:
                continue
            size = fit_size(items, col_w - 0.32, BODY_H - head_h - 0.1, sizes=(22, 20, 18, 17, 16, 15, 14, 13, 12))
            tf = textbox(slide, x, BODY_Y + head_h, col_w, BODY_H - head_h)
            for i, text in enumerate(items):
                p = line(tf, i == 0, space_after=size * 0.62, line_spacing=1.18)
                add_runs(p, text, size=size, color=self.color("text"),
                         font=self.theme["font_body"])
                for r in p.runs:
                    if r.font.bold:
                        r.font.color.rgb = self.color("primary")
                try:
                    set_bullet(p, indent_in=0.24)
                except Exception:
                    p.runs[0].text = "\u2022  " + p.runs[0].text

    def l_stats(self, slide, s):
        if s.get("image"):
            self.l_photo_stats(slide, s)
            return
        self.chrome(slide, s["title"], s.get("kicker", self.section), s.get("subtitle"),
                   s.get("source"))
        items = s.get("items", [])
        if not items:
            return
        gap, n = 0.32, len(items)
        w = (CONTENT_W - gap * (n - 1)) / n
        top, height = BODY_Y + 0.35, 2.45
        for i, item in enumerate(items):
            x = MARGIN + i * (w + gap)
            rect(slide, x, top, w, height, fill=self.color("panel"),
                 shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
            value = str(item.get("value", ""))
            vsize = 46 if len(value) <= 5 else (34 if len(value) <= 9 else 26)
            tf = textbox(slide, x + 0.30, top + 0.36, w - 0.6, 1.15)
            add_runs(tf.paragraphs[0], value, size=vsize, color=self.color("accent"),
                     font=self.theme["font_head"], bold=True)
            tf = textbox(slide, x + 0.30, top + 1.55, w - 0.6, height - 1.65)
            add_runs(line(tf, True, line_spacing=1.18), item.get("label", ""), size=13,
                     color=self.color("muted"), font=self.theme["font_body"])

    def l_photo_stats(self, slide, s):
        """Three oversized automotive performance metrics over a photo."""
        from PIL import Image
        path = s["image"]
        with Image.open(path) as im:
            iw, ih = im.size
        scale = max(SLIDE_W / iw, SLIDE_H / ih)
        w, h = iw * scale, ih * scale
        pic = slide.shapes.add_picture(path, Inches((SLIDE_W - w) / 2), Inches((SLIDE_H - h) / 2),
                                       width=Inches(w), height=Inches(h))
        pic.name = "bleed:performance-image"
        pic._element.nvPicPr.cNvPr.set("descr", s.get("alt", "BMW M5 CS photographed at Goodwood Festival of Speed."))
        rect(slide, 0, 0, SLIDE_W, 1.48, fill=rgb("101315"))
        rect(slide, 0, 4.38, SLIDE_W, 3.12, fill=rgb("101315"))
        tf = textbox(slide, MARGIN, 0.48, CONTENT_W, 0.28, name="chrome:kicker")
        add_runs(tf.paragraphs[0], (s.get("kicker") or "BMW M5 CS").upper(), size=10,
                 color=self.color("accent"), font=self.theme["font_head"], bold=True, spacing=1.4)
        tf = textbox(slide, MARGIN, 0.82, CONTENT_W, 0.54)
        add_runs(line(tf, True), s["title"], size=28, color=rgb("FFFFFF"),
                 font=self.theme["font_head"], bold=True)
        items = s.get("items", [])
        gap = 0.38
        n = max(1, len(items))
        col_w = (CONTENT_W - gap * (n - 1)) / n
        for i, item in enumerate(items):
            x = MARGIN + i * (col_w + gap)
            tf = textbox(slide, x, 4.76, col_w, 0.76)
            add_runs(line(tf, True, line_spacing=0.94), str(item.get("value", "")),
                     size=36 if len(str(item.get("value", ""))) < 8 else 28,
                     color=rgb("FFFFFF"), font=self.theme["font_head"], bold=True)
            rect(slide, x, 5.70, 0.62, 0.045, fill=self.color("accent"))
            tf = textbox(slide, x, 5.89, col_w, 0.68)
            add_runs(line(tf, True, line_spacing=1.12), item.get("label", ""), size=12,
                     color=rgb("E1E2E3"), font=self.theme["font_body"])
        if s.get("source"):
            tf = textbox(slide, MARGIN, 6.73, CONTENT_W, 0.18, name="chrome:source")
            add_runs(line(tf, True), s["source"], size=9,
                     color=rgb("B9BCBE"), font=self.theme["font_body"], italic=True)
        if s.get("image_credit"):
            tf = textbox(slide, MARGIN, 7.28, CONTENT_W, 0.14, name="chrome:credit")
            add_runs(tf.paragraphs[0], s["image_credit"], size=8,
                     color=rgb("B9BCBE"), font=self.theme["font_body"])

    def l_photo_hero_stat(self, slide, s):
        """Full-bleed performance hero with a dramatic single metric overlay."""
        from PIL import Image
        path = s["image"]
        with Image.open(path) as im:
            iw, ih = im.size
        scale = max(SLIDE_W / iw, SLIDE_H / ih)
        w, h = iw * scale, ih * scale
        pic = slide.shapes.add_picture(path, Inches((SLIDE_W - w) / 2), Inches((SLIDE_H - h) / 2),
                                       width=Inches(w), height=Inches(h))
        pic.name = "bleed:hero-stat-image"
        pic._element.nvPicPr.cNvPr.set("descr", s.get("alt", "BMW M5 CS photograph."))
        # Place the visual first; this overlay only occupies negative-space sky
        # and is deliberately free of opaque blocks across the car's silhouette.
        rect(slide, 0, 0, SLIDE_W, 0.72, fill=rgb("101315"))
        tf = textbox(slide, MARGIN, 0.34, CONTENT_W, 0.24, name="chrome:kicker")
        add_runs(tf.paragraphs[0], (s.get("kicker") or "BMW M5 CS").upper(), size=10,
                 color=self.color("accent"), font=self.theme["font_head"], bold=True, spacing=1.3)
        tf = textbox(slide, MARGIN, 0.94, 5.4, 1.65)
        add_runs(line(tf, True, line_spacing=0.88), str(s.get("value", "")), size=96,
                 color=rgb("FFFFFF"), font=self.theme["font_head"], bold=True)
        if s.get("unit"):
            tf = textbox(slide, MARGIN, 2.62, 5.6, 0.42)
            add_runs(line(tf, True), s["unit"], size=20, color=self.color("accent"),
                     font=self.theme["font_head"], bold=True, spacing=1.2)
        if s.get("text"):
            tf = textbox(slide, MARGIN, 3.12, 5.2, 0.90)
            add_runs(line(tf, True, line_spacing=1.18), s["text"], size=14,
                     color=rgb("FFFFFF"), font=self.theme["font_body"])
        if s.get("source"):
            tf = textbox(slide, MARGIN, 7.10, CONTENT_W, 0.16, name="chrome:source")
            add_runs(line(tf, True), s["source"], size=9,
                     color=rgb("FFFFFF"), font=self.theme["font_body"], italic=True)
        if s.get("image_credit"):
            tf = textbox(slide, MARGIN, 7.29, CONTENT_W, 0.13, name="chrome:credit")
            add_runs(tf.paragraphs[0], s["image_credit"], size=8,
                     color=rgb("FFFFFF"), font=self.theme["font_body"])

    def l_timeline(self, slide, s):
        items = s.get("items", [])
        if not 2 <= len(items) <= 6:
            raise ValueError(
                "timeline layout supports 2-6 items (got %d). Split into two slides."
                % len(items)
            )
        self.chrome(slide, s["title"], s.get("kicker", self.section), s.get("subtitle"),
                   s.get("source"))
        accent, primary, muted = self.color("accent"), self.color("primary"), self.color("muted")
        pad = 0.7
        x0, x1 = MARGIN + pad, MARGIN + CONTENT_W - pad
        rail_y = BODY_Y + 1.05
        connector(slide, x0, rail_y, x1, rail_y, color=self.color("border"), weight=2.0)
        step = (x1 - x0) / (len(items) - 1) if len(items) > 1 else 0
        slot = min(2.4, CONTENT_W / len(items) - 0.15)
        for i, item in enumerate(items):
            cx = x0 + step * i
            rect(slide, cx - 0.11, rail_y - 0.11, 0.22, 0.22, fill=accent, shape=MSO_SHAPE.OVAL)
            tf = textbox(slide, cx - slot / 2, rail_y - 0.78, slot, 0.5)
            p = line(tf, True)
            p.alignment = PP_ALIGN.CENTER
            add_runs(p, str(item.get("date", "")), size=15, color=primary,
                     font=self.theme["font_head"], bold=True)
            text_y = rail_y + 0.30
            if item.get("label"):
                tf = textbox(slide, cx - slot / 2, rail_y + 0.28, slot, 0.4)
                add_runs(line(tf, True, line_spacing=1.2), item["label"], size=12,
                         color=primary, font=self.theme["font_body"], bold=True)
                text_y = rail_y + 0.68
            tf = textbox(slide, cx - slot / 2, text_y, slot, 1.7)
            add_runs(line(tf, True, line_spacing=1.2), item.get("text", ""), size=11,
                     color=muted, font=self.theme["font_body"])

    def l_quote(self, slide, s):
        self.chrome(slide, s.get("title", ""), s.get("kicker", self.section),
                    source=s.get("source"))
        tf = textbox(slide, MARGIN - 0.05, BODY_Y - 0.30, 1.2, 1.35, name="chrome:quote-mark")
        add_runs(tf.paragraphs[0], "\u201C", size=72, color=rgb("C7D6EE"),
                 font=self.theme["font_head"], bold=True)
        indent = 1.15
        text = s.get("text", "")
        size = fit_size([text], CONTENT_W - indent, 2.6, sizes=(30, 27, 24, 21, 18))
        tf = textbox(slide, MARGIN + indent, BODY_Y + 0.45, CONTENT_W - indent, 2.6)
        add_runs(line(tf, True, line_spacing=1.16), text, size=size, color=self.color("primary"),
                 font=self.theme["font_head"], italic=True)
        if s.get("attribution"):
            tf = textbox(slide, MARGIN + indent, BODY_Y + 3.05, CONTENT_W - indent, 0.4)
            add_runs(tf.paragraphs[0], "\u2014 " + s["attribution"], size=13,
                     color=self.color("muted"), font=self.theme["font_body"])

    def l_table(self, slide, s):
        self.chrome(slide, s["title"], s.get("kicker", self.section), s.get("subtitle"),
                   s.get("source"))
        headers = list(s.get("headers", []))
        rows = [list(r) for r in s.get("rows", [])]
        if not headers or not rows:
            return
        grid = table_grid(headers, rows)
        widths = column_widths(grid, CONTENT_W)
        available = BODY_H - 0.05
        # Biggest size that fits wins, but never below 12pt: a table too dense to
        # read at 12pt is a slide to split, not one to squeeze into illegibility.
        size = None
        for candidate in (14, 13, 12):
            if sum(row_heights(grid, widths, candidate)) <= available:
                size = candidate
                break
        if size is None:
            raise ValueError(
                "table is too dense: %d rows x %d columns needs %.2fin at 12pt but "
                "only %.2fin is available. Split it across two slides."
                % (len(grid), len(widths), sum(row_heights(grid, widths, 12)), available))
        # Rows get their measured minimum, then share the slack, so a table reads
        # as a filled block instead of a cramped band stranded at the top.
        heights = distribute_heights(row_heights(grid, widths, size), available)
        gf = slide.shapes.add_table(len(grid), len(widths), Inches(MARGIN),
                                    Inches(BODY_Y), Inches(CONTENT_W),
                                    Inches(sum(heights)))
        table = gf.table
        table.first_row = True
        table.horz_banding = False
        for c, w in enumerate(widths):
            table.columns[c].width = Inches(w)
        for r, h in enumerate(heights):
            table.rows[r].height = Inches(h)
        for c, head in enumerate(grid[0]):
            self._cell(table.cell(0, c), head, size=size, bold=True,
                       fg=rgb("FFFFFF"), bg=self.color("primary"))
        for r, row in enumerate(grid[1:], start=1):
            bg = self.color("bg") if r % 2 else self.color("panel")
            for c, value in enumerate(row):
                self._cell(table.cell(r, c), value, size=size, fg=self.color("text"), bg=bg)

    def _cell(self, cell, text, *, size, fg, bg, bold=False):
        cell.fill.solid()
        cell.fill.fore_color.rgb = bg
        # 0.10/0.05 keep the real cell box identical to CELL_INSET/CELL_PAD in
        # textmetrics, so the builder and the validator measure the same width.
        cell.margin_left = cell.margin_right = Inches(0.10)
        cell.margin_top = cell.margin_bottom = Inches(0.05)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf = cell.text_frame
        tf.word_wrap = True
        add_runs(line(tf, True, line_spacing=1.1), str(text), size=size, color=fg,
                 font=self.theme["font_body"], bold=bold)

    def l_chart(self, slide, s):
        self.chrome(slide, s["title"], s.get("kicker", self.section), s.get("subtitle"),
                   s.get("source"))
        bullets = [str(b) for b in s.get("bullets", [])]
        if bullets:
            col_w = CONTENT_W * 0.36
            size = fit_size(bullets, col_w - 0.32, BODY_H - 0.1, sizes=(16, 15, 14, 13, 12))
            tf = textbox(slide, MARGIN, BODY_Y + 0.1, col_w, BODY_H)
            for i, text in enumerate(bullets):
                p = line(tf, i == 0, space_after=size * 0.7, line_spacing=1.18)
                add_runs(p, text, size=size, color=self.color("text"),
                         font=self.theme["font_body"])
                for r in p.runs:
                    if r.font.bold:
                        r.font.color.rgb = self.color("primary")
                try:
                    set_bullet(p, indent_in=0.24)
                except Exception:
                    p.runs[0].text = "\u2022  " + p.runs[0].text
            cx = MARGIN + col_w + 0.45
            cw = CONTENT_W - col_w - 0.45
        else:
            cx, cw = MARGIN, CONTENT_W
        kind = s.get("chart_type", "bar")
        chart_data = CategoryChartData()
        chart_data.categories = [str(c) for c in s.get("categories", [])]
        for series in s.get("series", []):
            chart_data.add_series(str(series.get("name", "")), series.get("values", []))
        gf = slide.shapes.add_chart(CHART_TYPES[kind], Inches(cx), Inches(BODY_Y + 0.05),
                                    Inches(cw), Inches(BODY_H - 0.1), chart_data)
        chart = gf.chart
        chart.has_title = False
        chart.font.size = Pt(12)
        chart.font.name = self.theme["font_body"]
        chart.font.color.rgb = self.color("muted")
        series_list = s.get("series", [])
        chart.has_legend = len(series_list) > 1
        if chart.has_legend:
            chart.legend.position = XL_LEGEND_POSITION.BOTTOM
            chart.legend.include_in_layout = False
        if kind in ("pie", "doughnut"):
            chart.plots[0].has_data_labels = True
            chart.plots[0].data_labels.show_percentage = True
            chart.plots[0].data_labels.show_category_name = False
        else:
            value_axis = chart.value_axis
            value_axis.has_major_gridlines = True
            if kind in ("bar", "hbar"):
                value_axis.minimum_scale = 0
            if s.get("unit"):
                value_axis.has_title = True
                value_axis.axis_title.text_frame.text = s["unit"]
                for p in value_axis.axis_title.text_frame.paragraphs:
                    for r in p.runs:
                        r.font.size = Pt(11)
                        r.font.color.rgb = self.color("muted")
        if kind in ("bar", "hbar"):
            chart.plots[0].gap_width = 70
        palette = [self.color("accent"), self.color("primary"), self.color("highlight"),
                   rgb("6B8FBF")]
        for i, series in enumerate(chart.series):
            colour = palette[i % len(palette)]
            fmt = series.format
            if kind in ("line",):
                fmt.line.color.rgb = colour
                fmt.line.width = Pt(2.5)
            else:
                fmt.fill.solid()
                fmt.fill.fore_color.rgb = colour

    def l_image(self, slide, s):
        if s.get("full_bleed"):
            self.l_photo_story(slide, s)
            return
        self.chrome(slide, s["title"], s.get("kicker", self.section), s.get("subtitle"),
                   s.get("source"))
        path = s["image"]
        from PIL import Image

        with Image.open(path) as im:
            iw, ih = im.size
        top = BODY_Y + 0.05
        avail_h = BODY_H - (0.45 if s.get("caption") else 0.1)
        scale = min(CONTENT_W / iw, avail_h / ih)
        w, h = iw * scale, ih * scale
        picture = slide.shapes.add_picture(
            path, Inches(MARGIN + (CONTENT_W - w) / 2), Inches(top),
            width=Inches(w), height=Inches(h))
        picture._element.nvPicPr.cNvPr.set("descr", s.get("alt") or s.get("caption", ""))
        if s.get("caption"):
            tf = textbox(slide, MARGIN, top + h + 0.14, CONTENT_W, 0.3)
            p = line(tf, True)
            p.alignment = PP_ALIGN.CENTER
            add_runs(p, s["caption"], size=11, color=self.color("muted"),
                     font=self.theme["font_body"], italic=True)

    def l_photo_story(self, slide, s):
        """Full-bleed automotive photograph with an editorial text overlay."""
        from PIL import Image
        path = s["image"]
        with Image.open(path) as im:
            iw, ih = im.size
        scale = max(SLIDE_W / iw, SLIDE_H / ih)
        w, h = iw * scale, ih * scale
        pic = slide.shapes.add_picture(path, Inches((SLIDE_W - w) / 2), Inches((SLIDE_H - h) / 2),
                                       width=Inches(w), height=Inches(h))
        pic.name = "bleed:story-image"
        pic._element.nvPicPr.cNvPr.set("descr", s.get("alt") or s.get("caption", ""))
        mode = s.get("panel", "bottom")
        if mode == "left":
            rect(slide, 0, 0, 4.70, SLIDE_H, fill=rgb("101315"))
            rect(slide, MARGIN, 0.82, 0.07, 0.52, fill=self.color("accent"))
            tf = textbox(slide, MARGIN + 0.27, 0.78, 3.45, 0.46, name="chrome:kicker")
            add_runs(tf.paragraphs[0], (s.get("kicker") or "BMW M5 CS").upper(), size=10,
                     color=self.color("accent"), font=self.theme["font_head"], bold=True, spacing=1.2)
            tf = textbox(slide, MARGIN, 1.55, 3.55, 1.70)
            add_runs(line(tf, True, line_spacing=0.98), s["title"], size=31,
                     color=rgb("FFFFFF"), font=self.theme["font_head"], bold=True)
            if s.get("caption"):
                tf = textbox(slide, MARGIN, 3.63, 3.55, 1.24)
                add_runs(line(tf, True, line_spacing=1.22), s["caption"], size=13,
                         color=rgb("E5E7E8"), font=self.theme["font_body"])
            if s.get("source"):
                tf = textbox(slide, MARGIN, 5.04, 3.55, 0.42, name="chrome:source")
                add_runs(line(tf, True), s["source"], size=9,
                         color=rgb("C5C8CA"), font=self.theme["font_body"], italic=True)
            credit_y = 7.12
        else:
            rect(slide, 0, 5.06, SLIDE_W, 2.44, fill=rgb("101315"))
            rect(slide, MARGIN, 5.39, 0.07, 1.51, fill=self.color("accent"))
            tf = textbox(slide, MARGIN + 0.28, 5.30, 10.8, 0.28, name="chrome:kicker")
            add_runs(tf.paragraphs[0], (s.get("kicker") or "BMW M5 CS").upper(), size=10,
                     color=self.color("accent"), font=self.theme["font_head"], bold=True, spacing=1.3)
            tf = textbox(slide, MARGIN + 0.28, 5.66, 11.3, 0.66)
            add_runs(line(tf, True, line_spacing=0.98), s["title"], size=31,
                     color=rgb("FFFFFF"), font=self.theme["font_head"], bold=True)
            if s.get("caption"):
                tf = textbox(slide, MARGIN + 0.28, 6.39, 11.4, 0.48)
                add_runs(line(tf, True, line_spacing=1.12), s["caption"], size=12,
                         color=rgb("E5E7E8"), font=self.theme["font_body"])
            credit_y = 7.12
        if s.get("image_credit"):
            tf = textbox(slide, MARGIN + 0.28, credit_y, 11.5, 0.18, name="chrome:credit")
            add_runs(tf.paragraphs[0], s["image_credit"], size=8,
                     color=rgb("B6B9BB"), font=self.theme["font_body"])

    def l_stack(self, slide, s):
        """Layered / stacked bands - structure diagrams (LED junction, stack, tiers)."""
        items = s.get("items", [])
        if not items:
            return
        if len(items) > 8:
            raise ValueError("stack layout supports at most 8 bands (got %d)" % len(items))
        self.chrome(slide, s["title"], s.get("kicker", self.section), s.get("subtitle"),
                   s.get("source"))
        gap = 0.14
        band_h = (BODY_H - gap * (len(items) - 1)) / len(items)
        # One source of truth for the three columns: label, note, marker. The note
        # takes exactly the space between the label column and the marker gutter.
        marker_w = 1.15
        marker_x = MARGIN + CONTENT_W - marker_w
        note_x = MARGIN + CONTENT_W * 0.47
        note_w = marker_x - 0.20 - note_x
        tints = [self.color("primary"), self.color("accent"), self.color("panel")]
        for i, item in enumerate(items):
            y = BODY_Y + i * (band_h + gap)
            # navy / blue / light repeating so structure reads as alternating
            idx = i % 3
            bg = tints[idx]
            fg = rgb("FFFFFF") if idx in (0, 1) else self.color("text")
            # F2F6FC, not the softer D3DEED: the note is 12pt normal, and D3DEED
            # only reaches 3.8:1 on the accent-blue band, under the 4.5:1 floor.
            note_fg = rgb("F2F6FC") if idx in (0, 1) else self.color("muted")
            rect(slide, MARGIN, y, CONTENT_W, band_h, fill=bg,
                 shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.10)
            tf = textbox(slide, MARGIN + 0.34, y + 0.10, CONTENT_W * 0.42, band_h - 0.2,
                         anchor=MSO_ANCHOR.MIDDLE)
            add_runs(line(tf, True, line_spacing=1.1), item.get("label", ""), size=16,
                     color=fg, font=self.theme["font_head"], bold=True)
            if item.get("note"):
                # The note must stop short of the marker column. Sizing the box to
                # the space actually left - rather than a fixed 44% of the width -
                # is what keeps a long note from running under its marker.
                tf = textbox(slide, note_x, y + 0.10, note_w, band_h - 0.2,
                             anchor=MSO_ANCHOR.MIDDLE)
                add_runs(line(tf, True, line_spacing=1.15), item["note"], size=12,
                         color=note_fg, font=self.theme["font_body"])
            if item.get("marker"):
                tf = textbox(slide, marker_x, y + 0.10, marker_w, band_h - 0.2,
                             anchor=MSO_ANCHOR.MIDDLE)
                p = line(tf, True)
                p.alignment = PP_ALIGN.RIGHT
                add_runs(p, item["marker"], size=11, color=note_fg,
                         font=self.theme["font_mono"])

    def l_closing(self, slide, s):
        ocean = s.get("motif") == "ocean"
        backdrop = self.color("bg_dark") if ocean else self.color("primary")
        accent = self.color("cyan") if ocean else self.color("accent")
        rect(slide, 0, 0, SLIDE_W, SLIDE_H, fill=backdrop)
        if ocean:
            self.ocean_motif(slide, grid=True, routes=False)
            self._seabed(slide, top=5.95)
            self._cable_glow(slide, [(14.0, 5.55), (11.9, 6.15), (9.6, 6.55),
                                     (7.0, 6.85), (4.4, 7.15)])
        if ocean:
            soft = rgb(mix(self.theme["cyan_soft"], self.theme["bg_dark"], 0.80))
            faint = rgb(mix(self.theme["cyan"], self.theme["bg_dark"], 0.50))
        else:
            soft, faint = rgb("C6D6EC"), rgb("8FA8CC")
        tf = textbox(slide, MARGIN, 2.45, 9.7, 1.62)
        add_runs(line(tf, True, line_spacing=0.96), s["title"], size=46,
                 color=rgb("FFFFFF"), font=self.theme["font_head"], bold=True)
        rect(slide, MARGIN, 4.28, 1.6, 0.06, fill=accent)
        if s.get("text"):
            tf = textbox(slide, MARGIN, 4.54, 8.6, 0.9)
            add_runs(line(tf, True, line_spacing=1.30), s["text"], size=16,
                     color=soft, font=self.theme["font_body"])
        if s.get("credit"):
            tf = textbox(slide, MARGIN, 6.42, 10.6, 0.6)
            add_runs(line(tf, True, line_spacing=1.25), s["credit"], size=10,
                     color=faint, font=self.theme["font_body"])

    # --------------------------------------------------- deep-ocean toolkit --
    def _dark_slide(self):
        slide = self.new_slide()
        rect(slide, 0, 0, SLIDE_W, SLIDE_H, fill=self.color("bg_dark"))
        return slide

    def _dark_kicker(self, slide, text, y=KICKER_Y):
        tf = textbox(slide, MARGIN, y, CONTENT_W, 0.32, name="chrome:kicker")
        add_runs(tf.paragraphs[0], (text or "").upper(), size=11, color=self.color("cyan"),
                 font=self.theme["font_head"], bold=True, spacing=1.6)

    def _dark_head(self, slide, title):
        """Kicker row + headline + accent rule, on a dark background."""
        tf = textbox(slide, MARGIN, TITLE_Y - 0.08, CONTENT_W, TITLE_H,
                     anchor=MSO_ANCHOR.MIDDLE)
        add_runs(line(tf, True, line_spacing=1.06), title,
                 size=fit_title(title, CONTENT_W), color=rgb("FFFFFF"),
                 font=self.theme["font_head"], bold=True)
        rect(slide, MARGIN, RULE_Y, 1.15, 0.055, fill=self.color("cyan"))

    def _dark_footer(self, slide, source=None, number=True):
        dark = self.theme["bg_dark"]
        if source:
            tf = textbox(slide, MARGIN, FOOTER_RULE_Y - 0.30, CONTENT_W, 0.26,
                         name="chrome:source")
            p = line(tf, True)
            p.alignment = PP_ALIGN.RIGHT
            add_runs(p, source, size=9, color=rgb(mix(self.theme["cyan_soft"], dark, 0.55)),
                     font=self.theme["font_body"], italic=True)
        connector(slide, MARGIN, FOOTER_RULE_Y, MARGIN + CONTENT_W, FOOTER_RULE_Y,
                  color=rgb(mix(self.theme["cyan"], dark, 0.30)), weight=0.75)
        tf = textbox(slide, MARGIN, FOOTER_TEXT_Y, CONTENT_W - 1.4, 0.28,
                     name="chrome:footer")
        add_runs(tf.paragraphs[0], self.footer, size=9,
                 color=rgb(mix(self.theme["cyan_soft"], dark, 0.45)),
                 font=self.theme["font_body"])
        if number:
            tf = textbox(slide, SLIDE_W - MARGIN - 1.2, FOOTER_TEXT_Y, 1.2, 0.28,
                         name="chrome:number")
            p = line(tf, True)
            p.alignment = PP_ALIGN.RIGHT
            add_runs(p, str(self.n), size=9, color=rgb(mix(self.theme["cyan"], dark, 0.5)),
                     font=self.theme["font_mono"])

    def _seabed(self, slide, top=6.05):
        """Ocean floor: a darker band with stacked contour lines."""
        dark = self.theme["bg_dark"]
        rect(slide, 0, top, SLIDE_W, SLIDE_H - top,
             fill=rgb(mix(self.theme["deep"], dark, 0.60)))
        for i, (dy, t) in enumerate(((0.0, 0.34), (0.30, 0.20), (0.62, 0.12))):
            pts = [(x / 14.0 * SLIDE_W,
                    top + dy + 0.09 * math.sin(x / 14.0 * 3.4 + i * 1.7))
                   for x in range(15)]
            polyline(slide, pts, color=rgb(mix(self.theme["cyan"], dark, t)), width=1.0)

    def _cable_glow(self, slide, pts, *, base=None, scale=1.0, dots=True):
        """Stacked strokes of decreasing width fake a glow without alpha XML."""
        base = base or self.theme["bg_dark"]
        for t, w in ((0.09, 11.0), (0.24, 5.5), (0.58, 2.2), (1.0, 1.0)):
            # runs off the slide edge on purpose: the cable should leave the frame
            polyline(slide, pts, color=rgb(mix(self.theme["cyan"], base, t)),
                     width=w * scale, name="bleed:cable")
        if dots:
            step = max(2, len(pts) // 5)
            for i in range(step, len(pts) - 2, step):
                x, y = pts[i]
                r = 0.045 * scale
                rect(slide, x - r, y - r, r * 2, r * 2,
                     fill=rgb(mix(self.theme["cyan"], base, 0.92)), shape=MSO_SHAPE.OVAL)

    def ocean_motif(self, slide, *, grid=True, routes=True):
        """Ambient furniture for dark slides: lat/long grid plus route arcs."""
        dark = self.theme["bg_dark"]
        if grid:
            faint = rgb(mix(self.theme["cyan"], dark, 0.13))
            for i in range(1, 8):
                connector(slide, 0, i * SLIDE_H / 8.0, SLIDE_W, i * SLIDE_H / 8.0,
                          color=faint, weight=0.5)
            for i in range(1, 12):
                connector(slide, i * SLIDE_W / 12.0, 0, i * SLIDE_W / 12.0, SLIDE_H,
                          color=faint, weight=0.5)
        if routes:
            cloud = rgb(mix(self.theme["cyan"], dark, 0.34))
            hub = [(1.30, 1.75), (3.55, 4.55), (6.05, 2.30), (8.75, 5.00), (11.05, 1.60)]
            for a, b in ((0, 1), (1, 2), (2, 3), (3, 4), (0, 2), (2, 4), (1, 3)):
                polyline(slide, arc_points(hub[a], hub[b], bulge=-0.45), color=cloud,
                         width=0.9)
            for x, y in hub:
                rect(slide, x - 0.05, y - 0.05, 0.10, 0.10,
                     fill=rgb(mix(self.theme["cyan"], dark, 0.80)), shape=MSO_SHAPE.OVAL)

    def _vchain(self, slide, x, y, w, steps, *, box_h, bg_hex, fg, gap=0.15, size=11,
                highlight=None):
        """Vertical sequence of labelled boxes joined by small arrows."""
        for i, text in enumerate(steps):
            yy = y + i * (box_h + gap)
            hot = i == highlight
            rect(slide, x, yy, w, box_h,
                 fill=self.color("alarm") if hot else rgb(bg_hex),
                 shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
            tf = textbox(slide, x + 0.14, yy, w - 0.28, box_h, anchor=MSO_ANCHOR.MIDDLE)
            add_runs(line(tf, True, line_spacing=1.1), text, size=size,
                     color=rgb("FFFFFF") if hot else fg,
                     font=self.theme["font_head"], bold=True, spacing=0.8)
            if i < len(steps) - 1:
                tri = rect(slide, x + w / 2 - 0.07, yy + box_h + gap / 2 - 0.05, 0.14, 0.10,
                           fill=rgb(mix(self.theme["cyan"], bg_hex, 0.60)),
                           shape=MSO_SHAPE.ISOSCELES_TRIANGLE)
                try:
                    tri.rotation = 180
                except (ValueError, AttributeError):
                    pass

    def _hchain(self, slide, y, steps, *, height=1.15, highlight=None, base_hex=None):
        """Horizontal sequence of labelled panels."""
        base_hex = base_hex or self.theme["bg"]
        n = len(steps)
        gap = 0.34
        w = (CONTENT_W - gap * (n - 1)) / n
        for i, text in enumerate(steps):
            x = MARGIN + i * (w + gap)
            hot = i == highlight
            rect(slide, x, y, w, height,
                 fill=self.color("alarm") if hot else self.color("panel"),
                 shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.10)
            tf = textbox(slide, x + 0.14, y, w - 0.28, height, anchor=MSO_ANCHOR.MIDDLE)
            p = line(tf, True, line_spacing=1.12)
            p.alignment = PP_ALIGN.CENTER
            add_runs(p, text, size=11, color=rgb("FFFFFF") if hot else self.color("primary"),
                     font=self.theme["font_head"], bold=True, spacing=0.6)
            if i < n - 1:
                rect(slide, x + w + 0.06, y + height / 2 - 0.055, 0.22, 0.11,
                     fill=rgb(mix(self.theme["cyan"], base_hex, 0.75)),
                     shape=MSO_SHAPE.RIGHT_ARROW)

    def _cross_strip(self, slide, x, y, w, h, *, base_hex=None, vessel=False):
        """Ocean cross-section: waterline, shelf, abyss, a cable on the floor."""
        base_hex = base_hex or self.theme["bg"]
        rect(slide, x, y, w, h, fill=rgb(mix(self.theme["ocean"], base_hex, 0.12)),
             shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.04)
        water = y + h * 0.26
        connector(slide, x + 0.12, water, x + w - 0.12, water,
                  color=rgb(mix(self.theme["cyan"], base_hex, 0.55)), weight=1.2)
        # shelf -> abyss -> shelf. Depths are expressed as fractions of the strip
        # height so the floor always stays inside it, whatever height is asked for.
        shelf, depth = y + h * 0.36, h * 0.56
        floor = []
        for i in range(61):
            u = i / 60.0
            d = min(1.0, min(u, 1 - u) / 0.24) ** 0.7
            floor.append((x + 0.12 + u * (w - 0.24), shelf + d * depth))
        polyline(slide, floor, color=rgb(mix(self.theme["cyan"], base_hex, 0.30)), width=2.0)
        self._cable_glow(slide, [(px, py - 0.07) for px, py in floor],
                         base=base_hex, scale=0.55, dots=False)
        if vessel:
            vx = x + w * 0.30
            hull = rgb(mix("C6D6EC", base_hex, 0.88))
            rect(slide, vx - 0.85, water - 0.30, 1.55, 0.24, fill=hull,
                 shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.30)
            rect(slide, vx - 0.45, water - 0.46, 0.75, 0.18, fill=hull)
            polyline(slide, [(vx, water - 0.06), (vx + 0.06, water + 0.7),
                             (vx - 0.05, water + 1.4), (vx + 0.04, water + 2.05)],
                     color=rgb(mix(self.theme["cyan"], base_hex, 0.85)), width=1.2)
            rect(slide, vx - 0.12, water + 2.05, 0.24, 0.16,
                 fill=rgb(mix(self.theme["cyan"], base_hex, 0.9)), shape=MSO_SHAPE.OVAL)
        return floor

    def _chips(self, slide, x, y, w, items, *, cols, base_hex=None, height=0.62, gap=0.18,
               size=10):
        base_hex = base_hex or self.theme["bg"]
        cw = (w - gap * (cols - 1)) / cols
        for i, item in enumerate(items):
            cx = x + (i % cols) * (cw + gap)
            cy = y + (i // cols) * (height + gap)
            rect(slide, cx, cy, cw, height, fill=None,
                 line_color=rgb(mix(self.theme["cyan"], base_hex, 0.42)),
                 shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.14, weight=0.9)
            tf = textbox(slide, cx + 0.10, cy, cw - 0.20, height, anchor=MSO_ANCHOR.MIDDLE)
            p = line(tf, True, line_spacing=1.1)
            p.alignment = PP_ALIGN.CENTER
            add_runs(p, item, size=size, color=rgb(mix(self.theme["cyan_soft"], base_hex, 0.9)),
                     font=self.theme["font_head"], bold=True, spacing=0.8)

    # --------------------------------------------------- deep-ocean layouts --
    def l_hero(self, slide, s):
        self._seabed(slide, top=6.10)
        self.ocean_motif(slide, grid=True, routes=True)
        self._cable_glow(slide, [(13.75, 0.75), (11.95, 1.70), (10.40, 2.95),
                                 (9.80, 4.30), (10.50, 5.55), (11.95, 6.50),
                                 (13.75, 6.95)])
        self._dark_kicker(slide, s.get("kicker"), 2.02)
        tf = textbox(slide, MARGIN, 2.40, 8.85, 2.10)
        add_runs(line(tf, True, line_spacing=0.98), s["title"], size=54,
                 color=rgb("FFFFFF"), font=self.theme["font_head"], bold=True)
        rect(slide, MARGIN, 4.52, 1.5, 0.055, fill=self.color("cyan"))
        if s.get("subtitle"):
            tf = textbox(slide, MARGIN, 4.80, 7.8, 0.9)
            add_runs(line(tf, True, line_spacing=1.25), s["subtitle"], size=16,
                     color=rgb(mix(self.theme["cyan_soft"], self.theme["bg_dark"], 0.78)),
                     font=self.theme["font_body"])
        if s.get("meta"):
            tf = textbox(slide, MARGIN, 6.45, 8.4, 0.3, name="chrome:meta")
            add_runs(line(tf, True), s["meta"], size=10,
                     color=rgb(mix(self.theme["cyan"], self.theme["bg_dark"], 0.50)),
                     font=self.theme["font_mono"])

    def l_split(self, slide, s):
        self.chrome(slide, s["title"], s.get("kicker", self.section), s.get("subtitle"),
                    s.get("source"))
        gap = 0.52
        pw = (CONTENT_W - gap) / 2.0
        top, ph = BODY_Y + 0.16, BODY_H - 0.95
        self._panel_device(slide, MARGIN, top, pw, ph)
        self._panel_ocean(slide, MARGIN + pw + gap, top, pw, ph)
        polyline(slide, arc_points((MARGIN + pw - 0.04, top + ph * 0.40),
                                   (MARGIN + pw + gap + 0.04, top + ph * 0.56),
                                   bulge=-0.72), color=self.color("cyan"), width=2.0)
        if s.get("text"):
            # keep clear of the source line at FOOTER_RULE_Y - 0.30
            text_y = top + ph + 0.20
            tf = textbox(slide, MARGIN, text_y, CONTENT_W,
                         max(0.34, FOOTER_RULE_Y - 0.34 - text_y))
            add_runs(line(tf, True, line_spacing=1.25), s["text"], size=12,
                     color=self.color("muted"), font=self.theme["font_body"])

    def _panel_device(self, slide, x, y, w, h):
        rect(slide, x, y, w, h, fill=self.color("panel"),
             shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.05)
        dw, dh = 1.30, h - 1.05
        dx, dy = x + (w - dw) / 2, y + 0.42
        rect(slide, dx, dy, dw, dh, fill=self.color("primary"),
             shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.11)
        rect(slide, dx + 0.09, dy + 0.20, dw - 0.18, dh - 0.42,
             fill=rgb(mix(self.theme["cyan"], self.theme["primary"], 0.55)),
             shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.07)
        rect(slide, dx + dw / 2 - 0.06, dy + 0.09, 0.12, 0.05,
             fill=rgb(mix(self.theme["cyan_soft"], self.theme["primary"], 0.80)))
        # signal arcs rising off the device
        ax, ay = dx + dw * 0.30, dy - 0.05
        for k in (0.0, 0.20, 0.40):
            polyline(slide, arc_points((ax, ay), (ax + 0.95, ay),
                                       bulge=-(0.40 + k), n=16),
                     color=rgb(mix(self.theme["cyan"], self.theme["panel"], 0.85)), width=1.2)

    def _panel_ocean(self, slide, x, y, w, h):
        dark = self.theme["bg_dark"]
        rect(slide, x, y, w, h, fill=rgb(mix(self.theme["deep"], dark, 0.80)),
             shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.05)
        floor = [(x + 0.20 + i / 20.0 * (w - 0.40),
                  y + h - 0.80 + 0.20 * math.sin(i / 20.0 * 5.0)) for i in range(21)]
        polyline(slide, floor, color=rgb(mix(self.theme["cyan"], dark, 0.28)), width=1.5)
        self._cable_glow(slide, [(px, py - 0.08) for px, py in floor], base=dark,
                         scale=0.5, dots=False)

    def l_statement(self, slide, s):
        self.ocean_motif(slide, grid=True, routes=True)
        self._seabed(slide, top=6.45)
        self._dark_kicker(slide, s.get("kicker"), 1.30)
        tf = textbox(slide, MARGIN, 1.80, CONTENT_W, 2.65, anchor=MSO_ANCHOR.MIDDLE)
        add_runs(line(tf, True, line_spacing=0.94), s["title"],
                 size=fit_size([s["title"]], CONTENT_W, 2.65, sizes=(72, 64, 56, 48), lead=1.0),
                 color=rgb("FFFFFF"), font=self.theme["font_head"], bold=True)
        rect(slide, MARGIN, 4.72, 1.6, 0.06, fill=self.color("cyan"))
        if s.get("text"):
            tf = textbox(slide, MARGIN, 4.98, 8.9, 0.9)
            add_runs(line(tf, True, line_spacing=1.30), s["text"], size=15,
                     color=rgb(mix(self.theme["cyan_soft"], self.theme["bg_dark"], 0.78)),
                     font=self.theme["font_body"])
        self._dark_footer(slide, s.get("source"))

    def l_hero_stat(self, slide, s):
        if s.get("image"):
            self.l_photo_hero_stat(slide, s)
            return
        self.ocean_motif(slide, grid=True, routes=True)
        self._dark_kicker(slide, s.get("kicker"), 0.95)
        tf = textbox(slide, MARGIN, 1.50, CONTENT_W, 2.15, anchor=MSO_ANCHOR.MIDDLE)
        add_runs(line(tf, True, line_spacing=0.94), s["value"], size=120,
                 color=rgb("FFFFFF"), font=self.theme["font_head"], bold=True)
        if s.get("unit"):
            tf = textbox(slide, MARGIN, 3.70, CONTENT_W, 0.5)
            add_runs(line(tf, True), s["unit"], size=26, color=self.color("cyan"),
                     font=self.theme["font_head"], bold=True, spacing=1.4)
        rect(slide, MARGIN, 4.38, 1.6, 0.06, fill=self.color("cyan"))
        if s.get("text"):
            tf = textbox(slide, MARGIN, 4.64, 8.9, 0.9)
            add_runs(line(tf, True, line_spacing=1.30), s["text"], size=16,
                     color=rgb(mix(self.theme["cyan_soft"], self.theme["bg_dark"], 0.82)),
                     font=self.theme["font_body"])
        self._dark_footer(slide, s.get("source"))

    def l_network(self, slide, s):
        self.ocean_motif(slide, grid=True, routes=False)
        self._dark_kicker(slide, s.get("kicker"), KICKER_Y)
        self._dark_head(slide, s["title"])
        dark = self.theme["bg_dark"]
        nodes = s.get("nodes", [])
        px, py = MARGIN + 0.55, BODY_Y + 0.20
        pw, ph = CONTENT_W - 1.10, FOOTER_RULE_Y - 0.85 - py
        pos = [(px + n.get("x", 0.5) * pw, py + n.get("y", 0.5) * ph) for n in nodes]
        link = rgb(mix(self.theme["cyan"], dark, 0.60))
        for a, b in s.get("links", []):
            if a < len(pos) and b < len(pos):
                polyline(slide, arc_points(pos[a], pos[b], bulge=-0.30), color=link, width=1.1)
        for (cx, cy), node in zip(pos, nodes):
            rect(slide, cx - 0.16, cy - 0.16, 0.32, 0.32, fill=None,
                 line_color=rgb(mix(self.theme["cyan"], dark, 0.45)),
                 shape=MSO_SHAPE.OVAL, weight=0.75)
            rect(slide, cx - 0.075, cy - 0.075, 0.15, 0.15, fill=self.color("cyan"),
                 shape=MSO_SHAPE.OVAL)
            tf = textbox(slide, cx - 1.05, cy + 0.19, 2.1, 0.34)
            p = line(tf, True)
            p.alignment = PP_ALIGN.CENTER
            add_runs(p, node.get("name", ""), size=10,
                     color=rgb(mix(self.theme["cyan_soft"], dark, 0.88)),
                     font=self.theme["font_head"], bold=True, spacing=0.8)
        if s.get("note"):
            tf = textbox(slide, MARGIN, FOOTER_RULE_Y - 0.62, CONTENT_W, 0.3)
            add_runs(line(tf, True), s["note"], size=10,
                     color=rgb(mix(self.theme["cyan"], dark, 0.55)),
                     font=self.theme["font_body"], italic=True)
        self._dark_footer(slide, s.get("source"))

    def l_forces(self, slide, s):
        self.ocean_motif(slide, grid=True, routes=False)
        self._dark_kicker(slide, s.get("kicker"), KICKER_Y)
        self._dark_head(slide, s["title"])
        dark = self.theme["bg_dark"]
        items = s.get("items", [])
        rows = (len(items) + 2) // 3
        self._chips(slide, MARGIN, BODY_Y, CONTENT_W, items, cols=min(3, len(items)),
                    base_hex=dark, height=0.80, gap=0.20)
        strip_y = BODY_Y + rows * 1.00 + 0.30
        self._seabed(slide, top=strip_y)
        floor = [(MARGIN - 0.4 + i / 24.0 * (CONTENT_W + 0.8),
                  strip_y + 0.42 + 0.07 * math.sin(i / 24.0 * 6.0)) for i in range(25)]
        self._cable_glow(slide, floor, base=dark, scale=0.7, dots=True)
        if s.get("note"):
            tf = textbox(slide, MARGIN, FOOTER_RULE_Y - 0.72, CONTENT_W, 0.52)
            add_runs(line(tf, True, line_spacing=1.15), s["note"], size=10,
                     color=rgb(mix(self.theme["cyan"], dark, 0.55)),
                     font=self.theme["font_body"], italic=True)
        self._dark_footer(slide, s.get("source"))

    def l_cutaway(self, slide, s):
        self.ocean_motif(slide, grid=True, routes=False)
        self._dark_kicker(slide, s.get("kicker"), KICKER_Y)
        self._dark_head(slide, s["title"])
        dark = self.theme["bg_dark"]
        layers = s.get("layers", [])
        col_w = CONTENT_W * 0.52
        gap = 0.14
        band = (BODY_H - 0.62 - gap * (len(layers) - 1)) / max(1, len(layers))
        for i, layer in enumerate(layers):
            y = BODY_Y + i * (band + gap)
            tint = (0.16, 0.30, 0.48, 0.66, 0.84)[i % 5]
            rect(slide, MARGIN, y, col_w, band,
                 fill=rgb(mix(self.theme["cyan"], dark, tint)),
                 shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.16)
            tf = textbox(slide, MARGIN + 0.26, y, col_w - 0.52, band, anchor=MSO_ANCHOR.MIDDLE)
            add_runs(line(tf, True, line_spacing=1.1), layer.get("label", ""), size=13,
                     color=rgb("FFFFFF") if tint < 0.5 else rgb(self.theme["bg_dark"]),
                     font=self.theme["font_head"], bold=True, spacing=0.8)
            # leader line out to the callout column
            cy = y + band / 2
            connector(slide, MARGIN + col_w, cy, MARGIN + col_w + 0.34, cy,
                      color=rgb(mix(self.theme["cyan"], dark, 0.40)), weight=0.75)
            tf = textbox(slide, MARGIN + col_w + 0.44, cy - 0.20, CONTENT_W - col_w - 0.44, 0.4)
            add_runs(line(tf, True, line_spacing=1.15), layer.get("note", ""), size=10,
                     color=rgb(mix(self.theme["cyan_soft"], dark, 0.72)),
                     font=self.theme["font_body"])
        if s.get("note"):
            tf = textbox(slide, MARGIN, FOOTER_RULE_Y - 0.72, CONTENT_W, 0.52)
            add_runs(line(tf, True, line_spacing=1.15), s["note"], size=10,
                     color=rgb(mix(self.theme["cyan"], dark, 0.58)),
                     font=self.theme["font_body"], italic=True)
        self._dark_footer(slide, s.get("source"))

    def l_journey(self, slide, s):
        self.chrome(slide, s["title"], s.get("kicker", self.section), s.get("subtitle"),
                    s.get("source"))
        strip_y, strip_h = BODY_Y + 0.36, BODY_H - 0.36
        self._cross_strip(slide, MARGIN, strip_y, CONTENT_W, strip_h)
        water = strip_y + strip_h * 0.26
        stations = s.get("stations", [])
        n = max(1, len(stations))
        span = CONTENT_W - 1.10
        # labels sit on a fixed pitch, so the box must not exceed it or they collide
        bw = max(1.15, span / max(1, n - 1) - 0.14) if n > 1 else 2.2
        for i, st in enumerate(stations):
            cx = MARGIN + 0.55 + span * (i / (n - 1.0) if n > 1 else 0.5)
            # Every label goes in the sky band above the waterline. Alternating
            # above/below would force a leader line straight through the
            # cross-section, which reads as a wire hanging off the cable.
            lys = water - 0.80
            tf = textbox(slide, cx - bw / 2, lys, bw, 0.64)
            p = line(tf, True, line_spacing=1.12)
            p.alignment = PP_ALIGN.CENTER
            add_runs(p, st.get("label", ""), size=10, color=self.color("primary"),
                     font=self.theme["font_head"], bold=True, spacing=0.6)
            connector(slide, cx, water - 0.13, cx, water - 0.01,
                      color=rgb(mix(self.theme["cyan"], self.theme["bg"], 0.45)), weight=0.75)
            rect(slide, cx - 0.06, water - 0.06, 0.12, 0.12, fill=self.color("cyan"),
                 shape=MSO_SHAPE.OVAL)
        if s.get("zones"):
            tf = textbox(slide, MARGIN, BODY_Y + 0.02, CONTENT_W, 0.3)
            p = line(tf, True)
            add_runs(p, "   ".join(x.upper() for x in s["zones"]), size=10,
                     color=self.color("muted"), font=self.theme["font_mono"], spacing=1.4)

    def l_flow(self, slide, s):
        dark = bool(s.get("dark"))
        if dark:
            self.ocean_motif(slide, grid=True, routes=False)
            self._dark_kicker(slide, s.get("kicker"), KICKER_Y)
            self._dark_head(slide, s["title"])
            base_hex = self.theme["bg_dark"]
            fg = rgb(mix(self.theme["cyan_soft"], base_hex, 0.92))
        else:
            self.chrome(slide, s["title"], s.get("kicker", self.section),
                        s.get("subtitle"), s.get("source"))
            base_hex = self.theme["bg"]
            fg = self.color("text")
        steps = s.get("steps", [])
        col_w = CONTENT_W * 0.36
        gap = 0.16
        box_h = (BODY_H - 0.10 - gap * (len(steps) - 1)) / max(1, len(steps))
        self._vchain(slide, MARGIN, BODY_Y, col_w, steps, box_h=min(box_h, 0.62),
                     bg_hex=mix(self.theme["cyan"], base_hex, 0.14), fg=fg, gap=gap)
        rx = MARGIN + col_w + 0.45
        rw = CONTENT_W - col_w - 0.45
        self._cross_strip(slide, rx, BODY_Y + 0.35, rw, 2.45,
                          base_hex=base_hex, vessel=bool(s.get("vessel")))
        if s.get("chips"):
            # strip ends at BODY_Y+2.80, source sits at FOOTER_RULE_Y-0.30
            self._chips(slide, rx, BODY_Y + 2.88, rw, s["chips"], cols=1,
                        base_hex=base_hex, height=0.30, gap=0.07, size=10)
        if dark:
            self._dark_footer(slide, s.get("source"))

    def l_compare(self, slide, s):
        self.chrome(slide, s["title"], s.get("kicker", self.section), s.get("subtitle"),
                    s.get("source"))
        gap = 0.62
        cw = (CONTENT_W - gap) / 2.0
        for i, block in enumerate((s.get("left") or {}, s.get("right") or {})):
            x = MARGIN + i * (cw + gap)
            rect(slide, x, BODY_Y, cw, BODY_H - 0.12, fill=self.color("panel"),
                 shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.04)
            tf = textbox(slide, x + 0.30, BODY_Y + 0.28, cw - 0.6, 0.45)
            add_runs(line(tf, True), block.get("heading", "").upper(), size=20,
                     color=self.color("primary"), font=self.theme["font_head"],
                     bold=True, spacing=1.4)
            motif = block.get("motif", "signal")
            my = BODY_Y + 0.90
            col = self.color("warm") if motif == "signal" else self.color("cyan")
            if motif == "signal":
                pts = [(x + 0.35 + k * (cw - 0.7) / 6.0,
                        my + (0.10 if k % 2 else -0.10)) for k in range(7)]
                polyline(slide, pts, color=col, width=1.8)
                for k in (1, 3, 5):
                    px = pts[k][0]
                    rect(slide, px - 0.055, my - 0.055, 0.11, 0.11, fill=col,
                         shape=MSO_SHAPE.OVAL)
            else:
                pts = [(x + 0.35, my), (x + cw - 0.35, my)]
                polyline(slide, pts, color=col, width=1.8)
                for k in range(4):
                    px = x + 0.35 + (cw - 0.7) * (k + 0.5) / 4.0
                    rect(slide, px - 0.08, my - 0.08, 0.16, 0.16, fill=None,
                         line_color=col, shape=MSO_SHAPE.OVAL, weight=1.2)
                    rect(slide, px - 0.03, my - 0.03, 0.06, 0.06, fill=col,
                         shape=MSO_SHAPE.OVAL)
            items = [str(b) for b in block.get("bullets", [])]
            size = fit_size(items, cw - 0.6, BODY_H - 1.85, sizes=(15, 14, 13, 12), lead=1.2)
            tf = textbox(slide, x + 0.30, my + 0.34, cw - 0.6, BODY_H - 1.9)
            for k, text in enumerate(items):
                p = line(tf, k == 0, space_after=size * 0.7, line_spacing=1.18)
                add_runs(p, text, size=size, color=self.color("text"),
                         font=self.theme["font_body"])
                for r in p.runs:
                    if r.font.bold:
                        r.font.color.rgb = self.color("primary")
                try:
                    set_bullet(p, indent_in=0.22)
                except Exception:
                    p.runs[0].text = "\u2022  " + p.runs[0].text

    def l_trinity(self, slide, s):
        self.chrome(slide, s["title"], s.get("kicker", self.section), s.get("subtitle"),
                    s.get("source"))
        items = s.get("items", [])
        n = max(1, len(items))
        arrow = 0.40
        reserve = 0.55 if s.get("text") else 0.12
        band = (BODY_H - reserve - arrow * (n - 1)) / n
        tints = (self.color("primary"), self.color("ocean"), self.color("panel"))
        for i, label in enumerate(items):
            y = BODY_Y + i * (band + arrow)
            rect(slide, MARGIN, y, CONTENT_W, band, fill=tints[i % 3],
                 shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.10)
            fg = rgb("FFFFFF") if i < 2 else self.color("primary")
            tf = textbox(slide, MARGIN + 0.5, y, CONTENT_W - 1.0, band,
                         anchor=MSO_ANCHOR.MIDDLE)
            add_runs(line(tf, True), label, size=26, color=fg,
                     font=self.theme["font_head"], bold=True, spacing=1.6)
            if i < n - 1:
                tri = rect(slide, MARGIN + CONTENT_W / 2 - 0.14, y + band + 0.05, 0.28, arrow - 0.10,
                           fill=self.color("cyan"), shape=MSO_SHAPE.ISOSCELES_TRIANGLE)
                try:
                    tri.rotation = 180
                except (ValueError, AttributeError):
                    pass
        if s.get("text"):
            tf = textbox(slide, MARGIN, FOOTER_RULE_Y - 0.62, CONTENT_W, 0.3)
            add_runs(line(tf, True), s["text"], size=11, color=self.color("muted"),
                     font=self.theme["font_body"], italic=True)

    def l_sequence(self, slide, s):
        self.chrome(slide, s["title"], s.get("kicker", self.section), s.get("subtitle"),
                    s.get("source"))
        steps = s.get("steps", [])
        self._hchain(slide, BODY_Y + 0.35, steps, height=1.15,
                     highlight=s.get("highlight", 0))
        if s.get("network"):
            y = FOOTER_RULE_Y - 1.55
            xs = [MARGIN + 1.5, MARGIN + CONTENT_W / 2, MARGIN + CONTENT_W - 1.5]
            live = rgb(mix(self.theme["cyan"], self.theme["bg"], 0.8))
            polyline(slide, arc_points((xs[0], y), (xs[1], y), bulge=-0.55), color=live, width=1.4)
            cut = arc_points((xs[1], y), (xs[2], y), bulge=-0.55)
            polyline(slide, cut[:len(cut) // 2 - 2], color=live, width=1.4)
            polyline(slide, cut[len(cut) // 2 + 3:], color=live, width=1.4)
            bx, by = cut[len(cut) // 2]
            for dx, dy in ((-1, -1), (1, 1), (-1, 1), (1, -1)):
                polyline(slide, [(bx, by), (bx + dx * 0.17, by + dy * 0.17)],
                         color=self.color("alarm"), width=2.4)
            for i, px in enumerate(xs):
                rect(slide, px - 0.08, y - 0.08, 0.16, 0.16,
                     fill=self.color("alarm") if i == 1 else self.color("primary"),
                     shape=MSO_SHAPE.OVAL)
        if s.get("note"):
            tf = textbox(slide, MARGIN, FOOTER_RULE_Y - 0.74, CONTENT_W, 0.54)
            add_runs(line(tf, True, line_spacing=1.2), s["note"], size=11,
                     color=self.color("muted"), font=self.theme["font_body"], italic=True)

    def render(self):
        renderers = {
            "title": self.l_title, "section": self.l_section, "bullets": self.l_bullets,
            "two_column": self.l_two_column, "stats": self.l_stats,
            "timeline": self.l_timeline, "quote": self.l_quote, "table": self.l_table,
            "chart": self.l_chart, "image": self.l_image, "stack": self.l_stack,
            "closing": self.l_closing,
            # deep-ocean / diagram layouts
            "hero": self.l_hero, "split": self.l_split, "statement": self.l_statement,
            "flow": self.l_flow, "cutaway": self.l_cutaway, "journey": self.l_journey,
            "hero_stat": self.l_hero_stat, "network": self.l_network,
            "forces": self.l_forces, "compare": self.l_compare,
            "trinity": self.l_trinity, "sequence": self.l_sequence,
        }
        for s in self.spec.get("slides", []):
            layout = s.get("layout", "bullets")
            if layout not in renderers:
                raise ValueError("unknown layout %r (have: %s)"
                                 % (layout, ", ".join(sorted(renderers))))
            slide = self.new_slide()
            renderers[layout](slide, s)
            self.notes(slide, s.get("notes"))
            # a section title becomes the running kicker for later slides
            if layout == "section":
                self.section = s.get("title")
        return self.prs


def build(spec, out_path, base=None):
    prs = Deck(spec, base=base).render()
    cp = prs.core_properties
    cp.title = spec.get("title", "")
    if spec.get("author"):
        cp.author = spec["author"]
    if spec.get("subtitle"):
        cp.subject = spec["subtitle"]
    cp.comments = "Generated from a JSON deck spec."
    # Remove inherited transitions from the output copy, never the source deck.
    for slide in prs.slides:
        for transition in list(slide._element):
            if transition.tag == "{http://schemas.openxmlformats.org/presentationml/2006/main}transition":
                slide._element.remove(transition)
    prs.save(out_path)
    return out_path


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build a .pptx deck from a JSON spec.")
    ap.add_argument("spec", help="path to the deck spec JSON")
    ap.add_argument("-o", "--out", required=True, help="output .pptx path")
    ap.add_argument("--base", help="optional .pptx to start from (its theme is kept)")
    args = ap.parse_args(argv)
    with open(args.spec, encoding="utf-8") as fh:
        spec = json.load(fh)
    # Asset paths belong to the spec, not the caller's working directory.
    for slide in spec.get("slides", []):
        if slide.get("image") and not os.path.isabs(slide["image"]):
            slide["image"] = os.path.join(os.path.dirname(os.path.abspath(args.spec)),
                                         slide["image"])
    path = build(spec, args.out, args.base)
    print("wrote %s (%d slides)" % (path, len(spec.get("slides", []))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
