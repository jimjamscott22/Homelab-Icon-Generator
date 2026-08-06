"""FastAPI web interface for the Homelab Icon Generator."""

from __future__ import annotations

import collections
import logging
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
from app.web.history import GalleryStore
from app.web.schemas import GenerateRequest

STATIC_DIR = Path(__file__).resolve().parent / "static"
# Resolved from the working directory (like the CLI's `--output-dir` default),
# not the package install location — an installed wheel must not write into
# site-packages. Override with HOMELAB_OUTPUT_DIR.
OUTPUT_DIR = Path(os.environ.get("HOMELAB_OUTPUT_DIR", Path.cwd() / "output"))

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


@app.exception_handler(RequestValidationError)
def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Match Flask: malformed input is a 400 with an {"error": ...} body.

    FastAPI defaults to 422, but the previous server returned 400 for a bad
    `size` value, a bad `limit`, and an unparseable body alike. Status codes
    stay byte-identical; only some message text differs.
    """
    return JSONResponse({"error": "malformed request body"}, status_code=400)


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
def search_icons(q: str = "", limit: str = "8"):
    query = q.strip()
    # Parsed by hand so a bad value keeps Flask's exact 400 message.
    try:
        count = int(limit)
    except ValueError:
        return JSONResponse({"error": "limit must be an integer"}, status_code=400)
    count = max(1, min(count, 20))
    if not query:
        return {"exact": None, "items": [], "query": query}

    resolver = get_default_resolver()
    exact = resolver.exact(query)
    return {
        "exact": _icon_payload(exact) if exact is not None else None,
        "items": [_icon_payload(icon) for icon in resolver.suggest(query, limit=count)],
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
    response_payload = {
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
            gallery.record(response_payload)
        except Exception:
            # The icon is the product; history is a convenience.
            _log.exception("failed to record gallery entry")
    return response_payload


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


@app.get("/api/history")
def history(limit: int = 50, offset: int = 0):
    gallery = get_gallery()
    if gallery is None:
        return {"items": []}
    return {"items": gallery.recent(limit=limit, offset=offset)}


ALIVE_MARKER = "homelab-icon-generator"


class Heartbeat:
    """Tracks liveness pings from the browser tab.

    Stays disarmed until the first ping, so a server whose browser never
    connected will not shut itself down.

    The default timeout is deliberately well above the 5s ping interval:
    browsers throttle timers in backgrounded tabs, and Chromium's intensive
    throttling can clamp a hidden tab's setInterval to firing at most once a
    minute. A shorter timeout would kill the server out from under a user
    who merely switched tabs, mistaking "backgrounded" for "closed".
    """

    def __init__(self, timeout: float = 90.0, clock=time.monotonic) -> None:
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
