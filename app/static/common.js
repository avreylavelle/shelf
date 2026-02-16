// Client-side behavior for common.js.

const BASE_PATH = window.BASE_PATH || ""; // injected by templates

// Withbase helper for this page.
function withBase(path) {
  if (!path.startsWith("/")) return `${BASE_PATH}/${path}`;
  return `${BASE_PATH}${path}`;
}

// Api helper for this page.
async function api(path, options = {}) {
  const url = withBase(path);
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const message = data.error || "Request failed";
    throw new Error(message);
  }
  return data;
}


let toastTimer;
// Showtoast helper for this page.
function showToast(message, timeout = 2200) {
  if (!message) return;
  let el = document.getElementById("toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "toast";
    el.className = "toast";
    document.body.appendChild(el);
  }
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    el.classList.remove("show");
  }, timeout);
}

// Load NavUser and update the UI.
async function loadNavUser() {
  const el = document.getElementById("nav-user");
  if (!el) return;
  try {
    const data = await api("/api/session");
    if (data.logged_in && data.user) {
      el.textContent = data.user;
      el.classList.add("show");
    } else {
      el.textContent = "";
      el.classList.remove("show");
    }
  } catch (err) {
    el.textContent = "";
  }
}

loadNavUser();

// Escapehtml helper for this page.
function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Parselistfield helper for this page.
function parseListField(value) {
  if (!value) return [];
  if (Array.isArray(value)) return value;
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) return [];
    if (trimmed.startsWith("[") && trimmed.endsWith("]")) {
      try {
        const cleaned = trimmed.replace(/'/g, '"');
        const parsed = JSON.parse(cleaned);
        if (Array.isArray(parsed)) return parsed;
      } catch (err) {}
    }
    return trimmed.split(",").map((v) => v.trim()).filter(Boolean);
  }
  return [];
}

// Parsejsonfield helper for this page.
function parseJsonField(value) {
  if (!value) return null;
  if (typeof value === "object") return value;
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) return null;
    try {
      return JSON.parse(trimmed);
    } catch (err) {
      return null;
    }
  }
  return null;
}

// Serieskey helper for this page.
function seriesKey(title) {
  if (!title) return "";
  let text = String(title).toLowerCase();
  text = text.replace(/\(.*?\)/g, "");
  text = text.split(/[:\-–—]/)[0];
  text = text.replace(/[^a-z0-9]+/g, " ").trim();
  return text;
}

// Collapsebymalid helper for this page.
function collapseByMalId(items) {
  if (!Array.isArray(items)) return [];
  const seen = new Set();
  const result = [];
  for (const item of items) {
    const malId = item && item.mal_id !== undefined && item.mal_id !== null ? String(item.mal_id) : "";
    let key = "";
    if (malId && malId !== "0" && malId !== "nan") {
      key = `mal:${malId}`;
    } else {
      const title =
        item?.display_title || item?.title || item?.english_name || item?.japanese_name || item?.manga_id || item?.id || "";
      const base = seriesKey(title);
      key = base ? `title:${base}` : "";
    }
    if (!key) {
      result.push(item);
      continue;
    }
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(item);
  }
  return result;
}

// Formatlanguage helper for this page.
function formatLanguage(code) {
  if (!code) return "";
  const map = {
    ja: "Japanese",
    en: "English",
    ko: "Korean",
    zh: "Chinese",
    "zh-hk": "Chinese (HK)",
    "zh-cn": "Chinese (CN)",
  };
  return map[code] || code;
}

// Formatdate helper for this page.
function formatDate(value) {
  if (!value) return "";
  const text = String(value);
  return text.split("T")[0];
}

// Render Chips into the page.
function renderChips(items) {
  let cleaned = items;
  if (!Array.isArray(cleaned)) {
    cleaned = parseListField(cleaned);
  }
  if (!Array.isArray(cleaned)) {
    cleaned = [];
  }
  cleaned = cleaned.filter(Boolean);
  if (!cleaned.length) return "<span class='muted'>n/a</span>";
  let html = "";
  for (const val of cleaned) {
    html += `<span class="badge">${escapeHtml(val)}</span>`;
  }
  return `<div class="details-chips">${html}</div>`;
}

