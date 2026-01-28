const searchInput = document.getElementById("dnr-search");
const searchBtn = document.getElementById("dnr-search-btn");
const searchStatus = document.getElementById("dnr-search-status");
const searchResults = document.getElementById("dnr-search-results");
const dnrList = document.getElementById("dnr-list");
const dnrSort = document.getElementById("dnr-sort");
const dnrFilter = document.getElementById("dnr-filter");
const typesButtons = Array.from(document.querySelectorAll(".dnr-types-open"));
const typesModal = document.getElementById("dnr-types-modal");
const typesSave = document.getElementById("dnr-types-save");
const typesCancel = document.getElementById("dnr-types-cancel");
const typesAll = document.getElementById("dnr-types-all");
const typesNone = document.getElementById("dnr-types-none");
const typeOptions = Array.from(document.querySelectorAll("#dnr-types-modal .type-option"));


async function loadUiPrefs() {
  try {
    const data = await api("/api/ui-prefs");
    const prefs = data.prefs || {};
    if (prefs.dnr_sort && dnrSort) {
      dnrSort.value = prefs.dnr_sort;
    }
    if (typeOptions.length) {
      if (prefs.dnr_types !== undefined) {
        const raw = prefs.dnr_types;
        const list = Array.isArray(raw) ? raw : String(raw).split(",").map((v) => v.trim()).filter(Boolean);
        const desired = new Set(list.map((val) => String(val)));
        typeOptions.forEach((opt) => {
          opt.checked = desired.has(opt.value);
        });
      } else {
        setDefaultTypes();
      }
    }
  } catch (err) {
    if (typeOptions.length) setDefaultTypes();
  }
}

async function saveUiPref(key, value) {
  try {
    await api("/api/ui-prefs", {
      method: "PUT",
      body: JSON.stringify({ [key]: value }),
    });
  } catch (err) {}
}

function setStatus(text, isError = false) {
  if (!searchStatus) return;
  searchStatus.textContent = text;
  searchStatus.className = isError ? "status error" : "status";
}


const state = { items: [], searchItems: [] };

function selectedTypes() {
  return typeOptions.filter((opt) => opt.checked).map((opt) => opt.value);
}

function selectedTypeSet() {
  const selected = selectedTypes();
  return selected.length ? new Set(selected) : null;
}

function setDefaultTypes() {
  if (!typeOptions.length) return;
  typeOptions.forEach((opt) => {
    opt.checked = true;
  });
}

function filterByType(items) {
  const typeSet = selectedTypeSet();
  if (!typeSet) return items;
  return items.filter((item) => !item.item_type || typeSet.has(item.item_type));
}

const listState = {
  ratings: new Set(),
  dnr: new Set(),
  reading: new Set(),
};

async function loadListState() {
  const [ratingsData, dnrData, readingData] = await Promise.all([
    api("/api/ratings/map").catch(() => ({ items: {} })),
    api("/api/dnr").catch(() => ({ items: [] })),
    api("/api/reading-list").catch(() => ({ items: [] })),
  ]);
  listState.ratings = new Set(Object.keys(ratingsData.items || {}));
  listState.dnr = new Set((dnrData.items || []).map((item) => item.manga_id));
  listState.reading = new Set((readingData.items || []).map((item) => item.manga_id));
}

function getLocations(title) {
  const locations = [];
  if (listState.ratings.has(title)) locations.push("Ratings");
  if (listState.reading.has(title)) locations.push("Reading List");
  if (listState.dnr.has(title)) locations.push("DNR");
  return locations;
}

function renderSearchResults(items) {
  if (!searchResults) return;
  if (!items.length) {
    searchResults.innerHTML = "<p class='muted'>No matches.</p>";
    return;
  }
  searchResults.innerHTML = items
    .map(
      (item) => `
        <div class="list-item">
          <div>
            <strong>${item.display_title || item.title}</strong>
            <div class="muted">Score: ${item.score ?? "n/a"}</div>
            ${getLocations(item.title).length ? `<div class="badge">Currently in: ${getLocations(item.title).join(", ")}</div>` : ""}
            <div class="details" data-details="${item.title}"></div>
          </div>
          <div class="row">
            <button class="details-btn" data-title="${item.title}" type="button">Details</button>
            <button class="dnr-add" data-title="${item.title}" type="button">Add to DNR</button>
          </div>
        </div>
      `
    )
    .join("");
}

