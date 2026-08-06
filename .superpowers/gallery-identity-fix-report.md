# Gallery identity fix

## Bug

`app/web/history.py` deduplicated gallery rows on a settings tuple
(`name, category, style, theme, size, format, transparent_bg, icon`) that is
finer-grained than the actual output filename (`_output_base` in
`app/generator/renderer.py`, which excludes `format`, `transparent_bg`, and
`icon`). Regenerating the same artwork with a different `icon`/
`transparent_bg`, or with two names that slugify identically, overwrote the
same file on disk but produced two gallery rows — one showing stale data.

## Fix

- `app/web/history.py`: added `output_key` (derived from the actual written
  file path — format directory and extension stripped, via
  `_derive_output_key`/`_output_key_from_rel`, used by both `record()` and
  the migration backfill). Replaced the 8-column unique index with
  `idx_generations_output_key` on `output_key` alone. `record()`'s
  `ON CONFLICT(output_key)` now updates every non-key column (built
  programmatically from the row dict) so no column can silently retain a
  stale value. `files`/`thumb_rel` continue to be replaced wholesale, not
  merged.
- Added `GalleryStore._migrate()`, run after schema creation in `_connect`:
  backfills `output_key` for legacy rows from their stored `files` JSON,
  drops the old unique index, deletes rows whose key can't be derived,
  collapses duplicates by `output_key` keeping the newest
  (`created_at DESC, id DESC`), then creates the new unique index. No-op on
  a fresh database.
- `tests/test_history.py`: added tests for icon/transparent_bg regeneration
  collapsing to one row with the latest data, slugify-collision merging,
  genuinely-different artifacts (size/style/theme/category) staying
  separate, `created_at` bump on update, and a migration test that builds an
  old-schema DB with a pre-existing duplicate and asserts it converges to
  one row under a working `output_key` index.

### Existing test that encoded the bug

`test_differing_settings_create_separate_rows` varied only `theme` while
reusing the same hardcoded file path for both payloads — an artifact of the
old settings-tuple identity that doesn't reflect how the renderer actually
names files (theme changes the filename too). Updated it to give each
settings variant (theme/style/size/category) its own realistic file path, so
it now asserts genuinely distinct artifacts stay separate rather than
accidentally asserting the old buggy dedup granularity.

## Gate

- `uv run pytest -q`: `197 passed, 1 warning in 5.30s`
- `uv build`: `Successfully built dist\homelab_icon_generator-0.1.0.tar.gz` /
  `Successfully built dist\homelab_icon_generator-0.1.0-py3-none-any.whl`
- `git diff --check`: only CRLF-normalization warnings, no whitespace errors

## Reproduction (post-fix)

```
rows: 1
  generic cloud_service /output/svg/cloud_service/nextcloud-minimal-blue-256.svg
```

One row, reflecting the latest (`generic`) generation — the stale `auto`
duplicate is gone.
