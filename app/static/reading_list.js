const searchInput = document.getElementById("reading-search");
const searchBtn = document.getElementById("reading-search-btn");
const searchStatus = document.getElementById("reading-search-status");
const searchResults = document.getElementById("reading-search-results");
const readingList = document.getElementById("reading-list");
const readingSort = document.getElementById("reading-sort");
const readingFilter = document.getElementById("reading-filter");
const readingStatusFilter = document.getElementById("reading-status-filter");
const typesButtons = Array.from(document.querySelectorAll(".reading-types-open"));
const typesModal = document.getElementById("reading-types-modal");
const typesSave = document.getElementById("reading-types-save");
const typesCancel = document.getElementById("reading-types-cancel");
const typesAll = document.getElementById("reading-types-all");
const typesNone = document.getElementById("reading-types-none");
const typeOptions = Array.from(document.querySelectorAll("#reading-types-modal .type-option"));

const rateModal = document.getElementById("rate-modal");
const rateModalTitle = document.getElementById("rate-modal-title");
const rateModalInput = document.getElementById("rate-modal-input");
const rateModalFlag = document.getElementById("rate-modal-flag");
const rateModalFinished = document.getElementById("rate-modal-finished");
const rateModalAdd = document.getElementById("rate-modal-add");
const rateModalClose = document.getElementById("rate-modal-close");

function openRateModal(mangaId, displayTitle) {
  if (!rateModal) return;
  rateModal.dataset.id = mangaId;
  rateModal.dataset.title = mangaId;
  rateModal.dataset.display = displayTitle || mangaId;
  rateModalTitle.textContent = displayTitle || mangaId;
  rateModalInput.value = "";
  rateModalFlag.checked = false;
  if (rateModalFinished) rateModalFinished.checked = false;
  rateModal.showModal();
}

function closeRateModal() {
  if (!rateModal) return;
  rateModal.close();
}



