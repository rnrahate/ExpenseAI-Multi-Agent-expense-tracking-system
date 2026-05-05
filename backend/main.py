from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from backend.logger import get_run_log_dir, setup_logger
from backend.config import settings
from backend.database import connect_db, disconnect_db
from backend.auth import create_access_token, verify_token, hash_password, verify_password
from backend.models.schemas import SignupRequest, LoginRequest, AnalyzeRequest, TokenResponse, AnalyzeResponse
from backend.services.db_service import DBService
from backend.agents.orchestrator import Orchestrator
from backend.exceptions import AppException, DatabaseUnavailableError

logger = setup_logger(__name__)
bearer_scheme = HTTPBearer()
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
index_page = frontend_dir / "index.html"
auth_page = frontend_dir / "auth.html"
dashboard_page = frontend_dir / "dashboard.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    logger.info("Application started")
    logger.info(f"Run logs directory: {get_run_log_dir()}")
    yield
    await disconnect_db()
    logger.info("Application stopped")


app = FastAPI(title="Expense Agent AI", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return payload


@app.post("/signup", status_code=201)
async def signup(payload: SignupRequest):
    try:
        db = DBService()
        existing = await db.find_user_by_email(payload.email)
        if existing:
            raise AppException("Email already registered", 409)
        existing_phone = await db.find_user_by_phone(payload.phone_number)
        if existing_phone:
            raise AppException("Phone number already registered", 409)
        hashed = hash_password(payload.password)
        user_data = payload.dict()
        user_data["password"] = hashed
        user_id = await db.create_user(user_data)
        logger.info(f"New user registered: {payload.email}")
        return {"message": "Registration successful", "user_id": str(user_id)}
    except DatabaseUnavailableError as e:
        logger.error(f"Signup database error: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    try:
        db = DBService()
        user = None
        if payload.email:
            user = await db.find_user_by_email(payload.email)
        elif payload.phone_number:
            user = await db.find_user_by_phone(payload.phone_number)
        if not user or not verify_password(payload.password, user["password"]):
            raise AppException("Invalid credentials", 401)
        token = create_access_token({"sub": str(user["_id"]), "email": user["email"]})
        logger.info(f"User logged in: {user['email']}")
        return TokenResponse(access_token=token, token_type="bearer",
                             first_name=user["first_name"], email=user["email"])
    except DatabaseUnavailableError as e:
        logger.error(f"Login database error: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(payload: AnalyzeRequest, current_user: dict = Depends(get_current_user)):
    try:
        logger.info(f"Analyze request from user: {current_user['email']}")
        orchestrator = Orchestrator()
        result = await orchestrator.run(payload.expenses, payload.monthly_limit)
        return result
    except Exception as e:
        logger.error(f"Analyze error: {e}")
        raise HTTPException(status_code=500, detail="Analysis failed")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(index_page)


@app.get("/index", include_in_schema=False)
async def index_redirect():
    return RedirectResponse(url="/")


@app.get("/index.html", include_in_schema=False)
async def index_html_redirect():
    return RedirectResponse(url="/")


@app.get("/auth", include_in_schema=False)
async def auth_template():
    return FileResponse(auth_page)


@app.get("/auth/", include_in_schema=False)
async def auth_redirect():
    return RedirectResponse(url="/auth")


@app.get("/auth.html", include_in_schema=False)
async def auth_html_redirect():
    return RedirectResponse(url="/auth")


@app.get("/dashboard", include_in_schema=False)
async def dashboard_template():
    return FileResponse(dashboard_page)


@app.get("/dashboard/", include_in_schema=False)
async def dashboard_redirect():
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard.html", include_in_schema=False)
async def dashboard_html_redirect():
    return RedirectResponse(url="/dashboard")


app.mount("/", StaticFiles(directory=frontend_dir), name="frontend")
