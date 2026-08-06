"""Create Windows shortcuts that launch the Homelab Icon Generator web UI.

The shortcut targets `pythonw.exe -m app.main` (not the `homelab-icons.exe`
console-script shim) so double-clicking it opens the web UI with no console
window. `homelab-icons.exe` is a console-subsystem executable — launching it
directly would flash a console window even with a minimised window style.

Maintainer script. Run once after `uv sync`:

    uv run python -m scripts.install_shortcut
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SHORTCUT_NAME = "Homelab Icon Generator.lnk"


def _launch_target() -> tuple[Path, Path]:
    """Return (pythonw.exe, the homelab-icons script) for the active venv."""
    scripts_dir = Path(sys.executable).parent
    pythonw = scripts_dir / "pythonw.exe"
    if not pythonw.is_file():
        pythonw = Path(sys.executable)
    entry = scripts_dir / "homelab-icons.exe"
    if not entry.is_file():
        raise SystemExit(
            "homelab-icons is not installed in this environment — run `uv sync` first"
        )
    return pythonw, entry


def _targets() -> list[Path]:
    home = Path.home()
    desktop = home / "Desktop"
    directories = [desktop]
    appdata = os.environ.get("APPDATA")
    if appdata:
        directories.append(
            Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        )
    return [directory for directory in directories if directory.is_dir()]


def main() -> int:
    if sys.platform != "win32":
        print("This script creates Windows shortcuts; nothing to do here.")
        return 0

    try:
        import win32com.client  # type: ignore
    except ImportError:
        pythonw, _ = _launch_target()
        print(
            "pywin32 is not installed, so the shortcut cannot be created "
            "automatically.\nCreate one by hand pointing at:\n"
            f"  {pythonw}\n"
            '  with arguments: -m app.main\n'
            "Install pywin32 with `uv add --dev pywin32` to automate this."
        )
        return 1

    pythonw, _ = _launch_target()
    shell = win32com.client.Dispatch("WScript.Shell")
    created = []
    for directory in _targets():
        path = directory / SHORTCUT_NAME
        shortcut = shell.CreateShortCut(str(path))
        shortcut.TargetPath = str(pythonw)
        shortcut.Arguments = "-m app.main"
        shortcut.WorkingDirectory = str(Path.cwd())
        shortcut.Description = "Open the Homelab Icon Generator web UI"
        shortcut.WindowStyle = 7  # minimised
        shortcut.save()
        created.append(path)

    for path in created:
        print(f"Created {path}")
    return 0 if created else 1


if __name__ == "__main__":
    raise SystemExit(main())
