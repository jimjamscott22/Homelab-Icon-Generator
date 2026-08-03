"""Manifest-driven loading and sanitization for local custom SVG icons."""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, Mapping

from defusedxml import ElementTree

from app.icons.models import VectorIcon, VectorNode
from app.icons.naming import normalize_icon_name


SVG_NS = "http://www.w3.org/2000/svg"
_KEY = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
_TRANSFORM = re.compile(
    rf"^(?:\s*(?:matrix|translate|scale|rotate|skewX|skewY)\s*"
    rf"\(\s*{_NUMBER}(?:[\s,]+{_NUMBER})*\s*\)\s*)+$"
)
_ALLOWED_TAGS = frozenset(
    {"path", "rect", "circle", "ellipse", "line", "polygon", "polyline", "g"}
)
_ROOT_ATTRIBUTES = frozenset({"viewBox", "width", "height", "role", "aria-label"})


class CustomIconError(ValueError):
    """Raised when a custom SVG crosses the geometry-only safety boundary."""


@dataclass(frozen=True)
class CustomIconDiagnostic:
    key: str | None
    filename: str
    severity: Literal["warning", "error"]
    message: str


@dataclass(frozen=True)
class CustomRegistry:
    """Valid custom icons plus normalized lookup aliases and isolated errors."""

    icons: Mapping[str, VectorIcon]
    aliases: Mapping[str, str]
    diagnostics: tuple[CustomIconDiagnostic, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "icons", MappingProxyType(dict(self.icons)))
        object.__setattr__(self, "aliases", MappingProxyType(dict(self.aliases)))
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))

    def get(self, key: str) -> VectorIcon | None:
        return self.icons.get(key)

    def exact(self, query: str) -> VectorIcon | None:
        key = self.aliases.get(normalize_icon_name(query))
        return self.icons.get(key) if key is not None else None

    def suggest(self, query: str, *, limit: int = 8) -> tuple[VectorIcon, ...]:
        from difflib import SequenceMatcher

        normalized = normalize_icon_name(query)
        if not normalized or limit <= 0:
            return ()
        scores: dict[str, float] = {}
        for name, key in self.aliases.items():
            score = SequenceMatcher(None, normalized, name).ratio()
            scores[key] = max(scores.get(key, 0.0), score)
        ranked = sorted(
            (
                (score, key, self.icons[key])
                for key, score in scores.items()
                if score >= 0.6
            ),
            key=lambda item: (-item[0], item[1]),
        )
        return tuple(item[2] for item in ranked[:limit])

    def diagnostic_for(self, key: str) -> CustomIconDiagnostic | None:
        for diagnostic in self.diagnostics:
            if diagnostic.key == key and diagnostic.severity == "error":
                return diagnostic
        return None


def _local_name(value: str) -> str:
    return value.rsplit("}", 1)[-1]


def _view_box(root: Any) -> tuple[float, float, float, float]:
    values = re.split(r"[\s,]+", root.attrib.get("viewBox", "").strip())
    try:
        parsed = tuple(float(value) for value in values)
    except ValueError as exc:
        raise CustomIconError("viewBox must contain four finite numbers") from exc
    if (
        len(parsed) != 4
        or not all(math.isfinite(value) for value in parsed)
        or parsed[2] <= 0
        or parsed[3] <= 0
    ):
        raise CustomIconError("viewBox must contain four finite numbers with positive size")
    return parsed  # type: ignore[return-value]


def _validate_transform(value: str) -> None:
    if not _TRANSFORM.fullmatch(value):
        raise CustomIconError("transform contains unsupported or non-finite values")
    numbers = re.findall(_NUMBER, value)
    if not numbers or not all(math.isfinite(float(number)) for number in numbers):
        raise CustomIconError("transform contains unsupported or non-finite values")


def _node(element: Any) -> VectorNode:
    tag = _local_name(element.tag)
    if tag not in _ALLOWED_TAGS:
        raise CustomIconError(f"unsupported element: {tag}")
    attrs: dict[str, str] = {}
    for raw_name, raw_value in element.attrib.items():
        name = _local_name(raw_name)
        lowered = name.casefold()
        if lowered.startswith("on"):
            raise CustomIconError("event-handler attributes are not allowed")
        if lowered in {"href", "style"} or "url(" in raw_value.casefold():
            raise CustomIconError("external resources and references are not allowed")
        if name == "transform":
            _validate_transform(raw_value)
        if tag == "path" and name == "d":
            if not raw_value.strip() or re.search(r"\b(?:nan|inf)\b", raw_value, re.I):
                raise CustomIconError("path data must be non-empty and finite")
        if name in {"fill", "stroke"} and raw_value != "none":
            raw_value = "currentColor"
        attrs[name] = raw_value
    children = tuple(_node(child) for child in element if _local_name(child.tag) != "title")
    try:
        return VectorNode(tag, attrs, children)  # type: ignore[arg-type]
    except ValueError as exc:
        raise CustomIconError(str(exc)) from exc


