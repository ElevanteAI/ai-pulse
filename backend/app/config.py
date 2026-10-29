import os

# Load .env if present (very small loader, no extra dependency)
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(_env_path):
    for line in open(_env_path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

def validate_secret(secret, dev_mode):
    if not dev_mode and (len(secret) < 32 or secret == "ai-pulse-dev-secret"):
        raise RuntimeError("Set a unique SECRET_KEY of at least 32 characters, or explicitly enable DEV_MODE for local development")
    return secret or "ai-pulse-dev-secret"


DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"
SECRET_KEY = validate_secret(os.getenv("SECRET_KEY", ""), DEV_MODE)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aipulse.db")
AI_MODE = os.getenv("AI_MODE", "mock")  # "mock" or "live"
LLM_API_URL = os.getenv("LLM_API_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")
TOKEN_HOURS = 12
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]
if "*" in CORS_ORIGINS:
    raise RuntimeError("CORS_ORIGINS must contain explicit origins")
