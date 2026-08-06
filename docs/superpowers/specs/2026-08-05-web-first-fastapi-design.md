# Web-first restructure: FastAPI server, desktop launcher, generation gallery

Date: 2026-08-05
Status: Approved for planning

## Problem

The Web UI is the intended primary interface, but the project is structured as a
CLI that happens to ship a web server:

- `server.py` sits at the repository root, outside the `app` package.
- `pyproject.toml` packages only `app`, so `uv build` produces a **CLI-only
  wheel** — the Web UI is unreachable from an installed copy.
- The single console script, `homelab-icons`, runs the CLI.
- Launching the UI requires a git checkout and `uv run python server.py`.

There is therefore nothing an icon can point at. A desktop shortcut is a
symptom; the packaging boundary is the cause.

Secondary goals: move the API to FastAPI/uvicorn, and add a gallery of past
generations.

## Decisions

| Decision | Choice | Reason |
|---|---|---|
| Web framework | FastAPI + uvicorn | uvicorn is production-capable, so one command serves both the local launcher and any future always-on use. Async is irrelevant here — generation is CPU-bound in resvg. |
| Frontend | Keep vanilla JS | A gallery is list rendering. React would add npm and a build step to a wheel, in a project that bars Node at runtime, for no structural gain. Revisit only if a batch workspace is added. |
| Entrypoint | `homelab-icons` bare → Web UI; with flags → CLI | Makes the web path primary without breaking a single documented CLI invocation. |
| Deployment | Local only, on demand | Launch by icon, exit when finished. No service management. |
| Shutdown | Browser heartbeat | Close the tab, server exits. No stray process, no console window. |
| History storage | SQLite (stdlib `sqlite3`) | No new dependency; clean pagination; tolerates concurrent tabs. |
| Retention | Newest 500 rows | Predictable, no maintenance. |
| Orphans | All files missing → row dropped | Gallery never shows a dead thumbnail. |
| Duplicates | Upsert on the settings tuple | Regenerating identical settings overwrites the same file; it should bubble to the top, not duplicate. |

Explicitly rejected: PyInstaller bundling (fights `resvg-py`'s native binary and
package-data catalog for no gain while Python is present); a React frontend; a
system-tray launcher (`pystray` dependency, Windows-specific code); shared
multi-user history.

## Architecture

```text
app/
  main.py                  CLI arg parsing; gains bare-invocation dispatch
  web/
    __init__.py
    api.py                 FastAPI app, routers, rate limiter, static mount
    schemas.py             Pydantic models — edge layer only
    history.py             SQLite gallery store
    launcher.py            single-instance probe, port pick, browser, uvicorn
    static/                index.html, app.css, app.js, gallery.js
scripts/
  install_shortcut.py      maintainer script; generates the Windows .lnk
server.py                  DELETED
```

Each unit has one job. `history.py` knows SQLite and nothing about HTTP.
`launcher.py` knows process lifecycle and nothing about icons. `api.py` knows
HTTP and delegates all domain work to the existing `app.generator` /
`app.icons` modules, whose boundaries are unchanged.

### Entrypoint dispatch

In `app/main.py`: empty `sys.argv[1:]` → `app.web.launcher.run()`; anything else
→ the existing `argparse` path, untouched. `--help` gains one line stating that
the bare form opens the Web UI.

The launcher import **must** sit inside the bare-argv branch so CLI and batch
runs never pay FastAPI import cost.

### Launcher sequence

1. `GET http://127.0.0.1:{port}/api/alive`. If it responds with our own marker,
   an instance is already running: open the browser at it and exit 0.
   Re-clicking the icon never errors or double-starts.
2. Otherwise bind: `PORT` env if set, else 5000, else the first free port above
   it. Always `127.0.0.1`.
3. Start uvicorn in a thread; once it accepts connections, `webbrowser.open()`
   the resolved URL.
4. Heartbeat watchdog: the page `POST`s `/api/alive` every 5s. A background
   thread checks last-seen; 30s of silence triggers graceful uvicorn shutdown.
   **The watchdog does not arm until the first heartbeat arrives**, so a slow
   browser start cannot kill the server before the user sees it.

### Windows shortcut

`scripts/install_shortcut.py` writes a `.lnk` to Desktop and Start Menu
targeting `pythonw.exe` running the console script in the current virtualenv, so
no console window appears. Maintainer script, consistent with existing
`scripts/` conventions.

### Packaging

- `homelab-icons` remains the only console script.
- `flask` leaves `dependencies`; `fastapi` and `uvicorn` enter.
- `httpx` joins the dev group for FastAPI's `TestClient`.
- `app/web/static/` must ship as package data — **verify** its presence inside
  the built wheel rather than assuming hatchling includes it.

## API surface

Existing routes port over with **byte-identical request and response payloads**,
so the current `app.js` keeps working across the framework swap.

| Route | Status | Purpose |
|---|---|---|
| `GET /` | unchanged | `index.html` |
| `GET /api/options` | unchanged | option lists |
| `GET /api/icons/search` | unchanged | icon search |
| `POST /api/generate` | unchanged payload | generates; now also records a history row |
| `GET /output/{fmt}/{category}/{file}` | unchanged | same allow-list validation |
| `GET /api/alive` | new | single-instance probe; returns a marker so a foreign service on :5000 is not adopted |
| `POST /api/alive` | new | heartbeat from the page |
| `GET /api/history?limit=50&before=<id>` | new | gallery feed, newest first |

