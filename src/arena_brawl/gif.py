"""GIF export: text frames -> animated GIF via Pillow.

Each frame is a list[list[Seg]] (rows of colored text). We rasterize onto a
fixed cell grid (10x20 px per cell, mono TTF at size 14) and hand the RGB
images to Pillow's GIF writer, which builds the global palette for the whole
sequence (pre-quantized P-mode frames collapse to 1 frame in Pillow 13).
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .render import Seg

CELL_W = 10
CELL_H = 20

PAL: list[tuple[int, int, int]] = [
    (0, 0, 0),        # 0 black / bg
    (205, 49, 49),    # 1 red
    (13, 188, 121),   # 2 green
    (229, 229, 16),   # 3 yellow
    (36, 114, 200),   # 4 blue
    (188, 63, 188),   # 5 magenta
    (17, 168, 205),   # 6 cyan
    (229, 229, 229),  # 7 white
    (102, 102, 102),  # 8 dim
    (255, 106, 0),    # 9 orange
    (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0),
    (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0),
    (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0),
    (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0),
]

_FONT_PATHS = [
    "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
]
_FONT_BOLD_PATHS = [
    "/usr/share/fonts/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
]


def _font(paths: list[str], size: int):
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def _cells(frame: list[list[Seg]]) -> tuple[int, int]:
    rows = len(frame)
    cols = max((sum(len(s.text) for s in row) for row in frame), default=1)
    return max(cols, 1), rows


def export(
    frames: list[list[list[Seg]]],
    path: str | Path,
    tick: float = 0.22,
    hold_last_ms: int = 2600,
) -> Path:
    if not frames:
        raise ValueError("no frames to export")
    cols, rows = _cells(frames[0])
    normal = _font(_FONT_PATHS, 14)
    bold = _font(_FONT_BOLD_PATHS, 14)

    # Keep frames in RGB and let Pillow's GIF writer build the global palette
    # across the whole sequence (it collapses pre-quantized P-mode frames
    # down to a single frame in Pillow 13). It ALSO collapses identical
    # consecutive frames, so each frame gets a recording-dot in the corner
    # that alternates color — kills accidental collapse and reads as a
    # live indicator.
    imgs: list = []
    for i, frame in enumerate(frames):
        im = Image.new("RGB", (cols * CELL_W, rows * CELL_H), PAL[0])
        d = ImageDraw.Draw(im)
        for y, row in enumerate(frame):
            x = 0
            for seg in row:
                color = PAL[seg.color % len(PAL)]
                fnt = bold if seg.bold else normal
                for ch in seg.text:
                    if ch != " ":
                        d.text(
                            (x * CELL_W, y * CELL_H + 1),
                            ch,
                            fill=color,
                            font=fnt,
                        )
                    x += 1
        d.rectangle(
            [cols * CELL_W - 7, 3, cols * CELL_W - 4, 6],
            fill=(13, 188, 121) if i % 2 == 0 else (60, 60, 60),
        )
        imgs.append(im)

    durations = [int(tick * 1000)] * (len(imgs) - 1) + [hold_last_ms]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    imgs[0].save(path, save_all=True, append_images=imgs[1:], duration=durations, loop=0)
    return path
