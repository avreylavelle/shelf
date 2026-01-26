const state = {
  loggedIn: false,
  user: null,
  ratingsExpanded: false,
  ratingsSort: "chron",
  ratingsCache: [],
};

const els = {
  username: document.getElementById("username"),
  password: document.getElementById("password"),
  loginBtn: document.getElementById("login-btn"),
  registerBtn: document.getElementById("register-btn"),
  logoutBtn: document.getElementById("logout-btn"),
  authStatus: document.getElementById("auth-status"),
  search: document.getElementById("search"),
  searchBtn: document.getElementById("search-btn"),
  searchResults: document.getElementById("search-results"),
  ratings: document.getElementById("ratings"),
  ratingsSort: document.getElementById("ratings-sort"),
  toggleRatings: document.getElementById("toggle-ratings"),
  recommendations: document.getElementById("recommendations"),
  recommendBtn: document.getElementById("recommend-btn"),
  prefGenres: document.getElementById("pref-genres"),
  prefThemes: document.getElementById("pref-themes"),
  profileUsername: document.getElementById("profile-username"),
  profileAge: document.getElementById("profile-age"),
  profileGender: document.getElementById("profile-gender"),
  saveProfile: document.getElementById("save-profile"),
  clearHistory: document.getElementById("clear-history"),
  currentPassword: document.getElementById("current-password"),
  newPassword: document.getElementById("new-password"),
  changePassword: document.getElementById("change-password"),
  profileStatus: document.getElementById("profile-status"),
};

function setStatus(text, isError = false) {
  els.authStatus.textContent = text;
  els.authStatus.className = isError ? "status error" : "status";
}

function setProfileStatus(text, isError = false) {
  els.profileStatus.textContent = text;
  els.profileStatus.className = isError ? "status error" : "status";
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const message = data.error || "Request failed";
    throw new Error(message);
  }
  return data;
}

async function refreshSession() {
  const data = await api("/api/session");
  state.loggedIn = data.logged_in;
  state.user = data.user;
  els.logoutBtn.style.display = state.loggedIn ? "inline-block" : "none";
  setStatus(state.loggedIn ? `Logged in as ${state.user}` : "Not logged in");
  if (state.loggedIn) {
    await Promise.all([loadProfile(), loadRatings(), loadRecommendations()]);
  } else {
    els.ratings.innerHTML = "<p class='muted'>Log in to see your ratings.</p>";
    els.recommendations.innerHTML = "<p class='muted'>Log in to see recommendations.</p>";
  }
}

