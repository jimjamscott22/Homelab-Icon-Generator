"""Tests for loading and searching the offline brand registry."""

from __future__ import annotations

import json
from pathlib import Path

from app.icons.catalog import icons_from_catalog
from app.icons.registry import CatalogRegistry
from scripts.sync_simple_icons import sync_catalog


FIXTURES = Path(__file__).parent / "fixtures"


def _registry(tmp_path: Path) -> CatalogRegistry:
    result = sync_catalog(
        FIXTURES / "simple-icons-package",
        "16.27.0",
        tmp_path,
        FIXTURES / "homelab-aliases.json",
    )
    payload = json.loads(result.catalog_path.read_text(encoding="utf-8"))
    return CatalogRegistry(icons_from_catalog(payload))


def test_registry_indexes_keys_titles_and_reviewed_aliases(tmp_path: Path) -> None:
    registry = _registry(tmp_path)

    assert registry.get("homeassistant").title == "Home Assistant"
    assert registry.exact("HOME ASSISTANT").key == "homeassistant"
    assert registry.exact("home-assistant").key == "homeassistant"
    assert registry.exact("Home Assistant Core").key == "homeassistant"
    assert registry.exact("ha").key == "homeassistant"
    assert registry.exact("does not exist") is None


def test_registry_suggestions_are_ranked_and_deterministic(tmp_path: Path) -> None:
    registry = _registry(tmp_path)

    first = registry.suggest("home assist", limit=2)
    second = registry.suggest("home assist", limit=2)

    assert [icon.key for icon in first] == ["homeassistant"]
    assert first == second


def test_catalog_records_become_vector_icons(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    icon = registry.get("nextcloud")

    assert icon.source == "simple-icons"
    assert icon.view_box == (0.0, 0.0, 24.0, 24.0)
    assert icon.nodes[0].tag == "path"
    assert icon.nodes[0].attrs["d"].startswith("M7 7")
