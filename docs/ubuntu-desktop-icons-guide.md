# How to Set Desktop Icons on Ubuntu

A practical guide covering three common scenarios: replacing an app's icon in the taskbar/launcher, creating a new `.desktop` entry, and setting a custom file/folder icon.

---

## Concepts

| Term | Meaning |
|---|---|
| `.desktop` file | Plain-text file that tells the shell how to launch an app and which icon to use |
| Icon theme | Directory hierarchy (usually `hicolor`) that the shell searches for icons by name |
| `~/.local/share/` | Your per-user data dir — changes here override system-wide files |

---

## 1. Replacing an App's Launcher Icon

### Step 1 — Prepare your icon file

Supported formats: **PNG**, **SVG** (preferred for sharpness at any size).

Recommended sizes: `16`, `22`, `32`, `48`, `64`, `128`, `256`, `512` px.

### Step 2 — Install the icon into the hicolor theme

```bash
# For a PNG (replace SIZE with the pixel dimension, e.g. 256)
mkdir -p ~/.local/share/icons/hicolor/<SIZE>x<SIZE>/apps/
cp my-icon.png ~/.local/share/icons/hicolor/<SIZE>x<SIZE>/apps/my-app-icon.png

# For an SVG (scalable, preferred)
mkdir -p ~/.local/share/icons/hicolor/scalable/apps/
cp my-icon.svg ~/.local/share/icons/hicolor/scalable/apps/my-app-icon.svg
```

### Step 3 — Refresh the icon cache

```bash
gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor/
```

### Step 4 — Point the `.desktop` entry at your icon

Copy the system entry locally so your changes aren't overwritten by updates:

```bash
cp /usr/share/applications/some-app.desktop ~/.local/share/applications/
```

Open it in a text editor and set the `Icon=` line to the **name** (no extension, no path) you used in Step 2:

```ini
Icon=my-app-icon
```

Save, then log out and back in (or run `killall -3 gnome-shell` on GNOME) to see the change.

---

## 2. Creating a New `.desktop` Entry from Scratch

Create `~/.local/share/applications/my-app.desktop`:

```ini
[Desktop Entry]
Name=My App
Comment=Short description shown in app search
Exec=/opt/my-app/my-app %U
Icon=my-app-icon
Terminal=false
Type=Application
Categories=Utility;
Keywords=keyword1;keyword2;
StartupWMClass=MyApp
```

Key fields:

| Field | Purpose |
|---|---|
| `Exec` | Full path to the binary; `%U` passes URLs/files |
| `Icon` | Icon name (resolved via the icon theme) or absolute path to a file |
| `Categories` | Controls which app-grid folder the app appears in |
| `StartupWMClass` | Matches the window class so the taskbar groups windows correctly |

Make it executable (required by some launchers):

```bash
chmod +x ~/.local/share/applications/my-app.desktop
```

Then refresh the desktop database:

```bash
update-desktop-database ~/.local/share/applications/
```

---

## 3. Pinning to the Taskbar / Dock (GNOME)

1. Search for the app in the Activities overview.
2. Right-click its icon → **Pin to Dash** (or **Add to Favorites**).

Alternatively, via the terminal:

```bash
# List current favourites
gsettings get org.gnome.shell favorite-apps

# Add an entry (replace existing list, keeping others)
gsettings set org.gnome.shell favorite-apps \
  "['firefox.desktop', 'my-app.desktop', 'org.gnome.Nautilus.desktop']"
```

---

## 4. Setting a Custom Icon on a File or Folder (GNOME Nautilus)

1. Right-click the file or folder → **Properties**.
2. Click the icon thumbnail in the top-left of the Properties dialog.
3. Browse to your image file and select it.

To do this from the command line with `gio`:

```bash
gio set -t string /path/to/folder metadata::custom-icon \
  "file:///home/$USER/.local/share/icons/hicolor/scalable/apps/my-app-icon.svg"
```

To clear a custom icon:

```bash
gio set -t unset /path/to/folder metadata::custom-icon
```

---

## 5. Troubleshooting

| Symptom | Fix |
|---|---|
| Icon still shows old image | Run `gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor/` then log out/in |
| `.desktop` file not appearing in search | Run `update-desktop-database ~/.local/share/applications/` |
| Wrong window grouped with app in dock | Set `StartupWMClass` to match the output of `xprop WM_CLASS` (click the window when prompted) |
| System update overwrites your icon | Always put custom `.desktop` files in `~/.local/share/applications/`, never edit `/usr/share/applications/` directly |
| GNOME doesn't pick up SVG icon | Ensure `librsvg2-common` is installed: `sudo apt install librsvg2-common` |

---

## Quick Reference

```bash
# Install a 256px PNG icon
mkdir -p ~/.local/share/icons/hicolor/256x256/apps/
cp icon.png ~/.local/share/icons/hicolor/256x256/apps/my-icon.png

# Install a scalable SVG icon
mkdir -p ~/.local/share/icons/hicolor/scalable/apps/
cp icon.svg ~/.local/share/icons/hicolor/scalable/apps/my-icon.svg

# Refresh icon cache
gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor/

# Copy and edit a system .desktop entry
cp /usr/share/applications/app.desktop ~/.local/share/applications/
nano ~/.local/share/applications/app.desktop
# Set: Icon=my-icon

# Refresh desktop DB
update-desktop-database ~/.local/share/applications/
```
