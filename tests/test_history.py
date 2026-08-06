"""Gallery store: persistence, upsert, pruning, and disk reconciliation."""

from __future__ import annotations

import json
import sqlite3
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


def test_identical_settings_update_in_place_instead_of_duplicating(
    store, monkeypatch: pytest.MonkeyPatch
) -> None:
    gallery, output_dir = store
    payload = _payload()
    _touch(output_dir, payload["files"]["svg"])
    gallery.record(payload)
    first = gallery.recent()[0]["created_at"]

    import app.web.history as history_module

    class _LaterDatetime(history_module.datetime):
        @classmethod
        def now(cls, tz=None):
            return super().now(tz) + history_module.timedelta(days=1)

    monkeypatch.setattr(history_module, "datetime", _LaterDatetime)
    gallery.record(payload)

    items = gallery.recent()

    assert len(items) == 1
    assert items[0]["created_at"] > first


def test_differing_settings_create_separate_rows(store) -> None:
    """Genuinely different artifacts -- distinct files on disk -- must not merge.

    Unlike settings alone, the file path a generation writes to always moves
    when category/style/theme/size change (see `_output_base` in
    app/generator/renderer.py), so each variant here gets its own path, the
    way the real renderer would produce it.
    """
    gallery, output_dir = store
    variants = [
        _payload(),
        _payload(
            theme="orange",
            files={"svg": "/output/svg/server/nextcloud-orange.svg"},
        ),
        _payload(
            style="terminal",
            files={"svg": "/output/svg/server/nextcloud-terminal.svg"},
        ),
        _payload(
            size=512,
            files={"svg": "/output/svg/server/nextcloud-512.svg"},
        ),
        _payload(
            category="cloud_service",
            files={"svg": "/output/svg/cloud_service/nextcloud.svg"},
        ),
    ]
    for payload in variants:
        _touch(output_dir, payload["files"]["svg"])
        gallery.record(payload)

    assert len(gallery.recent()) == len(variants)


def test_regenerating_with_different_icon_updates_the_existing_row(store) -> None:
    """The reported bug: same output file, different `icon` -> one row, latest wins."""
    gallery, output_dir = store
    payload = _payload(icon="auto", icon_key="nextcloud")
    _touch(output_dir, payload["files"]["svg"])
    gallery.record(payload)

    gallery.record(_payload(icon="generic", icon_key="generic-server"))

    items = gallery.recent()

    assert len(items) == 1
    assert items[0]["icon"] == "generic"
    assert items[0]["icon_key"] == "generic-server"


def test_regenerating_with_different_transparent_bg_updates_the_existing_row(
    store,
) -> None:
    """Same class of bug as `icon`: transparent_bg must not fork the row either."""
    gallery, output_dir = store
    payload = _payload(transparent_bg=False)
    _touch(output_dir, payload["files"]["svg"])
    gallery.record(payload)

    gallery.record(_payload(transparent_bg=True))

    items = gallery.recent()

    assert len(items) == 1
    assert items[0]["transparent_bg"] is True


def test_names_that_slugify_identically_share_one_row(store) -> None:
    """'Next Cloud' and 'next-cloud' both slugify to the same output file."""
    gallery, output_dir = store
    shared_files = {"svg": "/output/svg/server/next-cloud.svg"}
    _touch(output_dir, shared_files["svg"])
    gallery.record(_payload(name="Next Cloud", files=dict(shared_files)))

    gallery.record(_payload(name="next-cloud", files=dict(shared_files)))

    items = gallery.recent()

    assert len(items) == 1
    assert items[0]["name"] == "next-cloud"


def test_regenerated_row_keeps_created_at_bumped_to_the_newest(
    store, monkeypatch: pytest.MonkeyPatch
) -> None:
    gallery, output_dir = store
    payload = _payload(icon="auto")
    _touch(output_dir, payload["files"]["svg"])
    gallery.record(payload)
    first = gallery.recent()[0]["created_at"]

    import app.web.history as history_module

    class _LaterDatetime(history_module.datetime):
        @classmethod
        def now(cls, tz=None):
            return super().now(tz) + history_module.timedelta(days=1)

    monkeypatch.setattr(history_module, "datetime", _LaterDatetime)
    gallery.record(_payload(icon="generic", icon_key="generic-server"))

    items = gallery.recent()

    assert len(items) == 1
    assert items[0]["created_at"] > first


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


