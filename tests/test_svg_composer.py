"""Tests for composing normalized icons into themed SVG documents."""

import re
import xml.etree.ElementTree as ET

from app.generator.layouts import get_layout
from app.generator.svg_composer import compose_svg
from app.icons.generic import get_generic_icon
from app.icons.models import IconResolution, VectorIcon, VectorNode
from app.models.icon_request import IconRequest
from app.styles.minimal import get_style
from app.generator.colors import get_palette


def _brand_resolution() -> IconResolution:
    icon = VectorIcon(
        key="nextcloud",
        title="Nextcloud",
        source="fixture-catalog",
        view_box=(0, 0, 24, 24),
        nodes=(VectorNode("path", {"d": "M0 0h24v24H0z"}),),
    )
    return IconResolution(icon, "catalog", "nextcloud", False)


def _generic_resolution(category: str = "nas") -> IconResolution:
    return IconResolution(get_generic_icon(category), "generic", "nas", True)


def test_brand_is_centered_without_initials() -> None:
    request = IconRequest("Nextcloud", "cloud_service", size=256)
    style = get_style(get_palette("blue"))

    svg = compose_svg(request, style, get_layout(256, style.font_scale), _brand_resolution())

    assert "<text" not in svg
    assert 'preserveAspectRatio="xMidYMid meet"' in svg
    assert 'viewBox="0 0 24 24"' in svg
    ET.fromstring(svg)


def test_generic_keeps_initials_and_scales_frame_proportionally() -> None:
    style = get_style(get_palette("blue"))
    small_request = IconRequest("NAS", "nas", size=64)
    large_request = IconRequest("NAS", "nas", size=256)

    small = compose_svg(
        small_request,
        style,
        get_layout(64, style.font_scale),
        _generic_resolution(),
    )
    large = compose_svg(
        large_request,
        style,
        get_layout(256, style.font_scale),
        _generic_resolution(),
    )

    assert ">N</text>" in small
    assert float(re.search(r'stroke-width="([\d.]+)"', large).group(1)) == 4 * float(
        re.search(r'stroke-width="([\d.]+)"', small).group(1)
    )


def test_transparent_composition_has_no_background_fill() -> None:
    request = IconRequest("NAS", "nas", size=128, transparent_bg=True)
    style = get_style(get_palette("green"))

    svg = compose_svg(
        request,
        style,
        get_layout(128, style.font_scale),
        _generic_resolution(),
    )

    assert 'data-role="background"' in svg
    assert 'data-role="background" fill="none"' in svg
