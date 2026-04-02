"""Color palette definitions for the Homelab Icon Generator."""

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


def get_palette(theme: str) -> ColorPalette:
    """Return palette for theme, raising ValueError if unknown."""
    if theme not in COLOR_THEMES:
        known = ", ".join(sorted(COLOR_THEMES.keys()))
        raise ValueError(f"Unknown theme '{theme}'. Known themes: {known}")
    return COLOR_THEMES[theme]
