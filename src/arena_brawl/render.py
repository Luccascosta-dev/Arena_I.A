"""Terminal rendering: visible-width-safe text lines built from colored segments.

A `Row` is a list of `Seg(text, color_index, bold)` — plain unicode text, no
ANSI escapes. ANSI is added only when printing to a terminal (see `paint`),
which is also what makes the GIF export trivial: segments already carry the
color needed for the pixel buffer.
"""
from __future__ import annotations

import textwrap
from dataclasses import dataclass

WIDTH = 76          # virtual canvas width, in cells
MAX_LINES = 12      # body lines per player pane


@dataclass
class Seg:
    text: str
    color: int = 7      # ANSI color index (0=black … 7=white)
    bold: bool = False


@dataclass
class ColState:
    """What one player looks like mid-battle."""
    name: str
    color: int
    text: str = ""
    chars: int = 0
    err: str | None = None

    def lines(self, w: int) -> list[str]:
        if self.text:
            return textwrap.wrap(self.text, w) or [""]
        return [""]

    def picked(self, w: int, max_lines: int = MAX_LINES) -> list[str]:
        ls = self.lines(w)
        if self.err:
            return [f"!! {self.err}"[:w]]
        if len(ls) > max_lines:
            return ls[-max_lines:]
        return ls + [""] * (max_lines - len(ls))


# ── ANSI helpers ──────────────────────────────────────────────────────────────
_CSI = {0: "30", 1: "31", 2: "32", 3: "33", 4: "34", 5: "35", 6: "36", 7: "37"}


def paint(row: list[Seg]) -> str:
    out = []
    for seg in row:
        code = _CSI[seg.color]
        pre = "\x1b[1m" if seg.bold else ""
        out.append(f"{pre}\x1b[{code}m{seg.text}\x1b[0m")
    return "".join(out)


def visible(row: list[Seg]) -> int:
    return sum(len(s.text) for s in row)


# ── frame assembly ────────────────────────────────────────────────────────────
def header(task: str, width: int = WIDTH) -> list[list[Seg]]:
    rows: list[list[Seg]] = []
    rows.append([Seg(" ARENA", 3, True), Seg("  battle-of-agents · you judge  · elo is public", 7, False)])
    rows.append([Seg("", 0, False)])
    for ln in textwrap.wrap(f"Task: {task}", width):
        rows.append([Seg(ln, 7, False)])
    rows.append([Seg("", 0, False)])
    return rows


def _pane_frame(col: ColState, w: int) -> list[list[Seg]]:
    head = f"── {col.name} "
    head += "─" * max(3, w - len(head))
    block: list[list[Seg]] = [[Seg(head, col.color, True)]]
    for ln in col.picked(w):
        block.append([Seg(ln, col.color, False)])
    return block


def _pad(row: list[Seg], w: int) -> list[Seg]:
    missing = w - visible(row)
    return row + ([Seg(" " * max(0, missing), 0, False)] if missing > 0 else [])


def make_frame(
    cols: list[ColState],
    task: str,
    status: list[Seg] | None = None,
    footer: list[Seg] | None = None,
    width: int = WIDTH,
    max_lines: int = MAX_LINES,
) -> list[list[Seg]]:
    """One frozen moment of the battle. Always the same number of rows, so the
    GIF canvas never changes size."""
    rows = header(task, width)
    half = (width - 3) // 2  # 36 | gutter(3) | 36 → fits exactly in 76 with 1 to spare
    panes = [_pane_frame(c, half) for c in cols]
    pane_rows = max(len(p) for p in panes)
    for p in panes:  # equalize pane heights
        while len(p) < pane_rows:
            p.append([Seg("", 0, False)])

    gutter = Seg(" │ ", 7, False)
    for i in range(pane_rows):
        merged: list[Seg] = []
        for j, p in enumerate(panes):
            merged += _pad(p[i], half)
            if j == 0:
                merged.append(gutter if len(panes) == 2 else Seg(" · ", 7, False))
        rows.append(merged)

    blank = [Seg("", 0, False)]
    rows.append(blank)
    if status:
        rows.append(status)
    if footer:
        rows.append([Seg("", 0, False)])
        rows.append(footer)
    return rows


def progress_row(cols: list[ColState], bar_w: int = 14) -> list[Seg]:
    mx = max(1, max(c.chars for c in cols))
    row: list[Seg] = []
    for j, c in enumerate(cols):
        n = int(bar_w * c.chars / mx)
        row.append(Seg(f" {c.name} ", c.color, True))
        row.append(Seg("▓" * n + "░" * (bar_w - n), c.color, False))
        row.append(Seg(f" {c.chars}c", 7, False))
        if j < len(cols) - 1:
            row.append(Seg("   ", 0, False))
    return row
