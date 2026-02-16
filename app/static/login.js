// Client-side behavior for login.js.

const usernameEl = document.getElementById("username");
const passwordEl = document.getElementById("password");
const loginBtn = document.getElementById("login-btn");
const registerBtn = document.getElementById("register-btn");
const statusEl = document.getElementById("auth-status");

// Set Status and keep the UI in sync.
function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.className = isError ? "status error" : "status";
}


// Handle Enter events.
function handleEnter(event) {
  if (event.key !== "Enter") return;
  event.preventDefault();
  login().catch((e) => setStatus(e.message, true));
}
// Login helper for this page.
async function login() {
  const username = usernameEl.value.trim();
  const password = passwordEl.value;
  const data = await api("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  setStatus(`Logged in as ${data.user.username}`);
  window.location.href = `${BASE_PATH}/dashboard`;
}

// Register helper for this page.
async function register() {
  const username = usernameEl.value.trim();
  const password = passwordEl.value;
  const data = await api("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  setStatus(`Registered ${data.user.username}. Please log in.`);
  passwordEl.value = "";
}

loginBtn.addEventListener("click", () => login().catch((e) => setStatus(e.message, true)));
registerBtn.addEventListener("click", () => register().catch((e) => setStatus(e.message, true)));

usernameEl.addEventListener("keydown", handleEnter);
passwordEl.addEventListener("keydown", handleEnter);
