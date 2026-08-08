# Custom Hue Theme Design

## Goal

Let users create an additional custom color theme from the web UI while
preserving the existing green, blue, orange, purple, and grayscale presets.
The selected color must affect generated artifacts, not only the browser
swatch, and must remain representable through the API and CLI.

## User Experience

The Chromatic `[HUE]` control retains its five preset swatches and adds a
sixth `CUSTOM` swatch button. Activating it selects the custom theme, reveals
a mini editor directly below the swatch row, and opens that editor's native
`<input type="color">`. The editor displays the normalized six-digit
hexadecimal value. Changing the input updates the swatch and keeps the custom
theme selected.

Choosing a preset switches away from the custom theme without forgetting the
last custom color. Choosing or changing the custom color switches back to the
custom theme. Existing keyboard focus indicators and `aria-pressed` selection
semantics apply to the new control. The native input retains an accessible
label.

The initial custom color is `#00b8a9`, a distinct cyan-teal that is not
duplicated by an existing preset. Dismissing the native picker without a
change leaves that color selected. Selecting a custom theme still requires
the user to press Generate, matching the current interaction model.

## Request Model and Data Flow

`IconRequest` and the web request schema gain an optional `custom_color`
field. `custom` is added to the valid theme set and returned by
`GET /api/options`. The active theme is represented as follows:

- Presets use their current theme names and omit `custom_color`.
- A custom theme uses `theme="custom"` and a normalized `#RRGGBB`
  `custom_color` value.

The frontend stores both the active theme and the last custom color. It sends
`custom_color` only when the active theme is custom. The API returns the
normalized custom color with generation metadata and returns `null` for preset
themes. The readout labels a custom build as `CUSTOM #RRGGBB`, and the
equivalent CLI uses
`--theme custom --custom-color "#RRGGBB"` so the shell does not interpret the
hash as a comment.

The CLI gains `--custom-color`. Batch entries may provide the same
`custom_color` field. Supplying `custom_color` with a preset is rejected to
avoid silently ignored input, and selecting `custom` without a color is also
rejected.

## Validation and Palette Derivation

Custom colors accept exactly six hexadecimal digits with one leading `#`.
Validation is centralized with the existing domain validation rather than
duplicated in Pydantic. A shared color helper lowercases accepted values for
rendering, response metadata, history, and filenames; callers do not mutate
the request object.

The chosen color is the exact accent color. The remaining palette colors are
derived deterministically in HSL space. Hue and saturation come from the
selected color, while lightness is fixed for each role:

- background: selected hue and saturation at 8% lightness
- foreground: selected hue and saturation at 24% lightness
- text: selected hue and saturation at 88% lightness

Achromatic selections therefore remain achromatic. HSL-to-RGB conversion
rounds each channel to the nearest integer before producing lowercase hex.
This keeps all three render styles coherent and makes repeated requests
byte-stable. The derivation helper lives in `app/generator/colors.py`; styles
continue to consume a `ColorPalette` without knowing whether it came from a
preset or custom input.

## Rendering, Filenames, and History

Style resolution includes `custom_color` in its cache key. Preset rendering is
unchanged. For custom themes, the output basename includes the normalized hex
digits, for example:

`nextcloud-minimal-custom-00b8a9-256.svg`

This prevents two custom colors with otherwise identical settings from
overwriting one another and gives the gallery a distinct output key for each
color. History gains a nullable `custom_color` column through the existing
idempotent migration mechanism. New custom records store the normalized value;
preset and legacy records use `NULL`. Restoring a custom gallery tile restores
both `theme="custom"` and its color before refreshing the UI and CLI snippet.

## Error Handling

Invalid custom colors, missing colors for the custom theme, and custom colors
attached to preset themes produce explicit `ValueError` messages and HTTP 400
responses. The frontend relies on the native picker for well-formed values but
the backend remains authoritative. Existing generation error presentation is
used without a success-shaped fallback.

## Verification

Focused tests will cover:

- valid and invalid custom-theme request combinations
- deterministic palette derivation and preservation of the exact accent
- distinct output filenames for distinct custom colors
- web API generation metadata and SVG color output
- CLI single and batch request wiring
- accessible custom picker markup and frontend request/readout behavior
- unchanged rendering across all existing preset style/theme combinations

The final verification gate is `uv run pytest -q`, `uv build`, and
`git diff --check`. Desktop and mobile layout behavior will be checked in a
browser if the local browser tooling is available; otherwise that limitation
will be reported explicitly.

## Out of Scope

This change does not add saved custom theme libraries, multiple named custom
themes, palette editing, automatic generation on picker movement, or changes
to the five preset palettes.
