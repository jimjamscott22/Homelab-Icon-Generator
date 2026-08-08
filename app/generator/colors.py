"""Color palette definitions for the Homelab Icon Generator."""

import colorsys
import re
from dataclasses import dataclass


@dataclass
class ColorPalette:
    """Represents a complete color palette for an icon theme."""

    bg: str      # background hex color e.g. "#1a1a2e"
    fg: str      # foreground/symbol color
    accent: str  # accent/highlight color
    text: str    # text/initials color


COLOR_THEMES: dict[str, ColorPalette] = {
    "green": ColorPalette(bg="#0d1f0d", fg="#2d6a2d", accent="#39ff14", text="#c8f7c8"),
    "blue": ColorPalette(bg="#0d1626", fg="#1a3a5c", accent="#4fc3f7", text="#b3e5fc"),
    "orange": ColorPalette(bg="#1a0d00", fg="#5c2d00", accent="#ff8c00", text="#ffe0b2"),
    "purple": ColorPalette(bg="#1a0d26", fg="#4a1a6e", accent="#ce93d8", text="#e1bee7"),
    "grayscale": ColorPalette(bg="#1a1a1a", fg="#3d3d3d", accent="#b0b0b0", text="#e8e8e8"),
}

CUSTOM_THEME = "custom"
DEFAULT_CUSTOM_COLOR = "#00b8a9"
_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def normalize_hex_color(value: str) -> str:
    """Return a lowercase six-digit hex color or raise ValueError."""
    if not isinstance(value, str) or _HEX_COLOR.fullmatch(value) is None:
        raise ValueError("custom_color must match #RRGGBB")
    return value.lower()


def _hls_hex(hue: float, saturation: float, lightness: float) -> str:
    red, green, blue = colorsys.hls_to_rgb(hue, lightness, saturation)
    channels = (round(red * 255), round(green * 255), round(blue * 255))
    return "#" + "".join(f"{channel:02x}" for channel in channels)


def derive_custom_palette(value: str) -> ColorPalette:
    """Derive a dark, coordinated palette from an exact accent color."""
    accent = normalize_hex_color(value)
    red, green, blue = (
        int(accent[index:index + 2], 16) / 255 for index in (1, 3, 5)
    )
    hue, _, saturation = colorsys.rgb_to_hls(red, green, blue)
    return ColorPalette(
        bg=_hls_hex(hue, saturation, 0.08),
        fg=_hls_hex(hue, saturation, 0.24),
        accent=accent,
        text=_hls_hex(hue, saturation, 0.88),
    )


def get_palette(theme: str, custom_color: str | None = None) -> ColorPalette:
    """Return palette for theme, raising ValueError if unknown."""
    if theme == CUSTOM_THEME:
        if custom_color is None:
            raise ValueError("theme 'custom' requires custom_color")
        return derive_custom_palette(custom_color)
    if theme not in COLOR_THEMES:
        known = ", ".join(sorted((*COLOR_THEMES.keys(), CUSTOM_THEME)))
        raise ValueError(f"Unknown theme '{theme}'. Known themes: {known}")
    return COLOR_THEMES[theme]
