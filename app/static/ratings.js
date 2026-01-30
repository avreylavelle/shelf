const ratingsEl = document.getElementById("ratings");
const ratingsSort = document.getElementById("ratings-sort");
const ratingsFilter = document.getElementById("ratings-filter");
const toggleRatings = document.getElementById("toggle-ratings");
const loadingEl = document.getElementById("ratings-loading");
const typesButtons = Array.from(document.querySelectorAll(".ratings-types-open"));
const typesModal = document.getElementById("ratings-types-modal");
const typesSave = document.getElementById("ratings-types-save");
const typesCancel = document.getElementById("ratings-types-cancel");
const typesAll = document.getElementById("ratings-types-all");
const typesNone = document.getElementById("ratings-types-none");
const typeOptions = Array.from(document.querySelectorAll("#ratings-types-modal .type-option"));
const rateModal = document.getElementById("rate-modal");
const rateModalTitle = document.getElementById("rate-modal-title");
const rateModalInput = document.getElementById("rate-modal-input");
const rateModalFlag = document.getElementById("rate-modal-flag");
const rateModalFinished = document.getElementById("rate-modal-finished");
const rateModalAdd = document.getElementById("rate-modal-add");
const rateModalReading = document.getElementById("rate-modal-reading");
const rateModalClose = document.getElementById("rate-modal-close");


const state = {
  expanded: false,
  sort: "chron",
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

function openRateModal(mangaId, displayTitle, rating = "", recommended = false, finished = false) {
  if (!rateModal) return;
  rateModal.dataset.id = mangaId;
  rateModal.dataset.title = mangaId;
  rateModal.dataset.display = displayTitle || mangaId;
  rateModal.dataset.currentRating = rating ?? "";
  rateModalTitle.textContent = displayTitle || mangaId;
  rateModalInput.value = rating ?? "";
  rateModalFlag.checked = Boolean(Number(recommended)) || recommended === true;
  if (rateModalFinished) rateModalFinished.checked = Boolean(Number(finished)) || finished === true;
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
    if (prefs.ratings_sort && ratingsSort) {
      ratingsSort.value = prefs.ratings_sort;
      state.sort = prefs.ratings_sort;
    }
    if (typeOptions.length) {
      if (prefs.ratings_types !== undefined) {
        const raw = prefs.ratings_types;
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

function setLoading(isLoading) {
  loadingEl.setAttribute("aria-busy", String(isLoading));
  loadingEl.style.display = isLoading ? "inline-flex" : "none";
}

function filterRatingItems(items) {
  const query = (ratingsFilter && ratingsFilter.value.trim().toLowerCase()) || "";
  const typeSet = selectedTypeSet();
  return items.filter((item) => {
    const title = (item.display_title || item.manga_id || "").toLowerCase();
    if (query && !title.includes(query)) return false;
    if (typeSet && item.item_type && !typeSet.has(item.item_type)) return false;
    return true;
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
    .map((item) => {
      const mangaId = item.mdex_id || item.manga_id;
      const title = item.display_title || item.manga_id;
      const cover = item.cover_url
        ? `<img class="result-cover" src="${item.cover_url}" alt="Cover" loading="lazy" referrerpolicy="no-referrer">`
        : `<div class="result-cover placeholder"></div>`;
      return `
        <div class="result-card" data-id="${mangaId}" data-display="${title}">
          <strong>${title}</strong>
          ${cover}
          <div class="muted">Rating: ${item.rating ?? "n/a"}</div>
          <div class="result-actions">
            <button class="details-btn" data-id="${mangaId}" type="button">Details</button>
            <button class="rate-open" data-id="${mangaId}" data-display="${title}" data-rating="${item.rating ?? ""}" data-rec="${item.recommended_by_us ? 1 : 0}" data-finished="${item.finished_reading ? 1 : 0}" type="button">Update</button>
            <button class="delete-btn" data-manga-id="${mangaId}">Remove</button>
          </div>
        </div>
      `;
    })
    .join("");

  toggleRatings.textContent = state.expanded ? "Show Less" : "Show All";
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
  if (event.target.classList.contains("details-btn")) {
    const mangaId = event.target.dataset.id;
    const title = event.target.closest(".result-card")?.querySelector("strong")?.textContent || mangaId;
    handleDetails(mangaId, title).catch(() => {});
  }
  if (event.target.classList.contains("delete-btn")) {
    const mangaId = event.target.dataset.mangaId;
    deleteRating(mangaId);
  }
  if (event.target.classList.contains("rate-open")) {
    const mangaId = event.target.dataset.id;
    const display = event.target.dataset.display;
    const rating = event.target.dataset.rating || "";
    const rec = event.target.dataset.rec || 0;
    const finished = event.target.dataset.finished || 0;
    openRateModal(mangaId, display, rating, rec, finished);
  }
});

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
    saveUiPref("ratings_types", selectedTypes());
    typesModal.close();
    renderRatings();
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

if (rateModalAdd) {
  rateModalAdd.addEventListener("click", () => {
    const mangaId = rateModal.dataset.title || rateModal.dataset.id;
    const display = rateModal.dataset.display || mangaId;
    const value = rateModalInput.value;
    const rating = value === "" ? null : Number(value);
    const recommendedByUs = rateModalFlag.checked;
    const finishedReading = rateModalFinished ? rateModalFinished.checked : false;
    const current = rateModal.dataset.currentRating || "";
    const ratingDisplay = value === "" ? (current !== "" ? current : "n/a") : rating;
    const locations = getLocations(mangaId).filter((loc) => loc !== "Ratings");
    if (locations.length) {
      if (!confirm(`Move from ${locations.join(", ")} to Ratings?`)) {
        return;
      }
    }
    api("/api/ratings", {
      method: "POST",
      body: JSON.stringify({ manga_id: mangaId, rating, recommended_by_us: recommendedByUs, finished_reading: finishedReading }),
    })
      .then(() => {
        showToast(`${display} added to ratings with rating ${ratingDisplay}`);
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
    const mangaId = rateModal.dataset.id || rateModal.dataset.title;
    api("/api/reading-list", {
      method: "POST",
      body: JSON.stringify({ manga_id: mangaId }),
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
