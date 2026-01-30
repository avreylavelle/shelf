const recommendationsEl = document.getElementById("recommendations");
const recommendBtn = document.getElementById("recommend-btn");
const optionsBtn = document.getElementById("options-btn");
const diversifyToggle = document.getElementById("diversify-toggle");
const noveltyToggle = document.getElementById("novelty-toggle");
const personalizeToggle = document.getElementById("personalize-toggle");
const infoBtn = document.getElementById("info-btn");
const infoModal = document.getElementById("info-modal");
const infoClose = document.getElementById("info-close");
const optionsModal = document.getElementById("options-modal");
const optionsSave = document.getElementById("options-save");
const optionsCancel = document.getElementById("options-cancel");
const minYearInput = document.getElementById("min-year");
const typeOptions = Array.from(document.querySelectorAll(".type-option"));
const typesAll = document.getElementById("types-all");
const typesNone = document.getElementById("types-none");
const genreSelect = document.getElementById("genre-select");
const themeSelect = document.getElementById("theme-select");
const addGenreBtn = document.getElementById("add-genre");
const addThemeBtn = document.getElementById("add-theme");
const selectedGenresEl = document.getElementById("selected-genres");
const selectedThemesEl = document.getElementById("selected-themes");
const blacklistGenreSelect = document.getElementById("blacklist-genre-select");
const blacklistThemeSelect = document.getElementById("blacklist-theme-select");
const addBlacklistGenreBtn = document.getElementById("add-blacklist-genre");
const addBlacklistThemeBtn = document.getElementById("add-blacklist-theme");
const blacklistGenresEl = document.getElementById("blacklist-genres");
const blacklistThemesEl = document.getElementById("blacklist-themes");
const loadingEl = document.getElementById("recs-loading");

// Keep a tiny local state, nothing fancy
const state = {
  genres: [],
  themes: [],
  blacklistGenres: [],
  blacklistThemes: [],
  ratingsMap: {},
};


const rateModal = document.getElementById("rate-modal");
const rateModalTitle = document.getElementById("rate-modal-title");
const rateModalInput = document.getElementById("rate-modal-input");
const rateModalFlag = document.getElementById("rate-modal-flag");
const rateModalFinished = document.getElementById("rate-modal-finished");
const rateModalAdd = document.getElementById("rate-modal-add");
const rateModalReading = document.getElementById("rate-modal-reading");
const rateModalClose = document.getElementById("rate-modal-close");
const addModal = document.getElementById("add-modal");
const addModalTitle = document.getElementById("add-modal-title");
const addRateBtn = document.getElementById("add-rate");
const addReadingBtn = document.getElementById("add-reading");
const addDnrBtn = document.getElementById("add-dnr");
const addCloseBtn = document.getElementById("add-close");

function openRateModal(mangaId, displayTitle) {
  if (!rateModal) return;
  rateModal.dataset.id = mangaId;
  rateModal.dataset.display = displayTitle || mangaId;
  const currentRating = state.ratingsMap[mangaId];
  rateModal.dataset.currentRating = currentRating ?? "";
  rateModalTitle.textContent = displayTitle || mangaId;
  rateModalInput.value = currentRating ?? "";
  rateModalFlag.checked = false;
  if (rateModalFinished) rateModalFinished.checked = false;
  rateModal.showModal();
}

function closeRateModal() {
  if (!rateModal) return;
  rateModal.close();
}

function openAddModal(mangaId, displayTitle) {
  if (!addModal) return;
  addModal.dataset.id = mangaId;
  addModal.dataset.display = displayTitle || mangaId;
  if (addModalTitle) addModalTitle.textContent = displayTitle || "Add";
  addModal.showModal();
}

function closeAddModal() {
  if (!addModal) return;
  addModal.close();
}


