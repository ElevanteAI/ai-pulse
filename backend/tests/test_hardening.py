import os
import subprocess
import sys

from app import models
from app.auth import hash_password, verify_password
from app.db import SessionLocal
from tests.conftest import login

BACKEND = os.path.join(os.path.dirname(__file__), "..")


def test_password_hashes_are_salted_and_verify():
    a, b = hash_password("pulse123"), hash_password("pulse123")
    assert a != b and a.startswith("pbkdf2$")
    assert verify_password("pulse123", a)
    assert not verify_password("wrong", a)


def test_old_unsalted_or_garbage_hashes_do_not_verify():
    assert not verify_password("pulse123", "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08")
    assert not verify_password("pulse123", "")


def test_repeated_failed_logins_are_blocked(client):
    bad = {"email": "asha@northwind.test", "password": "nope"}
    assert [client.post("/auth/login", json=bad).status_code for _ in range(5)] == [401] * 5
    assert client.post("/auth/login", json=bad).status_code == 429
    # even the right password is refused while locked out
    good = {"email": "asha@northwind.test", "password": "pulse123"}
    assert client.post("/auth/login", json=good).status_code == 429


def test_successful_login_clears_failures(client):
    bad = {"email": "asha@northwind.test", "password": "nope"}
    good = {"email": "asha@northwind.test", "password": "pulse123"}
    for _ in range(4):
        client.post("/auth/login", json=bad)
    assert client.post("/auth/login", json=good).status_code == 200
    for _ in range(4):
        assert client.post("/auth/login", json=bad).status_code == 401


def test_sensitive_actions_are_audited(client):
    admin, data = login(client, "asha@northwind.test", "Northwind Logistics")
    client.get(f"/dashboard?org_id={data['organizations'][0]['org_id']}", headers=admin)
    client.get("/playbooks/policy_unaware", headers=admin)
    emp, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    client.delete("/diagnostic/me", headers=emp)

    db = SessionLocal()
    actions = [r.action for r in db.query(models.AuditLog).order_by(models.AuditLog.id)]
    db.close()
    assert actions == ["dashboard_view", "playbook_view", "responses_deleted"]


def test_blocked_dashboard_request_is_not_audited(client):
    admin, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    client.get("/dashboard?org_id=2", headers=admin)
    db = SessionLocal()
    assert db.query(models.AuditLog).count() == 0
    db.close()


def _import_config(**env):
    full = {**os.environ, **env}
    return subprocess.run([sys.executable, "-c", "import app.config"], cwd=BACKEND, env=full,
                          capture_output=True, text=True)


def test_production_refuses_default_secret():
    r = _import_config(APP_ENV="production", SECRET_KEY="ai-pulse-dev-secret")
    assert r.returncode != 0 and "SECRET_KEY" in r.stderr


def test_production_accepts_custom_secret():
    assert _import_config(APP_ENV="production", SECRET_KEY="something-private").returncode == 0


def test_cors_is_not_wide_open(client):
    r = client.options("/health", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert r.headers.get("access-control-allow-origin") != "*"
    assert "access-control-allow-origin" not in r.headers
    ok = client.options("/health", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
