# Project Review & Roadmap

Status updated after the hybrid brand icon rollout on
`codex/hybrid-brand-icon-system`.

## Completed foundation

- ✅ Automated validation, renderer, resolver, catalog, custom-icon, CLI, API,
  contact-sheet, and full category/style/theme coverage.
- ✅ All 24 generic categories are represented once as normalized vector
  geometry; PNG and ICO rasterize the authoritative SVG.
- ✅ Border widths and corner radii scale fractionally from 32px through 2048px.
- ✅ The renderer is a focused orchestrator; obsolete Pillow symbol helpers and
  duplicated SVG functions are removed.
- ✅ PNG, SVG, ICO, `both`, and `all` formats share validation and output rules;
  ICO is safely capped at 256px.
- ✅ XML escaping, Unicode-safe fallback filenames, transparent output, and all
  backend category lists are covered.
- ✅ The web UI obtains its options from the backend and works at desktop and
  mobile widths without external font requests.

## Completed hybrid identity system

- ✅ Pinned Simple Icons 16.27.0 catalog with 3,450 offline brand paths,
  provenance fields, archive/content checksums, and reviewed homelab aliases.
- ✅ Conservative automatic resolution: exact matches only, with controlled
  deployment-suffix removal and fuzzy suggestions that never auto-select.
- ✅ `--icon auto|generic|<stable-key>` across CLI, batch, API, and web UI.
- ✅ Geometry-only custom SVG manifests, explicit/env/default directory
  precedence, invalid-entry diagnostics, and custom-over-built-in overrides.
- ✅ API resolution metadata and catalog search, plus detected/fallback/manual
  identity controls with accessible pressed states.
- ✅ Deterministic brand/custom/generic contact sheet and golden image.

## Remaining product opportunities

1. **Dashboard integration presets** — Homarr, Dashy, Homepage, and Heimdall
   naming/config exports.
2. **Favicon and app-icon bundles** — multi-resolution ICO, touch icon, 192/512
   PNGs, and HTML link snippets.
3. **Custom theme data** — user-provided palettes and light variants.
4. **Live preview and batch ZIP** — in-memory preview endpoint plus archive
   download for a generated set.
5. **Additional generic categories** — DNS, reverse proxy, monitoring, backup,
   home automation, printer, TV, VM/hypervisor, and Kubernetes.
6. **Badges and overlays** — status, port, or environment variants without
   duplicating identity geometry.
7. **Distribution** — PyPI release automation and a containerized web service.
8. **CLI discoverability** — argparse choices, list commands, catalog details,
   and dry-run output planning.

## Suggested next sequence

1. Dashboard presets and favicon bundles for immediate homelab utility.
2. Live preview/ZIP and custom palette data for workflow polish.
3. Additional generic categories now that each requires one vector definition.
4. Distribution automation after the public interface settles.
