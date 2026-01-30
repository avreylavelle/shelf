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

const LEGACY_DEFAULT_TYPES = new Set(["Manga", "Manhwa", "Manhua"]);

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
        applyLegacyDefaultTypes(desired);
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

const state = { items: [] };

function selectedTypes() {
  return typeOptions.filter((opt) => opt.checked).map((opt) => opt.value);
}

function setDefaultTypes() {
  if (!typeOptions.length) return;
  typeOptions.forEach((opt) => {
    opt.checked = true;
  });
}

function applyLegacyDefaultTypes(desired) {
  if (!desired || !typeOptions.length) return false;
  if (desired.size !== LEGACY_DEFAULT_TYPES.size) return false;
  for (const value of LEGACY_DEFAULT_TYPES) {
    if (!desired.has(value)) return false;
  }
  typeOptions.forEach((opt) => {
    opt.checked = true;
  });
  return true;
}

function selectedTypeSet() {
  const selected = selectedTypes();
  return selected.length ? new Set(selected) : null;
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
        const title = item.display_title || item.manga_id;
        const cover = item.cover_url
          ? `<img class="result-cover" src="${item.cover_url}" alt="Cover" loading="lazy" referrerpolicy="no-referrer">`
          : `<div class="result-cover placeholder"></div>`;
        return `
        <div class="result-card" data-id="${mangaId}" data-display="${title}">
          <strong>${title}</strong>
          ${cover}
          <div class="muted">Added: ${item.created_at}</div>
          <div class="result-actions">
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
    loadDnr().catch((e) => showToast(e.message));
  });
}

if (dnrList) {
  dnrList.addEventListener("click", (event) => {
    if (event.target.classList.contains("details-btn")) {
      const mangaId = event.target.dataset.id;
      const title = event.target.closest(".result-card")?.querySelector("strong")?.textContent || mangaId;
      handleDetails(mangaId, title).catch(() => {});
      return;
    }
    if (!event.target.classList.contains("dnr-remove")) return;
    const mangaId = event.target.dataset.id;
    api(`/api/dnr/${encodeURIComponent(mangaId)}`, { method: "DELETE" })
      .then(loadDnr)
      .catch((e) => showToast(e.message));
  });
}

loadUiPrefs().then(() => loadDnr().catch((e) => showToast(e.message)));
