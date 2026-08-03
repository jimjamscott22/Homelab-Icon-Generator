"""Immutable data models shared by icon sources and renderers."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal, Mapping, TypeAlias

VectorTag: TypeAlias = Literal[
    "path",
    "rect",
    "circle",
    "ellipse",
    "line",
    "polygon",
    "polyline",
    "g",
]
MatchMethod: TypeAlias = Literal[
    "explicit",
    "custom",
    "catalog",
    "normalized",
    "generic",
]
AttributeValue: TypeAlias = str | int | float

_ALLOWED_TAGS = frozenset(
    {"path", "rect", "circle", "ellipse", "line", "polygon", "polyline", "g"}
)
_COMMON_ATTRIBUTES = frozenset(
    {
        "aria-label",
        "clip-rule",
        "fill",
        "fill-rule",
        "opacity",
        "stroke",
        "stroke-linecap",
        "stroke-linejoin",
        "stroke-width",
        "transform",
    }
)
_TAG_ATTRIBUTES: dict[str, frozenset[str]] = {
    "path": frozenset({"d"}),
    "rect": frozenset({"x", "y", "width", "height", "rx", "ry"}),
    "circle": frozenset({"cx", "cy", "r"}),
    "ellipse": frozenset({"cx", "cy", "rx", "ry"}),
    "line": frozenset({"x1", "y1", "x2", "y2"}),
    "polygon": frozenset({"points"}),
    "polyline": frozenset({"points"}),
    "g": frozenset(),
}


@dataclass(frozen=True)
class VectorNode:
    """One validated geometry node in a normalized vector icon."""

    tag: VectorTag
    attrs: Mapping[str, AttributeValue] = field(default_factory=dict)
    children: tuple[VectorNode, ...] = ()

    def __post_init__(self) -> None:
        if self.tag not in _ALLOWED_TAGS:
            raise ValueError(f"Unsupported vector element '{self.tag}'")

        allowed = _COMMON_ATTRIBUTES | _TAG_ATTRIBUTES[self.tag]
        attrs = dict(self.attrs)
        unsupported = sorted(set(attrs) - allowed)
        if unsupported:
            names = ", ".join(unsupported)
            raise ValueError(f"Unsupported attributes for {self.tag}: {names}")

        object.__setattr__(self, "attrs", MappingProxyType(attrs))
        object.__setattr__(self, "children", tuple(self.children))


@dataclass(frozen=True)
class VectorIcon:
    """Source-independent vector artwork and its provenance."""

    key: str
    title: str
    source: str
    view_box: tuple[float, float, float, float]
    nodes: tuple[VectorNode, ...]
    aliases: tuple[str, ...] = ()
    source_url: str | None = None
    license: str | None = None
    guidelines_url: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "view_box", tuple(self.view_box))
        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "aliases", tuple(self.aliases))


@dataclass(frozen=True)
class IconResolution:
    """The selected icon plus an explanation of how it was chosen."""

    icon: VectorIcon
    match_method: MatchMethod
    query: str
    used_fallback: bool

    @property
    def show_initials(self) -> bool:
        """Return whether the composed icon should include name initials."""
        return self.match_method == "generic"
