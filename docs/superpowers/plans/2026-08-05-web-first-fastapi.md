# Web-First FastAPI Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Web UI the primary interface — move the server into the `app` package so it ships in the wheel, swap Flask for FastAPI/uvicorn, launch it from a desktop icon, and back the artifact strip with a persistent gallery.

**Architecture:** `server.py` moves into `app/web/` as four focused modules: `api.py` (HTTP), `schemas.py` (shape validation only), `history.py` (SQLite gallery store), `launcher.py` (process lifecycle). `homelab-icons` with no arguments starts uvicorn and opens a browser; with flags it runs today's CLI unchanged. A heartbeat from the page keeps the server alive; closing the tab lets it exit.

**Tech Stack:** Python 3.10+, FastAPI, uvicorn, Pydantic v2, stdlib `sqlite3`, vanilla JS, pytest, UV, hatchling.

**Source spec:** `docs/superpowers/specs/2026-08-05-web-first-fastapi-design.md`

## Global Constraints

- Python 3.10+. Use `from __future__ import annotations` in new modules, matching the codebase.
- Every dependency and command runs through UV: `uv sync`, `uv run pytest -q`, `uv build`.
- **`IconRequest` and `app/utils/validation.py` remain the single source of truth for domain rules.** Pydantic models validate shape only — presence and type. Never duplicate the category/style/theme/format/size rules into Pydantic.
- Existing route payloads must stay byte-identical so the current `app.js` keeps working: `/`, `/api/options`, `/api/icons/search`, `POST /api/generate`, `/output/{fmt}/{category}/{filename}`.
- Server binds `127.0.0.1` only. Normal generation must not access the network.
- Env vars keep their names and defaults: `PORT` (5000), `GENERATE_RATE_LIMIT` (20), `GENERATE_RATE_WINDOW` (60). `FLASK_DEBUG` is retired.
- Gallery retention: newest **500** rows. Heartbeat interval **5s**, timeout **30s**.
- SVG remains the source of truth for rendering. Do not add a second Pillow drawing path.
- Markdown tables in docs use the repo's compact style (`|---|---|`), per `README.md:58`.
- Commit after every task. Work on branch `web-first-fastapi`.

## Deviations from the spec (deliberate — both discovered while reading the code)

1. **The gallery reuses the existing `#strip` panel** (`06 — RECENT ARTIFACTS`) rather than adding a new section. `app.js` already has a session-only recent strip (`state.recent`, `renderRecent()`, `_makeSlot()`, 10-item cap). This work upgrades that strip from in-memory to server-backed and makes clicking restore settings. Less new UI, same outcome.
2. **Pagination uses `offset`, not `before=<id>`.** Upsert bumps `created_at` while keeping `id`, so an id cursor is inconsistent with `created_at DESC` ordering. With a hard 500-row cap, `OFFSET` is correct and simpler.

## File Structure

| File | Responsibility |
|---|---|
| `app/web/__init__.py` | Package marker (empty) |
| `app/web/schemas.py` | Pydantic request models; shape only |
| `app/web/history.py` | `GalleryStore` — SQLite persistence, upsert, prune, reconcile. Knows nothing about HTTP |
| `app/web/api.py` | FastAPI app, routes, rate limiter, `Heartbeat`. Delegates all domain work |
| `app/web/launcher.py` | Port selection, single-instance probe, uvicorn, browser, watchdog. Knows nothing about icons |
| `app/web/static/gallery.js` | Server-backed artifact strip; click restores settings |
| `app/main.py` | Gains bare-argv dispatch (modify) |
| `scripts/install_shortcut.py` | Windows `.lnk` generator (maintainer script) |
| `server.py` | **Deleted** |
| `tests/test_server.py` | Rewritten onto FastAPI `TestClient` |
| `tests/test_history.py` | New — store behavior |
| `tests/test_launcher.py` | New — port/probe/watchdog |

---

### Task 1: FastAPI port with identical payloads

Swap the framework with zero behavior change. This task is a clean reviewer gate: if the existing tests pass unchanged in substance, the port is correct.

**Files:**
- Create: `app/web/__init__.py`, `app/web/schemas.py`, `app/web/api.py`
- Delete: `server.py`
- Modify: `pyproject.toml`
- Test: `tests/test_server.py` (rewrite fixture only)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `app.web.api.app` (FastAPI instance), `app.web.api.OUTPUT_DIR` (module-level `Path`, read at request time so tests can monkeypatch it), `app.web.api._req_times` (rate-limiter deque), `app.web.schemas.GenerateRequest`.

- [ ] **Step 1: Update dependencies**

In `pyproject.toml`, replace `"flask>=3.0.0"` with FastAPI and uvicorn, and add `httpx` to the dev group:

```toml
dependencies = [
    "pillow>=10.1.0",
    "fastapi>=0.115.0",
    "uvicorn>=0.30.0",
    "resvg-py==0.3.3",
    "defusedxml>=0.7.1,<0.8",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "httpx>=0.27.0",
]
```

- [ ] **Step 2: Sync**

Run: `uv sync`
Expected: resolves; `flask` disappears, `fastapi`/`uvicorn`/`httpx` appear.

- [ ] **Step 3: Create the package marker**

Create `app/web/__init__.py` as an empty file. `app/web/` currently has no `__init__.py` — without it the module is not importable.

- [ ] **Step 4: Write `app/web/schemas.py`**

