"""Cyberpunk style: high contrast, layered accents, strong presence."""

from app.generator.colors import ColorPalette
from app.styles.base import StyleDefinition


def _brighten(hex_color: str, amount: float) -> str:
    """Brighten a hex color by blending toward white.

    Each RGB channel is blended toward 255 by `amount` fraction, then clamped
    to [0, 255]. Returns a valid #RRGGBB hex string.
    """
    color = hex_color.lstrip("#")
    r, g, b = (int(color[i:i + 2], 16) for i in (0, 2, 4))
    r = max(0, min(255, int(r + (255 - r) * amount)))
    g = max(0, min(255, int(g + (255 - g) * amount)))
    b = max(0, min(255, int(b + (255 - b) * amount)))
    return f"#{r:02x}{g:02x}{b:02x}"


def get_style(palette: ColorPalette) -> StyleDefinition:
    """Return a StyleDefinition for the cyberpunk style using the given palette.

    Cyberpunk style maximises visual impact: accent color used for both fg and
    accent slots for maximum pop, brightened text, glow effect enabled, and
    slightly larger initials to fill the frame boldly.
    """
    return StyleDefinition(
        bg_color=palette.bg,
        fg_color=palette.accent,
        accent_color=palette.accent,
        text_color=_brighten(palette.text, 0.2),
        border_width=3,
        corner_radius=8,
        use_glow=True,
        font_scale=1.1,
    )
