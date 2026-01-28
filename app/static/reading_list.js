const searchInput = document.getElementById("reading-search");
const searchBtn = document.getElementById("reading-search-btn");
const searchStatus = document.getElementById("reading-search-status");
const searchResults = document.getElementById("reading-search-results");
const readingList = document.getElementById("reading-list");
const readingSort = document.getElementById("reading-sort");
const readingFilter = document.getElementById("reading-filter");
const readingStatusFilter = document.getElementById("reading-status-filter");

const rateModal = document.getElementById("rate-modal");
const rateModalTitle = document.getElementById("rate-modal-title");
const rateModalInput = document.getElementById("rate-modal-input");
const rateModalFlag = document.getElementById("rate-modal-flag");
const rateModalFinished = document.getElementById("rate-modal-finished");
const rateModalAdd = document.getElementById("rate-modal-add");
const rateModalClose = document.getElementById("rate-modal-close");

function openRateModal(title, displayTitle) {
  if (!rateModal) return;
  rateModal.dataset.title = title;
  rateModal.dataset.display = displayTitle || title;
  rateModalTitle.textContent = displayTitle || title;
  rateModalInput.value = "";
  rateModalFlag.checked = true;
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
  } catch (err) {}
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
};

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
          </div>
          <div class="row">
            <button class="reading-add" data-title="${item.title}" type="button">Add to Reading List</button>
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
  const items = (data.items || []).filter((item) => !listState.reading.has(item.title));
  renderSearchResults(items);
  setStatus("");
}

function normalizeStatus(status) {
  return status || "Plan to Read";
}

function filterReadingItems(items) {
  const query = (readingFilter && readingFilter.value.trim().toLowerCase()) || "";
  const statusFilter = (readingStatusFilter && readingStatusFilter.value) || "";
  return items.filter((item) => {
    const title = (item.display_title || item.manga_id || "").toLowerCase();
    const status = normalizeStatus(item.status);
    if (query && !title.includes(query)) return false;
    if (statusFilter && status !== statusFilter) return false;
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
      (item) => `
        <div class="list-item">
          <div>
            <strong>${item.display_title || item.manga_id}</strong>
            <div class="muted">Added: ${item.created_at}</div>
          </div>
          <div class="row">
            <select class="reading-status" data-title="${item.manga_id}">
              <option value="Plan to Read" ${normalizeStatus(item.status) === "Plan to Read" ? "selected" : ""}>Plan to Read</option>
              <option value="In Progress" ${normalizeStatus(item.status) === "In Progress" ? "selected" : ""}>In Progress</option>
            </select>
            <button class="reading-rate" data-title="${item.manga_id}" data-display="${item.display_title || item.manga_id}" type="button">Rate</button>
            <button class="reading-remove" data-title="${item.manga_id}" type="button">Remove</button>
          </div>
        </div>
      `
    )
    .join("");
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
    if (!event.target.classList.contains("reading-add")) return;
    const title = event.target.dataset.title;
    const card = event.target.closest(".list-item");
    const display = card?.querySelector("strong")?.textContent || title;
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
    const title = event.target.dataset.title;
    const status = event.target.value;
    api("/api/reading-list", {
      method: "PUT",
      body: JSON.stringify({ manga_id: title, status }),
    }).catch((e) => setStatus(e.message, true));
  });
}

if (readingList) {
  readingList.addEventListener("click", (event) => {
    if (event.target.classList.contains("reading-remove")) {
      const title = event.target.dataset.title;
      api(`/api/reading-list/${encodeURIComponent(title)}`, { method: "DELETE" })
        .then(loadReadingList)
        .catch((e) => setStatus(e.message, true));
    }
    if (event.target.classList.contains("reading-rate")) {
      const title = event.target.dataset.title;
      const display = event.target.dataset.display || title;
      openRateModal(title, display);
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
    api("/api/ratings", {
      method: "POST",
      body: JSON.stringify({ manga_id: title, rating, recommended_by_us: recommendedByUs, finished_reading: finishedReading }),
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
