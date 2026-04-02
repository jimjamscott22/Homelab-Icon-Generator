from dataclasses import dataclass


@dataclass
class LayoutSpec:
    symbol_cx: int      # center x for symbol drawing
    symbol_cy: int      # center y for symbol drawing
    symbol_size: int    # size parameter passed to draw_symbol
    show_initials: bool
    initials_cx: int    # center x for initials text
    initials_cy: int    # center y for initials text
    font_size: int      # target font size in pixels


def get_layout(size: int, font_scale: float = 1.0) -> LayoutSpec:
    """Compute layout for a square canvas of ``size`` pixels.

    The symbol is centered slightly above the canvas midpoint so there is
    room for the initials label below.  When ``size`` is smaller than 64 px
    the initials are omitted and the symbol is centered instead.
    """
    show = size >= 64
    symbol_cy = int(size * 0.42) if show else size // 2
    initials_cy = int(size * 0.78)
    font_size = max(8, int(size * 0.14 * font_scale))
    return LayoutSpec(
        symbol_cx=size // 2,
        symbol_cy=symbol_cy,
        symbol_size=size,
        show_initials=show,
        initials_cx=size // 2,
        initials_cy=initials_cy,
        font_size=font_size,
    )
