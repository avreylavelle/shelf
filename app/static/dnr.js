const searchInput = document.getElementById("dnr-search");
const searchBtn = document.getElementById("dnr-search-btn");
const searchStatus = document.getElementById("dnr-search-status");
const searchResults = document.getElementById("dnr-search-results");
const dnrList = document.getElementById("dnr-list");
const dnrSort = document.getElementById("dnr-sort");
const dnrFilter = document.getElementById("dnr-filter");


async function loadUiPrefs() {
  try {
    const data = await api("/api/ui-prefs");
    const prefs = data.prefs || {};
    if (prefs.dnr_sort && dnrSort) {
      dnrSort.value = prefs.dnr_sort;
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


const state = { items: [] };

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
  renderSearchResults(items);
  setStatus("");
}

function filterDnrItems(items) {
  const query = (dnrFilter && dnrFilter.value.trim().toLowerCase()) || "";
  if (!query) return items;
  return items.filter((item) => {
    const title = (item.display_title || item.manga_id || "").toLowerCase();
    return title.includes(query);
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
          </div>
          <div class="row">
            <button class="dnr-remove" data-title="${item.manga_id}" type="button">Remove</button>
          </div>
        </div>
      `
    )
    .join("");
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
    if (!event.target.classList.contains("dnr-remove")) return;
    const title = event.target.dataset.title;
    api(`/api/dnr/${encodeURIComponent(title)}`, { method: "DELETE" })
      .then(loadDnr)
      .catch((e) => setStatus(e.message, true));
  });
}

loadUiPrefs().then(() => loadListState().then(() => loadDnr().catch((e) => setStatus(e.message, true))));
