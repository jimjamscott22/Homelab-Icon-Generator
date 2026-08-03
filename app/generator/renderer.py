"""SVG-first output orchestration for the Homelab Icon Generator."""

from __future__ import annotations

import importlib
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from PIL import Image

from app.generator.colors import get_palette
from app.generator.layouts import LayoutSpec, get_layout
from app.generator.rasterizer import rasterize_svg
from app.generator.svg_composer import compose_svg
from app.icons.generic import get_generic_icon
from app.icons.models import IconResolution
from app.models.icon_request import IconRequest
from app.styles.base import StyleDefinition
from app.utils.validation import validate_request

_CREATED_OUTPUT_DIRS: set[str] = set()


class Resolver(Protocol):
    """Minimal resolver interface accepted by the renderer."""

    def resolve(self, request: IconRequest) -> IconResolution:
        """Resolve a request to vector artwork."""


@dataclass(frozen=True)
class GenerationResult:
    """Generated file paths plus the identity decision used to render them."""

    paths: dict[str, str]
    resolution: IconResolution


@lru_cache(maxsize=64)
def _resolve_style(style_name: str, theme: str) -> StyleDefinition:
    palette = get_palette(theme)
    style_module = importlib.import_module(f"app.styles.{style_name}")
    return style_module.get_style(palette)


@lru_cache(maxsize=64)
def _resolve_layout(size: int, font_scale: float) -> LayoutSpec:
    return get_layout(size, font_scale)


def _generic_resolution(request: IconRequest) -> IconResolution:
    return IconResolution(
        icon=get_generic_icon(request.category),
        match_method="generic",
        query=request.name,
        used_fallback=True,
    )


def render_svg(
    request: IconRequest,
    style: StyleDefinition,
    layout: LayoutSpec,
    resolution: IconResolution | None = None,
) -> str:
    """Render a request as the authoritative SVG string."""
    return compose_svg(
        request,
        style,
        layout,
        resolution or _generic_resolution(request),
    )


def render_png(
    request: IconRequest,
    style: StyleDefinition,
    layout: LayoutSpec,
    resolution: IconResolution | None = None,
) -> Image.Image:
    """Rasterize the authoritative SVG into an RGBA image."""
    svg = render_svg(request, style, layout, resolution)
    return rasterize_svg(svg, request.size, request.size)


def _output_path(request: IconRequest, base: str, extension: str) -> str:
    destination = os.path.join(request.output_dir, extension, request.category)
    if destination not in _CREATED_OUTPUT_DIRS:
        os.makedirs(destination, exist_ok=True)
        _CREATED_OUTPUT_DIRS.add(destination)
    return os.path.join(destination, f"{base}.{extension}")


def _output_base(request: IconRequest) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", request.name.lower()).strip("-")
    if not slug:
        slug = request.category
    return f"{slug}-{request.style}-{request.theme}-{request.size}"


def generate_icon_result(
    request: IconRequest,
    resolver: Resolver | None = None,
) -> GenerationResult:
    """Generate requested formats and return paths with resolution metadata."""
    validate_request(request)
    resolution = resolver.resolve(request) if resolver is not None else _generic_resolution(request)
    style = _resolve_style(request.style, request.theme)
    layout = _resolve_layout(request.size, style.font_scale)
    svg = render_svg(request, style, layout, resolution)
    base = _output_base(request)
    paths: dict[str, str] = {}

    if request.format in ("svg", "both", "all"):
        svg_path = _output_path(request, base, "svg")
        with open(svg_path, "w", encoding="utf-8") as output_file:
            output_file.write(svg)
        paths["svg"] = svg_path

    needs_png = request.format in ("png", "both", "all")
    needs_ico = request.format in ("ico", "all")
    raster: Image.Image | None = None
    if needs_png or needs_ico:
        raster = rasterize_svg(svg, request.size, request.size)

    if needs_png and raster is not None:
        png_path = _output_path(request, base, "png")
        png_image = raster if request.transparent_bg else raster.convert("RGB")
        png_image.save(png_path, format="PNG")
        paths["png"] = png_path

    if needs_ico and raster is not None:
        ico_path = _output_path(request, base, "ico")
        ico_image = raster if request.transparent_bg else raster.convert("RGB")
        ico_image.save(
            ico_path,
            format="ICO",
            sizes=[(request.size, request.size)],
        )
        paths["ico"] = ico_path

    return GenerationResult(paths=paths, resolution=resolution)


def generate_icon(request: IconRequest) -> dict[str, str]:
    """Backward-compatible paths-only generation API."""
    return generate_icon_result(request).paths