Every field has a default. This is deliberate: Flask used `request.get_json(silent=True) or {}`, so a missing body produced empty values and a **400** from `IconRequest`. Required Pydantic fields would return 422 instead and change behavior.

```python
"""Pydantic edge models for the web API.

Shape validation only — field presence and type. Every domain rule
(categories, styles, themes, formats, size bounds) lives in IconRequest and
app/utils/validation.py and must not be duplicated here.
"""

from __future__ import annotations

from pydantic import BaseModel


class GenerateRequest(BaseModel):
    """Body of POST /api/generate. Defaults mirror the previous Flask route."""

    name: str = ""
    category: str = ""
    style: str = "minimal"
    theme: str = "blue"
    size: int = 256
    format: str = "both"
    icon: str = "auto"
    transparent_bg: bool = False
```

- [ ] **Step 5: Write `app/web/api.py`**

Note three things. Routes are `def`, not `async def` — icon generation is CPU-bound in resvg, so FastAPI runs them in its threadpool where they belong. `OUTPUT_DIR` is read inside handlers so tests can monkeypatch the module global. The validation-error handler returns `{"error": ...}` so the frontend has one error shape to parse.

```python
"""FastAPI web interface for the Homelab Icon Generator."""

from __future__ import annotations

import collections
import os
import threading
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.generator.renderer import generate_icon_result
from app.icons.models import VectorIcon
from app.icons.resolver import get_default_resolver
from app.models.icon_request import IconRequest
from app.utils.validation import (
    VALID_CATEGORIES,
    VALID_FORMATS,
    VALID_STYLES,
    VALID_THEMES,
)
from app.web.schemas import GenerateRequest

ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = Path(__file__).resolve().parent / "static"
OUTPUT_DIR = ROOT / "output"

app = FastAPI(title="Homelab Icon Generator", docs_url="/api/docs", redoc_url=None)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Sliding-window rate limiter for /api/generate (no external dependency needed).
_RATE_LIMIT = int(os.environ.get("GENERATE_RATE_LIMIT", 20))  # requests
_RATE_WINDOW = int(os.environ.get("GENERATE_RATE_WINDOW", 60))  # seconds
_req_times: collections.deque[float] = collections.deque()
_rate_lock = threading.Lock()


def _allow_request() -> bool:
    now = time.monotonic()
    with _rate_lock:
        while _req_times and now - _req_times[0] > _RATE_WINDOW:
            _req_times.popleft()
        if len(_req_times) >= _RATE_LIMIT:
            return False
        _req_times.append(now)
        return True


@app.exception_handler(RequestValidationError)
def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Normalise FastAPI's 422 body to the {"error": ...} shape the UI parses."""
    return JSONResponse({"error": "malformed request body"}, status_code=422)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/options")
def options() -> dict:
    resolver = get_default_resolver()
    return {
        "categories": sorted(VALID_CATEGORIES),
        "styles": sorted(VALID_STYLES),
        "themes": sorted(VALID_THEMES),
        "formats": sorted(VALID_FORMATS),
        "icon_modes": ["auto", "generic"],
        "icon_diagnostics": [
            asdict(item) if is_dataclass(item) else str(item)
            for item in resolver.diagnostics
        ],
    }


def _icon_payload(icon: VectorIcon) -> dict[str, str | None]:
    return {
        "key": icon.key,
        "title": icon.title,
        "source": icon.source,
        "source_url": icon.source_url,
        "license": icon.license,
        "guidelines_url": icon.guidelines_url,
    }


@app.get("/api/icons/search")
def search_icons(q: str = "", limit: int = 8):
    query = q.strip()
    limit = max(1, min(limit, 20))
    if not query:
        return {"exact": None, "items": [], "query": query}

    resolver = get_default_resolver()
    exact = resolver.exact(query)
    return {
        "exact": _icon_payload(exact) if exact is not None else None,
        "items": [_icon_payload(icon) for icon in resolver.suggest(query, limit=limit)],
        "query": query,
    }


@app.post("/api/generate")
def generate(payload: GenerateRequest | None = None):
    if not _allow_request():
        return JSONResponse(
            {"error": "rate limit exceeded — try again shortly"}, status_code=429
        )
    data = payload or GenerateRequest()
    try:
        req = IconRequest(
            name=data.name.strip(),
            category=data.category,
            style=data.style,
            theme=data.theme,
            size=data.size,
            format=data.format,
            icon=data.icon,
            transparent_bg=data.transparent_bg,
            output_dir=str(OUTPUT_DIR),
        )
        started = time.perf_counter()
        result = generate_icon_result(req, resolver=get_default_resolver())
        elapsed_ms = int((time.perf_counter() - started) * 1000)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except Exception as exc:
        return JSONResponse({"error": f"generation failed: {exc}"}, status_code=500)

    files = {
        fmt: f"/output/{Path(p).resolve().relative_to(OUTPUT_DIR.resolve()).as_posix()}"
        for fmt, p in result.paths.items()
    }
    return {
        "files": files,
        "elapsed_ms": elapsed_ms,
        "name": req.name,
        "category": req.category,
        "style": req.style,
        "theme": req.theme,
        "size": req.size,
        "format": req.format,
        "transparent_bg": req.transparent_bg,
        "icon": req.icon,
        "icon_key": result.resolution.icon.key,
        "icon_title": result.resolution.icon.title,
        "icon_source": result.resolution.icon.source,
        "match_method": result.resolution.match_method,
        "used_fallback": result.resolution.used_fallback,
    }


_OUTPUT_FORMATS = frozenset({"png", "svg", "ico"})
_OUTPUT_EXTS = frozenset({".png", ".svg", ".ico"})


@app.get("/output/{fmt}/{category}/{filename}")
def serve_output(fmt: str, category: str, filename: str):
    if fmt not in _OUTPUT_FORMATS or category not in VALID_CATEGORIES:
        return Response(status_code=404)
    if Path(filename).suffix not in _OUTPUT_EXTS:
        return Response(status_code=404)
    base = (OUTPUT_DIR / fmt / category).resolve()
    target = (base / filename).resolve()
    if base not in target.parents or not target.is_file():
        return Response(status_code=404)
    return FileResponse(
        target, headers={"Cache-Control": "public, max-age=31536000, immutable"}
    )
```

