"""CORS is configured from the environment at import time, so each case runs in a fresh interpreter."""
import json
import os
import subprocess
import sys

BACKEND = os.path.join(os.path.dirname(__file__), "..")
FRONTEND = "https://ai-pulse-frontend-u0aj.onrender.com"

SCRIPT = """
import json, os
os.environ["DATABASE_URL"] = "sqlite:///./cors_test.db"
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
def pre(origin, path="/auth/login"):
    r = c.options(path, headers={"Origin": origin, "Access-Control-Request-Method": "POST",
                                 "Access-Control-Request-Headers": "content-type,authorization"})
    return {"status": r.status_code, "origin": r.headers.get("access-control-allow-origin"),
            "credentials": r.headers.get("access-control-allow-credentials")}
print(json.dumps({o: pre(o) for o in json.loads(os.environ["ORIGINS_TO_TRY"])}))
"""


def preflight(origins, **env):
    clean = {k: v for k, v in os.environ.items() if k not in ("CLIENT_URL", "CORS_ORIGINS")}
    full = {**clean, **env, "ORIGINS_TO_TRY": json.dumps(origins), "PYTHONPATH": BACKEND}
    r = subprocess.run([sys.executable, "-c", SCRIPT], cwd=BACKEND, env=full, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_deployed_frontend_origin_is_allowed_with_credentials_via_client_url():
    got = preflight([FRONTEND], CLIENT_URL=FRONTEND)[FRONTEND]
    assert got == {"status": 200, "origin": FRONTEND, "credentials": "true"}


def test_deployed_frontend_origin_is_allowed_via_cors_origins():
    assert preflight([FRONTEND], CORS_ORIGINS=FRONTEND)[FRONTEND]["origin"] == FRONTEND


def test_trailing_slash_in_setting_is_normalised():
    assert preflight([FRONTEND], CLIENT_URL=FRONTEND + "/")[FRONTEND]["status"] == 200


def test_unlisted_origins_are_rejected():
    got = preflight([FRONTEND, "https://evil.example", "http://ai-pulse-frontend-u0aj.onrender.com"],
                    CLIENT_URL=FRONTEND)
    assert got["https://evil.example"]["status"] == 400
    assert got["http://ai-pulse-frontend-u0aj.onrender.com"]["status"] == 400  # wrong scheme
    assert got[FRONTEND]["status"] == 200


def test_without_configuration_only_local_dev_is_allowed():
    """This is the state the live Render service was in: the frontend origin gets a 400."""
    got = preflight([FRONTEND, "http://localhost:5173"])
    assert got[FRONTEND]["status"] == 400
    assert got["http://localhost:5173"]["status"] == 200


def test_wildcard_never_comes_with_credentials():
    got = preflight([FRONTEND], CORS_ORIGINS="*")[FRONTEND]
    assert got["credentials"] is None
