from PIL import ImageDraw


def draw_rounded_rect(
    draw: ImageDraw.ImageDraw,
    xy: tuple[tuple[int, int], tuple[int, int]],
    radius: int,
    fill: str | None = None,
    outline: str | None = None,
    width: int = 1,
) -> None:
    """Draw a rounded rectangle using Pillow's built-in rounded_rectangle."""
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_circle(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    radius: int,
    fill: str | None = None,
    outline: str | None = None,
    width: int = 1,
) -> None:
    """Draw a circle given center point and radius."""
    x, y = center
    draw.ellipse(
        [(x - radius, y - radius), (x + radius, y + radius)],
        fill=fill,
        outline=outline,
        width=width,
    )


def draw_polygon(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    fill: str | None = None,
    outline: str | None = None,
) -> None:
    """Draw a filled polygon from a list of (x, y) points."""
    draw.polygon(points, fill=fill, outline=outline)
