"""Small constructors for normalized generic icon definitions."""

from __future__ import annotations

from app.icons.models import VectorIcon, VectorNode

VIEW_BOX = (0.0, 0.0, 100.0, 100.0)


def icon(key: str, title: str, *nodes: VectorNode) -> VectorIcon:
    return VectorIcon(
        key=key,
        title=title,
        source="generic",
        view_box=VIEW_BOX,
        nodes=nodes,
    )


def rect(
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    rx: float = 0,
    fill: str = "currentColor",
    stroke: str | None = None,
    stroke_width: float | None = None,
) -> VectorNode:
    attrs: dict[str, str | float] = {
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "fill": fill,
    }
    if rx:
        attrs["rx"] = rx
    if stroke is not None:
        attrs["stroke"] = stroke
    if stroke_width is not None:
        attrs["stroke-width"] = stroke_width
    return VectorNode("rect", attrs)


def circle(
    cx: float,
    cy: float,
    radius: float,
    *,
    fill: str = "currentColor",
    stroke: str | None = None,
    stroke_width: float | None = None,
) -> VectorNode:
    attrs: dict[str, str | float] = {
        "cx": cx,
        "cy": cy,
        "r": radius,
        "fill": fill,
    }
    if stroke is not None:
        attrs["stroke"] = stroke
    if stroke_width is not None:
        attrs["stroke-width"] = stroke_width
    return VectorNode("circle", attrs)


def ellipse(cx: float, cy: float, rx: float, ry: float) -> VectorNode:
    return VectorNode(
        "ellipse",
        {"cx": cx, "cy": cy, "rx": rx, "ry": ry, "fill": "currentColor"},
    )


def line(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    width: float,
    *,
    linecap: str = "round",
) -> VectorNode:
    return VectorNode(
        "line",
        {
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "stroke": "currentColor",
            "stroke-width": width,
            "stroke-linecap": linecap,
        },
    )


def polygon(points: str, *, fill: str = "currentColor") -> VectorNode:
    return VectorNode("polygon", {"points": points, "fill": fill})


def path(
    d: str,
    *,
    fill: str = "currentColor",
    stroke: str | None = None,
    stroke_width: float | None = None,
    linecap: str | None = None,
) -> VectorNode:
    attrs: dict[str, str | float] = {"d": d, "fill": fill}
    if stroke is not None:
        attrs["stroke"] = stroke
    if stroke_width is not None:
        attrs["stroke-width"] = stroke_width
    if linecap is not None:
        attrs["stroke-linecap"] = linecap
    return VectorNode("path", attrs)
