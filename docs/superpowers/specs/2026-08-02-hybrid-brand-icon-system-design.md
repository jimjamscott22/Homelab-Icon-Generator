# Hybrid Brand and Generic Icon System Design

**Status:** Implemented on `codex/hybrid-brand-icon-system` on 2026-08-02
**Scope:** Icon selection, vector representation, rendering, catalog management,
custom icons, web/CLI controls, and verification

## Problem

The generator currently selects artwork only from 24 generic categories. The
entered name affects the initials but does not select service-specific artwork,
so a request named "Nextcloud" can still render as a generic server. Each
generic symbol is also implemented twice, once for Pillow and once for SVG,
which increases maintenance cost and permits the formats to drift.

The application needs broad, recognizable service coverage while retaining its
procedural homelab identity for private or unknown services.

## Goals

- Automatically select recognizable official logo geometry for known services.
- Recolor brand geometry through the existing style and theme system.
- Preserve generic procedural icons as a reliable fallback.
- Support local custom SVG icons and aliases for private or missing services.
- Keep normal generation offline, deterministic, and private.
- Produce matching geometry in SVG, PNG, and ICO outputs.
- Make resolution decisions visible and manually overridable.
- Make generic symbols single-source so new categories are inexpensive to add.

## Non-goals

- Fetching icons from a CDN during normal generation.
- Automatically selecting an uncertain fuzzy match.
- Reproducing official multicolor brand palettes in the first release.
- Generating logos with an AI model.
- Supporting arbitrary active or externally referenced SVG content.
- Aggregating multiple upstream catalogs in the first release.

## Approved Product Decisions

1. Use a hybrid system: known services use brand artwork and unknown services
   use the selected generic category.
2. Use official logo geometry recolored to the selected theme.
3. Detect brands automatically and allow a manual override.
4. Ship a broad maintained catalog locally after installation.
5. Support a local custom-icon directory with user-defined aliases.
6. Hide initials for branded and custom icons; retain initials for generic
   icons.
7. Use a normalized, pinned Simple Icons snapshot as the first catalog.
8. Make SVG the rendering source of truth and use `resvg_py` for PNG
   rasterization.

## Architecture

The pipeline becomes:

```text
CLI, batch entry, or web request
    -> IconRequest validation
    -> IconResolver
         -> explicit selection
         -> custom registry
         -> built-in brand registry
         -> generic fallback
    -> IconResolution + VectorIcon
    -> SvgComposer
    -> SVG output
    -> resvg_py rasterization for PNG
    -> Pillow packaging for ICO
```

The resolver determines identity. The composer determines presentation. Catalog
loading, custom SVG validation, vector composition, and rasterization remain
separate units with narrow interfaces.

## Request Model and Compatibility

`IconRequest` gains one field:

```text
icon: string = "auto"
```

Accepted values are:

- `auto`: resolve from the entered name, then fall back to the category.
- `generic`: bypass brand resolution and use the category.
- A stable icon key such as `nextcloud`: require that catalog or custom icon.

The field is available through the CLI, JSON/NDJSON batches, and web API.
Existing requests remain syntactically valid and now receive automatic brand
resolution by default. Category remains required because it defines the safe
fallback. Existing output directories and filenames remain category-based.

## Resolution Rules

Resolution is deterministic and applies this precedence:

1. An explicit icon key supplied by the user.
2. An exact custom-icon canonical name or alias.
3. An exact built-in catalog canonical name, slug, or curated alias.
4. Another exact lookup after controlled trailing deployment words are removed.
5. The requested generic category.

Names are normalized with Unicode NFKC normalization, case folding, punctuation
replacement, whitespace collapse, and trimming. Exact lookup always occurs
before suffix removal. The controlled suffix set is limited to deployment terms
such as `app`, `service`, `server`, `instance`, `container`, and `vm`.
Service-specific phrases such as "Plex Media Server" belong in the curated alias
map instead of relying on broad token deletion.

Fuzzy search is used only to return manual suggestions. It never changes the
automatic selection. Alias collisions within one registry layer are errors.
Custom entries may deliberately override built-in keys or aliases; the override
is included in diagnostics.

The resolver returns an `IconResolution` containing the selected asset, match
method, source, normalized query, and fallback status. API consumers can explain
every selection.

## Vector Model

All artwork is represented as a `VectorIcon` with:

- Stable key and display title
- Source identifier and upstream source URL
- View box
- Ordered vector nodes
- Canonical aliases
- License and brand-guideline metadata when supplied upstream

Supported vector nodes include paths, rectangles, rounded rectangles, circles,
ellipses, lines, polygons, polylines, and groups with validated transforms. The
model preserves path fill rules so counters and holes remain accurate.

Simple Icons assets normally become one path in a `0 0 24 24` view box. Existing
generic draw functions are migrated to focused vector-definition modules that
return the same node model. There is no separate Pillow implementation of a
symbol.

## Catalog Lifecycle

A maintainer-only sync command imports a named, pinned Simple Icons release. The
initial implementation targets the current 16.27.0 release and records its
archive checksum. The sync operation:

1. Downloads or reads the pinned upstream release outside normal generation.
2. Extracts canonical titles, slugs, SVG paths, sources, licenses, and guideline
   links.
3. Applies the repository's reviewed homelab alias file.
4. Validates unique keys, aliases, view boxes, and path data.
5. Writes a compact package-data registry and generated third-party notice.

The generated registry is committed and shipped with the Python application.
Runtime code neither requires Node.js nor contacts Simple Icons. Catalog updates
arrive as reviewed application updates and remain reproducible through the
recorded release version and checksum.