_OLD_SCHEMA = """
CREATE TABLE generations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  style TEXT NOT NULL,
  theme TEXT NOT NULL,
  size INTEGER NOT NULL,
  format TEXT NOT NULL,
  transparent_bg INTEGER NOT NULL,
  icon TEXT NOT NULL,
  icon_key TEXT NOT NULL,
  icon_title TEXT,
  icon_source TEXT,
  match_method TEXT,
  used_fallback INTEGER NOT NULL,
  files TEXT NOT NULL,
  thumb_rel TEXT
);
CREATE UNIQUE INDEX idx_generations_identity
  ON generations(name, category, style, theme, size, format, transparent_bg, icon);
"""

_OLD_INSERT = (
    "INSERT INTO generations (created_at, name, category, style, theme, size, "
    "format, transparent_bg, icon, icon_key, icon_title, icon_source, "
    "match_method, used_fallback, files, thumb_rel) "
    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
)


def test_migration_collapses_pre_existing_duplicates_and_rebuilds_the_index(
    tmp_path: Path,
) -> None:
    """A DB built under the old (name, ..., icon) identity has exactly the
    duplicate the reported bug produces: two rows, one file on disk. Opening
    a GalleryStore on it must migrate to one row -- the newest -- under a
    working output_key unique index.
    """
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    db_path = output_dir / ".gallery.db"
    files_rel = {"svg": "svg/server/nextcloud.svg"}

    conn = sqlite3.connect(db_path)
    conn.executescript(_OLD_SCHEMA)
    conn.execute(
        _OLD_INSERT,
        (
            "2024-01-01T00:00:00+00:00", "Nextcloud", "server", "minimal", "blue",
            256, "svg", 0, "auto", "nextcloud", "Nextcloud", "simple-icons",
            "catalog", 0, json.dumps(files_rel), files_rel["svg"],
        ),
    )
    conn.execute(
        _OLD_INSERT,
        (
            "2024-01-02T00:00:00+00:00", "Nextcloud", "server", "minimal", "blue",
            256, "svg", 0, "generic", "generic-server", None, None,
            "fallback", 1, json.dumps(files_rel), files_rel["svg"],
        ),
    )
    conn.commit()
    conn.close()

    _touch(output_dir, "/output/svg/server/nextcloud.svg")

    gallery = GalleryStore(db_path, output_dir)
    try:
        items = gallery.recent()

        assert len(items) == 1
        assert items[0]["icon"] == "generic"
        assert items[0]["icon_key"] == "generic-server"
        assert items[0]["used_fallback"] is True

        indexes = {
            row[0]
            for row in gallery._conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()
        }
        assert "idx_generations_output_key" in indexes
        assert "idx_generations_identity" not in indexes

        # The unique index now guards output_key, not the old settings tuple:
        # a raw insert colliding only on output_key must be rejected.
        with pytest.raises(sqlite3.IntegrityError):
            gallery._conn.execute(
                "INSERT INTO generations (created_at, name, category, style, "
                "theme, size, format, transparent_bg, icon, icon_key, "
                "icon_title, icon_source, match_method, used_fallback, "
                "files, thumb_rel, output_key) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    "2024-01-03T00:00:00+00:00", "Nextcloud", "server",
                    "minimal", "blue", 256, "svg", 0, "auto", "nextcloud",
                    "Nextcloud", "simple-icons", "catalog", 0,
                    json.dumps(files_rel), files_rel["svg"],
                    "server/nextcloud",
                ),
            )
    finally:
        gallery.close()


def test_migration_is_a_no_op_on_a_brand_new_database(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    gallery = GalleryStore(output_dir / ".gallery.db", output_dir)
    try:
        payload = _payload()
        _touch(output_dir, payload["files"]["svg"])
        gallery.record(payload)

        assert len(gallery.recent()) == 1
    finally:
        gallery.close()
