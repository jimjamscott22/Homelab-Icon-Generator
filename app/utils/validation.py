"""Validation constants and helpers for IconRequest fields."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.icon_request import IconRequest

VALID_CATEGORIES = {
    "raspberry_pi", "server", "router", "switch", "laptop",
    "desktop", "phone", "iot", "container", "database",
    "cloud_service", "generic_service",
}
VALID_STYLES = {"minimal", "terminal", "cyberpunk"}
VALID_THEMES = {"green", "blue", "orange", "purple", "grayscale"}
VALID_FORMATS = {"png", "svg", "both"}

_MIN_SIZE = 32
_MAX_SIZE = 2048


def validate_request(request: IconRequest) -> None:
    """Validate an IconRequest, raising ValueError on the first invalid field.

    Checks name, category, style, theme, format, and size.
    """
    if not request.name or not request.name.strip():
        raise ValueError("name must not be empty")
    if request.category not in VALID_CATEGORIES:
        raise ValueError(
            f"Invalid category '{request.category}'. "
            f"Valid options: {sorted(VALID_CATEGORIES)}"
        )
    if request.style not in VALID_STYLES:
        raise ValueError(
            f"Invalid style '{request.style}'. "
            f"Valid options: {sorted(VALID_STYLES)}"
        )
    if request.theme not in VALID_THEMES:
        raise ValueError(
            f"Invalid theme '{request.theme}'. "
            f"Valid options: {sorted(VALID_THEMES)}"
        )
    if request.format not in VALID_FORMATS:
        raise ValueError(
            f"Invalid format '{request.format}'. "
            f"Valid options: {sorted(VALID_FORMATS)}"
        )
    if not (_MIN_SIZE <= request.size <= _MAX_SIZE):
        raise ValueError(
            f"Size {request.size} is out of range. "
            f"Must be between {_MIN_SIZE} and {_MAX_SIZE} (inclusive)."
        )
