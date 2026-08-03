"""Build the application's deterministic offline Simple Icons catalog."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tarfile
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from defusedxml import ElementTree


NPM_TARBALL = "https://registry.npmjs.org/simple-icons/-/simple-icons-{version}.tgz"


@dataclass(frozen=True)
class CatalogSyncResult:
    """Paths and counts produced by one successful catalog sync."""

    catalog_path: Path
    manifest_path: Path
    notice_path: Path
    icon_count: int


def _write_json(path: Path, payload: object) -> bytes:
    data = (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )
    path.write_bytes(data)
    return data


def _alias_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _alias_strings(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            if key in {"aka", "old", "dup", "loc", "title"}:
                yield from _alias_strings(item)


def _svg_geometry(svg_path: Path) -> tuple[list[float], str]:
    root = ElementTree.parse(svg_path).getroot()
    view_box = [float(value) for value in root.attrib.get("viewBox", "").split()]
    if len(view_box) != 4 or view_box[2] <= 0 or view_box[3] <= 0:
        raise ValueError(f"Invalid viewBox in {svg_path}")

    paths = [
        element.attrib.get("d", "").strip()
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == "path"
    ]
    if len(paths) != 1 or not paths[0]:
        raise ValueError(f"Expected exactly one non-empty path in {svg_path}")
    return view_box, paths[0]


def _load_reviewed_aliases(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not all(
        isinstance(alias, str) and isinstance(target, str)
        for alias, target in payload.items()
    ):
        raise ValueError("Reviewed aliases must be a JSON object of alias-to-slug strings")
    return payload


def _license_name(record: dict[str, Any]) -> str | None:
    license_data = record.get("license")
    if isinstance(license_data, str):
        return license_data
    if isinstance(license_data, dict) and isinstance(license_data.get("type"), str):
        return license_data["type"]
    return None


def _build_notice(version: str, icon_count: int) -> str:
    return f"""# Third-party icons

This application bundles {icon_count} icon paths from Simple Icons {version} for
offline lookup. Simple Icons is licensed under CC0-1.0; individual brands may
have additional terms. Source URLs, brand guidelines, and explicit per-icon
license identifiers are retained in `app/icons/data/simple-icons.json`.

- Project: https://simpleicons.org/
- Package: https://www.npmjs.com/package/simple-icons/v/{version}
- Disclaimer: https://github.com/simple-icons/simple-icons/blob/{version}/DISCLAIMER.md

All product names, logos, and brands remain property of their respective owners.
"""


def sync_catalog(
    source_dir: Path,
    version: str,
    output_dir: Path,
    aliases_path: Path | None = None,
    *,
    notice_path: Path | None = None,
    archive_sha256: str | None = None,
) -> CatalogSyncResult:
    """Convert an extracted Simple Icons package into bundled application data."""
    source_dir = Path(source_dir)
    output_dir = Path(output_dir)
    metadata_path = source_dir / "data" / "simple-icons.json"
    icons_dir = source_dir / "icons"
    records = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("Simple Icons metadata must be a JSON array")

    reviewed_aliases = _load_reviewed_aliases(aliases_path)
    slugs = {record.get("slug") for record in records if isinstance(record, dict)}
    missing_targets = sorted(set(reviewed_aliases.values()) - slugs)
    if missing_targets:
        raise ValueError(
            "Reviewed aliases target missing icon(s): " + ", ".join(missing_targets)
        )

    aliases_by_slug: dict[str, list[str]] = {}
    for alias, slug in reviewed_aliases.items():
        aliases_by_slug.setdefault(slug, []).append(alias)

    icons: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Each Simple Icons record must be a JSON object")
        slug = record.get("slug")
        title = record.get("title")
        source_url = record.get("source")
        if not all(isinstance(value, str) and value for value in (slug, title, source_url)):
            raise ValueError("Every icon requires non-empty slug, title, and source")

        view_box, path_data = _svg_geometry(icons_dir / f"{slug}.svg")
        aliases = set(_alias_strings(record.get("aliases", {})))
        aliases.update(aliases_by_slug.get(slug, []))
        icon: dict[str, Any] = {
            "aliases": sorted(aliases, key=lambda value: (value.casefold(), value)),
            "guidelines_url": record.get("guidelines"),
            "key": slug,
            "license": _license_name(record),
            "path": path_data,
            "source_url": source_url,
            "title": title,
            "view_box": view_box,
        }
        icons.append(icon)

    icons.sort(key=lambda icon: icon["key"])
    output_dir.mkdir(parents=True, exist_ok=True)
    catalog_path = output_dir / "simple-icons.json"
    catalog_bytes = _write_json(
        catalog_path,
        {"catalog": "simple-icons", "icons": icons, "version": version},
    )
    content_sha256 = hashlib.sha256(catalog_bytes).hexdigest()
    manifest_path = output_dir / "catalog-manifest.json"
    _write_json(
        manifest_path,
        {
            "archive_sha256": archive_sha256,
            "catalog": "simple-icons",
            "content_sha256": content_sha256,
            "icon_count": len(icons),
            "source_url": NPM_TARBALL.format(version=version),
            "version": version,
        },
    )

    resolved_notice = notice_path or output_dir / "THIRD_PARTY_ICONS.md"
    resolved_notice.parent.mkdir(parents=True, exist_ok=True)
    resolved_notice.write_text(_build_notice(version, len(icons)), encoding="utf-8")
    return CatalogSyncResult(catalog_path, manifest_path, resolved_notice, len(icons))


def _safe_extract(archive: Path, destination: Path) -> Path:
    destination = destination.resolve()
    with tarfile.open(archive, "r:gz") as package:
        for member in package.getmembers():
            target = (destination / member.name).resolve()
            if destination != target and destination not in target.parents:
                raise ValueError(f"Unsafe archive member: {member.name}")
        package.extractall(destination)
    return destination / "package"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--aliases", type=Path)
    parser.add_argument("--notice", type=Path)
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    if args.source_dir and args.archive:
        parser.error("use either --source-dir or --archive, not both")

    with tempfile.TemporaryDirectory(prefix="homelab-simple-icons-") as temp_name:
        temp_dir = Path(temp_name)
        archive = args.archive
        if args.source_dir:
            source_dir = args.source_dir
            digest = None
        else:
            if archive is None:
                archive = temp_dir / f"simple-icons-{args.version}.tgz"
                urllib.request.urlretrieve(NPM_TARBALL.format(version=args.version), archive)
            copied_archive = temp_dir / archive.name
            if archive.resolve() != copied_archive.resolve():
                shutil.copyfile(archive, copied_archive)
            archive = copied_archive
            digest = _sha256(archive)
            source_dir = _safe_extract(archive, temp_dir / "extracted")

        result = sync_catalog(
            source_dir,
            args.version,
            args.output,
            args.aliases,
            notice_path=args.notice,
            archive_sha256=digest,
        )
    print(f"Wrote {result.icon_count} icons to {result.catalog_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
