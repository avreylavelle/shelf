const ratingsEl = document.getElementById("ratings");
const ratingsSort = document.getElementById("ratings-sort");
const toggleRatings = document.getElementById("toggle-ratings");
const loadingEl = document.getElementById("ratings-loading");

const state = {
  expanded: false,
  sort: "chron",
  items: [],
};

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
            <strong>${item.manga_id}</strong>
            <span class="muted">Rating: ${item.rating ?? "n/a"}</span>
          </div>
          <div class="row">
            <input type="number" min="0" max="10" step="0.1" placeholder="update" data-manga-id="${item.manga_id}" class="rating-update" />
            <button class="update-btn" data-manga-id="${item.manga_id}">Update</button>
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

async function saveRating(mangaId, inputEl) {
  const rating = inputEl.value === "" ? null : Number(inputEl.value);
  await api("/api/ratings", {
    method: "POST",
    body: JSON.stringify({ manga_id: mangaId, rating }),
  });
  inputEl.value = "";
  await loadRatings();
}

async function deleteRating(mangaId) {
  await api(`/api/ratings/${encodeURIComponent(mangaId)}`, { method: "DELETE" });
  await loadRatings();
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
    const inputEl = event.target.parentElement.querySelector(".rating-update");
    saveRating(mangaId, inputEl);
  }
});

setLoading(false);
loadRatings();
