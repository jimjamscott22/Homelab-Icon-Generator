# Hybrid Brand Icon System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add accurate offline brand detection and custom SVG overrides while retaining single-source procedural fallbacks and identical SVG, PNG, and ICO geometry.

**Architecture:** Resolve each request to a normalized `VectorIcon`, compose one authoritative SVG, and rasterize that SVG with `resvg_py`. A pinned Simple Icons registry and sanitized custom registry feed a conservative resolver; generic definitions remain the deterministic fallback.

**Tech Stack:** Python 3.10+, UV, dataclasses, defusedxml, resvg_py 0.3.3, Pillow, Flask, vanilla HTML/CSS/JavaScript, pytest

## Global Constraints

- Normal generation performs no network access.
- `icon` defaults to `auto`; `generic` forces the category; any other value is an explicit stable key.
- Exact names and reviewed aliases may auto-resolve; fuzzy matches are suggestions only.
- Custom entries override built-in entries and branded/custom icons omit initials.
- Generic categories and category-based output paths remain backward compatible.
- SVG is authoritative; PNG and ICO derive from the same SVG composition.
- Custom SVG rejects active content, external resources, embedded images, text, and unsupported references.
- Canvas size remains 32-2048; ICO remains limited to 256.
- Each task ends with focused verification and an independently reviewable commit.

---

### Task 1: Normalized vector model and safe serializer

**Files:**
- Create: `app/icons/__init__.py`
- Create: `app/icons/models.py`
- Create: `app/icons/svg.py`
- Create: `tests/test_vector_svg.py`

**Interfaces:**
- Consumes: `StyleDefinition` colors only through caller-provided serializer arguments.
- Produces: `VectorNode`, `VectorIcon`, `IconResolution`, `serialize_nodes(nodes, color) -> str`.

- [ ] **Step 1: Write the failing model and serialization tests**

```python
@pytest.fixture
def sample_icon():
    return VectorIcon(
        key="test", title="Test", source="fixture", view_box=(0, 0, 24, 24),
        nodes=(VectorNode("path", {"d": "M0 0h24v24z", "fill-rule": "evenodd"}),),
    )

def test_serialize_path_uses_requested_color_and_escapes_attributes(sample_icon):
    assert serialize_nodes(sample_icon.nodes, "#4fc3f7") == (
        '<path d="M0 0h24v24z" fill="#4fc3f7" fill-rule="evenodd"/>'
    )

def test_resolution_exposes_fallback_and_initials_policy(sample_icon):
    result = IconResolution(icon=sample_icon, match_method="generic", query="unknown", used_fallback=True)
    assert result.show_initials is True
```

- [ ] **Step 2: Verify the tests fail**

Run: `uv run pytest tests/test_vector_svg.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.icons'`.

- [ ] **Step 3: Implement immutable vector types and deterministic XML serialization**

```python
@dataclass(frozen=True)
class VectorNode:
    tag: Literal["path", "rect", "circle", "ellipse", "line", "polygon", "polyline", "g"]
    attrs: Mapping[str, str | int | float] = field(default_factory=dict)
    children: tuple["VectorNode", ...] = ()

@dataclass(frozen=True)
class VectorIcon:
    key: str
    title: str
    source: str
    view_box: tuple[float, float, float, float]
    nodes: tuple[VectorNode, ...]
    aliases: tuple[str, ...] = ()
    source_url: str | None = None
    license: str | None = None
    guidelines_url: str | None = None

@dataclass(frozen=True)
class IconResolution:
    icon: VectorIcon
    match_method: Literal["explicit", "custom", "catalog", "normalized", "generic"]
    query: str
    used_fallback: bool

    @property
    def show_initials(self) -> bool:
        return self.match_method == "generic"

def serialize_nodes(nodes: tuple[VectorNode, ...], color: str) -> str:
    return "\n".join(_serialize_node(node, color) for node in nodes)

def _serialize_node(node: VectorNode, color: str) -> str:
    attrs = dict(node.attrs)
    if node.tag == "line":
        attrs.setdefault("stroke", color)
    elif node.tag != "g":
        attrs.setdefault("fill", color)
    attrs = {name: color if value == "currentColor" else value for name, value in attrs.items()}
    rendered = " ".join(f"{name}={quoteattr(str(value))}" for name, value in sorted(attrs.items()))
    if node.children:
        children = "".join(_serialize_node(child, color) for child in node.children)
        return f"<{node.tag} {rendered}>{children}</{node.tag}>"
    return f"<{node.tag} {rendered}/>"
```

