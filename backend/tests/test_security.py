import pytest

from app import seed
from app.auth import hash_password, verify_password
from app.config import validate_secret


def test_passwords_are_salted_and_verified():
    first = hash_password("pulse123")
    second = hash_password("pulse123")
    assert first != second
    assert first.startswith("$2b$")
    assert verify_password("pulse123", first)
    assert not verify_password("wrong", first)
    assert not verify_password("pulse123", "old-sha256-hash")
    assert not verify_password("a" * 73, first)


@pytest.mark.parametrize("secret", ["", "ai-pulse-dev-secret", "short"])
def test_production_rejects_unsafe_secrets(secret):
    with pytest.raises(RuntimeError):
        validate_secret(secret, False)


def test_dev_secret_requires_explicit_dev_mode():
    assert validate_secret("", True) == "ai-pulse-dev-secret"
    assert validate_secret("a" * 40, False) == "a" * 40


def test_seed_refuses_production_before_dropping_tables(monkeypatch):
    monkeypatch.setattr(seed, "DEV_MODE", False)
    with pytest.raises(RuntimeError):
        seed.run()


def test_cors_rejects_unapproved_origin(client):
    response = client.options("/auth/login", headers={"Origin": "https://evil.test", "Access-Control-Request-Method": "POST"})
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_cors_allows_local_frontend(client):
    response = client.options("/auth/login", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
