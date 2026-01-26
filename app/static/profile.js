const profileUsername = document.getElementById("profile-username");
const profileAge = document.getElementById("profile-age");
const profileGender = document.getElementById("profile-gender");
const profileLanguage = document.getElementById("profile-language");
const saveProfileBtn = document.getElementById("save-profile");
const clearHistoryBtn = document.getElementById("clear-history");
const currentPassword = document.getElementById("current-password");
const newPassword = document.getElementById("new-password");
const changePasswordBtn = document.getElementById("change-password");
const deleteAccountBtn = document.getElementById("delete-account");
const statusEl = document.getElementById("profile-status");
const historyGenresEl = document.getElementById("history-genres");
const historyThemesEl = document.getElementById("history-themes");

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.className = isError ? "status error" : "status";
}

function renderHistory(container, items) {
  const entries = Object.entries(items || {});
  if (!entries.length) {
    container.innerHTML = "<span class='muted'>None yet</span>";
    return;
  }
  const chips = entries
    .sort((a, b) => b[1] - a[1])
    .map(([name, count]) => `<span class="chip">${name} (${count})</span>`);
  container.innerHTML = chips.join("");
}

async function loadProfile() {
  const data = await api("/api/profile");
  const profile = data.profile || {};
  profileUsername.value = profile.username || "";
  profileAge.value = profile.age ?? "";
  profileGender.value = profile.gender || "";
  if (profileLanguage) profileLanguage.value = profile.language || "English";
  renderHistory(historyGenresEl, profile.preferred_genres);
  renderHistory(historyThemesEl, profile.preferred_themes);
}

async function saveProfile() {
  const payload = {
    username: profileUsername.value.trim(),
    age: profileAge.value,
    gender: profileGender.value.trim(),
    language: profileLanguage ? profileLanguage.value : "English",
  };
  await api("/api/profile", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  setStatus("Profile saved.");
  loadNavUser();
  await loadProfile();
}

async function clearHistory() {
  // Wipes preferred_genres/preferred_themes
  await api("/api/profile/clear-history", { method: "POST" });
  setStatus("History cleared.");
  await loadProfile();
}


async function deleteAccount() {
  const ok = window.confirm(
    "This will delete your account profile. Your ratings will stay in the database. Continue?"
  );
  if (!ok) return;
  await api("/api/auth/delete-account", { method: "POST" });
  setStatus("Account deleted. Redirecting...");
  window.location.href = `${BASE_PATH}/login`;
}

async function changePassword() {
  await api("/api/auth/change-password", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPassword.value,
      new_password: newPassword.value,
    }),
  });
  currentPassword.value = "";
  newPassword.value = "";
  setStatus("Password changed.");
}

saveProfileBtn.addEventListener("click", () => saveProfile().catch((e) => setStatus(e.message, true)));
clearHistoryBtn.addEventListener("click", () => clearHistory().catch((e) => setStatus(e.message, true)));
changePasswordBtn.addEventListener("click", () => changePassword().catch((e) => setStatus(e.message, true)));
if (deleteAccountBtn) {
  deleteAccountBtn.addEventListener("click", () => deleteAccount().catch((e) => setStatus(e.message, true)));
}

loadProfile().catch((e) => setStatus(e.message, true));