async function loadUiPrefs() {
  try {
    const data = await api("/api/ui-prefs");
    const prefs = data.prefs || {};
    if (diversifyToggle && prefs.recs_diversify !== undefined) {
      diversifyToggle.checked = Boolean(prefs.recs_diversify);
    }
    if (noveltyToggle && prefs.recs_novelty !== undefined) {
      noveltyToggle.checked = Boolean(prefs.recs_novelty);
    }
    if (personalizeToggle && prefs.recs_personalize !== undefined) {
      personalizeToggle.checked = Boolean(prefs.recs_personalize);
    }
    if (minYearInput && prefs.recs_min_year) {
      minYearInput.value = prefs.recs_min_year;
    }
    if (typeOptions.length) {
      if (prefs.recs_types !== undefined) {
        const raw = prefs.recs_types;
        const list = Array.isArray(raw) ? raw : String(raw).split(",").map((v) => v.trim()).filter(Boolean);
        const desired = new Set(list.map((val) => String(val)));
        typeOptions.forEach((opt) => {
          opt.checked = desired.has(opt.value);
        });
      } else {
        typeOptions.forEach((opt) => {
          opt.checked = true;
        });
      }
      if (!typeOptions.some((opt) => opt.checked)) {
        typeOptions.forEach((opt) => {
          opt.checked = true;
        });
      }
    }
  } catch (err) {
    if (typeOptions.length) {
      typeOptions.forEach((opt) => {
        opt.checked = true;
      });
    }
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


function cssEscape(value) {
  if (window.CSS && CSS.escape) return CSS.escape(value);
  return String(value).replace(/"/g, '\"');
}

function removeRecommendation(mangaId) {
  const selector = `.result-card[data-id="${cssEscape(mangaId)}"]`;
  const el = recommendationsEl.querySelector(selector);
  if (el) el.remove();
}

function displayForTitle(mangaId) {
  const selector = `.result-card[data-id="${cssEscape(mangaId)}"]`;
  const el = recommendationsEl.querySelector(selector);
  return (el && el.dataset.display) || mangaId;
}

function renderRecommendations(items) {
  if (!items.length) {
    recommendationsEl.innerHTML = "<p class='muted'>No recommendations yet.</p>";
    return;
  }

  recommendationsEl.innerHTML = items
    .map((item) => {
      const mangaId = item.id || item.title;
      const currentRating = state.ratingsMap[mangaId];
      const ratingText = currentRating == null ? "" : `Your rating: ${currentRating}`;
      const displayTitle = item.display_title || item.english_name || item.title;
      const cover = item.cover_url
        ? `<img class="result-cover" src="${item.cover_url}" alt="Cover" loading="lazy" referrerpolicy="no-referrer">`
        : `<div class="result-cover placeholder"></div>`;
      const reasons = (item.reasons || [])
        .map((reason) => `<span class="badge">${reason}</span>`)
        .join("");
      return `
        <div class="result-card" data-id="${mangaId}" data-display="${displayTitle}">
          <strong>${displayTitle}</strong>
          ${cover}
          ${ratingText ? `<div class="muted">${ratingText}</div>` : ""}
          ${reasons ? `<div class="badges">${reasons}</div>` : ""}
          <div class="result-actions">
            <button class="details-btn" data-id="${mangaId}" type="button">Details</button>
            <button class="add-open" data-id="${mangaId}" data-display="${displayTitle}" type="button">Add</button>
          </div>
        </div>
      `;
    })
    .join("");
}

function selectedTypes() {
  return typeOptions.filter((opt) => opt.checked).map((opt) => opt.value);
}


function renderSelectionChips(container, items, type) {
  if (!container) return;
  const safeItems = Array.isArray(items) ? items : [];
  container.innerHTML = safeItems
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
  state.genres.push(value);
  renderSelectionChips(selectedGenresEl, state.genres, "genre");
}

function addTheme() {
  const value = themeSelect.value;
  if (!value || state.themes.includes(value)) return;
  state.themes.push(value);
  renderSelectionChips(selectedThemesEl, state.themes, "theme");
}

function addBlacklistGenre() {
  const value = blacklistGenreSelect ? blacklistGenreSelect.value : "";
  if (!value || state.blacklistGenres.includes(value)) return;
  state.blacklistGenres.push(value);
  renderSelectionChips(blacklistGenresEl, state.blacklistGenres, "blacklist-genre");
}

function addBlacklistTheme() {
  const value = blacklistThemeSelect ? blacklistThemeSelect.value : "";
  if (!value || state.blacklistThemes.includes(value)) return;
  state.blacklistThemes.push(value);
  renderSelectionChips(blacklistThemesEl, state.blacklistThemes, "blacklist-theme");
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
        blacklist_genres: state.blacklistGenres,
        blacklist_themes: state.blacklistThemes,
        diversify: diversifyToggle ? diversifyToggle.checked : true,
        novelty: noveltyToggle ? noveltyToggle.checked : false,
        personalize: personalizeToggle ? personalizeToggle.checked : true,
        min_year: minYearInput ? Number(minYearInput.value) : undefined,
        content_types: selectedTypes(),
      }),
    });
    await loadRatingsMap();
    const items = collapseByMalId(data.items || []);
    renderRecommendations(items);
  } catch (err) {
    recommendationsEl.innerHTML = `<p class='muted'>${err.message}</p>`;
  } finally {
    setLoading(false);
  }
}