Permit only the declared tags and an attribute allowlist per tag. Sort emitted
attributes, XML-escape values, inject the selected color into fill/stroke, and
serialize groups recursively.

- [ ] **Step 4: Run focused tests and the existing suite**

Run: `uv run pytest tests/test_vector_svg.py tests/test_renderer.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/icons tests/test_vector_svg.py
git commit -m "feat: add normalized vector icon model"
```

### Task 2: Single-source generic icons and SVG composer

**Files:**
- Create: `app/icons/generic/__init__.py`
- Create: `app/icons/generic/infrastructure.py`
- Create: `app/icons/generic/devices.py`
- Create: `app/icons/generic/services.py`
- Create: `app/generator/svg_composer.py`
- Modify: `app/styles/base.py`
- Modify: `app/styles/minimal.py`
- Modify: `app/styles/terminal.py`
- Modify: `app/styles/cyberpunk.py`
- Modify: `app/generator/layouts.py`
- Test: `tests/test_generic_icons.py`
- Test: `tests/test_svg_composer.py`

**Interfaces:**
- Consumes: `VectorIcon`, `VectorNode`, `serialize_nodes`, `IconRequest`, `StyleDefinition`, `LayoutSpec`.
- Produces: `get_generic_icon(category: str) -> VectorIcon` and `compose_svg(request, style, layout, resolution) -> str`.

- [ ] **Step 1: Add failing coverage for all categories and initials policy**

```python
@pytest.mark.parametrize("category", sorted(VALID_CATEGORIES))
def test_every_category_has_one_vector_definition(category):
    assert get_generic_icon(category).key == category

def test_brand_is_centered_without_initials(brand_request, minimal_style, brand_layout, brand_resolution):
    svg = compose_svg(brand_request, minimal_style, brand_layout, brand_resolution)
    assert "<text" not in svg
    assert 'preserveAspectRatio="xMidYMid meet"' in svg

def test_generic_keeps_initials_and_fractional_frame_scaling(minimal_style, generic_resolution):
    small_request = IconRequest("NAS", "nas", size=64)
    large_request = IconRequest("NAS", "nas", size=256)
    small = compose_svg(small_request, minimal_style, get_layout(64), generic_resolution)
    large = compose_svg(large_request, minimal_style, get_layout(256), generic_resolution)
    assert "<text" in small
    assert 'stroke-width="0.5"' in small
    assert 'stroke-width="2"' in large
```

- [ ] **Step 2: Verify failure before migration**

Run: `uv run pytest tests/test_generic_icons.py tests/test_svg_composer.py -q`
Expected: FAIL because generic modules and `compose_svg` do not exist.

- [ ] **Step 3: Move all 24 SVG definitions into three focused registries**

```python
def compose_svg(
    request: IconRequest,
    style: StyleDefinition,
    layout: LayoutSpec,
    resolution: IconResolution,
) -> str:
    return SvgComposer(request.size).compose(request, style, layout, resolution)

GENERIC_ICONS = {
    **INFRASTRUCTURE_ICONS,
    **DEVICE_ICONS,
    **SERVICE_ICONS,
}

def get_generic_icon(category: str) -> VectorIcon:
    try:
        return GENERIC_ICONS[category]
    except KeyError as exc:
        raise ValueError(f"Unknown generic category '{category}'") from exc
```

Translate the existing `_svg_*` geometry exactly into normalized nodes, grouped
by domain. Move frame construction into `compose_svg`. Change style fields to
`border_width_ratio` and `corner_radius_ratio`, preserving the 256px appearance
with ratios `old_value / 256`.

- [ ] **Step 4: Verify every category and style**

Run: `uv run pytest tests/test_generic_icons.py tests/test_svg_composer.py tests/test_renderer.py -q`
Expected: PASS with 24 category cases and all style/theme cases.

