"""CLI entry point for the Homelab Icon Generator."""

import argparse
import json
import sys

from app.generator.renderer import generate_icon
from app.models.icon_request import IconRequest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate homelab icons for devices and services.",
    )

    parser.add_argument("--name", type=str, default=None, help="Device/service name")
    parser.add_argument("--category", type=str, default=None, help="One of the 12 valid categories")
    parser.add_argument("--style", type=str, default="minimal", help="minimal / terminal / cyberpunk")
    parser.add_argument("--theme", type=str, default="blue", help="green / blue / orange / purple / grayscale")
    parser.add_argument("--size", type=int, default=256, help="Icon size in pixels")
    parser.add_argument("--format", type=str, default="both", help="png / svg / both")
    parser.add_argument("--output-dir", type=str, default="output", help="Output directory")
    parser.add_argument("--transparent", action="store_true", default=False, help="Enable transparent background")
    parser.add_argument("--batch", type=str, default=None, help="Path to JSON batch file")

    return parser, parser.parse_args()


def run_single(args: argparse.Namespace) -> None:
    request = IconRequest(
        name=args.name,
        category=args.category,
        style=args.style,
        theme=args.theme,
        size=args.size,
        format=args.format,
        transparent_bg=args.transparent,
        output_dir=args.output_dir,
    )
    try:
        paths = generate_icon(request)
        for fmt, path in paths.items():
            print(f"  [{fmt.upper()}] {path}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def run_batch(json_path: str, output_dir: str) -> None:
    """Load a JSON array of icon configs and generate each one."""
    with open(json_path) as f:
        entries = json.load(f)

    succeeded, failed = 0, 0
    for i, entry in enumerate(entries):
        name = entry.get("name", f"entry-{i}")
        try:
            request = IconRequest(
                name=name,
                category=entry["category"],
                style=entry.get("style", "minimal"),
                theme=entry.get("theme", "blue"),
                size=entry.get("size", 256),
                format=entry.get("format", "both"),
                transparent_bg=entry.get("transparent_bg", False),
                output_dir=entry.get("output_dir", output_dir),
            )
            paths = generate_icon(request)
            print(f"  [OK] {name}")
            for fmt, path in paths.items():
                print(f"    [{fmt.upper()}] {path}")
            succeeded += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}", file=sys.stderr)
            failed += 1

    print(f"\nBatch complete: {succeeded} succeeded, {failed} failed")


def main() -> None:
    parser, args = parse_args()

    if args.batch:
        run_batch(args.batch, args.output_dir)
    elif args.name and args.category:
        run_single(args)
    else:
        parser.error("Provide --name and --category, or --batch <file>")


if __name__ == "__main__":
    main()
