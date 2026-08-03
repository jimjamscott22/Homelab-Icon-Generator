# Hybrid Brand Icon System Implementation Summary

## Outcome

The application now recognizes thousands of common services accurately while
preserving its procedural homelab style for private and unknown names. It ships
Simple Icons 16.27.0 locally, resolves only deterministic exact matches, accepts
sanitized custom SVG overrides, and renders one authoritative SVG composition
into SVG, PNG, and ICO outputs.

## Implemented architecture

Requests gain `icon="auto"` and flow through a dedicated resolver before
presentation. Resolution precedence is explicit key, custom key/title/alias,
built-in key/title/reviewed alias, controlled deployment-suffix removal, then
the requested generic category. Fuzzy matching only supplies suggestions.

Every asset is normalized to `VectorIcon`/`VectorNode`. The composer owns the
frame, theme, safe-area placement, glow, and initials policy. `resvg_py`
rasterizes that exact SVG for PNG, and Pillow packages ICO. The old duplicated
Pillow/SVG symbol implementations were removed.

## Catalog and provenance

- Pinned package: `simple-icons@16.27.0`
- Bundled icons: 3,450
- Generated data: `app/icons/data/simple-icons.json`
- Reproducibility: archive URL plus archive/content SHA-256 in
  `catalog-manifest.json`
- Reviewed shortcuts: `homelab-aliases.json`
- Legal/provenance: `docs/THIRD_PARTY_ICONS.md`

The maintainer sync script safely extracts a versioned npm archive, validates
one finite view box/path per upstream icon, retains sources/licenses/guidelines,
merges reviewed aliases, sorts output deterministically, and writes package
data. Runtime generation has no catalog network path.

## Custom icon boundary

Custom manifests support stable keys, display names, SVG filenames, and
aliases. The loader accepts geometry-only elements and finite transforms,
normalizes color to the selected theme, and rejects scripts, event handlers,
external resources, embedded images, text, animation, definitions/references,
foreign objects, unsupported attributes, malformed geometry, and traversal.
Invalid entries are isolated as structured diagnostics. Valid custom keys and
aliases intentionally override bundled matches.

## Interfaces

- CLI/batch: `--icon` and `--icon-dir`
- Environment: `HOMELAB_ICON_DIR`
- API: backend options, catalog search, and resolution metadata
- Web: detected/fallback readout, search suggestions, manual override, explicit
  generic choice, and matching CLI snippet
- Diagnostics: unknown explicit keys include close suggestions; invalid custom
  keys include their sanitizer reason

The web UI now exposes all 24 backend categories, uses no remote font assets,
has focus-visible and pressed-state treatment, and uses normal document scrolling
on small screens.

## Compatibility

Existing `IconRequest` calls remain valid because `icon` defaults to `auto`.
Category is still required and continues to control fallback and output
directories. `generate_icon()` still returns the original paths dictionary;
`generate_icon_result()` adds resolution metadata. Existing sizes, themes,
styles, transparency, and formats remain supported.

## Verification

- Complete pytest suite: 152 passing tests
- Package build: wheel and source distribution
- Wheel inspection: catalog JSON, manifest, aliases, and data package included
- Deterministic contact sheet: bundled Nextcloud, sanitized custom Internal API,
  and forced generic NAS golden comparison
- Browser QA: desktop and 390px mobile layouts; 24 categories; automatic exact
  detection; typo fallback; manual override; generated preview/downloads;
  zero current console errors or warnings
- Repository whitespace check: clean

Representative artifact: `tests/golden/hybrid-contact-sheet.png`.

## Commits

- `e62afd8` normalized vector model
- `856e15b` SVG-first generic icons
- `491a6b5` authoritative SVG rasterization
- `20fe9b3` pinned offline brand catalog
- `8950993` conservative resolver and CLI controls
- `46e753e` sanitized custom icon overrides
- `cae43cb` API metadata and web detection controls

