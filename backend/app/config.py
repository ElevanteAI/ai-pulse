import os

# Load .env if present (very small loader, no extra dependency)
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(_env_path):
    for line in open(_env_path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

APP_ENV = os.getenv("APP_ENV", "dev")  # "production" turns on the startup check below
_DEV_SECRET = "ai-pulse-dev-secret"
SECRET_KEY = os.getenv("SECRET_KEY", _DEV_SECRET)
if APP_ENV == "production" and SECRET_KEY == _DEV_SECRET:
    raise RuntimeError("SECRET_KEY must be set to a private value when APP_ENV=production")
# Browser origins allowed to call the API (supports CORS_ORIGINS and CLIENT_URL)
CLIENT_URL = os.getenv("CLIENT_URL", "")
_origins = [o.strip().rstrip("/") for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
if CLIENT_URL:
    for u in CLIENT_URL.split(","):
        cleaned = u.strip().rstrip("/")
        if cleaned and cleaned not in _origins:
            _origins.append(cleaned)
CORS_ORIGINS = _origins
PASSWORD_ITERATIONS = int(os.getenv("PASSWORD_ITERATIONS", "600000"))
LOGIN_MAX_FAILURES = 5
LOGIN_WINDOW_SECONDS = 15 * 60
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aipulse.db")
AI_MODE = os.getenv("AI_MODE", "mock")  # "mock" or "live"
LLM_API_URL = os.getenv("LLM_API_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")
TOKEN_HOURS = 12
