"""Minimal style: flat, clean, simple geometry."""

from app.generator.colors import ColorPalette
from app.styles.base import StyleDefinition


def get_style(palette: ColorPalette) -> StyleDefinition:
    """Return a StyleDefinition for the minimal style using the given palette.

    Minimal style is flat and clean with light border, no glow, and slight
    corner rounding. Suitable for a crisp, unadorned icon appearance.
    """
    return StyleDefinition(
        bg_color=palette.bg,
        fg_color=palette.fg,
        accent_color=palette.accent,
        text_color=palette.text,
        border_width=2,
        corner_radius=16,
        use_glow=False,
        font_scale=1.0,
    )
