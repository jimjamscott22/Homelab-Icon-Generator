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


def draw_media(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str
) -> None:
    """Clapperboard/play button motif for media."""
    # Outer rectangle
    bw = int(size * 0.45)
    bh = int(size * 0.35)
    draw.rectangle(
        [(cx - bw // 2, cy - bh // 2), (cx + bw // 2, cy + bh // 2)],
        fill=None,
        outline=color,
        width=int(size * 0.04),
    )
    # play triangle outline
    tw = int(size * 0.15)
    th = int(size * 0.15)
    draw_polygon(
        draw,
        [
            (cx - tw // 3, cy - th // 2),
            (cx + tw * 2 // 3, cy),
            (cx - tw // 3, cy + th // 2),
        ],
        fill=color,
    )


def draw_ai(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str
) -> None:
    """Robot/brain motif."""
    w = int(size * 0.40)
    h = int(size * 0.35)
    draw_rounded_rect(
        draw,
        [(cx - w // 2, cy - h // 2), (cx + w // 2, cy + h // 2)],
        radius=max(2, int(size * 0.05)),
        fill=None,
        outline=color,
        width=int(size * 0.04),
    )
    # eyes
    eye_w = int(size * 0.08)
    eye_h = int(size * 0.08)
    draw.rectangle(
        [(cx - w // 4 - eye_w // 2, cy - h // 4), (cx - w // 4 + eye_w // 2, cy - h // 4 + eye_h)], fill=color
    )
    draw.rectangle(
        [(cx + w // 4 - eye_w // 2, cy - h // 4), (cx + w // 4 + eye_w // 2, cy - h // 4 + eye_h)], fill=color
    )
    # mouth
    draw.line([(cx - w // 4, cy + h // 4), (cx + w // 4, cy + h // 4)], fill=color, width=max(2, int(size * 0.02)))


def draw_camera(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str
) -> None:
    """Security camera / photo camera."""
    bw = int(size * 0.46)
    bh = int(size * 0.30)
    draw_rounded_rect(
        draw,
        [(cx - bw // 2, cy - bh // 2), (cx + bw // 2, cy + bh // 2)],
        radius=max(2, int(size * 0.04)),
        fill=None, outline=color, width=int(size * 0.04)
    )
    # lens (circle in middle)
    draw_circle(draw, (cx, cy), int(size * 0.10), fill=color)
    # top flash
    draw.rectangle(
        [(cx - int(size * 0.05), cy - bh // 2 - int(size * 0.06)), (cx + int(size * 0.05), cy - bh // 2)],
        fill=color
    )


def draw_game_console(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str
) -> None:
    """Controller motif."""
    w = int(size * 0.55)
    h = int(size * 0.35)
    draw_rounded_rect(
        draw, [(cx - w // 2, cy - h // 2), (cx + w // 2, cy + h // 2)], radius=int(size * 0.1), fill=color
    )
    # D-pad (left)
    draw.line([(cx - w // 3, cy - int(size * 0.06)), (cx - w // 3, cy + int(size * 0.06))], fill=None, width=int(size * 0.02))
    # buttons (right)
    draw.circle((cx + w // 4, cy - int(size * 0.04)), int(size * 0.02), fill=None) # outline is solid color

def draw_cli(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str
) -> None:
    """Terminal prompt: '>' chevron + filled cursor block."""
    lw = max(2, int(size * 0.04))
    # chevron arrow '>'
    draw.line(
        [(cx - int(size * 0.22), cy - int(size * 0.16)),
         (cx - int(size * 0.06), cy)],
        fill=color, width=lw,
    )
    draw.line(
        [(cx - int(size * 0.06), cy),
         (cx - int(size * 0.22), cy + int(size * 0.16))],
        fill=color, width=lw,
    )
    # cursor block
    draw.rectangle(
        [(cx + int(size * 0.04), cy - int(size * 0.06)),
         (cx + int(size * 0.22), cy + int(size * 0.06))],
        fill=color,
    )


def draw_code(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str
) -> None:
    """Code brackets motif: '< / >'."""
    lw = max(2, int(size * 0.04))
    # left angle '<'
    draw.line(
        [(cx - int(size * 0.10), cy - int(size * 0.18)),
         (cx - int(size * 0.26), cy)],
        fill=color, width=lw,
    )
    draw.line(
        [(cx - int(size * 0.26), cy),
         (cx - int(size * 0.10), cy + int(size * 0.18))],
        fill=color, width=lw,
    )
    # right angle '>'
    draw.line(
        [(cx + int(size * 0.10), cy - int(size * 0.18)),
         (cx + int(size * 0.26), cy)],
        fill=color, width=lw,
    )
    draw.line(
        [(cx + int(size * 0.26), cy),
         (cx + int(size * 0.10), cy + int(size * 0.18))],
        fill=color, width=lw,
    )
    # slash '/'
    draw.line(
        [(cx - int(size * 0.07), cy + int(size * 0.20)),
         (cx + int(size * 0.07), cy - int(size * 0.20))],
        fill=color, width=lw,
    )


def draw_git_branch(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str
) -> None:
    """Git branch motif: trunk with two nodes + branch node off to the side."""
    lw = max(2, int(size * 0.03))
    node_r = int(size * 0.06)
    trunk_x = cx - int(size * 0.12)
    top = (trunk_x, cy - int(size * 0.22))
    bot = (trunk_x, cy + int(size * 0.22))
    branch = (cx + int(size * 0.20), cy)
    # trunk
    draw.line([top, bot], fill=color, width=lw)
    # branch arc (approx with diagonal line)
    draw.line([(trunk_x, cy), branch], fill=color, width=lw)
    for pt in (top, bot, branch):
        draw_circle(draw, pt, node_r, fill=color)


def draw_api(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str
) -> None:
    """Gear motif: ring + 8 rectangular teeth."""
    outer_r = int(size * 0.28)
    inner_r = int(size * 0.18)
    hole_r = int(size * 0.08)
    lw = max(2, int(size * 0.025))
    # teeth
    tw = int(size * 0.08)
    th = int(size * 0.10)
    for i in range(8):
        ang = math.radians(i * 45)
        tx = cx + int((outer_r - th // 2) * math.cos(ang))
        ty = cy + int((outer_r - th // 2) * math.sin(ang))
        draw.rectangle(
            [(tx - tw // 2, ty - th // 2), (tx + tw // 2, ty + th // 2)],
            fill=color,
        )
    # ring
    draw_circle(draw, (cx, cy), inner_r, fill=None, outline=color, width=lw)
    # hub
    draw_circle(draw, (cx, cy), hole_r, fill=color)


def draw_firewall(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str
) -> None:
    """Brick wall pattern (3 staggered rows)."""
    lw = max(2, int(size * 0.02))
    bw = int(size * 0.18)
    bh = int(size * 0.12)
    total_w = bw * 3
    left = cx - total_w // 2
    top = cy - int(bh * 1.5)
    # outer outline
    draw.rectangle(
        [(left, top), (left + total_w, top + bh * 3)],
        fill=None, outline=color, width=lw,
    )
    # row 1: 3 full bricks
    for i in range(1, 3):
        x = left + i * bw
        draw.line([(x, top), (x, top + bh)], fill=color, width=lw)
    # row 2: offset (half + 2 full + half)
    y2 = top + bh
    draw.line([(left, y2), (left + total_w, y2)], fill=color, width=lw)
    for i in (1, 2):
        x = left + bw // 2 + (i - 1) * bw
        draw.line([(x, y2), (x, y2 + bh)], fill=color, width=lw)
    x_last = left + bw // 2 + bw
    draw.line([(x_last, y2), (x_last, y2 + bh)], fill=color, width=lw)
    # row 3: 3 full bricks
    y3 = top + 2 * bh
    draw.line([(left, y3), (left + total_w, y3)], fill=color, width=lw)
    for i in range(1, 3):
        x = left + i * bw
        draw.line([(x, y3), (x, y3 + bh)], fill=color, width=lw)


def draw_vpn(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str
) -> None:
    """Shield with keyhole (lock motif)."""
    # shield polygon
    points = [
        (cx, cy - int(size * 0.28)),
        (cx + int(size * 0.24), cy - int(size * 0.16)),
        (cx + int(size * 0.20), cy + int(size * 0.18)),
        (cx, cy + int(size * 0.30)),
        (cx - int(size * 0.20), cy + int(size * 0.18)),
        (cx - int(size * 0.24), cy - int(size * 0.16)),
    ]
    draw_polygon(draw, points, fill=color)
    # keyhole (negative space — overdraw with bg-ish; use small contrasting circle)
    # keep monochrome: draw small circle as cutout-style with second smaller fill
    # Simpler: leave shield solid, no keyhole (still reads as VPN/shield).


def draw_nas(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str
) -> None:
    """Stacked disk bays (3 horizontal slots with status dots)."""
    bw = int(size * 0.55)
    bh = int(size * 0.12)
    gap = int(size * 0.04)
    total_h = 3 * bh + 2 * gap
    top = cy - total_h // 2
    radius = max(2, int(size * 0.02))
    dot_r = int(size * 0.025)
    for i in range(3):
        y = top + i * (bh + gap)
        draw_rounded_rect(
            draw,
            [(cx - bw // 2, y), (cx + bw // 2, y + bh)],
            radius=radius,
            fill=None, outline=color, width=max(2, int(size * 0.02)),
        )
        # status dot on the right
        draw_circle(
            draw,
            (cx + bw // 2 - int(size * 0.06), y + bh // 2),
            dot_r, fill=color,
        )


def draw_power(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: str
) -> None:
    """Power button: arc with vertical bar through the gap at top."""
    r = int(size * 0.26)
    lw = max(2, int(size * 0.05))
    # arc from 30° to 330° (gap at top)
    draw.arc(
        [(cx - r, cy - r), (cx + r, cy + r)],
        start=300, end=240,
        fill=color, width=lw,
    )
    # vertical bar
    draw.line(
        [(cx, cy - r - int(size * 0.04)), (cx, cy - int(size * 0.02))],
        fill=color, width=lw,
    )


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
    "media": draw_media,
    "ai": draw_ai,
    "camera": draw_camera,
    "game_console": draw_game_console,
    "cli": draw_cli,
    "code": draw_code,
    "git_branch": draw_git_branch,
    "api": draw_api,
    "firewall": draw_firewall,
    "vpn": draw_vpn,
    "nas": draw_nas,
    "power": draw_power,
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
