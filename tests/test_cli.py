"""CLI request wiring for automatic and explicit icon selection."""

from __future__ import annotations

import json
import sys
from argparse import Namespace
from pathlib import Path

import pytest

import app.main as cli


def test_parse_args_accepts_icon_override(monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["homelab-icons", "--name", "Cloud", "--category", "server", "--icon", "nextcloud"],
    )

    _, args = cli.parse_args()

    assert args.icon == "nextcloud"


def test_single_request_passes_icon_to_generator(monkeypatch, tmp_path: Path) -> None:
    captured = []
    monkeypatch.setattr(cli, "generate_icon", lambda request: captured.append(request) or {})
    args = Namespace(
        name="Cloud",
        category="server",
        style="minimal",
        theme="blue",
        custom_color=None,
        size=128,
        format="svg",
        icon="generic",
        transparent=False,
        output_dir=str(tmp_path),
    )

    cli.run_single(args)

    assert captured[0].icon == "generic"


def test_single_request_passes_custom_color_to_generator(
    monkeypatch, tmp_path: Path
) -> None:
    captured = []
    monkeypatch.setattr(cli, "generate_icon", lambda request: captured.append(request) or {})
    args = Namespace(
        name="Node",
        category="server",
        style="minimal",
        theme="custom",
        custom_color="#00B8A9",
        size=128,
        format="svg",
        icon="generic",
        transparent=False,
        output_dir=str(tmp_path),
    )

    cli.run_single(args)

    assert captured[0].custom_color == "#00B8A9"


def test_batch_entry_passes_icon_to_generator(monkeypatch, tmp_path: Path) -> None:
    batch = tmp_path / "icons.json"
    batch.write_text(
        json.dumps([{"name": "Cloud", "category": "server", "icon": "nextcloud"}]),
        encoding="utf-8",
    )
    captured = []
    monkeypatch.setattr(cli, "generate_icon", lambda request: captured.append(request) or {})

    cli.run_batch(str(batch), str(tmp_path))

    assert captured[0].icon == "nextcloud"


def test_batch_entry_passes_custom_color_to_generator(
    monkeypatch, tmp_path: Path
) -> None:
    batch = tmp_path / "icons.json"
    batch.write_text(
        json.dumps(
            [
                {
                    "name": "Node",
                    "category": "server",
                    "theme": "custom",
                    "custom_color": "#00b8a9",
                }
            ]
        ),
        encoding="utf-8",
    )
    captured = []
    monkeypatch.setattr(cli, "generate_icon", lambda request: captured.append(request) or {})

    cli.run_batch(str(batch), str(tmp_path))

    assert captured[0].custom_color == "#00b8a9"


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
