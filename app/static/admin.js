// Client-side behavior for admin.js.

const switchUsername = document.getElementById("switch-username");
const switchBtn = document.getElementById("switch-user");
const adminStatus = document.getElementById("admin-status");
const importCsv = document.getElementById("import-csv");
const importBtn = document.getElementById("import-btn");
const importStatus = document.getElementById("import-status");

// Set Status and keep the UI in sync.
function setStatus(el, text, isError = false) {
  el.textContent = text;
  el.className = isError ? "status error" : "status";
}

// Switchuser helper for this page.
async function switchUser() {
  const username = switchUsername.value.trim();
  if (!username) return;
  const data = await api("/api/admin/switch-user", {
    method: "POST",
    body: JSON.stringify({ username }),
  });
  setStatus(adminStatus, `Switched to ${data.user}`);
  loadNavUser();
}

// Importratings helper for this page.
async function importRatings() {
  const csv = importCsv.value.trim();
  if (!csv) return;
  const data = await api("/api/admin/ratings/import", {
    method: "POST",
    body: JSON.stringify({ csv }),
  });
  setStatus(importStatus, `Imported ${data.count} ratings.`);
}

switchBtn.addEventListener("click", () => switchUser().catch((e) => setStatus(adminStatus, e.message, true)));
importBtn.addEventListener("click", () => importRatings().catch((e) => setStatus(importStatus, e.message, true)));
