def _svg_media(cx: int, cy: int, size: int, color: str) -> str:
    bw = int(size * 0.45)
    bh = int(size * 0.35)
    tw = int(size * 0.15)
    th = int(size * 0.15)
    points = [
        (cx - tw // 3, cy - th // 2),
        (cx + tw * 2 // 3, cy),
        (cx - tw // 3, cy + th // 2),
    ]
    return "\n".join([
        _svg_rect(cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2, fill="none") + " stroke=\"" + color + "\" stroke-width=\"" + str(int(size * 0.04)) + "\"",
        _svg_polygon(points, fill=color)
    ])

def _svg_ai(cx: int, cy: int, size: int, color: str) -> str:
    w = int(size * 0.40)
    h = int(size * 0.35)
    elements = [
        _svg_rounded_rect(cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2, max(2, int(size * 0.05)), fill="none", stroke=color, stroke_width=int(size * 0.04)),
        _svg_rect(cx - w // 4 - int(size * 0.04), cy - h // 4, cx - w // 4 + int(size * 0.04), cy - h // 4 + int(size * 0.08), fill=color),
        _svg_rect(cx + w // 4 - int(size * 0.04), cy - h // 4, cx + w // 4 + int(size * 0.04), cy - h // 4 + int(size * 0.08), fill=color),
        _svg_line(cx - w // 4, cy + h // 4, cx + w // 4, cy + h // 4, stroke=color, width=max(2, int(size * 0.02)))
    ]
    return "\n".join(elements)

def _svg_camera(cx: int, cy: int, size: int, color: str) -> str:
    bw = int(size * 0.46)
    bh = int(size * 0.30)
    elements = [
        _svg_rounded_rect(cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2, max(2, int(size * 0.04)), fill="none", stroke=color, stroke_width=int(size * 0.04)),
        _svg_circle(cx, cy, int(size * 0.10), fill=color),
        _svg_rect(cx - int(size * 0.05), cy - bh // 2 - int(size * 0.06), cx + int(size * 0.05), cy - bh // 2, fill=color)
    ]
    return "\n".join(elements)

def _svg_game_console(cx: int, cy: int, size: int, color: str) -> str:
    w = int(size * 0.55)
    h = int(size * 0.35)
    elements = [
        _svg_rounded_rect(cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2, int(size * 0.1), fill=color),
        _svg_line(cx - w // 3, cy - int(size * 0.06), cx - w // 3, cy + int(size * 0.06), stroke="white", width=int(size * 0.02)),
        _svg_circle(cx + w // 4, cy - int(size * 0.04), int(size * 0.02), fill="white")
    ]
    return "\n".join(elements)
