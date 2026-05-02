# 💸 ExpenseAI — Agentic AI Expense Management System

> An intelligent, production-ready expense management system powered by a multi-agent AI pipeline using Google Gemini, FastAPI, and MongoDB.

---

## ✨ Features

- 🔐 **Secure Auth** — JWT-based login/signup with bcrypt password hashing
- 🤖 **Multi-Agent AI Pipeline** — Ingestion → Classification → Pattern Detection → Risk Evaluation → Suggestion Generation
- 🧠 **Google Gemini AI** — Smart expense classification and personalized financial suggestions
- 📊 **Interactive Dashboard** — Real-time charts (pie + bar), category breakdown, budget tracker
- 🔔 **Smart Alerts** — Budget overruns, harmful expenses, large transactions
- 🏷️ **Auto-Categorization** — Rule-based + AI fallback classification
- ⚠️ **Risk Scoring** — 0-10 financial risk score with severity indicators
- 📱 **Responsive UI** — Modern dark theme, mobile-friendly layout

---

## 🧱 Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.11+ |
| Database | MongoDB (Motor async driver) |
| Auth | JWT (PyJWT), passlib[bcrypt] |
| AI/LLM | Google Gemini 1.5 Flash |
| Agent Orchestration | Custom pipeline (LangChain-compatible) |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Charts | Chart.js v4 |

---

## 📁 Project Structure

```
expense-agent-ai/
│
├── backend/
│   ├── main.py                 # FastAPI app, routes
│   ├── config.py               # Pydantic settings
│   ├── logger.py               # Logging setup
│   ├── exceptions.py           # Custom exceptions
│   ├── auth.py                 # JWT + bcrypt
│   ├── database.py             # MongoDB connection
│   │
│   ├── agents/
│   │   ├── orchestrator.py     # Pipeline coordinator
│   │   ├── ingestion_agent.py  # Validate & normalize
│   │   ├── classification_agent.py  # Rule + AI classify
│   │   ├── pattern_agent.py    # Spending pattern detection
│   │   ├── risk_agent.py       # Risk scoring & alerts
│   │   └── suggestion_agent.py # Gemini suggestions
│   │
│   ├── services/
│   │   ├── gemini_service.py   # Gemini API wrapper
│   │   └── db_service.py       # MongoDB operations
│   │
│   ├── models/schemas.py       # Pydantic schemas
│   ├── utils/
│   │   ├── helpers.py          # Utility functions
│   │   └── validators.py       # Input validation
│   │
│   ├── .env                    # Environment variables
│   └── requirements.txt
│
├── frontend/
│   ├── auth.html               # Login/Signup page
│   ├── dashboard.html          # Main dashboard
│   ├── styles.css              # Global dark theme styles
│   ├── auth.js                 # Auth API calls
│   └── app.js                  # Dashboard logic + charts
│
├── README.md
└── .gitignore
```

---

## ⚙️ Setup Instructions

### 1. Prerequisites
- Python 3.11+
- MongoDB running locally (or MongoDB Atlas URI)
- Google Gemini API key ([get one here](https://aistudio.google.com/))

### 2. Clone & Configure

```bash
git clone https://github.com/yourusername/expense-agent-ai.git
cd expense-agent-ai
```

### 3. Configure Environment Variables

Edit `backend/.env`:

```env
GEMINI_API_KEY=your_gemini_api_key_here
MONGO_URI=mongodb://localhost:27017
SECRET_KEY=your_super_secret_jwt_key_change_this
```

### 4. Install Backend Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Run the Backend

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend runs at: `http://localhost:8000`  
API docs at: `http://localhost:8000/docs`

### 6. Open the Frontend

Simply open `frontend/auth.html` in your browser (or serve with a static file server):

```bash
# Option A: Direct open
open frontend/auth.html

# Option B: Python static server
cd frontend
python -m http.server 3000
# Open http://localhost:3000/auth.html
```

---

## 🌐 API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/signup` | No | Register new user |
| POST | `/login` | No | Login, get JWT token |
| POST | `/analyze` | JWT | Run AI expense analysis |
| GET | `/health` | No | Health check |

### Example: Analyze Request

```json
POST /analyze
Authorization: Bearer <token>

{
  "expenses": [
    {"description": "Grocery shopping", "amount": 285.50, "date": "2024-01-15"},
    {"description": "Netflix", "amount": 15.99, "date": "2024-01-15"}
  ],
  "monthly_limit": 3000
}
```

---

## 🔐 Environment Variables

| Variable | Description | Example |
|---|---|---|
| `GEMINI_API_KEY` | Google AI Studio API key | `AIza...` |
| `MONGO_URI` | MongoDB connection string | `mongodb://localhost:27017` |
| `SECRET_KEY` | JWT signing secret (change in production!) | `my-secret-key-123` |

---

## 🤖 Agent Pipeline

```
User Expenses
     │
     ▼
IngestionAgent      → Validate & normalize expense data
     │
     ▼
ClassificationAgent → Rule-based + Gemini AI categorization
     │
     ▼
PatternAgent        → Detect spending patterns & compute totals
     │
     ▼
RiskAgent           → Score financial risk, generate alerts
     │
     ▼
SuggestionAgent     → Gemini-powered personalized tips
     │
     ▼
Dashboard Response
```

---

## 📸 Screenshots

![Project Screenshot](image.png)

---

## 📄 Documentation
- `auth.html` — Login/Signup page
- `dashboard.html` — Full analytics dashboard with charts and insights

---

## 🚀 Future Improvements

- [ ] Receipt OCR upload (image → expense extraction)
- [ ] CSV/bank statement import
- [ ] Monthly trend analysis & historical graphs
- [ ] Email/SMS alerts for budget overruns
- [ ] Multi-currency support
- [ ] Recurring expense detection
- [ ] Export reports as PDF
- [ ] PWA / Mobile app wrapper
- [ ] Google OAuth integration

---

## 📄 License

MIT License — free to use for personal and commercial projects.
