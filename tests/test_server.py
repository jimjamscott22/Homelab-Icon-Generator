"""Flask API coverage for backend options, icon search, and resolution metadata."""

from __future__ import annotations

from pathlib import Path

import pytest

import server
from app.utils.validation import VALID_CATEGORIES, VALID_FORMATS


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(server, "OUTPUT_DIR", tmp_path / "output")
    server._req_times.clear()
    server.app.config.update(TESTING=True)
    with server.app.test_client() as test_client:
        yield test_client


def test_options_exposes_every_backend_choice(client) -> None:
    response = client.get("/api/options")
    data = response.get_json()

    assert response.status_code == 200
    assert set(data["categories"]) == VALID_CATEGORIES
    assert set(data["formats"]) == VALID_FORMATS
    assert data["icon_modes"] == ["auto", "generic"]


def test_search_reports_exact_match_and_advisory_suggestions(client) -> None:
    exact = client.get("/api/icons/search?q=Nextcloud").get_json()
    typo = client.get("/api/icons/search?q=Nextclod").get_json()

    assert exact["exact"]["key"] == "nextcloud"
    assert exact["exact"]["source"] == "simple-icons"
    assert typo["exact"] is None
    assert typo["items"][0]["key"] == "nextcloud"


def test_generate_reports_brand_resolution_without_breaking_files(client) -> None:
    response = client.post(
        "/api/generate",
        json={
            "name": "Nextcloud",
            "category": "cloud_service",
            "format": "svg",
            "size": 128,
        },
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["icon_key"] == "nextcloud"
    assert data["icon_source"] == "simple-icons"
    assert data["match_method"] == "catalog"
    assert data["used_fallback"] is False
    assert set(data["files"]) == {"svg"}


def test_generate_reports_generic_fallback_and_manual_generic(client) -> None:
    fallback = client.post(
        "/api/generate",
        json={"name": "Unknown Private Node", "category": "server", "format": "svg"},
    ).get_json()
    forced = client.post(
        "/api/generate",
        json={
            "name": "Nextcloud",
            "category": "server",
            "format": "svg",
            "icon": "generic",
        },
    ).get_json()

    assert fallback["icon_key"] == "server"
    assert fallback["used_fallback"] is True
    assert forced["icon_key"] == "server"
    assert forced["used_fallback"] is False


def test_unknown_explicit_key_is_a_client_error_with_suggestions(client) -> None:
    response = client.post(
        "/api/generate",
        json={
            "name": "Cloud",
            "category": "cloud_service",
            "format": "svg",
            "icon": "nextclod",
        },
    )

    assert response.status_code == 400
    assert "nextcloud" in response.get_json()["error"]


def test_page_has_accessible_override_controls_and_no_external_fonts(client) -> None:
    page = client.get("/").get_data(as_text=True)

    assert 'id="iconDetection"' in page
    assert 'data-icon-key="generic"' in page
    assert 'aria-live="polite"' in page
    assert "fonts.googleapis.com" not in page
