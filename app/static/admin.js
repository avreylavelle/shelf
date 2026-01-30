const switchUsername = document.getElementById("switch-username");
const switchBtn = document.getElementById("switch-user");
const adminStatus = document.getElementById("admin-status");
const importCsv = document.getElementById("import-csv");
const importBtn = document.getElementById("import-btn");
const importStatus = document.getElementById("import-status");

function setStatus(el, text, isError = false) {
  el.textContent = text;
  el.className = isError ? "status error" : "status";
}

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
