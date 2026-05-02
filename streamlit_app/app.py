import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime
import json

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
API_BASE = "http://localhost:8001"

st.set_page_config(
    page_title="ExpenseAI",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Main background */
.stApp { background: #0d0f14; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: #141720 !important;
    border-right: 1px solid rgba(255,255,255,0.07);
}

/* Hide streamlit branding */
#MainMenu, footer, header { visibility: hidden; }

/* Metric cards */
[data-testid="metric-container"] {
    background: #1a1e2e;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 1rem 1.25rem;
}

[data-testid="stMetricValue"] { color: #e2e8f0 !important; font-weight: 800; }
[data-testid="stMetricLabel"] { color: #94a3b8 !important; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; }
[data-testid="stMetricDelta"] svg { display: none; }

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #6c63ff, #8b5cf6) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    padding: 0.6rem 1.5rem !important;
    transition: all 0.2s !important;
}
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 20px rgba(108,99,255,0.4) !important; }

/* Input fields */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stDateInput > div > div > input {
    background: #1a1e2e !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    color: #e2e8f0 !important;
    border-radius: 10px !important;
}

/* Dataframe */
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: #141720; border-radius: 10px; padding: 4px; }
.stTabs [data-baseweb="tab"] { color: #94a3b8 !important; border-radius: 8px; }
.stTabs [aria-selected="true"] { background: #6c63ff !important; color: white !important; }

/* Alerts */
.alert-box {
    padding: 0.75rem 1rem;
    border-radius: 10px;
    margin-bottom: 0.5rem;
    font-size: 0.875rem;
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
}
.alert-high { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); color: #fca5a5; }
.alert-medium { background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.3); color: #fcd34d; }
.alert-low { background: rgba(56,189,248,0.1); border: 1px solid rgba(56,189,248,0.3); color: #7dd3fc; }

.suggestion-box {
    background: rgba(108,99,255,0.08);
    border: 1px solid rgba(108,99,255,0.2);
    border-radius: 10px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.5rem;
    font-size: 0.875rem;
    color: #c4b5fd;
}
.pattern-tag {
    display: inline-block;
    background: rgba(56,189,248,0.1);
    border: 1px solid rgba(56,189,248,0.2);
    color: #7dd3fc;
    border-radius: 99px;
    padding: 0.3rem 0.75rem;
    font-size: 0.78rem;
    margin: 0.2rem;
}

.risk-badge {
    display: inline-block;
    padding: 0.35rem 1rem;
    border-radius: 99px;
    font-size: 0.85rem;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
if "token" not in st.session_state:
    st.session_state.token = None
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "page" not in st.session_state:
    st.session_state.page = "auth"


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def fmt(n):
    return f"${n:,.2f}"


def api_post(endpoint, payload, auth=False):
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    try:
        res = requests.post(f"{API_BASE}{endpoint}", json=payload, headers=headers, timeout=30)
        return res.status_code, res.json()
    except requests.exceptions.ConnectionError:
        return 0, {"detail": "Cannot connect to backend. Is it running on port 8000?"}
    except Exception as e:
        return 0, {"detail": str(e)}


def risk_color(score):
    if score < 3:
        return "#22c55e"
    elif score < 6:
        return "#f59e0b"
    else:
        return "#ef4444"


def risk_label(score):
    if score < 3:
        return "🟢 Low Risk"
    elif score < 6:
        return "🟡 Medium Risk"
    else:
        return "🔴 High Risk"


# ─────────────────────────────────────────────
# AUTH PAGE
# ─────────────────────────────────────────────
def render_auth():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div style='text-align:center; margin-bottom:2rem;'>
            <div style='font-size:3rem;'>💸</div>
            <h1 style='font-size:2rem; font-weight:800; margin:0; color:#e2e8f0;'>
                Expense<span style='color:#6c63ff;'>AI</span>
            </h1>
            <p style='color:#94a3b8; margin-top:0.25rem;'>Agentic AI-powered expense intelligence</p>
        </div>
        """, unsafe_allow_html=True)

        tab_login, tab_signup = st.tabs(["🔑 Sign In", "✨ Create Account"])

        # ── LOGIN ──
        with tab_login:
            st.markdown("<br>", unsafe_allow_html=True)
            identifier = st.text_input("Email or Phone", key="login_id", placeholder="email@example.com or +91...")
            password = st.text_input("Password", type="password", key="login_pass")

            if st.button("Sign In →", key="login_btn", use_container_width=True):
                if not identifier or not password:
                    st.error("Please fill all fields")
                else:
                    body = {"password": password}
                    if "@" in identifier:
                        body["email"] = identifier
                    else:
                        body["phone_number"] = identifier

                    with st.spinner("Signing in..."):
                        status, data = api_post("/login", body)

                    if status == 200:
                        st.session_state.token = data["access_token"]
                        st.session_state.user_name = data["first_name"]
                        st.session_state.user_email = data["email"]
                        st.session_state.page = "dashboard"
                        st.success("Login successful! Redirecting...")
                        st.rerun()
                    else:
                        st.error(data.get("detail", "Login failed"))

        # ── SIGNUP ──
        with tab_signup:
            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                first_name = st.text_input("First Name", key="su_fname")
            with c2:
                last_name = st.text_input("Last Name", key="su_lname")
            email = st.text_input("Email", key="su_email")
            phone = st.text_input("Phone Number", key="su_phone", placeholder="+91 9876543210")
            pwd = st.text_input("Password", type="password", key="su_pass", help="Minimum 6 characters")

            if st.button("Create Account →", key="signup_btn", use_container_width=True):
                first_name = first_name.strip()
                last_name = last_name.strip()
                email = email.strip()
                phone = phone.strip()
                pwd = pwd.strip()

                if not all([first_name, last_name, email, phone, pwd]):
                    st.error("Please fill all fields")
                elif len(pwd) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    status, data = api_post("/signup", {
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                        "phone_number": phone,
                        "password": pwd
                    })

                    if status == 201:
                        st.success("Account created! Please sign in.")
                    else:
                        st.error(data.get("detail", "Signup failed"))

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown(f"""
        <div style='display:flex; align-items:center; gap:0.75rem; margin-bottom:2rem; padding:0.5rem;'>
            <div style='width:40px;height:40px;background:linear-gradient(135deg,#6c63ff,#38bdf8);
                        border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:1.2rem;'>💸</div>
            <div>
                <div style='font-weight:800;font-size:1.1rem;color:#e2e8f0;'>Expense<span style="color:#6c63ff;">AI</span></div>
                <div style='font-size:0.72rem;color:#94a3b8;'>Agentic Intelligence</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("**NAVIGATION**")
        pages = {
            "📊 Dashboard": "dashboard",
            "🤖 Analyze": "analyze",
            "📋 History": "history",
        }
        for label, pg in pages.items():
            if st.button(label, key=f"nav_{pg}", use_container_width=True):
                st.session_state.page = pg
                st.rerun()

        st.markdown("---")

        # User widget
        initials = st.session_state.user_name[0].upper() if st.session_state.user_name else "U"
        st.markdown(f"""
        <div style='background:#1a1e2e;border-radius:12px;padding:0.75rem;display:flex;
                    align-items:center;gap:0.75rem;margin-bottom:0.75rem;'>
            <div style='width:36px;height:36px;background:linear-gradient(135deg,#6c63ff,#8b5cf6);
                        border-radius:50%;display:flex;align-items:center;justify-content:center;
                        font-weight:700;color:white;'>{initials}</div>
            <div>
                <div style='font-size:0.875rem;font-weight:600;color:#e2e8f0;'>{st.session_state.user_name}</div>
                <div style='font-size:0.72rem;color:#94a3b8;'>{st.session_state.user_email}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🚪 Sign Out", key="logout", use_container_width=True):
            for k in ["token", "user_name", "user_email", "analysis_result"]:
                st.session_state[k] = None if k in ["token", "analysis_result"] else ""
            st.session_state.page = "auth"
            st.rerun()


# ─────────────────────────────────────────────
# ANALYZE PAGE  (input form)
# ─────────────────────────────────────────────
def render_analyze():
    st.markdown("## 🤖 AI Expense Analyzer")
    st.markdown("<p style='color:#94a3b8;'>Enter your expenses and let the AI agent pipeline do the rest.</p>", unsafe_allow_html=True)

    # Monthly limit
    monthly_limit = st.number_input(
        "💳 Monthly Budget Limit ($)", min_value=1.0, value=3000.0, step=50.0
    )

    st.markdown("---")
    st.markdown("### 📝 Add Expenses")

    # Dynamic rows stored in session state
    if "expense_rows" not in st.session_state:
        st.session_state.expense_rows = [
            {"desc": "Grocery shopping", "amount": 285.0, "date": date.today()},
            {"desc": "Netflix subscription", "amount": 15.99, "date": date.today()},
            {"desc": "Electricity bill", "amount": 120.0, "date": date.today()},
            {"desc": "Restaurant dinner", "amount": 85.0, "date": date.today()},
            {"desc": "Uber rides", "amount": 45.0, "date": date.today()},
            {"desc": "Online shopping", "amount": 230.0, "date": date.today()},
        ]

    rows = st.session_state.expense_rows
    to_delete = []

    for i, row in enumerate(rows):
        c1, c2, c3, c4 = st.columns([3, 1.5, 1.5, 0.4])
        with c1:
            rows[i]["desc"] = st.text_input(
                "Description" if i == 0 else " ", key=f"desc_{i}",
                value=row["desc"], label_visibility="visible" if i == 0 else "collapsed"
            )
        with c2:
            rows[i]["amount"] = st.number_input(
                "Amount ($)" if i == 0 else " ", key=f"amt_{i}",
                value=float(row["amount"]), min_value=0.01, step=1.0,
                label_visibility="visible" if i == 0 else "collapsed"
            )
        with c3:
            rows[i]["date"] = st.date_input(
                "Date" if i == 0 else " ", key=f"date_{i}",
                value=row["date"],
                label_visibility="visible" if i == 0 else "collapsed"
            )
        with c4:
            st.markdown("<br>" if i == 0 else "", unsafe_allow_html=True)
            if st.button("✕", key=f"del_{i}"):
                to_delete.append(i)

    for i in reversed(to_delete):
        st.session_state.expense_rows.pop(i)
        st.rerun()

    col_add, col_analyze, _ = st.columns([1, 1.5, 3])
    with col_add:
        if st.button("＋ Add Row", use_container_width=True):
            st.session_state.expense_rows.append({"desc": "", "amount": 0.0, "date": date.today()})
            st.rerun()

    with col_analyze:
        run = st.button("🤖 Run AI Analysis", use_container_width=True)

    if run:
        expenses = [
            {"description": r["desc"], "amount": r["amount"],
             "date": r["date"].strftime("%Y-%m-%d") if r["date"] else None}
            for r in rows if r["desc"].strip() and r["amount"] > 0
        ]
        if not expenses:
            st.error("Add at least one valid expense (description + amount)")
            return

        with st.spinner("🤖 AI agents analyzing your expenses..."):
            status, data = api_post("/analyze", {
                "expenses": expenses,
                "monthly_limit": monthly_limit
            }, auth=True)

        if status == 200:
            st.session_state.analysis_result = data
            st.session_state.page = "dashboard"
            st.success("Analysis complete! Redirecting to dashboard...")
            st.rerun()
        elif status == 401:
            st.error("Session expired. Please log in again.")
            st.session_state.token = None
            st.session_state.page = "auth"
            st.rerun()
        else:
            st.error(data.get("detail", "Analysis failed. Check backend logs."))


# ─────────────────────────────────────────────
# DASHBOARD PAGE
# ─────────────────────────────────────────────
def render_dashboard():
    st.markdown("## 📊 Financial Dashboard")

    res = st.session_state.analysis_result

    if res is None:
        st.markdown("""
        <div style='text-align:center;padding:4rem 2rem;'>
            <div style='font-size:4rem;margin-bottom:1rem;'>🤖</div>
            <h3 style='color:#e2e8f0;'>No Analysis Yet</h3>
            <p style='color:#94a3b8;'>Go to the Analyze tab to run your first AI expense analysis.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🤖 Go to Analyzer", use_container_width=False):
            st.session_state.page = "analyze"
            st.rerun()
        return

    total = res["total_spent"]
    limit = res["monthly_limit"]
    remaining = res["remaining_budget"]
    essential = res["essential_total"]
    non_ess = res["non_essential_total"]
    risk = res["risk_score"]

    # ── TOP METRICS ──
    m1, m2, m3, m4, m5 = st.columns(5)
    pct_used = (total / limit * 100) if limit > 0 else 0
    ess_pct = (essential / total * 100) if total > 0 else 0
    ness_pct = (non_ess / total * 100) if total > 0 else 0

    m1.metric("💰 Total Spent", fmt(total), f"{pct_used:.1f}% of budget")
    m2.metric("✅ Essential", fmt(essential), f"{ess_pct:.1f}%")
    m3.metric("🛍️ Non-Essential", fmt(non_ess), f"{ness_pct:.1f}%")
    m4.metric("🎯 Remaining", fmt(remaining), f"of {fmt(limit)}")
    m5.metric("⚠️ Risk Score", f"{risk}/10", risk_label(risk))

    st.markdown("<br>", unsafe_allow_html=True)

    # ── BUDGET PROGRESS BAR ──
    bar_pct = min(pct_used, 100)
    bar_color = "#22c55e" if bar_pct < 70 else "#f59e0b" if bar_pct < 90 else "#ef4444"
    st.markdown(f"""
    <div style='margin-bottom:1.5rem;'>
        <div style='display:flex;justify-content:space-between;font-size:0.8rem;color:#94a3b8;margin-bottom:0.4rem;'>
            <span>Budget Used: {fmt(total)}</span>
            <span>Limit: {fmt(limit)}</span>
        </div>
        <div style='height:10px;background:#1a1e2e;border-radius:5px;overflow:hidden;border:1px solid rgba(255,255,255,0.07);'>
            <div style='height:100%;width:{bar_pct}%;background:{bar_color};border-radius:5px;
                        transition:width 1s ease;'></div>
        </div>
        <div style='text-align:right;font-size:0.75rem;color:{bar_color};margin-top:0.3rem;'>{bar_pct:.1f}% used</div>
    </div>
    """, unsafe_allow_html=True)

    # ── CHARTS ROW ──
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("#### 🍩 Spending by Category")
        cats = res.get("categories", [])
        if cats:
            df_cats = pd.DataFrame(cats)
            fig_pie = px.pie(
                df_cats, values="total", names="category",
                hole=0.55,
                color_discrete_sequence=px.colors.qualitative.Vivid,
            )
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#94a3b8", showlegend=True,
                legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8", size=11)),
                margin=dict(t=10, b=10, l=10, r=10),
                height=300,
            )
            fig_pie.update_traces(textfont_color="white", textinfo="percent+label")
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No category data")

    with chart_col2:
        st.markdown("#### 📊 Essential vs Non-Essential")
        fig_bar = go.Figure(data=[
            go.Bar(
                x=["Essential", "Non-Essential"],
                y=[essential, non_ess],
                marker_color=["rgba(34,197,94,0.8)", "rgba(239,68,68,0.8)"],
                marker_line_color=["#22c55e", "#ef4444"],
                marker_line_width=2,
                text=[fmt(essential), fmt(non_ess)],
                textposition="outside",
                textfont=dict(color="white", size=12),
            )
        ])
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#94a3b8", showlegend=False,
            margin=dict(t=30, b=10, l=10, r=10),
            height=300,
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickprefix="$"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ── CATEGORY BAR CHART ──
    st.markdown("#### 🏷️ Category Breakdown")
    cats = res.get("categories", [])
    if cats:
        df_cats = pd.DataFrame(cats).sort_values("total", ascending=True)
        fig_h = px.bar(
            df_cats, x="total", y="category", orientation="h",
            color="total",
            color_continuous_scale=["#6c63ff", "#38bdf8"],
            text=df_cats["total"].apply(lambda x: fmt(x)),
        )
        fig_h.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#94a3b8", coloraxis_showscale=False,
            margin=dict(t=10, b=10, l=10, r=10),
            height=max(200, len(cats) * 45),
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickprefix="$"),
            yaxis=dict(gridcolor="rgba(0,0,0,0)"),
        )
        fig_h.update_traces(textfont_color="white", textposition="outside")
        st.plotly_chart(fig_h, use_container_width=True)

    # ── RISK + PATTERNS ──
    risk_col, pat_col = st.columns([1, 2])

    with risk_col:
        st.markdown("#### ⚠️ Risk Meter")
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=risk,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "Risk Score", "font": {"color": "#94a3b8", "size": 14}},
            number={"font": {"color": risk_color(risk), "size": 40}},
            gauge={
                "axis": {"range": [0, 10], "tickcolor": "#94a3b8", "tickfont": {"color": "#94a3b8"}},
                "bar": {"color": risk_color(risk), "thickness": 0.3},
                "bgcolor": "#1a1e2e",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 3], "color": "rgba(34,197,94,0.15)"},
                    {"range": [3, 6], "color": "rgba(245,158,11,0.15)"},
                    {"range": [6, 10], "color": "rgba(239,68,68,0.15)"},
                ],
                "threshold": {"line": {"color": risk_color(risk), "width": 3}, "thickness": 0.75, "value": risk},
            }
        ))
        fig_gauge.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#94a3b8", height=250,
            margin=dict(t=30, b=10, l=20, r=20),
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

    with pat_col:
        st.markdown("#### 📌 Detected Patterns")
        patterns = res.get("patterns", [])
        if patterns:
            tags_html = "".join([f'<span class="pattern-tag">📌 {p}</span>' for p in patterns])
            st.markdown(tags_html, unsafe_allow_html=True)
        else:
            st.info("No patterns detected")

    # ── ALERTS + SUGGESTIONS ──
    al_col, sug_col = st.columns(2)

    with al_col:
        st.markdown("#### 🔔 Alerts")
        alerts = res.get("alerts", [])
        if alerts:
            for a in alerts:
                sev = a["severity"]
                icon = "🔴" if sev == "high" else "🟡" if sev == "medium" else "🔵"
                st.markdown(f"""
                <div class="alert-box alert-{sev}">
                    <span>{icon}</span>
                    <span>{a['message']}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ No alerts — great financial health!")

    with sug_col:
        st.markdown("#### 💡 AI Suggestions")
        suggestions = res.get("suggestions", [])
        for i, s in enumerate(suggestions, 1):
            st.markdown(f"""
            <div class="suggestion-box">
                <strong style='color:#8b85ff;'>#{i}</strong>&nbsp; {s}
            </div>
            """, unsafe_allow_html=True)

    # ── EXPENSE TABLE ──
    st.markdown("#### 📋 Classified Expenses")
    expenses = res.get("classified_expenses", [])
    if expenses:
        df = pd.DataFrame(expenses)
        cols = ["description", "amount", "category", "is_essential", "is_harmful", "classification_method"]
        cols = [c for c in cols if c in df.columns]
        df = df[cols].rename(columns={
            "description": "Description",
            "amount": "Amount ($)",
            "category": "Category",
            "is_essential": "Essential",
            "is_harmful": "Harmful",
            "classification_method": "Method",
        })
        df["Amount ($)"] = df["Amount ($)"].apply(lambda x: f"${x:,.2f}")
        st.dataframe(df, use_container_width=True, hide_index=True)

    # Re-analyze button
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Re-Analyze with New Expenses"):
        st.session_state.page = "analyze"
        st.rerun()


# ─────────────────────────────────────────────
# HISTORY PAGE (placeholder)
# ─────────────────────────────────────────────
def render_history():
    st.markdown("## 📋 Analysis History")
    st.info("This page will show historical analysis results stored in MongoDB. Connect to backend DB to populate.")
    if st.session_state.analysis_result:
        st.markdown("### Latest Analysis")
        st.json(st.session_state.analysis_result)


# ─────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────
def main():
    if not st.session_state.token:
        render_auth()
        return

    render_sidebar()

    page = st.session_state.page
    if page in ("dashboard", None):
        render_dashboard()
    elif page == "analyze":
        render_analyze()
    elif page == "history":
        render_history()
    else:
        render_dashboard()


if __name__ == "__main__":
    main()
