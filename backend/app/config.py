import os

# Load .env if present (very small loader, no extra dependency)
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(_env_path):
    for line in open(_env_path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

APP_ENV = os.getenv("APP_ENV", "development")
SECRET_KEY = os.getenv("SECRET_KEY", "ai-pulse-dev-secret")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aipulse.db")
AI_MODE = os.getenv("AI_MODE", "mock")  # "mock" or "live"
LLM_API_URL = os.getenv("LLM_API_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")
TOKEN_HOURS = 12
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]


def validate_settings() -> None:
    """Fail closed when a production deployment is missing essential secrets."""
    if APP_ENV == "production" and SECRET_KEY == "ai-pulse-dev-secret":
        raise RuntimeError("SECRET_KEY must be configured in production")
    if AI_MODE not in {"mock", "live"}:
        raise RuntimeError("AI_MODE must be either 'mock' or 'live'")
    if AI_MODE == "live" and not all([LLM_API_URL, LLM_API_KEY, LLM_MODEL]):
        raise RuntimeError("LLM_API_URL, LLM_API_KEY, and LLM_MODEL are required in live AI mode")
