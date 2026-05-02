const API_BASE = "http://localhost:8000";
const token = localStorage.getItem("token");
let pieChartInstance = null;
let barChartInstance = null;

// Auth guard
if (!token) window.location.href = "auth.html";

// Init user info
document.getElementById("userName").textContent = localStorage.getItem("userName") || "User";
document.getElementById("userEmail").textContent = localStorage.getItem("userEmail") || "";
const initials = (localStorage.getItem("userName") || "U")[0].toUpperCase();
document.getElementById("userAvatar").textContent = initials;

function logout() {
  localStorage.clear();
  window.location.href = "auth.html";
}

// ============ EXPENSE ROWS ============
let rowCount = 0;

function addExpenseRow(desc = "", amount = "", date = "") {
  rowCount++;
  const id = `row_${rowCount}`;
  const container = document.getElementById("expenseRows");
  const div = document.createElement("div");
  div.className = "expense-row";
  div.id = id;
  div.innerHTML = `
    <div class="form-group" style="margin:0">
      <label>Description</label>
      <input type="text" placeholder="e.g. Grocery shopping" value="${desc}" class="exp-desc" />
    </div>
    <div class="form-group" style="margin:0">
      <label>Amount ($)</label>
      <input type="number" placeholder="0.00" value="${amount}" min="0.01" step="0.01" class="exp-amount" />
    </div>
    <div class="form-group" style="margin:0">
      <label>Date</label>
      <input type="date" value="${date}" class="exp-date" />
    </div>
    <div class="form-group" style="margin:0">
      <label>&nbsp;</label>
      <button class="btn-remove-row" onclick="removeRow('${id}')">✕</button>
    </div>
  `;
  container.appendChild(div);
}

function removeRow(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

// Load sample expenses
const samples = [
  ["Grocery store", "285", getTodayDate()],
  ["Netflix subscription", "15.99", getTodayDate()],
  ["Electricity bill", "120", getTodayDate()],
  ["Restaurant dinner", "85", getTodayDate()],
  ["Uber rides", "45", getTodayDate()],
  ["Online shopping", "230", getTodayDate()],
];

function getTodayDate() {
  return new Date().toISOString().split("T")[0];
}

samples.forEach(([d, a, dt]) => addExpenseRow(d, a, dt));

// ============ ANALYSIS ============
async function runAnalysis() {
  const rows = document.querySelectorAll(".expense-row");
  const expenses = [];

  rows.forEach((row) => {
    const desc = row.querySelector(".exp-desc").value.trim();
    const amount = parseFloat(row.querySelector(".exp-amount").value);
    const date = row.querySelector(".exp-date").value;
    if (desc && amount > 0) {
      expenses.push({ description: desc, amount, date: date || undefined });
    }
  });

  if (expenses.length === 0) {
    alert("Please add at least one expense with a description and amount.");
    return;
  }

  const monthlyLimit = parseFloat(document.getElementById("monthlyLimit").value);
  if (!monthlyLimit || monthlyLimit <= 0) {
    alert("Please enter a valid monthly budget limit.");
    return;
  }

  showLoading(true);
  document.getElementById("analyzeBtn").disabled = true;

  try {
    const res = await fetch(`${API_BASE}/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ expenses, monthly_limit: monthlyLimit }),
    });

    if (res.status === 401) {
      localStorage.clear();
      window.location.href = "auth.html";
      return;
    }

    const data = await res.json();
    if (!res.ok) {
      alert(data.detail || "Analysis failed. Please try again.");
      return;
    }

    renderDashboard(data);
  } catch (err) {
    alert("Cannot reach server. Is the backend running on port 8000?");
    console.error(err);
  } finally {
    showLoading(false);
    document.getElementById("analyzeBtn").disabled = false;
  }
}

function showLoading(show) {
  const el = document.getElementById("loadingOverlay");
  el.classList.toggle("show", show);
}

// ============ RENDER ============
function fmt(n) {
  return "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function pct(part, total) {
  return total > 0 ? ((part / total) * 100).toFixed(1) : "0.0";
}

function renderDashboard(data) {
  // Stats
  document.getElementById("statTotal").textContent = fmt(data.total_spent);
  document.getElementById("statBudgetPct").textContent = `${pct(data.total_spent, data.monthly_limit)}% of budget used`;
  document.getElementById("statEssential").textContent = fmt(data.essential_total);
  document.getElementById("statEssentialPct").textContent = `${pct(data.essential_total, data.total_spent)}% of spending`;
  document.getElementById("statNonEssential").textContent = fmt(data.non_essential_total);
  document.getElementById("statNonEssentialPct").textContent = `${pct(data.non_essential_total, data.total_spent)}% of spending`;
  document.getElementById("statRemaining").textContent = fmt(data.remaining_budget);
  document.getElementById("statLimit").textContent = `of ${fmt(data.monthly_limit)} limit`;

  // Risk badge
  const riskBadge = document.getElementById("riskBadge");
  const rs = data.risk_score;
  let badgeClass = rs < 3 ? "badge-success" : rs < 6 ? "badge-warning" : "badge-danger";
  let badgeLabel = rs < 3 ? "Low Risk" : rs < 6 ? "Medium Risk" : "High Risk";
  riskBadge.innerHTML = `<span class="badge ${badgeClass}">⚠️ ${badgeLabel} (${rs}/10)</span>`;

  // Risk meter
  document.getElementById("riskScore").textContent = rs;
  const riskBar = document.getElementById("riskBar");
  riskBar.style.width = `${rs * 10}%`;
  riskBar.style.background = rs < 3 ? "var(--success)" : rs < 6 ? "var(--warning)" : "var(--danger)";

  // Budget bar
  const budgetPct = Math.min((data.total_spent / data.monthly_limit) * 100, 100);
  const budgetBar = document.getElementById("budgetBar");
  budgetBar.style.width = `${budgetPct}%`;
  budgetBar.style.background = budgetPct < 70 ? "var(--success)" : budgetPct < 90 ? "var(--warning)" : "var(--danger)";
  document.getElementById("budgetUsed").textContent = `${fmt(data.total_spent)} used`;
  document.getElementById("budgetLimit").textContent = `${fmt(data.monthly_limit)} limit`;

  // Patterns
  const patternsEl = document.getElementById("patternsContainer");
  patternsEl.innerHTML = (data.patterns || []).map(p => `<span class="pattern-tag">📌 ${p}</span>`).join("");

  // Charts
  renderPieChart(data.categories);
  renderBarChart(data.essential_total, data.non_essential_total);

  // Categories
  renderCategories(data.categories, data.total_spent);

  // Alerts
  renderAlerts(data.alerts);

  // Suggestions
  renderSuggestions(data.suggestions);

  // Show sections
  document.getElementById("chartsRow").style.display = "grid";
  document.getElementById("budgetRow").style.display = "grid";
  document.getElementById("categoriesSection").style.display = "block";
  document.getElementById("alerts-section").style.display = "grid";
}

// CHART COLORS
const CHART_COLORS = [
  "#6c63ff", "#38bdf8", "#22c55e", "#f59e0b",
  "#ef4444", "#a78bfa", "#fb923c", "#34d399",
  "#f472b6", "#60a5fa"
];

function renderPieChart(categories) {
  if (pieChartInstance) pieChartInstance.destroy();
  const ctx = document.getElementById("pieChart").getContext("2d");
  pieChartInstance = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: categories.map(c => c.category),
      datasets: [{
        data: categories.map(c => c.total),
        backgroundColor: CHART_COLORS.slice(0, categories.length),
        borderWidth: 2,
        borderColor: "#1a1e2e",
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "right",
          labels: { color: "#94a3b8", font: { size: 11 }, boxWidth: 12, padding: 10 }
        },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.label}: $${ctx.raw.toFixed(2)}`
          }
        }
      },
      cutout: "60%",
    }
  });
}

