# Custom Hue Theme Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Execution override (2026-08-07):** The user requested inline implementation
> without subagents or TDD. Implement each task directly, then add and run its
> focused tests before advancing to the next task.

**Goal:** Add a sixth custom theme to the Hue selector that uses a compact native color picker and generates a complete deterministic palette from any selected `#RRGGBB` color.

**Architecture:** Preserve the five static palettes and represent user colors as `theme="custom"` plus an optional `custom_color` request field. Central color helpers validate, normalize, and derive a `ColorPalette`; renderer, API, CLI, history, and frontend pass that value explicitly, with the normalized hex included in custom output filenames.

**Tech Stack:** Python 3.10+, standard-library `colorsys`, FastAPI/Pydantic, SQLite, vanilla HTML/CSS/JavaScript, pytest, UV.

## Global Constraints

- Preserve the existing green, blue, orange, purple, and grayscale palette values exactly.
- Accept custom colors only as one leading `#` plus exactly six hexadecimal digits.
- Use `#00b8a9` as the initial custom color.
- The selected custom color is the exact palette accent; derived HSL lightness values are background 8%, foreground 24%, and text 88%.
- HSL-to-RGB conversion rounds each channel to the nearest integer and emits lowercase hex.
- Preset requests must omit `custom_color`; custom requests must provide it.
- Custom output basenames must include normalized hex digits without `#`.
- Do not add dependencies, saved theme libraries, palette editing, or automatic generation on picker movement.
- The user still presses Generate after selecting a custom hue.

## File Structure

- `app/generator/colors.py`: color syntax normalization and deterministic custom palette derivation.
- `app/models/icon_request.py`: optional custom color in the domain request.
- `app/utils/validation.py`: valid request combinations for preset and custom themes.
- `app/generator/renderer.py`: custom-aware cached style resolution and collision-free output names.
- `app/main.py`: single and batch CLI transport for `custom_color`.
- `app/web/schemas.py`: web request shape.
- `app/web/api.py`: request wiring and normalized response metadata.
- `app/web/history.py`: nullable history persistence and idempotent migration.
- `app/web/static/index.html`: custom color editor markup.
- `app/web/static/app.js`: custom theme state, payload, CLI, readout, and restoration behavior.
- `app/web/static/app.css`: compact custom swatch/editor styling across desktop and mobile.
- `README.md`: user-facing custom theme and CLI example.
- `tests/test_renderer.py`: palette, validation, rendering, and filename coverage.
- `tests/test_cli.py`: CLI and batch wiring.
- `tests/test_server.py`: options, generation metadata, SVG color, and accessible markup.
- `tests/test_history.py`: custom color round-trip and legacy schema migration.

---

### Task 1: Custom Theme Domain and Renderer

**Files:**
- Modify: `app/generator/colors.py`
- Modify: `app/models/icon_request.py`
- Modify: `app/utils/validation.py`
- Modify: `app/generator/renderer.py`
- Test: `tests/test_renderer.py`

**Interfaces:**
- Produces: `CUSTOM_THEME: str`, `DEFAULT_CUSTOM_COLOR: str`, `normalize_hex_color(value: str) -> str`, `derive_custom_palette(value: str) -> ColorPalette`, and `get_palette(theme: str, custom_color: str | None = None) -> ColorPalette`.
- Produces: `IconRequest.custom_color: str | None`.
- Produces: `_resolve_style(style_name: str, theme: str, custom_color: str | None = None) -> StyleDefinition`.
- Consumes: Existing `ColorPalette`, preset `COLOR_THEMES`, and request validation pipeline.

- [ ] **Step 1: Write failing color and validation tests**

Add imports and tests to `tests/test_renderer.py`:

