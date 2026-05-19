Build a Python project called “Homelab Icon Generator”.

Goal:
Create a practical icon generator for homelab and self-hosted environments that can generate clean, visually consistent icons for devices and services such as Raspberry Pi servers, routers, laptops, IoT devices, Nextcloud, Vaultwarden, Docker containers, and other homelab-related assets.

This should not be a toy script. Build it like a small real application with clean architecture, reusable modules, and readable code.

Core requirements:
1. Use Python.
2. Use Pillow for raster image generation.
3. Use svgwrite for SVG generation.
4. Support exporting both PNG and SVG.
5. Accept structured input such as:
   - name
   - category
   - style
   - color theme
   - output size
6. Generate icons that include:
   - a background shape
   - a foreground symbol or simple procedural shape
   - optional initials derived from the device/service name
7. Make the icons suitable for dashboards and network tools.

Initial supported categories:
- raspberry_pi
- server
- router
- switch
- laptop
- desktop
- phone
- iot
- container
- database
- cloud_service
- generic_service

Initial supported styles:
- minimal
- terminal
- cyberpunk

Initial supported themes:
- green
- blue
- orange
- purple
- grayscale

Implementation requirements:
1. Create a modular project structure.
2. Separate icon generation logic into reusable modules:
   - shapes
   - colors
   - layouts
   - text rendering
   - category-to-symbol mapping
   - style definitions
3. Include a clean main entry point.
4. Add a CLI interface so a user can run commands like:
   python main.py --name "Raspberry Pi Server" --category raspberry_pi --style terminal --theme green --size 256 --format png
5. Also support batch generation from a JSON file.
6. Auto-generate initials from names, such as:
   - Raspberry Pi Server -> RPS
   - Nextcloud -> N
7. Include sensible defaults when fields are omitted.
8. Make style definitions consistent and reusable so adding new styles later is easy.
9. Add robust error handling and validation for invalid categories, formats, and themes.
10. Add docstrings and concise comments where helpful, but do not over-comment everything.

Suggested project structure:
homelab-icon-generator/
├─ app/
│  ├─ generator/
│  │  ├─ shapes.py
│  │  ├─ colors.py
│  │  ├─ layouts.py
│  │  ├─ text_utils.py
│  │  ├─ symbols.py
│  │  └─ renderer.py
│  ├─ styles/
│  │  ├─ base.py
│  │  ├─ minimal.py
│  │  ├─ terminal.py
│  │  └─ cyberpunk.py
│  ├─ models/
│  │  └─ icon_request.py
│  ├─ utils/
│  │  ├─ naming.py
│  │  └─ validation.py
│  └─ main.py
├─ output/
├─ examples/
│  └─ sample_icons.json
├─ requirements.txt
└─ README.md

Behavior details:
1. Icons should feel modern, clean, and dashboard-friendly.
2. Use procedural shapes rather than relying on external icon packs.
3. For each category, create a simple symbolic visual identity. Example ideas:
   - raspberry_pi: chip-like shape or circuit motif
   - server: stacked rectangle motif
   - router: antenna or horizontal unit motif
   - switch: port-grid motif
   - laptop: screen + base
   - phone: rounded vertical rectangle
   - iot: sensor/wave motif
   - container: box/grid motif
   - database: cylinder motif
   - cloud_service: cloud motif
4. Terminal style should have darker backgrounds and phosphor-like accents.
5. Minimal style should use flat clean geometry.
6. Cyberpunk style should use stronger contrast and layered accents, but still remain readable.

Outputs:
1. Generate PNG icons.
2. Generate SVG icons.
3. Save files with slugified filenames.
4. Store outputs in an output directory.

Batch mode:
1. Read a JSON file containing multiple icon requests.
2. Generate icons for each request.
3. Continue processing valid entries even if one entry fails.
4. Print a clear summary at the end.

README requirements:
1. Explain what the project does.
2. Explain installation.
3. Show CLI examples.
4. Show JSON batch input example.
5. Explain the architecture briefly.

Important coding preferences:
- Use dataclasses or Pydantic models for structured input if helpful.
- Prefer clean, readable, production-style code.
- Avoid unnecessary abstractions, but keep the design extensible.
- Do not put all logic in one file.
- Make it easy for a future developer to add new device categories and styles.

Nice-to-have features if time permits:
- optional transparent background support
- optional circular vs rounded-square canvas
- automatic color selection based on category
- preview contact sheet generation for all categories/styles
- a small test suite for utility functions

At the end:
1. Create the initial working project structure.
2. Implement a functional MVP.
3. Include at least a few example generated icon configurations.
4. Make sure the app can be run immediately after installing requirements.