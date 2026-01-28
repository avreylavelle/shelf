const ratingsEl = document.getElementById("ratings");
const searchInput = document.getElementById("rating-search");
const searchBtn = document.getElementById("rating-search-btn");
const searchStatus = document.getElementById("rating-search-status");
const searchResults = document.getElementById("rating-search-results");
const ratingsSort = document.getElementById("ratings-sort");
const ratingsFilter = document.getElementById("ratings-filter");
const toggleRatings = document.getElementById("toggle-ratings");
const loadingEl = document.getElementById("ratings-loading");
const rateModal = document.getElementById("rate-modal");
const rateModalTitle = document.getElementById("rate-modal-title");
const rateModalInput = document.getElementById("rate-modal-input");
const rateModalFlag = document.getElementById("rate-modal-flag");
const rateModalFinished = document.getElementById("rate-modal-finished");
const rateModalAdd = document.getElementById("rate-modal-add");
const rateModalReading = document.getElementById("rate-modal-reading");
const rateModalClose = document.getElementById("rate-modal-close");


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

const state = {
  expanded: false,
  sort: "chron",
  items: [],
};

function openRateModal(title, displayTitle, rating = "", recommended = true, finished = false) {
  if (!rateModal) return;
  rateModal.dataset.title = title;
  rateModal.dataset.display = displayTitle || title;
  rateModal.dataset.currentRating = rating ?? "";
  rateModalTitle.textContent = displayTitle || title;
  rateModalInput.value = rating ?? "";
  rateModalFlag.checked = Boolean(Number(recommended)) || recommended === true;
  if (rateModalFinished) rateModalFinished.checked = Boolean(Number(finished)) || finished === true;
  rateModal.showModal();
}

function closeRateModal() {
  if (!rateModal) return;
  rateModal.close();
}

function setSearchStatus(text, isError = false) {
  if (!searchStatus) return;
  searchStatus.textContent = text;
  searchStatus.className = isError ? "status error" : "status";
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
            <button class="rate-open" data-title="${item.title}" data-display="${item.display_title || item.title}" type="button">Rate</button>
          </div>
        </div>
      `
    )
    .join("");
}

async function searchTitles() {
  if (!searchInput || !searchResults) return;
  const query = searchInput.value.trim();
  if (!query) {
    setSearchStatus("Enter a title to search.", true);
    return;
  }
  setSearchStatus("Searching...");
  await loadListState();
  const data = await api(`/api/manga/search?q=${encodeURIComponent(query)}`);
  const items = (data.items || []).filter((item) => !listState.ratings.has(item.title));
  renderSearchResults(items);
  setSearchStatus("");
}

async function loadUiPrefs() {
  try {
    const data = await api("/api/ui-prefs");
    const prefs = data.prefs || {};
    if (prefs.ratings_sort && ratingsSort) {
      ratingsSort.value = prefs.ratings_sort;
      state.sort = prefs.ratings_sort;
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

function setLoading(isLoading) {
  loadingEl.setAttribute("aria-busy", String(isLoading));
  loadingEl.style.display = isLoading ? "inline-flex" : "none";
}

function filterRatingItems(items) {
  const query = (ratingsFilter && ratingsFilter.value.trim().toLowerCase()) || "";
  if (!query) return items;
  return items.filter((item) => {
    const title = (item.display_title || item.manga_id || "").toLowerCase();
    return title.includes(query);
  });
}

function renderRatings() {
  const filtered = filterRatingItems(state.items);
  const limit = state.expanded ? filtered.length : 10;
  const items = filtered.slice(0, limit);

  if (!items.length) {
    ratingsEl.innerHTML = "<p class='muted'>No ratings yet.</p>";
    return;
  }

  ratingsEl.innerHTML = items
    .map(
      (item) => `
        <div class="list-item">
          <div>
            <strong>${item.display_title || item.manga_id}</strong>
            <span class="muted">Rating: ${item.rating ?? "n/a"}</span>
          </div>
          <div class="row">
            <button class="rate-open" data-title="${item.manga_id}" data-display="${item.display_title || item.manga_id}" data-rating="${item.rating ?? ""}" data-rec="${item.recommended_by_us ? 1 : 0}" data-finished="${item.finished_reading ? 1 : 0}" type="button">Rate</button>
            <button class="delete-btn" data-manga-id="${item.manga_id}">Remove</button>
          </div>
        </div>
      `
    )
    .join("");

  toggleRatings.textContent = state.expanded ? "Show Less" : "Show All";
}

async function loadRatings() {
  setLoading(true);
  try {
    const data = await api(`/api/ratings?sort=${encodeURIComponent(state.sort)}`);
    state.items = data.items || [];
    renderRatings();
  } finally {
    setLoading(false);
  }
}

async function deleteRating(mangaId) {
  await api(`/api/ratings/${encodeURIComponent(mangaId)}`, { method: "DELETE" });
  await loadRatings();
}

if (searchBtn) {
  searchBtn.addEventListener("click", () => searchTitles().catch((e) => setSearchStatus(e.message, true)));
}
if (searchInput) {
  searchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      searchTitles().catch((e) => setSearchStatus(e.message, true));
    }
  });
}

if (ratingsFilter) {
  ratingsFilter.addEventListener("input", () => {
    renderRatings();
  });
}

ratingsSort.addEventListener("change", () => {
  state.sort = ratingsSort.value;
  saveUiPref("ratings_sort", state.sort);
  loadRatings();
});

toggleRatings.addEventListener("click", () => {
  state.expanded = !state.expanded;
  renderRatings();
});

ratingsEl.addEventListener("click", (event) => {
  if (event.target.classList.contains("delete-btn")) {
    const mangaId = event.target.dataset.mangaId;
    deleteRating(mangaId);
  }
  if (event.target.classList.contains("rate-open")) {
    const title = event.target.dataset.title;
    const display = event.target.dataset.display;
    const rating = event.target.dataset.rating || "";
    const rec = event.target.dataset.rec || 0;
    const finished = event.target.dataset.finished || 0;
    openRateModal(title, display, rating, rec, finished);
  }
});

if (searchResults) {
  searchResults.addEventListener("click", (event) => {
    if (!event.target.classList.contains("rate-open")) return;
    const title = event.target.dataset.title;
    const display = event.target.dataset.display;
    openRateModal(title, display);
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
    const current = rateModal.dataset.currentRating || "";
    const ratingDisplay = value === "" ? (current !== "" ? current : "n/a") : rating;
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
        showToast(`${display} added to ratings with rating ${ratingDisplay}`);
        if (searchInput) searchInput.value = "";
        if (searchResults) searchResults.innerHTML = "";
        setTimeout(() => window.location.reload(), 600);
      })
      .catch((err) => {
        showToast(err.message || "Request failed");
      })
      .finally(closeRateModal);
  });
}

if (rateModalReading) {
  rateModalReading.addEventListener("click", () => {
    const title = rateModal.dataset.title;
    api("/api/reading-list", {
      method: "POST",
      body: JSON.stringify({ manga_id: title }),
    })
      .then(closeRateModal)
      .catch(() => {});
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

setLoading(false);
loadListState().then(() => loadUiPrefs().then(loadRatings));