```python
from pathlib import Path

from app.generator.colors import (
    COLOR_THEMES,
    derive_custom_palette,
    normalize_hex_color,
)
from app.utils.validation import validate_request


def test_custom_color_is_normalized_and_drives_palette() -> None:
    assert normalize_hex_color("#00B8A9") == "#00b8a9"
    palette = derive_custom_palette("#00B8A9")
    assert palette.accent == "#00b8a9"
    assert palette.bg == "#002925"
    assert palette.fg == "#007a70"
    assert palette.text == "#c2fffa"


@pytest.mark.parametrize("value", ["00b8a9", "#abc", "#00b8a9ff", "#00b8ag"])
def test_custom_color_rejects_non_canonical_hex(value: str) -> None:
    with pytest.raises(ValueError, match="custom_color must match"):
        normalize_hex_color(value)


def test_custom_theme_requires_color_and_presets_reject_it() -> None:
    with pytest.raises(ValueError, match="requires custom_color"):
        validate_request(IconRequest(name="Node", category="server", theme="custom"))
    with pytest.raises(ValueError, match="only valid when theme is 'custom'"):
        validate_request(
            IconRequest(
                name="Node", category="server", theme="blue", custom_color="#00b8a9"
            )
        )
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `uv run pytest -q tests/test_renderer.py -k "custom_color or custom_theme"`

Expected: collection fails because the new color helpers and request field do not exist.

- [ ] **Step 3: Implement normalization and deterministic palette derivation**

In `app/generator/colors.py`, add `colorsys`, `re`, constants, and helpers. Keep the five existing entries unchanged:

```python
CUSTOM_THEME = "custom"
DEFAULT_CUSTOM_COLOR = "#00b8a9"
_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def normalize_hex_color(value: str) -> str:
    if not isinstance(value, str) or _HEX_COLOR.fullmatch(value) is None:
        raise ValueError("custom_color must match #RRGGBB")
    return value.lower()


def _hls_hex(hue: float, saturation: float, lightness: float) -> str:
    red, green, blue = colorsys.hls_to_rgb(hue, lightness, saturation)
    channels = (round(red * 255), round(green * 255), round(blue * 255))
    return "#" + "".join(f"{channel:02x}" for channel in channels)


def derive_custom_palette(value: str) -> ColorPalette:
    accent = normalize_hex_color(value)
    red, green, blue = (
        int(accent[index:index + 2], 16) / 255 for index in (1, 3, 5)
    )
    hue, _, saturation = colorsys.rgb_to_hls(red, green, blue)
    return ColorPalette(
        bg=_hls_hex(hue, saturation, 0.08),
        fg=_hls_hex(hue, saturation, 0.24),
        accent=accent,
        text=_hls_hex(hue, saturation, 0.88),
    )
```

Change `get_palette` to accept `custom_color=None`, return `derive_custom_palette(custom_color)` for `theme == CUSTOM_THEME`, and retain the current unknown-preset error for other values.

- [ ] **Step 4: Add the request field and combination validation**

Add `custom_color: str | None = None` immediately after `theme` in `IconRequest`. In `app/utils/validation.py`, define:

```python
from app.generator.colors import COLOR_THEMES, CUSTOM_THEME, normalize_hex_color

VALID_THEMES = set(COLOR_THEMES) | {CUSTOM_THEME}
```

After the existing theme membership check, validate:

```python
if request.theme == CUSTOM_THEME:
    if request.custom_color is None:
        raise ValueError("theme 'custom' requires custom_color")
    normalize_hex_color(request.custom_color)
elif request.custom_color is not None:
    raise ValueError("custom_color is only valid when theme is 'custom'")
```

- [ ] **Step 5: Wire normalized colors into style caching and filenames**

Update `_resolve_style` to accept the optional color and call `get_palette(theme, custom_color)`. In `generate_icon_result`, normalize only for the custom theme, pass the value into `_resolve_style`, and pass it to `_output_base`. Change `_output_base` to accept the normalized value and emit:

```python
theme_part = request.theme
if request.theme == CUSTOM_THEME and custom_color is not None:
    theme_part = f"custom-{custom_color.removeprefix('#')}"
return f"{slug}-{request.style}-{theme_part}-{request.size}"
```

Update the test helpers in `tests/test_renderer.py` to pass `request.custom_color` into `_resolve_style`. Change `THEMES` to `sorted(COLOR_THEMES)` so the preset matrix does not construct an invalid colorless custom request, and change `test_every_theme_defined` to assert `set(COLOR_THEMES) == VALID_THEMES - {"custom"}`.

- [ ] **Step 6: Add rendering and output identity tests**

```python
def test_custom_theme_renders_exact_accent_and_distinct_output_names(tmp_path) -> None:
    first = IconRequest(
        name="Node", category="server", theme="custom", custom_color="#00B8A9",
        format="svg", output_dir=str(tmp_path),
    )
    second = IconRequest(
        name="Node", category="server", theme="custom", custom_color="#ff0066",
        format="svg", output_dir=str(tmp_path),
    )
    first_path = generate_icon(first)["svg"]
    second_path = generate_icon(second)["svg"]
    assert first_path.endswith("node-minimal-custom-00b8a9-256.svg")
    assert second_path.endswith("node-minimal-custom-ff0066-256.svg")
    assert first_path != second_path
    assert '#00b8a9' in Path(first_path).read_text(encoding="utf-8")
