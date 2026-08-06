"""Launcher: port selection, instance probing, and idle shutdown."""

from __future__ import annotations

import socket

from fastapi.testclient import TestClient

from app.web import api, launcher


def _free_port() -> int:
    """An ephemeral port that is free at the moment this returns."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((launcher.HOST, 0))
        return probe.getsockname()[1]


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


def test_find_existing_returns_none_and_probes_nothing_when_no_instance_file(
    tmp_path, monkeypatch
) -> None:
    """The ordinary cold-launch case: nothing has ever started here, so no
    `.instance` file exists. find_existing must report None without issuing
    any HTTP request — that's the case that matters most, since it's the
    common path every double-click launch takes.
    """
    monkeypatch.setattr(api, "OUTPUT_DIR", tmp_path / "output")

    def _fail_if_called(*args, **kwargs):
        raise AssertionError(
            "find_existing must not issue an HTTP request when no instance file exists"
        )

    monkeypatch.setattr(launcher.urllib.request, "urlopen", _fail_if_called)

    assert launcher.find_existing() is None


def test_find_existing_returns_the_recorded_port_when_our_marker_answers(
    tmp_path, monkeypatch
) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    monkeypatch.setattr(api, "OUTPUT_DIR", output_dir)
    (output_dir / launcher.INSTANCE_FILENAME).write_text("5001", encoding="utf-8")
    monkeypatch.setattr(launcher, "probe_existing", lambda port, timeout=0.5: port == 5001)

    assert launcher.find_existing() == 5001


def test_find_existing_returns_none_when_the_recorded_port_is_a_foreign_service(
    tmp_path, monkeypatch
) -> None:
    """A stale instance file can point at a port a foreign service has since
    taken over. The file's contents must never be trusted without the
    marker check confirming it's really us.
    """
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    monkeypatch.setattr(api, "OUTPUT_DIR", output_dir)
    (output_dir / launcher.INSTANCE_FILENAME).write_text("5001", encoding="utf-8")
    monkeypatch.setattr(launcher, "probe_existing", lambda port, timeout=0.5: False)

    assert launcher.find_existing() is None


def test_find_existing_returns_none_when_the_recorded_port_is_silent(tmp_path, monkeypatch) -> None:
    """A stale instance file can point at a port nothing listens on anymore
    (the process exited without cleanup). Must resolve to None promptly,
    no hang.
    """
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    monkeypatch.setattr(api, "OUTPUT_DIR", output_dir)
    closed = _free_port()
    (output_dir / launcher.INSTANCE_FILENAME).write_text(str(closed), encoding="utf-8")

    assert launcher.find_existing(timeout=0.2) is None


def test_find_existing_returns_none_for_garbage_file_contents(tmp_path, monkeypatch) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    monkeypatch.setattr(api, "OUTPUT_DIR", output_dir)
    (output_dir / launcher.INSTANCE_FILENAME).write_text("not-a-port\x00garbage", encoding="utf-8")

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("an unparseable instance file must never reach the HTTP probe")

    monkeypatch.setattr(launcher.urllib.request, "urlopen", _fail_if_called)

    assert launcher.find_existing() is None


def test_write_instance_file_round_trips_with_find_existing(tmp_path, monkeypatch) -> None:
    """write_instance_file and find_existing must agree on where the port
    lives and what the alive URL looks like — a sanity check that the write
    path and read path are talking about the same file and the same port,
    with only the network transport itself stubbed.
    """
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    monkeypatch.setattr(api, "OUTPUT_DIR", output_dir)

    port = _free_port()

    class _AliveResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def read(self):
            return b'{"service": "' + api.ALIVE_MARKER.encode() + b'"}'

    def fake_urlopen(url, timeout=0.5):
        assert url == f"http://{launcher.HOST}:{port}/api/alive"
        return _AliveResponse()

    monkeypatch.setattr(launcher.urllib.request, "urlopen", fake_urlopen)

    launcher.write_instance_file(port)

    assert launcher.find_existing() == port


def test_remove_instance_file_is_safe_when_nothing_exists(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(api, "OUTPUT_DIR", tmp_path / "output-not-created")

    launcher.remove_instance_file()  # must not raise


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
