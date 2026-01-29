const searchInput = document.getElementById("search-input");
const searchBtn = document.getElementById("search-btn");
const searchStatus = document.getElementById("search-status");
const searchResults = document.getElementById("search-results");

const browseBtn = document.getElementById("browse-btn");
const browseResults = document.getElementById("browse-results");
const browseGenreSelect = document.getElementById("browse-genre-select");
const browseThemeSelect = document.getElementById("browse-theme-select");
const browseAddGenre = document.getElementById("browse-add-genre");
const browseAddTheme = document.getElementById("browse-add-theme");
const browseGenresEl = document.getElementById("browse-genres");
const browseThemesEl = document.getElementById("browse-themes");
const browseSort = document.getElementById("browse-sort");
const browseMinScore = document.getElementById("browse-min-score");
const browseStatus = document.getElementById("browse-status");

const typesButtons = Array.from(document.querySelectorAll(".search-types-open"));
const typesModal = document.getElementById("search-types-modal");
const typesSave = document.getElementById("search-types-save");
const typesCancel = document.getElementById("search-types-cancel");
const typesAll = document.getElementById("search-types-all");
const typesNone = document.getElementById("search-types-none");
const typeOptions = Array.from(document.querySelectorAll("#search-types-modal .type-option"));

const addModal = document.getElementById("add-modal");
const addModalTitle = document.getElementById("add-modal-title");
const addRateBtn = document.getElementById("add-rate");
const addReadingBtn = document.getElementById("add-reading");
const addDnrBtn = document.getElementById("add-dnr");
const addCloseBtn = document.getElementById("add-close");

const rateModal = document.getElementById("rate-modal");
const rateModalTitle = document.getElementById("rate-modal-title");
const rateModalInput = document.getElementById("rate-modal-input");
const rateModalFlag = document.getElementById("rate-modal-flag");
const rateModalFinished = document.getElementById("rate-modal-finished");
const rateModalAdd = document.getElementById("rate-modal-add");
const rateModalClose = document.getElementById("rate-modal-close");

const state = {
  searchItems: [],
  browseItems: [],
  browseGenres: [],
  browseThemes: [],
};

const listState = {
  ratings: new Set(),
  dnr: new Set(),
  reading: new Set(),
};