async function searchTitles() {
  if (!searchInput) return;
  const query = searchInput.value.trim();
  if (!query) {
    setStatus("Enter a title to search.", true);
    return;
  }
  setStatus("Searching...");
  await loadListState();
  const data = await api(`/api/manga/search?q=${encodeURIComponent(query)}`);
  const items = (data.items || []).filter((item) => !listState.dnr.has(item.title));
  state.searchItems = items;
  renderSearchResults(filterByType(state.searchItems));
  setStatus("");
}

function filterDnrItems(items) {
  const query = (dnrFilter && dnrFilter.value.trim().toLowerCase()) || "";
  const typeSet = selectedTypeSet();
  return items.filter((item) => {
    const title = (item.display_title || item.manga_id || "").toLowerCase();
    if (query && !title.includes(query)) return false;
    if (typeSet && item.item_type && !typeSet.has(item.item_type)) return false;
    return true;
  });
}

function renderDnr(items) {
  if (!dnrList) return;
  if (!items.length) {
    dnrList.innerHTML = "<p class='muted'>No DNR titles yet.</p>";
    return;
  }
  const filtered = filterDnrItems(items);
  dnrList.innerHTML = filtered
    .map(
      (item) => `
        <div class="list-item">
          <div>
            <strong>${item.display_title || item.manga_id}</strong>
            <div class="muted">Added: ${item.created_at}</div>
            <div class="details" data-details="${item.manga_id}"></div>
          </div>
          <div class="row">
            <button class="details-btn" data-title="${item.manga_id}" type="button">Details</button>
            <button class="dnr-remove" data-title="${item.manga_id}" type="button">Remove</button>
          </div>
        </div>
      `
    )
    .join("");
}

async function handleDetails(title, targetEl) {
  if (!targetEl) return;
  api("/api/events", {
    method: "POST",
    body: JSON.stringify({ event_type: "details", manga_id: title }),
  }).catch(() => {});
  const data = await api(`/api/manga/details?title=${encodeURIComponent(title)}`);
  const item = data.item || {};
  const toList = (value) => {
    if (!value) return [];
    if (Array.isArray(value)) return value;
    if (typeof value === "string") {
      const trimmed = value.trim();
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
  };
  const renderChips = (items) =>
    items.length ? `<div class="details-chips">${items.map((val) => `<span class="badge">${val}</span>`).join("")}</div>` : "<span class='muted'>n/a</span>";

  const rows = [
    ["Type", item.item_type],
    ["Status", item.status],
    ["Publishing", item.publishing_date],
    ["Volumes", item.volumes],
    ["Chapters", item.chapters],
    ["Score", item.score],
  ]
    .filter((entry) => entry[1] !== undefined && entry[1] !== null && entry[1] !== "")
    .map(
      ([label, value]) => `
        <div class="details-row">
          <div class="details-label">${label}</div>
          <div class="details-value">${value}</div>
        </div>
      `
    )
    .join("");

  targetEl.innerHTML = `
    <div class="details-box">
      <div class="details-grid">
        ${rows || `<div class="muted">No extra details available.</div>`}
      </div>
      <div class="details-group">
        <div class="details-label">Demographic</div>
        ${renderChips(toList(item.demographic))}
      </div>
      <div class="details-group">
        <div class="details-label">Authors</div>
        ${renderChips(toList(item.authors))}
      </div>
      <div class="details-group">
        <div class="details-label">Serialization</div>
        ${renderChips(toList(item.serialization))}
      </div>
      <div class="details-group">
        <div class="details-label">Genres</div>
        ${renderChips(toList(item.genres))}
      </div>
      <div class="details-group">
        <div class="details-label">Themes</div>
        ${renderChips(toList(item.themes))}
      </div>
    </div>
  `;
}

async function loadDnr() {
  const sort = dnrSort ? dnrSort.value : "chron";
  const data = await api(`/api/dnr?sort=${encodeURIComponent(sort)}`);
  state.items = data.items || [];
  renderDnr(state.items);
}

if (searchBtn) {
  searchBtn.addEventListener("click", () => searchTitles().catch((e) => setStatus(e.message, true)));
}
if (searchInput) {
  searchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      searchTitles().catch((e) => setStatus(e.message, true));
    }
  });
}

