"""FastAPI coverage for backend options, icon search, and resolution metadata."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.web import api
from app.utils.validation import VALID_CATEGORIES, VALID_FORMATS


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(api, "OUTPUT_DIR", tmp_path / "output")
    api._req_times.clear()
    api.reset_gallery()
    with TestClient(api.app) as test_client:
        yield test_client
    api.reset_gallery()


def test_options_exposes_every_backend_choice(client) -> None:
    response = client.get("/api/options")
    data = response.json()

    assert response.status_code == 200
    assert set(data["categories"]) == VALID_CATEGORIES
    assert set(data["formats"]) == VALID_FORMATS
    assert data["icon_modes"] == ["auto", "generic"]


def test_search_reports_exact_match_and_advisory_suggestions(client) -> None:
    exact = client.get("/api/icons/search?q=Nextcloud").json()
    typo = client.get("/api/icons/search?q=Nextclod").json()

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
    data = response.json()

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
    ).json()
    forced = client.post(
        "/api/generate",
        json={
            "name": "Nextcloud",
            "category": "server",
            "format": "svg",
            "icon": "generic",
        },
    ).json()

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
    assert "nextcloud" in response.json()["error"]


def test_page_has_accessible_override_controls_and_no_external_fonts(client) -> None:
    page = client.get("/").text

    assert 'id="iconDetection"' in page
    assert 'data-icon-key="generic"' in page
    assert 'aria-live="polite"' in page
    assert "fonts.googleapis.com" not in page


def test_generate_with_empty_body_is_a_client_error(client) -> None:
    response = client.post("/api/generate")

    assert response.status_code == 400
    assert "error" in response.json()


def test_generate_populates_history(client) -> None:
    client.post(
        "/api/generate",
        json={"name": "Nextcloud", "category": "cloud_service", "format": "svg"},
    )

    items = client.get("/api/history").json()["items"]

    assert len(items) == 1
    assert items[0]["name"] == "Nextcloud"
    assert items[0]["icon_key"] == "nextcloud"
    assert items[0]["thumb"].startswith("/output/svg/")


def test_history_is_empty_before_any_generation(client) -> None:
    assert client.get("/api/history").json()["items"] == []


def test_repeat_generation_does_not_duplicate_history(client) -> None:
    body = {"name": "Nextcloud", "category": "cloud_service", "format": "svg"}
    client.post("/api/generate", json=body)
    client.post("/api/generate", json=body)

    assert len(client.get("/api/history").json()["items"]) == 1


def test_generation_survives_a_failing_gallery(client, monkeypatch) -> None:
    class _ExplodingGallery:
        def record(self, payload: dict) -> None:
            raise RuntimeError("boom")

    monkeypatch.setattr(api, "get_gallery", lambda: _ExplodingGallery())

    response = client.post(
        "/api/generate",
        json={"name": "Nextcloud", "category": "cloud_service", "format": "svg"},
    )
    data = response.json()

    assert response.status_code == 200
    assert set(data["files"]) == {"svg"}
    assert data["icon_key"] == "nextcloud"


def test_generation_survives_no_gallery_at_all(client, monkeypatch) -> None:
    monkeypatch.setattr(api, "get_gallery", lambda: None)

    response = client.post(
        "/api/generate",
        json={"name": "Nextcloud", "category": "cloud_service", "format": "svg"},
    )
    data = response.json()

    assert response.status_code == 200
    assert set(data["files"]) == {"svg"}
    assert data["icon_key"] == "nextcloud"


def test_history_degrades_to_empty_when_gallery_unavailable(client, monkeypatch) -> None:
    monkeypatch.setattr(api, "get_gallery", lambda: None)

    response = client.get("/api/history")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_search_with_non_integer_limit_is_a_client_error(client) -> None:
    response = client.get("/api/icons/search?q=Nextcloud&limit=abc")

    assert response.status_code == 400
    assert response.json()["error"] == "limit must be an integer"


def test_output_dir_follows_cwd_not_package_install_location(tmp_path: Path) -> None:
    """OUTPUT_DIR is computed at import time from Path.cwd(), so this pins
    the computation with a fresh subprocess per working directory rather than
    relying on the already-imported (and possibly monkeypatched) module.
    """
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    code = "from app.web import api; print(api.OUTPUT_DIR)"

    result_first = subprocess.run(
        [sys.executable, "-c", code],
        cwd=first,
        capture_output=True,
        text=True,
        check=True,
    )
    result_second = subprocess.run(
        [sys.executable, "-c", code],
        cwd=second,
        capture_output=True,
        text=True,
        check=True,
    )

    assert Path(result_first.stdout.strip()) == first / "output"
    assert Path(result_second.stdout.strip()) == second / "output"


def test_generate_with_non_integer_size_is_a_client_error(client) -> None:
    response = client.post(
        "/api/generate",
        json={"name": "Nextcloud", "category": "cloud_service", "size": "abc"},
    )

    assert response.status_code == 400
    assert "error" in response.json()


def test_generate_with_unparseable_json_body_is_a_client_error(client) -> None:
    response = client.post(
        "/api/generate",
        content="not json",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 400
    assert "error" in response.json()