function renderBarChart(essential, nonEssential) {
  if (barChartInstance) barChartInstance.destroy();
  const ctx = document.getElementById("barChart").getContext("2d");
  barChartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Essential", "Non-Essential"],
      datasets: [{
        data: [essential, nonEssential],
        backgroundColor: ["rgba(34,197,94,0.7)", "rgba(239,68,68,0.7)"],
        borderColor: ["#22c55e", "#ef4444"],
        borderWidth: 2,
        borderRadius: 8,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: { label: (ctx) => ` $${ctx.raw.toFixed(2)}` }
        }
      },
      scales: {
        x: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#94a3b8" } },
        y: {
          grid: { color: "rgba(255,255,255,0.05)" },
          ticks: { color: "#94a3b8", callback: (v) => "$" + v }
        }
      }
    }
  });
}

function renderCategories(categories, total) {
  const container = document.getElementById("categoriesContainer");
  const colors = CHART_COLORS;
  container.innerHTML = categories.map((c, i) => `
    <div class="category-row">
      <span class="category-name" style="color:${colors[i % colors.length]}">${c.category}</span>
      <div class="category-bar-wrap">
        <div class="category-bar" style="width:${pct(c.total, total)}%; background:${colors[i % colors.length]}"></div>
      </div>
      <span class="category-amount">${fmt(c.total)}</span>
      <span style="font-size:0.75rem; color:var(--text-muted); min-width:40px;">${c.count}×</span>
    </div>
  `).join("");
}

function renderAlerts(alerts) {
  const container = document.getElementById("alertsContainer");
  if (!alerts || alerts.length === 0) {
    container.innerHTML = `<div class="empty-state"><div class="icon">✅</div><p>No alerts! Great job managing expenses.</p></div>`;
    return;
  }
  container.innerHTML = alerts.map(a => `
    <div class="alert-item ${a.severity}">
      <div class="alert-dot"></div>
      <span>${a.message}</span>
    </div>
  `).join("");
}

function renderSuggestions(suggestions) {
  const container = document.getElementById("suggestionsContainer");
  if (!suggestions || suggestions.length === 0) {
    container.innerHTML = `<div class="empty-state"><div class="icon">💡</div><p>No suggestions available.</p></div>`;
    return;
  }
  container.innerHTML = suggestions.map((s, i) => `
    <div class="suggestion-item">
      <div class="suggestion-num">${i + 1}</div>
      <span>${s}</span>
    </div>
  `).join("");
}