- [ ] **Step 6: Delete the old server**

```bash
git rm server.py
```

- [ ] **Step 7: Rewrite the test fixture**

Only the fixture and import change in `tests/test_server.py`. The six test bodies stay exactly as they are — they assert payloads, not framework internals. Replace lines 1-19 with:

```python
"""FastAPI coverage for backend options, icon search, and resolution metadata."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.web import api


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(api, "OUTPUT_DIR", tmp_path / "output")
    api._req_times.clear()
    with TestClient(api.app) as test_client:
        yield test_client
```

Then update the call sites, since `TestClient` returns httpx responses rather than Flask ones:
- `.get_json()` → `.json()`
- `.get_data(as_text=True)` → `.text`
- `client.post("/api/generate", json={...})` is unchanged.

- [ ] **Step 8: Run the ported tests**

Run: `uv run pytest tests/test_server.py -v`
Expected: all 6 PASS.

- [ ] **Step 9: Run the full suite**

Run: `uv run pytest -q`
Expected: all pass. Nothing outside `tests/test_server.py` should be affected.

- [ ] **Step 10: Commit**

```bash
git add pyproject.toml uv.lock app/web tests/test_server.py
git rm --cached server.py 2>/dev/null; git add -A
git commit -m "refactor: port web server from Flask to FastAPI under app/web"
```

---

### Task 2: SQLite gallery store

Pure persistence. No HTTP, no FastAPI import. Testable on its own.

**Files:**
- Create: `app/web/history.py`
- Test: `tests/test_history.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `GalleryStore(db_path: Path, output_dir: Path)`
  - `GalleryStore.record(payload: dict) -> None` — `payload` is the `/api/generate` response dict; `files` values are `/output/...` URL paths.
  - `GalleryStore.recent(limit: int = 50, offset: int = 0) -> list[dict]` — newest first; each dict has the `/api/generate` field names, with `files` back as `/output/...` URLs plus a `thumb` key.
  - `GalleryStore.close() -> None`
  - `MAX_ROWS = 500`

- [ ] **Step 1: Write `app/web/history.py`**

```python
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
```

- [ ] **Step 2: Write `tests/test_history.py`**

```python
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
```

- [ ] **Step 3: Run the store tests**

Run: `uv run pytest tests/test_history.py -v`
Expected: all 8 PASS.

If `test_corrupt_database_is_moved_aside_and_recreated` fails because `sqlite3.connect` succeeds lazily, note that the `executescript` call inside `_connect` is what forces the read and raises `DatabaseError` — keep it there.

- [ ] **Step 4: Ignore the database file**

Append to `.gitignore`, under the existing `# Generated Icons` block:

```gitignore
output/.gallery.db
output/.gallery.db-wal
output/.gallery.db-shm
output/.gallery.db.bad
```

- [ ] **Step 5: Commit**

```bash
git add app/web/history.py tests/test_history.py .gitignore
git commit -m "feat: add SQLite gallery store for generation history"
```

---

### Task 3: Wire history into the API

**Files:**
- Modify: `app/web/api.py`
- Test: `tests/test_server.py` (append)

**Interfaces:**
- Consumes: `app.web.history.GalleryStore`, `app.web.api.OUTPUT_DIR`.
- Produces: `GET /api/history?limit=&offset=` returning `{"items": [...]}`; `app.web.api.get_gallery() -> GalleryStore | None`; `app.web.api.reset_gallery() -> None` for tests.

- [ ] **Step 1: Add a lazily-built store to `app/web/api.py`**

Lazy construction matters — `OUTPUT_DIR` is monkeypatched per test, so the store must not be built at import time.

First add `import logging` to the stdlib import block at the top of the file and `from app.web.history import GalleryStore` to the local import block (next to `from app.web.schemas import GenerateRequest`). Then add the following after the rate limiter block:

```python
_log = logging.getLogger(__name__)
_gallery: GalleryStore | None = None
_gallery_dir: Path | None = None
_gallery_lock = threading.Lock()


def get_gallery() -> GalleryStore | None:
    """Return the store for the current OUTPUT_DIR, rebuilding if it changed.

    Returns None if the store cannot be opened; a broken gallery must never
    stop icons from being generated.
    """
    global _gallery, _gallery_dir
    with _gallery_lock:
        if _gallery is not None and _gallery_dir == OUTPUT_DIR:
            return _gallery
        if _gallery is not None:
            _gallery.close()
            _gallery = None
        try:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            _gallery = GalleryStore(OUTPUT_DIR / ".gallery.db", OUTPUT_DIR)
            _gallery_dir = OUTPUT_DIR
        except Exception:
            _log.exception("gallery unavailable")
            _gallery = None
        return _gallery


def reset_gallery() -> None:
    """Drop the cached store. Used by tests between OUTPUT_DIR swaps."""
    global _gallery, _gallery_dir
    with _gallery_lock:
        if _gallery is not None:
            _gallery.close()
        _gallery = None
        _gallery_dir = None
```