if (typesButtons.length && typesModal) {
  typesButtons.forEach((btn) => btn.addEventListener("click", () => typesModal.showModal()));
}
if (typesAll && typeOptions.length) {
  typesAll.addEventListener("click", () => {
    typeOptions.forEach((opt) => {
      opt.checked = true;
    });
  });
}
if (typesNone && typeOptions.length) {
  typesNone.addEventListener("click", () => {
    typeOptions.forEach((opt) => {
      opt.checked = false;
    });
  });
}
if (typesSave && typesModal) {
  typesSave.addEventListener("click", () => {
    saveUiPref("dnr_types", selectedTypes());
    typesModal.close();
    renderDnr(state.items || []);
    if (state.searchItems.length) {
      renderSearchResults(filterByType(state.searchItems));
    }
  });
}
if (typesCancel && typesModal) {
  typesCancel.addEventListener("click", () => typesModal.close());
}
if (typesModal) {
  typesModal.addEventListener("click", (event) => {
    const rect = typesModal.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) {
      typesModal.close();
    }
  });
}


if (dnrFilter) {
  dnrFilter.addEventListener("input", () => {
    renderDnr(state.items || []);
  });
}

if (dnrSort) {
  dnrSort.addEventListener("change", () => {
    saveUiPref("dnr_sort", dnrSort.value);
    loadDnr().catch((e) => setStatus(e.message, true));
  });
}
if (searchResults) {
  searchResults.addEventListener("click", (event) => {
    if (event.target.classList.contains("details-btn")) {
      const title = event.target.dataset.title;
      const targetEl = event.target.closest(".list-item").querySelector(".details");
      if (targetEl.innerHTML) {
        targetEl.innerHTML = "";
        return;
      }
      handleDetails(title, targetEl).catch(() => {});
      return;
    }
    if (!event.target.classList.contains("dnr-add")) return;
    const title = event.target.dataset.title;
    const card = event.target.closest(".list-item");
    const display = card?.querySelector("strong")?.textContent || title;
    const locations = getLocations(title).filter((loc) => loc !== "DNR");
    if (locations.length) {
      if (!confirm(`Move from ${locations.join(", ")} to DNR?`)) {
        return;
      }
    }
    api("/api/dnr", {
      method: "POST",
      body: JSON.stringify({ manga_id: title }),
    })
      .then(() => {
        showToast(`Added ${display} to DNR`);
        if (searchInput) searchInput.value = "";
        if (searchResults) searchResults.innerHTML = "";
        setTimeout(() => window.location.reload(), 600);
      })
      .catch((e) => setStatus(e.message, true));
  });
}

if (dnrList) {
  dnrList.addEventListener("click", (event) => {
    if (event.target.classList.contains("details-btn")) {
      const title = event.target.dataset.title;
      const targetEl = event.target.closest(".list-item").querySelector(".details");
      if (targetEl.innerHTML) {
        targetEl.innerHTML = "";
        return;
      }
      handleDetails(title, targetEl).catch(() => {});
      return;
    }
    if (!event.target.classList.contains("dnr-remove")) return;
    const title = event.target.dataset.title;
    api(`/api/dnr/${encodeURIComponent(title)}`, { method: "DELETE" })
      .then(loadDnr)
      .catch((e) => setStatus(e.message, true));
  });
}

loadUiPrefs().then(() => loadListState().then(() => loadDnr().catch((e) => setStatus(e.message, true))));
