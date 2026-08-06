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
STARTUP_TIMEOUT = 30.0


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
    return isinstance(body, dict) and body.get("service") == api.ALIVE_MARKER


def find_existing(preferred: int, attempts: int = 20, timeout: float = 0.5) -> int | None:
    """Scan the same candidate range `find_free_port` would try, looking for
    OUR server. A relaunch must find an instance that fell back to a
    non-preferred port, not just probe the preferred one and start a
    silent second instance.
    """
    for offset in range(attempts):
        candidate = preferred + offset
        if probe_existing(candidate, timeout=timeout):
            return candidate
    return None


def _watch(server: uvicorn.Server) -> None:
    """Shut uvicorn down once the browser stops checking in."""
    while not server.should_exit:
        time.sleep(WATCHDOG_INTERVAL)
        if api.HEARTBEAT.expired():
            server.should_exit = True
            return


def run() -> int:
    preferred = int(os.environ.get("PORT", DEFAULT_PORT))

    existing_port = find_existing(preferred)
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
