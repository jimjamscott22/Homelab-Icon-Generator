# Project Review & Roadmap

A review of the Homelab Icon Generator with concrete follow-up work. Items are
grouped into **review findings** (bugs / drift / hygiene) and **feature
suggestions** (new capabilities). Status reflects the state as of the
`claude/project-review-features-vokicg` branch.

## Legend

- ✅ **Done** — completed on this branch
- ⬜ **To do** — not yet started

---

## Review findings

| # | Finding | Status |
|---|---------|--------|
| 1 | **No test coverage.** The renderer is highly testable (deterministic SVG strings, checkable PNG size/mode). | ✅ Done — added `tests/` pytest suite: validation, initials, and a full category × style × theme render sweep (74 tests). |
| 2 | **`patch_renderer.py` leftover dev artifact** at repo root; its contents were already merged into `renderer.py`. | ✅ Done — deleted. |
| 3 | **Doc drift.** README said 16 categories, CLAUDE.md said 12, actual count is 24; formats and category list were stale; `requirements.txt` referenced but absent. | ✅ Done — README + CLAUDE.md synced to code. |
| 4 | **Generated output committed** under `output/` with mismatched category/name pairs. | ✅ Done — untracked and added `output/ico/**` to `.gitignore`. |
| 5 | **Web UI couldn't serve ICO** — `serve_output` whitelisted only png/svg, so ICO URLs from `/api/generate` 404'd. | ✅ Done — added `ico` to the format/extension whitelist. |
| 6 | **ICO breaks above 256px** — the container can't encode a side length >256. | ✅ Done — validation rejects `ico`/`all` with `size > 256` up front. |
| 7 | **SVG initials not XML-escaped**, and fully non-ASCII names slugify to an empty filename. | ✅ Done — initials escaped via `xml.sax.saxutils.escape`; empty slug falls back to the category name. |
| 8 | **`corner_radius` / `border_width` are absolute pixels** while everything else is fractional, so borders/corners look wrong at 32px vs 2048px — contradicts the project's own "never hardcode pixel values" rule. | ⬜ To do — make them fractions of `size` in the style definitions and renderer. |
| 9 | **Structural scar in `renderer.py`** — `_svg_media` and the later symbol functions sit *after* `generate_icon`, out of order with the file's section comments. | ⬜ To do — reorder so all symbol helpers precede the orchestrator (pairs naturally with feature #1 below). |

---

## Feature suggestions

Ranked roughly by value-to-effort for a homelab audience. All are **⬜ To do**.

### 1. Single-source symbol definitions
Every category currently needs two hand-written functions (PIL + SVG) kept
visually in sync by hand — the biggest maintenance tax, and it grows with every
category. Define each symbol once as a list of shape primitives
(`("rounded_rect", x1, y1, x2, y2, r)`, …) and write one PIL interpreter and one
SVG interpreter. Adding a category becomes one declaration; PNG/SVG can never
drift apart. **Do this before adding more categories (#7).**

### 2. Dashboard integration presets
The killer feature for the target audience: batch-generate an icon pack laid out
for Homarr / Dashy / Homepage / Heimdall, ideally emitting a config snippet
(e.g. Dashy `items:` YAML pointing at the icon paths). A `--preset dashy` flag
that fixes size/format/naming conventions makes the tool useful end-to-end.

### 3. Favicon / app-icon bundles
A `--format favicon` that emits the standard set from one render: multi-res
`.ico` (16/32/48), `apple-touch-icon.png` (180), 192 and 512 PNGs, plus a
ready-to-paste `<link>` HTML snippet. Every self-hosted service behind a reverse
proxy wants this.

### 4. Custom themes as data, not code
Themes are just four hex colors. Allow `--colors bg=#111,fg=#3a5,...` or loading
extra themes from a `themes.json`. Also: all five built-in themes are dark — add
light variants.

### 5. Contact sheet / gallery mode
`--gallery` renders one grid image (or HTML page) of all categories in the chosen
style + theme, so users can browse before batch-generating. Doubles as a visual
regression artifact for the test suite.

### 6. Web UI: live preview + zip download
The SVG renderer already returns a string — add an `/api/preview` endpoint that
returns SVG without writing to disk, debounced as the user tweaks options. Add a
"download all as .zip" for batch results.

### 7. More homelab categories
Obvious gaps: `dns`, `proxy`/`reverse_proxy`, `monitoring`, `backup`,
`home_automation`, `printer`, `tv`, `vm`/`hypervisor`, `kubernetes`. Much cheaper
to add after #1.

### 8. Status badges / overlays
Optional corner dot or small label (`--badge green`, `--badge "8080"`) for
network-map exports where you want up/down or port variants of the same icon.

### 9. Package + Docker distribution
Publish to PyPI with a `homelab-icon` console script; add a Dockerfile /
compose file for the web UI. Homelab users overwhelmingly deploy via compose,
and the project is currently clone-only.

### 10. CLI polish
Use argparse `choices=` so invalid values fail at parse time with the option
list; add `--list-categories` / `--list-themes`; add a `--dry-run` that prints
target paths without writing.

---

## Suggested sequencing

1. **#1 (single-source symbols)** and finding **#9 (reorder renderer)** together
   — they touch the same code and unblock cheap category growth.
2. **Finding #8 (fractional radius/border)** — small, improves every icon.
3. **#7 (categories)**, **#4 (custom themes)** — quick wins once #1 lands.
4. **#2 / #3 (dashboard presets, favicon bundles)** — highest user value.
5. **#6 (web preview/zip)**, **#5 (gallery)**, **#10 (CLI polish)** — UX.
6. **#9 (packaging/Docker)** — distribution once the feature set settles.
