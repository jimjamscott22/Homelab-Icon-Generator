"""Launcher: port selection, instance probing, and idle shutdown."""

from __future__ import annotations

import socket

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


def test_probe_rejects_a_non_dict_json_body(monkeypatch) -> None:
    """A foreign service can return valid JSON that isn't an object (e.g. a
    top-level array). probe_existing must treat that as "not ours" rather
    than raising AttributeError from body.get(...).
    """

    class _StubResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def read(self):
            return b"[1, 2, 3]"

    monkeypatch.setattr(
        launcher.urllib.request,
        "urlopen",
        lambda *a, **k: _StubResponse(),
    )

    assert launcher.probe_existing(5000, timeout=0.2) is False


def test_probe_rejects_a_foreign_service_with_a_mismatched_marker(monkeypatch) -> None:
    """A foreign service can answer with valid JSON shaped like ours but
    naming a different service — that must not be adopted as our instance.
    """

    class _StubResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def read(self):
            return b'{"service": "grafana"}'

    monkeypatch.setattr(
        launcher.urllib.request,
        "urlopen",
        lambda *a, **k: _StubResponse(),
    )

    assert launcher.probe_existing(5000, timeout=0.2) is False


def test_find_existing_scans_the_whole_range_find_free_port_would_try(monkeypatch) -> None:
    """A relaunch must not stop at the preferred port: if it's held by a
    foreign service but our server fell back to a higher port in the same
    range find_free_port would scan, find_existing must locate it instead of
    reporting no existing instance (which would start a silent duplicate).
    """
    preferred = 5000
    our_port = preferred + 3

    def fake_probe(port: int, timeout: float = 0.5) -> bool:
        return port == our_port

    monkeypatch.setattr(launcher, "probe_existing", fake_probe)

    assert launcher.find_existing(preferred) == our_port


def test_find_existing_returns_none_when_nothing_answers(monkeypatch) -> None:
    monkeypatch.setattr(launcher, "probe_existing", lambda port, timeout=0.5: False)

    assert launcher.find_existing(5000, attempts=5) is None


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
