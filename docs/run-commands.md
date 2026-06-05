# Run Command Variations

Use these examples to generate different icon types and styles.

All commands follow the same template:

```bash
uv run main.py --name "<NAME>" --category <CATEGORY> --style <STYLE> --theme <THEME> --size <SIZE> --format <FORMAT>
```

Pick a row and substitute the values:

| #  | Name           | Category       | Style     | Theme     | Size | Format |
|----|----------------|----------------|-----------|-----------|------|--------|
| 1  | Pi Node        | raspberry_pi   | terminal  | green     | 256  | svg    |
| 2  | Main Server    | server         | minimal   | blue      | 256  | both   |
| 3  | Edge Router    | router         | cyberpunk | orange    | 512  | png    |
| 4  | Core Switch    | switch         | terminal  | grayscale | 256  | ico    |
| 5  | Dev Laptop     | laptop         | minimal   | purple    | 128  | all    |
| 6  | Workstation    | desktop        | cyberpunk | blue      | 512  | svg    |
| 7  | Mobile App     | phone          | minimal   | orange    | 256  | both   |
| 8  | Sensor Hub     | iot            | terminal  | green     | 256  | png    |
| 9  | Docker Stack   | container      | cyberpunk | purple    | 256  | both   |
| 10 | Postgres DB    | database       | minimal   | blue      | 256  | all    |
| 11 | Shell Prompt   | cli            | terminal  | green     | 256  | svg    |
| 12 | Source Code    | code           | minimal   | purple    | 256  | both   |
| 13 | Git Repo       | git_branch     | cyberpunk | orange    | 512  | png    |
| 14 | API Gateway    | api            | minimal   | blue      | 256  | all    |
| 15 | Edge Firewall  | firewall       | terminal  | orange    | 256  | both   |
| 16 | WireGuard VPN  | vpn            | cyberpunk | purple    | 512  | svg    |
| 17 | Synology NAS   | nas            | minimal   | grayscale | 256  | both   |
| 18 | PDU            | power          | cyberpunk | green     | 256  | ico    |

## Valid values

- **category**: `raspberry_pi`, `server`, `router`, `switch`, `laptop`, `desktop`, `phone`, `iot`, `container`, `database`, `cloud_service`, `generic_service`, `media`, `ai`, `camera`, `game_console`, `cli`, `code`, `git_branch`, `api`, `firewall`, `vpn`, `nas`, `power`
- **style**: `minimal`, `terminal`, `cyberpunk`
- **theme**: `green`, `blue`, `orange`, `purple`, `grayscale`
- **format**: `png`, `svg`, `ico`, `both` (png + svg), `all` (png + svg + ico)
- **size**: integer between `32` and `2048`. Common sizes:
  - `16`, `32`, `48` — favicons, system tray, file manager thumbnails (note: `16` and `48` are below the `32` minimum; use `32` as the floor)
  - `64`, `128` — desktop shortcuts, dock icons (macOS), taskbar
  - `256` — high-DPI desktop icons, Windows `.ico` standard, app launchers
  - `512` — macOS app icons, retina displays, Homepage/Homer dashboard tiles
  - `1024`, `2048` — App Store / marketing assets, print, source masters
