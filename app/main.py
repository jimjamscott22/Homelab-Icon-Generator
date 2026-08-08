"""CLI entry point for the Homelab Icon Generator."""

import argparse
import json
import sys
from typing import Any, Iterator

from app.generator.renderer import generate_icon
from app.icons.resolver import build_resolver
from app.models.icon_request import IconRequest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate homelab icons for devices and services.",
        epilog="Run with no arguments to open the web UI.",
    )

    parser.add_argument("--name", type=str, default=None, help="Device/service name")
    parser.add_argument("--category", type=str, default=None, help="One of the 12 valid categories")
    parser.add_argument("--style", type=str, default="minimal", help="minimal / terminal / cyberpunk")
    parser.add_argument("--theme", type=str, default="blue", help="green / blue / orange / purple / grayscale / custom")
    parser.add_argument(
        "--custom-color",
        type=str,
        default=None,
        help='Custom theme color as "#RRGGBB" (requires --theme custom)',
    )
    parser.add_argument("--size", type=int, default=256, help="Icon size in pixels")
    parser.add_argument("--format", type=str, default="both", help="png / svg / both")
    parser.add_argument(
        "--icon",
        type=str,
        default="auto",
        help="auto / generic / stable icon key such as nextcloud",
    )
    parser.add_argument("--output-dir", type=str, default="output", help="Output directory")
    parser.add_argument("--transparent", action="store_true", default=False, help="Enable transparent background")
    parser.add_argument("--batch", type=str, default=None, help="Path to JSON batch file")
    parser.add_argument(
        "--icon-dir",
        type=str,
        default=None,
        help="Directory containing custom icon manifest.json and SVG files",
    )

    return parser, parser.parse_args()


def run_single(args: argparse.Namespace) -> None:
    request = IconRequest(
        name=args.name,
        category=args.category,
        style=args.style,
        theme=args.theme,
        custom_color=getattr(args, "custom_color", None),
        size=args.size,
        format=args.format,
        icon=args.icon,
        transparent_bg=args.transparent,
        output_dir=args.output_dir,
    )
    try:
        icon_dir = getattr(args, "icon_dir", None)
        resolver = build_resolver(icon_dir) if icon_dir else None
        paths = (
            generate_icon(request, resolver=resolver)
            if resolver is not None
            else generate_icon(request)
        )
        for fmt, path in paths.items():
            print(f"  [{fmt.upper()}] {path}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _iter_batch_entries(json_path: str) -> Iterator[dict[str, Any]]:
    """Yield icon entries from JSON array files or NDJSON files."""
    with open(json_path, encoding="utf-8") as f:
        first = ""
        for chunk in iter(lambda: f.read(1024), ""):
            for ch in chunk:
                if not ch.isspace():
                    first = ch
                    break
            if first:
                break
        if not first:
            return
        f.seek(0)

        if first == "[":
            entries = json.load(f)
            for entry in entries:
                if isinstance(entry, dict):
                    yield entry
            return

        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            entry = json.loads(stripped)
            if isinstance(entry, dict):
                yield entry


def run_batch(json_path: str, output_dir: str, icon_dir: str | None = None) -> None:
    """Load a batch file and generate each icon entry."""

    succeeded, failed = 0, 0
    for i, entry in enumerate(_iter_batch_entries(json_path)):
        name = entry.get("name", f"entry-{i}")
        try:
            request = IconRequest(
                name=name,
                category=entry["category"],
                style=entry.get("style", "minimal"),
                theme=entry.get("theme", "blue"),
                custom_color=entry.get("custom_color"),
                size=entry.get("size", 256),
                format=entry.get("format", "both"),
                icon=entry.get("icon", "auto"),
                transparent_bg=entry.get("transparent_bg", False),
                output_dir=entry.get("output_dir", output_dir),
            )
            resolver = build_resolver(icon_dir) if icon_dir else None
            paths = (
                generate_icon(request, resolver=resolver)
                if resolver is not None
                else generate_icon(request)
            )
            print(f"  [OK] {name}")
            for fmt, path in paths.items():
                print(f"    [{fmt.upper()}] {path}")
            succeeded += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}", file=sys.stderr)
            failed += 1

    print(f"\nBatch complete: {succeeded} succeeded, {failed} failed")


def main() -> None:
    # No arguments: this is a web-first tool, so open the UI.
    if len(sys.argv) == 1:
        from app.web.launcher import run

        raise SystemExit(run())

    parser, args = parse_args()

    if args.batch:
        run_batch(args.batch, args.output_dir, args.icon_dir)
    elif args.name and args.category:
        run_single(args)
    else:
        parser.error("Provide --name and --category, or --batch <file>")


if __name__ == "__main__":
    main()
