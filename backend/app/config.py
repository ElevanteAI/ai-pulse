import os
import secrets

# Load .env if present (very small loader, no extra dependency).
# Real environment variables always win over the file.
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(_env_path):
    for line in open(_env_path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

# Secure by default: anything that isn't explicitly dev/test is treated as production.
APP_ENV = os.getenv("APP_ENV", "production")
IS_DEV = APP_ENV in ("dev", "test")

SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    if not IS_DEV:
        raise RuntimeError("SECRET_KEY must be set when APP_ENV is not dev/test")
    SECRET_KEY = secrets.token_urlsafe(48)  # random per process, never a known value
elif not IS_DEV and (len(SECRET_KEY) < 32 or "change-me" in SECRET_KEY):
    raise RuntimeError("SECRET_KEY is too weak for production (need 32+ random characters)")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aipulse.db")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]

AI_MODE = os.getenv("AI_MODE", "mock")  # "mock" or "live"
LLM_API_URL = os.getenv("LLM_API_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")

TOKEN_HOURS = 12
# OWASP 2023 recommendation for PBKDF2-HMAC-SHA256. Tests lower it to keep the suite fast;
# the count is stored inside each hash, so existing hashes keep verifying if this changes.
PASSWORD_ITERATIONS = int(os.getenv("PASSWORD_ITERATIONS", "600000"))

# Client requirement (Northwind): no group smaller than this is ever reported on its own.
# Can be raised per deployment, never lowered below 5.
MIN_GROUP_SIZE = max(5, int(os.getenv("MIN_GROUP_SIZE", "5")))
