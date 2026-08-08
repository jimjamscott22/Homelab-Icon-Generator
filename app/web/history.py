"""SQLite-backed record of past generations, powering the artifact gallery.

Deliberately knows nothing about HTTP. Rows store paths relative to the
output directory; callers convert to and from /output/ URLs.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

MAX_ROWS = 500

_SCHEMA = """
CREATE TABLE IF NOT EXISTS generations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  style TEXT NOT NULL,
  theme TEXT NOT NULL,
  custom_color TEXT,
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
  -- Stored for potential future use; recent() intentionally recomputes the
  -- thumbnail fresh from the surviving-files set instead of reading this
  -- back, since a stored value could point at a since-deleted file.
  thumb_rel TEXT,
  -- The real uniqueness constraint: the output path(s) a generation actually
  -- wrote (minus format directory and extension). Two requests that render
  -- to the same file on disk MUST collapse to one row, no matter how their
  -- settings differ (see _derive_output_key). Column is added via migration
  -- for legacy databases, so it can't carry a NOT NULL here for those; new
  -- databases always populate it through record()/the migration backfill.
  output_key TEXT
);
CREATE INDEX IF NOT EXISTS idx_generations_created_at
  ON generations(created_at DESC);
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


def _output_key_from_rel(rel: str) -> str | None:
    """'svg/cloud_service/nextcloud-minimal-blue-256.svg' -> 'cloud_service/nextcloud-minimal-blue-256'.

    Strips the leading format directory and the extension, leaving the part
    of the path that every format of one generation shares — i.e. the real
    identity of "what got written to disk".
    """
    parts = PurePosixPath(rel).parts
    if len(parts) < 2:
        return None
    return str(PurePosixPath(*parts[1:]).with_suffix(""))


def _derive_output_key(files: dict[str, str]) -> str | None:
    """Derive the shared output key from any one entry in a files mapping.

    Every format written by a single generation shares the same base path,
    so the first usable entry is sufficient. Non-string entries (a tampered
    or hand-edited DB) are skipped rather than raising — this must stay a
    plain "couldn't find a key" result so the caller's corruption handling
    (sqlite3.DatabaseError, in _connect) still applies; a stray TypeError
    here would instead crash the gallery outright.
    """
    for rel in files.values():
        if not isinstance(rel, str):
            continue
        key = _output_key_from_rel(rel)
        if key:
            return key
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
            self._migrate(conn)
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
            conn = None
            try:
                conn = sqlite3.connect(self._db_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA journal_mode=WAL")
                conn.executescript(_SCHEMA)
                conn.commit()
                self._migrate(conn)
                return conn
            except Exception:
                if conn is not None:
                    conn.close()
                raise

    @staticmethod
    def _migrate(conn: sqlite3.Connection) -> None:
        """Bring an existing database up to the output_key identity model.

        Idempotent and safe on a brand-new empty database: every step is a
        no-op there (column already present, no old index, no duplicate
        rows to collapse).

        The "add column" and "backfill values" steps are deliberately
        decoupled rather than gated together behind one `if "output_key"
        not in columns` check. `ALTER TABLE` takes effect immediately under
        SQLite's DDL autocommit — Python's sqlite3 module doesn't open an
        implicit transaction until the first DML statement — so a process
        interrupted between the ALTER and the backfill commit leaves a
        database with the column present but every value NULL. If backfill
        were gated on "column absent", the next open would see the column,
        skip backfilling, and the unkeyable-row cleanup below would then
        delete every legacy row. Instead the backfill runs unconditionally,
        scoped to whatever rows still need it, so an interrupted migration
        just resumes on the next open instead of destroying data.
        """
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(generations)")}
        if "custom_color" not in columns:
            conn.execute("ALTER TABLE generations ADD COLUMN custom_color TEXT")
            conn.commit()
        if "output_key" not in columns:
            conn.execute("ALTER TABLE generations ADD COLUMN output_key TEXT")
            conn.commit()

        for row in conn.execute(
            "SELECT id, files FROM generations WHERE output_key IS NULL OR output_key = ''"
        ).fetchall():
            try:
                files = json.loads(row["files"])
            except (json.JSONDecodeError, TypeError):
                files = {}
            key = _derive_output_key(files) if isinstance(files, dict) else None
            if key:
                conn.execute(
                    "UPDATE generations SET output_key = ? WHERE id = ?", (key, row["id"])
                )
        conn.commit()

        # Superseded by the output_key index below; old databases still
        # carry it and it would otherwise conflict with legitimate updates
        # (same output_key, different name/format/icon/etc).
        conn.execute("DROP INDEX IF EXISTS idx_generations_identity")

        # Rows still unkeyed after a real backfill attempt above are
        # genuinely unkeyable (corrupt/empty files) and would break the
        # NOT NULL-equivalent uniqueness constraint below — drop them
        # rather than leave them unmigratable.
        conn.execute("DELETE FROM generations WHERE output_key IS NULL OR output_key = ''")

        # Collapse rows that collide under the real (output_key) identity,
        # keeping the newest write per key — exactly the duplicates this
        # migration exists to clean up.
        conn.execute(
            "DELETE FROM generations WHERE id NOT IN ("
            "  SELECT id FROM ("
            "    SELECT id, ROW_NUMBER() OVER ("
            "      PARTITION BY output_key ORDER BY created_at DESC, id DESC"
            "    ) AS rn FROM generations"
            "  ) WHERE rn = 1"
            ")"
        )

        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_generations_output_key "
            "ON generations(output_key)"
        )
        conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def record(self, payload: dict) -> None:
        files = {fmt: _to_rel(url) for fmt, url in payload["files"].items()}
        output_key = _derive_output_key(files)
        if output_key is None:
            raise ValueError("record() requires at least one usable output file path")
        row = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "name": payload["name"],
            "category": payload["category"],
            "style": payload["style"],
            "theme": payload["theme"],
            "custom_color": payload.get("custom_color"),
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
            "output_key": output_key,
        }
        columns = ", ".join(row)
        placeholders = ", ".join(f":{key}" for key in row)
        # The real identity is output_key (see class docstring / module
        # comment): whatever wrote to the same file wins. Every other column
        # is mutable across regenerations that share that file, so the
        # DO UPDATE SET below covers all of them — a column silently
        # retaining a stale value here is exactly the bug this replaces.
        update_columns = [key for key in row if key != "output_key"]
        updates = ", ".join(f"{key}=excluded.{key}" for key in update_columns)
        with self._lock:
            self._conn.execute(
                f"INSERT INTO generations ({columns}) VALUES ({placeholders}) "
                f"ON CONFLICT(output_key) DO UPDATE SET {updates}",
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

    def _reconcile_locked(self) -> None:
        """Drop rows whose files have all been deleted. Caller holds the lock."""
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
        with self._lock:
            self._reconcile_locked()
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
