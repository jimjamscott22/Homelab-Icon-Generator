# Performance Findings (Batch/Rendering/I/O/Style Import)

## 1) Batch input can be memory-heavy for large JSON arrays
- **Location:** `app/main.py:50-76`
- **Finding:** Batch parsing supports JSON array input (`json.load`) and now also supports line-by-line NDJSON processing.
- **Impact:** Large JSON arrays still require full in-memory load; NDJSON path is streaming.
- **Suggestion:** Prefer NDJSON for large runs; if JSON array streaming is needed, introduce an incremental parser.
- **Status (2026-06-04):** NDJSON documented as the recommended large-batch format in `CLAUDE.md`. Incremental array parsing (`ijson`) intentionally deferred — not worth a new dependency for the current workload.

## 2) Duplicate raster work for PNG+ICO in `all` mode
- **Location:** `app/generator/renderer.py:526-558`
- **Finding:** This hotspot was addressed by rendering once (`base_img`) and reusing it for PNG and ICO writes.
- **Impact:** Removes repeated raster rendering for `format=all`.
- **Suggestion:** Keep reuse path and benchmark with large batch workloads.

## 3) Repeated style import/computation per icon
- **Location:** `app/generator/renderer.py:39-48`, `app/generator/renderer.py:510-513`
- **Finding:** Dynamic style resolution and layout computation are now cached via `@lru_cache`.
- **Impact:** Cuts repeated work for common `(style, theme, size)` combinations.
- **Suggestion:** Periodically review cache size and hit rate for very diverse workloads.

## 4) Repeated output directory creation checks
- **Location:** `app/generator/renderer.py:518-523`
- **Finding:** Directory creation calls are now guarded by an in-process `_CREATED_OUTPUT_DIRS` cache.
- **Impact:** Reduces redundant filesystem calls in batch runs.
- **Suggestion:** Keep this cache process-local; no cross-process synchronization needed for current CLI/server usage.

## 5) Font lookup/loading overhead during initials rendering
- **Location:** `app/generator/text_utils.py:27-52`
- **Finding:** Font object loading (`_load_font`) and path discovery (`_find_font_path`) are now cached.
- **Impact:** Reduces repeated filesystem checks and font initialization overhead across icons.
- **Suggestion:** Keep cache bounded (current maxsize=64) and revisit only if many distinct font sizes are used.

## 6) Additional note: SVG string assembly still allocates many intermediates
- **Location:** `app/generator/renderer.py` (multiple `_svg_*` helpers and joins, e.g. `455`, `468-478`, `561+`)
- **Finding:** SVG construction relies on many small strings and joins.
- **Impact:** Moderate allocation overhead in SVG-heavy batches.
- **Suggestion:** Future pass can optimize assembly by reducing split/join passes and building directly from append-only buffers.
- **Status (2026-06-04):** Removed the per-icon cosmetic re-indent (split→rejoin) of the symbol group in `render_svg`; whitespace is non-semantic in SVG. Also fixed a correctness bug in `_svg_media` where stroke attributes were appended after a self-closed `<rect/>`, producing invalid XML and an unstroked media icon.
