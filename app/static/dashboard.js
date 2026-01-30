const summaryEl = document.getElementById("summary");

async function loadSummary() {
  try {
    const [profileData, ratingsData] = await Promise.all([
      api("/api/profile"),
      api("/api/ratings"),
    ]);
    const profile = profileData.profile || {};
    const count = ratingsData.items ? ratingsData.items.length : 0;
    summaryEl.textContent = `${profile.username || "User"} · Ratings: ${count}`;
  } catch (err) {
    summaryEl.textContent = "Unable to load summary.";
  }
}

loadSummary();
