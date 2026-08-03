"""Deterministic XML serialization for validated vector nodes."""

from __future__ import annotations

from xml.sax.saxutils import escape

from app.icons.models import VectorNode


def _quote(value: object) -> str:
    escaped = escape(str(value), {'"': "&quot;"})
    return f'"{escaped}"'


def _serialize_node(node: VectorNode, color: str) -> str:
    attrs = dict(node.attrs)
    if node.tag == "line":
        attrs.setdefault("stroke", color)
    elif node.tag != "g":
        attrs.setdefault("fill", color)

    attrs = {
        name: color if value == "currentColor" else value
        for name, value in attrs.items()
    }
    rendered_attrs = " ".join(
        f"{name}={_quote(value)}" for name, value in sorted(attrs.items())
    )
    suffix = f" {rendered_attrs}" if rendered_attrs else ""

    if node.children:
        children = "".join(_serialize_node(child, color) for child in node.children)
        return f"<{node.tag}{suffix}>{children}</{node.tag}>"
    return f"<{node.tag}{suffix}/>"


def serialize_nodes(nodes: tuple[VectorNode, ...], color: str) -> str:
    """Serialize vector nodes using a caller-selected theme color."""
    return "\n".join(_serialize_node(node, color) for node in nodes)
