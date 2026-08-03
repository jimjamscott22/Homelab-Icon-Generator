"""Device-oriented generic icon definitions."""

from app.icons.generic._helpers import circle, icon, line, rect


LAPTOP = icon(
    "laptop",
    "Laptop",
    rect(25, 30, 50, 32, rx=2),
    rect(21, 64, 58, 6, rx=1),
)

DESKTOP = icon(
    "desktop",
    "Desktop",
    rect(36, 26, 28, 48, rx=2),
    rect(32, 74, 36, 5, rx=1),
)

PHONE = icon("phone", "Phone", rect(36, 25, 28, 50, rx=6))

CAMERA = icon(
    "camera",
    "Camera",
    rect(27, 35, 46, 30, rx=4, fill="none", stroke="currentColor", stroke_width=4),
    circle(50, 50, 10),
    rect(45, 29, 10, 6),
)

GAME_CONSOLE = icon(
    "game_console",
    "Game Console",
    rect(22.5, 32.5, 55, 35, rx=10, fill="none", stroke="currentColor", stroke_width=4),
    line(34, 50, 46, 50, 3),
    line(40, 44, 40, 56, 3),
    circle(62, 47, 3),
    circle(68, 53, 3),
)

DEVICE_ICONS = {
    item.key: item for item in (LAPTOP, DESKTOP, PHONE, CAMERA, GAME_CONSOLE)
}
