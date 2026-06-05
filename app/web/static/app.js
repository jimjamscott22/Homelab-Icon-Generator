const CATEGORIES = [
  "raspberry_pi","server","router","switch","laptop","desktop",
  "phone","iot","container","database","cloud_service","generic_service",
  "media","ai","camera","game_console"
];
const STYLES  = ["minimal","terminal","cyberpunk"];
const THEMES  = ["green","blue","orange","purple","grayscale"];
const FORMATS = ["png","svg","both"];

const state = {
  name: "NEXTCLOUD",
  category: "server",
  style: "minimal",
  theme: "blue",
  format: "both",
  size: 256,
  transparent: false,
  recent: [],
  builds: 0,
};
let _cliText = "";

const $  = (id) => document.getElementById(id);
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

/* ============ NAME + TRANSPARENT ============ */
$("name").addEventListener("input", (e) => {
  state.name = e.target.value;
  syncCli();
});
$("transparent").addEventListener("change", (e) => {
  state.transparent = e.target.checked;
  syncCli();
});

/* ============ CLI SNIPPET ============ */
function syncCli() {
  const name = (state.name || "").toUpperCase() || "…";
  const args = [
    `--name "${name}"`,
    `--category ${state.category}`,
    `--style ${state.style}`,
    `--theme ${state.theme}`,
    `--size ${state.size}`,
    `--format ${state.format}`,
  ];
  if (state.transparent) args.push("--transparent");
  _cliText = `python main.py ${args.join(" ")}`;

  const parts = [
    '<span class="cmd">python main.py</span>',
    `--name <b>"${name}"</b>`,
    `--category <b>${state.category}</b>`,
    `--style <b>${state.style}</b>`,
    `--theme <b>${state.theme}</b>`,
    `--size <b>${state.size}</b>`,
    `--format <b>${state.format}</b>`,
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
  log(`<span class="amber">[REQ]</span> ${state.name} / ${state.category} / ${state.style}-${state.theme}-${state.size}`);

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
    log(`<span class="err">[ERR]</span> ${err.message}`, "err");
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

  // recent strip
  state.recent.unshift({
    name: data.name,
    category: data.category,
    style: data.style,
    theme: data.theme,
    size: data.size,
    url: previewUrl,
  });
  state.recent = state.recent.slice(0, 10);
  renderRecent();

  log(`<span class="ok">[OK]</span> built ${data.name} in ${data.elapsed_ms}ms`, "ok");
}

function _makeSlot(r, num) {
  const slot = el("div", {
    class: "slot filled",
    title: `${r.name} — ${r.style}/${r.theme}/${r.size}`,
  });
  slot.addEventListener("click", () => {
    const artifact = $("artifact");
    artifact.innerHTML = "";
    artifact.append(el("img", { src: r.url, alt: r.name }));
    $("artifactName").textContent = r.name.toUpperCase();
  });
  slot.append(
    el("span", { class: "num" }, String(num).padStart(2, "0")),
    el("img", { src: r.url, alt: r.name, loading: "lazy" }),
    el("span", { class: "lbl" }, r.name),
  );
  return slot;
}

function renderRecent() {
  const strip = $("strip");

  if (state.recent.length === 0) {
    strip.innerHTML = "";
    strip.append(el("div", { class: "empty" }, "NO RECENT ARTIFACTS / GENERATE TO POPULATE"));
    return;
  }

  strip.querySelector(".empty")?.remove();

  const filledBefore = strip.querySelectorAll(".slot.filled");

  if (filledBefore.length === 0) {
    // First build: create all slots from scratch
    state.recent.forEach((r, i) => {
      strip.append(_makeSlot(r, state.recent.length - i));
    });
  } else {
    // Subsequent builds: prepend new slot, reuse existing image nodes
    strip.insertBefore(
      _makeSlot(state.recent[0], state.recent.length),
      strip.querySelector(".slot.filled"),
    );
    // Trim last slot when at the 10-item cap
    const filled = strip.querySelectorAll(".slot.filled");
    for (let i = state.recent.length; i < filled.length; i++) {
      filled[i].remove();
    }
    // At cap every existing slot shifts down by one position, so renumber
    if (state.recent.length === 10) {
      strip.querySelectorAll(".slot.filled .num").forEach((numEl, i) => {
        numEl.textContent = String(10 - i).padStart(2, "0");
      });
    }
  }

  // Sync empty padding slots to keep a minimum of 6 visible
  strip.querySelectorAll(".slot:not(.filled)").forEach(s => s.remove());
  for (let i = 0; i < Math.max(0, 6 - state.recent.length); i++) {
    strip.append(el("div", { class: "slot" }));
  }
}

/* ============ INIT ============ */
renderCategories();
renderStyles();
renderThemes();
renderFormats();
updateSliderFill();
syncCli();
log(`terminal initialised — ready for build`, "amber");
