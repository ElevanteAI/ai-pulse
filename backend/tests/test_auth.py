import jwt

from app import models
from app.auth import hash_password, verify_password
from app.db import SessionLocal
from tests.conftest import login


def test_password_hash_is_salted_and_verifies():
    a, b = hash_password("pulse123"), hash_password("pulse123")
    assert a != b  # random salt: same password, different hash
    assert a.startswith("pbkdf2_sha256$")
    assert verify_password("pulse123", a)
    assert not verify_password("wrong", a)


def test_old_unsalted_sha256_hash_is_not_accepted():
    legacy = "0944d46b846e79f412475fe55c645d59cfec36c4d303ffb143719796baf93015"  # sha256("pulse123")
    assert not verify_password("pulse123", legacy)


def test_login_wrong_password_and_unknown_email_look_the_same(client):
    r1 = client.post("/auth/login", json={"email": "priya@northwind.test", "password": "nope"})
    r2 = client.post("/auth/login", json={"email": "nobody@northwind.test", "password": "nope"})
    assert r1.status_code == r2.status_code == 401
    assert r1.json() == r2.json()


def test_login_email_is_case_insensitive(client):
    r = client.post("/auth/login", json={"email": " Priya@Northwind.TEST ", "password": "pulse123"})
    assert r.status_code == 200


def test_select_org_rejects_org_user_is_not_in(client):
    # Priya only belongs to Northwind
    r = client.post("/auth/login", json={"email": "priya@northwind.test", "password": "pulse123"})
    token = r.json()["token"]
    bluepeak_id = SessionLocal().query(models.Organization).filter_by(name="Bluepeak Retail").one().id
    r = client.post("/auth/select-org", json={"org_id": bluepeak_id}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    assert "token" not in r.json()


def test_token_signed_with_leaked_key_is_rejected(client):
    """The key committed in the original backend/.env must not be valid any more."""
    db = SessionLocal()
    meera = db.query(models.User).filter_by(email="meera@bluepeak.test").one()
    org = db.query(models.Organization).filter_by(name="Bluepeak Retail").one()
    forged = jwt.encode({"sub": str(meera.id), "org": org.id, "exp": 9999999999},
                        "pulse-7f3a9c2e1b-prod", algorithm="HS256")
    r = client.get("/reports/me", headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401


def test_requests_without_token_are_rejected(client):
    assert client.get("/reports/me").status_code == 401
    assert client.get("/diagnostic/questions").status_code == 401


def test_cors_does_not_allow_arbitrary_origins(client):
    r = client.options("/auth/login", headers={
        "Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert r.headers.get("access-control-allow-origin") != "https://evil.example"
    r = client.options("/auth/login", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_seed_refuses_to_run_in_production(monkeypatch):
    from app import seed
    monkeypatch.setattr(seed, "IS_DEV", False)
    try:
        seed.run()
    except SystemExit as e:
        assert "Refusing to seed" in str(e)
    else:
        raise AssertionError("seed.run() should refuse outside dev/test")


def test_login_helper_still_works(client):
    headers, data = login(client, "ravi@consult.test", "Bluepeak Retail")
    assert client.get("/reports/me", headers=headers).status_code == 200
