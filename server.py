"""Flask web interface for the Homelab Icon Generator.

Run with:
    python server.py

Then open http://127.0.0.1:5000 in a browser.
"""

from __future__ import annotations

import collections
import os
import threading
import time
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from app.generator.renderer import generate_icon
from app.models.icon_request import IconRequest
from app.utils.validation import (
    VALID_CATEGORIES,
    VALID_FORMATS,
    VALID_STYLES,
    VALID_THEMES,
)

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "app" / "web" / "static"
OUTPUT_DIR = ROOT / "output"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")

# Sliding-window rate limiter for /api/generate (no external dependency needed).
# Protects against memory pressure on low-power hosts (Pi) if the server is
# ever bound to a non-loopback address.
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


@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/api/options")
def options():
    return jsonify(
        {
            "categories": sorted(VALID_CATEGORIES),
            "styles": sorted(VALID_STYLES),
            "themes": sorted(VALID_THEMES),
            "formats": sorted(VALID_FORMATS),
        }
    )


@app.route("/api/generate", methods=["POST"])
def generate():
    if not _allow_request():
        return jsonify({"error": "rate limit exceeded — try again shortly"}), 429
    data = request.get_json(silent=True) or {}
    try:
        req = IconRequest(
            name=(data.get("name") or "").strip(),
            category=data.get("category", ""),
            style=data.get("style", "minimal"),
            theme=data.get("theme", "blue"),
            size=int(data.get("size", 256)),
            format=data.get("format", "both"),
            transparent_bg=bool(data.get("transparent_bg", False)),
            output_dir=str(OUTPUT_DIR),
        )
        started = time.perf_counter()
        paths = generate_icon(req)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"generation failed: {exc}"}), 500

    files = {
        fmt: f"/output/{Path(p).resolve().relative_to(OUTPUT_DIR.resolve()).as_posix()}"
        for fmt, p in paths.items()
    }
    return jsonify(
        {
            "files": files,
            "elapsed_ms": elapsed_ms,
            "name": req.name,
            "category": req.category,
            "style": req.style,
            "theme": req.theme,
            "size": req.size,
            "format": req.format,
            "transparent_bg": req.transparent_bg,
        }
    )


_OUTPUT_FORMATS = frozenset({"png", "svg", "ico"})
_OUTPUT_EXTS = frozenset({".png", ".svg", ".ico"})


@app.route("/output/<fmt>/<category>/<filename>")
def serve_output(fmt: str, category: str, filename: str):
    if fmt not in _OUTPUT_FORMATS or category not in VALID_CATEGORIES:
        return "", 404
    if Path(filename).suffix not in _OUTPUT_EXTS:
        return "", 404
    resp = send_from_directory(OUTPUT_DIR / fmt / category, filename)
    resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return resp


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(exist_ok=True)
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="127.0.0.1", port=port, debug=debug)
