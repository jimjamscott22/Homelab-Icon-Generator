"""Base style definition dataclass for the Homelab Icon Generator."""

from dataclasses import dataclass


@dataclass
class StyleDefinition:
    """Describes all visual parameters needed to render an icon in a given style."""

    bg_color: str       # background fill color (hex)
    fg_color: str       # foreground/symbol fill color (hex)
    accent_color: str   # accent/highlight color (hex)
    text_color: str     # initials text color (hex)
    border_width: int   # border/stroke width in pixels (relative to 256px canvas)
    corner_radius: int  # corner radius for rounded rect background
    use_glow: bool      # whether to apply a glow/shadow effect
    font_scale: float   # multiplier for initials font size (1.0 = normal)
