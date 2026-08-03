"""Tests for high-fidelity in-memory SVG rasterization."""

from PIL import Image

from app.generator.rasterizer import rasterize_svg
from app.generator.renderer import GenerationResult, generate_icon, generate_icon_result
from app.models.icon_request import IconRequest


def test_rasterize_svg_returns_rgba_at_requested_size() -> None:
    """Returning encoded bytes or a wrongly sized image must fail."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
        '<rect width="1" height="1" fill="#fff"/></svg>'
    )

    image = rasterize_svg(svg, 96, 96)

    assert isinstance(image, Image.Image)
    assert image.mode == "RGBA"
    assert image.size == (96, 96)


def test_generate_icon_result_exposes_resolution_and_wrapper_keeps_dict(tmp_path) -> None:
    """Detailed generation must not break the public paths-only wrapper."""
    request = IconRequest(
        "NAS",
        "nas",
        format="both",
        size=128,
        output_dir=str(tmp_path),
    )

    result = generate_icon_result(request)
    paths = generate_icon(request)

    assert isinstance(result, GenerationResult)
    assert result.resolution.icon.key == "nas"
    assert result.resolution.match_method == "generic"
    assert set(result.paths) == {"png", "svg"}
    assert set(paths) == {"png", "svg"}


def test_png_is_rasterized_from_same_glowing_svg(tmp_path) -> None:
    """Terminal PNG must use the SVG glow path instead of the old flat renderer."""
    request = IconRequest(
        "CLI",
        "cli",
        style="terminal",
        format="both",
        size=128,
        output_dir=str(tmp_path),
    )

    result = generate_icon_result(request)

    svg = open(result.paths["svg"], encoding="utf-8").read()
    with Image.open(result.paths["png"]) as image:
        assert image.size == (128, 128)
    assert 'filter="url(#glow)"' in svg
