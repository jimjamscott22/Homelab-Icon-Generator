"""Software and service generic icon definitions."""

from __future__ import annotations

import math

from app.icons.generic._helpers import circle, ellipse, icon, line, path, polygon, rect
from app.icons.models import VectorNode


def _arc(radius: float) -> VectorNode:
    offset = radius * math.sqrt(0.5)
    return path(
        f"M {50 - offset:.3f} {50 - offset:.3f} "
        f"A {radius} {radius} 0 0 1 {50 + offset:.3f} {50 - offset:.3f}",
        fill="none",
        stroke="currentColor",
        stroke_width=2.5,
        linecap="round",
    )


IOT = icon("iot", "IoT", _arc(28), _arc(20), _arc(12), circle(50, 50, 4))

CONTAINER = icon(
    "container",
    "Container",
    rect(26, 26, 48, 48, rx=2, fill="none", stroke="currentColor", stroke_width=2.5),
    line(50, 28.5, 50, 71.5, 2.5, linecap="butt"),
    line(28.5, 50, 71.5, 50, 2.5, linecap="butt"),
)

DATABASE = icon(
    "database",
    "Database",
    rect(29, 41, 42, 30),
    ellipse(50, 71, 21, 6),
    ellipse(50, 35, 21, 6),
)

CLOUD_SERVICE = icon(
    "cloud_service",
    "Cloud Service",
    circle(36, 54, 14),
    circle(50, 54, 14),
    circle(64, 54, 14),
    circle(50, 44, 11),
)

_hex_points = " ".join(
    f"{50 + 28 * math.cos(math.radians(60 * index - 30)):.3f},"
    f"{50 + 28 * math.sin(math.radians(60 * index - 30)):.3f}"
    for index in range(6)
)
GENERIC_SERVICE = icon("generic_service", "Generic Service", polygon(_hex_points))

MEDIA = icon(
    "media",
    "Media",
    rect(27.5, 32.5, 45, 35, fill="none", stroke="currentColor", stroke_width=4),
    polygon("45,42.5 60,50 45,57.5"),
)

AI = icon(
    "ai",
    "Artificial Intelligence",
    rect(30, 32.5, 40, 35, rx=5, fill="none", stroke="currentColor", stroke_width=4),
    rect(36, 41, 8, 8),
    rect(56, 41, 8, 8),
    line(40, 59, 60, 59, 2),
)

CLI = icon(
    "cli",
    "Command Line",
    line(28, 34, 44, 50, 4),
    line(44, 50, 28, 66, 4),
    rect(54, 44, 18, 12),
)

CODE = icon(
    "code",
    "Code",
    line(40, 32, 24, 50, 4),
    line(24, 50, 40, 68, 4),
    line(60, 32, 76, 50, 4),
    line(76, 50, 60, 68, 4),
    line(43, 70, 57, 30, 4),
)

GIT_BRANCH = icon(
    "git_branch",
    "Git Branch",
    line(38, 28, 38, 72, 3),
    line(38, 50, 70, 50, 3),
    circle(38, 28, 6),
    circle(38, 72, 6),
    circle(70, 50, 6),
)

_gear_teeth = []
for index in range(8):
    angle = math.radians(index * 45)
    x = 50 + 23 * math.cos(angle)
    y = 50 + 23 * math.sin(angle)
    _gear_teeth.append(rect(x - 4, y - 5, 8, 10))
API = icon(
    "api",
    "API",
    *_gear_teeth,
    circle(50, 50, 18, fill="none", stroke="currentColor", stroke_width=2.5),
    circle(50, 50, 8),
)

VPN = icon(
    "vpn",
    "VPN",
    polygon("50,22 74,34 70,68 50,80 30,68 26,34"),
)

SERVICE_ICONS = {
    item.key: item
    for item in (
        IOT,
        CONTAINER,
        DATABASE,
        CLOUD_SERVICE,
        GENERIC_SERVICE,
        MEDIA,
        AI,
        CLI,
        CODE,
        GIT_BRANCH,
        API,
        VPN,
    )
}
