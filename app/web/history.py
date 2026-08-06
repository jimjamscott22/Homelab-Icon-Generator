"""SQLite-backed record of past generations, powering the artifact gallery.

Deliberately knows nothing about HTTP. Rows store paths relative to the
output directory; callers convert to and from /output/ URLs.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

MAX_ROWS = 500

#: Regenerating with these values identical overwrites the same file on disk,
#: so the row is updated and bumped rather than duplicated.
_IDENTITY = ("name", "category", "style", "theme", "size", "format", "transparent_bg", "icon")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS generations (
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
CREATE INDEX IF NOT EXISTS idx_generations_created_at
  ON generations(created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_generations_identity
  ON generations(name, category, style, theme, size, format, transparent_bg, icon);
"""

_URL_PREFIX = "/output/"


def _to_rel(url: str) -> str:
    """'/output/svg/server/x.svg' -> 'svg/server/x.svg'."""
    return url[len(_URL_PREFIX):] if url.startswith(_URL_PREFIX) else url.lstrip("/")


def _to_url(rel: str) -> str:
    return _URL_PREFIX + rel


def _pick_thumb(files: dict[str, str]) -> str | None:
    """png, else svg, else ico — an ICO-only build still gets a tile."""
    for fmt in ("png", "svg", "ico"):
        if fmt in files:
            return files[fmt]
    return None


class GalleryStore:
    def __init__(self, db_path: Path, output_dir: Path) -> None:
        self._db_path = Path(db_path)
        self._output_dir = Path(output_dir)
        self._lock = threading.Lock()
        self._conn = self._connect()

    def _connect(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn: sqlite3.Connection | None = None
        try:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(_SCHEMA)
            conn.commit()
            return conn
        except sqlite3.DatabaseError:
            # Corrupt file: move it aside and start clean. History is a
            # convenience; refusing to start over it would be worse.
            if conn is not None:
                # Windows keeps the file handle open until the connection is
                # closed, which would make the rename below fail.
                conn.close()
            bad = self._db_path.with_suffix(self._db_path.suffix + ".bad")
            bad.unlink(missing_ok=True)
            self._db_path.replace(bad)
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(_SCHEMA)
            conn.commit()
            return conn

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def record(self, payload: dict) -> None:
        files = {fmt: _to_rel(url) for fmt, url in payload["files"].items()}
        row = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "name": payload["name"],
            "category": payload["category"],
            "style": payload["style"],
            "theme": payload["theme"],
            "size": int(payload["size"]),
            "format": payload["format"],
            "transparent_bg": int(bool(payload["transparent_bg"])),
            "icon": payload["icon"],
            "icon_key": payload["icon_key"],
            "icon_title": payload.get("icon_title"),
            "icon_source": payload.get("icon_source"),
            "match_method": payload.get("match_method"),
            "used_fallback": int(bool(payload["used_fallback"])),
            "files": json.dumps(files),
            "thumb_rel": _pick_thumb(files),
        }
        columns = ", ".join(row)
        placeholders = ", ".join(f":{key}" for key in row)
        conflict = ", ".join(_IDENTITY)
        with self._lock:
            self._conn.execute(
                f"INSERT INTO generations ({columns}) VALUES ({placeholders}) "
                f"ON CONFLICT({conflict}) DO UPDATE SET "
                "created_at=excluded.created_at, files=excluded.files, "
                "thumb_rel=excluded.thumb_rel, icon_key=excluded.icon_key, "
                "icon_title=excluded.icon_title, icon_source=excluded.icon_source, "
                "match_method=excluded.match_method, "
                "used_fallback=excluded.used_fallback",
                row,
            )
            # Prune rows only. Files on disk are never deleted automatically.
            self._conn.execute(
                "DELETE FROM generations WHERE id NOT IN ("
                "  SELECT id FROM generations"
                "  ORDER BY created_at DESC, id DESC LIMIT ?)",
                (MAX_ROWS,),
            )
            self._conn.commit()

    def _reconcile(self) -> None:
        """Drop rows whose files have all been deleted from disk."""
        with self._lock:
            rows = self._conn.execute("SELECT id, files FROM generations").fetchall()
            dead = [
                row["id"]
                for row in rows
                if not any(
                    (self._output_dir / rel).is_file()
                    for rel in json.loads(row["files"]).values()
                )
            ]
            if dead:
                self._conn.executemany(
                    "DELETE FROM generations WHERE id = ?", [(i,) for i in dead]
                )
                self._conn.commit()

    def recent(self, limit: int = 50, offset: int = 0) -> list[dict]:
        self._reconcile()
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM generations "
                "ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
                (max(1, min(limit, MAX_ROWS)), max(0, offset)),
            ).fetchall()

        items = []
        for row in rows:
            files = json.loads(row["files"])
            # A partially deleted set keeps the row; only survivors are returned.
            surviving = {
                fmt: _to_url(rel)
                for fmt, rel in files.items()
                if (self._output_dir / rel).is_file()
            }
            item = {key: row[key] for key in row.keys() if key not in {"files", "thumb_rel"}}
            item["transparent_bg"] = bool(row["transparent_bg"])
            item["used_fallback"] = bool(row["used_fallback"])
            item["files"] = surviving
            item["thumb"] = _pick_thumb(surviving)
            items.append(item)
        return items