- [ ] **Step 5: Commit**

```bash
git add app/icons/generic app/generator/svg_composer.py app/generator/layouts.py app/styles tests/test_generic_icons.py tests/test_svg_composer.py
git commit -m "refactor: make generic icons SVG-first"
```

### Task 3: Rasterizer and output orchestration

**Files:**
- Create: `app/generator/rasterizer.py`
- Modify: `app/generator/renderer.py`
- Modify: `pyproject.toml`
- Delete after parity tests pass: `app/generator/symbols.py`
- Delete after parity tests pass: `app/generator/shapes.py`
- Delete after parity tests pass: `app/generator/text_utils.py`
- Test: `tests/test_rasterizer.py`
- Test: `tests/test_renderer.py`

**Interfaces:**
- Consumes: `compose_svg(...) -> str`, `IconResolution`.
- Produces: `rasterize_svg(svg, width, height) -> Image.Image`, `GenerationResult`, `generate_icon_result(request, resolver=None)`, backward-compatible `generate_icon(request) -> dict[str, str]`.

- [ ] **Step 1: Add failing parity and output-wrapper tests**

```python
def test_rasterize_svg_returns_rgba_at_requested_size():
    image = rasterize_svg('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><rect width="1" height="1" fill="#fff"/></svg>', 96, 96)
    assert image.mode == "RGBA"
    assert image.size == (96, 96)

def test_generate_icon_wrapper_preserves_paths_dict(tmp_path):
    request = IconRequest("NAS", "nas", format="both", output_dir=str(tmp_path))
    paths = generate_icon(request)
    assert set(paths) == {"png", "svg"}
```

- [ ] **Step 2: Add locked dependencies and verify the test fails at the missing adapter**

Run: `uv add "resvg-py==0.3.3" "defusedxml>=0.7.1,<0.8"`
Run: `uv run pytest tests/test_rasterizer.py -q`
Expected: FAIL because `rasterize_svg` does not exist.

- [ ] **Step 3: Implement in-memory rasterization and replace Pillow drawing**

```python
def rasterize_svg(svg: str, width: int, height: int) -> Image.Image:
    png = resvg_py.svg_to_bytes(svg_string=svg, width=width, height=height)
    image = Image.open(BytesIO(png))
    image.load()
    return image.convert("RGBA")

@dataclass(frozen=True)
class GenerationResult:
    paths: dict[str, str]
    resolution: IconResolution
```

Compose SVG once per request. Write it directly when requested, rasterize it once
for PNG/ICO, and keep `generate_icon` as `generate_icon_result(request).paths`.
Remove obsolete Pillow symbol drawing and the duplicated SVG functions only after
the full renderer suite passes. Remove the unused `svgwrite` dependency.

- [ ] **Step 4: Verify formats, parity, and package build**

Run: `uv run pytest tests/test_rasterizer.py tests/test_renderer.py -q`
Run: `uv build`
Expected: tests PASS and wheel/sdist build successfully.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml app/generator tests/test_rasterizer.py tests/test_renderer.py
git commit -m "feat: rasterize icons from authoritative SVG"
```

### Task 4: Pinned Simple Icons catalog and cached registry

**Files:**
- Create: `scripts/sync_simple_icons.py`
- Create: `app/icons/catalog.py`
- Create: `app/icons/registry.py`
- Create: `app/icons/data/__init__.py`
- Create: `app/icons/data/simple-icons.json`
- Create: `app/icons/data/catalog-manifest.json`
- Create: `app/icons/data/homelab-aliases.json`
- Create: `docs/THIRD_PARTY_ICONS.md`
- Create: `tests/fixtures/simple-icons-package/`
- Test: `tests/test_catalog_sync.py`
- Test: `tests/test_registry.py`

**Interfaces:**
- Consumes: Simple Icons 16.27.0 package metadata and `VectorIcon`.
- Produces: `CatalogSyncResult`, `sync_catalog(source_dir, version, output_dir)`, `load_builtin_registry()`, `CatalogRegistry.get(key)`, `exact(query)`, and `suggest(query, limit=8)`.

- [ ] **Step 1: Write failing deterministic-import and registry tests**

```python
def test_sync_catalog_is_deterministic(tmp_path, simple_icons_source):
    first = sync_catalog(simple_icons_source, "16.27.0", tmp_path / "first")
    second = sync_catalog(simple_icons_source, "16.27.0", tmp_path / "second")
    assert first.catalog_path.read_bytes() == second.catalog_path.read_bytes()

