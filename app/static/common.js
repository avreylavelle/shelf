const BASE_PATH = window.BASE_PATH || ""; // injected by templates

function withBase(path) {
  if (!path.startsWith("/")) return `${BASE_PATH}/${path}`;
  return `${BASE_PATH}${path}`;
}

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

function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

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

function formatDate(value) {
  if (!value) return "";
  const text = String(value);
  return text.split("T")[0];
}

function renderChips(items) {
  const cleaned = (items || []).filter(Boolean);
  if (!cleaned.length) return "<span class='muted'>n/a</span>";
  return `<div class="details-chips">${cleaned.map((val) => `<span class="badge">${escapeHtml(val)}</span>`).join("")}</div>`;
}

function renderDetailsHTML(item) {
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

  const rows = [
    ["Type", item.item_type],
    ["Status", item.status],
    ["Publishing", item.publishing_date],
    ["Volumes", item.volumes],
    ["Chapters", item.chapters],
    ["Score", item.score],
    ["Content rating", item.content_rating],
    ["Original language", formatLanguage(item.original_language)],
    ["Updated", formatDate(item.updated_at)],
  ]
    .filter((entry) => entry[1] !== undefined && entry[1] !== null && entry[1] !== "")
    .map(
      ([label, value]) => `
        <div class="details-row">
          <div class="details-label">${escapeHtml(label)}</div>
          <div class="details-value">${escapeHtml(value)}</div>
        </div>
      `
    )
    .join("");

  const description = item.description ? escapeHtml(item.description) : "";
  const cover = item.cover_url
    ? `<img class="details-cover" src="${escapeHtml(item.cover_url)}" alt="Cover">`
    : "";
  const linkHtml = external.length
    ? `<div class="details-links">${external
        .map((link) => `<a href="${escapeHtml(link.url)}" target="_blank" rel="noopener">${escapeHtml(link.label)}</a>`)
        .join("")}</div>`
    : "";

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
}

window.renderDetailsHTML = renderDetailsHTML;
