"""Rendering smoke tests covering every category, style, and theme."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from PIL import Image

from app.generator.renderer import generate_icon, render_svg
from app.generator.colors import (
    COLOR_THEMES,
    derive_custom_palette,
    normalize_hex_color,
)
from app.models.icon_request import IconRequest
from app.utils.validation import (
    VALID_CATEGORIES,
    VALID_STYLES,
    VALID_THEMES,
    validate_request,
)

CATEGORIES = sorted(VALID_CATEGORIES)
STYLES = sorted(VALID_STYLES)
THEMES = sorted(COLOR_THEMES)


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

    return _resolve_style(request.style, request.theme, request.custom_color)


def _layout_for(request):
    from app.generator.renderer import _resolve_style, _resolve_layout

    style = _resolve_style(request.style, request.theme, request.custom_color)
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
    assert set(COLOR_THEMES) == VALID_THEMES - {"custom"}


def test_custom_color_is_normalized_and_drives_palette() -> None:
    assert normalize_hex_color("#00B8A9") == "#00b8a9"

    palette = derive_custom_palette("#00B8A9")

    assert palette.accent == "#00b8a9"
    assert palette.bg == "#002925"
    assert palette.fg == "#007a70"
    assert palette.text == "#c2fffa"


@pytest.mark.parametrize("value", ["00b8a9", "#abc", "#00b8a9ff", "#00b8ag"])
def test_custom_color_rejects_non_canonical_hex(value: str) -> None:
    with pytest.raises(ValueError, match="custom_color must match"):
        normalize_hex_color(value)


def test_custom_theme_requires_color_and_presets_reject_it() -> None:
    with pytest.raises(ValueError, match="requires custom_color"):
        validate_request(IconRequest(name="Node", category="server", theme="custom"))
    with pytest.raises(ValueError, match="only valid when theme is 'custom'"):
        validate_request(
            IconRequest(
                name="Node",
                category="server",
                theme="blue",
                custom_color="#00b8a9",
            )
        )


def test_custom_theme_renders_exact_accent_and_distinct_output_names(
    tmp_path: Path,
) -> None:
    first = IconRequest(
        name="Node",
        category="server",
        theme="custom",
        custom_color="#00B8A9",
        format="svg",
        output_dir=str(tmp_path),
    )
    second = IconRequest(
        name="Node",
        category="server",
        theme="custom",
        custom_color="#ff0066",
        format="svg",
        output_dir=str(tmp_path),
    )

    first_path = generate_icon(first)["svg"]
    second_path = generate_icon(second)["svg"]

    assert first_path.endswith("node-minimal-custom-00b8a9-256.svg")
    assert second_path.endswith("node-minimal-custom-ff0066-256.svg")
    assert first_path != second_path
    assert '#00b8a9' in Path(first_path).read_text(encoding="utf-8")