There is no restore endpoint. Clicking a tile repopulates the form client-side
from data already present in the feed; generating is then the normal button.

## Gallery store

The current `/api/generate` response already carries every field history needs,
so no new data is computed.

```sql
CREATE TABLE generations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,          -- ISO-8601 UTC
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  style TEXT NOT NULL,
  theme TEXT NOT NULL,
  size INTEGER NOT NULL,
  format TEXT NOT NULL,
  transparent_bg INTEGER NOT NULL,
  icon TEXT NOT NULL,                -- requested: auto | generic | key
  icon_key TEXT NOT NULL,            -- resolved
  icon_title TEXT,
  icon_source TEXT,
  match_method TEXT,
  used_fallback INTEGER NOT NULL,
  files TEXT NOT NULL,               -- JSON {fmt: relpath}
  thumb_rel TEXT                     -- png, else svg, else ico
);
CREATE INDEX idx_generations_created_at ON generations(created_at DESC);
```

Location: `output/.gallery.db`, WAL mode, sibling to `png/` `svg/` `ico/`.
Clearing `output/` clears history with it, consistent with the mirror-disk rule.
Gitignored, and excluded from output listing.

**Identity tuple for upsert:** `(name, category, style, theme, size, format,
transparent_bg, icon)`. A matching row has `created_at` and `files` updated and
rises to the top rather than duplicating.

**Reconciliation is lazy, on read.** `GET /api/history` calls `exists()` on each
row's files. All missing → row deleted and omitted from the response. Some
missing → row kept, only surviving files returned. No watcher, no daemon.

**Pruning runs on insert:** keep the newest 500 rows, delete the remainder.
Files on disk are never touched. A pruned row's images simply leave the gallery
and remain in `output/`.

## Gallery UI

A new section in `index.html` driven by a new `gallery.js` module. `app.js` is
already 539 lines and must not absorb this.

- Loads 50 entries on page load and refreshes after each successful generate.
- "Load more" pages via `before=<id>`.
- Tile: thumbnail (`loading="lazy"`), name, style/theme badges.
- Click fills the form. It does **not** auto-generate — the user reviews, then
  presses Generate.

## Error handling

`schemas.py` Pydantic models validate **shape only** — field presence, types,
`size` as an integer. Every domain rule (the 24 categories, styles, themes,
formats, the ICO ≤256 constraint) stays in `IconRequest` and
`app/utils/validation.py`, which remain the single source of truth. The route
constructs an `IconRequest` and lets its `ValueError` surface. Two copies of
those rules is how they drift.

| Condition | Behavior |
|---|---|
| Domain validation | 400 `{"error": ...}` — unchanged shape |
| Malformed/missing JSON, or a bad `size`/`limit` value | 400 `{"error": ...}` via an exception handler. FastAPI defaults to 422, but Flask returned 400 for all of these, and the byte-identical constraint governs |
| Generation raises | 500 `{"error": "generation failed: ..."}` — unchanged |
| Rate limit | 429; same limiter and same `GENERATE_RATE_LIMIT` / `GENERATE_RATE_WINDOW` env vars |
| History write fails | Logged and swallowed. A broken gallery must never fail a generation — the icon is the product, history is a convenience |
| `output/.gallery.db` corrupt | Detected on open, moved aside to `.gallery.db.bad`, recreated empty |
| Preferred port held by a foreign service | Probe returns no marker → bind the next free port, open the browser there |
| `webbrowser.open()` fails | Server still runs; launcher prints the URL to stdout |
| Browser never sends a heartbeat | Watchdog stays disarmed; the server does not self-terminate |

## Testing

- `tests/test_server.py` rewrites onto FastAPI's `TestClient`. The six existing
  assertions carry over intact — they test payloads, not Flask.
- `tests/test_history.py` (new): insert/read round-trip; upsert bumps instead of
  duplicating; the 500-cap prunes rows while leaving files alone; rows with all
  files missing are dropped on read; rows with partial files are kept and return
  only surviving files.
- `tests/test_launcher.py` (new): port fallback when the preferred port is
  bound; the single-instance probe rejects a foreign service on :5000; the
  watchdog stays disarmed with no heartbeat and fires after silence. Use an
  injected clock — no real sleeping.
- CLI, renderer, resolver, composer, catalog and custom-icon tests are untouched
  by this work and must stay green.

## Cutover

- `server.py` is deleted, not left as a shim.
- README replaces `uv run python server.py` with `homelab-icons`, and documents
  `scripts/install_shortcut.py`.
- CLAUDE.md updates its "Module boundaries" list for `app/web/` and moves the
  server-configuration paragraph accordingly.

## Verification

The standard gate:

```bash
uv run pytest -q
uv build
git diff --check
```

Plus two checks the gate cannot perform:

1. Confirm `app/web/static/` is actually present inside the built wheel.
2. Double-click the shortcut end to end: launch → generate → gallery tile
   appears → click tile repopulates the form → close tab → process exits within
   ~30s.
