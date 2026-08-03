"""CLI request wiring for automatic and explicit icon selection."""

from __future__ import annotations

import json
import sys
from argparse import Namespace
from pathlib import Path

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
        size=128,
        format="svg",
        icon="generic",
        transparent=False,
        output_dir=str(tmp_path),
    )

    cli.run_single(args)

    assert captured[0].icon == "generic"


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
