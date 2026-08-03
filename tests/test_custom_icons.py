"""Custom icon manifest, sanitization, override, and diagnostic behavior."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.icons.custom import load_custom_registry, resolve_custom_icon_dir
from app.icons.resolver import build_resolver
from app.models.icon_request import IconRequest


FIXTURE = Path(__file__).parent / "fixtures" / "custom-icons"


def _write_entry(directory: Path, svg: str, *, key: str = "unsafe") -> None:
    directory.mkdir()
    (directory / "manifest.json").write_text(
        json.dumps(
            {
                "icons": [
                    {
                        "key": key,
                        "name": key.title(),
                        "file": "icon.svg",
                        "aliases": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (directory / "icon.svg").write_text(svg, encoding="utf-8")


def test_geometry_only_svg_loads_and_is_recolorable() -> None:
    registry = load_custom_registry(FIXTURE)

    icon = registry.get("internal-api")
    assert icon is not None
    assert icon.source == "custom"
    assert registry.exact("corp api") is icon
    assert icon.nodes[0].attrs["transform"].startswith("translate")
    assert icon.nodes[0].children[0].attrs["fill"] == "currentColor"
    assert registry.diagnostics == ()


@pytest.mark.parametrize(
    "payload, reason",
    [
        ('<svg viewBox="0 0 24 24"><script>alert(1)</script></svg>', "script"),
        ('<svg viewBox="0 0 24 24"><image href="https://x/y.png"/></svg>', "image"),
        ('<svg viewBox="0 0 24 24"><path onclick="alert(1)" d="M0 0"/></svg>', "event-handler"),
        ('<svg viewBox="0 0 24 24"><foreignObject/></svg>', "foreignObject"),
        ('<svg viewBox="0 0 24 24"><text>secret</text></svg>', "text"),
        ('<svg viewBox="0 0 24 24"><path fill="url(#paint)" d="M0 0"/></svg>', "references"),
        ('<svg viewBox="0 0 24 24"><path transform="scale(NaN)" d="M0 0"/></svg>', "transform"),
    ],
)
def test_active_external_or_unsupported_svg_is_isolated(
    tmp_path: Path, payload: str, reason: str
) -> None:
    directory = tmp_path / "custom"
    _write_entry(directory, payload)

    registry = load_custom_registry(directory)

    assert registry.get("unsafe") is None
    assert registry.diagnostics[0].severity == "error"
    assert reason.casefold() in registry.diagnostics[0].message.casefold()


def test_custom_name_and_key_override_bundled_catalog(tmp_path: Path) -> None:
    directory = tmp_path / "custom"
    _write_entry(
        directory,
        '<svg viewBox="0 0 24 24"><path d="M2 2h20v20H2z"/></svg>',
        key="nextcloud",
    )
    resolver = build_resolver(str(directory))

    automatic = resolver.resolve(IconRequest("Nextcloud", "cloud_service"))
    explicit = resolver.resolve(
        IconRequest("Anything", "cloud_service", icon="nextcloud")
    )

    assert automatic.icon.source == "custom"
    assert automatic.match_method == "custom"
    assert explicit.icon.source == "custom"
    assert explicit.match_method == "explicit"


def test_explicit_invalid_custom_icon_reports_its_diagnostic(tmp_path: Path) -> None:
    directory = tmp_path / "custom"
    _write_entry(
        directory,
        '<svg viewBox="0 0 24 24"><script/></svg>',
        key="broken-icon",
    )

    with pytest.raises(ValueError, match=r"broken-icon.*unsupported element: script"):
        build_resolver(str(directory)).resolve(
            IconRequest("Broken", "generic_service", icon="broken-icon")
        )


def test_icon_directory_precedence(monkeypatch, tmp_path: Path) -> None:
    configured = tmp_path / "configured"
    explicit = tmp_path / "explicit"
    monkeypatch.setenv("HOMELAB_ICON_DIR", str(configured))

    assert resolve_custom_icon_dir(explicit) == explicit
    assert resolve_custom_icon_dir() == configured


def test_missing_custom_directory_is_valid(tmp_path: Path) -> None:
    registry = load_custom_registry(tmp_path / "absent")

    assert not registry.icons
    assert registry.diagnostics == ()
