/* ============ ARTIFACT GALLERY ============ */
/* Server-backed history. Clicking a tile restores the settings that built it. */

const GALLERY_PAGE = 50;
const HEARTBEAT_MS = 5000;

let galleryLoaded = 0;
let galleryExhausted = false;

function _galleryTile(record, num) {
  const slot = el("div", {
    class: "slot filled",
    title: `${record.name} — ${record.style}/${record.theme}/${record.size}`,
    role: "button",
    tabindex: "0",
  });
  const restore = () => Gallery.restore(record);
  slot.addEventListener("click", restore);
  slot.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      restore();
    }
  });
  slot.append(el("span", { class: "num" }, String(num).padStart(2, "0")));
  if (record.thumb) {
    slot.append(el("img", { src: record.thumb, alt: record.name, loading: "lazy" }));
  }
  slot.append(el("span", { class: "lbl" }, record.name));
  return slot;
}

function _renderGallery(items, { append }) {
  const strip = $("strip");

  if (!append) {
    strip.innerHTML = "";
    galleryLoaded = 0;
  }
  strip.querySelector(".empty")?.remove();
  strip.querySelector(".gallery-more")?.remove();
  strip.querySelectorAll(".slot:not(.filled)").forEach((s) => s.remove());

  if (items.length === 0 && galleryLoaded === 0) {
    strip.append(el("div", { class: "empty" }, "NO RECENT ARTIFACTS / GENERATE TO POPULATE"));
    return;
  }

  items.forEach((record) => {
    galleryLoaded += 1;
    strip.append(_galleryTile(record, galleryLoaded));
  });

  // Keep a minimum of 6 cells so the strip holds its shape.
  for (let i = 0; i < Math.max(0, 6 - galleryLoaded); i++) {
    strip.append(el("div", { class: "slot" }));
  }

  if (!galleryExhausted) {
    strip.append(
      el("button", {
        type: "button",
        class: "gallery-more",
        onclick: () => Gallery.loadMore(),
      }, "LOAD MORE"),
    );
  }
}

const Gallery = {
  async refresh() {
    galleryExhausted = false;
    try {
      const response = await fetch(`/api/history?limit=${GALLERY_PAGE}&offset=0`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "history load failed");
      if (data.items.length < GALLERY_PAGE) galleryExhausted = true;
      _renderGallery(data.items, { append: false });
    } catch (error) {
      log(`[ERR] gallery unavailable: ${escapeHtml(error.message)}`, "err");
    }
  },

  async loadMore() {
    try {
      const response = await fetch(
        `/api/history?limit=${GALLERY_PAGE}&offset=${galleryLoaded}`,
      );
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "history load failed");
      if (data.items.length < GALLERY_PAGE) galleryExhausted = true;
      _renderGallery(data.items, { append: true });
    } catch (error) {
      log(`[ERR] gallery unavailable: ${escapeHtml(error.message)}`, "err");
    }
  },

  /* Fills the form. Deliberately does NOT generate — the user reviews first. */
  restore(record) {
    $("name").value = record.name;
    state.name = record.name;
    setCategory(record.category);
    setStyle(record.style);
    setTheme(record.theme);
    setFormat(record.format);

    $("size").value = record.size;
    state.size = record.size;
    $("sizeOut").textContent = String(record.size);
    updateSliderFill();

    $("transparent").checked = record.transparent_bg;
    state.transparent = record.transparent_bg;

    setIcon(record.icon, record.icon_title, record.icon_source);

    if (record.thumb) {
      const artifact = $("artifact");
      artifact.innerHTML = "";
      artifact.append(el("img", { src: record.thumb, alt: record.name }));
      $("viewport").classList.add("has-artifact");
      $("artifactName").textContent = record.name.toUpperCase();
    }

    syncCli();
    log(`restored ${escapeHtml(record.name)} — review and generate`, "amber");
  },
};

window.Gallery = Gallery;

/* Liveness: the server exits ~30s after these stop arriving. */
function heartbeat() {
  fetch("/api/alive", { method: "POST", keepalive: true }).catch(() => {});
}
heartbeat();
setInterval(heartbeat, HEARTBEAT_MS);

Gallery.refresh();