```

- [ ] **Step 7: Run domain and renderer tests**

Run: `uv run pytest -q tests/test_renderer.py tests/test_svg_composer.py`

Expected: all tests pass, including the unchanged preset matrix.

- [ ] **Step 8: Commit the domain slice**

```bash
git add app/generator/colors.py app/models/icon_request.py app/utils/validation.py app/generator/renderer.py tests/test_renderer.py
git commit -m "feat: derive palettes from custom hues"
```

---

### Task 2: CLI, API, and Persistent History Transport

**Files:**
- Modify: `app/main.py`
- Modify: `app/web/schemas.py`
- Modify: `app/web/api.py`
- Modify: `app/web/history.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_server.py`
- Test: `tests/test_history.py`

**Interfaces:**
- Consumes: `IconRequest.custom_color`, `CUSTOM_THEME`, and `normalize_hex_color` from Task 1.
- Produces: CLI flag `--custom-color`, JSON request/response field `custom_color`, and nullable SQLite column `custom_color`.

- [ ] **Step 1: Write failing CLI transport tests**

Extend the `Namespace` in `test_single_request_passes_icon_to_generator` with `custom_color=None`, then add:

```python
def test_single_request_passes_custom_color_to_generator(monkeypatch, tmp_path: Path) -> None:
    captured = []
    monkeypatch.setattr(cli, "generate_icon", lambda request: captured.append(request) or {})
    args = Namespace(
        name="Node", category="server", style="minimal", theme="custom",
        custom_color="#00B8A9", size=128, format="svg", icon="generic",
        transparent=False, output_dir=str(tmp_path),
    )
    cli.run_single(args)
    assert captured[0].custom_color == "#00B8A9"


def test_batch_entry_passes_custom_color_to_generator(monkeypatch, tmp_path: Path) -> None:
    batch = tmp_path / "icons.json"
    batch.write_text(json.dumps([{
        "name": "Node", "category": "server", "theme": "custom",
        "custom_color": "#00b8a9",
    }]), encoding="utf-8")
    captured = []
    monkeypatch.setattr(cli, "generate_icon", lambda request: captured.append(request) or {})
    cli.run_batch(str(batch), str(tmp_path))
    assert captured[0].custom_color == "#00b8a9"
```

- [ ] **Step 2: Write failing API and history tests**

Add to `tests/test_server.py`:

```python
def test_generate_custom_theme_returns_normalized_color_and_colored_svg(client) -> None:
    response = client.post("/api/generate", json={
        "name": "Node", "category": "server", "theme": "custom",
        "custom_color": "#00B8A9", "format": "svg",
    })
    data = response.json()
    assert response.status_code == 200
    assert data["theme"] == "custom"
    assert data["custom_color"] == "#00b8a9"
    assert "custom-00b8a9" in data["files"]["svg"]
    svg = client.get(data["files"]["svg"]).text
    assert '#00b8a9' in svg


def test_generate_rejects_invalid_custom_theme_combinations(client) -> None:
    missing = client.post("/api/generate", json={
        "name": "Node", "category": "server", "theme": "custom",
    })
    misplaced = client.post("/api/generate", json={
        "name": "Node", "category": "server", "theme": "blue",
        "custom_color": "#00b8a9",
    })
    assert missing.status_code == 400
    assert misplaced.status_code == 400
```

Update `_payload()` in `tests/test_history.py` with `"custom_color": None`, and add:

```python
def test_custom_color_round_trips(store) -> None:
    gallery, output_dir = store
    payload = _payload(
        theme="custom",
        custom_color="#00b8a9",
        files={"svg": "/output/svg/server/node-custom-00b8a9.svg"},
    )
    _touch(output_dir, payload["files"]["svg"])
    gallery.record(payload)

    item = gallery.recent()[0]
    assert item["theme"] == "custom"
    assert item["custom_color"] == "#00b8a9"
