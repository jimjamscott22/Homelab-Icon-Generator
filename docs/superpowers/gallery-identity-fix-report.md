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

```text
rows: 1
  generic cloud_service /output/svg/cloud_service/nextcloud-minimal-blue-256.svg
```

One row, reflecting the latest (`generic`) generation — the stale `auto`
duplicate is gone.

## Behavior worth flagging (not a bug)

Regenerating the same settings with `format=png` then `format=svg` now
collapses to one gallery row, and the PNG stops being offered on the tile
even though the file is still on disk. This is intentional — `files` is
replaced wholesale rather than merged, because a leftover artifact from an
earlier `format`/`icon`/`transparent_bg` could be stale — but it's a
user-visible change from the pre-fix behavior (which, via its own bug,
happened to keep both as separate rows) and shouldn't be mistaken for an
oversight later.

## Review round 2 (commit 505857b -> this commit)

Two Important issues found in review, both fixed here; two Minor issues also
fixed.

**Finding 1 (Important) — interrupted migration could delete legacy
history.** The backfill gate was `if "output_key" not in columns:`, wrapping
both `ALTER TABLE ... ADD COLUMN` and the per-row backfill `UPDATE`s. SQLite
DDL autocommits `ALTER TABLE` independently of Python's `sqlite3` implicit
transaction (which only opens at the first DML statement), so a process
killed between the ALTER and the backfill `commit()` left the column present
but every value NULL. On the next open, the gate saw the column and skipped
backfilling — and the unkeyable-row cleanup then deleted every row. Fixed by
decoupling: the `ALTER` still runs once, gated and committed immediately,
but the backfill query now runs unconditionally on every `_connect`, scoped
to `WHERE output_key IS NULL OR output_key = ''`, so an interrupted
migration resumes instead of being mistaken for "already done." Covered by
new test `test_interrupted_migration_recovers_instead_of_deleting_rows`,
which reproduces the exact sequence (ALTER + commit, no backfill, close,
reopen) and asserts both legacy rows survive with correct keys.

**Finding 2 (Important) — `gallery.js`'s client dedup key regressed.**
`_recordKey` still joined the old 8-field settings tuple, which is no longer
a stable row identity now that `format`/`transparent_bg`/`icon` are mutable
server-side on the same row. A row updated between page-1 and page-2 of
`/api/history` changed its client key and escaped dedup — the exact bug
commit `afeb090` had fixed, from the other direction. Fixed by changing
`_recordKey` to return `record.output_key` (already present on every item
from `recent()`). Confirmed no other identity logic exists in `gallery.js`.

**Finding 3 (Minor) — `_derive_output_key` could raise on a tampered DB.**
A non-string entry in a row's `files` mapping raised `TypeError`, which
`_connect`'s corruption handler doesn't catch (only `sqlite3.DatabaseError`
is caught there), disabling the gallery outright instead of quarantining
and rebuilding like every other corruption path. Fixed with an
`isinstance(rel, str)` guard in `_derive_output_key` so malformed entries
are skipped and treated as unkeyable.

**Finding 4 (Minor) — report committed at a removed scratch path.** Moved
from `.superpowers/gallery-identity-fix-report.md` (gitignored locally,
and the equivalent top-level dir was deleted from main in `a6a5156`) to
`docs/superpowers/gallery-identity-fix-report.md`, alongside the existing
`docs/superpowers/{plans,specs}`.

**Also adjusted:** the pre-existing migration test's fixture now puts the
newer `created_at` on the lower-`id` row (previously both moved together),
so it actually discriminates the `created_at DESC, id DESC` ordering clause
instead of passing whether or not `id` were used alone.

### Gate (re-run)

- `uv run pytest -q`: `198 passed, 1 warning in 4.66s`
- `uv build`: `Successfully built dist\homelab_icon_generator-0.1.0.tar.gz` /
  `Successfully built dist\homelab_icon_generator-0.1.0-py3-none-any.whl`
- `git diff --check`: only CRLF-normalization warnings, no whitespace errors

### Reproduction (re-run, post round-2 fix)

```text
rows: 1
  generic cloud_service /output/svg/cloud_service/nextcloud-minimal-blue-256.svg
```
