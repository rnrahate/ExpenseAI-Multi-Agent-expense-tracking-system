const API_BASE = "http://localhost:8000";

function switchTab(tab) {
  const loginForm = document.getElementById("loginForm");
  const signupForm = document.getElementById("signupForm");
  const loginTab = document.getElementById("loginTab");
  const signupTab = document.getElementById("signupTab");
  clearMessage();

  if (tab === "login") {
    loginForm.style.display = "block";
    signupForm.style.display = "none";
    loginTab.classList.add("active");
    signupTab.classList.remove("active");
  } else {
    loginForm.style.display = "none";
    signupForm.style.display = "block";
    loginTab.classList.remove("active");
    signupTab.classList.add("active");
  }
}

function showMessage(msg, type = "error") {
  const el = document.getElementById("authMessage");
  el.textContent = msg;
  el.className = `auth-message ${type}`;
  el.style.display = "block";
}

function clearMessage() {
  const el = document.getElementById("authMessage");
  el.style.display = "none";
}

async function handleLogin() {
  const identifier = document.getElementById("loginIdentifier").value.trim();
  const password = document.getElementById("loginPassword").value;

  if (!identifier || !password) {
    showMessage("Please fill all fields");
    return;
  }

  const btn = document.getElementById("loginBtn");
  btn.disabled = true;
  btn.textContent = "Signing in...";
  clearMessage();

  const body = { password };
  if (identifier.includes("@")) {
    body.email = identifier;
  } else {
    body.phone_number = identifier;
  }

  try {
    const res = await fetch(`${API_BASE}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    if (!res.ok) {
      showMessage(data.detail || "Login failed");
      return;
    }

    localStorage.setItem("token", data.access_token);
    localStorage.setItem("userName", data.first_name);
    localStorage.setItem("userEmail", data.email);

    showMessage("Login successful! Redirecting...", "success");
    setTimeout(() => { window.location.href = "dashboard.html"; }, 800);
  } catch (err) {
    showMessage("Cannot reach server. Is the backend running?");
  } finally {
    btn.disabled = false;
    btn.textContent = "Sign In →";
  }
}

async function handleSignup() {
  const firstName = document.getElementById("firstName").value.trim();
  const lastName = document.getElementById("lastName").value.trim();
  const email = document.getElementById("signupEmail").value.trim();
  const phone = document.getElementById("signupPhone").value.trim();
  const password = document.getElementById("signupPassword").value;

  if (!firstName || !lastName || !email || !phone || !password) {
    showMessage("Please fill all fields");
    return;
  }

  if (password.length < 6) {
    showMessage("Password must be at least 6 characters");
    return;
  }

  const btn = document.getElementById("signupBtn");
  btn.disabled = true;
  btn.textContent = "Creating account...";
  clearMessage();

  try {
    const res = await fetch(`${API_BASE}/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        first_name: firstName,
        last_name: lastName,
        email,
        phone_number: phone,
        password,
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      showMessage(data.detail || "Signup failed");
      return;
    }

    showMessage("Account created! Please sign in.", "success");
    setTimeout(() => switchTab("login"), 1500);
  } catch (err) {
    showMessage("Cannot reach server. Is the backend running?");
  } finally {
    btn.disabled = false;
    btn.textContent = "Create Account →";
  }
}

// Redirect if already logged in
if (localStorage.getItem("token")) {
  window.location.href = "dashboard.html";
}

// Enter key support
document.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    const loginForm = document.getElementById("loginForm");
    if (loginForm.style.display !== "none") handleLogin();
    else handleSignup();
  }
});
