"""Infrastructure-oriented generic icon definitions."""

from __future__ import annotations

import math

from app.icons.generic._helpers import circle, icon, line, path, rect


RASPBERRY_PI = icon(
    "raspberry_pi",
    "Raspberry Pi",
    rect(22, 22, 56, 56, rx=6),
    *(circle(x, y, 4) for x in (28, 72) for y in (28, 72)),
)

SERVER = icon(
    "server",
    "Server",
    *(rect(22.5, y, 55, 10, rx=1) for y in (31, 45, 59)),
)

ROUTER = icon(
    "router",
    "Router",
    rect(25, 41, 50, 18, rx=2),
    *(rect(x - 2, 21, 4, 20) for x in (35, 50, 65)),
)

SWITCH = icon(
    "switch",
    "Network Switch",
    *(
        rect(28 + column * 16, 36 + row * 16, 12, 12, rx=1)
        for row in range(2)
        for column in range(3)
    ),
)

FIREWALL = icon(
    "firewall",
    "Firewall",
    rect(23, 32, 54, 36, fill="none", stroke="currentColor", stroke_width=2),
    line(41, 32, 41, 44, 2, linecap="butt"),
    line(59, 32, 59, 44, 2, linecap="butt"),
    line(23, 44, 77, 44, 2, linecap="butt"),
    line(32, 44, 32, 56, 2, linecap="butt"),
    line(50, 44, 50, 56, 2, linecap="butt"),
    line(68, 44, 68, 56, 2, linecap="butt"),
    line(23, 56, 77, 56, 2, linecap="butt"),
    line(41, 56, 41, 68, 2, linecap="butt"),
    line(59, 56, 59, 68, 2, linecap="butt"),
)

NAS = icon(
    "nas",
    "Network Attached Storage",
    *(
        node
        for y in (31, 47, 63)
        for node in (
            rect(22.5, y, 55, 12, rx=2, fill="none", stroke="currentColor", stroke_width=2),
            circle(71.5, y + 6, 2.5),
        )
    ),
)

_power_radius = 26
_power_start = (
    50 + _power_radius * math.cos(math.radians(300)),
    50 + _power_radius * math.sin(math.radians(300)),
)
_power_end = (
    50 + _power_radius * math.cos(math.radians(240)),
    50 + _power_radius * math.sin(math.radians(240)),
)
POWER = icon(
    "power",
    "Power",
    path(
        f"M {_power_start[0]:.3f} {_power_start[1]:.3f} "
        f"A {_power_radius} {_power_radius} 0 1 1 {_power_end[0]:.3f} {_power_end[1]:.3f}",
        fill="none",
        stroke="currentColor",
        stroke_width=5,
        linecap="round",
    ),
    line(50, 20, 50, 48, 5),
)

INFRASTRUCTURE_ICONS = {
    item.key: item
    for item in (RASPBERRY_PI, SERVER, ROUTER, SWITCH, FIREWALL, NAS, POWER)
}
