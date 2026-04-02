"""PNG and SVG renderer functions for the Homelab Icon Generator."""

from __future__ import annotations

import math
import os
import re
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw

from app.generator.layouts import LayoutSpec
from app.generator.shapes import draw_rounded_rect
from app.generator.symbols import draw_symbol
from app.generator.text_utils import render_initials
from app.styles.base import StyleDefinition

if TYPE_CHECKING:
    from app.models.icon_request import IconRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert a hex color string (e.g. '#1a2b3c') to an (R, G, B) tuple."""
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


# ---------------------------------------------------------------------------
# PNG renderer
# ---------------------------------------------------------------------------

def render_png(
    request: "IconRequest",
    style: StyleDefinition,
    layout: LayoutSpec,
) -> Image.Image:
    """Render an icon as a PIL Image (RGBA mode).

    Glow is intentionally skipped for PNG; use SVG if glow is desired.
    """
    size = request.size
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background
    if not request.transparent_bg:
        r, g, b = _hex_to_rgb(style.bg_color)
        draw.rounded_rectangle(
            [(0, 0), (size - 1, size - 1)],
            radius=style.corner_radius,
            fill=(r, g, b, 255),
        )

    # Border
    if style.border_width > 0:
        inset = style.border_width // 2
        draw_rounded_rect(
            draw,
            [(inset, inset), (size - 1 - inset, size - 1 - inset)],
            radius=style.corner_radius,
            fill=None,
            outline=style.accent_color,
            width=style.border_width,
        )

    # Symbol
    symbol_draw_size = (
        int(layout.symbol_size * 0.55)
        if layout.show_initials
        else int(layout.symbol_size * 0.65)
    )
    draw_symbol(
        request.category,
        draw,
        layout.symbol_cx,
        layout.symbol_cy,
        symbol_draw_size,
        style.fg_color,
    )

    # Initials
    if layout.show_initials:
        render_initials(
            draw,
            request.initials,
            layout.initials_cx,
            layout.initials_cy,
            layout.font_size,
            style.text_color,
        )

    return img


# ---------------------------------------------------------------------------
# SVG symbol helpers
# ---------------------------------------------------------------------------

def _svg_rounded_rect(
    x1: int, y1: int, x2: int, y2: int,
    radius: int,
    fill: str = "none",
    stroke: str = "none",
    stroke_width: int = 0,
) -> str:
    """Return an SVG <rect> element with rounded corners."""
    w = x2 - x1
    h = y2 - y1
    parts = [
        f'<rect x="{x1}" y="{y1}" width="{w}" height="{h}" rx="{radius}"',
        f' fill="{fill}"',
    ]
    if stroke != "none" and stroke_width > 0:
        parts.append(f' stroke="{stroke}" stroke-width="{stroke_width}"')
    parts.append("/>")
    return "".join(parts)


def _svg_circle(cx: int, cy: int, r: int, fill: str) -> str:
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"/>'


def _svg_ellipse(cx: int, cy: int, rx: int, ry: int, fill: str) -> str:
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}"/>'


def _svg_line(x1: int, y1: int, x2: int, y2: int, stroke: str, width: int) -> str:
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"'
        f' stroke="{stroke}" stroke-width="{width}"/>'
    )


def _svg_polygon(points: list[tuple[int, int]], fill: str) -> str:
    pts = " ".join(f"{x},{y}" for x, y in points)
    return f'<polygon points="{pts}" fill="{fill}"/>'


def _svg_rect(x1: int, y1: int, x2: int, y2: int, fill: str) -> str:
    """Plain rectangle (no rounding)."""
    w = x2 - x1
    h = y2 - y1
    return f'<rect x="{x1}" y="{y1}" width="{w}" height="{h}" fill="{fill}"/>'


# ---------------------------------------------------------------------------
# Per-category SVG symbol functions
# Each mirrors the corresponding draw_* function in symbols.py.
# ---------------------------------------------------------------------------

def _svg_raspberry_pi(cx: int, cy: int, size: int, color: str) -> str:
    r = int(size * 0.28)
    radius = int(size * 0.06)
    elements = [
        _svg_rounded_rect(cx - r, cy - r, cx + r, cy + r, radius, fill=color)
    ]
    pin_r = int(size * 0.04)
    offset = int(size * 0.22)
    for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
        elements.append(
            _svg_circle(cx + dx * offset, cy + dy * offset, pin_r, color)
        )
    return "\n".join(elements)


def _svg_server(cx: int, cy: int, size: int, color: str) -> str:
    bar_h = int(size * 0.10)
    bar_w = int(size * 0.55)
    gap = int(size * 0.04)
    total = 3 * bar_h + 2 * gap
    top = cy - total // 2
    elements = []
    for i in range(3):
        y = top + i * (bar_h + gap)
        radius = max(2, int(size * 0.01))
        elements.append(
            _svg_rounded_rect(
                cx - bar_w // 2, y, cx + bar_w // 2, y + bar_h,
                radius, fill=color,
            )
        )
    return "\n".join(elements)


def _svg_router(cx: int, cy: int, size: int, color: str) -> str:
    bw = int(size * 0.50)
    bh = int(size * 0.18)
    radius = max(2, int(size * 0.02))
    elements = [
        _svg_rounded_rect(
            cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2,
            radius, fill=color,
        )
    ]
    ant_h = int(size * 0.20)
    ant_w = max(2, int(size * 0.04))
    for dx in [-int(size * 0.15), 0, int(size * 0.15)]:
        x = cx + dx
        elements.append(
            _svg_rect(
                x - ant_w // 2,
                cy - bh // 2 - ant_h,
                x + ant_w // 2,
                cy - bh // 2,
                color,
            )
        )
    return "\n".join(elements)


def _svg_switch(cx: int, cy: int, size: int, color: str) -> str:
    pw = int(size * 0.12)
    ph = int(size * 0.12)
    gap = int(size * 0.04)
    cols, rows = 3, 2
    total_w = cols * pw + (cols - 1) * gap
    total_h = rows * ph + (rows - 1) * gap
    ox = cx - total_w // 2
    oy = cy - total_h // 2
    radius = max(2, int(size * 0.01))
    elements = []
    for row in range(rows):
        for col in range(cols):
            x = ox + col * (pw + gap)
            y = oy + row * (ph + gap)
            elements.append(
                _svg_rounded_rect(x, y, x + pw, y + ph, radius, fill=color)
            )
    return "\n".join(elements)


def _svg_laptop(cx: int, cy: int, size: int, color: str) -> str:
    sw = int(size * 0.50)
    sh = int(size * 0.32)
    screen_top = cy - sh // 2 - int(size * 0.04)
    radius = max(2, int(size * 0.02))
    elements = [
        _svg_rounded_rect(
            cx - sw // 2, screen_top, cx + sw // 2, screen_top + sh,
            radius, fill=color,
        )
    ]
    bw = int(size * 0.58)
    bh = int(size * 0.06)
    base_y = screen_top + sh + int(size * 0.02)
    elements.append(
        _svg_rounded_rect(
            cx - bw // 2, base_y, cx + bw // 2, base_y + bh,
            max(2, int(size * 0.01)), fill=color,
        )
    )
    return "\n".join(elements)


def _svg_desktop(cx: int, cy: int, size: int, color: str) -> str:
    tw = int(size * 0.28)
    th = int(size * 0.48)
    radius = max(2, int(size * 0.02))
    elements = [
        _svg_rounded_rect(
            cx - tw // 2, cy - th // 2, cx + tw // 2, cy + th // 2,
            radius, fill=color,
        )
    ]
    bw = int(size * 0.36)
    bh = int(size * 0.05)
    base_y = cy + th // 2
    elements.append(
        _svg_rounded_rect(
            cx - bw // 2, base_y, cx + bw // 2, base_y + bh,
            max(2, int(size * 0.01)), fill=color,
        )
    )
    return "\n".join(elements)


def _svg_phone(cx: int, cy: int, size: int, color: str) -> str:
    w = int(size * 0.28)
    h = int(size * 0.50)
    radius = int(size * 0.06)
    return _svg_rounded_rect(
        cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2,
        radius, fill=color,
    )


def _svg_iot(cx: int, cy: int, size: int, color: str) -> str:
    parts = []
    stroke_w = max(2, int(size * 0.025))
    for r in [int(size * 0.28), int(size * 0.20), int(size * 0.12)]:
        parts.append(
            f'<path d="M {cx-r},{cy} A {r},{r} 0 0,1 {cx+r},{cy}" '
            f'stroke="{color}" stroke-width="{stroke_w}" fill="none"/>'
        )
    dot_r = int(size * 0.04)
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{dot_r}" fill="{color}"/>')
    return "\n".join(parts)


def _svg_container(cx: int, cy: int, size: int, color: str) -> str:
    s = int(size * 0.48)
    lw = max(2, int(size * 0.025))
    radius = max(2, int(size * 0.02))
    half = s // 2
    elements = [
        _svg_rounded_rect(
            cx - half, cy - half, cx + half, cy + half,
            radius,
            fill="none",
            stroke=color,
            stroke_width=lw,
        ),
        # Vertical divider
        _svg_line(cx, cy - half + lw, cx, cy + half - lw, color, lw),
        # Horizontal divider
        _svg_line(cx - half + lw, cy, cx + half - lw, cy, color, lw),
    ]
    return "\n".join(elements)


def _svg_database(cx: int, cy: int, size: int, color: str) -> str:
    ew = int(size * 0.42)
    eh = int(size * 0.12)
    body_h = int(size * 0.30)
    top_y = cy - body_h // 2
    half_ew = ew // 2
    half_eh = eh // 2

    body_top = top_y + half_eh
    body_bottom = body_top + body_h

    elements = [
        # Rectangular body
        _svg_rect(cx - half_ew, body_top, cx + half_ew, body_bottom, color),
        # Bottom ellipse cap
        _svg_ellipse(
            cx, body_bottom,
            half_ew, half_eh,
            color,
        ),
        # Top ellipse cap (drawn on top)
        _svg_ellipse(
            cx, top_y + half_eh,
            half_ew, half_eh,
            color,
        ),
    ]
    return "\n".join(elements)


def _svg_cloud_service(cx: int, cy: int, size: int, color: str) -> str:
    r = int(size * 0.14)
    base_cy = cy + int(size * 0.04)
    elements = []
    for dx in [-int(size * 0.14), 0, int(size * 0.14)]:
        elements.append(_svg_circle(cx + dx, base_cy, r, color))
    # Top puff
    elements.append(
        _svg_circle(cx, base_cy - int(size * 0.10), int(size * 0.11), color)
    )
    return "\n".join(elements)


def _svg_generic_service(cx: int, cy: int, size: int, color: str) -> str:
    r = int(size * 0.28)
    points = [
        (
            int(cx + r * math.cos(math.radians(60 * i - 30))),
            int(cy + r * math.sin(math.radians(60 * i - 30))),
        )
        for i in range(6)
    ]
    return _svg_polygon(points, color)


_SVG_SYMBOL_FUNCS = {
    "raspberry_pi": _svg_raspberry_pi,
    "server": _svg_server,
    "router": _svg_router,
    "switch": _svg_switch,
    "laptop": _svg_laptop,
    "desktop": _svg_desktop,
    "phone": _svg_phone,
    "iot": _svg_iot,
    "container": _svg_container,
    "database": _svg_database,
    "cloud_service": _svg_cloud_service,
    "generic_service": _svg_generic_service,
}


def _category_svg(
    category: str,
    cx: int,
    cy: int,
    size: int,
    color: str,
    use_glow: bool,
) -> str:
    """Return an SVG group string for the given category symbol."""
    fn = _SVG_SYMBOL_FUNCS.get(category, _svg_generic_service)
    inner = fn(cx, cy, size, color)
    if use_glow:
        return f'<g filter="url(#glow)">\n{inner}\n</g>'
    return f"<g>\n{inner}\n</g>"


# ---------------------------------------------------------------------------
# SVG renderer
# ---------------------------------------------------------------------------

_GLOW_FILTER = """\
  <filter id="glow">
    <feGaussianBlur stdDeviation="3" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>"""


def render_svg(
    request: "IconRequest",
    style: StyleDefinition,
    layout: LayoutSpec,
) -> str:
    """Render an icon as an SVG string."""
    size = request.size

    # Defs section
    defs_content = _GLOW_FILTER if style.use_glow else ""
    defs_block = f"  <defs>\n{defs_content}\n  </defs>" if defs_content else "  <defs/>"

    # Background
    bg_fill = "none" if request.transparent_bg else style.bg_color
    bg_rect = (
        f'  <rect width="{size}" height="{size}"'
        f' rx="{style.corner_radius}" fill="{bg_fill}"/>'
    )

    # Border
    border_parts: list[str] = []
    if style.border_width > 0:
        inset = style.border_width // 2
        bw = size - 2 * inset
        border_parts.append(
            f'  <rect x="{inset}" y="{inset}" width="{bw}" height="{bw}"'
            f' rx="{style.corner_radius}"'
            f' stroke="{style.accent_color}" stroke-width="{style.border_width}"'
            f' fill="none"/>'
        )

    # Symbol
    symbol_draw_size = (
        int(layout.symbol_size * 0.55)
        if layout.show_initials
        else int(layout.symbol_size * 0.65)
    )
    symbol_group = _category_svg(
        request.category,
        layout.symbol_cx,
        layout.symbol_cy,
        symbol_draw_size,
        style.fg_color,
        style.use_glow,
    )
    # Indent the group block for readability
    symbol_block = "\n".join(f"  {line}" for line in symbol_group.splitlines())

    # Initials text
    text_parts: list[str] = []
    if layout.show_initials:
        text_parts.append(
            f'  <text x="{layout.initials_cx}" y="{layout.initials_cy}"'
            f' font-family="monospace" font-size="{layout.font_size}"'
            f' fill="{style.text_color}"'
            f' text-anchor="middle" dominant-baseline="middle">'
            f"{request.initials}</text>"
        )

    sections = [
        f'<svg xmlns="http://www.w3.org/2000/svg"'
        f' width="{size}" height="{size}" viewBox="0 0 {size} {size}">',
        defs_block,
        bg_rect,
        *border_parts,
        symbol_block,
        *text_parts,
        "</svg>",
    ]
    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def generate_icon(request: "IconRequest") -> dict[str, str]:
    """Run the full icon generation pipeline and return a dict of output paths.

    The returned dict contains keys "png" and/or "svg" depending on the
    requested format, mapping to the absolute file paths of the saved files.
    """
    import importlib

    from app.generator.colors import get_palette
    from app.generator.layouts import get_layout
    from app.utils.validation import validate_request

    validate_request(request)

    palette = get_palette(request.theme)

    style_mod = importlib.import_module(f"app.styles.{request.style}")
    style: StyleDefinition = style_mod.get_style(palette)

    layout = get_layout(request.size, style.font_scale)

    os.makedirs(request.output_dir, exist_ok=True)

    slug = re.sub(r"[^a-z0-9]+", "-", request.name.lower()).strip("-")
    base = f"{slug}-{request.style}-{request.theme}-{request.size}"

    output: dict[str, str] = {}

    if request.format in ("png", "both"):
        img = render_png(request, style, layout)
        png_path = os.path.join(request.output_dir, f"{base}.png")
        if request.transparent_bg:
            img.save(png_path, format="PNG")
        else:
            img.convert("RGB").save(png_path, format="PNG")
        output["png"] = png_path

    if request.format in ("svg", "both"):
        svg_str = render_svg(request, style, layout)
        svg_path = os.path.join(request.output_dir, f"{base}.svg")
        with open(svg_path, "w", encoding="utf-8") as fh:
            fh.write(svg_str)
        output["svg"] = svg_path

    return output
