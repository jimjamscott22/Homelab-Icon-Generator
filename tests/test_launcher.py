"""Launcher: port selection, instance probing, and idle shutdown."""

from __future__ import annotations

import contextlib
import socket

from fastapi.testclient import TestClient

from app.web import api, launcher


def _free_port() -> int:
    """An ephemeral port that is free at the moment this returns."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((launcher.HOST, 0))
        return probe.getsockname()[1]


@contextlib.contextmanager
def _hold_ports(*ports: int):
    """Keep real listening sockets open on `ports` for the duration of the
    block, so `_can_bind` genuinely reports them as occupied — a bind-gated
    scan must reach the HTTP probe for these ports rather than short-circuit.
    """
    with contextlib.ExitStack() as stack:
        for port in ports:
            sock = stack.enter_context(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
            sock.bind((launcher.HOST, port))
            sock.listen(1)
        yield


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

    The bind gate in front of the HTTP probe means a candidate is only ever
    probed if something is genuinely listening there — so the candidates
    below `our_port` must be real, held sockets, not just a monkeypatched
    probe_existing, or the scan would short-circuit on the first (free) port
    before ever reaching the fake.
    """
    preferred = _free_port()
    our_port = preferred + 3

    def fake_probe(port: int, timeout: float = 0.5) -> bool:
        return port == our_port

    monkeypatch.setattr(launcher, "probe_existing", fake_probe)

    with _hold_ports(preferred, preferred + 1, preferred + 2, our_port):
        assert launcher.find_existing(preferred) == our_port


def test_find_existing_returns_none_when_every_candidate_is_foreign(monkeypatch) -> None:
    """All candidates in range are occupied (bind fails on each, so each is
    HTTP-probed) but none answer with our marker — find_existing must fall
    through to None rather than adopting a foreign service.
    """
    preferred = _free_port()

    monkeypatch.setattr(launcher, "probe_existing", lambda port, timeout=0.5: False)

    with _hold_ports(*(preferred + offset for offset in range(5))):
        assert launcher.find_existing(preferred, attempts=5) is None


def test_find_existing_does_not_probe_over_the_network_when_the_port_is_free(
    monkeypatch,
) -> None:
    """Regression: the HTTP probe must be gated behind an instant bind()
    check. A free preferred port (the ordinary cold-launch case — nothing
    running yet) must be detected by the bind check alone; issuing an HTTP
    request at all here means a Windows loopback port that silently drops
    the SYN would burn a full probe timeout per candidate before uvicorn
    even starts. Assert on the absence of the call rather than timing it,
    which would be flaky.
    """
    preferred = _free_port()

    def _fail_if_called(*args, **kwargs):
        raise AssertionError(
            "find_existing must not issue an HTTP request when the port is free"
        )

    monkeypatch.setattr(launcher.urllib.request, "urlopen", _fail_if_called)

    assert launcher.find_existing(preferred) is None


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
