"""Base style definition dataclass for the Homelab Icon Generator."""

from dataclasses import dataclass


@dataclass
class StyleDefinition:
    """Describes all visual parameters needed to render an icon in a given style."""

    bg_color: str       # background fill color (hex)
    fg_color: str       # foreground/symbol fill color (hex)
    accent_color: str   # accent/highlight color (hex)
    text_color: str     # initials text color (hex)
    border_width_ratio: float  # border/stroke width as a fraction of canvas size
    corner_radius_ratio: float  # rounded-corner radius as a fraction of canvas size
    use_glow: bool      # whether to apply a glow/shadow effect
    font_scale: float   # multiplier for initials font size (1.0 = normal)

    @property
    def border_width(self) -> int:
        """Compatibility value for the legacy 256px renderer."""
        return round(self.border_width_ratio * 256)

    @property
    def corner_radius(self) -> int:
        """Compatibility value for the legacy 256px renderer."""
        return round(self.corner_radius_ratio * 256)
