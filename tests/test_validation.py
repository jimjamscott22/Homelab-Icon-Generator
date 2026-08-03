"""Tests for IconRequest field validation."""

import pytest

from app.models.icon_request import IconRequest
from app.utils.validation import (
    VALID_CATEGORIES,
    VALID_FORMATS,
    VALID_STYLES,
    VALID_THEMES,
    validate_request,
)


def _request(**overrides) -> IconRequest:
    defaults = dict(name="Nextcloud", category="cloud_service")
    defaults.update(overrides)
    return IconRequest(**defaults)


def test_valid_request_passes():
    validate_request(_request())


@pytest.mark.parametrize("name", ["", "   "])
def test_empty_name_rejected(name):
    with pytest.raises(ValueError, match="name"):
        validate_request(_request(name=name))


def test_unknown_category_rejected():
    with pytest.raises(ValueError, match="category"):
        validate_request(_request(category="not_a_category"))


def test_unknown_style_rejected():
    with pytest.raises(ValueError, match="style"):
        validate_request(_request(style="glitter"))


def test_unknown_theme_rejected():
    with pytest.raises(ValueError, match="theme"):
        validate_request(_request(theme="chartreuse"))


def test_unknown_format_rejected():
    with pytest.raises(ValueError, match="format"):
        validate_request(_request(format="tiff"))


@pytest.mark.parametrize("icon", ["", "   ", None])
def test_empty_icon_selection_rejected(icon):
    with pytest.raises(ValueError, match="icon"):
        validate_request(_request(icon=icon))


@pytest.mark.parametrize("size", [31, 2049, 0, -1])
def test_size_out_of_range_rejected(size):
    with pytest.raises(ValueError, match="out of range"):
        validate_request(_request(size=size))


@pytest.mark.parametrize("size", [32, 256, 2048])
def test_size_boundaries_allowed(size):
    validate_request(_request(size=size))


@pytest.mark.parametrize("fmt", ["ico", "all"])
def test_ico_rejects_oversize(fmt):
    with pytest.raises(ValueError, match="ICO"):
        validate_request(_request(format=fmt, size=512))


@pytest.mark.parametrize("fmt", ["ico", "all"])
def test_ico_allows_max_supported_size(fmt):
    validate_request(_request(format=fmt, size=256))


@pytest.mark.parametrize("fmt", ["png", "svg", "both"])
def test_non_ico_formats_allow_large_sizes(fmt):
    validate_request(_request(format=fmt, size=2048))


def test_valid_sets_are_nonempty():
    assert VALID_CATEGORIES
    assert VALID_STYLES == {"minimal", "terminal", "cyberpunk"}
    assert VALID_THEMES == {"green", "blue", "orange", "purple", "grayscale"}
    assert {"png", "svg", "ico", "both", "all"} <= VALID_FORMATS
