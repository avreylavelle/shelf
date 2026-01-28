const BASE_PATH = window.BASE_PATH || ""; // injected by templates

function withBase(path) {
  if (!path.startsWith("/")) return `${BASE_PATH}/${path}`;
  return `${BASE_PATH}${path}`;
}

async function api(path, options = {}) {
  const url = withBase(path);
  const res = await fetch(url, {
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


let toastTimer;
function showToast(message, timeout = 2200) {
  if (!message) return;
  let el = document.getElementById("toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "toast";
    el.className = "toast";
    document.body.appendChild(el);
  }
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    el.classList.remove("show");
  }, timeout);
}

async function loadNavUser() {
  const el = document.getElementById("nav-user");
  if (!el) return;
  try {
    const data = await api("/api/session");
    if (data.logged_in && data.user) {
      el.textContent = data.user;
      el.classList.add("show");
    } else {
      el.textContent = "";
      el.classList.remove("show");
    }
  } catch (err) {
    el.textContent = "";
  }
}

loadNavUser();