async function handleDetails(mangaId, title) {
  api("/api/events", {
    method: "POST",
    body: JSON.stringify({ event_type: "clicked", manga_id: mangaId }),
  }).catch(() => {});
  try {
    const data = await api(`/api/manga/details?id=${encodeURIComponent(mangaId)}`);
    const item = data.item || {};
    if (window.openDetailsModal && window.renderDetailsHTML) {
      window.openDetailsModal(window.renderDetailsHTML(item), title || item.display_title || item.title);
    }
  } catch (err) {
    const message = err?.message || "Details failed";
    showToast(message);
    if (window.openDetailsModal) {
      window.openDetailsModal(`<div class='muted'>${message}</div>`, title || mangaId || "Details");
    }
  }
}

addGenreBtn.addEventListener("click", (event) => {
  event.preventDefault();
  addGenre();
});
addThemeBtn.addEventListener("click", (event) => {
  event.preventDefault();
  addTheme();
});
if (addBlacklistGenreBtn) {
  addBlacklistGenreBtn.addEventListener("click", (event) => {
    event.preventDefault();
    addBlacklistGenre();
  });
}
if (addBlacklistThemeBtn) {
  addBlacklistThemeBtn.addEventListener("click", (event) => {
    event.preventDefault();
    addBlacklistTheme();
  });
}
if (diversifyToggle) {
  diversifyToggle.addEventListener("change", () => {
    saveUiPref("recs_diversify", diversifyToggle.checked);
  });
}
if (noveltyToggle) {
  noveltyToggle.addEventListener("change", () => {
    saveUiPref("recs_novelty", noveltyToggle.checked);
  });
}
if (personalizeToggle) {
  personalizeToggle.addEventListener("change", () => {
    saveUiPref("recs_personalize", personalizeToggle.checked);
  });
}
if (optionsBtn && optionsModal) {
  optionsBtn.addEventListener("click", () => optionsModal.showModal());
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
if (optionsSave && optionsModal) {
  optionsSave.addEventListener("click", () => {
    if (diversifyToggle) saveUiPref("recs_diversify", diversifyToggle.checked);
    if (noveltyToggle) saveUiPref("recs_novelty", noveltyToggle.checked);
    if (personalizeToggle) saveUiPref("recs_personalize", personalizeToggle.checked);
    if (minYearInput) saveUiPref("recs_min_year", Number(minYearInput.value) || 2007);
    if (typeOptions.length) {
      const types = selectedTypes();
      typeOptions.forEach((opt) => {
        opt.checked = types.includes(opt.value);
      });
      saveUiPref("recs_types", types);
    }
    optionsModal.close();
  });
}
if (optionsCancel && optionsModal) {
  optionsCancel.addEventListener("click", () => optionsModal.close());
}
if (optionsModal) {
  optionsModal.addEventListener("click", (event) => {
    const rect = optionsModal.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) {
      optionsModal.close();
    }
  });
}

recommendBtn.addEventListener("click", (event) => {
  event.preventDefault();
  fetchRecommendationsWithPrefs();
});

selectedGenresEl.addEventListener("click", (event) => {
  const target = event.target.closest(".chip");
  if (!target) return;
  const value = target.dataset.value;
  state.genres = state.genres.filter((item) => item !== value);
  renderSelectionChips(selectedGenresEl, state.genres, "genre");
});

