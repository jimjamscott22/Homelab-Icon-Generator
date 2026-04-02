# 🎨 Homelab Icon Generator

Generate clean, consistent icons for homelab devices and services using Python.

## 🧠 Overview

Homelab Icon Generator is a Python-based tool for creating simple, visually consistent icons for devices and services commonly found in self-hosted environments.

Instead of relying on external icon packs, this project generates icons programmatically using shapes, colors, and text, making it easy to produce scalable, customizable assets for dashboards and tools like network monitors or internal apps.

## 🚀 Features

- Generate icons for servers, routers, IoT devices, containers, databases, and more.
- Export formats:
  - PNG (raster)
  - SVG (vector)
- Style support:
  - minimal
  - terminal
  - cyberpunk (planned/optional)
- Automatic initials generation (for example, Raspberry Pi Server -> RPS)
- CLI-based usage
- Batch generation via JSON input
- Clean, modular architecture for easy extension

## 🛠️ Tech Stack

- Python
- Pillow (image generation)
- svgwrite (SVG creation)

## ⚙️ Installation

```bash
git clone https://github.com/YOUR_USERNAME/homelab-icon-generator.git
cd homelab-icon-generator
pip install -r requirements.txt
```

## ▶️ Usage

### Generate a Single Icon

```bash
python main.py \
  --name "Raspberry Pi Server" \
  --category raspberry_pi \
  --style terminal \
  --theme green \
  --size 256 \
  --format png
```

### Batch Generation

Create a JSON file:

```json
[
  {
    "name": "Nextcloud",
    "category": "cloud_service",
    "style": "minimal",
    "theme": "blue"
  },
  {
    "name": "Home Router",
    "category": "router",
    "style": "terminal",
    "theme": "green"
  }
]
```

Then run:

```bash
python main.py --batch examples/sample_icons.json
```

## 🗂️ Project Structure

```text
homelab-icon-generator/
|- app/
|  |- generator/
|  |- styles/
|  |- models/
|  |- utils/
|  \- main.py
|- output/
|- examples/
|- requirements.txt
\- README.md
```

## 🎯 Use Cases

- Network dashboards (like your own homelab control panel)
- Device visualization tools
- Internal apps and admin panels
- Custom icon packs for self-hosted services

## 🔮 Future Ideas

- AI-generated icon styles
- Automatic icon assignment based on device detection
- Theme packs (dark mode, neon, retro terminal)
- Web UI for generating icons visually

## 💡 Philosophy

Icons should be consistent, meaningful, and easy to generate, not hunted down across random icon packs.

## 📜 License

MIT License (or whatever you choose)