def test_registry_exact_alias_and_suggestions(catalog_records):
    registry = CatalogRegistry.from_records(catalog_records)
    assert registry.exact("home assistant").key == "homeassistant"
    assert registry.exact("ha") is None
    assert registry.suggest("home assist", limit=3)[0].key == "homeassistant"
```

- [ ] **Step 2: Verify the catalog tests fail**

Run: `uv run pytest tests/test_catalog_sync.py tests/test_registry.py -q`
Expected: FAIL because importer and registry modules do not exist.

- [ ] **Step 3: Implement the importer and immutable cached indexes**

```python
@dataclass(frozen=True)
class CatalogSyncResult:
    catalog_path: Path
    manifest_path: Path
    notice_path: Path

class CatalogRegistry:
    def __init__(self, icons: Mapping[str, VectorIcon], aliases: Mapping[str, str]):
        self._icons = dict(icons)
        self._aliases = dict(aliases)

    def get(self, key: str) -> VectorIcon | None:
        return self._icons.get(key)

    def exact(self, query: str) -> VectorIcon | None:
        key = self._aliases.get(query, query)
        return self._icons.get(key)

    def suggest(self, query: str, limit: int = 8) -> list[VectorIcon]:
        matches = difflib.get_close_matches(query, self._aliases, n=limit, cutoff=0.5)
        return [self._icons[self._aliases[name]] for name in matches]

@lru_cache(maxsize=1)
def load_builtin_registry() -> CatalogRegistry:
    payload = resources.files("app.icons.data").joinpath("simple-icons.json").read_text("utf-8")
    return CatalogRegistry.from_records(json.loads(payload)["icons"])
```

The CLI downloads the versioned npm archive when `--source-dir` is omitted and
records its SHA-256; tests pass the extracted fixture through `--source-dir`.
The sync script reads `_data/simple-icons.json` and `icons/<slug>.svg`, extracts
the path and `viewBox`, merges reviewed aliases, sorts all records and aliases,
records version plus SHA-256, and generates the third-party notice. Reject
duplicate normalized identifiers and malformed geometry before writing output.

- [ ] **Step 4: Generate and verify the pinned registry**

Run: `uv run python scripts/sync_simple_icons.py --version 16.27.0 --output app/icons/data`
Run: `uv run pytest tests/test_catalog_sync.py tests/test_registry.py -q`
Run: `uv build`
Expected: registry generation succeeds, tests PASS, and the manifest records
`16.27.0` with a non-empty SHA-256; the wheel contains all three JSON data files.

- [ ] **Step 5: Commit**

```bash
git add scripts app/icons/data app/icons/catalog.py app/icons/registry.py docs/THIRD_PARTY_ICONS.md tests/fixtures/simple-icons-package tests/test_catalog_sync.py tests/test_registry.py
git commit -m "feat: ship pinned offline brand catalog"
```

### Task 5: Conservative resolver, request field, and CLI controls

**Files:**
- Create: `app/icons/resolver.py`
- Modify: `app/models/icon_request.py`
- Modify: `app/utils/validation.py`
- Modify: `app/main.py`
- Modify: `app/generator/renderer.py`
- Test: `tests/test_resolver.py`
- Test: `tests/test_validation.py`
- Create: `tests/test_cli.py`

**Interfaces:**
- Consumes: `CatalogRegistry`, `get_generic_icon`, `IconRequest.icon`.
- Produces: `normalize_icon_name(value)`, `IconResolver.resolve(request) -> IconResolution`, `IconResolver.suggest(query, limit=8)`.

- [ ] **Step 1: Add failing matching and no-fuzzy-selection tests**

```python
@pytest.mark.parametrize("name", ["Nextcloud", "NEXTCLOUD", "Nextcloud Server"])
def test_known_name_resolves_catalog(name, resolver):
    result = resolver.resolve(IconRequest(name=name, category="server", icon="auto"))
    assert result.icon.key == "nextcloud"
    assert result.used_fallback is False

