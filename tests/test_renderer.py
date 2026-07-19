"""Rendering smoke tests covering every category, style, and theme."""

import xml.etree.ElementTree as ET

import pytest
from PIL import Image

from app.generator.renderer import generate_icon, render_svg
from app.generator.colors import COLOR_THEMES
from app.models.icon_request import IconRequest
from app.utils.validation import (
    VALID_CATEGORIES,
    VALID_STYLES,
    VALID_THEMES,
)

CATEGORIES = sorted(VALID_CATEGORIES)
STYLES = sorted(VALID_STYLES)
THEMES = sorted(VALID_THEMES)


@pytest.mark.parametrize("category", CATEGORIES)
def test_every_category_renders_both_formats(category, tmp_path):
    request = IconRequest(
        name="Test Service",
        category=category,
        format="both",
        size=128,
        output_dir=str(tmp_path),
    )
    paths = generate_icon(request)

    assert set(paths) == {"png", "svg"}

    png = Image.open(paths["png"])
    assert png.size == (128, 128)
    # Non-transparent output should have painted a background, not be blank.
    assert png.getbbox() is not None

    # SVG must be well-formed XML.
    tree = ET.parse(paths["svg"])
    assert tree.getroot().tag.endswith("svg")


@pytest.mark.parametrize("style", STYLES)
@pytest.mark.parametrize("theme", THEMES)
def test_style_theme_matrix_svg_is_valid_xml(style, theme):
    request = IconRequest(
        name="Nextcloud",
        category="cloud_service",
        style=style,
        theme=theme,
        size=256,
    )
    svg = render_svg(
        request,
        _style_for(request),
        _layout_for(request),
    )
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")


def _style_for(request):
    from app.generator.renderer import _resolve_style

    return _resolve_style(request.style, request.theme)


def _layout_for(request):
    from app.generator.renderer import _resolve_style, _resolve_layout

    style = _resolve_style(request.style, request.theme)
    return _resolve_layout(request.size, style.font_scale)


def test_svg_escapes_special_characters():
    # Initials are drawn from the first character of each word, so a word
    # beginning with "&" puts a raw ampersand into the text node.
    request = IconRequest(name="Foo & Bar", category="server", size=256)
    assert request.initials == "F&B"
    svg = render_svg(request, _style_for(request), _layout_for(request))
    # Raw ampersand would make the XML invalid; escaping keeps it parseable.
    assert "&amp;" in svg
    ET.fromstring(svg)


def test_transparent_background_has_no_fill_rect():
    request = IconRequest(
        name="Server", category="server", size=256, transparent_bg=True
    )
    svg = render_svg(request, _style_for(request), _layout_for(request))
    assert 'fill="none"' in svg


def test_transparent_png_has_alpha(tmp_path):
    request = IconRequest(
        name="Server",
        category="server",
        format="png",
        size=64,
        transparent_bg=True,
        output_dir=str(tmp_path),
    )
    paths = generate_icon(request)
    png = Image.open(paths["png"])
    assert png.mode == "RGBA"


def test_empty_slug_falls_back_to_category(tmp_path):
    # A name made entirely of punctuation slugifies to an empty string.
    request = IconRequest(
        name="!!!",
        category="database",
        format="svg",
        size=128,
        output_dir=str(tmp_path),
    )
    paths = generate_icon(request)
    assert "database-" in paths["svg"].rsplit("/", 1)[-1]


def test_ico_output_written(tmp_path):
    request = IconRequest(
        name="Nextcloud",
        category="cloud_service",
        format="ico",
        size=128,
        output_dir=str(tmp_path),
    )
    paths = generate_icon(request)
    assert "ico" in paths
    img = Image.open(paths["ico"])
    assert img.format == "ICO"


def test_all_format_produces_three_files(tmp_path):
    request = IconRequest(
        name="Nextcloud",
        category="cloud_service",
        format="all",
        size=128,
        output_dir=str(tmp_path),
    )
    paths = generate_icon(request)
    assert set(paths) == {"png", "svg", "ico"}


def test_every_theme_defined():
    assert set(COLOR_THEMES) == VALID_THEMES
