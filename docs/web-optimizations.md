# Web Interface Optimizations

Punch list of issues found while reviewing `server.py` and `app/web/static/index.html`. Ordered roughly by impact.

## Bugs & correctness

### 1. Directory traversal surface area on `/output/<path:filename>`

`server.py:88` — `serve_output` accepts any path under `output/`. Flask's `send_from_directory` blocks `..` traversal, but the route is broader than needed. Lock it down to a known subtree (e.g. `/output/<fmt>/<category>/<filename>`) or at least validate the extension is `.png` or `.svg`.

### 2. `debug=True` is hardcoded ✅ DONE

`server.py:96` — debug mode shouldn't ship. Gate it behind an env var:

```python
debug = os.environ.get("FLASK_DEBUG", "0") == "1"
app.run(host="127.0.0.1", port=port, debug=debug)
```

### 3. Broken download URLs ✅ DONE

`server.py:72` — output now lives at `output/{format}/{category}/file.ext` (per CLAUDE.md), but the response builds `/output/{Path(p).name}`, stripping the subdirs. Downloads will 404. Fix:

```python
files = {fmt: f"/output/{Path(p).relative_to(OUTPUT_DIR).as_posix()}" for fmt, p in paths.items()}
```

### 4. Contradictory class/style assignments on `mStatus` ✅ DONE

`index.html:1384-1388` — sets `className = "ok"`, then `.classList.add("amber")`, then `style.color = "var(--moss)"`. The intent is "moss green BUILT" but the code fights itself. Just `mStatus.className = "ok"` would do.

### 5. Incorrect empty-slot fill in recent strip ✅ DONE

`index.html:1456` — `for (let i = state.recent.length; i < 6; i++)` always fills to 6 even after slicing recent to 10. Compare against `Math.max(6, state.recent.length)` or skip the fill once `recent.length >= 6`.

## Performance

### 6. Film-grain SVG re-decoded on every repaint ✅ DONE

`index.html:57` — inline data-URL SVG with `feTurbulence` on a fixed `::before` with `mix-blend-mode: overlay`. On low-power devices (Raspberry Pi 5), this is the single biggest paint cost. Bake to a small PNG served as a static file, or drop opacity / use a coarser turbulence, or remove the blend mode.

### 7. `setInterval` clock runs while tab is hidden ✅ DONE

`index.html:1314` — `setInterval(tickClock, 1000)` runs forever. Pause via `visibilitychange`, or use `document.hidden` check inside the tick.

### 8. Recent strip rebuilds DOM on every build

`index.html:1430` — `renderRecent` runs on every successful build and rebuilds 10+ DOM nodes including `<img>` elements that re-fetch. Set `loading="lazy"` and reuse nodes when possible.

### 9. 39 KB single-file HTML

~960 lines of CSS inlined. Splitting into `/static/app.css` and `/static/app.js` lets the browser cache across reloads.

## Code quality

### 10. No `Cache-Control` on `/output/...`

Generated artifacts can be cached aggressively — their filenames are content-addressed by params (`{slug}-{style}-{theme}-{size}.{ext}`).

### 11. No rate limiting on `/api/generate`

Fine for localhost, but binding to anything other than 127.0.0.1 would be risky — size goes up to 2048px (memory pressure on a Pi).

### 12. Fragile clipboard parsing

`index.html:1287` — `innerText.replace(/\s+\\\s+/g, " ")` reconstructs the command from rendered HTML. Build the plain string in `syncCli` and stash it on a closure variable or data attribute.
