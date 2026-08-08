# CLAUDE.md

## Project overview

Homelab Icon Generator is a Python 3.10+ CLI and local FastAPI web application
for creating styled dashboard icons. Known names resolve against a pinned offline
Simple Icons catalog, local custom SVGs can override bundled brands, and unknown
names use one of 24 generic categories. Brand/custom geometry omits initials;
generic geometry retains them.

Use UV for every dependency and execution workflow:

```bash
uv sync
uv run python main.py --name "Nextcloud" --category cloud_service --format both
uv run homelab-icons  # bare invocation opens the web UI
uv run pytest -q
uv build
```

`app/web/api.py` reads `PORT` (default 5000) and
`GENERATE_RATE_LIMIT`/`GENERATE_RATE_WINDOW` (default 20 requests/60s) for the
`/api/generate` rate limiter. `FLASK_DEBUG` is retired.

Batch input supports JSON arrays and streaming NDJSON. Prefer NDJSON for large
batches. Output stays under `output/{format}/{category}/` and filenames remain
category-compatible even when brand artwork is selected.

## Runtime pipeline

```text
IconRequest + validation
  -> IconResolver
       explicit key
       custom exact key/title/alias
       bundled exact key/title/reviewed alias
       controlled deployment-suffix removal
       generic category fallback
  -> IconResolution + VectorIcon
  -> SvgComposer (authoritative rendering)
  -> SVG write and resvg_py rasterization
  -> PNG / ICO packaging
```

Fuzzy matching is suggestion-only and must never select artwork automatically.
Normal generation must not access the network.

## Module boundaries

- `app/icons/models.py`: immutable `VectorNode`, `VectorIcon`, `IconResolution`
- `app/icons/generic/`: single-source procedural category geometry
- `app/icons/catalog.py`: bundled package-data loading
- `app/icons/registry.py`: built-in and custom-first indexes
- `app/icons/resolver.py`: matching precedence, suffix control, suggestions
- `app/icons/custom.py`: manifest validation and geometry-only SVG sanitization
- `app/icons/naming.py`: name normalization for resolution (`normalize_icon_name`) —
  distinct from `app/utils/naming.py`, which derives display initials
  (`generate_initials`); don't confuse the two
- `app/generator/svg_composer.py`: presentation, safe area, glow, initials
- `app/generator/colors.py` / `layouts.py`: theme palettes and per-style layout geometry
- `app/generator/rasterizer.py`: resvg adapter returning Pillow RGBA images
- `app/generator/renderer.py`: validation, orchestration, and output paths
- `app/styles/`: minimal/terminal/cyberpunk visual style definitions
- `app/web/api.py`: FastAPI routes — metadata, search, generation, history, liveness
- `app/web/schemas.py`: Pydantic edge models; shape validation only, never domain rules
- `app/web/history.py`: SQLite gallery store (500-row cap, disk reconciliation)
- `app/web/launcher.py`: port selection, single-instance probe, uvicorn, heartbeat shutdown
- `app/web/static/`: the static UI itself (`index.html`, `app.js`, `gallery.js`, `app.css`)
- `scripts/sync_simple_icons.py`: maintainer-only pinned catalog import

Keep new features modular. Generic geometry belongs in the focused domain file,
not in the renderer. SVG remains the source of truth; do not introduce a second
Pillow drawing implementation.

## Identity and compatibility rules

`IconRequest.icon` defaults to `auto`:

- `auto`: exact custom/bundled resolution, then generic fallback
- `generic`: force the category and initials
- other value: require that exact stable key or raise with suggestions

Name normalization uses Unicode NFKC, case folding, punctuation replacement,
and whitespace collapse. Only controlled trailing words (`app`, `service`,
`server`, `instance`, `container`, `vm`) may be removed after exact lookup.

Validation ranges:

- category: one of the 24 `VALID_CATEGORIES`
- style: minimal, terminal, cyberpunk
- theme: green, blue, orange, purple, grayscale, or custom with a six-digit `custom_color`
- format: png, svg, ico, both, all
- size: 32-2048; ICO/all require 256 or smaller

## Custom icon safety

Directory precedence is explicit CLI/server configuration,
`HOMELAB_ICON_DIR`, then `custom-icons/manifest.json` in the working directory.
The sanitizer permits only normalized geometry and finite transforms. Reject
active content, event handlers, external references, images, text, animation,
definitions, unsupported namespaces/elements/attributes, and non-finite data.
Invalid entries are isolated in diagnostics; an explicit invalid key must report
its specific diagnostic.

## Catalog lifecycle

The bundled snapshot is Simple Icons 16.27.0. Refresh it only through
`scripts/sync_simple_icons.py`, retain reviewed aliases, and review the generated
manifest/checksums and `docs/THIRD_PARTY_ICONS.md`. Runtime code must not depend
on Node.js or a remote catalog.

## Verification expectations

For relevant changes run focused tests, then the complete gate:

```bash
uv run pytest -q
uv build
git diff --check
```

Use `scripts/generate_contact_sheet.py` for representative visual regression.
For web changes, verify desktop and mobile layouts, automatic detection, typo
fallback, manual override, accessible pressed states, generated preview, and
console cleanliness.