```

In `test_migration_collapses_pre_existing_duplicates_and_rebuilds_the_index`,
after reading `items`, add:

```python
columns = {
    row["name"]
    for row in gallery._conn.execute("PRAGMA table_info(generations)").fetchall()
}
assert "custom_color" in columns
assert items[0]["custom_color"] is None
```

- [ ] **Step 3: Run focused transport tests and verify they fail**

Run: `uv run pytest -q tests/test_cli.py tests/test_server.py tests/test_history.py -k "custom or migration"`

Expected: failures show missing request, response, and persistence wiring.

- [ ] **Step 4: Implement CLI and API transport**

In `app/main.py`, add:

```python
parser.add_argument(
    "--custom-color",
    type=str,
    default=None,
    help='Custom theme color as "#RRGGBB" (requires --theme custom)',
)
```

Pass `custom_color=getattr(args, "custom_color", None)` in `run_single` and `entry.get("custom_color")` in `run_batch`. Add `custom_color: str | None = None` to `GenerateRequest`, pass it into `IconRequest`, and return a normalized `custom_color` for custom responses or `None` for presets.

- [ ] **Step 5: Add the nullable history column and migration**

Add `custom_color TEXT` after `theme TEXT NOT NULL` in `_SCHEMA`. In `_migrate`, query columns and run the following before output-key migration:

```python
if "custom_color" not in columns:
    conn.execute("ALTER TABLE generations ADD COLUMN custom_color TEXT")
    conn.commit()
```

Add `"custom_color": payload.get("custom_color")` to `record()`'s row. `recent()` already returns all non-file columns, so no custom serializer is needed.

- [ ] **Step 6: Run transport and migration tests**

Run: `uv run pytest -q tests/test_cli.py tests/test_server.py tests/test_history.py`

Expected: all CLI, API, history, legacy migration, and interrupted migration tests pass.

- [ ] **Step 7: Commit the transport slice**

```bash
git add app/main.py app/web/schemas.py app/web/api.py app/web/history.py tests/test_cli.py tests/test_server.py tests/test_history.py
git commit -m "feat: carry custom hues across interfaces"
```

---

### Task 3: Mini Color Picker and Gallery Restoration

**Files:**
- Modify: `app/web/static/index.html`
- Modify: `app/web/static/app.js`
- Modify: `app/web/static/app.css`
- Modify: `app/web/static/gallery.js`
- Modify: `README.md`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `/api/options` theme `custom`, `/api/generate` `custom_color`, and history `custom_color` from Task 2.
- Produces: `state.customColor`, `setCustomColor(value: string)`, a custom swatch button, and a native `#customColor` input with visible `#customColorValue` readout.

- [ ] **Step 1: Write failing static UI contract tests**

Extend `test_page_has_accessible_override_controls_and_no_external_fonts` or add a focused test:

```python
def test_page_has_accessible_custom_color_editor(client) -> None:
    page = client.get("/").text
    assert 'id="customColor"' in page
    assert 'type="color"' in page
    assert 'id="customColorValue"' in page
    assert 'aria-label="Choose custom theme color"' in page
```

Add `assert "custom" in client.get("/api/options").json()["themes"]` to the options test.

- [ ] **Step 2: Run the UI contract tests and verify they fail**

Run: `uv run pytest -q tests/test_server.py -k "custom_color_editor or options"`

Expected: the custom editor markup assertion fails.

- [ ] **Step 3: Add compact editor markup and styling**

Immediately after `<div class="theme-row" id="themes"></div>` in `index.html`, add:

```html
<div class="custom-color-editor" id="customColorEditor" hidden>
  <label for="customColor">CUSTOM SIGNAL</label>
  <input type="color" id="customColor" value="#00b8a9"
         aria-label="Choose custom theme color">
  <output id="customColorValue" for="customColor">#00b8a9</output>
</div>
```

In CSS, keep the six swatches in the current single row, make the custom pip
use its button's inline `--swatch` value, and add:

```css
.custom-color-editor {
  display: grid;
  grid-template-columns: 1fr 38px auto;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  padding: 7px 8px;
  border: 1px solid var(--rule);
  background: var(--bg);
}
.custom-color-editor[hidden] { display: none; }
.custom-color-editor label,
.custom-color-editor output {
  color: var(--ink-dim);
  font-size: 8px;
  letter-spacing: .12em;
  text-transform: uppercase;
}
.custom-color-editor output {
  color: var(--amber-hot);
  font-variant-numeric: tabular-nums;
}
.custom-color-editor input[type="color"] {
  width: 38px;
  min-height: 32px;
  padding: 2px;
  border: 1px solid var(--rule-hi);
  background: var(--panel-hi);
  cursor: pointer;
}
```

The global `input:focus-visible` rule supplies the focus ring. At the existing
mobile breakpoint, retain the same three columns; the 38px color input already
exceeds the 32px minimum touch target and does not widen the controls panel.

- [ ] **Step 4: Implement custom theme state and events**

