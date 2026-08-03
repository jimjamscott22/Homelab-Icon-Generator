"""Load serialized brand catalog records into normalized vector icons."""

from __future__ import annotations

import json
from importlib import resources
from typing import Any, Iterable, Mapping

from app.icons.models import VectorIcon, VectorNode


def icons_from_catalog(payload: Mapping[str, Any]) -> Iterable[VectorIcon]:
    """Yield validated vector icons from one serialized catalog payload."""
    if payload.get("catalog") != "simple-icons" or not isinstance(
        payload.get("icons"), list
    ):
        raise ValueError("Unsupported or malformed icon catalog")
    for record in payload["icons"]:
        yield VectorIcon(
            key=record["key"],
            title=record["title"],
            source="simple-icons",
            view_box=tuple(record["view_box"]),
            nodes=(VectorNode("path", {"d": record["path"]}),),
            aliases=tuple(record.get("aliases", ())),
            source_url=record.get("source_url"),
            license=record.get("license"),
            guidelines_url=record.get("guidelines_url"),
        )


def load_builtin_icons() -> tuple[VectorIcon, ...]:
    """Load the catalog bundled inside the installed application package."""
    catalog = resources.files("app.icons.data").joinpath("simple-icons.json")
    payload = json.loads(catalog.read_text(encoding="utf-8"))
    return tuple(icons_from_catalog(payload))
