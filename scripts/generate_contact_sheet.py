"""Generate a deterministic representative icon contact sheet."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Sequence

from PIL import Image

from app.generator.renderer import generate_icon_result
from app.icons.resolver import IconResolver, build_resolver
from app.models.icon_request import IconRequest


def representative_cases(*, include_custom: bool) -> tuple[IconRequest, ...]:
    """Return brand, optional custom, and forced-generic visual samples."""
    custom_icon = "internal-api" if include_custom else "generic"
    return (
        IconRequest(
            "Nextcloud",
            "cloud_service",
            style="minimal",
            theme="blue",
            icon="nextcloud",
        ),
        IconRequest(
            "Internal API",
            "api",
            style="terminal",
            theme="green",
            icon=custom_icon,
        ),
        IconRequest(
            "Unknown NAS",
            "nas",
            style="cyberpunk",
            theme="purple",
            icon="generic",
        ),
    )


def generate_contact_sheet(
    output: Path,
    cases: Sequence[IconRequest],
    cell_size: int,
    resolver: IconResolver,
) -> Image.Image:
    """Render cases into one horizontal, transparent RGBA validation sheet."""
    if not cases:
        raise ValueError("contact sheet requires at least one icon request")
    if cell_size < 32:
        raise ValueError("cell_size must be at least 32 pixels")

    sheet = Image.new("RGBA", (cell_size * len(cases), cell_size), (0, 0, 0, 0))
    with TemporaryDirectory(prefix="homelab-contact-sheet-") as temp_dir:
        for index, request in enumerate(cases):
            rendered_request = replace(
                request,
                size=cell_size,
                format="png",
                transparent_bg=False,
                output_dir=temp_dir,
            )
            result = generate_icon_result(rendered_request, resolver=resolver)
            with Image.open(result.paths["png"]) as rendered:
                sheet.alpha_composite(rendered.convert("RGBA"), (index * cell_size, 0))

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, format="PNG")
    return sheet


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("output/contact-sheet.png"))
    parser.add_argument("--cell-size", type=int, default=128)
    parser.add_argument("--icon-dir", type=str, default=None)
    args = parser.parse_args()
    resolver = build_resolver(args.icon_dir)
    sheet = generate_contact_sheet(
        args.output,
        representative_cases(include_custom=args.icon_dir is not None),
        args.cell_size,
        resolver,
    )
    print(f"Wrote {sheet.width}x{sheet.height} contact sheet to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
