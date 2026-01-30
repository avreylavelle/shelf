const readingList = document.getElementById("reading-list");
const readingSort = document.getElementById("reading-sort");
const readingFilter = document.getElementById("reading-filter");
const readingStatusFilter = document.getElementById("reading-status-filter");
const typesButtons = Array.from(document.querySelectorAll(".reading-types-open"));
const typesModal = document.getElementById("reading-types-modal");
const typesSave = document.getElementById("reading-types-save");
const typesCancel = document.getElementById("reading-types-cancel");
const typesAll = document.getElementById("reading-types-all");
const typesNone = document.getElementById("reading-types-none");
const typeOptions = Array.from(document.querySelectorAll("#reading-types-modal .type-option"));

const rateModal = document.getElementById("rate-modal");
const rateModalTitle = document.getElementById("rate-modal-title");
const rateModalInput = document.getElementById("rate-modal-input");
const rateModalFlag = document.getElementById("rate-modal-flag");
const rateModalFinished = document.getElementById("rate-modal-finished");
const rateModalAdd = document.getElementById("rate-modal-add");
const rateModalClose = document.getElementById("rate-modal-close");

const LEGACY_DEFAULT_TYPES = new Set(["Manga", "Manhwa", "Manhua"]);

function openRateModal(mangaId, displayTitle) {
  if (!rateModal) return;
  rateModal.dataset.id = mangaId;
  rateModal.dataset.title = mangaId;
  rateModal.dataset.display = displayTitle || mangaId;
  rateModalTitle.textContent = displayTitle || mangaId;
  rateModalInput.value = "";
  rateModalFlag.checked = false;
  if (rateModalFinished) rateModalFinished.checked = false;
  rateModal.showModal();
}

function closeRateModal() {
  if (!rateModal) return;
  rateModal.close();
}



async function loadUiPrefs() {
  try {
    const data = await api("/api/ui-prefs");
    const prefs = data.prefs || {};
    if (prefs.reading_sort && readingSort) {
      readingSort.value = prefs.reading_sort;
    }
    if (typeOptions.length) {
      if (prefs.reading_types !== undefined) {
        const raw = prefs.reading_types;
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

const state = {
  items: [],
};

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

function normalizeStatus(status) {
  return status || "Plan to Read";
}

function filterReadingItems(items) {
  const query = (readingFilter && readingFilter.value.trim().toLowerCase()) || "";
  const statusFilter = (readingStatusFilter && readingStatusFilter.value) || "";
  const typeSet = selectedTypeSet();
  return items.filter((item) => {
    const title = (item.display_title || item.manga_id || "").toLowerCase();
    const status = normalizeStatus(item.status);
    if (query && !title.includes(query)) return false;
    if (statusFilter && status !== statusFilter) return false;
    if (typeSet && item.item_type && !typeSet.has(item.item_type)) return false;
    return true;
  });
}

function renderReadingList(items) {
  if (!readingList) return;
  if (!items.length) {
    readingList.innerHTML = "<p class='muted'>No reading list titles yet.</p>";
    return;
  }
  readingList.innerHTML = items
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
          <div class="muted">Status</div>
          <select class="reading-status" data-id="${mangaId}">
            <option value="Plan to Read" ${normalizeStatus(item.status) === "Plan to Read" ? "selected" : ""}>Plan to Read</option>
            <option value="In Progress" ${normalizeStatus(item.status) === "In Progress" ? "selected" : ""}>In Progress</option>
          </select>
          <div class="result-actions">
            <button class="details-btn" data-id="${mangaId}" type="button">Details</button>
            <button class="reading-rate" data-id="${mangaId}" data-display="${title}" type="button">Rate</button>
            <button class="reading-remove" data-id="${mangaId}" type="button">Remove</button>
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

async function loadReadingList() {
  const sort = readingSort ? readingSort.value : "chron";
  const data = await api(`/api/reading-list?sort=${encodeURIComponent(sort)}`);
  state.items = data.items || [];
  renderReadingList(filterReadingItems(state.items));
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
    saveUiPref("reading_types", selectedTypes());
    typesModal.close();
    renderReadingList(filterReadingItems(state.items));
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


if (readingFilter) {
  readingFilter.addEventListener("input", () => {
    renderReadingList(filterReadingItems(state.items));
  });
}
if (readingStatusFilter) {
  readingStatusFilter.addEventListener("change", () => {
    renderReadingList(filterReadingItems(state.items));
  });
}

if (readingSort) {
  readingSort.addEventListener("change", () => {
    saveUiPref("reading_sort", readingSort.value);
    loadReadingList().catch((e) => showToast(e.message));
  });
}

if (readingList) {
  readingList.addEventListener("change", (event) => {
    if (!event.target.classList.contains("reading-status")) return;
    const mangaId = event.target.dataset.id;
    const status = event.target.value;
    api("/api/reading-list", {
      method: "PUT",
      body: JSON.stringify({ manga_id: mangaId, status }),
    }).catch((e) => showToast(e.message));
  });
}

if (readingList) {
  readingList.addEventListener("click", (event) => {
    if (event.target.classList.contains("details-btn")) {
      const mangaId = event.target.dataset.id;
      const title = event.target.closest(".result-card")?.querySelector("strong")?.textContent || mangaId;
      handleDetails(mangaId, title).catch(() => {});
      return;
    }
    if (event.target.classList.contains("reading-remove")) {
      const mangaId = event.target.dataset.id;
      api(`/api/reading-list/${encodeURIComponent(mangaId)}`, { method: "DELETE" })
        .then(loadReadingList)
        .catch((e) => showToast(e.message));
    }
    if (event.target.classList.contains("reading-rate")) {
      const mangaId = event.target.dataset.id;
      const display = event.target.dataset.display || mangaId;
      openRateModal(mangaId, display);
    }
  });
}


if (rateModalAdd) {
  rateModalAdd.addEventListener("click", () => {
    const mangaId = rateModal.dataset.id || rateModal.dataset.title;
    const display = rateModal.dataset.display || mangaId;
    const value = rateModalInput.value;
    const rating = value === "" ? null : Number(value);
    const recommendedByUs = rateModalFlag.checked;
    const finishedReading = rateModalFinished ? rateModalFinished.checked : false;
    api("/api/ratings", {
      method: "POST",
      body: JSON.stringify({ manga_id: mangaId, rating, recommended_by_us: recommendedByUs, finished_reading: finishedReading }),
    })
      .then(() => {
        showToast(`${display} added to ratings with rating ${value === "" ? "n/a" : rating}`);
        setTimeout(() => window.location.reload(), 600);
      })
      .then(closeRateModal)
      .catch((err) => showToast(err.message));
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
loadUiPrefs().then(() => loadReadingList().catch((e) => showToast(e.message)));