## Custom Icons

The custom icon directory is selected in this order:

1. CLI or server configuration
2. `HOMELAB_ICON_DIR`
3. An optional `custom-icons` directory under the working directory

The directory contains SVG files and a `manifest.json`. Each manifest entry has
a stable key, display name, filename, and zero or more aliases. A missing custom
directory is valid and produces an empty custom registry.

Custom SVG parsing permits geometry-only SVG. It rejects scripts, event-handler
attributes, external resources, embedded raster images, animation,
`foreignObject`, text, and unsupported definitions or references. Geometry and
finite transforms are normalized into `VectorIcon` nodes and recolored by the
composer. An unsupported file is excluded and reported with its filename and
reason. Explicitly requesting that entry returns a validation error.

## SVG Composition and Raster Output

`SvgComposer` owns the background, border, theme colors, glow definitions,
symbol placement, and initials. It escapes all text and serializes only the
normalized vector model.

Brand and custom artwork is centered in a safe-area box with aspect ratio
preserved and no initials. Generic artwork retains the current upper symbol
region and initials at sizes of 64 pixels or larger. Background corner radii and
border widths become fractions of canvas size, fixing the existing scaling
defect.

The composed SVG is written directly for SVG output. `resvg_py` rasterizes the
same in-memory SVG bytes at the requested dimensions for PNG. Pillow opens that
PNG only to package ICO output. Rasterization errors stop the affected output
rather than falling back to a visually different renderer.

## Proposed Module Boundaries

- `app/icons/models.py`: `VectorNode`, `VectorIcon`, and `IconResolution`
- `app/icons/registry.py`: cached built-in and custom registry indexes
- `app/icons/resolver.py`: deterministic matching and suggestions
- `app/icons/custom.py`: manifest loading and SVG sanitization
- `app/icons/catalog.py`: package-data access and provenance
- `app/icons/generic/`: focused single-source generic definitions
- `app/generator/svg_composer.py`: style and layout composition
- `app/generator/rasterizer.py`: `resvg_py` adapter
- `scripts/sync_simple_icons.py`: maintainer-only pinned catalog import

The existing renderer remains a thin orchestration and file-output boundary.
Modules are kept small enough to test without generating files.

## Web and API Experience

The web UI adds a detected-icon panel showing the display name, source, and
match method. A searchable picker allows a deliberate override, and a generic
option returns control to the category. When automatic resolution falls back,
the UI says so instead of implying that the brand was recognized.

The backend exposes catalog search and generator-options endpoints. The web UI
loads categories, styles, themes, and formats from backend data, eliminating the
current duplicated category list that exposes only 16 of 24 categories.

Generation responses add `icon_key`, `icon_source`, `match_method`, and
`used_fallback`. Existing response fields remain unchanged.

## Error Handling and Diagnostics

- Unknown automatic names use the generic fallback and report it.
- Unknown explicit keys are errors with close manual suggestions.
- Invalid catalog data fails the catalog build.
- Invalid custom entries are isolated and listed in diagnostics.
- Custom overrides are accepted but reported.
- SVG rasterization failures identify the requested format and preserve any
  independently successful SVG output.
- No failure path silently performs a network request.

## Verification Strategy

Focused automated coverage includes:

- Resolver tests for names, slugs, aliases, suffix removal, overrides, Unicode,
  ambiguity, suggestions, and fallback.
- Tests proving fuzzy suggestions are never auto-selected.
- Catalog integrity tests for unique normalized identifiers, valid paths,
  provenance, and deterministic generated output.
- SVG sanitizer tests for permitted geometry and rejected active, external, or
  malformed content.
- Renderer tests across brand, custom, and generic assets; every style;
  transparency; and representative sizes from 32 through 2048 pixels.
- Representative golden images and contact sheets for visual regression.
- PNG/SVG geometry parity, PNG dimensions/mode, and ICO packaging tests.
- Existing CLI and batch compatibility tests plus API and web interaction tests
  for detection, override, and fallback states.

The registry is loaded once per process and reused for batch generation. Tests
also verify that normal generation performs no network access.

## Legal and Provenance

The shipped catalog retains upstream source, license, and brand-guideline fields
when available. A generated third-party notice records the pinned catalog
release and explains that product names and trademarks belong to their owners.
The UI may link to provenance details but does not present catalog inclusion as
endorsement. Recoloring remains the user's selected presentation and may differ
from an owner's published brand guidance.

## Acceptance Criteria

- Known catalog names and reviewed aliases resolve deterministically to their
  correct geometry.
- Unknown or ambiguous names never receive an unconfirmed brand automatically.
- A user can inspect and override the detected icon in the web UI and CLI.
- A valid custom icon can override a built-in icon without changing application
  code.
- All existing generic categories still render.
- SVG, PNG, and ICO use the same vector composition.
- Generation works offline on supported Windows, Linux, macOS, and ARM systems.
- The web UI exposes every backend category.
- Catalog provenance and custom-icon validation failures are inspectable.

## References

- Simple Icons package and data model: https://www.npmjs.com/package/simple-icons
- Simple Icons legal disclaimer: https://github.com/simple-icons/simple-icons/blob/develop/DISCLAIMER.md
- `resvg_py` installation and platform support: https://resvg-py.readthedocs.io/en/latest/installation.html
- `resvg_py` API: https://resvg-py.readthedocs.io/en/latest/api.html
- Dashboard Icons, considered as a future provider: https://github.com/homarr-labs/dashboard-icons