- [ ] **Step 2: Record on successful generation**

In `generate()`, immediately before the `return {...}` statement, build the payload once and record it. Replace the final `return {` block with:

```python
    payload = {
        "files": files,
        "elapsed_ms": elapsed_ms,
        "name": req.name,
        "category": req.category,
        "style": req.style,
        "theme": req.theme,
        "size": req.size,
        "format": req.format,
        "transparent_bg": req.transparent_bg,
        "icon": req.icon,
        "icon_key": result.resolution.icon.key,
        "icon_title": result.resolution.icon.title,
        "icon_source": result.resolution.icon.source,
        "match_method": result.resolution.match_method,
        "used_fallback": result.resolution.used_fallback,
    }
    gallery = get_gallery()
    if gallery is not None:
        try:
            gallery.record(payload)
        except Exception:
            # The icon is the product; history is a convenience.
            _log.exception("failed to record gallery entry")
    return payload
```

- [ ] **Step 3: Add the history route**

Add after `serve_output`:

```python
@app.get("/api/history")
def history(limit: int = 50, offset: int = 0):
    gallery = get_gallery()
    if gallery is None:
        return {"items": []}
    return {"items": gallery.recent(limit=limit, offset=offset)}
```

- [ ] **Step 4: Reset the store in the test fixture**

In `tests/test_server.py`, add `api.reset_gallery()` to the `client` fixture, after the monkeypatch and before the `TestClient` block, plus a teardown call:

```python
@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(api, "OUTPUT_DIR", tmp_path / "output")
    api._req_times.clear()
    api.reset_gallery()
    with TestClient(api.app) as test_client:
        yield test_client
    api.reset_gallery()
```

- [ ] **Step 5: Append API-level history tests**

Add to `tests/test_server.py`:

```python
def test_generate_populates_history(client) -> None:
    client.post(
        "/api/generate",
        json={"name": "Nextcloud", "category": "cloud_service", "format": "svg"},
    )

    items = client.get("/api/history").json()["items"]

    assert len(items) == 1
    assert items[0]["name"] == "Nextcloud"
    assert items[0]["icon_key"] == "nextcloud"
    assert items[0]["thumb"].startswith("/output/svg/")


def test_history_is_empty_before_any_generation(client) -> None:
    assert client.get("/api/history").json()["items"] == []


def test_repeat_generation_does_not_duplicate_history(client) -> None:
    body = {"name": "Nextcloud", "category": "cloud_service", "format": "svg"}
    client.post("/api/generate", json=body)
    client.post("/api/generate", json=body)

    assert len(client.get("/api/history").json()["items"]) == 1
```

- [ ] **Step 6: Run the tests**

Run: `uv run pytest tests/test_server.py tests/test_history.py -v`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add app/web/api.py tests/test_server.py
git commit -m "feat: record generations to the gallery and expose /api/history"
```

---

### Task 4: Heartbeat and launcher

**Files:**
- Modify: `app/web/api.py`
- Create: `app/web/launcher.py`
- Test: `tests/test_launcher.py`

**Interfaces:**
- Consumes: `app.web.api.app`.
- Produces:
  - `app.web.api.Heartbeat` with `beat()`, `armed() -> bool`, `expired() -> bool`; constructor `Heartbeat(timeout: float = 30.0, clock=time.monotonic)`
  - `app.web.api.HEARTBEAT` — module-level instance
  - `app.web.api.ALIVE_MARKER = "homelab-icon-generator"`
  - `app.web.launcher.find_free_port(preferred: int, attempts: int = 20) -> int`
  - `app.web.launcher.probe_existing(port: int, timeout: float = 0.5) -> bool`
  - `app.web.launcher.run() -> int`

- [ ] **Step 1: Add the heartbeat to `app/web/api.py`**

The clock is injected so tests can advance time without sleeping. `armed()` is what prevents a slow browser from being mistaken for a closed tab.

```python
ALIVE_MARKER = "homelab-icon-generator"


class Heartbeat:
    """Tracks liveness pings from the browser tab.

    Stays disarmed until the first ping, so a server whose browser never
    connected will not shut itself down.
    """

    def __init__(self, timeout: float = 30.0, clock=time.monotonic) -> None:
        self._timeout = timeout
        self._clock = clock
        self._last: float | None = None
        self._lock = threading.Lock()

    def beat(self) -> None:
        with self._lock:
            self._last = self._clock()

    def armed(self) -> bool:
        with self._lock:
            return self._last is not None

    def expired(self) -> bool:
        with self._lock:
            if self._last is None:
                return False
            return (self._clock() - self._last) > self._timeout


HEARTBEAT = Heartbeat()


@app.get("/api/alive")
def alive_probe() -> dict:
    """Identifies this process so the launcher never adopts a foreign server."""
    return {"service": ALIVE_MARKER}


@app.post("/api/alive")
def alive_beat() -> dict:
    HEARTBEAT.beat()
    return {"service": ALIVE_MARKER}
```

- [ ] **Step 2: Write `app/web/launcher.py`**

```python
"""On-demand launcher: pick a port, start uvicorn, open a browser, exit when idle.

Knows about process lifecycle only. All HTTP behaviour lives in app.web.api.
"""

from __future__ import annotations