async function loadUiPrefs() {
  try {
    const data = await api("/api/ui-prefs");
    const prefs = data.prefs || {};
    if (prefs.reading_sort && readingSort) {
      readingSort.value = prefs.reading_sort;
    }
    if (typeOptions.length) {
      if (prefs.reading_types !== undefined) {
        const raw = prefs.reading_types;
        const list = Array.isArray(raw) ? raw : String(raw).split(",").map((v) => v.trim()).filter(Boolean);
        const desired = new Set(list.map((val) => String(val)));
        typeOptions.forEach((opt) => {
          opt.checked = desired.has(opt.value);
        });
      } else {
        setDefaultTypes();
      }
      if (!typeOptions.some((opt) => opt.checked)) {
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


const state = {
  items: [],
  searchItems: [],
};

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
  listState.dnr = new Set((dnrData.items || []).map((item) => item.mdex_id || item.manga_id));
  listState.reading = new Set((readingData.items || []).map((item) => item.mdex_id || item.manga_id));
}

function getLocations(mangaId) {
  const locations = [];
  if (listState.ratings.has(mangaId)) locations.push("Ratings");
  if (listState.reading.has(mangaId)) locations.push("Reading List");
  if (listState.dnr.has(mangaId)) locations.push("DNR");
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
            ${getLocations(item.id).length ? `<div class="badge">Currently in: ${getLocations(item.id).join(", ")}</div>` : ""}
            <div class="details" data-details="${item.id}"></div>
          </div>
          <div class="row">
            <button class="details-btn" data-id="${item.id}" type="button">Details</button>
            <button class="reading-add" data-id="${item.id}" type="button">Add to Reading List</button>
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
  const items = (data.items || []).filter((item) => !listState.reading.has(item.id));
  state.searchItems = items;
  renderSearchResults(filterByType(state.searchItems));
  setStatus("");
}

function normalizeStatus(status) {
  return status || "Plan to Read";
}

function filterReadingItems(items) {
  const query = (readingFilter && readingFilter.value.trim().toLowerCase()) || "";
  const statusFilter = (readingStatusFilter && readingStatusFilter.value) || "";
  const typeSet = selectedTypeSet();
  return items.filter((item) => {
    const title = (item.display_title || item.manga_id || "").toLowerCase();
    const status = normalizeStatus(item.status);
    if (query && !title.includes(query)) return false;
    if (statusFilter && status !== statusFilter) return false;
    if (typeSet && item.item_type && !typeSet.has(item.item_type)) return false;
    return true;
  });
}

function renderReadingList(items) {
  if (!readingList) return;
  if (!items.length) {
    readingList.innerHTML = "<p class='muted'>No reading list titles yet.</p>";
    return;
  }
  readingList.innerHTML = items
    .map(
      (item) => {
        const mangaId = item.mdex_id || item.manga_id;
        return `
        <div class="list-item">
          <div>
            <strong>${item.display_title || item.manga_id}</strong>
            <div class="muted">Added: ${item.created_at}</div>
            <div class="details" data-details="${mangaId}"></div>
          </div>
          <div class="row">
            <button class="details-btn" data-id="${mangaId}" type="button">Details</button>
            <select class="reading-status" data-id="${mangaId}">
              <option value="Plan to Read" ${normalizeStatus(item.status) === "Plan to Read" ? "selected" : ""}>Plan to Read</option>
              <option value="In Progress" ${normalizeStatus(item.status) === "In Progress" ? "selected" : ""}>In Progress</option>
            </select>
            <button class="reading-rate" data-id="${mangaId}" data-display="${item.display_title || item.manga_id}" type="button">Rate</button>
            <button class="reading-remove" data-id="${mangaId}" type="button">Remove</button>
          </div>
        </div>
      `;
      }
    )
    .join("");
}

async function handleDetails(mangaId, title) {
  api("/api/events", {
    method: "POST",
    body: JSON.stringify({ event_type: "details", manga_id: mangaId }),
  }).catch(() => {});
  const data = await api(`/api/manga/details?id=${encodeURIComponent(mangaId)}`);
  const item = data.item || {};
  if (window.openDetailsModal && window.renderDetailsHTML) {
    window.openDetailsModal(window.renderDetailsHTML(item), title || item.display_title || item.title);
  }
}

async function loadReadingList() {
  const sort = readingSort ? readingSort.value : "chron";
  const data = await api(`/api/reading-list?sort=${encodeURIComponent(sort)}`);
  state.items = data.items || [];
  renderReadingList(filterReadingItems(state.items));
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
    saveUiPref("reading_types", selectedTypes());
    typesModal.close();
    renderReadingList(filterReadingItems(state.items));
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


if (readingFilter) {
  readingFilter.addEventListener("input", () => {
    renderReadingList(filterReadingItems(state.items));
  });
}
if (readingStatusFilter) {
  readingStatusFilter.addEventListener("change", () => {
    renderReadingList(filterReadingItems(state.items));
  });
}

if (readingSort) {
  readingSort.addEventListener("change", () => {
    saveUiPref("reading_sort", readingSort.value);
    loadUiPrefs().then(() => loadListState().then(() => loadReadingList().catch((e) => setStatus(e.message, true))));
  });
}
if (searchResults) {
  searchResults.addEventListener("click", (event) => {
    if (event.target.classList.contains("details-btn")) {
      const mangaId = event.target.dataset.id;
      const title = event.target.closest(".list-item")?.querySelector("strong")?.textContent || mangaId;
      handleDetails(mangaId, title).catch(() => {});
      return;
    }
    if (!event.target.classList.contains("reading-add")) return;
    const mangaId = event.target.dataset.id;
    const card = event.target.closest(".list-item");
    const display = card?.querySelector("strong")?.textContent || mangaId;
    const locations = getLocations(mangaId).filter((loc) => loc !== "Reading List");
    if (locations.length) {
      if (!confirm(`Move from ${locations.join(", ")} to Reading List?`)) {
        return;
      }
    }
    api("/api/reading-list", {
      method: "POST",
      body: JSON.stringify({ manga_id: mangaId }),
    })
      .then(() => {
        showToast(`Added ${display} to Reading List`);
        if (searchInput) searchInput.value = "";
        if (searchResults) searchResults.innerHTML = "";
        setTimeout(() => window.location.reload(), 600);
      })
      .catch((e) => setStatus(e.message, true));
  });
}


if (readingList) {
  readingList.addEventListener("change", (event) => {
    if (!event.target.classList.contains("reading-status")) return;
    const mangaId = event.target.dataset.id;
    const status = event.target.value;
    api("/api/reading-list", {
      method: "PUT",
      body: JSON.stringify({ manga_id: mangaId, status }),
    }).catch((e) => setStatus(e.message, true));
  });
}

if (readingList) {
  readingList.addEventListener("click", (event) => {
    if (event.target.classList.contains("details-btn")) {
      const mangaId = event.target.dataset.id;
      const title = event.target.closest(".list-item")?.querySelector("strong")?.textContent || mangaId;
      handleDetails(mangaId, title).catch(() => {});
      return;
    }
    if (event.target.classList.contains("reading-remove")) {
      const mangaId = event.target.dataset.id;
      api(`/api/reading-list/${encodeURIComponent(mangaId)}`, { method: "DELETE" })
        .then(loadReadingList)
        .catch((e) => setStatus(e.message, true));
    }
    if (event.target.classList.contains("reading-rate")) {
      const mangaId = event.target.dataset.id;
      const display = event.target.dataset.display || mangaId;
      openRateModal(mangaId, display);
    }
  });
}


if (rateModalAdd) {
  rateModalAdd.addEventListener("click", () => {
    const mangaId = rateModal.dataset.id || rateModal.dataset.title;
    const display = rateModal.dataset.display || mangaId;
    const value = rateModalInput.value;
    const rating = value === "" ? null : Number(value);
    const recommendedByUs = rateModalFlag.checked;
    const finishedReading = rateModalFinished ? rateModalFinished.checked : false;
    api("/api/ratings", {
      method: "POST",
      body: JSON.stringify({ manga_id: mangaId, rating, recommended_by_us: recommendedByUs, finished_reading: finishedReading }),
    })
      .then(() => {
        showToast(`${display} added to ratings with rating ${value === "" ? "n/a" : rating}`);
        if (searchInput) searchInput.value = "";
        if (searchResults) searchResults.innerHTML = "";
        setTimeout(() => window.location.reload(), 600);
      })
      .then(closeRateModal)
      .catch((err) => setStatus(err.message, true));
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
loadListState().then(() => loadReadingList().catch((e) => setStatus(e.message, true)));
