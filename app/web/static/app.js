let CATEGORIES = [];
let STYLES = [];
let THEMES = [];
let FORMATS = [];

const state = {
  name: "NEXTCLOUD",
  category: "server",
  style: "minimal",
  theme: "blue",
  format: "both",
  size: 256,
  transparent: false,
  icon: "auto",
  iconTitle: null,
  iconSource: null,
  builds: 0,
};
let _cliText = "";
let iconSearchTimer = null;

const $  = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value).replace(
  /[&<>"']/g,
  (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character],
);
const el = (tag, props = {}, ...kids) => {
  const n = document.createElement(tag);
  Object.entries(props).forEach(([k, v]) => {
    if (k === "class") n.className = v;
    else if (k === "html") n.innerHTML = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v);
  });
  kids.forEach((k) => n.append(k.nodeType ? k : document.createTextNode(k)));
  return n;
};

/* ============ BUILD CONTROL UI ============ */
function renderCategories() {
  const host = $("categories");
  host.innerHTML = "";
  CATEGORIES.forEach((cat, i) => {
    const btn = el("button", {
      type: "button",
      class: "chip",
      "data-value": cat,
      "aria-pressed": cat === state.category ? "true" : "false",
      onclick: () => setCategory(cat),
    });
    btn.append(
      el("span", { class: "idx" }, String(i + 1).padStart(2, "0")),
      document.createTextNode(cat.replace(/_/g, " "))
    );
    host.append(btn);
  });
}
function setCategory(v) {
  state.category = v;
  document.querySelectorAll("#categories .chip").forEach((c) =>
    c.setAttribute("aria-pressed", c.dataset.value === v ? "true" : "false")
  );
  if (state.icon === "auto") detectIcon(state.name);
  if (state.icon === "generic") setIcon("generic");
  syncCli();
}

function renderStyles() {
  const host = $("styles");
  host.innerHTML = "";
  STYLES.forEach((s) => {
    const btn = el("button", {
      type: "button",
      class: "style-card",
      "data-style": s,
      "data-value": s,
      "aria-pressed": s === state.style ? "true" : "false",
      onclick: () => setStyle(s),
    });
    btn.append(document.createTextNode(s));
    host.append(btn);
  });
}
function setStyle(v) {
  state.style = v;
  document.querySelectorAll("#styles .style-card").forEach((c) =>
    c.setAttribute("aria-pressed", c.dataset.value === v ? "true" : "false")
  );
  syncCli();
}

function renderThemes() {
  const host = $("themes");
  host.innerHTML = "";
  THEMES.forEach((t) => {
    const btn = el("button", {
      type: "button",
      class: "theme-swatch",
      "data-theme": t,
      "data-value": t,
      "aria-pressed": t === state.theme ? "true" : "false",
      onclick: () => setTheme(t),
    });
    btn.append(el("span", { class: "pip" }), el("span", {}, t.slice(0, 3)));
    host.append(btn);
  });
}
function setTheme(v) {
  state.theme = v;
  document.querySelectorAll("#themes .theme-swatch").forEach((c) =>
    c.setAttribute("aria-pressed", c.dataset.value === v ? "true" : "false")
  );
  syncCli();
}

function renderFormats() {
  const host = $("formats");
  host.innerHTML = "";
  FORMATS.forEach((f) => {
    const btn = el("button", {
      type: "button",
      class: "format-btn",
      "data-value": f,
      "aria-pressed": f === state.format ? "true" : "false",
      onclick: () => setFormat(f),
    });
    btn.textContent = f === "both" ? "BOTH" : f.toUpperCase();
    host.append(btn);
  });
}
function setFormat(v) {
  state.format = v;
  document.querySelectorAll("#formats .format-btn").forEach((c) =>
    c.setAttribute("aria-pressed", c.dataset.value === v ? "true" : "false")
  );
  syncCli();
}

/* ============ SIZE SLIDER ============ */
const sizeInput = $("size");
function updateSliderFill() {
  const pct = ((sizeInput.value - sizeInput.min) / (sizeInput.max - sizeInput.min)) * 100;
  sizeInput.style.setProperty("--pct", pct + "%");
}
sizeInput.addEventListener("input", () => {
  state.size = parseInt(sizeInput.value, 10);
  $("sizeOut").textContent = state.size;
  updateSliderFill();
  syncCli();
});

/* ============ ICON DETECTION / OVERRIDE ============ */
function updateIconButtons() {
  document.querySelectorAll("[data-icon-key]").forEach((button) => {
    button.setAttribute("aria-pressed", button.dataset.iconKey === state.icon ? "true" : "false");
  });
}

function setIcon(key, title = null, source = null) {
  state.icon = key;
  state.iconTitle = title;
  state.iconSource = source;
  updateIconButtons();
  if (key === "auto") {
    detectIcon(state.name);
  } else if (key === "generic") {
    $("iconDetection").className = "icon-detection fallback";
    $("iconDetection").querySelector("span:last-child").textContent =
      `GENERIC // ${state.category.replace(/_/g, " ").toUpperCase()}`;
  } else {
    $("iconDetection").className = "icon-detection override";
    $("iconDetection").querySelector("span:last-child").textContent =
      `OVERRIDE // ${(title || key).toUpperCase()} · ${(source || "custom").toUpperCase()}`;
  }
  syncCli();
}

