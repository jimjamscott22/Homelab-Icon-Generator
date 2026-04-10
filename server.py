"""Flask web interface for the Homelab Icon Generator.

Run with:
    python server.py

Then open http://127.0.0.1:5000 in a browser.
"""

from __future__ import annotations

import os
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

    files = {fmt: f"/output/{Path(p).name}" for fmt, p in paths.items()}
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


@app.route("/output/<path:filename>")
def serve_output(filename: str):
    return send_from_directory(OUTPUT_DIR, filename)


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(exist_ok=True)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=True)