def test_near_match_is_only_a_suggestion(resolver):
    result = resolver.resolve(IconRequest(name="Nextclod", category="server", icon="auto"))
    assert result.icon.key == "server"
    assert result.used_fallback is True
    assert resolver.suggest("Nextclod")[0].key == "nextcloud"

def test_normalization_is_unicode_safe_and_offline(monkeypatch, resolver):
    monkeypatch.setattr(socket, "create_connection", lambda *args, **kwargs: pytest.fail("network used"))
    result = resolver.resolve(IconRequest(name="ＮＥＸＴＣＬＯＵＤ", category="server"))
    assert result.icon.key == "nextcloud"
```

- [ ] **Step 2: Verify the resolver tests fail**

Run: `uv run pytest tests/test_resolver.py tests/test_validation.py tests/test_cli.py -q`
Expected: FAIL because `IconRequest` has no `icon` and resolver is absent.

- [ ] **Step 3: Implement exact precedence and integrate all request paths**

```python
class IconResolver:
    def __init__(self, catalog: CatalogRegistry):
        self._catalog = catalog

    def resolve(self, request: IconRequest) -> IconResolution:
        query = normalize_icon_name(request.name)
        if request.icon == "generic":
            return self._generic(request, query, used_fallback=False)
        if request.icon != "auto":
            return self._explicit(request.icon, query)
        exact = self._catalog.exact(query) or self._catalog.exact(strip_deployment_suffix(query))
        return self._catalog_result(exact, query) if exact else self._generic(request, query, used_fallback=True)
```

Add `--icon` with default `auto`; pass `icon` through single and batch requests.
Unknown explicit keys raise `ValueError` containing up to three suggestions.
Wire `generate_icon_result` to a cached default resolver.

- [ ] **Step 4: Verify resolver, CLI, and existing requests**

Run: `uv run pytest tests/test_resolver.py tests/test_validation.py tests/test_cli.py tests/test_renderer.py -q`
Expected: PASS, including an old request without `icon`.

- [ ] **Step 5: Commit**

```bash
git add app/icons/resolver.py app/models/icon_request.py app/utils/validation.py app/main.py app/generator/renderer.py tests/test_resolver.py tests/test_validation.py tests/test_cli.py
git commit -m "feat: resolve service names to brand icons"
```

### Task 6: Sanitized custom icons and overrides

**Files:**
- Create: `app/icons/custom.py`
- Create: `custom-icons/README.md`
- Create: `custom-icons/manifest.example.json`
- Modify: `app/icons/registry.py`
- Modify: `app/icons/resolver.py`
- Modify: `app/main.py`
- Modify: `server.py`
- Test: `tests/fixtures/custom-icons/`
- Test: `tests/test_custom_icons.py`

**Interfaces:**
- Consumes: `VectorNode`, `VectorIcon`, built-in `CatalogRegistry`.
- Produces: `load_custom_registry(path) -> CustomRegistry`, `CombinedRegistry`, and structured `CustomIconDiagnostic` records.

- [ ] **Step 1: Add failing safe/unsafe SVG and override tests**

```python
UNSAFE_SVGS = [
    '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.com/x.png"/></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><path onclick="alert(1)" d="M0 0"/></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><foreignObject/></svg>',
]

def test_geometry_only_svg_loads(custom_dir):
    registry = load_custom_registry(custom_dir)
    assert registry.get("internal-api").source == "custom"

@pytest.mark.parametrize("payload", UNSAFE_SVGS)
def test_active_or_external_svg_is_rejected(tmp_path, payload):
    diagnostic = load_one_invalid_icon(tmp_path, payload)
    assert diagnostic.severity == "error"

def test_custom_alias_overrides_builtin(combined_registry):
    assert combined_registry.exact("nextcloud").source == "custom"
```

- [ ] **Step 2: Verify sanitizer tests fail**

Run: `uv run pytest tests/test_custom_icons.py -q`
Expected: FAIL because custom registry loading does not exist.

- [ ] **Step 3: Implement manifest validation and geometry-only parsing**

```python
root = DefusedET.fromstring(svg_text)
if root.tag != f"{{{SVG_NS}}}svg":
    raise CustomIconError("root element must be svg")
