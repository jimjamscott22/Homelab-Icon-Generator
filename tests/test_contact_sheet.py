"""Deterministic visual coverage for brand, custom, and generic rendering."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops

from app.icons.resolver import build_resolver
from scripts.generate_contact_sheet import generate_contact_sheet, representative_cases


ROOT = Path(__file__).resolve().parents[1]


def test_contact_sheet_matches_brand_custom_and_generic_golden(tmp_path: Path) -> None:
    icon_dir = ROOT / "tests" / "fixtures" / "custom-icons"
    result = generate_contact_sheet(
        tmp_path / "contact-sheet.png",
        representative_cases(include_custom=True),
        128,
        build_resolver(str(icon_dir)),
    )
    with Image.open(ROOT / "tests" / "golden" / "hybrid-contact-sheet.png") as expected:
        difference = ImageChops.difference(result, expected.convert("RGBA"))

    assert result.size == (384, 128)
    assert difference.getbbox() is None


def test_contact_sheet_rejects_empty_cases(tmp_path: Path) -> None:
    try:
        generate_contact_sheet(tmp_path / "empty.png", (), 128, build_resolver())
    except ValueError as exc:
        assert "at least one" in str(exc)
    else:
        raise AssertionError("empty contact sheets must be rejected")
