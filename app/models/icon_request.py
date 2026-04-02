"""Data model for an icon generation request."""

from dataclasses import dataclass, field


@dataclass
class IconRequest:
    """Represents a single icon generation request.

    Required fields:
        name:     Human-readable service or device name (e.g. "Raspberry Pi Server").
        category: Device/service category used to select a base symbol.

    Optional fields default to a sensible minimal-blue 256px PNG+SVG output.
    """

    name: str
    category: str
    style: str = "minimal"
    theme: str = "blue"
    size: int = 256
    format: str = "both"          # "png" | "svg" | "both"
    transparent_bg: bool = False
    output_dir: str = "output"

    @property
    def initials(self) -> str:
        """Return uppercase initials derived from the icon name."""
        from app.utils.naming import generate_initials
        return generate_initials(self.name)
