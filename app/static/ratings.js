const ratingsEl = document.getElementById("ratings");
const searchInput = document.getElementById("rating-search");
const searchBtn = document.getElementById("rating-search-btn");
const searchStatus = document.getElementById("rating-search-status");
const searchResults = document.getElementById("rating-search-results");
const ratingsSort = document.getElementById("ratings-sort");
const toggleRatings = document.getElementById("toggle-ratings");
const loadingEl = document.getElementById("ratings-loading");

const state = {
  expanded: false,
  sort: "chron",
  items: [],
};

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
          </div>
          <div class="stack">
            <div class="row">
              <input type="number" min="0" max="10" step="0.1" placeholder="rating" class="rating-new" data-manga-id="${item.title}" />
            </div>
            <div class="row">
              <label class="inline flag-line">
              <input type="checkbox" class="rating-recommended" data-manga-id="${item.title}" />
              Recommended by us
            </label>
            <button class="add-rating-btn" data-manga-id="${item.title}">Add</button>
            </div>
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
  const data = await api(`/api/manga/search?q=${encodeURIComponent(query)}`);
  renderSearchResults(data.items || []);
  setSearchStatus("");
}

function setLoading(isLoading) {
  loadingEl.setAttribute("aria-busy", String(isLoading));
  loadingEl.style.display = isLoading ? "inline-flex" : "none";
}

function renderRatings() {
  const limit = state.expanded ? state.items.length : 10;
  const items = state.items.slice(0, limit);

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
          <div class="stack">
            <div class="row">
              <input type="number" min="0" max="10" step="0.1" placeholder="update" data-manga-id="${item.manga_id}" class="rating-update" />
            </div>
            <div class="row">
              <label class="inline flag-line">
              <input type="checkbox" class="rating-recommended" data-manga-id="${item.manga_id}" ${item.recommended_by_us ? "checked" : ""} />
              Recommended by us
            </label>
            <button class="update-btn" data-manga-id="${item.manga_id}">Update</button>
            <button class="delete-btn" data-manga-id="${item.manga_id}">Remove</button>
            </div>
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

async function saveRating(mangaId, inputEl) {
  const rating = inputEl.value === "" ? null : Number(inputEl.value);
  const row = inputEl ? inputEl.closest(".list-item") : null;
  const flagEl = row ? row.querySelector(`.rating-recommended[data-manga-id="${mangaId}"]`) : null;
  const recommendedByUs = flagEl ? flagEl.checked : false;
  await api("/api/ratings", {
    method: "POST",
    body: JSON.stringify({ manga_id: mangaId, rating, recommended_by_us: recommendedByUs }),
  });
  inputEl.value = "";
  await loadRatings();
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

ratingsSort.addEventListener("change", () => {
  state.sort = ratingsSort.value;
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
  if (event.target.classList.contains("update-btn")) {
    const mangaId = event.target.dataset.mangaId;
    const row = event.target.closest(".list-item");
    const inputEl = row ? row.querySelector(".rating-update") : null;
    if (!inputEl) return;
    saveRating(mangaId, inputEl);
  }
});

if (searchResults) {
  searchResults.addEventListener("click", (event) => {
    if (!event.target.classList.contains("add-rating-btn")) return;
    const mangaId = event.target.dataset.mangaId;
    const inputEl = searchResults.querySelector(`.rating-new[data-manga-id="${mangaId}"]`);
    const flagEl = searchResults.querySelector(`.rating-recommended[data-manga-id="${mangaId}"]`);
    const rating = inputEl && inputEl.value !== "" ? Number(inputEl.value) : null;
    const recommendedByUs = flagEl ? flagEl.checked : false;
    api("/api/ratings", {
      method: "POST",
      body: JSON.stringify({ manga_id: mangaId, rating, recommended_by_us: recommendedByUs }),
    })
      .then(() => {
        setSearchStatus(`Added rating for ${mangaId}.`);
        if (inputEl) inputEl.value = "";
        loadRatings();
      })
      .catch((e) => setSearchStatus(e.message, true));
  });
}

setLoading(false);
loadRatings();
