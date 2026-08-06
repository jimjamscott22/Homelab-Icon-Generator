# Homelab Icon Generator

Generate consistent homelab icons with recognizable brand geometry, safe local
SVG overrides, and procedural fallbacks. Normal generation is offline: the
application ships a pinned Simple Icons catalog and never fetches artwork at
request time.

## Highlights

- 3,450 bundled brands from Simple Icons 16.27.0
- Conservative automatic detection: exact names and reviewed aliases only
- Fuzzy suggestions for manual selection, never silent fuzzy auto-matches
- Sanitized custom SVG icons and custom-over-built-in overrides
- 24 procedural fallback categories with initials
- One authoritative SVG composition for SVG, PNG, and ICO geometry
- Minimal, terminal, and cyberpunk styles with five color themes
- Accessible web search/override controls and resolution metadata
- PNG, SVG, ICO, `both`, and `all` output modes

Brand and custom geometry is recolored using the selected theme and omits
initials. Unknown names retain the selected generic category and initials.

## Install

This project uses [UV](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/jimjamscott22/Homelab-Icon-Generator.git
cd Homelab-Icon-Generator
uv sync
```

## CLI usage

Automatic brand detection is the default. `uv run homelab-icons --name ...` is
the primary form; `uv run python main.py` still works identically:

```bash
uv run homelab-icons \
  --name "Nextcloud" \
  --category cloud_service \
  --style minimal \
  --theme blue \
  --size 256 \
  --format both
```

Control identity with `--icon`:

```bash
# Require this exact bundled/custom key
uv run homelab-icons --name "Private Cloud" --category cloud_service --icon nextcloud

# Bypass brand detection and force the category artwork
uv run homelab-icons --name "Nextcloud" --category cloud_service --icon generic
```

| Flag | Default | Description |
|---|---:|---|
| `--name` | required | Device or service name |
| `--category` | required | Generic fallback category |
| `--icon` | `auto` | `auto`, `generic`, or an exact stable icon key |
| `--icon-dir` | — | Custom icon directory; overrides environment/default discovery |
| `--style` | `minimal` | `minimal`, `terminal`, or `cyberpunk` |
| `--theme` | `blue` | `green`, `blue`, `orange`, `purple`, or `grayscale` |
| `--size` | `256` | Square size from 32 through 2048 pixels |
| `--format` | `both` | `png`, `svg`, `ico`, `both`, or `all` |
| `--output-dir` | `output` | Output root directory |
| `--transparent` | off | Use a transparent canvas |
| `--batch` | — | JSON-array or NDJSON batch file |

ICO output is limited to 256px. Files remain grouped by fallback category at
`output/{format}/{category}/{slug}-{style}-{theme}-{size}.{ext}`.

### Categories

```text
raspberry_pi  server       router        switch
laptop        desktop      phone         iot
container     database     cloud_service generic_service
media         ai           camera        game_console
cli           code         git_branch    api
firewall      vpn          nas           power
```

### Batch generation

Every entry accepts the same request fields, including `icon`:

```json
[
  {
    "name": "Nextcloud",
    "category": "cloud_service",
    "icon": "auto",
    "style": "minimal",
    "theme": "blue",
    "format": "both"
  },
  {
    "name": "Unknown NAS",
    "category": "nas",
    "icon": "generic",
    "style": "terminal",
    "theme": "green"
  }
]
```

```bash
uv run homelab-icons --batch examples/sample_icons.json
```

NDJSON is streamed line by line and is preferred for large batches.

## Custom icons

Directory precedence is:

1. `--icon-dir`
2. `HOMELAB_ICON_DIR`
3. `custom-icons/manifest.json` under the working directory

Manifest format:

```json
{
  "icons": [
    {
      "key": "internal-api",
      "name": "Internal API",
      "file": "internal-api.svg",
      "aliases": ["corp api", "private api"]
    }
  ]
}
```

Custom files may contain geometry elements (`path`, `rect`, `circle`, `ellipse`,
`line`, `polygon`, `polyline`, and `g`) with validated attributes and finite
transforms. Scripts, event handlers, external resources, images, text,
animation, definitions/references, `foreignObject`, and malformed geometry are
rejected and reported as diagnostics. See [custom-icons/README.md](custom-icons/README.md).

## Web UI and API

### Web UI

```bash
uv run homelab-icons
```

Running with no arguments starts the local server and opens
<http://127.0.0.1:5000> in your browser. Closing the tab shuts the server down
after about 30 seconds. Re-running while it is already up just reopens the tab.

For a desktop icon:

```bash
uv run python -m scripts.install_shortcut
```

The UI loads all option lists from the backend, shows automatic
detection/fallback state, provides searchable manual overrides, and keeps a
persistent gallery of your last 500 generations. Clicking a gallery tile
restores the settings that produced it.

API endpoints:

- `GET /api/options` — categories, styles, themes, formats, and diagnostics
- `GET /api/icons/search?q=Nextclod` — exact match plus advisory suggestions
- `POST /api/generate` — files plus icon key/source/match/fallback metadata
- `GET /api/history` — persistent gallery of recent generations
- `GET /api/alive` — liveness probe used by the heartbeat shutdown

Optional server variables are `PORT`, `GENERATE_RATE_LIMIT`,
`GENERATE_RATE_WINDOW`, and `HOMELAB_ICON_DIR`.

## Catalog maintenance

Normal generation has no network path. A maintainer refreshes the committed
catalog explicitly:

```bash
uv run python -m scripts.sync_simple_icons \
  --version 16.27.0 \
  --aliases app/icons/data/homelab-aliases.json \
  --output app/icons/data \
  --notice docs/THIRD_PARTY_ICONS.md
```

The generated manifest records the npm archive URL, archive SHA-256, catalog
content SHA-256, version, and icon count. Legal/provenance notes are in
[docs/THIRD_PARTY_ICONS.md](docs/THIRD_PARTY_ICONS.md).

## Architecture

```text
CLI / batch / web request
  -> IconRequest validation
  -> explicit/custom/bundled/exact-suffix/generic resolution
  -> normalized VectorIcon
  -> one SVG composition
  -> direct SVG output + resvg rasterization
  -> PNG and optional ICO packaging
```

Key modules:

- `app/icons/` — models, generic artwork, catalog, custom sanitizer, registries,
  and resolver
- `app/generator/svg_composer.py` — frame, theme, geometry, glow, and initials
- `app/generator/rasterizer.py` — `resvg_py` adapter
- `app/generator/renderer.py` — validation and file orchestration
- `scripts/` — pinned catalog sync and representative contact sheet

To add a generic category, add its key to `VALID_CATEGORIES`, define one
`VectorIcon` in the appropriate `app/icons/generic/` module, and register it in
`app/icons/generic/__init__.py`. There is no separate PNG implementation.

## Verification

```bash
uv run pytest -q
uv build
git diff --check
```

Generate the representative brand/custom/generic contact sheet with:

```bash
uv run python -m scripts.generate_contact_sheet \
  --icon-dir tests/fixtures/custom-icons \
  --output output/contact-sheet.png
```

## License

Application code is MIT licensed. Product names, logos, and brands remain the
property of their respective owners; see the third-party notice for catalog
details.