def parse_custom_svg(svg_text: str, *, key: str, title: str) -> VectorIcon:
    """Parse one SVG into safe, recolorable normalized geometry."""
    try:
        root = ElementTree.fromstring(svg_text)
    except Exception as exc:
        raise CustomIconError(f"malformed SVG: {exc}") from exc
    if _local_name(root.tag) != "svg":
        raise CustomIconError("root element must be svg")
    namespace = root.tag[1:].split("}", 1)[0] if root.tag.startswith("{") else ""
    if namespace not in {"", SVG_NS}:
        raise CustomIconError("root element must use the SVG namespace")
    for raw_name, raw_value in root.attrib.items():
        name = _local_name(raw_name)
        if name.casefold().startswith("on"):
            raise CustomIconError("event-handler attributes are not allowed")
        if name not in _ROOT_ATTRIBUTES or "url(" in raw_value.casefold():
            raise CustomIconError(f"unsupported svg attribute: {name}")

    nodes = tuple(_node(child) for child in root if _local_name(child.tag) != "title")
    if not nodes:
        raise CustomIconError("SVG must contain at least one geometry element")
    return VectorIcon(
        key=key,
        title=title,
        source="custom",
        view_box=_view_box(root),
        nodes=nodes,
    )


def _empty(*diagnostics: CustomIconDiagnostic) -> CustomRegistry:
    return CustomRegistry({}, {}, diagnostics)


def load_custom_registry(path: str | Path | None) -> CustomRegistry:
    """Load valid manifest entries while retaining diagnostics for invalid ones."""
    if path is None:
        return _empty()
    directory = Path(path)
    if not directory.exists():
        return _empty()
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        return _empty(
            CustomIconDiagnostic(None, "manifest.json", "error", "manifest.json is missing")
        )
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _empty(CustomIconDiagnostic(None, "manifest.json", "error", str(exc)))
    entries = payload.get("icons") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        return _empty(
            CustomIconDiagnostic(
                None, "manifest.json", "error", "manifest must contain an icons array"
            )
        )

    icons: dict[str, VectorIcon] = {}
    aliases: dict[str, str] = {}
    diagnostics: list[CustomIconDiagnostic] = []
    for entry in entries:
        key = entry.get("key") if isinstance(entry, dict) else None
        filename = entry.get("file", "manifest.json") if isinstance(entry, dict) else "manifest.json"
        try:
            if not isinstance(entry, dict):
                raise CustomIconError("manifest icon entry must be an object")
            title = entry.get("name")
            raw_aliases = entry.get("aliases", [])
            if not isinstance(key, str) or not _KEY.fullmatch(key):
                raise CustomIconError("key must be a lowercase kebab-case identifier")
            if key in icons:
                raise CustomIconError(f"duplicate custom icon key: {key}")
            if not isinstance(title, str) or not title.strip():
                raise CustomIconError("name must be a non-empty string")
            if (
                not isinstance(filename, str)
                or Path(filename).name != filename
                or Path(filename).suffix.casefold() != ".svg"
            ):
                raise CustomIconError("file must name an SVG in the custom icon directory")
            if not isinstance(raw_aliases, list) or not all(
                isinstance(alias, str) and alias.strip() for alias in raw_aliases
            ):
                raise CustomIconError("aliases must be an array of non-empty strings")
            icon_path = directory / filename
            svg_text = icon_path.read_text(encoding="utf-8")
            parsed = parse_custom_svg(svg_text, key=key, title=title.strip())
            icon = VectorIcon(
                key=parsed.key,
                title=parsed.title,
                source=parsed.source,
                view_box=parsed.view_box,
                nodes=parsed.nodes,
                aliases=tuple(sorted(set(raw_aliases), key=str.casefold)),
            )
            lookup_names = {key, title, *raw_aliases}
            normalized_names = {normalize_icon_name(name) for name in lookup_names}
            collisions = sorted(name for name in normalized_names if name in aliases)
            if collisions:
                raise CustomIconError(
                    "normalized name collides with another custom icon: "
                    + ", ".join(collisions)
                )
            icons[key] = icon
            aliases.update({name: key for name in normalized_names})
        except (CustomIconError, OSError, UnicodeError) as exc:
            diagnostics.append(
                CustomIconDiagnostic(
                    key if isinstance(key, str) else None,
                    str(filename),
                    "error",
                    str(exc),
                )
            )
    return CustomRegistry(icons, aliases, tuple(diagnostics))


def resolve_custom_icon_dir(explicit: str | Path | None = None) -> Path | None:
    """Apply CLI/server, environment, then working-directory precedence."""
    if explicit:
        return Path(explicit).expanduser()
    configured = os.environ.get("HOMELAB_ICON_DIR")
    if configured:
        return Path(configured).expanduser()
    candidate = Path.cwd() / "custom-icons"
    return candidate if (candidate / "manifest.json").is_file() else None