function cssEscape(value) {
  if (window.CSS && CSS.escape) return CSS.escape(value);
  return String(value).replace(/"/g, '\\"');
}

function setStatus(text, isError = false) {
  if (!searchStatus) return;
  searchStatus.textContent = text;
  searchStatus.className = isError ? "status error" : "status";
}

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

function updateListState(title, destination) {
  listState.ratings.delete(title);
  listState.reading.delete(title);
  listState.dnr.delete(title);
  if (destination === "Ratings") listState.ratings.add(title);
  if (destination === "Reading List") listState.reading.add(title);
  if (destination === "DNR") listState.dnr.add(title);
}

function getLocations(title) {
  const locations = [];
  if (listState.ratings.has(title)) locations.push("Ratings");
  if (listState.reading.has(title)) locations.push("Reading List");
  if (listState.dnr.has(title)) locations.push("DNR");
  return locations;
}

function openAddModal(title, displayTitle) {
  if (!addModal) return;
  addModal.dataset.title = title;
  addModal.dataset.display = displayTitle || title;
  if (addModalTitle) addModalTitle.textContent = displayTitle || "Add";
  addModal.showModal();
}

function closeAddModal() {
  if (!addModal) return;
  addModal.close();
}

function openRateModal(title, displayTitle) {
  if (!rateModal) return;
  rateModal.dataset.title = title;
  rateModal.dataset.display = displayTitle || title;
  rateModalTitle.textContent = displayTitle || title;
  rateModalInput.value = "";
  rateModalFlag.checked = false;
  if (rateModalFinished) rateModalFinished.checked = false;
  rateModal.showModal();
}

function closeRateModal() {
  if (!rateModal) return;
  rateModal.close();
}

function removeItemEverywhere(title) {
  if (searchResults) {
    const el = searchResults.querySelector(`.list-item[data-title="${cssEscape(title)}"]`);
    if (el) el.remove();
  }
  if (browseResults) {
    const el = browseResults.querySelector(`.list-item[data-title="${cssEscape(title)}"]`);
    if (el) el.remove();
  }
  state.searchItems = state.searchItems.filter((item) => item.title !== title);
  state.browseItems = state.browseItems.filter((item) => item.title !== title);
}

function renderList(container, items) {
  if (!container) return;
  if (!items.length) {
    container.innerHTML = "<p class='muted'>No matches.</p>";
    return;
  }
  container.innerHTML = items
    .map(
      (item) => `
        <div class="list-item" data-title="${item.title}" data-display="${item.display_title || item.title}">
          <div>
            <strong>${item.display_title || item.title}</strong>
            <div class="muted">Score: ${item.score ?? "n/a"}</div>
            ${getLocations(item.title).length ? `<div class="badge">Currently in: ${getLocations(item.title).join(", ")}</div>` : ""}
            <div class="details" data-details="${item.title}"></div>
          </div>
          <div class="row">
            <button class="details-btn" data-title="${item.title}" type="button">Details</button>
            <button class="add-open" data-title="${item.title}" data-display="${item.display_title || item.title}" type="button">Add</button>
          </div>
        </div>
      `
    )
    .join("");
}

function renderBrowseChips() {
  if (browseGenresEl) {
    browseGenresEl.innerHTML = state.browseGenres
      .map(
        (item) => `
          <button class="chip" data-type="genre" data-value="${item}" type="button">
            ${item} <span aria-hidden="true">×</span>
          </button>
        `
      )
      .join("");
  }
  if (browseThemesEl) {
    browseThemesEl.innerHTML = state.browseThemes
      .map(
        (item) => `
          <button class="chip" data-type="theme" data-value="${item}" type="button">
            ${item} <span aria-hidden="true">×</span>
          </button>
        `
      )
      .join("");
  }
}

function addBrowseGenre() {
  if (!browseGenreSelect) return;
  const value = browseGenreSelect.value;
  if (!value || state.browseGenres.includes(value)) return;
  state.browseGenres.push(value);
  renderBrowseChips();
}

function addBrowseTheme() {
  if (!browseThemeSelect) return;
  const value = browseThemeSelect.value;
  if (!value || state.browseThemes.includes(value)) return;
  state.browseThemes.push(value);
  renderBrowseChips();
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
  state.searchItems = filterByType(data.items || []);
  renderList(searchResults, state.searchItems);
  setStatus("");
}

async function browseTitles() {
  await loadListState();
  const params = new URLSearchParams();
  if (browseSort && browseSort.value) params.set("sort", browseSort.value);
  if (browseMinScore && browseMinScore.value) params.set("min_score", browseMinScore.value);
  if (browseStatus && browseStatus.value) params.set("status", browseStatus.value);
  if (state.browseGenres.length) params.set("genres", state.browseGenres.join(","));
  if (state.browseThemes.length) params.set("themes", state.browseThemes.join(","));
  const types = selectedTypes();
  if (types.length) params.set("content_types", types.join(","));

  const data = await api(`/api/manga/browse?${params.toString()}`);
  state.browseItems = filterByType(data.items || []);
  renderList(browseResults, state.browseItems);
}

async function loadUiPrefs() {
  try {
    const data = await api("/api/ui-prefs");
    const prefs = data.prefs || {};
    if (typeOptions.length) {
      if (prefs.search_types !== undefined) {
        const raw = prefs.search_types;
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
if (browseBtn) {
  browseBtn.addEventListener("click", () => browseTitles().catch((e) => setStatus(e.message, true)));
}

if (browseAddGenre) {
  browseAddGenre.addEventListener("click", (event) => {
    event.preventDefault();
    addBrowseGenre();
  });
}
if (browseAddTheme) {
  browseAddTheme.addEventListener("click", (event) => {
    event.preventDefault();
    addBrowseTheme();
  });
}

if (browseGenresEl) {
  browseGenresEl.addEventListener("click", (event) => {
    if (!event.target.closest(".chip")) return;
    const chip = event.target.closest(".chip");
    const value = chip.dataset.value;
    state.browseGenres = state.browseGenres.filter((item) => item !== value);
    renderBrowseChips();
  });
}
if (browseThemesEl) {
  browseThemesEl.addEventListener("click", (event) => {
    if (!event.target.closest(".chip")) return;
    const chip = event.target.closest(".chip");
    const value = chip.dataset.value;
    state.browseThemes = state.browseThemes.filter((item) => item !== value);
    renderBrowseChips();
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
    saveUiPref("search_types", selectedTypes());
    typesModal.close();
    renderList(searchResults, filterByType(state.searchItems));
    renderList(browseResults, filterByType(state.browseItems));
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

function attachListHandlers(container) {
  if (!container) return;
  container.addEventListener("click", (event) => {
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
    if (event.target.classList.contains("add-open")) {
      const title = event.target.dataset.title;
      const displayTitle = event.target.dataset.display;
      openAddModal(title, displayTitle);
    }
  });
}

attachListHandlers(searchResults);
attachListHandlers(browseResults);

if (addRateBtn) {
  addRateBtn.addEventListener("click", () => {
    const title = addModal.dataset.title;
    const display = addModal.dataset.display || title;
    closeAddModal();
    openRateModal(title, display);
  });
}
if (addReadingBtn) {
  addReadingBtn.addEventListener("click", () => {
    const title = addModal.dataset.title;
    const display = addModal.dataset.display || title;
    const locations = getLocations(title).filter((loc) => loc !== "Reading List");
    if (locations.length) {
      if (!confirm(`Move from ${locations.join(", ")} to Reading List?`)) {
        return;
      }
    }
    api("/api/reading-list", {
      method: "POST",
      body: JSON.stringify({ manga_id: title }),
    })
      .then(() => {
        updateListState(title, "Reading List");
        showToast(`Added ${display} to Reading List`);
        removeItemEverywhere(title);
      })
      .catch((err) => {
        showToast(err.message || "Request failed");
      })
      .finally(closeAddModal);
  });
}
if (addDnrBtn) {
  addDnrBtn.addEventListener("click", () => {
    const title = addModal.dataset.title;
    const display = addModal.dataset.display || title;
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
        updateListState(title, "DNR");
        showToast(`Added ${display} to DNR`);
        removeItemEverywhere(title);
      })
      .catch((err) => {
        showToast(err.message || "Request failed");
      })
      .finally(closeAddModal);
  });
}
if (addCloseBtn) {
  addCloseBtn.addEventListener("click", closeAddModal);
}
if (addModal) {
  addModal.addEventListener("click", (event) => {
    const rect = addModal.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) {
      closeAddModal();
    }
  });
}

if (rateModalAdd) {
  rateModalAdd.addEventListener("click", () => {
    const title = rateModal.dataset.title;
    const display = rateModal.dataset.display || title;
    const value = rateModalInput.value;
    const rating = value === "" ? null : Number(value);
    const recommendedByUs = rateModalFlag.checked;
    const finishedReading = rateModalFinished ? rateModalFinished.checked : false;
    const locations = getLocations(title).filter((loc) => loc !== "Ratings");
    if (locations.length) {
      if (!confirm(`Move from ${locations.join(", ")} to Ratings?`)) {
        return;
      }
    }
    api("/api/ratings", {
      method: "POST",
      body: JSON.stringify({ manga_id: title, rating, recommended_by_us: recommendedByUs, finished_reading: finishedReading }),
    })
      .then(() => {
        updateListState(title, "Ratings");
        showToast(`${display} added to ratings with rating ${value === "" ? "n/a" : rating}`);
        removeItemEverywhere(title);
      })
      .catch((err) => {
        showToast(err.message || "Request failed");
      })
      .finally(closeRateModal);
  });
}
if (rateModalClose) {
  rateModalClose.addEventListener("click", closeRateModal);
}
if (rateModal) {
  rateModal.addEventListener("click", (event) => {
    const rect = rateModal.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) {
      closeRateModal();
    }
  });
}

loadUiPrefs().catch(() => {});
loadListState().catch(() => {});
