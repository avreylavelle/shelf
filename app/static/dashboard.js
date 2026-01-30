const summaryEl = document.getElementById("summary");

async function loadSummary() {
  try {
    const [profileData, ratingsData, dnrData, readingData] = await Promise.all([
      api("/api/profile"),
      api("/api/ratings"),
      api("/api/dnr"),
      api("/api/reading-list"),
    ]);
    const profile = profileData.profile || {};
    const count = ratingsData.items ? ratingsData.items.length : 0;
    const dnrCount = dnrData.items ? dnrData.items.length : 0;
    const readingCount = readingData.items ? readingData.items.length : 0;
    summaryEl.textContent = `${profile.username || "User"} · Ratings: ${count} · Reading List: ${readingCount} · DNR: ${dnrCount}`;
  } catch (err) {
    summaryEl.textContent = "Unable to load summary.";
  }
}

loadSummary();
