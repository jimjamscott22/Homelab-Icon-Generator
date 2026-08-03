# Custom icons

Place a `manifest.json` and its referenced SVG files in this directory, or pass
another directory with `--icon-dir`. `HOMELAB_ICON_DIR` is used when the CLI
option is absent.

Only geometry-only SVG is accepted. Supported elements are `path`, `rect`,
`circle`, `ellipse`, `line`, `polygon`, `polyline`, and `g`. Active content,
external references, images, text, styles, definitions, and event attributes
are rejected. Accepted geometry is recolored using the selected application
theme.

Copy `manifest.example.json` to `manifest.json`, then add one entry per icon.
Keys must be lowercase kebab-case and filenames must refer to SVG files directly
inside this directory. Custom keys and aliases take precedence over bundled
brands.
