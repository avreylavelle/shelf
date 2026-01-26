const recommendationsEl = document.getElementById("recommendations");
const recommendBtn = document.getElementById("recommend-btn");
const genreSelect = document.getElementById("genre-select");
const themeSelect = document.getElementById("theme-select");
const addGenreBtn = document.getElementById("add-genre");
const addThemeBtn = document.getElementById("add-theme");
const selectedGenresEl = document.getElementById("selected-genres");
const selectedThemesEl = document.getElementById("selected-themes");
const loadingEl = document.getElementById("recs-loading");

// Keep a tiny local state, nothing fancy
const state = {
  genres: [],
  themes: [],
  ratingsMap: {},
};


const rateModal = document.getElementById("rate-modal");
const rateModalTitle = document.getElementById("rate-modal-title");
const rateModalInput = document.getElementById("rate-modal-input");
const rateModalFlag = document.getElementById("rate-modal-flag");
const rateModalAdd = document.getElementById("rate-modal-add");
const rateModalClose = document.getElementById("rate-modal-close");

function openRateModal(title, displayTitle) {
  if (!rateModal) return;
  rateModal.dataset.title = title;
  rateModalTitle.textContent = displayTitle || title;
  const currentRating = state.ratingsMap[title];
  rateModalInput.value = currentRating ?? "";
  rateModalFlag.checked = true;
  rateModal.showModal();
}

function closeRateModal() {
  if (!rateModal) return;
  rateModal.close();
}

function setLoading(isLoading) {
  loadingEl.setAttribute("aria-busy", String(isLoading));
  loadingEl.style.display = isLoading ? "inline-flex" : "none";
}

function renderRecommendations(items) {
  if (!items.length) {
    recommendationsEl.innerHTML = "<p class='muted'>No recommendations yet.</p>";
    return;
  }

  recommendationsEl.innerHTML = items
    .map((item) => {
      const currentRating = state.ratingsMap[item.title];
      const ratingText = currentRating == null ? "Not rated" : `Your rating: ${currentRating}`;
      const displayTitle = item.display_title || item.title;
      return `
        <div class="list-item">
          <div class="rec-main">
            <strong>${displayTitle}</strong>
            <div class="muted">Score: ${item.score ?? "n/a"}</div>
            <div class="muted">Match: ${item.match_score?.toFixed?.(3) ?? "n/a"} | Combined: ${item.combined_score?.toFixed?.(3) ?? "n/a"}</div>
            <div class="muted">${ratingText}</div>
          </div>
          <div class="rec-actions">
            <button class="details-btn" data-title="${item.title}" type="button">Details</button>
            <button class="rate-open" data-title="${item.title}" data-display="${displayTitle}" type="button">Rate →</button>
            <div class="details" data-details="${item.title}"></div>
          </div>
        </div>
      `;
    })
    .join("");
}

function renderChips(container, items, type) {
  container.innerHTML = items
    .map(
      (item) => `
        <button class="chip" data-type="${type}" data-value="${item}" type="button">
          ${item} <span aria-hidden="true">×</span>
        </button>
      `
    )
    .join("");
}

function addGenre() {
  const value = genreSelect.value;
  if (!value || state.genres.includes(value)) return;
  if (state.genres.length >= 3) return; // hard cap like the CLI
  state.genres.push(value);
  renderChips(selectedGenresEl, state.genres, "genre");
}

function addTheme() {
  const value = themeSelect.value;
  if (!value || state.themes.includes(value)) return;
  if (state.themes.length >= 2) return; // hard cap like the CLI
  state.themes.push(value);
  renderChips(selectedThemesEl, state.themes, "theme");
}

async function loadRatingsMap() {
  const data = await api("/api/ratings/map");
  state.ratingsMap = data.items || {};
}

async function fetchRecommendationsWithPrefs() {
  // ONLY fetch on button click (no auto-recs on load)
  setLoading(true);
  try {
    const data = await api("/api/recommendations", {
      method: "POST",
      body: JSON.stringify({
        genres: state.genres,
        themes: state.themes,
      }),
    });
    await loadRatingsMap();
    renderRecommendations(data.items || []);
  } catch (err) {
    recommendationsEl.innerHTML = `<p class='muted'>${err.message}</p>`;
  } finally {
    setLoading(false);
  }
}

async function handleDetails(title, targetEl) {
  const data = await api(`/api/manga/details?title=${encodeURIComponent(title)}`);
  const item = data.item || {};
  targetEl.innerHTML = `
    <div class="details-box">
      <div><strong>Type:</strong> ${item.item_type ?? "n/a"}</div>
      <div><strong>Volumes:</strong> ${item.volumes ?? "n/a"}</div>
      <div><strong>Chapters:</strong> ${item.chapters ?? "n/a"}</div>
      <div><strong>Status:</strong> ${item.status ?? "n/a"}</div>
      <div><strong>Publishing:</strong> ${item.publishing_date ?? "n/a"}</div>
      <div><strong>Authors:</strong> ${item.authors ?? "n/a"}</div>
      <div><strong>Demographic:</strong> ${item.demographic ?? "n/a"}</div>
      <div><strong>Genres:</strong> ${item.genres ?? "n/a"}</div>
      <div><strong>Themes:</strong> ${item.themes ?? "n/a"}</div>
    </div>
  `;
}

addGenreBtn.addEventListener("click", (event) => {
  event.preventDefault();
  addGenre();
});
addThemeBtn.addEventListener("click", (event) => {
  event.preventDefault();
  addTheme();
});
recommendBtn.addEventListener("click", (event) => {
  event.preventDefault();
  fetchRecommendationsWithPrefs();
});

selectedGenresEl.addEventListener("click", (event) => {
  const target = event.target.closest(".chip");
  if (!target) return;
  const value = target.dataset.value;
  state.genres = state.genres.filter((item) => item !== value);
  renderChips(selectedGenresEl, state.genres, "genre");
});

selectedThemesEl.addEventListener("click", (event) => {
  const target = event.target.closest(".chip");
  if (!target) return;
  const value = target.dataset.value;
  state.themes = state.themes.filter((item) => item !== value);
  renderChips(selectedThemesEl, state.themes, "theme");
});

if (rateModalAdd) {
  rateModalAdd.addEventListener("click", () => {
    const title = rateModal.dataset.title;
    const value = rateModalInput.value;
    const rating = value === "" ? null : Number(value);
    const recommendedByUs = rateModalFlag.checked;
    api("/api/ratings", {
      method: "POST",
      body: JSON.stringify({ manga_id: title, rating, recommended_by_us: recommendedByUs }),
    })
      .then(() => loadRatingsMap())
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

recommendationsEl.addEventListener("click", (event) => {
  if (event.target.classList.contains("details-btn")) {
    const title = event.target.dataset.title;
    const targetEl = event.target.parentElement.querySelector(".details");
    if (targetEl.innerHTML) {
      targetEl.innerHTML = "";
      return;
    }
    handleDetails(title, targetEl).catch(() => {});
  }

  if (event.target.classList.contains("rate-open")) {
    const title = event.target.dataset.title;
    const displayTitle = event.target.dataset.display;
    openRateModal(title, displayTitle);
  }
});

setLoading(false);
