"""Tests for the deterministic Simple Icons catalog importer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sync_simple_icons import sync_catalog


FIXTURES = Path(__file__).parent / "fixtures"
PACKAGE = FIXTURES / "simple-icons-package"
ALIASES = FIXTURES / "homelab-aliases.json"


def test_sync_catalog_is_deterministic_and_preserves_provenance(tmp_path: Path) -> None:
    first = sync_catalog(PACKAGE, "16.27.0", tmp_path / "first", ALIASES)
    second = sync_catalog(PACKAGE, "16.27.0", tmp_path / "second", ALIASES)

    assert first.catalog_path.read_bytes() == second.catalog_path.read_bytes()
    assert first.manifest_path.read_bytes() == second.manifest_path.read_bytes()
    assert first.notice_path.read_bytes() == second.notice_path.read_bytes()

    catalog = json.loads(first.catalog_path.read_text(encoding="utf-8"))
    assert [icon["key"] for icon in catalog["icons"]] == [
        "homeassistant",
        "nextcloud",
    ]
    home_assistant = catalog["icons"][0]
    assert home_assistant["path"] == "M12 1 2 10v13h7v-7h6v7h7V10z"
    assert home_assistant["aliases"] == ["ha", "Hass", "Home Assistant Core"]
    assert home_assistant["source_url"] == "https://www.home-assistant.io/"
    assert home_assistant["license"] == "CC-BY-4.0"
    assert home_assistant["guidelines_url"].startswith("https://")

    manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    assert manifest["version"] == "16.27.0"
    assert manifest["icon_count"] == 2
    assert len(manifest["content_sha256"]) == 64


def test_sync_catalog_rejects_alias_to_missing_icon(tmp_path: Path) -> None:
    aliases = tmp_path / "aliases.json"
    aliases.write_text('{"unknown appliance": "missing"}', encoding="utf-8")

    with pytest.raises(ValueError, match="missing"):
        sync_catalog(PACKAGE, "16.27.0", tmp_path / "out", aliases)