import json
import os
import socket
import threading
import time
import urllib.error
import urllib.request
import webbrowser

import uvicorn

from app.web import api

DEFAULT_PORT = 5000
HOST = "127.0.0.1"
WATCHDOG_INTERVAL = 2.0


def find_free_port(preferred: int, attempts: int = 20) -> int:
    """Return the first bindable port at or above `preferred`."""
    for offset in range(attempts):
        candidate = preferred + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((HOST, candidate))
                return candidate
            except OSError:
                continue
    raise RuntimeError(
        f"no free port in {preferred}-{preferred + attempts - 1} on {HOST}"
    )


def probe_existing(port: int, timeout: float = 0.5) -> bool:
    """True only if OUR server is already answering on this port."""
    url = f"http://{HOST}:{port}/api/alive"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return False
    return body.get("service") == api.ALIVE_MARKER


def _watch(server: uvicorn.Server) -> None:
    """Shut uvicorn down once the browser stops checking in."""
    while not server.should_exit:
        time.sleep(WATCHDOG_INTERVAL)
        if api.HEARTBEAT.expired():
            server.should_exit = True
            return


def run() -> int:
    preferred = int(os.environ.get("PORT", DEFAULT_PORT))

    if probe_existing(preferred):
        url = f"http://{HOST}:{preferred}/"
        print(f"Homelab Icon Generator already running — opening {url}")
        webbrowser.open(url)
        return 0

    port = find_free_port(preferred)
    api.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    url = f"http://{HOST}:{port}/"

    config = uvicorn.Config(api.app, host=HOST, port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    while not server.started and thread.is_alive():
        time.sleep(0.05)
    if not thread.is_alive():
        print("Server failed to start")
        return 1

    print(f"Homelab Icon Generator running at {url}")
    try:
        webbrowser.open(url)
    except Exception:
        print(f"Could not open a browser automatically — visit {url}")

    watchdog = threading.Thread(target=_watch, args=(server,), daemon=True)
    watchdog.start()

    try:
        while thread.is_alive():
            thread.join(timeout=0.5)
    except KeyboardInterrupt:
        server.should_exit = True
        thread.join(timeout=5)
    return 0
```

- [ ] **Step 3: Write `tests/test_launcher.py`**

No real sleeping anywhere — the heartbeat clock is injected.

```python
"""Launcher: port selection, instance probing, and idle shutdown."""

from __future__ import annotations

import socket

import pytest
from fastapi.testclient import TestClient

from app.web import api, launcher


def test_find_free_port_returns_preferred_when_available() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((launcher.HOST, 0))
        free = probe.getsockname()[1]

    assert launcher.find_free_port(free) == free


def test_find_free_port_skips_a_bound_port() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as held:
        held.bind((launcher.HOST, 0))
        held.listen(1)
        taken = held.getsockname()[1]

        assert launcher.find_free_port(taken) > taken


def test_probe_rejects_a_port_nothing_is_listening_on() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((launcher.HOST, 0))
        closed = probe.getsockname()[1]

    assert launcher.probe_existing(closed, timeout=0.2) is False


def test_probe_rejects_a_foreign_service(monkeypatch) -> None:
    monkeypatch.setattr(
        launcher.urllib.request,
        "urlopen",
        lambda *a, **k: (_ for _ in ()).throw(OSError("connection refused")),
    )

    assert launcher.probe_existing(5000, timeout=0.2) is False


def test_alive_probe_identifies_this_service() -> None:
    with TestClient(api.app) as client:
        assert client.get("/api/alive").json()["service"] == api.ALIVE_MARKER


def test_heartbeat_stays_disarmed_until_the_first_ping() -> None:
    clock = iter([0.0, 100.0, 200.0])
    beat = api.Heartbeat(timeout=30.0, clock=lambda: next(clock))

    assert beat.armed() is False
    assert beat.expired() is False, "a server with no browser must not self-terminate"


def test_heartbeat_expires_after_silence() -> None:
    now = [0.0]
    beat = api.Heartbeat(timeout=30.0, clock=lambda: now[0])
    beat.beat()

    assert beat.armed() is True
    now[0] = 29.0
    assert beat.expired() is False
    now[0] = 31.0
    assert beat.expired() is True


def test_heartbeat_resets_on_each_ping() -> None:
    now = [0.0]
    beat = api.Heartbeat(timeout=30.0, clock=lambda: now[0])
    beat.beat()
    now[0] = 29.0
    beat.beat()
    now[0] = 50.0

    assert beat.expired() is False
```

- [ ] **Step 4: Run the launcher tests**

Run: `uv run pytest tests/test_launcher.py -v`
Expected: all 8 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/web/api.py app/web/launcher.py tests/test_launcher.py
git commit -m "feat: add on-demand launcher with heartbeat shutdown"
```

---

### Task 5: Bare-argv dispatch and packaging

**Files:**
- Modify: `app/main.py:136-144`, `pyproject.toml`
- Test: `tests/test_cli.py` (append)

**Interfaces:**
- Consumes: `app.web.launcher.run`.
- Produces: `homelab-icons` bare → Web UI; `homelab-icons <flags>` → existing CLI.

- [ ] **Step 1: Add dispatch to `app/main.py`**

The `app.web.launcher` import sits **inside** the branch so CLI and batch runs never pay the FastAPI import cost. Replace `main()` (lines 136-144) with:

```python
def main() -> None:
    # No arguments: this is a web-first tool, so open the UI.
    if len(sys.argv) == 1:
        from app.web.launcher import run

        raise SystemExit(run())

    parser, args = parse_args()

    if args.batch:
        run_batch(args.batch, args.output_dir, args.icon_dir)
    elif args.name and args.category:
        run_single(args)
    else:
        parser.error("Provide --name and --category, or --batch <file>")
```

- [ ] **Step 2: Document it in `--help`**

Change the `ArgumentParser` construction at `app/main.py:14-16` to:

```python
    parser = argparse.ArgumentParser(
        description="Generate homelab icons for devices and services.",
        epilog="Run with no arguments to open the web UI.",
    )
```

- [ ] **Step 3: Test the dispatch**

Append to `tests/test_cli.py`:

```python
def test_bare_invocation_opens_the_web_ui(monkeypatch) -> None:
    import app.main

    calls = []
    monkeypatch.setattr(sys, "argv", ["homelab-icons"])
    monkeypatch.setattr(
        "app.web.launcher.run", lambda: calls.append("launched") or 0
    )

    with pytest.raises(SystemExit) as excinfo:
        app.main.main()

    assert calls == ["launched"]
    assert excinfo.value.code == 0


def test_flagged_invocation_still_runs_the_cli(monkeypatch, tmp_path) -> None:
    import app.main

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "homelab-icons",
            "--name", "Nextcloud",
            "--category", "cloud_service",
            "--format", "svg",
            "--output-dir", str(tmp_path),
        ],
    )
    monkeypatch.setattr(
        "app.web.launcher.run",
        lambda: pytest.fail("CLI invocation must not start the web server"),
    )

    app.main.main()

    assert list(tmp_path.rglob("*.svg"))
```

Ensure `tests/test_cli.py` imports `sys` and `pytest` at the top; add them if absent.

- [ ] **Step 4: Run the CLI tests**

Run: `uv run pytest tests/test_cli.py -v`
Expected: all PASS, including the two new tests.

- [ ] **Step 5: Confirm static assets ship in the wheel**

The wheel must contain the UI, or an installed copy has no web interface. Do not assume hatchling picks up non-Python files.

Run:

```bash
uv build
uv run python -c "import zipfile,glob; w=sorted(glob.glob('dist/*.whl'))[-1]; names=zipfile.ZipFile(w).namelist(); print(w); print([n for n in names if 'web/static' in n])"
```

Expected: the list includes `app/web/static/index.html`, `app.css`, `app.js`.

If the list is **empty**, add this to `pyproject.toml` and rebuild:

```toml
[tool.hatch.build.targets.wheel.force-include]
"app/web/static" = "app/web/static"
```

- [ ] **Step 6: Commit**

```bash
git add app/main.py pyproject.toml tests/test_cli.py
git commit -m "feat: launch the web UI when homelab-icons is run with no arguments"
```

---

### Task 6: Server-backed artifact gallery

Upgrades the existing `06 — RECENT ARTIFACTS` strip from session memory to persistent history, and makes clicking a tile restore the settings that produced it.

**Files:**
- Create: `app/web/static/gallery.js`
- Modify: `app/web/static/index.html:154-156`, `app/web/static/index.html` (script tags), `app/web/static/app.js:16` (drop `recent`), `app/web/static/app.js:433-443` (call `Gallery.refresh()`), `app/web/static/app.js:448-509` (remove `_makeSlot`/`renderRecent`)
- Modify: `app/web/static/app.css` (append gallery-specific rules)

**Interfaces:**
- Consumes: `GET /api/history`, `POST /api/alive`; globals from `app.js`: `state`, `$`, `el`, `log`, `escapeHtml`, `setCategory`, `setStyle`, `setTheme`, `setFormat`, `setIcon`, `updateSliderFill`, `syncCli`.
- Produces: `window.Gallery = { refresh, loadMore, restore }`.

- [ ] **Step 1: Remove the in-memory strip from `app.js`**

1. Delete `recent: [],` from the `state` object (line 16).
2. Replace the `// recent strip` block in `onBuildSuccess` (lines 433-443) with:

```js
  // gallery (server-backed)
  Gallery.refresh();
```

3. Delete `_makeSlot` and `renderRecent` entirely (lines 448-509).

- [ ] **Step 2: Write `app/web/static/gallery.js`**

```js
/* ============ ARTIFACT GALLERY ============ */
/* Server-backed history. Clicking a tile restores the settings that built it. */

const GALLERY_PAGE = 50;
const HEARTBEAT_MS = 5000;

let galleryLoaded = 0;
let galleryExhausted = false;

function _galleryTile(record, num) {
  const slot = el("div", {
    class: "slot filled",
    title: `${record.name} — ${record.style}/${record.theme}/${record.size}`,
    role: "button",
    tabindex: "0",
  });
  const restore = () => Gallery.restore(record);
  slot.addEventListener("click", restore);
  slot.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      restore();
    }
  });
  slot.append(el("span", { class: "num" }, String(num).padStart(2, "0")));
  if (record.thumb) {
    slot.append(el("img", { src: record.thumb, alt: record.name, loading: "lazy" }));
  }
  slot.append(el("span", { class: "lbl" }, record.name));
  return slot;
}

function _renderGallery(items, { append }) {
  const strip = $("strip");

  if (!append) {
    strip.innerHTML = "";
    galleryLoaded = 0;
  }
  strip.querySelector(".empty")?.remove();
  strip.querySelector(".gallery-more")?.remove();
  strip.querySelectorAll(".slot:not(.filled)").forEach((s) => s.remove());

  if (items.length === 0 && galleryLoaded === 0) {
    strip.append(el("div", { class: "empty" }, "NO RECENT ARTIFACTS / GENERATE TO POPULATE"));
    return;
  }

  items.forEach((record) => {
    galleryLoaded += 1;
    strip.append(_galleryTile(record, galleryLoaded));
  });

  // Keep a minimum of 6 cells so the strip holds its shape.
  for (let i = 0; i < Math.max(0, 6 - galleryLoaded); i++) {
    strip.append(el("div", { class: "slot" }));
  }

  if (!galleryExhausted) {
    strip.append(
      el("button", {
        type: "button",
        class: "gallery-more",
        onclick: () => Gallery.loadMore(),
      }, "LOAD MORE"),
    );
  }
}

const Gallery = {
  async refresh() {
    galleryExhausted = false;
    try {
      const response = await fetch(`/api/history?limit=${GALLERY_PAGE}&offset=0`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "history load failed");
      if (data.items.length < GALLERY_PAGE) galleryExhausted = true;
      _renderGallery(data.items, { append: false });
    } catch (error) {
      log(`[ERR] gallery unavailable: ${escapeHtml(error.message)}`, "err");
    }
  },

  async loadMore() {
    try {
      const response = await fetch(
        `/api/history?limit=${GALLERY_PAGE}&offset=${galleryLoaded}`,
      );
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "history load failed");
      if (data.items.length < GALLERY_PAGE) galleryExhausted = true;
      _renderGallery(data.items, { append: true });
    } catch (error) {
      log(`[ERR] gallery unavailable: ${escapeHtml(error.message)}`, "err");
    }
  },

  /* Fills the form. Deliberately does NOT generate — the user reviews first. */
  restore(record) {
    $("name").value = record.name;
    state.name = record.name;
    setCategory(record.category);
    setStyle(record.style);
    setTheme(record.theme);
    setFormat(record.format);

    $("size").value = record.size;
    state.size = record.size;
    $("sizeOut").textContent = String(record.size);
    updateSliderFill();

    $("transparent").checked = record.transparent_bg;
    state.transparent = record.transparent_bg;

    setIcon(record.icon, record.icon_title, record.icon_source);

    if (record.thumb) {
      const artifact = $("artifact");
      artifact.innerHTML = "";
      artifact.append(el("img", { src: record.thumb, alt: record.name }));
      $("viewport").classList.add("has-artifact");
      $("artifactName").textContent = record.name.toUpperCase();
    }

    syncCli();
    log(`restored ${escapeHtml(record.name)} — review and generate`, "amber");
  },
};

window.Gallery = Gallery;

/* Liveness: the server exits ~30s after these stop arriving. */
function heartbeat() {
  fetch("/api/alive", { method: "POST", keepalive: true }).catch(() => {});
}
heartbeat();
setInterval(heartbeat, HEARTBEAT_MS);

Gallery.refresh();
```

- [ ] **Step 3: Load the module**

In `index.html`, replace the single script tag with both, in order. `defer` guarantees `app.js` runs first, so `gallery.js` can use its globals:

```html
<script src="/static/app.js" defer></script>
<script src="/static/gallery.js" defer></script>
```

- [ ] **Step 4: Relabel the strip**

In `index.html:154`, change the panel label so it reflects persistence:

```html
      <div class="panel strip" data-label="06 — ARTIFACT GALLERY" id="strip">
```

- [ ] **Step 5: Style the new controls**

Append to `app.css`. Match the surrounding terminal aesthetic — reuse existing custom properties rather than introducing new colours:

```css
/* ---- gallery ---- */
.strip .slot.filled { cursor: pointer; }
.strip .slot.filled:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: 2px;
}
.gallery-more {
  align-self: center;
  flex: 0 0 auto;
  margin-left: .75rem;
  padding: .4rem .8rem;
  font: inherit;
  font-size: .7rem;
  letter-spacing: .08em;
  color: inherit;
  background: transparent;
  border: 1px solid currentColor;
  cursor: pointer;
}
.gallery-more:hover { filter: brightness(1.4); }
```

- [ ] **Step 6: Verify the page still asserts clean**

Run: `uv run pytest tests/test_server.py::test_page_has_accessible_override_controls_and_no_external_fonts -v`
Expected: PASS.

- [ ] **Step 7: Manual browser check**

Run: `uv run homelab-icons`

Confirm, in order:
1. A browser opens automatically at `http://127.0.0.1:5000/`.
2. Generating an icon adds a tile to the gallery strip.
3. Reloading the page keeps the tile — history is persistent.
4. Clicking a tile refills name, category, style, theme, size, format, transparency, and icon, and does **not** auto-generate.
5. Generating the same icon twice does not create a second tile.
6. The browser console is clean.
7. Check the layout at a mobile width (DevTools, ~390px).
8. Close the tab; within ~30 seconds the process exits on its own.

- [ ] **Step 8: Commit**

```bash
git add app/web/static
git commit -m "feat: back the artifact strip with persistent gallery history"
```

---

### Task 7: Desktop shortcut, docs, and the full gate

**Files:**
- Create: `scripts/install_shortcut.py`
- Modify: `README.md`, `CLAUDE.md`

**Interfaces:**
- Consumes: the `homelab-icons` console script.
- Produces: `scripts/install_shortcut.py` with `main() -> int`.

- [ ] **Step 1: Write `scripts/install_shortcut.py`**

Targets `pythonw.exe` so no console window appears. Uses WScript.Shell through COM, which is present on stock Windows — no new dependency.

```python
"""Create Windows shortcuts that launch the Homelab Icon Generator web UI.

Maintainer script. Run once after `uv sync`:

    uv run python -m scripts.install_shortcut
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SHORTCUT_NAME = "Homelab Icon Generator.lnk"


def _launch_target() -> tuple[Path, Path]:
    """Return (pythonw.exe, the homelab-icons script) for the active venv."""
    scripts_dir = Path(sys.executable).parent
    pythonw = scripts_dir / "pythonw.exe"
    if not pythonw.is_file():
        pythonw = Path(sys.executable)
    entry = scripts_dir / "homelab-icons.exe"
    if not entry.is_file():
        raise SystemExit(
            "homelab-icons is not installed in this environment — run `uv sync` first"
        )
    return pythonw, entry


def _targets() -> list[Path]:
    home = Path.home()
    desktop = home / "Desktop"
    start_menu = (
        Path(os.environ["APPDATA"])
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
    )
    return [directory for directory in (desktop, start_menu) if directory.is_dir()]


def main() -> int:
    if sys.platform != "win32":
        print("This script creates Windows shortcuts; nothing to do here.")
        return 0

    try:
        import win32com.client  # type: ignore
    except ImportError:
        _, entry = _launch_target()
        print(
            "pywin32 is not installed, so the shortcut cannot be created "
            "automatically.\nCreate one by hand pointing at:\n"
            f"  {entry}\n"
            "Install pywin32 with `uv add --dev pywin32` to automate this."
        )
        return 1

    _, entry = _launch_target()
    shell = win32com.client.Dispatch("WScript.Shell")
    created = []
    for directory in _targets():
        path = directory / SHORTCUT_NAME
        shortcut = shell.CreateShortCut(str(path))
        shortcut.TargetPath = str(entry)
        shortcut.WorkingDirectory = str(Path.cwd())
        shortcut.Description = "Open the Homelab Icon Generator web UI"
        shortcut.WindowStyle = 7  # minimised
        shortcut.save()
        created.append(path)

    for path in created:
        print(f"Created {path}")
    return 0 if created else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Update `README.md`**

Replace the web section (around line 145-151):

````markdown
### Web UI

```bash
uv run homelab-icons
```

Running with no arguments starts the local server and opens
<http://127.0.0.1:5000> in your browser. Closing the tab shuts the server down
after about 30 seconds. Re-running while it is already up just reopens the tab.

For a desktop icon:

```bash
uv run python -m scripts.install_shortcut
```

The UI loads all option lists from the backend, shows automatic
detection/fallback state, provides searchable manual overrides, and keeps a
persistent gallery of your last 500 generations. Clicking a gallery tile
restores the settings that produced it.
````

Also update the CLI examples: `uv run python main.py` still works, but document `uv run homelab-icons --name ...` as the primary form. Remove any remaining reference to `uv run python server.py`.

- [ ] **Step 3: Update `CLAUDE.md`**

Three edits:

1. In the UV workflow block, replace `uv run python server.py` with `uv run homelab-icons` and add a comment that the bare form opens the web UI.
2. Replace the `server.py` paragraph with:

```markdown
`app/web/api.py` reads `PORT` (default 5000) and
`GENERATE_RATE_LIMIT`/`GENERATE_RATE_WINDOW` (default 20 requests/60s) for the
`/api/generate` rate limiter. `FLASK_DEBUG` is retired.
```

3. Replace the `server.py` and `app/web/static/` entries in "Module boundaries" with:

```markdown
- `app/web/api.py`: FastAPI routes — metadata, search, generation, history, liveness
- `app/web/schemas.py`: Pydantic edge models; shape validation only, never domain rules
- `app/web/history.py`: SQLite gallery store (500-row cap, disk reconciliation)
- `app/web/launcher.py`: port selection, single-instance probe, uvicorn, heartbeat shutdown
- `app/web/static/`: the static UI itself (`index.html`, `app.js`, `gallery.js`, `app.css`)
```

- [ ] **Step 4: Run the full gate**

```bash
uv run pytest -q
uv build
git diff --check
```

Expected: all tests pass, the wheel builds, no whitespace errors.

- [ ] **Step 5: Re-confirm the wheel carries the UI**

```bash
uv run python -c "import zipfile,glob; w=sorted(glob.glob('dist/*.whl'))[-1]; names=zipfile.ZipFile(w).namelist(); print([n for n in names if 'web/static' in n])"
```

Expected: `index.html`, `app.css`, `app.js`, `gallery.js` all listed.

- [ ] **Step 6: Visual regression**

```bash
uv run python -m scripts.generate_contact_sheet \
  --icon-dir tests/fixtures/custom-icons \
  --output output/contact-sheet.png
```

Expected: the sheet renders as before. This work does not touch geometry, so any change here is a regression.

- [ ] **Step 7: Commit**

```bash
git add scripts/install_shortcut.py README.md CLAUDE.md
git commit -m "docs: document the web-first workflow and add a shortcut installer"
```

---

## Verification Summary

| Check | Command |
|---|---|
| Full suite | `uv run pytest -q` |
| Package builds | `uv build` |
| Whitespace | `git diff --check` |
| UI ships in wheel | zipfile check in Task 5 Step 5 |
| Visual regression | `scripts/generate_contact_sheet.py` |
| End-to-end | Task 6 Step 7 manual checklist |