// Render DetailsHTML into the page.
function renderDetailsHTML(item) {
  try {
    if (!item) return "<div class='details-box'><div class='muted'>No details available.</div></div>";
    const links = parseJsonField(item.links) || {};
    const external = [];
    if (item.link) {
      external.push({ label: "MangaDex", url: item.link });
    }
    if (links.al) {
      external.push({ label: "AniList", url: `https://anilist.co/manga/${links.al}` });
    }
    if (links.kitsu) {
      external.push({ label: "Kitsu", url: `https://kitsu.io/manga/${links.kitsu}` });
    }
    if (links.mu) {
      external.push({ label: "MangaUpdates", url: `https://www.mangaupdates.com/series/${links.mu}` });
    }
    if (links.mal) {
      external.push({ label: "MyAnimeList", url: `https://myanimelist.net/manga/${links.mal}` });
    }

  const rowsData = [
    ["Type", item.item_type],
    ["Status", item.status],
    ["Publishing", item.publishing_date],
    ["Volumes", item.volumes],
    ["Chapters", item.chapters],
    ["Score", item.score],
    ["Content rating", item.content_rating],
    ["Original language", formatLanguage(item.original_language)],
    ["Updated", formatDate(item.updated_at)],
  ];
  let rows = "";
  for (const [label, value] of rowsData) {
    if (value === undefined || value === null || value === "") continue;
    rows += `
        <div class="details-row">
          <div class="details-label">${escapeHtml(label)}</div>
          <div class="details-value">${escapeHtml(value)}</div>
        </div>
      `;
  }

  const description = item.description ? escapeHtml(item.description) : "";
  const cover = item.cover_url
    ? `<img class="details-cover" src="${escapeHtml(item.cover_url)}" alt="Cover" loading="lazy" referrerpolicy="no-referrer">`
    : "";
  let linkHtml = "";
  if (external.length) {
    let linksOut = "";
    for (const link of external) {
      linksOut += `<a href="${escapeHtml(link.url)}" target="_blank" rel="noopener">${escapeHtml(link.label)}</a>`;
    }
    linkHtml = `<div class="details-links">${linksOut}</div>`;
  }

    return `
    <div class="details-box">
      <div class="details-header">
        ${cover}
        <div class="details-meta">
          <div class="details-grid">
            ${rows || `<div class="muted">No extra details available.</div>`}
          </div>
          ${linkHtml}
        </div>
      </div>
      ${description ? `<div class="details-description">${description}</div>` : ""}
      <div class="details-group">
        <div class="details-label">Demographic</div>
        ${renderChips(parseListField(item.demographic))}
      </div>
      <div class="details-group">
        <div class="details-label">Authors</div>
        ${renderChips(parseListField(item.authors))}
      </div>
      <div class="details-group">
        <div class="details-label">Serialization</div>
        ${renderChips(parseListField(item.serialization))}
      </div>
      <div class="details-group">
        <div class="details-label">Genres</div>
        ${renderChips(parseListField(item.genres))}
      </div>
      <div class="details-group">
        <div class="details-label">Themes</div>
        ${renderChips(parseListField(item.themes))}
      </div>
    </div>
  `;
  } catch (err) {
    const message = err?.message || "Failed to render details.";
    return `<div class='details-box'><div class='muted'>${escapeHtml(message)}</div></div>`;
  }
}

window.renderDetailsHTML = renderDetailsHTML;

let detailsModal;
let detailsModalTitle;
let detailsModalContent;
let detailsModalClose;

// Ensuredetailsmodal helper for this page.
function ensureDetailsModal() {
  if (detailsModal) return;
  detailsModal = document.getElementById("details-modal");
  if (!detailsModal) {
    detailsModal = document.createElement("dialog");
    detailsModal.id = "details-modal";
    detailsModal.className = "modal details-modal";
    detailsModal.innerHTML = `
      <div class="details-modal-header">
        <h3 id="details-modal-title">Details</h3>
        <button id="details-modal-close" class="ghost" type="button">Close</button>
      </div>
      <div id="details-modal-content" class="details-modal-content"></div>
    `;
    document.body.appendChild(detailsModal);
  }
  detailsModalTitle = document.getElementById("details-modal-title");
  detailsModalContent = document.getElementById("details-modal-content");
  detailsModalClose = document.getElementById("details-modal-close");
  if (detailsModalClose) {
    detailsModalClose.addEventListener("click", () => detailsModal.close());
  }
  detailsModal.addEventListener("click", (event) => {
    const rect = detailsModal.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) {
      detailsModal.close();
    }
  });
}

// Opendetailsmodal helper for this page.
function openDetailsModal(html, title) {
  ensureDetailsModal();
  if (detailsModalTitle) detailsModalTitle.textContent = title || "Details";
  if (detailsModalContent) detailsModalContent.innerHTML = html || "<div class='muted'>No details available.</div>";
  detailsModal.showModal();
}

window.openDetailsModal = openDetailsModal;