selectedThemesEl.addEventListener("click", (event) => {
  const target = event.target.closest(".chip");
  if (!target) return;
  const value = target.dataset.value;
  state.themes = state.themes.filter((item) => item !== value);
  renderSelectionChips(selectedThemesEl, state.themes, "theme");
});
if (blacklistGenresEl) {
  blacklistGenresEl.addEventListener("click", (event) => {
    const target = event.target.closest(".chip");
    if (!target) return;
    const value = target.dataset.value;
    state.blacklistGenres = state.blacklistGenres.filter((item) => item !== value);
    renderSelectionChips(blacklistGenresEl, state.blacklistGenres, "blacklist-genre");
  });
}
if (blacklistThemesEl) {
  blacklistThemesEl.addEventListener("click", (event) => {
    const target = event.target.closest(".chip");
    if (!target) return;
    const value = target.dataset.value;
    state.blacklistThemes = state.blacklistThemes.filter((item) => item !== value);
    renderSelectionChips(blacklistThemesEl, state.blacklistThemes, "blacklist-theme");
  });
}

if (rateModalAdd) {
  rateModalAdd.addEventListener("click", () => {
    const mangaId = rateModal.dataset.id;
    const display = rateModal.dataset.display || mangaId;
    const value = rateModalInput.value;
    const rating = value === "" ? null : Number(value);
    const recommendedByUs = rateModalFlag.checked;
    const finishedReading = rateModalFinished ? rateModalFinished.checked : false;
    const current = rateModal.dataset.currentRating || "";
    const ratingDisplay = value === "" ? (current !== "" ? current : "n/a") : rating;
    api("/api/ratings", {
      method: "POST",
      body: JSON.stringify({ manga_id: mangaId, rating, recommended_by_us: recommendedByUs, finished_reading: finishedReading }),
    })
      .then(() => loadRatingsMap())
      .then(() => {
        showToast(`${display} added to ratings with rating ${ratingDisplay}`);
        removeRecommendation(mangaId);
        closeRateModal();
      })
      .catch((err) => {
        showToast(err.message || "Request failed");
      });
  });
}

if (rateModalReading) {
  rateModalReading.addEventListener("click", () => {
    const mangaId = rateModal.dataset.id;
    api("/api/reading-list", {
      method: "POST",
      body: JSON.stringify({ manga_id: mangaId }),
    })
      .then(() => {
        showToast(`Added ${displayForTitle(mangaId)} to Reading List`);
        removeRecommendation(mangaId);
        closeRateModal();
      })
      .catch((err) => showToast(err.message || "Request failed"));
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

if (addRateBtn) {
  addRateBtn.addEventListener("click", () => {
    const mangaId = addModal.dataset.id;
    const display = addModal.dataset.display || mangaId;
    closeAddModal();
    openRateModal(mangaId, display);
  });
}
if (addReadingBtn) {
  addReadingBtn.addEventListener("click", () => {
    const mangaId = addModal.dataset.id;
    api("/api/reading-list", {
      method: "POST",
      body: JSON.stringify({ manga_id: mangaId }),
    })
      .then(() => {
        showToast(`Added ${displayForTitle(mangaId)} to Reading List`);
        removeRecommendation(mangaId);
        closeAddModal();
      })
      .catch((err) => showToast(err.message || "Request failed"));
  });
}
if (addDnrBtn) {
  addDnrBtn.addEventListener("click", () => {
    const mangaId = addModal.dataset.id;
    api("/api/dnr", {
      method: "POST",
      body: JSON.stringify({ manga_id: mangaId }),
    })
      .then(() => {
        showToast(`Added ${displayForTitle(mangaId)} to DNR`);
        removeRecommendation(mangaId);
        closeAddModal();
      })
      .catch((err) => showToast(err.message || "Request failed"));
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

if (infoBtn && infoModal) {
  infoBtn.addEventListener("click", () => infoModal.showModal());
}
if (infoClose && infoModal) {
  infoClose.addEventListener("click", () => infoModal.close());
}
if (infoModal) {
  infoModal.addEventListener("click", (event) => {
    const rect = infoModal.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) {
      infoModal.close();
    }
  });
}

recommendationsEl.addEventListener("click", (event) => {
  const detailsBtn = event.target.closest(".details-btn");
  if (detailsBtn) {
    const mangaId = detailsBtn.dataset.id;
    const title = detailsBtn.closest(".result-card")?.dataset?.display || mangaId;
    handleDetails(mangaId, title).catch(() => {});
    return;
  }

  const addBtn = event.target.closest(".add-open");
  if (addBtn) {
    const mangaId = addBtn.dataset.id;
    const displayTitle = addBtn.dataset.display;
    openAddModal(mangaId, displayTitle);
  }
});

setLoading(false);
loadUiPrefs().catch(() => {});