for element in root.iter():
    if local_name(element.tag) not in ALLOWED_TAGS:
        raise CustomIconError(f"unsupported element: {local_name(element.tag)}")
    if any(name.lower().startswith("on") for name in element.attrib):
        raise CustomIconError("event-handler attributes are not allowed")

@dataclass(frozen=True)
class CustomIconDiagnostic:
    key: str | None
    filename: str
    severity: Literal["warning", "error"]
    message: str

@dataclass(frozen=True)
class CustomRegistry:
    icons: Mapping[str, VectorIcon]
    aliases: Mapping[str, str]
    diagnostics: tuple[CustomIconDiagnostic, ...]

class CombinedRegistry:
    def __init__(self, custom: CustomRegistry, builtin: CatalogRegistry):
        self._custom = custom
        self._builtin = builtin

    def get(self, key: str) -> VectorIcon | None:
        return self._custom.icons.get(key) or self._builtin.get(key)

    def exact(self, query: str) -> VectorIcon | None:
        custom_key = self._custom.aliases.get(query, query)
        return self._custom.icons.get(custom_key) or self._builtin.exact(query)

    def suggest(self, query: str, limit: int = 8) -> list[VectorIcon]:
        custom = [icon for key, icon in self._custom.icons.items() if query in key]
        merged = {icon.key: icon for icon in [*custom, *self._builtin.suggest(query, limit)]}
        return list(merged.values())[:limit]
```

Validate finite transforms and the manifest schema. Directory precedence is
`--icon-dir`, `HOMELAB_ICON_DIR`, then `custom-icons`. Isolate invalid entries,
retain diagnostics by declared key so explicit invalid requests report the
specific reason, and let valid custom keys/aliases override built-ins.

Use this exact manifest shape:

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

- [ ] **Step 4: Verify custom behavior and security boundaries**

Run: `uv run pytest tests/test_custom_icons.py tests/test_resolver.py -q`
Expected: PASS with each rejected construct named in its diagnostic.

- [ ] **Step 5: Commit**

```bash
git add app/icons/custom.py app/icons/registry.py app/icons/resolver.py app/main.py server.py custom-icons tests/fixtures/custom-icons tests/test_custom_icons.py
git commit -m "feat: support sanitized custom icon overrides"
```

### Task 7: API metadata, catalog search, and web override UI

**Files:**
- Modify: `server.py`
- Modify: `app/web/static/index.html`
- Modify: `app/web/static/app.js`
- Modify: `app/web/static/app.css`
- Create: `tests/test_server.py`

**Interfaces:**
- Consumes: `generate_icon_result`, `IconResolver.suggest`, backend validation constants.
- Produces: `GET /api/options`, `GET /api/icons/search?q=`, generation metadata, detected-icon/override UI.

- [ ] **Step 1: Add failing Flask API tests**

```python
def test_options_exposes_all_backend_categories(client):
    assert set(client.get("/api/options").get_json()["categories"]) == VALID_CATEGORIES

def test_generate_reports_resolution(client):
    data = client.post("/api/generate", json={
        "name": "Nextcloud", "category": "cloud_service", "format": "svg",
    }).get_json()
    assert data["icon_key"] == "nextcloud"
    assert data["icon_source"] == "simple-icons"
    assert data["used_fallback"] is False

def test_search_returns_suggestions_without_selecting_them(client):
    data = client.get("/api/icons/search?q=Nextclod").get_json()
    assert data["items"][0]["key"] == "nextcloud"
```

- [ ] **Step 2: Verify endpoint tests fail**

Run: `uv run pytest tests/test_server.py -q`
Expected: FAIL because resolution metadata and search are absent.

- [ ] **Step 3: Implement backend-driven controls and accessible override UI**

```javascript
async function detectIcon() {
  const response = await fetch(`/api/icons/search?q=${encodeURIComponent(state.name)}`);
  const data = await response.json();
  renderIconSuggestions(data.items);
}