function renderIconSuggestions(items) {
  const host = $("iconSuggestions");
  host.innerHTML = "";
  items.slice(0, 6).forEach((item) => {
    const button = el("button", {
      type: "button",
      class: "icon-option",
      "data-icon-key": item.key,
      "aria-pressed": item.key === state.icon ? "true" : "false",
      onclick: () => setIcon(item.key, item.title, item.source),
    });
    button.append(
      el("span", { class: "icon-option-title" }, item.title),
      el("span", { class: "icon-option-source" }, item.source),
    );
    host.append(button);
  });
}

async function detectIcon(query) {
  const value = (query || "").trim();
  if (!value) {
    renderIconSuggestions([]);
    return;
  }
  try {
    const response = await fetch(`/api/icons/search?q=${encodeURIComponent(value)}&limit=6`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "catalog search failed");
    renderIconSuggestions(data.items || []);
    if (state.icon !== "auto") {
      updateIconButtons();
      return;
    }
    const readout = $("iconDetection");
    if (data.exact) {
      state.iconTitle = data.exact.title;
      state.iconSource = data.exact.source;
      readout.className = "icon-detection detected";
      readout.querySelector("span:last-child").textContent =
        `DETECTED // ${data.exact.title.toUpperCase()} · ${data.exact.source.toUpperCase()}`;
    } else {
      state.iconTitle = null;
      state.iconSource = null;
      readout.className = "icon-detection fallback";
      readout.querySelector("span:last-child").textContent =
        `NO EXACT MATCH // FALLBACK ${state.category.replace(/_/g, " ").toUpperCase()}`;
    }
  } catch (error) {
    $("iconDetection").className = "icon-detection error";
    $("iconDetection").querySelector("span:last-child").textContent = "CATALOG SEARCH UNAVAILABLE";
    log(`[ERR] ${escapeHtml(error.message)}`, "err");
  }
}

document.querySelectorAll(".icon-mode").forEach((button) => {
  button.addEventListener("click", () => setIcon(button.dataset.iconKey));
});

$("iconSearch").addEventListener("input", (event) => {
  clearTimeout(iconSearchTimer);
  iconSearchTimer = setTimeout(() => detectIcon(event.target.value || state.name), 220);
});

/* ============ NAME + TRANSPARENT ============ */
$("name").addEventListener("input", (e) => {
  state.name = e.target.value;
  syncCli();
  if (state.icon === "auto") {
    clearTimeout(iconSearchTimer);
    iconSearchTimer = setTimeout(() => detectIcon(state.name), 220);
  }
});
$("transparent").addEventListener("change", (e) => {
  state.transparent = e.target.checked;
  syncCli();
});

/* ============ CLI SNIPPET ============ */
function syncCli() {
  const name = (state.name || "").toUpperCase() || "…";
  const displayedName = escapeHtml(name);
  const args = [
    `--name "${name}"`,
    `--category ${state.category}`,
    `--style ${state.style}`,
    `--theme ${state.theme}`,
    `--size ${state.size}`,
    `--format ${state.format}`,
    `--icon ${state.icon}`,
  ];
  if (state.transparent) args.push("--transparent");
  _cliText = `python main.py ${args.join(" ")}`;

  const parts = [
    '<span class="cmd">python main.py</span>',
    `--name <b>"${displayedName}"</b>`,
    `--category <b>${state.category}</b>`,
    `--style <b>${state.style}</b>`,
    `--theme <b>${state.theme}</b>`,
    `--size <b>${state.size}</b>`,
    `--format <b>${state.format}</b>`,
    `--icon <b>${state.icon}</b>`,
  ];
  if (state.transparent) parts.push(`<b>--transparent</b>`);
  $("cli").innerHTML = parts.join(" \\<br>&nbsp;&nbsp;");
}

$("cli").addEventListener("click", () => {
  navigator.clipboard?.writeText(_cliText).then(
    () => log(`[OK] CLI command copied to clipboard`, "ok"),
    () => log(`[ERR] clipboard unavailable`, "err")
  );
});

/* ============ LOG / STATUS ============ */
function ts() {
  const d = new Date();
  return d.toTimeString().slice(0, 8);
}
function log(msg, cls = "") {
  const line = `<span class="ts">[${ts()}]</span><span class="${cls}">${msg}</span>`;
  $("log").innerHTML = line;
}

