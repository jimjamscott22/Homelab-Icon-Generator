import math
from typing import Callable

from PIL import ImageDraw

from app.generator.shapes import draw_circle, draw_polygon, draw_rounded_rect


# ---------------------------------------------------------------------------
# Individual symbol draw functions
# All functions share the same signature:
#   draw_*(draw, cx, cy, size, color) -> None
#
# cx, cy  – center of the canvas in pixels
# size    – canvas side length (e.g. 256)
# color   – hex fill/stroke color string
#
# All coordinates are derived as fractions of `size` so they scale correctly.
# ---------------------------------------------------------------------------


def draw_raspberry_pi(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str
) -> None:
    """Circuit-board motif: rounded rect body + four corner pin dots."""
    r = int(size * 0.28)
    radius = int(size * 0.06)
    draw_rounded_rect(
        draw, [(cx - r, cy - r), (cx + r, cy + r)], radius=radius, fill=color
    )
    pin_r = int(size * 0.04)
    offset = int(size * 0.22)
    for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
        draw_circle(
            draw, (cx + dx * offset, cy + dy * offset), pin_r, fill=color
        )


def draw_server(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str
) -> None:
    """Three horizontal bars representing rack units."""
    bar_h = int(size * 0.10)
    bar_w = int(size * 0.55)
    gap = int(size * 0.04)
    total = 3 * bar_h + 2 * gap
    top = cy - total // 2
    for i in range(3):
        y = top + i * (bar_h + gap)
        draw_rounded_rect(
            draw,
            [(cx - bar_w // 2, y), (cx + bar_w // 2, y + bar_h)],
            radius=max(2, int(size * 0.01)),
            fill=color,
        )


def draw_router(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str
) -> None:
    """Horizontal box body with three vertical antenna stubs on top."""
    bw = int(size * 0.50)
    bh = int(size * 0.18)
    draw_rounded_rect(
        draw,
        [(cx - bw // 2, cy - bh // 2), (cx + bw // 2, cy + bh // 2)],
        radius=max(2, int(size * 0.02)),
        fill=color,
    )
    ant_h = int(size * 0.20)
    ant_w = max(2, int(size * 0.04))
    for dx in [-int(size * 0.15), 0, int(size * 0.15)]:
        x = cx + dx
        draw.rectangle(
            [
                (x - ant_w // 2, cy - bh // 2 - ant_h),
                (x + ant_w // 2, cy - bh // 2),
            ],
            fill=color,
        )


def draw_switch(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str
) -> None:
    """3x2 grid of port rectangles."""
    pw = int(size * 0.12)
    ph = int(size * 0.12)
    gap = int(size * 0.04)
    cols, rows = 3, 2
    total_w = cols * pw + (cols - 1) * gap
    total_h = rows * ph + (rows - 1) * gap
    ox = cx - total_w // 2
    oy = cy - total_h // 2
    for row in range(rows):
        for col in range(cols):
            x = ox + col * (pw + gap)
            y = oy + row * (ph + gap)
            draw_rounded_rect(
                draw, [(x, y), (x + pw, y + ph)], radius=max(2, int(size * 0.01)), fill=color
            )


def draw_laptop(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str
) -> None:
    """Screen (rounded rect) + wide base bar below."""
    sw = int(size * 0.50)
    sh = int(size * 0.32)
    screen_top = cy - sh // 2 - int(size * 0.04)
    draw_rounded_rect(
        draw,
        [(cx - sw // 2, screen_top), (cx + sw // 2, screen_top + sh)],
        radius=max(2, int(size * 0.02)),
        fill=color,
    )
    bw = int(size * 0.58)
    bh = int(size * 0.06)
    base_y = screen_top + sh + int(size * 0.02)
    draw_rounded_rect(
        draw,
        [(cx - bw // 2, base_y), (cx + bw // 2, base_y + bh)],
        radius=max(2, int(size * 0.01)),
        fill=color,
    )


def draw_desktop(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str
) -> None:
    """Tall tower rectangle with a wide base/stand at the bottom."""
    tw = int(size * 0.28)
    th = int(size * 0.48)
    draw_rounded_rect(
        draw,
        [(cx - tw // 2, cy - th // 2), (cx + tw // 2, cy + th // 2)],
        radius=max(2, int(size * 0.02)),
        fill=color,
    )
    bw = int(size * 0.36)
    bh = int(size * 0.05)
    base_y = cy + th // 2
    draw_rounded_rect(
        draw,
        [(cx - bw // 2, base_y), (cx + bw // 2, base_y + bh)],
        radius=max(2, int(size * 0.01)),
        fill=color,
    )


def draw_phone(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str
) -> None:
    """Vertical rounded rectangle representing a mobile/VOIP handset."""
    w = int(size * 0.28)
    h = int(size * 0.50)
    draw_rounded_rect(
        draw,
        [(cx - w // 2, cy - h // 2), (cx + w // 2, cy + h // 2)],
        radius=int(size * 0.06),
        fill=color,
    )


def draw_iot(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str
) -> None:
    """Concentric arc rings (sensor/wave motif) with a center dot."""
    lw = max(2, int(size * 0.025))
    for r in [int(size * 0.28), int(size * 0.20), int(size * 0.12)]:
        draw.arc(
            [(cx - r, cy - r), (cx + r, cy + r)],
            start=45,
            end=135,
            fill=color,
            width=lw,
        )
    draw_circle(draw, (cx, cy), int(size * 0.04), fill=color)


def draw_container(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str
) -> None:
    """Outer box with inner 2x2 grid dividers (container/pod motif)."""
    s = int(size * 0.48)
    lw = max(2, int(size * 0.025))
    draw_rounded_rect(
        draw,
        [(cx - s // 2, cy - s // 2), (cx + s // 2, cy + s // 2)],
        radius=max(2, int(size * 0.02)),
        fill=None,
        outline=color,
        width=lw,
    )
    # vertical divider
    draw.line(
        [(cx, cy - s // 2 + lw), (cx, cy + s // 2 - lw)],
        fill=color,
        width=lw,
    )
    # horizontal divider
    draw.line(
        [(cx - s // 2 + lw, cy), (cx + s // 2 - lw, cy)],
        fill=color,
        width=lw,
    )


def draw_database(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str
) -> None:
    """Cylinder shape: rect body capped with top and bottom ellipses."""
    ew = int(size * 0.42)
    eh = int(size * 0.12)
    body_h = int(size * 0.30)
    top_y = cy - body_h // 2

    # Rectangular body (drawn between ellipse mid-points to avoid gaps)
    draw.rectangle(
        [
            (cx - ew // 2, top_y + eh // 2),
            (cx + ew // 2, top_y + eh // 2 + body_h),
        ],
        fill=color,
    )
    # Bottom ellipse cap
    draw.ellipse(
        [
            (cx - ew // 2, top_y + eh // 2 + body_h - eh // 2),
            (cx + ew // 2, top_y + eh // 2 + body_h + eh // 2),
        ],
        fill=color,
    )
    # Top ellipse cap (drawn last so it sits on top of the body)
    draw.ellipse(
        [(cx - ew // 2, top_y), (cx + ew // 2, top_y + eh)],
        fill=color,
    )


def draw_cloud_service(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str
) -> None:
    """Three overlapping circles in a row + one larger bubble on top."""
    r = int(size * 0.14)
    base_cy = cy + int(size * 0.04)
    for dx in [-int(size * 0.14), 0, int(size * 0.14)]:
        draw_circle(draw, (cx + dx, base_cy), r, fill=color)
    # Top-center puff
    draw_circle(draw, (cx, base_cy - int(size * 0.10)), int(size * 0.11), fill=color)


def draw_generic_service(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str
) -> None:
    """Regular hexagon as a generic service/app icon."""
    r = int(size * 0.28)
    points = [
        (
            int(cx + r * math.cos(math.radians(60 * i - 30))),
            int(cy + r * math.sin(math.radians(60 * i - 30))),
        )
        for i in range(6)
    ]
    draw_polygon(draw, points, fill=color)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

SYMBOL_DRAWERS: dict[str, Callable] = {
    "raspberry_pi": draw_raspberry_pi,
    "server": draw_server,
    "router": draw_router,
    "switch": draw_switch,
    "laptop": draw_laptop,
    "desktop": draw_desktop,
    "phone": draw_phone,
    "iot": draw_iot,
    "container": draw_container,
    "database": draw_database,
    "cloud_service": draw_cloud_service,
    "generic_service": draw_generic_service,
}


def draw_symbol(
    category: str,
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    size: int,
    color: str,
) -> None:
    """Dispatch to the correct symbol drawing function by category.

    Falls back to ``draw_generic_service`` for unknown category names.
    """
    fn = SYMBOL_DRAWERS.get(category)
    if fn is None:
        draw_generic_service(draw, cx, cy, size, color)
    else:
        fn(draw, cx, cy, size, color)
