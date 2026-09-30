#!/usr/bin/env python3
"""Text and table measurement, shared by the deck builder and the validator.

The builder sizes rows, columns and type with these estimates; the validator
re-measures the finished deck with the *same* maths. Keeping one owner means a
table cannot pass validation merely by being measured differently from the way
it was built - that divergence is how a cramped table shipped as "ok".

Everything here is a heuristic: an average glyph advance of `ratio` em, not a
font engine. It is calibrated to catch gross overflow, not to typeset.
"""
from __future__ import annotations

import math

# Average glyph advance as a fraction of the point size, for Segoe UI / Calibri
# prose. Caps and 'mw' run wider, 'il' narrower; 0.5 averages out on sentences.
GLYPH_RATIO = 0.5
# Line advance as a multiple of the point size (PowerPoint single spacing).
LEAD = 1.22
# Default cell padding: PowerPoint's 0.05in top + 0.05in bottom.
CELL_PAD = 0.10
# Left + right cell margin, PowerPoint's default 0.1in each side.
CELL_INSET = 0.20


def est_lines(text, width_in, size_pt, ratio=GLYPH_RATIO):
    """Rough line count for `text` at `size_pt` inside `width_in` inches."""
    if not text:
        return 0
    char_w = max(size_pt * ratio / 72.0, 0.01)
    per_line = max(1, int(width_in / char_w))
    return sum(max(1, math.ceil(len(seg) / per_line)) for seg in str(text).split("\n"))


def text_width(text, size_pt, ratio=GLYPH_RATIO):
    """Rough rendered width in inches of the longest line in `text`."""
    if not text:
        return 0.0
    char_w = size_pt * ratio / 72.0
    return max(len(seg) for seg in str(text).split("\n")) * char_w


def column_widths(grid, total_w, floor=1.5):
    """Widths in inches for the columns of `grid` (list of rows of strings).

    Every column is guaranteed `floor` inches - a narrow "label" column that
    starves and wraps its label over three lines is the classic table defect -
    and whatever space is left is shared out in proportion to how much text each
    column actually holds.
    """
    if not grid:
        return []
    ncols = max(len(r) for r in grid)
    demand = []
    for c in range(ncols):
        longest = max((len(r[c]) for r in grid if c < len(r) and r[c] is not None),
                      default=1)
        demand.append(max(1, longest))
    floor = min(floor, total_w / ncols)
    free = total_w - floor * ncols
    total = sum(demand)
    return [floor + free * d / total for d in demand]


def row_heights(grid, widths, size, pad=CELL_PAD, lead=LEAD, inset=CELL_INSET):
    """Content-driven minimum height in inches for each row of `grid`.

    `size` is a point size for every row, or a per-row sequence when the rows
    are set in different sizes. A row is as tall as its worst-wrapping cell, so
    a row whose cell text wraps to three lines gets the room for three lines
    instead of a height chosen for the shortest cell.
    """
    sizes = list(size) if isinstance(size, (list, tuple)) else [size] * len(grid)
    heights = []
    for row, size_pt in zip(grid, sizes):
        lines = 1
        for c, text in enumerate(row):
            avail = max(widths[c] - inset, 0.35)
            lines = max(lines, est_lines(text, avail, size_pt))
        heights.append(lines * size_pt * lead / 72.0 + pad)
    return heights


def table_grid(headers, rows):
    """Normalise a table into one rectangular grid of strings."""
    ncols = max([len(headers)] + [len(r) for r in rows] or [0])
    out = [[("" if c >= len(headers) else str(headers[c])) for c in range(ncols)]]
    for r in rows:
        out.append([("" if c >= len(r) else str(r[c])) for c in range(ncols)])
    return out


def distribute_heights(heights, available, cap=0.34):
    """Grow every row by the same amount so the table fills up to `available`.

    A table whose rows declare only their content minimum renders as a cramped
    band of text stranded at the top of an empty zone. Spreading the slack keeps
    rows as generous as the space allows, with `cap` so a two-row table does not
    become two enormous slabs.
    """
    if not heights:
        return []
    slack = available - sum(heights)
    if slack <= 0:
        return list(heights)
    pad = min(slack / len(heights), cap)
    return [h + pad for h in heights]
