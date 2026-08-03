"""Compose normalized icon geometry into the authoritative SVG document."""

from __future__ import annotations

from xml.sax.saxutils import escape

from app.generator.layouts import LayoutSpec
from app.icons.models import IconResolution
from app.icons.svg import serialize_nodes
from app.models.icon_request import IconRequest
from app.styles.base import StyleDefinition


def _number(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _view_box(values: tuple[float, float, float, float]) -> str:
    return " ".join(_number(value) for value in values)


def compose_svg(
    request: IconRequest,
    style: StyleDefinition,
    layout: LayoutSpec,
    resolution: IconResolution,
) -> str:
    """Return a complete SVG document for a resolved icon request."""
    size = request.size
    border_width = size * style.border_width_ratio
    corner_radius = size * style.corner_radius_ratio
    background = "none" if request.transparent_bg else style.bg_color

    defs = ""
    if style.use_glow:
        deviation = _number(size * 0.012)
        defs = (
            '<defs><filter id="glow"><feGaussianBlur stdDeviation="'
            f'{deviation}" result="blur"/><feMerge><feMergeNode in="blur"/>'
            '<feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
        )

    frame = [
        f'<rect data-role="background" fill="{background}" height="{size}" '
        f'rx="{_number(corner_radius)}" width="{size}"/>',
    ]
    if border_width > 0:
        inset = border_width / 2
        dimension = size - border_width
        frame.append(
            f'<rect data-role="border" fill="none" height="{_number(dimension)}" '
            f'rx="{_number(corner_radius)}" stroke="{style.accent_color}" '
            f'stroke-width="{_number(border_width)}" width="{_number(dimension)}" '
            f'x="{_number(inset)}" y="{_number(inset)}"/>'
        )

    show_initials = resolution.show_initials and layout.show_initials
    if resolution.show_initials:
        symbol_size = size * (0.55 if show_initials else 0.65)
        symbol_cx = layout.symbol_cx
        symbol_cy = layout.symbol_cy
    else:
        symbol_size = size * 0.62
        symbol_cx = size / 2
        symbol_cy = size / 2

    symbol_x = symbol_cx - symbol_size / 2
    symbol_y = symbol_cy - symbol_size / 2
    geometry = serialize_nodes(resolution.icon.nodes, style.fg_color)
    nested = (
        f'<svg data-role="symbol" height="{_number(symbol_size)}" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'viewBox="{_view_box(resolution.icon.view_box)}" '
        f'width="{_number(symbol_size)}" x="{_number(symbol_x)}" '
        f'y="{_number(symbol_y)}">{geometry}</svg>'
    )
    if style.use_glow:
        nested = f'<g filter="url(#glow)">{nested}</g>'

    initials = ""
    if show_initials:
        initials = (
            f'<text dominant-baseline="middle" fill="{style.text_color}" '
            f'font-family="monospace" font-size="{layout.font_size}" '
            f'text-anchor="middle" x="{layout.initials_cx}" y="{layout.initials_cy}">'
            f"{escape(request.initials)}</text>"
        )

    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" height="{size}" '
            f'viewBox="0 0 {size} {size}" width="{size}">',
            defs,
            *frame,
            nested,
            initials,
            "</svg>",
        ]
    )