function setIcon(key) {
  state.icon = key;
  document.querySelectorAll("[data-icon-key]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.iconKey === key));
  });
  syncCli();
}
```

Load all option arrays from `/api/options` instead of hard-coded JavaScript.
Add a detected source/readout, debounced search, manual selection, and explicit
generic choice. Include `icon` in requests and CLI snippets. Preserve keyboard
operation, focus visibility, `aria-pressed`, and terminal styling.

- [ ] **Step 4: Run API tests and focused browser verification**

Run: `uv run pytest tests/test_server.py tests/test_renderer.py -q`
Run: `uv run python server.py`
Expected: tests PASS; in the browser, Nextcloud auto-detects without initials,
`Nextclod` visibly falls back, manual Nextcloud override works, and all 24
categories are selectable at desktop and mobile widths.

- [ ] **Step 5: Commit**

```bash
git add server.py app/web/static tests/test_server.py
git commit -m "feat: add brand detection controls to web UI"
```

### Task 8: Visual regression artifacts, documentation, and release verification

**Files:**
- Create: `scripts/generate_contact_sheet.py`
- Create: `tests/test_contact_sheet.py`
- Create: `tests/golden/hybrid-contact-sheet.png`
- Modify: `README.md`
- Modify: `CLAUDE.md`
- Modify: `docs/PROJECT_REVIEW.md`
- Modify: `docs/implementation-summaries/2026-08-02-hybrid-brand-icon-system.md`

**Interfaces:**
- Consumes: public CLI/API behavior and the committed catalog.
- Produces: deterministic representative contact sheet plus final user/developer documentation.

- [ ] **Step 1: Add a failing deterministic contact-sheet test**

```python
def test_contact_sheet_contains_brand_custom_and_generic(tmp_path, custom_resolver):
    cases = [
        IconRequest("Nextcloud", "cloud_service", icon="nextcloud"),
        IconRequest("Internal API", "api", icon="internal-api"),
        IconRequest("Unknown NAS", "nas", icon="generic"),
    ]
    result = generate_contact_sheet(
        output=tmp_path / "sheet.png",
        cases=cases,
        cell_size=128,
        resolver=custom_resolver,
    )
    assert result.size == (384, 128)
    expected = Image.open("tests/golden/hybrid-contact-sheet.png").convert("RGBA")
    assert ImageChops.difference(result, expected).getbbox() is None
```

- [ ] **Step 2: Verify the test fails**

Run: `uv run pytest tests/test_contact_sheet.py -q`
Expected: FAIL because the contact-sheet utility is absent.

- [ ] **Step 3: Implement the contact sheet and update documentation**

```python
def generate_contact_sheet(
    output: Path,
    cases: Sequence[IconRequest],
    cell_size: int,
    resolver: IconResolver,
) -> Image.Image:
    sheet = Image.new("RGBA", (cell_size * len(cases), cell_size), (0, 0, 0, 0))
    with TemporaryDirectory() as temp_dir:
        for index, request in enumerate(cases):
            rendered_request = replace(
                request, size=cell_size, format="png", output_dir=temp_dir,
            )
            result = generate_icon_result(rendered_request, resolver=resolver)
            with Image.open(result.paths["png"]) as rendered:
                sheet.alpha_composite(rendered.convert("RGBA"), (index * cell_size, 0))
    sheet.save(output)
    return sheet
```

Document `--icon`, `--icon-dir`, manifest format, automatic/fallback behavior,
catalog provenance, offline guarantees, and update workflow. Mark the roadmap's
single-source symbol and category-expansion prerequisites complete. Replace the
design-only summary with the actual files, behavior, and verification results.

- [ ] **Step 4: Run the complete release gate**

Run: `uv run pytest -q`
Run: `uv build`
Run: `git diff --check`
Expected: all tests PASS, package build succeeds, and the diff check is empty.
Also generate the representative contact sheet and inspect it at 100% and 25%
scale for recognizable geometry, clipping, frame scaling, glow, and initials.

- [ ] **Step 5: Commit**

```bash
git add scripts/generate_contact_sheet.py tests/test_contact_sheet.py tests/golden/hybrid-contact-sheet.png README.md CLAUDE.md docs
git commit -m "docs: complete hybrid icon system rollout"
```
