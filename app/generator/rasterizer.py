"""In-memory rasterization of authoritative SVG documents."""

from __future__ import annotations

from io import BytesIO

import resvg_py
from PIL import Image


def rasterize_svg(svg: str, width: int, height: int) -> Image.Image:
    """Rasterize an SVG string into a fully loaded RGBA Pillow image."""
    png_bytes = resvg_py.svg_to_bytes(
        svg_string=svg,
        width=width,
        height=height,
    )
    with Image.open(BytesIO(png_bytes)) as source:
        source.load()
        return source.convert("RGBA")
