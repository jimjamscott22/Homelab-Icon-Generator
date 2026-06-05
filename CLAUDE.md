# CLAUDE.md

## Running the project

This project uses [uv](https://docs.astral.sh/uv/) for dependency and environment management. Dependencies are declared in `pyproject.toml` and locked in `uv.lock`.

Sync the environment:
```bash
uv sync
```

Single icon:
```bash
uv run python main.py --name "Nextcloud" --category cloud_service --style minimal --theme blue --size 256 --format both
```

Batch mode:
```bash
uv run python main.py --batch examples/sample_icons.json
```

The batch file may be either a JSON array (`[{...}, {...}]`) or NDJSON (one JSON object per line). The JSON array path is loaded fully into memory via `json.load`; the NDJSON path is streamed line-by-line. **Prefer NDJSON for large batches** to keep memory flat — see `_iter_batch_entries` in `app/main.py`.

Output files land in `output/{format}/{category}/` with slugified filenames: `{slug}-{style}-{theme}-{size}.{ext}` — e.g. `output/png/cloud_service/nextcloud-minimal-blue-256.png`. Output directories are created automatically on first write; the `.gitkeep` file keeps the `output/` directory in version control while generated files are ignored.

## Architecture

The pipeline flows through these layers:

```
CLI args / JSON entry
    → IconRequest (app/models/icon_request.py)
    → validate_request (app/utils/validation.py)
    → get_palette (app/generator/colors.py)        # theme → ColorPalette
    → get_style (app/styles/<style>.py)            # palette → StyleDefinition
    → get_layout (app/generator/layouts.py)        # size → LayoutSpec
    → render_png / render_svg (app/generator/renderer.py)
    → save to output/{format}/{category}/
```

## Key design decisions

- **Symbols are fully procedural**: all coordinates are expressed as fractions of `size` (e.g. `int(size * 0.28)`), so every symbol scales correctly from 32px to 2048px. Never use hardcoded pixel values in symbol or renderer code.

- **Glow effect is SVG-only**: PNG ignores `StyleDefinition.use_glow`. SVG uses `<feGaussianBlur>` in a `<defs>` filter. This was a deliberate choice — Pillow glow requires multi-pass rendering, while SVG supports it natively.

- **SVG is hand-built XML**: the renderer builds SVG strings directly rather than using svgwrite. This gives full control over filter elements and keeps the output readable.

- **Style modules are stateless**: each `app/styles/<name>.py` exports only `get_style(palette) -> StyleDefinition`. Adding a new style is self-contained — no central registry to update beyond `VALID_STYLES`.

- **Styles are loaded via importlib**: `renderer.py` uses `importlib.import_module(f"app.styles.{request.style}")` to avoid a hard import of every style module and to keep the style list as the single source of truth in `validation.py`.

## Performance & Debugging

### Memory Efficiency

- **Batch processing**: NDJSON streaming keeps memory flat for large batches; JSON array path loads fully into memory
- **Symbol rendering**: All coordinates are fractional (no per-size computation), so scaling up is cheap
- For large batches (1000+ icons), prefer NDJSON input

### Profiling & Analysis

See [docs/PERFORMANCE_FINDINGS.md](docs/PERFORMANCE_FINDINGS.md) for detailed performance characteristics and optimization strategies discovered during recent profiling work.

## Extending the project

### New category

1. `app/utils/validation.py` — add to `VALID_CATEGORIES`
2. `app/generator/symbols.py` — add `draw_<category>(draw, cx, cy, size, color)` using only fractional coordinates; register in `SYMBOL_DRAWERS`
3. `app/generator/renderer.py` — add `_svg_<category>(cx, cy, size, color)` mirroring the PIL version; register in `_SVG_SYMBOL_FUNCS`

### New style

1. Create `app/styles/<name>.py` with `get_style(palette: ColorPalette) -> StyleDefinition`
2. `app/utils/validation.py` — add to `VALID_STYLES`

### New theme

1. `app/generator/colors.py` — add entry to `COLOR_THEMES`
2. `app/utils/validation.py` — add to `VALID_THEMES`

## Validation rules

- `name`: required, non-empty
- `category`: must be in `VALID_CATEGORIES` (12 values)
- `style`: must be in `VALID_STYLES` (minimal, terminal, cyberpunk)
- `theme`: must be in `VALID_THEMES` (green, blue, orange, purple, grayscale)
- `format`: must be in `VALID_FORMATS` (png, svg, both)
- `size`: integer between 32 and 2048 inclusive