Add `customColor: "#00b8a9"` to `state`. In `renderThemes()`, keep preset button creation, but for `custom` set the pip style with `--swatch: ${state.customColor}` and label it `cus`. The custom button handler must call:

```javascript
setTheme("custom");
$("customColor").click();
```

Update `setTheme(v)` to toggle `customColorEditor.hidden`, refresh the custom pip, and synchronize CLI. Implement:

```javascript
function setCustomColor(value) {
  state.customColor = value.toLowerCase();
  $("customColor").value = state.customColor;
  $("customColorValue").textContent = state.customColor;
  document.querySelector('[data-theme="custom"]')
    ?.style.setProperty("--swatch", state.customColor);
  setTheme("custom");
}

$("customColor").addEventListener("input", (event) => {
  setCustomColor(event.target.value);
});
```

In `syncCli`, append `--custom-color "${state.customColor}"` only for the custom theme. In the generate payload, send `custom_color: state.theme === "custom" ? state.customColor : null`. In the build log/readout, display `CUSTOM ${data.custom_color.toUpperCase()}` for custom builds and retain current preset labels.

- [ ] **Step 5: Restore custom colors from gallery records**

In `Gallery.restore(record)`, before `setTheme(record.theme)`, add:

```javascript
if (record.theme === "custom" && record.custom_color) {
  setCustomColor(record.custom_color);
}
```

Then call `setTheme(record.theme)` as today. Do not open the native picker during restore; only the custom swatch's direct click handler opens it.

- [ ] **Step 6: Update user documentation**

Change README's “five color themes” wording to “five color presets plus a custom hue picker.” Add one CLI example:

```bash
uv run python main.py --name "Router" --category router --theme custom --custom-color "#00b8a9"
```

- [ ] **Step 7: Run web and documentation checks**

Run: `uv run pytest -q tests/test_server.py tests/test_history.py tests/test_cli.py`

Run: `git diff --check`

Expected: all focused tests pass and no whitespace errors are reported.

- [ ] **Step 8: Commit the frontend slice**

```bash
git add app/web/static/index.html app/web/static/app.js app/web/static/app.css app/web/static/gallery.js README.md tests/test_server.py
git commit -m "feat: add custom hue picker to web UI"
```

---

### Task 4: End-to-End Verification

**Files:**
- Modify only if a verification failure reveals a scoped defect in files already listed above.

**Interfaces:**
- Consumes: The complete custom hue flow from Tasks 1-3.
- Produces: Verified preset compatibility, custom artifact generation, gallery restore behavior, and responsive picker UI.

- [ ] **Step 1: Run the complete automated test suite**

Run: `uv run pytest -q`

Expected: every test passes.

- [ ] **Step 2: Build the distributable package**

Run: `uv build`

Expected: source and wheel builds complete successfully.

- [ ] **Step 3: Start the local web application**

Run: `uv run uvicorn app.web.api:app --host 127.0.0.1 --port 5000`

Expected: Uvicorn reports the application running on `http://127.0.0.1:5000`.

- [ ] **Step 4: Verify the custom flow in a browser at desktop and mobile widths**

At 1440x900 and 390x844, verify:

- all five preset swatches remain visible and selectable
- `CUSTOM` opens the native color picker and reveals the compact hex editor
- choosing `#ff0066` updates the custom swatch and hex readout
- Generate produces a visibly custom-colored artifact and `CUSTOM #FF0066` readout
- the CLI snippet includes `--theme custom --custom-color "#ff0066"`
- switching to blue hides the editor and omits `--custom-color`
- clicking the custom gallery tile restores `#ff0066` without opening the picker
- keyboard focus and selected states are visible
- the console contains no errors

- [ ] **Step 5: Run final repository checks**

Run: `git diff --check`

Run: `git status --short`

Expected: no whitespace errors and only intentional changes, generated package artifacts already ignored by the repository.

- [ ] **Step 6: Commit any verification-only fixes**

If Step 4 required scoped fixes, list the changed files with `git status
--short`, verify each diff, stage those explicit paths (never a glob or the
whole tree), and commit:

```bash
git add app/generator/colors.py app/models/icon_request.py app/utils/validation.py app/generator/renderer.py app/main.py app/web/schemas.py app/web/api.py app/web/history.py app/web/static/index.html app/web/static/app.js app/web/static/app.css app/web/static/gallery.js README.md tests/test_renderer.py tests/test_cli.py tests/test_server.py tests/test_history.py
git commit -m "fix: polish custom hue interactions"
```

If no fixes were needed, do not create an empty commit.
