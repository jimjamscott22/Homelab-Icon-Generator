"""Gallery store: persistence, upsert, pruning, and disk reconciliation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.web.history import MAX_ROWS, GalleryStore


def _payload(name: str = "Nextcloud", **overrides) -> dict:
    payload = {
        "files": {"svg": f"/output/svg/server/{name.lower()}.svg"},
        "name": name,
        "category": "server",
        "style": "minimal",
        "theme": "blue",
        "size": 256,
        "format": "svg",
        "transparent_bg": False,
        "icon": "auto",
        "icon_key": "nextcloud",
        "icon_title": "Nextcloud",
        "icon_source": "simple-icons",
        "match_method": "catalog",
        "used_fallback": False,
    }
    payload.update(overrides)
    return payload


def _touch(output_dir: Path, url: str) -> Path:
    path = output_dir / url.removeprefix("/output/")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("<svg/>", encoding="utf-8")
    return path


@pytest.fixture
def store(tmp_path: Path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    gallery = GalleryStore(output_dir / ".gallery.db", output_dir)
    yield gallery, output_dir
    gallery.close()


def test_record_round_trips_settings(store) -> None:
    gallery, output_dir = store
    payload = _payload()
    _touch(output_dir, payload["files"]["svg"])
    gallery.record(payload)

    items = gallery.recent()

    assert len(items) == 1
    assert items[0]["name"] == "Nextcloud"
    assert items[0]["icon_key"] == "nextcloud"
    assert items[0]["used_fallback"] is False
    assert items[0]["transparent_bg"] is False
    assert items[0]["files"] == {"svg": "/output/svg/server/nextcloud.svg"}
    assert items[0]["thumb"] == "/output/svg/server/nextcloud.svg"


def test_identical_settings_update_in_place_instead_of_duplicating(store) -> None:
    gallery, output_dir = store
    payload = _payload()
    _touch(output_dir, payload["files"]["svg"])
    gallery.record(payload)
    first = gallery.recent()[0]["created_at"]
    gallery.record(payload)

    items = gallery.recent()

    assert len(items) == 1
    assert items[0]["created_at"] >= first


def test_differing_settings_create_separate_rows(store) -> None:
    gallery, output_dir = store
    blue = _payload()
    orange = _payload(theme="orange")
    _touch(output_dir, blue["files"]["svg"])
    gallery.record(blue)
    gallery.record(orange)

    assert len(gallery.recent()) == 2


def test_cap_prunes_oldest_rows_but_never_touches_files(store) -> None:
    gallery, output_dir = store
    paths = []
    for index in range(MAX_ROWS + 5):
        payload = _payload(name=f"Service{index}")
        paths.append(_touch(output_dir, payload["files"]["svg"]))
        gallery.record(payload)

    items = gallery.recent(limit=MAX_ROWS)

    assert len(items) == MAX_ROWS
    assert items[0]["name"] == f"Service{MAX_ROWS + 4}"
    assert all(path.is_file() for path in paths), "pruning must not delete artwork"


def test_rows_are_dropped_once_every_file_is_gone(store) -> None:
    gallery, output_dir = store
    payload = _payload()
    path = _touch(output_dir, payload["files"]["svg"])
    gallery.record(payload)
    path.unlink()

    assert gallery.recent() == []


def test_partially_deleted_rows_survive_and_report_only_live_files(store) -> None:
    gallery, output_dir = store
    payload = _payload(
        format="both",
        files={
            "svg": "/output/svg/server/nextcloud.svg",
            "png": "/output/png/server/nextcloud.png",
        },
    )
    _touch(output_dir, payload["files"]["svg"])
    png = _touch(output_dir, payload["files"]["png"])
    gallery.record(payload)
    png.unlink()

    items = gallery.recent()

    assert len(items) == 1
    assert set(items[0]["files"]) == {"svg"}
    assert items[0]["thumb"] == "/output/svg/server/nextcloud.svg"


def test_offset_pages_through_history(store) -> None:
    gallery, output_dir = store
    for index in range(5):
        payload = _payload(name=f"Service{index}")
        _touch(output_dir, payload["files"]["svg"])
        gallery.record(payload)

    page = gallery.recent(limit=2, offset=2)

    assert [item["name"] for item in page] == ["Service2", "Service1"]


def test_corrupt_database_is_moved_aside_and_recreated(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    db_path = output_dir / ".gallery.db"
    db_path.write_bytes(b"this is not a database")

    gallery = GalleryStore(db_path, output_dir)
    try:
        assert gallery.recent() == []
        assert db_path.with_suffix(".db.bad").is_file()
    finally:
        gallery.close()
