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
            <button class="dnr-add" data-id="${item.id}" type="button">Add to DNR</button>
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
  const items = (data.items || []).filter((item) => !listState.dnr.has(item.id));
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
            <button class="dnr-remove" data-id="${mangaId}" type="button">Remove</button>
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
      const mangaId = event.target.dataset.id;
      const title = event.target.closest(".list-item")?.querySelector("strong")?.textContent || mangaId;
      handleDetails(mangaId, title).catch(() => {});
      return;
    }
    if (!event.target.classList.contains("dnr-add")) return;
    const mangaId = event.target.dataset.id;
    const card = event.target.closest(".list-item");
    const display = card?.querySelector("strong")?.textContent || mangaId;
    const locations = getLocations(mangaId).filter((loc) => loc !== "DNR");
    if (locations.length) {
      if (!confirm(`Move from ${locations.join(", ")} to DNR?`)) {
        return;
      }
    }
    api("/api/dnr", {
      method: "POST",
      body: JSON.stringify({ manga_id: mangaId }),
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
        const mangaId = event.target.dataset.id;
        const title = event.target.closest(".list-item")?.querySelector("strong")?.textContent || mangaId;
        handleDetails(mangaId, title).catch(() => {});
        return;
      }
    if (!event.target.classList.contains("dnr-remove")) return;
    const mangaId = event.target.dataset.id;
    api(`/api/dnr/${encodeURIComponent(mangaId)}`, { method: "DELETE" })
      .then(loadDnr)
      .catch((e) => setStatus(e.message, true));
  });
}

loadUiPrefs().then(() => loadListState().then(() => loadDnr().catch((e) => setStatus(e.message, true))));
