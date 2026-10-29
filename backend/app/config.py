import os

# Load .env if present (very small loader, no extra dependency)
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(_env_path):
    for line in open(_env_path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

_DEV_SECRET = "ai-pulse-dev-secret"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")  # "production" on the deployed server
SECRET_KEY = os.getenv("SECRET_KEY", _DEV_SECRET)
if ENVIRONMENT == "production" and SECRET_KEY == _DEV_SECRET:
    raise RuntimeError("SECRET_KEY must be set to a long random value in production")


def _normalize_db_url(url: str) -> str:
    # Hosts hand out "postgres://..." or "postgresql://..."; SQLAlchemy needs the driver name
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


DATABASE_URL = _normalize_db_url(os.getenv("DATABASE_URL", "sqlite:///./aipulse.db"))
# Comma-separated list of frontend origins allowed to call the API, e.g. https://ai-pulse.onrender.com
ALLOWED_ORIGINS = [o.strip().rstrip("/") for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
AUTO_SEED = os.getenv("AUTO_SEED", "false").lower() == "true"  # create demo data on first start if the DB is empty
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "pulse123")
AI_MODE = os.getenv("AI_MODE", "mock")  # "mock" or "live"
LLM_API_URL = os.getenv("LLM_API_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")
TOKEN_HOURS = 12
MIN_GROUP_SIZE = 5  # departments with fewer respondents are never shown on their own
