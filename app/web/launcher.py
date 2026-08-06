"""On-demand launcher: pick a port, start uvicorn, open a browser, exit when idle.

Knows about process lifecycle only. All HTTP behaviour lives in app.web.api.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

import uvicorn

from app.web import api

DEFAULT_PORT = 5000
HOST = "127.0.0.1"
WATCHDOG_INTERVAL = 2.0
STARTUP_TIMEOUT = 30.0
INSTANCE_FILENAME = ".instance"

_log = logging.getLogger(__name__)


def _can_bind(port: int) -> bool:
    """True if `port` is currently free to bind on HOST.

    Plain bind, deliberately no SO_REUSEADDR: on Windows that option permits
    binding a port that's already bound by another socket, which would make
    this always report "free" and silently break `find_free_port`.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((HOST, port))
            return True
        except OSError:
            return False


def find_free_port(preferred: int, attempts: int = 20) -> int:
    """Return the first bindable port at or above `preferred`."""
    for offset in range(attempts):
        candidate = preferred + offset
        if _can_bind(candidate):
            return candidate
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
    return isinstance(body, dict) and body.get("service") == api.ALIVE_MARKER


def _instance_file() -> Path:
    """Path to the instance marker, scoped to OUTPUT_DIR deliberately: the
    thing being protected is two servers sharing one gallery database, and
    the gallery lives in OUTPUT_DIR. Two launches from different working
    directories have different output dirs and different galleries, so they
    legitimately run side by side — that's correct, not a bug to prevent.
    """
    return api.OUTPUT_DIR / INSTANCE_FILENAME


def write_instance_file(port: int) -> None:
    """Record the bound port so a relaunch can find this instance directly
    instead of guessing where it is. Call only after startup is confirmed —
    a file naming a port nothing is listening on is worse than no file.

    Best-effort, like the gallery-record failure in app.web.api: the file is
    a relaunch optimization, not the product, and by this point the server
    is already up and serving. Losing the write just means the next relaunch
    finds no file and starts a fresh instance — the pre-existing behavior —
    which is obviously better than an unhandled exception killing an
    already-running server with no console to show the traceback in.
    """
    try:
        _instance_file().write_text(str(port), encoding="utf-8")
    except OSError:
        _log.exception("failed to write instance file")


def remove_instance_file() -> None:
    """Clean up on graceful shutdown. Best-effort: a leftover file from a
    crash is already handled safely by find_existing's marker check, so a
    failure to remove it here must not be fatal.
    """
    try:
        _instance_file().unlink(missing_ok=True)
    except OSError:
        pass


def find_existing(timeout: float = 0.5) -> int | None:
    """Return the port of an already-running instance for this OUTPUT_DIR,
    if any.

    Reads the port a previous successful startup recorded and probes
    exactly that one port — one file read, one HTTP request, always
    correct, unlike scanning a candidate range (which is either slow if it
    HTTP-probes ports nothing is listening on, or unsound if it tries to
    infer "nothing of ours is running" from bind() results alone: a port
    freed by an unrelated process after our instance started elsewhere in
    the range would be misread as proof no instance exists).

    The file's contents are never trusted on their own — missing, corrupt,
    or naming a port that's now silent or answering a foreign service all
    resolve to None, and the caller starts a fresh instance.
    """
    try:
        port = int(_instance_file().read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None
    return port if probe_existing(port, timeout=timeout) else None


def _watch(server: uvicorn.Server) -> None:
    """Shut uvicorn down once the browser stops checking in."""
    while not server.should_exit:
        time.sleep(WATCHDOG_INTERVAL)
        if api.HEARTBEAT.expired():
            server.should_exit = True
            return


def run() -> int:
    preferred = int(os.environ.get("PORT", DEFAULT_PORT))

    existing_port = find_existing()
    if existing_port is not None:
        url = f"http://{HOST}:{existing_port}/"
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

    deadline = time.monotonic() + STARTUP_TIMEOUT
    while not server.started and thread.is_alive():
        if time.monotonic() > deadline:
            server.should_exit = True
            print(f"Server did not start within {STARTUP_TIMEOUT:.0f}s on port {port}")
            return 1
        time.sleep(0.05)
    if not thread.is_alive():
        print("Server failed to start")
        return 1

    write_instance_file(port)

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
    finally:
        remove_instance_file()
    return 0
