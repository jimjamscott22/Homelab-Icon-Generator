"""Terminal style: darker bg, phosphor-like accents, monospace feel."""

from app.generator.colors import ColorPalette
from app.styles.base import StyleDefinition


def _darken(hex_color: str, amount: float) -> str:
    """Darken a hex color by reducing each channel by `amount` fraction.

    Each RGB channel is multiplied by (1 - amount), then clamped to [0, 255].
    Returns a valid #RRGGBB hex string.
    """
    color = hex_color.lstrip("#")
    r, g, b = (int(color[i:i + 2], 16) for i in (0, 2, 4))
    factor = 1.0 - amount
    r = max(0, min(255, int(r * factor)))
    g = max(0, min(255, int(g * factor)))
    b = max(0, min(255, int(b * factor)))
    return f"#{r:02x}{g:02x}{b:02x}"


def get_style(palette: ColorPalette) -> StyleDefinition:
    """Return a StyleDefinition for the terminal style using the given palette.

    Terminal style evokes a phosphor monitor: darkened background, accent color
    used as the foreground for a glowing character effect, minimal rounding, and
    a subtle glow applied to the icon.
    """
    return StyleDefinition(
        bg_color=_darken(palette.bg, 0.3),
        fg_color=palette.accent,
        accent_color=palette.accent,
        text_color=palette.text,
        border_width=1,
        corner_radius=4,
        use_glow=True,
        font_scale=0.9,
    )