/* ============ CLOCK / UPTIME ============ */
const started = Date.now();
let clockTimer = null;
function tickClock() {
  const d = new Date();
  $("clock").textContent = d.toTimeString().slice(0, 8);
  const s = Math.floor((Date.now() - started) / 1000);
  const mm = String(Math.floor(s / 60)).padStart(2, "0");
  const ss = String(s % 60).padStart(2, "0");
  $("uptime").textContent = `${mm}:${ss}`;
}
function startClock() {
  if (clockTimer == null) {
    tickClock();
    clockTimer = setInterval(tickClock, 1000);
  }
}
function stopClock() {
  if (clockTimer != null) {
    clearInterval(clockTimer);
    clockTimer = null;
  }
}
document.addEventListener("visibilitychange", () => {
  if (document.hidden) stopClock();
  else startClock();
});
startClock();

/* ============ SESSION ID ============ */
$("sess").textContent = Math.random().toString(16).slice(2, 8).toUpperCase();

/* ============ GENERATE ============ */
$("form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!state.name.trim()) {
    log(`[ERR] designation required`, "err");
    $("name").focus();
    return;
  }
  const btn = $("genBtn");
  const vp = $("viewport");
  btn.disabled = true;
  btn.textContent = "◌ BUILDING…";
  vp.classList.add("busy");
  $("mStatus").textContent = "BUILDING…";
  $("mStatus").className = "amber";
  $("axisId").textContent = "BUILDING";
  log(`<span class="amber">[REQ]</span> ${escapeHtml(state.name)} / ${state.category} / ${state.style}-${state.theme}-${state.size}`);

  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: state.name,
        category: state.category,
        style: state.style,
        theme: state.theme,
        size: state.size,
        format: state.format,
        icon: state.icon,
        transparent_bg: state.transparent,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "unknown error");
    onBuildSuccess(data);
  } catch (err) {
    $("mStatus").textContent = "ERROR";
    $("mStatus").className = "";
    $("mStatus").style.color = "var(--blood)";
    $("axisId").textContent = "ERROR";
    log(`<span class="err">[ERR]</span> ${escapeHtml(err.message)}`, "err");
  } finally {
    btn.disabled = false;
    btn.textContent = "▶ GENERATE";
    vp.classList.remove("busy");
  }
});

function onBuildSuccess(data) {
  state.builds += 1;
  $("buildCount").textContent = String(state.builds).padStart(2, "0");

  // preview — prefer SVG for crisp scaling
  const previewUrl = data.files.svg || data.files.png;
  const artifact = $("artifact");
  artifact.innerHTML = "";
  const img = el("img", {
    src: previewUrl + "?t=" + Date.now(),
    alt: data.name,
  });
  artifact.append(img);
  $("viewport").classList.add("has-artifact");

  // marquee + meta
  $("artifactName").textContent = data.name.toUpperCase();
  $("mStatus").textContent = "BUILT";
  $("mStatus").className = "ok";
  $("mStatus").style.color = "";
  $("mCat").textContent = data.category.replace(/_/g, " ").toUpperCase();
  $("mStyle").textContent = data.style.toUpperCase();
  $("mTheme").textContent = data.theme.toUpperCase();
  $("mSize").textContent = `${data.size} × ${data.size} PX`;
  $("mFmt").textContent = data.format.toUpperCase();
  $("mIcon").textContent = data.icon_title.toUpperCase();
  $("mSource").textContent = `${data.match_method.toUpperCase()} / ${data.icon_source.toUpperCase()}`;
  $("mElapsed").textContent = `${data.elapsed_ms} MS`;
  $("axisId").textContent = `ID ${String(state.builds).padStart(4, "0")}`;

  // downloads
  const dl = $("downloads");
  dl.innerHTML = "";
  Object.entries(data.files).forEach(([fmt, url]) => {
    const name = url.split("/").pop();
    const a = el("a", {
      class: "dl-btn",
      href: url,
      download: name,
      title: name,
    });
    a.append(
      el("span", {}, `↓ DOWNLOAD ${fmt.toUpperCase()}`),
      el("span", { class: "ext" }, name.split(".").pop().toUpperCase()),
    );
    dl.append(a);
  });

  // gallery (server-backed)
  Gallery.refresh();

  log(`<span class="ok">[OK]</span> built ${escapeHtml(data.name)} in ${data.elapsed_ms}ms`, "ok");
}

/* ============ INIT ============ */
async function initialize() {
  try {
    const response = await fetch("/api/options");
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "option load failed");
    CATEGORIES = data.categories;
    STYLES = data.styles;
    THEMES = data.themes;
    FORMATS = data.formats;
    if (!CATEGORIES.includes(state.category)) state.category = CATEGORIES[0];
    if (!STYLES.includes(state.style)) state.style = STYLES[0];
    if (!THEMES.includes(state.theme)) state.theme = THEMES[0];
    if (!FORMATS.includes(state.format)) state.format = FORMATS[0];
    renderCategories();
    renderStyles();
    renderThemes();
    renderFormats();
    updateSliderFill();
    syncCli();
    await detectIcon(state.name);
    log(`terminal initialised — ${CATEGORIES.length} categories / catalog online`, "amber");
  } catch (error) {
    log(`[ERR] initialisation failed: ${escapeHtml(error.message)}`, "err");
    $("genBtn").disabled = true;
  }
}

initialize();
