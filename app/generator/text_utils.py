import os

from PIL import ImageDraw, ImageFont


def render_initials(
    draw: ImageDraw.ImageDraw,
    text: str,
    cx: int,
    cy: int,
    font_size: int,
    color: str,
) -> None:
    """Draw initials text centered at (cx, cy).

    Attempts to load a system monospace TrueType font; falls back to the
    Pillow built-in bitmap font when no system font can be found.
    """
    font = _load_font(font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = cx - (bbox[0] + bbox[2]) // 2
    y = cy - (bbox[1] + bbox[3]) // 2
    draw.text((x, y), text, font=font, fill=color)


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try common monospace font paths; fall back to Pillow default."""
    candidates = [
        "C:/Windows/Fonts/consola.ttf",                              # Windows Consolas
        "C:/Windows/Fonts/cour.ttf",                                 # Windows Courier New
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",       # Linux (Debian/Ubuntu)
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",  # Linux (RHEL/Fedora)
        "/System/Library/Fonts/Monaco.ttf",                          # macOS
        "/System/Library/Fonts/Menlo.ttc",                           # macOS (newer)
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default(size=size)
