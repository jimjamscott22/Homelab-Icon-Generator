"""Resolver coverage for exact brands, controlled normalization, and fallback."""

from __future__ import annotations

import socket

import pytest

from app.icons.resolver import get_default_resolver, normalize_icon_name
from app.models.icon_request import IconRequest


@pytest.mark.parametrize("name", ["Nextcloud", "NEXTCLOUD", "Nextcloud Server"])
def test_known_name_resolves_catalog(name: str) -> None:
    result = get_default_resolver().resolve(
        IconRequest(name=name, category="cloud_service")
    )

    assert result.icon.key == "nextcloud"
    assert result.used_fallback is False
    assert result.show_initials is False


def test_near_match_is_suggestion_only() -> None:
    resolver = get_default_resolver()

    result = resolver.resolve(IconRequest("Nextclod", "cloud_service"))

    assert result.icon.key == "cloud_service"
    assert result.used_fallback is True
    assert resolver.suggest("Nextclod")[0].key == "nextcloud"


def test_unicode_normalization_and_resolution_are_offline(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "create_connection",
        lambda *args, **kwargs: pytest.fail("normal generation used the network"),
    )

    result = get_default_resolver().resolve(
        IconRequest("ＮＥＸＴＣＬＯＵＤ", "cloud_service")
    )

    assert normalize_icon_name("ＮＥＸＴＣＬＯＵＤ") == "nextcloud"
    assert result.icon.key == "nextcloud"


def test_controlled_deployment_suffix_can_match() -> None:
    result = get_default_resolver().resolve(
        IconRequest("Grafana instance", "generic_service")
    )

    assert result.icon.key == "grafana"
    assert result.match_method == "normalized"


def test_generic_and_explicit_controls_override_auto() -> None:
    resolver = get_default_resolver()

    generic = resolver.resolve(
        IconRequest("Nextcloud", "cloud_service", icon="generic")
    )
    explicit = resolver.resolve(
        IconRequest("Private Cloud", "cloud_service", icon="nextcloud")
    )

    assert generic.icon.key == "cloud_service"
    assert generic.used_fallback is False
    assert generic.show_initials is True
    assert explicit.icon.key == "nextcloud"
    assert explicit.match_method == "explicit"


def test_unknown_explicit_icon_reports_suggestions() -> None:
    with pytest.raises(ValueError, match=r"Unknown explicit icon.*nextcloud"):
        get_default_resolver().resolve(
            IconRequest("Cloud", "cloud_service", icon="nextclod")
        )