async function login() {
  const username = els.username.value.trim();
  const password = els.password.value;
  const data = await api("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  setStatus(`Logged in as ${data.user.username}`);
  await refreshSession();
}

async function register() {
  const username = els.username.value.trim();
  const password = els.password.value;
  const data = await api("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  setStatus(`Registered ${data.user.username}`);
  await refreshSession();
}

async function logout() {
  await api("/api/auth/logout", { method: "POST" });
  setStatus("Logged out");
  await refreshSession();
}

async function loadProfile() {
  const data = await api("/api/profile");
  const profile = data.profile || {};
  els.profileUsername.value = profile.username || "";
  els.profileAge.value = profile.age ?? "";
  els.profileGender.value = profile.gender || "";
}

async function saveProfile() {
  const payload = {
    username: els.profileUsername.value.trim(),
    age: els.profileAge.value,
    gender: els.profileGender.value.trim(),
  };
  const data = await api("/api/profile", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  setProfileStatus("Profile saved.");
  if (data.profile?.username) {
    setStatus(`Logged in as ${data.profile.username}`);
  }
}

async function clearHistory() {
  await api("/api/profile/clear-history", { method: "POST" });
  setProfileStatus("History cleared.");
}

async function changePassword() {
  const current_password = els.currentPassword.value;
  const new_password = els.newPassword.value;
  await api("/api/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ current_password, new_password }),
  });
  els.currentPassword.value = "";
  els.newPassword.value = "";
  setProfileStatus("Password changed.");
}

async function searchManga() {
  const query = els.search.value.trim();
  if (!query) {
    els.searchResults.innerHTML = "<p class='muted'>Enter a title to search.</p>";
    return;
  }
  const data = await api(`/api/manga/search?q=${encodeURIComponent(query)}`);
  els.searchResults.innerHTML = data.items
    .map(
      (item) => `
        <div class="list-item">
          <div>
            <strong>${item.title}</strong>
            <span class="muted">Score: ${item.score ?? "n/a"}</span>
          </div>
          <div class="row">
            <input type="number" min="0" max="10" step="0.1" placeholder="rating" data-manga-id="${item.title}" class="rating-input" />
            <button class="rate-btn" data-manga-id="${item.title}">Save</button>
          </div>
        </div>
      `
    )
    .join("");
}

function renderRatings() {
  const limit = state.ratingsExpanded ? state.ratingsCache.length : 10;
  const items = state.ratingsCache.slice(0, limit);

  if (!items.length) {
    els.ratings.innerHTML = "<p class='muted'>No ratings yet.</p>";
    return;
  }

  els.ratings.innerHTML = items
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

  els.toggleRatings.textContent = state.ratingsExpanded ? "Show Less" : "Show All";
}

async function loadRatings() {
  const data = await api(`/api/ratings?sort=${encodeURIComponent(state.ratingsSort)}`);
  state.ratingsCache = data.items || [];
  renderRatings();
}

async function loadRecommendations() {
  const data = await api("/api/recommendations");
  renderRecommendations(data.items || []);
}

function renderRecommendations(items) {
  if (!items.length) {
    els.recommendations.innerHTML = "<p class='muted'>No recommendations yet.</p>";
    return;
  }
  els.recommendations.innerHTML = items
    .map(
      (item) => `
        <div class="list-item">
          <div>
            <strong>${item.title}</strong>
            <div class="muted">Score: ${item.score ?? "n/a"}</div>
            <div class="muted">Match: ${item.match_score?.toFixed?.(3) ?? "n/a"} | Combined: ${item.combined_score?.toFixed?.(3) ?? "n/a"}</div>
          </div>
          <button class="details-btn" data-title="${item.title}">Details</button>
          <div class="details" data-details="${item.title}"></div>
        </div>
      `
    )
    .join("");
}

async function fetchRecommendationsWithPrefs() {
  const genres = els.prefGenres.value.trim();
  const themes = els.prefThemes.value.trim();
  const data = await api("/api/recommendations", {
    method: "POST",
    body: JSON.stringify({ genres, themes }),
  });
  renderRecommendations(data.items || []);
}

async function handleRatingSave(mangaId, inputEl) {
  const rating = inputEl.value === "" ? null : Number(inputEl.value);
  await api("/api/ratings", {
    method: "POST",
    body: JSON.stringify({ manga_id: mangaId, rating }),
  });
  inputEl.value = "";
  await loadRatings();
  await loadRecommendations();
}

async function handleRatingDelete(mangaId) {
  await api(`/api/ratings/${encodeURIComponent(mangaId)}`, { method: "DELETE" });
  await loadRatings();
  await loadRecommendations();
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

els.loginBtn.addEventListener("click", () => login().catch((e) => setStatus(e.message, true)));
els.registerBtn.addEventListener("click", () => register().catch((e) => setStatus(e.message, true)));
els.logoutBtn.addEventListener("click", () => logout().catch((e) => setStatus(e.message, true)));
els.searchBtn.addEventListener("click", () => searchManga().catch((e) => setStatus(e.message, true)));
els.saveProfile.addEventListener("click", () => saveProfile().catch((e) => setProfileStatus(e.message, true)));
els.clearHistory.addEventListener("click", () => clearHistory().catch((e) => setProfileStatus(e.message, true)));
els.changePassword.addEventListener("click", () => changePassword().catch((e) => setProfileStatus(e.message, true)));
els.recommendBtn.addEventListener("click", () => fetchRecommendationsWithPrefs().catch((e) => setStatus(e.message, true)));

els.ratingsSort.addEventListener("change", () => {
  state.ratingsSort = els.ratingsSort.value;
  loadRatings().catch((e) => setStatus(e.message, true));
});

els.toggleRatings.addEventListener("click", () => {
  state.ratingsExpanded = !state.ratingsExpanded;
  renderRatings();
});

els.searchResults.addEventListener("click", (event) => {
  if (!event.target.classList.contains("rate-btn")) return;
  const mangaId = event.target.dataset.mangaId;
  const inputEl = event.target.parentElement.querySelector(".rating-input");
  handleRatingSave(mangaId, inputEl).catch((e) => setStatus(e.message, true));
});

els.ratings.addEventListener("click", (event) => {
  if (event.target.classList.contains("delete-btn")) {
    const mangaId = event.target.dataset.mangaId;
    handleRatingDelete(mangaId).catch((e) => setStatus(e.message, true));
  }
  if (event.target.classList.contains("update-btn")) {
    const mangaId = event.target.dataset.mangaId;
    const inputEl = event.target.parentElement.querySelector(".rating-update");
    handleRatingSave(mangaId, inputEl).catch((e) => setStatus(e.message, true));
  }
});

els.recommendations.addEventListener("click", (event) => {
  if (!event.target.classList.contains("details-btn")) return;
  const title = event.target.dataset.title;
  const targetEl = event.target.parentElement.querySelector(".details");
  if (targetEl.innerHTML) {
    targetEl.innerHTML = "";
    return;
  }
  handleDetails(title, targetEl).catch((e) => setStatus(e.message, true));
});

refreshSession().catch((e) => setStatus(e.message, true));
