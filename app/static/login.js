const usernameEl = document.getElementById("username");
const passwordEl = document.getElementById("password");
const loginBtn = document.getElementById("login-btn");
const registerBtn = document.getElementById("register-btn");
const statusEl = document.getElementById("auth-status");

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.className = isError ? "status error" : "status";
}

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

async function register() {
  const username = usernameEl.value.trim();
  const password = passwordEl.value;
  const data = await api("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  setStatus(`Registered ${data.user.username}`);
  window.location.href = `${BASE_PATH}/dashboard`;
}

loginBtn.addEventListener("click", () => login().catch((e) => setStatus(e.message, true)));
registerBtn.addEventListener("click", () => register().catch((e) => setStatus(e.message, true)));
